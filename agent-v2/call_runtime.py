"""Per-operation deadlines and usage; workers never write to the database."""
from __future__ import annotations

from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Any, Callable


class DeadlineExceeded(TimeoutError):
    pass


@dataclass
class Attempt:
    max_tokens: int
    deadline: float
    observed: bool = False
    usage: dict[str, int] = field(default_factory=dict)
    usage_known: bool = False
    cancelled: threading.Event = field(default_factory=threading.Event)
    closers: list[Callable] = field(default_factory=list)

    def check(self):
        if self.cancelled.is_set() or time.monotonic() >= self.deadline:
            raise DeadlineExceeded("operation deadline exceeded")


CURRENT: ContextVar[Attempt | None] = ContextVar("nia_attempt", default=None)
RUN_DEADLINE: float | None = None


def observe() -> None:
    state = CURRENT.get()
    if state:
        state.observed = True
        state.check()


def capture(usage: Any, provider: str) -> None:
    state = CURRENT.get()
    if not state or not usage:
        return
    def get(name, default=0):
        return usage.get(name, default) if isinstance(usage, dict) else getattr(usage, name, default)
    values: dict[str, int] = {}
    if provider == "chat":
        hit = int(get("prompt_cache_hit_tokens") or 0)
        tin, tout = get("prompt_tokens", None), get("completion_tokens", None)
        values = {"tokens_in": max(0, int(get("prompt_cache_miss_tokens", (tin or 0) - hit))),
                  "tokens_out": int(tout or 0), "cache_hit": hit}
    else:
        tin, tout = get("input_tokens", None), get("output_tokens", None)
        details = get("input_tokens_details", {}) or {}
        hit = int(get("cache_read_input_tokens") or (details.get("cached_tokens", 0) if isinstance(details, dict) else 0))
        values = {"tokens_in": max(0, int(tin or 0) - (hit if provider == "responses" else 0)),
                  "tokens_out": int(tout or 0), "cache_hit": hit}
        created = get("cache_creation", None)
        hour = (created.get("ephemeral_1h_input_tokens", 0) if isinstance(created, dict)
                else getattr(created, "ephemeral_1h_input_tokens", 0)) or 0
        values["cache_write_1h"] = int(hour)
        values["cache_write_5m"] = max(0, int(get("cache_creation_input_tokens") or 0) - int(hour))
        tool = get("server_tool_use", None)
        if tool:
            values["web_searches"] = int((tool.get("web_search_requests", 0) if isinstance(tool, dict)
                                           else getattr(tool, "web_search_requests", 0)) or 0)
    state.usage = values
    state.usage_known = tin is not None and tout is not None


def token_limit(default: int) -> int:
    state = CURRENT.get()
    return state.max_tokens if state else default


def check() -> None:
    state = CURRENT.get()
    if state:
        state.check()


def watch(resource: Any) -> None:
    state = CURRENT.get()
    close = getattr(resource, "close", None)
    if state and callable(close):
        state.closers.append(close)
        state.check()


def invoke(state: Attempt, fn: Callable):
    """Bound even a transport that blocks; close it without blocking the caller.

    A cancelled remote request may still be billed. Its reservation stays as
    unknown exposure. There is no database access or automatic retry in workers.
    """
    result = queue.Queue(maxsize=1)
    def worker():
        token = CURRENT.set(state)
        try:
            result.put((True, fn()))
        except BaseException as exc:
            result.put((False, exc))
        finally:
            CURRENT.reset(token)
    context = copy_context()
    threading.Thread(target=lambda: context.run(worker), daemon=True).start()
    try:
        while True:
            state.check()
            try:
                ok, value = result.get(timeout=min(15, max(.001, state.deadline - time.monotonic())))
                if ok:
                    return value
                raise value
            except queue.Empty:
                state.check()
                print("  [model] oczekuje na odpowiedz; pozostalo %.0f s" % (state.deadline - time.monotonic()), flush=True)
    except BaseException:
        state.cancelled.set()
        for close in state.closers:
            def safe_close(fn=close):
                try:
                    fn()
                except Exception:
                    pass
            threading.Thread(target=safe_close, daemon=True).start()
        raise

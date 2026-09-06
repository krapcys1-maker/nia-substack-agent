"""Record the bot's own Substack browser tab during one explicit action.

Raw frames stay in the active instance. Review them before sharing: a logged-in
browser may display private account details. This observer does not record the
desktop, inspect cookies, alter prompts, or enable publishing by itself.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent-v2"))


class Recorder:
    def __init__(self, directory: Path):
        self.directory = directory
        self.started = time.monotonic()
        self.frames: list[dict] = []
        self.pages = 0
        self.last_frame = -1.0
        self.errors: list[str] = []

    def attach(self, context, page):
        self.pages += 1
        number = self.pages
        page.set_viewport_size({"width": 1440, "height": 900})
        session = context.new_cdp_session(page)

        def frame(event):
            try:
                session.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            except Exception as exc:
                # The engine closes its tab after an action. A final queued
                # frame can arrive after closure; the observer must not fail it.
                if not page.is_closed():
                    self.errors.append(f"Frame acknowledgement: {type(exc).__name__}")
                return
            location = urlsplit(page.url)
            host = location.hostname or ""
            if not (host == "substack.com" or host.endswith(".substack.com")):
                return
            if location.path.startswith(("/api/", "/settings", "/sign-in", "/sign-up", "/account")):
                return
            elapsed = time.monotonic() - self.started
            if elapsed - self.last_frame < 0.16:
                return
            self.last_frame = elapsed
            name = f"frame-{len(self.frames):06d}.jpg"
            (self.directory / name).write_bytes(base64.b64decode(event["data"]))
            self.frames.append({"file": name, "seconds": round(elapsed, 3), "page": number})

        session.on("Page.screencastFrame", frame)
        session.send("Page.startScreencast", {
            "format": "jpeg", "quality": 82,
            "maxWidth": 1440, "maxHeight": 900, "everyNthFrame": 1,
        })

    def save(self, result):
        manifest = {
            "kind": "actual-browser-recording", "elapsed_seconds": round(time.monotonic() - self.started, 3),
            "frames": self.frames, "result": result,
            "capture_errors": self.errors,
            "privacy": "Private raw capture. Review every scene before publishing.",
        }
        (self.directory / "recording.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("sesja", "notka", "artykul", "komentarz", "polubienie", "restack", "subskrypcja"))
    parser.add_argument("--plik", type=Path, help="Note JSON from stages.note, or article Markdown")
    parser.add_argument("--kandydat", type=int, default=0, help="Index in stages.note's candidates array (default: 0)")
    parser.add_argument("--url", help="A specific Substack Note for a like or restack")
    parser.add_argument("--profil", help="Substack handle for a free subscription")
    parser.add_argument("--wyslij", action="store_true", help="Publish the supplied content on the active account")
    args = parser.parse_args()
    if args.action in ("notka", "artykul", "komentarz") and (not args.plik or not args.plik.is_file()):
        parser.error("notka/artykul/komentarz requires an existing --plik")
    if args.action in ("polubienie", "restack"):
        parsed = urlsplit(args.url or "")
        if parsed.scheme != "https" or parsed.hostname != "substack.com" or "/note/" not in parsed.path:
            parser.error("--url must be an https://substack.com/ Note URL")
    if args.action == "subskrypcja" and not args.profil:
        parser.error("subskrypcja requires --profil")
    if args.action == "sesja" and args.wyslij:
        parser.error("sesja is read-only")

    import config
    import preset
    import browser
    preset.wymagaj_aktywnego(config, "nagraj_publikacje.py")
    if args.wyslij and config.KILL_SWITCH:
        parser.error("KILL_SWITCH=true: publication disabled")
    directory = config.DATA_DIR / "nagrania" / time.strftime("%Y%m%d-%H%M%S")
    directory.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(directory)
    connect = browser.podlacz_sie

    def observed_connect():
        runtime, instance, context = connect()
        context.on("page", lambda page: recorder.attach(context, page))
        return runtime, instance, context

    browser.podlacz_sie = observed_connect
    result = {"completed": False}
    try:
        if args.action == "sesja":
            browser.sprawdz_sesje()
            result = {"session_check_completed": True}
        elif args.action == "notka":
            data = json.loads(args.plik.read_text(encoding="utf-8"))
            note = data
            if "candidates" in data:
                if not 0 <= args.kandydat < len(data["candidates"]):
                    raise ValueError("Candidate index outside the recorded result")
                note = data["candidates"][args.kandydat]
            if not note.get("note") or note.get("odrzucony") or note.get("safe_to_post") is False:
                raise ValueError("Missing note text or rejected candidate")
            result = browser.wystaw_notke(
                note["note"], wyslij=args.wyslij, typ=data.get("type", ""),
                forma=data.get("forma", data.get("form", "")), model=note.get("model", ""))
        elif args.action == "artykul":
            result = browser.wystaw_artykul(args.plik, wyslij=args.wyslij)
        elif args.action == "komentarz":
            from run import opis_celu

            data = json.loads(args.plik.read_text(encoding="utf-8"))
            candidates = data["result"]["candidates"]
            if not 0 <= args.kandydat < len(candidates):
                raise ValueError("Candidate index outside the recorded result")
            candidate = candidates[args.kandydat]
            if not candidate.get("comment") or candidate.get("odrzucony") or candidate.get("safe_to_post") is False:
                raise ValueError("Missing or rejected comment")
            target = data["target"]
            # Match the main bot's journal schema. The raw target has its own
            # rodzaj, which conflicts with the action kind after publication.
            context = opis_celu(target)
            if target.get("rodzaj") == "notka":
                result = browser.wystaw_odpowiedz(int(target["id"]), candidate["comment"],
                    wyslij=args.wyslij, rodzaj="komentarz", kontekst=context)
            else:
                result = browser.wystaw_komentarz(target["url"], candidate["comment"],
                    wyslij=args.wyslij, kontekst=context)
        elif args.action == "polubienie":
            result = browser.polub_w_kanale(1, wyslij=args.wyslij, url=args.url)
        elif args.action == "subskrypcja":
            result = browser.zasubskrybuj(args.profil.lstrip("@"), wyslij=args.wyslij)
        elif args.action == "restack":
            import db
            import stages
            conn = db.connect()
            run_id = db.start_run(conn, "record-restack")
            try:
                result = browser.restackuj_w_kanale(1,
                    lambda note: stages.ocen_restack(conn, run_id, note),
                    wyslij=args.wyslij, url=args.url)
                db.finish_run(conn, run_id, "DONE", "record-restack", "")
            except BaseException as exc:
                db.finish_run(conn, run_id, "FAILED", "record-restack", type(exc).__name__)
                raise
            finally:
                conn.close()
        print(json.dumps(result, ensure_ascii=False))
        success = result.get("wyslane") or result.get("zrobione") or result.get("polubione") or result.get("restackowane") or result.get("pominiete")
        return 0 if not result.get("blad") and (not args.wyslij or success) else 1
    finally:
        browser.podlacz_sie = connect
        recorder.save(result)
        print(f"Private recording: {directory} ({len(recorder.frames)} frames)")


if __name__ == "__main__":
    raise SystemExit(main())

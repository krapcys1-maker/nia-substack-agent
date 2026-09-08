"""Per-instance, per-URL feed recovery. Disk recovery is not network recovery."""
import hashlib
import json
import math
from pathlib import Path
import time
from xml.etree import ElementTree as ET

import result_cache
import retry_policy

FRESH_SECONDS = 1800
MAX_AGE_SECONDS = 86400
MAX_BYTES = 2_000_000


def _valid(body):
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        return False
    try:
        return ET.fromstring(body).tag in ('rss', '{http://www.w3.org/2005/Atom}feed', '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
    except (ET.ParseError, ValueError):
        return False


def fetch(directory, url, request, now=None):
    """Return validated XML and provenance; never refresh cache age on failure."""
    now = time.time() if now is None else now
    path = Path(directory) / 'feed-cache' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict) or state.get('url') != url:
            state = {}
    except (OSError, ValueError):
        state = {}
    try:
        age = now - float(state.get('fetched_at', 0))
        retry_at = float(state.get('retry_at', 0))
        failures = int(state.get('failures', 0))
        if not math.isfinite(age) or not math.isfinite(retry_at) or failures < 0:
            raise ValueError('Invalid cache timing')
    except (ValueError, TypeError, OverflowError):
        state, age, retry_at, failures = {}, MAX_AGE_SECONDS + 1, 0, 0
    try:
        body = bytes.fromhex(state.get('xml_hex', ''))
    except (ValueError, TypeError):
        body = b''
    usable = 0 <= age <= MAX_AGE_SECONDS and _valid(body)
    if usable and age < FRESH_SECONDS:
        return body, 'cache'
    if now < retry_at:
        return (body if usable else b''), ('stale' if usable else 'deferred')
    error, delay = '', 0
    try:
        response = request()
        if response.status_code == 200 and _valid(response.content):
            body = response.content
            state = dict(url=url, fetched_at=now, xml_hex=body.hex(), failures=0, retry_at=0, error='')
        else:
            error = 'HTTP %s' % response.status_code if response.status_code != 200 else 'invalid XML feed'
            delay = retry_policy.retry_after(getattr(response, 'headers', {}), now=now) or 0
    except Exception as exc:
        error = type(exc).__name__
    if error:
        failures += 1
        delay = max(delay, min(21600, 300 * 2 ** min(failures - 1, 7)))
        state.update(url=url, failures=failures, retry_at=now + delay, error=error)
    state['checked_at'] = now
    try:
        result_cache.write_json(path, state)
    except OSError:
        pass  # Fresh content remains usable when persistence is unavailable.
    if error:
        return (body if usable else b''), ('stale' if usable else 'unavailable')
    return body, 'network'

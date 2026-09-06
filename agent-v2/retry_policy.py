"""Remember server-requested pauses without treating a deferred call as an attempt."""
import math
import time
from datetime import timezone
from email.utils import parsedate_to_datetime

import result_cache


def retry_after(headers, now=None):
    """Retry-After can be seconds or an HTTP date; malformed values are ignored."""
    raw = headers.get('retry-after') if headers is not None else None
    if raw is None:
        return None
    now = time.time() if now is None else now
    try:
        seconds = float(raw)
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(str(raw))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = date.timestamp() - now
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0., seconds) if math.isfinite(seconds) else None


def path_for(directory, scope):
    return directory / 'retry-pauses' / (result_cache.digest(scope) + '.json')


def remaining(path):
    saved = result_cache.read(path, 366 * 86400)
    if not isinstance(saved, dict):
        return 0.
    try:
        seconds = float(saved['until']) - time.time()
        return max(0., seconds) if math.isfinite(seconds) else 0.
    except (KeyError, ValueError, TypeError):
        return 0.


def defer(path, seconds):
    if seconds > 0:
        result_cache.write(path, {'until': time.time() + max(seconds, remaining(path))})

"""Skip confirmed interactions before paying to write them again."""
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def target_key(value):
    value = str(value or '').strip()
    # A reply targets a specific parent, not every conversation on its profile.
    note = re.fullmatch(r'(?:https?://(?:www\.)?substack\.com/(?:@[^/]+/)?)?note/c-(\d+)/?(?:[?#].*)?', value)
    if note:
        return 'note/c-' + note[1]
    try:
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username:
            return ''
        # Keep content IDs in query strings; discard only known tracking fields.
        query = urlencode([(k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)
                           if not k.lower().startswith('utm_')])
        return urlunsplit(('https', url.netloc.lower(), url.path.rstrip('/'), query, ''))
    except ValueError:
        return ''


def confirmed_targets(directory):
    found = set()
    try:
        with (Path(directory) / 'dziennik.jsonl').open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row, dict) or row.get('udane') is not True or row.get('pominiete'):
                    continue
                if row.get('rodzaj') not in ('komentarz', 'odpowiedz'):
                    continue
                key = target_key(row.get('gdzie'))
                if key:
                    found.add(key)
    except OSError:
        pass  # The publisher's live duplicate check remains in place.
    return found


def unhandled(posts, directory):
    """Only confirmed target IDs are excluded; failed attempts remain eligible."""
    known = confirmed_targets(directory)
    result = [p for p in posts if not target_key(p.get('url')) or target_key(p.get('url')) not in known]
    if len(result) != len(posts):
        print('  [cele] already answered: %d; skipped before writing' % (len(posts) - len(result)), flush=True)
    return result

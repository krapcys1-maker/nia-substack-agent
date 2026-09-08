"""Read-only cost, outcome and research report. No application startup or API calls."""
import argparse
from contextlib import closing
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit


def moment(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def rows(path, warnings=None):
    result = []
    try:
        with Path(path).open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        result.append(item)
                except ValueError:
                    if warnings is not None:
                        warnings.add('incomplete_records')
    except FileNotFoundError:
        pass
    except OSError:
        if warnings is not None:
            warnings.add('unreadable_records')
    return result


def at_window(records, published, hours, now, field='wyswietlenia'):
    """Latest measured value at/before the horizon, no more than 2h earlier."""
    if published is None:
        return None
    target = published + timedelta(hours=hours)
    if now < target:
        return None
    candidates = []
    for row in records:
        # Read time is not measurement time when the platform reports a delay.
        measured = moment(row.get('zmierzone') or row.get('kiedy'))
        if measured is None or measured > now:
            continue
        value = number(row.get(field))
        if field == 'wyswietlenia' and row.get('ma_karty_zasiegu') is not True:
            value = None
        if value is not None and target - timedelta(hours=2) <= measured <= target:
            candidates.append((measured, value))
        windows = row.get('windows') or {}
        window = windows.get(str(hours), {}) if isinstance(windows, dict) else {}
        window = window if isinstance(window, dict) else {}
        if field == 'wyswietlenia' and window.get('published') == published.isoformat() and measured >= target:
            value = number(window.get('views'))
            if value is not None:
                candidates.append((target, value))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def graph_windows(card, published, measured):
    """Extract mature primary curves only; no invented values for missing windows."""
    start, end = moment(published), moment(measured)
    result = {}
    graph = card.get('graphData') if isinstance(card, dict) else None
    if not start or not end or not isinstance(graph, dict):
        return result
    series_list = graph.get('series')
    for series in series_list if isinstance(series_list, list) else []:
        if not isinstance(series, dict) or series.get('isPrimary') is not True:
            continue
        points = []
        values = series.get('values')
        for item in values if isinstance(values, list) else []:
            if not isinstance(item, dict):
                continue
            stamp, value = moment(item.get('timestamp')), number(item.get('value'))
            if stamp and value is not None and start <= stamp <= end:
                points.append((stamp, value))
        points.sort()
        for hours in (24, 48):
            target = start + timedelta(hours=hours)
            before = [(t, v) for t, v in points if target - timedelta(hours=2) <= t <= target]
            if before and points[-1][0] >= target:
                result[str(hours)] = dict(published=start.isoformat(), views=before[-1][1])
    return result


def channel(value):
    value = str(value or '')
    if value.startswith('komentarz'):
        return 'komentarz'
    return value if value in ('notka', 'artykul', 'odpowiedz', 'restack') else 'shared'


def collect(directory, days=7, now=None):
    directory = Path(directory).resolve()
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    warnings = set()
    journal = rows(directory / 'dziennik.jsonl', warnings)
    stats = rows(directory / 'statystyki.jsonl', warnings)
    calls, runs, sources = [], {}, []
    database = directory / 'agent-v2.db'
    if database.exists():
        try:
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'runs' in tables:
                    runs = {r['id']: dict(r) for r in conn.execute('SELECT * FROM runs')}
                if 'calls' in tables:
                    calls = [dict(r) for r in conn.execute('SELECT * FROM calls WHERE at>=?', (since.date().isoformat(),))]
                if 'sources' in tables:
                    sources = [dict(r) for r in conn.execute('SELECT * FROM sources WHERE at>=?', (since.date().isoformat(),))]
        except sqlite3.Error:
            warnings.add('database_unavailable')
    else:
        warnings.add('no_database')

    def in_period(value):
        stamp = moment(value)
        return stamp is not None and since <= stamp <= now

    def group():
        return dict(recorded_usd=0., unresolved_reserved_usd=0., unknown_attempts=0,
                    attempts=0, failed_attempts=0, publications=0, measured_24h=0,
                    measured_48h=0, views_24h=None, views_48h=None, period_usd_per_publication=None)

    groups = defaultdict(group)
    test_cost = 0.
    for call in calls:
        if not in_period(call.get('at')):
            continue
        measured_price = number(call.get('cost_usd'))
        price = measured_price or 0.
        if runs.get(call.get('run_id'), {}).get('tryb') == 'test':
            test_cost += price
            continue
        g = groups[channel(call.get('akcja'))]
        g['recorded_usd'] += price
        g['attempts'] += 1
        g['failed_attempts'] += int(not call.get('ok'))
        state = call.get('usage_status', 'legacy')
        unknown = measured_price is None or state in ('pending', 'unknown') or (state == 'legacy' and not call.get('ok') and not price)
        if unknown:
            g['unknown_attempts'] += 1
            g['unresolved_reserved_usd'] += number(call.get('reserved_usd')) or 0.
    per_id = defaultdict(list)
    for row in stats:
        per_id[str(row.get('rodzaj')), str(row.get('id'))].append(row)
    seen = set()
    publications = []
    for row in journal:
        kind = channel(row.get('rodzaj'))
        if kind == 'shared' or row.get('udane') is not True or row.get('pominiete') or not in_period(row.get('kiedy')):
            continue
        # Notes are published with `id`; replies use `nasz_id`. For interactions,
        # an unqualified `id` may identify somebody else's post, not our reply.
        own_id = row.get('nasz_id') or (row.get('id') if kind in ('notka', 'artykul') else None)
        identity = (kind, str(own_id or ''), str(row.get('gdzie') or row.get('tekst') or row.get('tytul') or ''))
        # Confirmed IDs are unique even if the recorded title/text later changes.
        if identity[1]:
            identity = identity[:2]
        if identity in seen:
            continue
        seen.add(identity)
        measured_kind = 'notka' if kind == 'restack' else kind
        observations = per_id[measured_kind, str(own_id)] if own_id else []
        dates = {moment(r.get('wystawione')) for r in observations if moment(r.get('wystawione'))}
        published = next(iter(dates)) if len(dates) == 1 else None
        # Legacy records can count publications, but not pretend to know their age.
        if not dates:
            published = moment(row.get('kiedy'))
        item = dict(kind=kind, id=own_id, published_at=published.isoformat() if published else None,
                    text=str(row.get('tekst') or row.get('tytul') or '')[:240])
        groups[kind]['publications'] += 1
        for hours in (24, 48):
            value = at_window(observations, published, hours, now)
            item['views_%dh' % hours] = value
            if value is not None:
                key = 'views_%dh' % hours
                groups[kind][key] = (groups[kind][key] or 0) + value
                groups[kind]['measured_%dh' % hours] += 1
        publications.append(item)
    for g in groups.values():
        for key in ('recorded_usd', 'unresolved_reserved_usd'):
            g[key] = round(g[key], 6)
        if g['publications'] and g['attempts'] and not g['unknown_attempts']:
            g['period_usd_per_publication'] = round(g['recorded_usd'] / g['publications'], 6)

    bank_path = directory / 'indeks_kandydatow.json'
    bank = read_json(bank_path)
    bank_available = isinstance(bank, list)
    if not bank_available:
        warnings.add('unreadable_idea_bank' if bank_path.exists() else 'no_idea_bank')
    bank = [r for r in bank if isinstance(r, dict)] if isinstance(bank, list) else []
    draft_choices = []
    def modified(path):
        try:
            return path.stat().st_mtime
        except OSError:
            return 0
    for path in sorted((directory / 'persona-drafts').glob('*.json'), key=modified, reverse=True)[:100]:
        row = read_json(path, {})
        if not isinstance(row, dict) or row.get('kind') != 'note' or not in_period(row.get('created_at')):
            continue
        urls = row.get('source_urls')
        urls = [u for u in urls if isinstance(u, str)] if isinstance(urls, list) else []
        draft_choices.append(dict(at=row.get('created_at'), run_id=row.get('run_id'),
                                  topic=row.get('topic', ''), status=row.get('status'),
                                  source_urls=urls))
    decisions = [r for r in rows(directory / 'editorial-decisions.jsonl', warnings) if in_period(r.get('at'))]
    research = []
    for path in (directory / 'research-tasks').glob('*.json'):
        item = read_json(path, {})
        if isinstance(item, dict) and in_period(item.get('at')):
            research.append({k: item.get(k) for k in ('at', 'run_id', 'title', 'question', 'lead_url', 'missing', 'held_sources')})
    feeds = []
    for path in (directory / 'feed-cache').glob('*.json'):
        item = read_json(path, {})
        if isinstance(item, dict) and item.get('url'):
            age = now.timestamp() - (number(item.get('fetched_at')) or 0)
            feeds.append(dict(url=item['url'], age_hours=round(age/3600, 1) if item.get('fetched_at') else None,
                              failures=item.get('failures', 0), error=item.get('error', ''),
                              retry_at=item.get('retry_at'), usable=0 <= age <= 86400 and bool(item.get('xml_hex'))))
    selected_domains = Counter()
    for d in draft_choices:
        for url in d['source_urls']:
            try:
                host = urlsplit(url).hostname
                if host:
                    selected_domains[host] += 1
            except ValueError:
                warnings.add('invalid_source_url')
    return dict(since=since.isoformat(), until=now.isoformat(), days=days,
                groups=dict(groups), test_recorded_usd=round(test_cost, 6), publications=publications[-100:],
                bank=dict(total=len(bank) if bank_available else None, statuses=dict(Counter(str(x.get('status', 'unknown')) for x in bank)),
                          candidates=[{k: x.get(k) for k in ('fact', 'url', 'source_date', 'status', 'ranga', 'na_artykul', 'powod', 'wazny_do')} for x in bank][-100:]),
                sources=dict(total=sum(in_period(s.get('at')) for s in sources),
                             failures=dict(Counter(str(s.get('fail_reason') or 'unknown') for s in sources if in_period(s.get('at')) and not s.get('fetched_ok')))),
                note_choices=draft_choices, selected_domains=dict(selected_domains), decisions=decisions[-100:],
                research=sorted(research, key=lambda r: r['at'], reverse=True)[:20], feeds=feeds,
                warnings=sorted(warnings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--days', type=int, choices=(7, 30), default=7)
    args = parser.parse_args()
    if args.data_dir is None:
        import config
        args.data_dir = config.DATA_DIR
    print(json.dumps(collect(args.data_dir, args.days), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

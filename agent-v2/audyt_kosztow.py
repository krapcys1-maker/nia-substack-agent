"""Read-only audit of the API ledger, research sources and editorial memory.

python agent-v2/audyt_kosztow.py [--data-dir PATH] [--min-run ID] [--json]
No provider requests, publications, schema migrations or memory writes.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3


def _json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _failure(note):
    text = str(note or '')
    status = re.search(r'\b([45]\d\d)\b', text)
    if status:
        return 'HTTP ' + status.group(1)
    if 'DeadlineExceeded' in text or 'Timeout' in text:
        return 'deadline/timeout'
    if 'ProtocolError' in text or 'incomplete chunked' in text:
        return 'connection interrupted'
    return 'other/unspecified'


def collect(directory, min_run=0):
    directory = Path(directory).resolve()
    path = directory / 'agent-v2.db'
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        calls = [dict(r) for r in conn.execute(
            'SELECT * FROM calls WHERE COALESCE(run_id,0)>=?', (min_run,))]
        sources = [dict(r) for r in conn.execute(
            'SELECT * FROM sources WHERE COALESCE(run_id,0)>=?', (min_run,))]
        articles = [dict(r) for r in conn.execute(
            'SELECT evidence FROM articles WHERE COALESCE(run_id,0)>=?', (min_run,))]
    finally:
        conn.close()
    purposes = defaultdict(lambda: dict(attempts=0, recorded_usd=0., failures=0,
        searches=0, input_tokens=0, output_tokens=0, cached_input_tokens=0))
    failures = Counter()
    states = Counter()
    exposure = 0.
    legacy_failed_without_usage = 0
    for call in calls:
        group = purposes[call['purpose']]
        group['attempts'] += 1
        group['recorded_usd'] += call.get('cost_usd') or 0.
        for key, source in [('searches','web_searches'),('input_tokens','tokens_in'),
                            ('output_tokens','tokens_out'),('cached_input_tokens','cache_hit')]:
            group[key] += call.get(source) or 0
        state = call.get('usage_status') or 'legacy'
        states[state] += 1
        if state in ('pending','unknown'):
            exposure += call.get('reserved_usd') or 0.
        if not call['ok']:
            group['failures'] += 1
            failures[_failure(call.get('note'))] += 1
            if state == 'legacy' and not any(call.get(k) for k in ('tokens_in','tokens_out','cache_hit','cost_usd')):
                legacy_failed_without_usage += 1
    for group in purposes.values():
        group['recorded_usd'] = round(group['recorded_usd'],6)

    index = _json(directory/'indeks_kandydatow.json', [])
    index = [x for x in index if isinstance(x,dict)] if isinstance(index,list) else []
    statuses = Counter(x.get('status','unknown') for x in index)
    exact = Counter(' '.join(str(x.get('fact') or '').split()) for x in index)
    now = datetime.now(timezone.utc)
    expired_new = 0
    for item in index:
        if item.get('status') != 'nowy':
            continue
        try:
            date = datetime.fromisoformat(str(item.get('wazny_do') or ''))
            date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
            expired_new += int(date <= now)
        except ValueError:
            pass
    fragments = Counter()
    for article in articles:
        try:
            card = json.loads(article.get('evidence') or '{}')
        except (ValueError,TypeError):
            continue
        if not isinstance(card,dict):
            continue
        for source in card.get('unused_evidence') or []:
            if not isinstance(source,dict):
                continue
            for fragment in source.get('excerpts') or []:
                text = ' '.join(str(fragment).split())
                if len(text) >= 60:
                    fragments[(str(source.get('url') or ''),text)] += 1
    outcomes = Counter()
    journal = directory/'dziennik.jsonl'
    if journal.exists():
        with journal.open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item,dict):
                    outcomes[(str(item.get('rodzaj','unknown')),item.get('udane') is True)] += 1
    return dict(
        directory=str(directory), min_run=min_run,
        recorded_usd=round(sum(x.get('cost_usd') or 0. for x in calls),6),
        attempts=len(calls), usage_states=dict(states), unresolved_reserved_usd=round(exposure,6),
        legacy_failures_without_usage=legacy_failed_without_usage,
        api_failures=dict(failures),
        by_purpose=dict(sorted(purposes.items(), key=lambda x:-x[1]['recorded_usd'])),
        sources=dict(total=len(sources), fetched=sum(bool(s.get('fetched_ok')) for s in sources),
            failures=dict(Counter(str(s.get('fail_reason') or 'unspecified') for s in sources if not s.get('fetched_ok')))),
        memory=dict(scope='whole instance; min_run only filters database records',
            candidates=len(index), statuses=dict(statuses), expired_new_with_explicit_date=expired_new,
            exact_duplicate_candidates=sum(n-1 for fact,n in exact.items() if fact and n>1),
            unused_fragment_occurrences=sum(fragments.values()), unique_unused_fragments=len(fragments),
            actions=[dict(kind=k,confirmed=ok,count=n) for (k,ok),n in sorted(outcomes.items())]),
        limits='Recorded estimates are not provider invoices. Legacy zero-cost failures may have been billed. '
               'Rejected material and failed requests are not automatically wasted spending. '
               'Copied databases overlap: do not add their totals without selecting disjoint runs. '
               'No prompt hashes exist in the historical ledger, so repeated purpose alone does not prove duplicate work.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--min-run',type=int,default=0)
    parser.add_argument('--json',action='store_true')
    args = parser.parse_args()
    if args.data_dir is None:
        import config
        args.data_dir = config.DATA_DIR
    report = collect(args.data_dir,args.min_run)
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(f"API: {report['attempts']} attempts; recorded ${report['recorded_usd']:.6f}")
        print(f"Unresolved reservations: ${report['unresolved_reserved_usd']:.6f}; legacy failures without usage: {report['legacy_failures_without_usage']}")
        for purpose,row in report['by_purpose'].items():
            print(f"  {purpose:22} ${row['recorded_usd']:.6f}  calls={row['attempts']} failed={row['failures']} searches={row['searches']}")
        print('API failures:',report['api_failures'])
        print('Research sources:',report['sources'])
        print('Memory:',report['memory'])
        print(report['limits'])


if __name__ == '__main__':
    main()

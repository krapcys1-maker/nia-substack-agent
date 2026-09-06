"""Bound source reads, including Playwright shutdown, in an owned subprocess."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def _stop_owned_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        # Only this child and its descendants; attached user Chrome is not one.
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _results(path):
    if not path.exists():
        return []
    entries=[]
    for line in path.read_bytes().decode('utf-8', errors='ignore').splitlines():
        try:
            entry=json.loads(line)
        except json.JSONDecodeError:
            continue  # The worker may still be writing its last line.
        if isinstance(entry, dict) and 'url' in entry:
            entries.append(entry)
    return entries


def _collect(command, urls, output, timeout):
    process=subprocess.Popen(command, start_new_session=os.name != 'nt')
    deadline=time.monotonic()+max(0, timeout)
    complete_at=None
    try:
        while process.poll() is None:
            entries=_results(output)
            now=time.monotonic()
            if len(entries) >= len(urls) and complete_at is None:
                complete_at=now
            if now >= deadline or (complete_at is not None and now-complete_at >= 2):
                print('  [przegladarka] limit odczytu/zamykania; zachowuje gotowe wyniki', flush=True)
                break
            time.sleep(.1)
    finally:
        _stop_owned_process(process)
    entries=_results(output)
    found={entry['url'] for entry in entries}
    entries.extend({'url':url, 'text':'', 'title':'', 'error':'browser read did not complete'}
                   for url in urls if url not in found)
    return entries


def read_pages(urls):
    if not urls:
        return []
    import call_runtime
    timeout=min(300, 30+50*len(urls))
    if call_runtime.RUN_DEADLINE is not None:
        timeout=min(timeout, max(0, call_runtime.RUN_DEADLINE-time.monotonic()))
    if timeout <= 0:
        raise call_runtime.DeadlineExceeded('run deadline exceeded before browser read')
    with tempfile.TemporaryDirectory(prefix='nia-read-') as directory:
        input_path=Path(directory)/'input.json'
        output=Path(directory)/'results.jsonl'
        input_path.write_text(json.dumps(urls),encoding='utf-8')
        return _collect([sys.executable, '-u', str(Path(__file__).resolve()),
                         '--worker', str(input_path), str(output)], urls, output, timeout)


def _worker(input_path, output):
    import browser
    urls=json.loads(Path(input_path).read_text(encoding='utf-8'))
    p, connection, context=browser.podlacz_sie()
    try:
        page=context.new_page()
        try:
            for url in urls:
                entry={'url':url, 'text':'', 'title':'', 'error':None}
                try:
                    page.goto(url,timeout=browser.READ_TIMEOUT_MS,wait_until='domcontentloaded')
                    page.wait_for_timeout(browser.SETTLE_MS)
                    entry['title']=page.title()
                    entry['text']=page.inner_text('body',timeout=browser.READ_TIMEOUT_MS)
                except Exception as exc:
                    entry['error']=f'{type(exc).__name__}: {exc}'[:200]
                with Path(output).open('a',encoding='utf-8') as handle:
                    handle.write(json.dumps(entry,ensure_ascii=False)+'\n')
                print('  [przegladarka] %s %d znakow %s' %
                      ('NIE' if entry['error'] else 'OK',len(entry['text']),url[:100]),flush=True)
        finally:
            page.close()
    finally:
        connection.close()
        p.stop()


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--worker':
        raise SystemExit('This module is a source-read worker, not a publishing command.')
    _worker(sys.argv[2],sys.argv[3])

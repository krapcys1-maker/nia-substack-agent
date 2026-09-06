"""Fixed operations launched by the local NIA panel, in a fresh process."""
from pathlib import Path
import os
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'agent-v2'))


def wait_for_parent():
    path = ROOT / 'agent-v2/data/panel/config.lock'
    for attempt in range(100):
        with path.open('a+b') as handle:
            try:
                if os.name == 'nt':
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except OSError:
                time.sleep(.05)
    raise RuntimeError('Configuration is still being changed; retry the operation.')


def main():
    wait_for_parent()
    import config
    import preset
    import browser
    action = sys.argv[1]
    preset.wymagaj_aktywnego(config, 'panel operation')
    if action in ('daily-draft', 'daily-publish', 'article-draft', 'article-publish'):
        if action.endswith('publish'):
            # Fail before paid work if the authenticated account is wrong.
            check_session(browser, False)
        if action.startswith('daily'):
            import run
            sys.argv = ['run.py', '--dzien'] + (['--wyslij'] if action.endswith('publish') else [])
            return run.main()
        import artykul_z_puli
        sys.argv = ['artykul_z_puli.py'] + (['--wyslij'] if action.endswith('publish') else [])
        return artykul_z_puli.main()
    import run
    # Read-only checks and session saving share the same instance lock as runs.
    # Keep the handle alive until this worker exits.
    global _instance_lock
    _instance_lock = run.zajmij_zamek()
    preset.wymagaj_aktywnego(config, 'panel operation')
    if action == 'login':
        if not browser.uruchom_chrome():
            raise RuntimeError('Could not open Chrome. See the installation guide for manual startup.')
        print('Chrome opened. Sign in manually, then use Verify and save session.')
    elif action in ('check', 'session'):
        errors, warnings = preset.sprawdz(config.PRESET, config, config.DOMYSLNE_SILNIKA, os.environ, do_aktywacji=True)
        for warning in warnings:
            print('INFO:', warning)
        if errors:
            raise RuntimeError('\n'.join(errors))
        import style
        style.load_profiles()
        style.przyklady_albo_pusto()
        print('PASS: preset, activation, style and instance paths.')
        check_session(browser, action == 'session')
        print('PASS: authenticated Substack account matches the configured account.')
        print('No paid model request was made. API key presence is not an API access test.')
    elif action == 'costs':
        import audyt_kosztow
        import json
        if not (config.DATA_DIR / 'agent-v2.db').exists():
            print('No cost or memory database yet. Run a workflow to create one.')
            return 0
        print(json.dumps(audyt_kosztow.collect(config.DATA_DIR), ensure_ascii=False, indent=2))
    elif action == 'dry':
        # Uses real loading/rendering without network, database writes or paid models.
        import style
        import stages
        print('Preset:', config.PRESET.nazwa, 'Instance:', config.INSTANCJA)
        print('Topic:', config.NISZA)
        print('Models:', config.MODEL_FOR)
        print('Style examples:', len(style.przyklady_albo_pusto()))
        fields = stages._pola_wspolne()
        print('Prompt blocks:', ', '.join(sorted(config.PRESET_BLOKI)))
        print('Rendered editorial direction:', fields.get('linia_redakcyjna', '')[:500])
        print('PASS: configuration preview. No model calls or publications.')
    return 0


def check_session(browser, save):
    if not browser._chrome_odpowiada():
        raise RuntimeError('Open the dedicated Chrome session and sign in first.')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        connection = runtime.chromium.connect_over_cdp('http://localhost:%s' % browser.CDP_PORT, timeout=20000)
        if not connection.contexts:
            raise RuntimeError('Chrome has no browser context.')
        context = connection.contexts[0]
        page = context.new_page()
        try:
            browser.wymagaj_wlasciwego_konta(page)
            if save:
                state = context.storage_state()
                import json
                import preset
                preset._zapisz_atomowo(browser.SESSION_FILE, json.dumps(state))
                os.chmod(browser.SESSION_FILE, 0o600)
                print('Session saved for the active instance.')
        finally:
            page.close()


if __name__ == '__main__':
    # A per-job lock and completion record survive closing/reopening the panel.
    import json
    import re
    job_id = os.environ.get('NIA_PANEL_JOB', '')
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise SystemExit('Start this worker from the NIA panel.')
    state = ROOT / 'agent-v2/data/panel'
    handle = (state / (job_id + '.lock')).open('a+b')
    if os.name == 'nt':
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        code = main() or 0
    except BaseException as exc:
        print('ERROR:', type(exc).__name__, str(exc), flush=True)
        code = 1
    finally:
        result = state / (job_id + '.result.json')
        temp = result.with_suffix('.tmp')
        temp.write_text(json.dumps({'exit_code': code}), encoding='utf-8')
        os.replace(temp, result)
        handle.close()
    raise SystemExit(code)

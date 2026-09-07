"""Task Scheduler entry point: load the active preset, verify account, log outcome."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import argparse
import sys
import traceback

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent-v2"))


def prepare_session(browser):
    """Reopen the existing browser profile; never automate login or payment."""
    if not browser._chrome_odpowiada() and not browser.uruchom_chrome():
        raise RuntimeError("Could not open the saved Chrome profile. Check the browser setup.")
    from panel_worker import check_session
    check_session(browser, False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("daily", "article"))
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    import config
    import preset
    preset.wymagaj_aktywnego(config, "scheduled run")
    if config.PRESET_AKTYWACJA.instancja != args.instance:
        raise RuntimeError("The scheduled instance is no longer active. Reinstall its schedule.")
    log = config.DATA_DIR / "logi" / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + args.kind + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8", buffering=1) as stream, redirect_stdout(stream), redirect_stderr(stream):
        try:
            # Explicit publication authorization lives in the installed task.
            # KILL_SWITCH and the normal activation/budget/account checks remain.
            config.DRY_RUN = False
            import browser
            prepare_session(browser)
            if args.kind == "daily":
                import run
                sys.argv = ["run.py", "--dzien", "--wyslij"]
                return run.main() or 0
            import artykul_z_puli
            sys.argv = ["artykul_z_puli.py", "--wyslij"]
            return artykul_z_puli.main() or 0
        except BaseException:
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())

"""Generate Task Scheduler XML from the active preset; --install registers it.

Runs as the current signed-in user, without storing a Windows password. The
computer must be awake and that user signed in. Linux uses jednostki.py instead.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent-v2"))
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
ET.register_namespace("", NS)


def task_xml(cfg, kind, python, root, sid, now=None):
    """UTC boundaries keep the configured UTC hours across daylight saving time."""
    now = now or datetime.now(timezone.utc)
    def add(parent, name, text=None, **attrs):
        node = ET.SubElement(parent, "{" + NS + "}" + name, attrs)
        if text is not None:
            node.text = str(text)
        return node
    task = ET.Element("{" + NS + "}Task", {"version": "1.2"})
    info = add(task, "RegistrationInfo")
    add(info, "Description", "NIA " + kind + " publishing for instance " + cfg.PRESET_AKTYWACJA.instancja)
    triggers = add(task, "Triggers")
    times = cfg.GODZINY_PRZEBIEGOW_UTC if kind == "daily" else (cfg.GODZINA_ARTYKULU_UTC,)
    if kind == "article" and not (cfg.ARTYKULY_TYGODNIOWO or cfg.ARTYKULY_MIESIECZNIE):
        return None
    for clock in times:
        trigger = add(triggers, "CalendarTrigger")
        boundary = datetime.fromisoformat(now.date().isoformat() + "T" + clock + ":00+00:00")
        if boundary <= now:
            boundary += timedelta(days=1)
        add(trigger, "StartBoundary", boundary.isoformat())
        add(trigger, "Enabled", "true")
        if kind == "daily":
            add(add(trigger, "ScheduleByDay"), "DaysInterval", "1")
        elif cfg.ARTYKULY_MIESIECZNIE:
            monthly = add(trigger, "ScheduleByMonth")
            days = add(monthly, "DaysOfMonth")
            for day in cfg.DNI_MIESIACA_ARTYKULU:
                add(days, "Day", day)
            months = add(monthly, "Months")
            for month in ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"):
                add(months, month)
        else:
            weekly = add(trigger, "ScheduleByWeek")
            add(weekly, "WeeksInterval", "1")
            days = add(weekly, "DaysOfWeek")
            names = dict(zip(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"), ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")))
            for day in cfg.DNI_ARTYKULU:
                add(days, names[day])
    principal = add(add(task, "Principals"), "Principal", id="Author")
    add(principal, "UserId", sid)
    add(principal, "LogonType", "InteractiveToken")
    add(principal, "RunLevel", "LeastPrivilege")
    settings = add(task, "Settings")
    add(settings, "MultipleInstancesPolicy", "IgnoreNew")
    add(settings, "DisallowStartIfOnBatteries", "false")
    add(settings, "StopIfGoingOnBatteries", "false")
    add(settings, "StartWhenAvailable", "false")
    add(settings, "ExecutionTimeLimit", "PT3H")
    add(settings, "Enabled", "true")
    action = add(add(task, "Actions", Context="Author"), "Exec")
    add(action, "Command", python)
    add(action, "Arguments", subprocess.list2cmdline([str(root / "narzedzia/scheduled_run.py"), kind, "--instance", cfg.PRESET_AKTYWACJA.instancja]))
    add(action, "WorkingDirectory", root)
    # Task Scheduler imports Unicode XML; declaration and file bytes must agree.
    return '<?xml version="1.0" encoding="UTF-16"?>\n' + ET.tostring(task, encoding="unicode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Enable autonomous publishing for the active instance")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows only; use narzedzia/jednostki.py on Linux")
    import config
    import preset
    preset.wymagaj_aktywnego(config, "install schedule")
    sid = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"], text=True).strip()
    folder = config.DATA_DIR / "schedule"
    folder.mkdir(parents=True, exist_ok=True)
    for kind in ("daily", "article"):
        name = "NIA-" + config.PRESET_AKTYWACJA.instancja + "-" + kind
        xml = task_xml(config, kind, sys.executable, ROOT, sid)
        if xml is None:
            # Remove a previously generated article task when articles are disabled.
            if args.install and subprocess.run(["schtasks.exe", "/Query", "/TN", name], capture_output=True).returncode == 0:
                subprocess.run(["schtasks.exe", "/Delete", "/TN", name, "/F"], check=True)
            continue
        path = folder / (kind + ".xml")
        path.write_text(xml, encoding="utf-16")
        print(path)
        if args.install:
            subprocess.run(["schtasks.exe", "/Create", "/TN", name, "/XML", str(path), "/F"], check=True)
    print("Installed." if args.install else "Review XML, then add --install to enable publishing.")


if __name__ == "__main__":
    main()

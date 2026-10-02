"""The task generated from a preset keeps UTC boundaries; the article task runs daily.

Since 2026-09-30 the article script decides the day (a plan day, or catching up a
plan day whose article did not come out), so the article trigger is daily for
monthly and weekly plans alike, and absent when the plan has no articles.
"""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "narzedzia"))
from schedule_windows import task_xml, NS
from scheduled_run import prepare_session


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.cfg = SimpleNamespace(PRESET_AKTYWACJA=SimpleNamespace(instancja="example"),
            GODZINY_PRZEBIEGOW_UTC=("13:30", "20:30"), GODZINA_ARTYKULU_UTC="17:00",
            ARTYKULY_TYGODNIOWO=0, ARTYKULY_MIESIECZNIE=2, DNI_MIESIACA_ARTYKULU=(8,22), DNI_ARTYKULU=())
        self.now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)

    def xml(self, kind):
        return ET.fromstring(task_xml(self.cfg, kind, "C:/Program Files/Python/python.exe", Path("C:/NIA app"), "S-1-5-example", self.now))

    def test_monthly_article_task_runs_daily_and_daily_stays_daily(self):
        article = self.xml("article")
        self.assertEqual(article.find(".//{%s}ScheduleByDay/{%s}DaysInterval" % (NS, NS)).text, "1")
        self.assertEqual(article.findall(".//{%s}Day" % NS), [])
        self.assertEqual(len(article.findall(".//{%s}CalendarTrigger" % NS)), 1)
        self.assertEqual(article.find(".//{%s}StartBoundary" % NS).text, "2026-09-07T17:00:00+00:00")
        daily = self.xml("daily")
        self.assertEqual(len(daily.findall(".//{%s}CalendarTrigger" % NS)), 2)
        self.assertIn('"C:', daily.find(".//{%s}Arguments" % NS).text)
        self.assertEqual(daily.find(".//{%s}LogonType" % NS).text, "InteractiveToken")

    def test_weekly_and_disabled(self):
        self.cfg.ARTYKULY_MIESIECZNIE = 0
        self.assertIsNone(task_xml(self.cfg, "article", "python", ROOT, "sid"))
        self.cfg.ARTYKULY_TYGODNIOWO = 1
        self.cfg.DNI_ARTYKULU = ("Tue",)
        weekly = self.xml("article")
        self.assertIsNone(weekly.find(".//{%s}Tuesday" % NS))
        self.assertEqual(weekly.find(".//{%s}ScheduleByDay/{%s}DaysInterval" % (NS, NS)).text, "1")

    def test_task_xml_declares_its_windows_unicode_encoding(self):
        xml = task_xml(self.cfg, "daily", "python", ROOT, "sid", self.now)
        self.assertIn('encoding="UTF-16"', xml.splitlines()[0])
        self.assertEqual(ET.fromstring(xml.encode("utf-16")).tag, "{%s}Task" % NS)

    def test_scheduled_start_opens_profile_then_checks_identity(self):
        browser = Mock()
        browser._chrome_odpowiada.return_value = False
        browser.uruchom_chrome.return_value = True
        with patch("panel_worker.check_session") as check:
            prepare_session(browser)
            browser.uruchom_chrome.assert_called_once()
            check.assert_called_once_with(browser, False)
        browser.uruchom_chrome.return_value = False
        with patch("panel_worker.check_session") as check:
            with self.assertRaises(RuntimeError):
                prepare_session(browser)
            check.assert_not_called()


if __name__ == "__main__":
    unittest.main()

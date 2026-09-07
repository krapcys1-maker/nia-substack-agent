"""The task generated from a preset uses real monthly days and UTC boundaries."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "narzedzia"))
from schedule_windows import task_xml, NS


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.cfg = SimpleNamespace(PRESET_AKTYWACJA=SimpleNamespace(instancja="example"),
            GODZINY_PRZEBIEGOW_UTC=("13:30", "20:30"), GODZINA_ARTYKULU_UTC="17:00",
            ARTYKULY_TYGODNIOWO=0, ARTYKULY_MIESIECZNIE=2, DNI_MIESIACA_ARTYKULU=(8,22), DNI_ARTYKULU=())
        self.now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)

    def xml(self, kind):
        return ET.fromstring(task_xml(self.cfg, kind, "C:/Program Files/Python/python.exe", Path("C:/NIA app"), "S-1-5-example", self.now))

    def test_monthly_and_daily_do_not_become_weekly(self):
        article = self.xml("article")
        self.assertEqual([n.text for n in article.findall(".//{%s}Day" % NS)], ["8", "22"])
        self.assertEqual(len(article.findall(".//{%s}Months/*" % NS)), 12)
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
        self.assertIsNotNone(self.xml("article").find(".//{%s}Tuesday" % NS))


if __name__ == "__main__":
    unittest.main()

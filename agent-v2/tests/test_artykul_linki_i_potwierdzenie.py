"""Article source links and the optional final publish dialog; no network."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import browser


class ArticlePublishing(unittest.TestCase):
    def test_inline_and_source_list_links_survive_rendering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "article.md"
            path.write_text('# Headline\n\n*Subtitle*\n\nRead the [source & details](https://example.org/a?x=1&y=2) here.\n\n'
                            '*AI illustration.*\n\n## Sources\n\n- [Official report](https://example.org/report)\n', encoding="utf-8")
            result = browser.rozbierz_artykul(path)
        self.assertEqual(result["podtytul"], "Subtitle")
        self.assertIn('<a href="https://example.org/a?x=1&amp;y=2">source &amp; details</a>', result["html"])
        self.assertIn('<li><a href="https://example.org/report">Official report</a></li>', result["html"])
        self.assertIn('<em>AI illustration.</em>', result["html"])

    def test_raw_html_and_non_web_link_are_never_executable(self):
        result = browser._html_z_linkami('<img src=x onerror=alert(1)> [bad](javascript:alert)')
        self.assertNotIn('<img', result)
        self.assertNotIn('href=', result)

    def test_known_final_prompt_is_confirmed_once(self):
        button = Mock()
        button.count.return_value = 1
        button.is_visible.return_value = True
        page = Mock()
        page.get_by_role.return_value = button
        self.assertTrue(browser._domknij_publikacje_artykulu(page))
        page.get_by_role.assert_called_once_with('button', name='Publish without buttons', exact=True)
        button.click.assert_called_once()

    def test_no_optional_prompt_does_not_click_again(self):
        button = Mock()
        button.count.return_value = 0
        page = Mock()
        page.get_by_role.return_value = button
        self.assertFalse(browser._domknij_publikacje_artykulu(page))
        button.click.assert_not_called()

    def test_delayed_publication_retries_reads_without_leaving_editor(self):
        page = Mock()
        control = page.context.new_page.return_value
        with patch.object(browser, '_domknij_publikacje_artykulu') as finish, \
                patch.object(browser, 'potwierdz_artykul', side_effect=[False, True]) as verify:
            self.assertTrue(browser._potwierdz_wysylke_artykulu(page, 'Headline'))
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(finish.call_count, 2)
        for call in verify.call_args_list:
            self.assertIs(call.args[0], control)
        page.goto.assert_not_called()
        page.get_by_role.assert_not_called()
        control.close.assert_called_once()

    def test_failed_read_can_recover_and_failure_is_bounded(self):
        for answers, expected, attempts in (([TimeoutError(), True], True, 2),
                                             ([False, False, False], False, 3)):
            with self.subTest(answers=answers):
                page = Mock()
                with patch.object(browser, '_domknij_publikacje_artykulu'), \
                        patch.object(browser, 'potwierdz_artykul', side_effect=answers) as verify:
                    self.assertEqual(browser._potwierdz_wysylke_artykulu(page, 'Headline'), expected)
                self.assertEqual(verify.call_count, attempts)
                page.context.new_page.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()

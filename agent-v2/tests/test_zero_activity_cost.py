"""Execute the real daily blocks: zero slots must not fetch or rank targets."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'run.py'


def block(name, slots, **values):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    daily = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'dzien')
    function = copy.deepcopy(next(n for n in daily.body if isinstance(n, ast.FunctionDef) and n.name == name))
    function.decorator_list = []  # Strip accounting context, retain the complete production body.
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = {'na_teraz': slots, **values}
    exec(compile(module, str(SOURCE), 'exec'), namespace)
    return namespace[name]


class NoUnusedWork(unittest.TestCase):
    def test_disabled_or_exhausted_comments_do_no_network_or_model_work(self):
        network = Mock(side_effect=AssertionError('unnecessary network request'))
        model = Mock(side_effect=AssertionError('unnecessary paid ranking'))
        for slots in (0, -1):
            block('komentarze', {'komentarze': slots},
                  kanal=SimpleNamespace(szukaj_nowych=network, posty_z_kanalu=network),
                  stages=SimpleNamespace(wybierz_cele=model))()
        network.assert_not_called()
        model.assert_not_called()

    def test_positive_comment_allocation_still_reaches_discovery(self):
        network = Mock(side_effect=RuntimeError('discovery reached'))
        with self.assertRaisesRegex(RuntimeError, 'discovery reached'):
            block('komentarze', {'komentarze': 1}, kanal=SimpleNamespace(szukaj_nowych=network))()
        network.assert_called_once()

    def test_likes_zero_skips_browser_but_positive_allocation_runs(self):
        send = Mock(return_value={'polubione': 1})
        result = {}
        for count in (0, 1):
            block('polubienia', {'lajki': count}, browser=SimpleNamespace(polub_w_kanale=send),
                  wyslij=False, zrobione=result)()
        send.assert_called_once_with(1, wyslij=False)
        self.assertEqual(result['polubienia'], 1)


if __name__ == '__main__':
    unittest.main()

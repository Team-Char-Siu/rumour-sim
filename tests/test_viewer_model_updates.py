"""Restoration regressions without opening a graphics context."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace
from main import makeSettings,parseArgs,settingsFromArgs
class RestorationTests(unittest.TestCase):
    def test_original_layout_defaults(self):
        p = makeSettings(500)
        self.assertEqual((p['groupSpread'],p['leash']),(33,15))
        self.assertEqual((p['correctionStrength'],p['correctionDuration'],p['correctionRadius']),(.03,50,4))
    def test_cli_matches_defaults(self):
        self.assertEqual(settingsFromArgs(parseArgs([])),makeSettings(500))
    def test_radius_scales_as_original(self):
        p = makeSettings(100)
        self.assertEqual(p['correctionRadius'],p['contactRadius'])
    def test_controls_effects_and_font_restored(self):
        tree = ast.parse((Path(__file__).resolve().parents[1]/'viewer_arcade.py').read_text())
        functions = {n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
        self.assertTrue({'drawArrow','traceChain','drawChartHover','drawPanel'} <= functions)
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertTrue({'treeMode','genMode','follow','rings','glowList','pulses','log','top'} <= attrs)
        body = [n for n in tree.body if isinstance(n,ast.Assign) or isinstance(n,ast.FunctionDef) and n.name == 'nodeColour']
        ns = dict(BOX=100,STIFLER=3)
        exec(compile(ast.Module(body=body,type_ignores=[]),'styles','exec'),ns)
        self.assertEqual(ns['FONT'][0],'Consolas')
        self.assertEqual((ns['SIDE'],ns['CHART_HEIGHT']),(440,220))
        a = SimpleNamespace(isFriend=False,isSubject=False,wasFriend=True,state=3)
        self.assertEqual(ns['nodeColour'](a),ns['EX_FRIEND_COL'])
        a.wasFriend = False
        self.assertEqual(ns['nodeColour'](a,1),ns['SPREAD_COL'])
    def test_invalid_settings(self):
        with self.assertRaises(ValueError):
            makeSettings(0)

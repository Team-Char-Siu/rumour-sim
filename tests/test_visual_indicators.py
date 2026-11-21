"""Pure styling and mocked-draw tests; no Arcade window required."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from viewer_effects import showsAvoidance,drawThinArrow

class VisualIndicatorTests(unittest.TestCase):
    def test_only_actual_avoiders_have_ring(self):
        for avoiding,subject,expected in [(True,False,True),(False,False,False),(True,True,False)]:
            a = SimpleNamespace(avoiding=avoiding,isSubject=subject)
            self.assertEqual(showsAvoidance(a),expected)
    def test_ring_does_not_change_agent(self):
        a = SimpleNamespace(avoiding=True,isSubject=False,believed=True,state=3)
        before = vars(a).copy()
        self.assertTrue(showsAvoidance(a))
        self.assertEqual(vars(a),before)
    def test_ring_disappears_after_correction(self):
        a = SimpleNamespace(avoiding=True,isSubject=False)
        a.avoiding = False
        self.assertFalse(showsAvoidance(a))
    def test_thin_transmission_arrow(self):
        mock = Mock()
        with patch.dict(sys.modules,arcade=mock):
            drawThinArrow((0,0),(100,0),(255,77,77,200),3)
        args = mock.draw_line.call_args.args
        self.assertEqual(args[-1],1.)
        self.assertEqual(args[-2][-1],130)
        self.assertEqual(args[:4],(6.,0.,94.,0.))
        mock.draw_triangle_filled.assert_called_once()
    def test_gold_chain_is_slightly_stronger(self):
        mock = Mock()
        with patch.dict(sys.modules,arcade=mock):
            drawThinArrow((0,0),(100,0),(255,214,10),3)
        self.assertEqual(mock.draw_line.call_args.args[-1],1.5)
    def test_zero_length_arrow_is_safe(self):
        mock = Mock()
        with patch.dict(sys.modules,arcade=mock):
            drawThinArrow((1,1),(1,1),(255,77,77),3)
        mock.draw_line.assert_not_called()
        mock.draw_triangle_filled.assert_not_called()

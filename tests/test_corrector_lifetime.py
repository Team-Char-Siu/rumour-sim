"""Finite correction activity supersedes the earlier permanence tests."""
import unittest
from agent import Agent,UNAWARE,CORRECTOR,STIFLER
class LifetimeTests(unittest.TestCase):
    def test_configurable_finite_duration(self):
        a = Agent(50,50,UNAWARE,1,0)
        a.correctionDuration = 110
        a.becomeCorrector()
        for _ in range(109):
            a.tick()
        self.assertEqual(a.state,CORRECTOR)
        a.tick()
        self.assertEqual(a.state,STIFLER)
        self.assertFalse(a.believed)

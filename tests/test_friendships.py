"""Run: python -m unittest discover -s tests -v"""
import contextlib
import io
import math
from pathlib import Path
import subprocess
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent import Agent, UNAWARE, SPREADER, CORRECTOR, STIFLER
from movement import safeMove, segmentDistance
from simulation import makeAgents, seedSpreaders, pickSubject, rollSpread, runSimulation
import main


class ModelTests(unittest.TestCase):
    def agent(self):
        return Agent(50, 50, UNAWARE, 1, 0)

    def test_loyal_friend_can_spread(self):
        a = self.agent(); a.isFriend = a.wasFriend = True; a.loyalty = 1
        a.becomeSpreader(0, 1, 2)
        self.assertEqual(a.state, SPREADER)
        self.assertTrue(a.isFriend)
        self.assertFalse(a.avoiding)

    def test_breakup_forces_exit_and_keeps_group(self):
        a = self.agent(); a.isFriend = a.wasFriend = a.linger = True; a.loyalty = 0
        a.becomeSpreader(0, 1, 2)
        self.assertFalse(a.isFriend or a.linger)
        self.assertTrue(a.avoiding)
        self.assertEqual((a.friendshipEndedAt, a.group), (2, 0))

    def test_one_time_avoidance(self):
        a = self.agent(); a.avoidChance = 0; a.becomeSpreader()
        a.avoidChance = 1; a.acceptBelief(9)
        self.assertFalse(a.avoiding)

    def test_correction_does_not_repair_friendship(self):
        a = self.agent(); a.isFriend = a.wasFriend = True; a.loyalty = 0
        a.becomeSpreader(); a.becomeCorrector()
        self.assertFalse(a.avoiding or a.isFriend or a.believed)

    def test_silent_believer(self):
        a = self.agent(); a.becomeSilentBeliever(0, 1, 2)
        self.assertTrue(a.believed)
        self.assertFalse(a.ignored)
        self.assertEqual(a.state, STIFLER)

    def test_timer_keeps_belief(self):
        a = self.agent(); a.avoidChance = 1; a.becomeSpreader(); a.counter = 1; a.tick()
        self.assertEqual(a.state, STIFLER)
        self.assertTrue(a.believed and a.avoiding)

    def test_openness_extremes(self):
        source = self.agent(); source.becomeCorrector()
        for openness in (0, 1):
            a = self.agent(); a.x = 51; a.openness = openness
            rollSpread([source, a], 0, 4, 1, 1)
            self.assertEqual(a.state, CORRECTOR if openness else UNAWARE)

    def test_silent_believer_can_accept_correction(self):
        source = self.agent(); source.becomeCorrector()
        a = self.agent(); a.becomeSilentBeliever(2, 1, 0); a.openness = 1
        rollSpread([source, a], 1, 4, 0, 1)
        self.assertEqual(a.state, CORRECTOR)
        self.assertFalse(a.avoiding)

    def test_sharing_extremes(self):
        source = self.agent(); source.becomeSpreader()
        for sharing in (0, 1):
            a = self.agent(); a.x = 51; a.sharingTendency = sharing
            rollSpread([source, a], 0, 4, 1, 0, 0)
            self.assertTrue(a.believed)
            self.assertEqual(a.state, SPREADER if sharing else STIFLER)

    def test_route_goes_around_not_through(self):
        point = (40, 50); centre = (50, 50)
        for _ in range(45):
            delta = np.array([60., 50.]) - point
            delta *= min(1., 2 / max(np.linalg.norm(delta), 1e-12))
            result = safeMove(point, np.array(point) + delta, centre, 7)
            self.assertGreaterEqual(segmentDistance(point, result, centre), 7 - 1e-9)
            point = result
        self.assertLess(math.dist(point, (60, 50)), 1)

    def test_overlap_evacuates(self):
        result = safeMove((50, 50), (51, 50), (50, 50), 7)
        self.assertGreaterEqual(math.dist(result, (50, 50)), 7)

    def test_1500_boundary_cases(self):
        rng = np.random.default_rng(9)
        for _ in range(1500):
            centre, start, goal = rng.uniform(0, 100, (3, 2))
            result = safeMove(start, goal, centre, 7)
            self.assertTrue(all(0 <= x <= 100 for x in result))
            self.assertGreaterEqual(math.dist(result, centre), 7 - 1e-9)
            if math.dist(start, centre) >= 7 + 1e-6:
                self.assertGreaterEqual(segmentDistance(start, result, centre), 7 - 1e-9)

    def test_friends_preserve_group_membership(self):
        agents = makeAgents(120, 42, .2, 15); seedSpreaders(agents, 1, 0)
        groups = [a.group for a in agents]; pickSubject(agents, 3)
        self.assertEqual(groups, [a.group for a in agents])
        self.assertEqual(sum(a.wasFriend for a in agents), 12)
        self.assertEqual(sum(a.linger for a in agents), 4)

    def test_repeatable_population_conservation(self):
        outputs = []
        for _ in range(2):
            settings = main.makeSettings(100)
            agents = main.buildAgents(100, 42, settings)
            counts, groups, near = runSimulation(agents, 100, settings)
            self.assertTrue(np.all(counts.sum(axis=1) == 100))
            outputs.append(([(a.x, a.y, a.state, a.isFriend, a.believed) for a in agents], counts.tolist()))
        self.assertEqual(outputs[0], outputs[1])


class EntryTests(unittest.TestCase):
    def test_import_is_safe(self):
        code = "import builtins,sys; builtins.input=lambda *a: (_ for _ in ()).throw(AssertionError('prompt')); import main; assert 'arcade' not in sys.modules; assert 'simulation' not in sys.modules"
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_cli(self):
        for arguments in (['--n=0'], ['--n=-1'], ['--steps=0'], ['--seed=-1'], ['--seed=4294967296']):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main.parseArgs(arguments)

    def test_settings_validation(self):
        for n in (0, -1, True, 2.5):
            with self.assertRaises(ValueError):
                main.makeSettings(n)

    def test_cli_defaults_and_overrides(self):
        self.assertEqual(main.parseArgs([]).n, 500)
        args = main.parseArgs(['test', '--n=200', '--steps=10', '--headless'])
        self.assertEqual((args.n, args.steps, args.headless), (200, 10, True))


if __name__ == '__main__':
    unittest.main()

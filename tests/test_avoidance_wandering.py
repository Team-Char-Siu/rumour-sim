"""Avoiders should not be attracted to a ring around the subject"""
import unittest
from unittest.mock import patch

import numpy as np

from agent import Agent, UNAWARE
from movement import GROUP_CENTRES, moveAgents


class AvoidanceWanderingTests(unittest.TestCase):
    def test_safe_move_away_from_subject_is_not_pulled_back(self):
        centreX, centreY = GROUP_CENTRES[0]

        subject = Agent(
            centreX,
            centreY,
            UNAWARE,
            0.5,
            0,
        )
        subject.isSubject = True

        agent = Agent(
            centreX + 11,
            centreY,
            UNAWARE,
            0.5,
            0,
        )
        agent.avoiding = True

        # - keep normal movement still to isolate avoidance logic
        # - propose a safe step further into the group
        with patch("movement.moveAgent"):
            with patch(
                "movement.np.random.uniform",
                side_effect=[1.0, 0.0],
            ):
                moveAgents(
                    [subject, agent],
                    stepSize=1.5,
                    travelChance=0,
                    travelSpeed=2,
                    leash=15,
                    stayLength=40,
                    subject=subject,
                    avoidRadius=7,
                    avoidVisualBuffer=1.15,
                )

        np.testing.assert_allclose(
            (agent.x, agent.y),
            (centreX + 12.5, centreY),
        )


if __name__ == "__main__":
    unittest.main()
"""Friendship and avoidance overlay for the viewer"""
import math

import arcade

import viewer_arcade as base
from agent import SPREADER, CORRECTOR, NO_GROUP
from movement import safeMove
from simulation import transmissionStats
from viewer_effects import (
    drawThinArrow,
    showsAvoidance,
    AVOID_RING_COL,
    AVOID_RING_WIDTH,
    AVOID_RING_GAP,
)

EX_FRIEND_COL = base.EX_FRIEND_COL


def diamondPoints(x, y, radius):
    """Make four points for no group diamond"""
    tip = radius * 1.5
    side = radius * 0.75

    return [
        (x, y + tip),
        (x + side, y),
        (x, y - tip),
        (x - side, y),
    ]


class FriendshipWindow(base.RumourWindow):
    """Viewer with friendships and avoidance"""

    def __init__(self, build, steps, p, rumour):
        base.drawArrow = drawThinArrow
        base.DOT_IDLE = 3.25
        base.DOT_ACTIVE = 5.75
        base.DOT_HOP = 4.75

        super().__init__(build, steps, p, rumour)

    def newRun(self):
        """Start new viewer run"""
        super().newRun()

        for agent, dot in zip(self.agents, self.dots):
            if agent.group == NO_GROUP:
                dot.alpha = 0

    def on_update(self, delta_time):
        """Update viewer each frame"""
        previous = self.shown.copy()
        super().on_update(delta_time)

        subject = next(
            (
                i for i, agent in enumerate(self.agents)
                if agent.isSubject
            ),
            None,
        )

        if subject is not None and self.intro >= base.INTRO_HOLD + base.INTRO_GLIDE:
            centre = self.shown[subject].copy()

            for i, agent in enumerate(self.agents):
                if agent.avoiding:
                    self.shown[i] = safeMove(
                        previous[i],
                        self.shown[i],
                        centre,
                        self.p.get("avoidRadius", 7),
                        agent.routeSide,
                    )

                self.dots[i].position = self.toScreen(self.shown[i])
                self.glows[i].position = self.dots[i].position

        for i, agent in enumerate(self.agents):
            if agent.isFriend or agent.wasFriend or agent.isSubject:
                self.dots[i].color = base.rgba(
                    base.nodeColour(agent, self.told[i]),
                    255,
                )
                self.dotStyle[i] = None

            if agent.group == NO_GROUP:
                # draw pointed polygon instead of rotated square sprite
                self.dots[i].alpha = 0

    def on_draw(self):
        """Draw friendship and avoidance overlay"""
        super().on_draw()

        for i, agent in enumerate(self.agents):
            x, y = self.toScreen(self.shown[i])
            active = agent.state in (SPREADER, CORRECTOR)

            if self.genMode and agent.generation >= 0:
                radius = base.DOT_HOP
            elif active:
                radius = base.DOT_ACTIVE
            else:
                radius = base.DOT_IDLE

            if self.spreadMode and self.told[i]:
                radius = max(
                    radius,
                    min(
                        base.SPREAD_MAX,
                        base.SPREAD_BASE
                        + base.SPREAD_GROW * math.sqrt(self.told[i]),
                    ),
                )

            extent = radius

            if agent.group == NO_GROUP:
                colour = (*self.dots[i].color[:3], 255)
                points = diamondPoints(x, y, radius)

                arcade.draw_polygon_filled(points, colour)
                arcade.draw_polygon_outline(points, colour, 1.0)

                extent = radius * 1.5

            if (agent.isFriend or agent.wasFriend) and active:
                arcade.draw_circle_outline(
                    x,
                    y,
                    extent + 2,
                    base.STATE_COL[agent.state],
                    2,
                )

            if showsAvoidance(agent):
                arcade.draw_circle_outline(
                    x,
                    y,
                    extent + AVOID_RING_GAP,
                    AVOID_RING_COL,
                    AVOID_RING_WIDTH,
                )

        stats = transmissionStats(self.agents)

        self.label(
            "friendsOverlay",
            "Friends: %d   Lost: %d   Silent/stopped believers: %d"
            % (
                stats["friends"],
                stats["lostFriends"],
                stats["silentBelievers"],
            ),
            12,
            10,
            base.SUBJECT_COL,
            10,
        )

        self.label(
            "avoidanceLegend",
            "Red outer ring = avoiding the subject",
            12,
            26,
            AVOID_RING_COL[:3],
            10,
        )

        self.label(
            "shapeLegend",
            "Circle = home group; diamond = no group",
            12,
            42,
            base.DIM,
            10,
        )


def runViewer(build, steps, p, rumour):
    """Run friendship viewer"""
    window = FriendshipWindow(build, steps, p, rumour)
    arcade.run()

    return window.agents, window.history

"""Original Team Char Siu Arcade viewer, restored from b4e128e.

Distance-model attribution: Le Nguyen, Simulation 102 (README ref 1).
Targeted additions: chart height/hover and clearer unaware/inactive colours.
"""
import math

import numpy as np
import arcade

from agent import UNAWARE, SPREADER, CORRECTOR, STIFLER, NO_GROUP
from movement import BOX, GROUP_CENTRES, GROUP_NAMES
from simulation import (
    stepSimulation,
    countStates,
    transmissionStats,
    nearSubject,
)

SIM = 700
SIDE = 440
SCALE = SIM / BOX
TICKS_PER_SECOND = 30
SMOOTH_RATE = 14
ARROW_LIFE = 5.0
PULSE_LIFE = 1.0
MAX_ARROWS = 30
MAX_PULSES = 10
FONT = ('Consolas', 'Menlo', 'DejaVu Sans Mono', 'Courier New')
INTRO_HOLD = 3.0
INTRO_GLIDE = 2.0
INTRO_GAP = 5
GLOW_RADIUS = 11
GLOW_ALPHA = 120
DOT_ACTIVE = 5
DOT_IDLE = 2.5
DOT_HOP = 4
PULSE_SIZE = 18
SPREAD_BASE = 3
SPREAD_GROW = 3
SPREAD_MAX = 16
CHART_HEIGHT = 220

# viewer colours
BG = (11, 16, 32)
PANEL = (17, 24, 46)
TEXT = (210, 218, 235)
DIM = (120, 130, 155)
GOLD = (255, 214, 10)
WHITE = (255, 255, 255)
IGNORED_COL = (150, 160, 185)
SUBJECT_COL = (255, 105, 180)
SPREAD_COL = (255, 159, 10)
EX_FRIEND_COL = (167, 139, 250)

STATE_COL = [
    (210, 220, 235),
    (255, 77, 77),
    (46, 214, 170),
    (108, 118, 138),
]
LINE_COL = [
    (210, 220, 235),
    (255, 77, 77),
    (46, 214, 170),
    (145, 155, 175),
]
STATE_NAMES = ['Unaware', 'Spreader', 'Corrector', 'Stifler']
STATE_HELP = [
    "hasn't heard it",
    'telling others',
    'spreading the correction',
    'heard it, stopped passing it on',
]
GROUP_COL = [
    (244, 162, 97),
    (67, 97, 238),
    (157, 78, 221),
    (141, 110, 99),
]
GEN_COL = [
    (255, 214, 10),
    (255, 159, 10),
    (255, 99, 71),
    (236, 72, 153),
    (168, 85, 247),
    (99, 102, 241),
    (56, 189, 248),
    (45, 212, 191),
]
SPEEDS = [0.25, 0.5, 1, 2, 4, 8]


def rgba(colour, alpha):
    """Make colour with alpha"""
    return (colour[0], colour[1], colour[2], alpha)


def wrap(text, width):
    """Wrap text into lines"""
    words = text.split()
    lines = []
    line = ''

    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()

    lines.append(line)
    return lines


def drawArrow(start, end, colour, width):
    """Draw arrow between two points"""
    arcade.draw_line(
        start[0],
        start[1],
        end[0],
        end[1],
        colour,
        width,
    )

    angle = math.atan2(
        end[1] - start[1],
        end[0] - start[0],
    )
    size = 9

    leftX = end[0] - size * math.cos(angle - 0.45)
    leftY = end[1] - size * math.sin(angle - 0.45)
    rightX = end[0] - size * math.cos(angle + 0.45)
    rightY = end[1] - size * math.sin(angle + 0.45)

    arcade.draw_triangle_filled(
        end[0],
        end[1],
        leftX,
        leftY,
        rightX,
        rightY,
        colour,
    )


def traceChain(agents, index):
    """Trace chain of tellers"""
    chain = []
    seen = set()

    while 0 <= index < len(agents) and index not in seen:
        seen.add(index)
        chain.append(index)
        index = agents[index].infector

    return chain[::-1]


def nodeColour(agent, told=0):
    """Choose colour for agent dot"""
    if agent.isFriend or agent.isSubject:
        return SUBJECT_COL

    if agent.wasFriend:
        return EX_FRIEND_COL

    if agent.state == STIFLER and told:
        return SPREAD_COL

    return STATE_COL[agent.state]


def describe(agents, index, p):
    """Make description lines for agent"""
    agent = agents[index]

    if agent.group == NO_GROUP:
        group = 'no group'
    else:
        group = 'group ' + GROUP_NAMES[agent.group]

    lines = [
        '#' + str(index) + '  ' + STATE_NAMES[agent.state] + ', ' + group
    ]

    if agent.isSubject:
        lines.append('the rumour is about this agent')

    if agent.isFriend:
        if agent.linger:
            lines.append('friend of subject; lingers nearby')
        else:
            lines.append('friend of subject')
    elif agent.wasFriend:
        lines.append(
            'former friend; ended at step ' + str(agent.friendshipEndedAt)
        )

    if agent.generation >= 0:
        if agent.infector < 0:
            lines.append('hop ' + str(agent.generation) + ', started it')
        else:
            lines.append(
                'hop ' + str(agent.generation)
                + ', told by #' + str(agent.infector)
            )

        if agent.ignored:
            lines.append('explicitly rejected the rumour')
    elif agent.isSubject and agent.heardAt is not None:
        lines.append('noticed avoidance; no direct rumour teller')
    else:
        lines.append('has not had the rumour')

    if agent.believed:
        if agent.avoiding:
            lines.append('believes it; avoids subject')
        else:
            lines.append('believes it; does not avoid')

    if agent.corrGeneration >= 0:
        if agent.corrSource < 0:
            lines.append('started correction')
        else:
            lines.append('correction from #' + str(agent.corrSource))

    lines.append(
        'gullibility %.2f; openness %.2f'
        % (agent.gullibility, agent.openness)
    )
    lines.append(
        'loyalty %.2f; sharing tendency %.2f'
        % (agent.loyalty, agent.sharingTendency)
    )

    minInterest = p.get('minInterest', 0.5)
    chance = minInterest + (1 - minInterest) * agent.sharingTendency
    lines.append(
        'chance to share if accepted: %d%%' % round(100 * chance)
    )

    return lines


class RumourWindow(arcade.Window):
    """Main Arcade viewer window"""

    def __init__(self, build, steps, p, rumour):
        super().__init__(
            SIM + SIDE,
            SIM,
            'Team Char Siu - Rumour Spread',
            vsync=True,
            antialiasing=True,
        )
        self.background_color = BG

        self.build = build
        self.steps = steps
        self.p = p
        self.rumour = rumour

        self.texts = {}
        self.speedIdx = 1
        self.paused = False
        self.treeMode = False
        self.genMode = False
        self.spreadMode = True
        self.follow = True
        self.rings = False
        self.effects = False
        self.mousePos = (-1000, -1000)
        self.now = 0.0

        self.newRun()

    def newRun(self):
        """Start new simulation run"""
        self.agents = self.build()
        count = len(self.agents)

        self.zeros = [
            index for index in range(count)
            if self.agents[index].state == SPREADER
        ]
        self.real = np.zeros((count, 2), dtype=float)
        self.shown = self.realPositions()
        self.real = self.shown.copy()
        self.history = []
        self.arrows = []
        self.pulses = []
        self.log = []
        self.latest = -1
        self.told = [0] * count
        self.top = []
        self.near = nearSubject(
            self.agents,
            self.p.get('nearRadius', 10),
        )
        self.near0 = self.near[0]
        self.t = 0
        self.counts = countStates(self.agents)
        self.stats = transmissionStats(self.agents)
        self.acc = 0.0
        self.selected = None
        self.intro = 0.0

        # place patient zero and subject for intro
        middle = BOX / 2
        self.introPos = {}

        for position, index in enumerate(self.zeros):
            self.introPos[index] = (
                middle - INTRO_GAP - 2 * position,
                middle,
            )

        for index in range(count):
            if self.agents[index].isSubject:
                self.introPos[index] = (middle + INTRO_GAP, middle)

        for index, position in self.introPos.items():
            self.shown[index] = position

        self.glowList = arcade.SpriteList()
        self.dotList = arcade.SpriteList()
        self.glows = []
        self.dots = []
        self.dotStyle = [None] * count
        self.glowStyle = [None] * count

        for agent in self.agents:
            glow = arcade.SpriteCircle(
                GLOW_RADIUS,
                (255, 255, 255, 255),
                soft=True,
            )
            glow.color = (255, 255, 255, 0)
            self.glowList.append(glow)
            self.glows.append(glow)

            if agent.group == NO_GROUP:
                dot = arcade.SpriteSolidColor(
                    10,
                    10,
                    color=(255, 255, 255, 255),
                )
                dot.angle = 45
            else:
                dot = arcade.SpriteCircle(
                    8,
                    (255, 255, 255, 255),
                )

            self.dotList.append(dot)
            self.dots.append(dot)

    def realPositions(self):
        """Upd and return reusable agent pos array"""
        for index, agent in enumerate(self.agents):
            self.real[index, 0] = agent.x
            self.real[index, 1] = agent.y

        return self.real

    def toScreen(self, position):
        """Convert simulation position to screen position"""
        return position[0] * SCALE, position[1] * SCALE

    def nearestAgent(self, mouse, maxDist):
        """Find nearest agent to mouse"""
        best = None
        bestDist = maxDist

        for index in range(len(self.agents)):
            screenX, screenY = self.toScreen(self.shown[index])
            distance = math.hypot(
                screenX - mouse[0],
                screenY - mouse[1],
            )

            if distance < bestDist:
                best = index
                bestDist = distance

        return best

    def on_key_press(self, symbol, modifiers):
        """Handle key presses"""
        key = arcade.key

        if symbol in (key.ESCAPE, key.Q):
            self.close()
        elif symbol == key.SPACE:
            self.paused = not self.paused
        elif symbol == key.ENTER:
            self.intro = INTRO_HOLD + INTRO_GLIDE
        elif symbol == key.UP:
            self.speedIdx = min(self.speedIdx + 1, len(SPEEDS) - 1)
        elif symbol == key.DOWN:
            self.speedIdx = max(self.speedIdx - 1, 0)
        elif symbol == key.T:
            self.treeMode = not self.treeMode
        elif symbol == key.G:
            self.genMode = not self.genMode
        elif symbol == key.S:
            self.spreadMode = not self.spreadMode
        elif symbol == key.F:
            self.follow = not self.follow
        elif symbol == key.H:
            self.rings = not self.rings
        elif symbol == key.E:
            self.effects = not self.effects
        elif symbol == key.R:
            self.newRun()

    def on_mouse_motion(self, x, y, dx, dy):
        """Track mouse position"""
        self.mousePos = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Select agent on click"""
        if x < SIM:
            self.selected = self.nearestAgent((x, y), 16)

    def on_update(self, delta_time):
        """Update simulation and viewer"""
        dt = min(delta_time, 0.05)
        self.now += dt

        introTotal = INTRO_HOLD + INTRO_GLIDE
        intro = self.intro < introTotal

        if intro:
            self.intro += dt

        events = []
        finished = self.t >= self.steps

        if not self.paused and not finished and not intro:
            self.acc += dt * TICKS_PER_SECOND * SPEEDS[self.speedIdx]

            while self.acc >= 1 and self.t < self.steps:
                self.acc -= 1
                stepSimulation(self.agents, self.t, self.p)

                for index in range(len(self.agents)):
                    agent = self.agents[index]

                    if agent.changedAt == self.t:
                        if agent.heardAt == self.t and agent.infector >= 0:
                            if agent.ignored:
                                kind = 'ignored'
                                colour = IGNORED_COL
                            else:
                                kind = 'rumour'
                                colour = STATE_COL[SPREADER]

                            events.append(
                                (
                                    agent.infector,
                                    index,
                                    colour,
                                    kind,
                                    agent.generation,
                                    self.t,
                                )
                            )

                            if not agent.ignored:
                                self.latest = index
                        elif (
                            agent.state == CORRECTOR
                            and agent.corrSource >= 0
                        ):
                            events.append(
                                (
                                    agent.corrSource,
                                    index,
                                    STATE_COL[CORRECTOR],
                                    'correction',
                                    agent.corrGeneration,
                                    self.t,
                                )
                            )

                self.history.append(countStates(self.agents))
                self.t += 1
                self.counts = countStates(self.agents)
                self.updateTransmissionCounts()

        # update cached transmission counts only after a new step
        if not hasattr(self, 'toldStep') or self.toldStep != self.t:
            self.updateTransmissionCounts()

        # smooth shown positions toward real positions
        smooth = 1 - math.exp(-dt * SMOOTH_RATE)
        real = self.realPositions()
        self.shown += (real - self.shown) * smooth

        if self.intro < introTotal:
            progress = max(
                0.0,
                (self.intro - INTRO_HOLD) / INTRO_GLIDE,
            )
            eased = progress * progress * (3 - 2 * progress)

            for index, (introX, introY) in self.introPos.items():
                self.shown[index] = (
                    introX + (real[index][0] - introX) * eased,
                    introY + (real[index][1] - introY) * eased,
                )

        # add arrows and pulses for new events
        for source, index, colour, kind, hop, time in events:
            start = self.toScreen(self.shown[source])
            end = self.toScreen(self.shown[index])

            self.arrows.append(
                [
                    start[0],
                    start[1],
                    end[0],
                    end[1],
                    self.now,
                    colour,
                ]
            )
            self.pulses.append([index, self.now, colour])
            self.log.append((time, source, index, hop, kind))

        if not self.treeMode:
            self.arrows = [
                arrow for arrow in self.arrows
                if self.now - arrow[4] < ARROW_LIFE

             ][-MAX_ARROWS:]

        self.pulses = [
            pulse for pulse in self.pulses
            if self.now - pulse[1] < PULSE_LIFE
        ][-MAX_PULSES:]
        self.log = self.log[-60:]

        # update dots and glows
        for index in range(len(self.agents)):
            agent = self.agents[index]
            screenX, screenY = self.toScreen(self.shown[index])
            active = agent.state in (SPREADER, CORRECTOR)

            if self.genMode and agent.generation >= 0:
                colour = GEN_COL[agent.generation % len(GEN_COL)]
                radius = DOT_HOP
            else:
                colour = STATE_COL[agent.state]

                if active:
                    radius = DOT_ACTIVE
                else:
                    radius = DOT_IDLE

            if self.spreadMode and self.told[index] > 0:
                radius = max(
                    radius,
                    min(
                        SPREAD_MAX,
                        SPREAD_BASE
                        + SPREAD_GROW * math.sqrt(self.told[index]),
                    ),
                )

                if not active and not self.genMode:
                    colour = SPREAD_COL

            dot = self.dots[index]
            dot.position = (screenX, screenY)

            if self.dotStyle[index] != (colour, radius):
                self.dotStyle[index] = (colour, radius)
                dot.color = rgba(colour, 255)

                if agent.group == NO_GROUP:
                    dot.scale = radius * 1.5 / 10
                else:
                    dot.scale = radius / 8

            glow = self.glows[index]
            glow.position = (screenX, screenY)

            if active and self.effects:
                glow.color = rgba(
                    STATE_COL[agent.state],
                    GLOW_ALPHA,
                )
                glow.scale = 0.85 + 0.15 * math.sin(self.now * 6 + index)
                self.glowStyle[index] = True
            elif self.glowStyle[index]:
                glow.color = (255, 255, 255, 0)
                self.glowStyle[index] = False
    def updateTransmissionCounts(self):
        """Update cached direct transmission counts for each agent"""
        told = [0] * len(self.agents)

        for agent in self.agents:
            if agent.infector >= 0:
                told[agent.infector] += 1

        self.told = told
        self.toldStep = self.t

        order = sorted(
            range(len(self.agents)),
            key=lambda index: self.told[index],
        )
        self.top = [
            index for index in order[:5] if told[index] > 0
        ]

        self.near = nearSubject(
            self.agents,
            self.p.get('nearRadius', 10),
        )

    def label(self, key, message, x, yTop, colour=TEXT, size=11, bold=False):
        """Draw or update label"""
        y = SIM - yTop
        text = self.texts.get(key)

        if text is None:
            text = arcade.Text(
                message,
                x,
                y,
                colour,
                size,
                font_name=FONT,
                bold=bold,
                anchor_y='top',
            )
            self.texts[key] = text
        else:
            if text.text != message:
                text.text = message

            text.position = (x, y)

            if tuple(text.color) != tuple(rgba(colour, 255)):
                text.color = rgba(colour, 255)

        text.draw()

    def on_draw(self):
        """Draw viewer"""
        self.clear()
        p = self.p
        radius = p['leash'] * SCALE

        # draw group areas
        for index in range(len(GROUP_CENTRES)):
            centreX = GROUP_CENTRES[index][0] * SCALE
            centreY = GROUP_CENTRES[index][1] * SCALE

            arcade.draw_circle_filled(
                centreX,
                centreY,
                radius,
                rgba(GROUP_COL[index], 20),
            )
            arcade.draw_circle_outline(
                centreX,
                centreY,
                radius,
                rgba(GROUP_COL[index], 90),
                1,
            )

        if self.effects:
            self.glowList.draw(
                blend_function=self.ctx.BLEND_PREMULTIPLIED_ALPHA
            )

        # draw arrows
        for arrow in self.arrows:
            age = self.now - arrow[4]

            if self.treeMode:
                minimum = 90
            else:
                minimum = 0

            alpha = max(
                minimum,
                int(255 * (1 - age / ARROW_LIFE)),
            )

            drawArrow(
                (arrow[0], arrow[1]),
                (arrow[2], arrow[3]),
                rgba(arrow[5], alpha),
                3,
            )

        # draw pulses
        for pulse in self.pulses:
            age = self.now - pulse[1]
            x, y = self.toScreen(self.shown[pulse[0]])

            arcade.draw_circle_outline(
                x,
                y,
                5 + PULSE_SIZE * age / PULSE_LIFE,
                rgba(
                    pulse[2],
                    int(255 * (1 - age / PULSE_LIFE)),
                ),
                2,
            )

        self.dotList.draw()

        # draw group rings
        if self.rings:
            for index in range(len(self.agents)):
                if self.agents[index].group != NO_GROUP:
                    x, y = self.toScreen(self.shown[index])

                    if self.dotStyle[index]:
                        ringRadius = self.dotStyle[index][1] + 2
                    else:
                        ringRadius = 5

                    arcade.draw_circle_outline(
                        x,
                        y,
                        ringRadius,
                        GROUP_COL[self.agents[index].group],
                        1,
                    )

        # draw gold chain
        if self.selected is not None:
            target = self.selected
        elif self.follow:
            target = self.latest
        else:
            target = -1

        if target >= 0:
            chain = traceChain(self.agents, target)

            if self.selected is not None:
                colour = WHITE
            else:
                colour = GOLD

            points = [
                self.toScreen(self.shown[index]) for index in chain
            ]

            for index in range(len(points) - 1):
                drawArrow(
                    points[index],
                    points[index + 1],
                    colour,
                    3,
                )

            for index in range(len(points)):
                arcade.draw_circle_outline(
                    points[index][0],
                    points[index][1],
                    9,
                    colour,
                    2,
                )

                if self.agents[chain[index]].generation >= 0:
                    self.label(
                        'hop' + str(index),
                        str(self.agents[chain[index]].generation),
                        points[index][0] + 8,
                        SIM - points[index][1] - 4,
                        colour,
                        10,
                    )

        # draw patient zero markers
        for number, zero in enumerate(self.zeros):
            x, y = self.toScreen(self.shown[zero])

            arcade.draw_circle_outline(
                x,
                y,
                12 + 3 * math.sin(self.now * 4.5),
                WHITE,
                2,
            )

            if len(self.zeros) == 1:
                text = 'PATIENT 0'
            else:
                text = 'P0'

            self.label(
                'p0_' + str(number),
                text,
                x - 4,
                SIM - y - 18,
                WHITE,
                10,
                True,
            )

        # draw subject marker
        for index in range(len(self.agents)):
            if self.agents[index].isSubject:
                x, y = self.toScreen(self.shown[index])

                arcade.draw_circle_outline(
                    x,
                    y,
                    14,
                    SUBJECT_COL,
                    2,
                )

                if p.get('avoidRadius', 0) > 0:
                    arcade.draw_circle_outline(
                        x,
                        y,
                        p['avoidRadius'] * SCALE,
                        rgba(SUBJECT_COL, 70),
                        1,
                    )

                self.label(
                    'subject',
                    'SUBJECT',
                    x - 4,
                    SIM - y - 20,
                    SUBJECT_COL,
                    10,
                    True,
                )

        # draw intro text
        if self.intro < INTRO_HOLD:
            centreX = BOX / 2 * SCALE
            centreY = BOX / 2 * SCALE

            self.label(
                'intro0',
                'PATIENT 0 starts the rumour',
                centreX - 110,
                SIM - centreY + 30,
                WHITE,
                11,
                True,
            )
            self.label(
                'intro1',
                "the SUBJECT is who it's about",
                centreX - 110,
                SIM - centreY + 48,
                SUBJECT_COL,
                11,
                True,
            )
            self.label(
                'intro2',
                'press ENTER to skip',
                centreX - 110,
                SIM - centreY + 68,
                DIM,
                10,
            )

        # draw top spreaders
        if self.spreadMode:
            for rank, index in enumerate(self.top[:3]):
                x, y = self.toScreen(self.shown[index])

                if rank == 0:
                    arcade.draw_circle_outline(
                        x,
                        y,
                        SPREAD_MAX + 4,
                        GOLD,
                        2,
                    )

                if rank == 0:
                    colour = GOLD
                else:
                    colour = TEXT

                self.label(
                    'top' + str(rank),
                    '#' + str(index) + ' told ' + str(self.told[index]),
                    x + 12,
                    SIM - y - 4,
                    colour,
                    10,
                    rank == 0,
                )

        # draw group labels
        for index in range(len(GROUP_CENTRES)):
            centreX = GROUP_CENTRES[index][0] * SCALE
            centreY = GROUP_CENTRES[index][1] * SCALE

            self.label(
                'grp' + str(index),
                'Group ' + GROUP_NAMES[index],
                centreX - 28,
                SIM - (centreY + radius + 4),
                GROUP_COL[index],
                10,
            )

        self.drawTooltip()
        self.drawPanel()

    def drawTooltip(self):
        """Draw tooltip for hovered agent"""
        mouseX, mouseY = self.mousePos

        if mouseX >= SIM or mouseX < 0:
            return

        hovered = self.nearestAgent(self.mousePos, 12)

        if hovered is None:
            return

        lines = describe(self.agents, hovered, self.p)
        width = max(len(line) for line in lines) * 7 + 14
        height = 16 * len(lines) + 8
        boxX = min(mouseX + 14, SIM - width - 4)
        boxY = min(mouseY + 8, SIM - height - 4)

        arcade.draw_lbwh_rectangle_filled(
            boxX,
            boxY,
            width,
            height,
            (30, 40, 75, 235),
        )
        arcade.draw_lbwh_rectangle_outline(
            boxX,
            boxY,
            width,
            height,
            (130, 145, 180),
            1,
        )

        for index, line in enumerate(lines):
            self.label(
                'tip' + str(index),
                line,
                boxX + 7,
                SIM - (boxY + height - 5 - 16 * index),
                TEXT,
                10,
            )

    def drawPanel(self):
        """Draw side panel"""
        arcade.draw_lbwh_rectangle_filled(
            SIM,
            0,
            SIDE,
            SIM,
            PANEL,
        )

        x0 = SIM + 20
        y = 38

        self.label(
            'title',
            'Team Char Siu - Rumour Spread',
            x0,
            10,
            TEXT,
            14,
            True,
        )

        for index, line in enumerate(
            wrap('"' + self.rumour + '"', 50)[:2]
        ):
            self.label(
                'rumour' + str(index),
                line,
                x0,
                y,
                GOLD,
                11,
            )
            y += 17

        y += 4

        if self.paused:
            pauseText = '   PAUSED'
        else:
            pauseText = ''

        if self.t >= self.steps:
            finishText = '   FINISHED (R replays)'
        else:
            finishText = ''

        if self.intro < INTRO_HOLD + INTRO_GLIDE:
            introText = '   INTRO'
        else:
            introText = ''

        self.label(
            'step',
            'step %d / %d   %sx%s%s%s'
            % (
                self.t,
                self.steps,
                SPEEDS[self.speedIdx],
                pauseText,
                finishText,
                introText,
            ),
            x0,
            y,
        )

        y += 22

        counts = self.counts
        stats = self.stats

        for index in range(4):
            arcade.draw_circle_filled(
                x0 + 6,
                SIM - (y + 8),
                5,
                LINE_COL[index],
            )

            self.label(
                'count' + str(index),
                STATE_NAMES[index] + ': ' + str(counts[index])
                + '  (' + STATE_HELP[index] + ')',
                x0 + 20,
                y,
            )
            y += 18

        self.label(
            'stats',
            'had the rumour: %d   ignored it: %d   believers: %d'
            % (
                stats['everHadRumour'],
                stats['ignoredIt'],
                stats['believers'],
            ),
            x0,
            y,
            DIM,
            10,
        )

        y += 16

        self.label(
            'near',
            'near the subject: %d (was %d), believers: %d'
            % (
                self.near[0],
                self.near0,
                self.near[1],
            ),
            x0,
            y,
            SUBJECT_COL,
            10,
        )

        y += 22

        chartWidth = SIDE - 40
        chartHeight = CHART_HEIGHT
        bottom = SIM - (y + chartHeight)
        self.chartRect = (x0, bottom, chartWidth, chartHeight)

        arcade.draw_lbwh_rectangle_filled(
            x0,
            bottom,
            chartWidth,
            chartHeight,
            (24, 32, 60),
        )
        arcade.draw_lbwh_rectangle_outline(
            x0,
            bottom,
            chartWidth,
            chartHeight,
            (60, 72, 110),
            1,
        )

        if len(self.history) > 1:
            for index in range(4):
                points = [
                    (
                        x0 + (step + 1) / self.steps * chartWidth,
                        bottom
                        + row[index] / len(self.agents) * chartHeight,
                    )
                    for step, row in enumerate(self.history)
                ]

                arcade.draw_line_strip(
                    points,
                    LINE_COL[index],
                    2,
                )

        self.label(
            'chart',
            'counts over time',
            x0 + 6,
            y + 4,
            DIM,
            10,
        )

        y += chartHeight + 10

        self.label(
            'topTitle',
            'top spreaders (told the most people)',
            x0,
            y,
            DIM,
            10,
        )

        y += 16

        if not self.top:
            self.label(
                'topNone',
                'nobody has passed it on yet',
                x0,
                y,
                DIM,
                10,
            )
            y += 14

        for rank, index in enumerate(self.top[:3]):
            agent = self.agents[index]

            if agent.group == NO_GROUP:
                group = 'no group'
            else:
                group = 'group ' + GROUP_NAMES[agent.group]

            if rank == 0:
                colour = GOLD
            else:
                colour = TEXT

            self.label(
                'topRow' + str(rank),
                '#%d  told %d   %s' % (index, self.told[index], group),
                x0,
                y,
                colour,
                10,
            )
            y += 14

        y += 10

        self.label(
            'logTitle',
            'latest passes (teller -> new person)',
            x0,
            y,
            DIM,
            10,
        )

        y += 16

        for index, entry in enumerate(self.log[::-1][:3]):
            if entry[4] == 'rumour':
                colour = LINE_COL[SPREADER]
            elif entry[4] == 'correction':
                colour = LINE_COL[CORRECTOR]
            else:
                colour = DIM

            if entry[4] == 'correction':
                suffix = '  (correction)'
            elif entry[4] == 'ignored':
                suffix = '  (ignored it)'
            else:
                suffix = ''

            self.label(
                'log' + str(index),
                't%d  #%d -> #%d%s'
                % (entry[0], entry[1], entry[2], suffix),
                x0,
                y,
                colour,
                10,
            )
            y += 14

        y += 10

        if self.selected is not None:
            for index, line in enumerate(
                describe(self.agents, self.selected, self.p)
            ):
                if y > SIM - 66:
                    break

                if index == 0:
                    text = 'Selected ' + line
                else:
                    text = line

                self.label(
                    'sel' + str(index),
                    text,
                    x0,
                    y,
                    WHITE,
                    10,
                )
                y += 14
        else:
            self.label(
                'sel0',
                'gold path = chain to the newest person (F)',
                x0,
                y,
                DIM,
                10,
            )
            self.label(
                'sel1',
                'click an agent to trace theirs',
                x0,
                y + 14,
                DIM,
                10,
            )

        if self.treeMode:
            arrowText = 'keep'
        else:
            arrowText = 'fade'

        if self.genMode:
            hopText = 'on'
        else:
            hopText = 'off'

        if self.follow:
            followText = 'on'
        else:
            followText = 'off'

        if self.rings:
            ringText = 'on'
        else:
            ringText = 'off'

        flags = (
            'T arrows: ' + arrowText
            + '   G hop colours: ' + hopText
            + '   F follow: ' + followText
            + '   H rings: ' + ringText
        )

        if self.spreadMode:
            spreadText = 'on'
        else:
            spreadText = 'off'

        self.label(
            'help0',
            'S spreader size: ' + spreadText
            + '    ENTER skips the intro',
            x0,
            SIM - 54,
            DIM,
            10,
        )
        self.label(
            'help1',
            'SPACE pause  UP/DOWN speed  R replay  ESC quit',
            x0,
            SIM - 38,
            DIM,
            10,
        )
        self.label(
            'help2',
            flags,
            x0,
            SIM - 22,
            DIM,
            10,
        )

        self.drawChartHover()

    def drawChartHover(self):
        """Draw chart hover tooltip"""
        x, y, width, height = self.chartRect
        mouseX, mouseY = self.mousePos

        if not self.history:
            return

        if not (
            x <= mouseX <= x + width
            and y <= mouseY <= y + height
        ):
            return

        step = max(
            1,
            min(
                len(self.history),
                round((mouseX - x) / width * self.steps),
            ),
        )
        guideX = x + step / self.steps * width

        arcade.draw_line(
            guideX,
            y,
            guideX,
            y + height,
            rgba(TEXT, 100),
            1,
        )

        lines = ['step ' + str(step)]

        for index in range(4):
            lines.append(
                STATE_NAMES[index] + ': '
                + str(self.history[step - 1][index])
            )

        boxX = min(x + width - 170, max(x, mouseX + 10))
        boxY = min(y + height - 4, max(y + 90, mouseY + 45))

        arcade.draw_lbwh_rectangle_filled(
            boxX,
            boxY - 90,
            170,
            90,
            (30, 40, 75, 245),
        )

        for index, line in enumerate(lines):
            if index == 0:
                colour = TEXT
            else:
                colour = LINE_COL[index - 1]

            self.label(
                'chartTip' + str(index),
                line,
                boxX + 6,
                SIM - (boxY - 5 - 16 * index),
                colour,
                10,
            )


def runViewer(build, steps, p, rumour):
    """Run Arcade viewer"""
    window = RumourWindow(build, steps, p, rumour)
    arcade.run()

    return window.agents, window.history

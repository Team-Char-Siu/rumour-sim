"""Agent states and social traits.

The basic timer idea is adapted from Le Nguyen's disease simulation.
Friendship, correction and avoidance are extra rules for this project.
"""
import numpy as np

UNAWARE, SPREADER, CORRECTOR, STIFLER = range(4)
HOW_LONG = 50
NO_GROUP = -1


class Agent:
    def __init__(self, x, y, state, gullibility, group, counter=0, interest=1.0):
        self.x = x
        self.y = y
        self.state = state
        self.gullibility = gullibility
        self.group = group
        self.counter = counter

        # Interest decides whether they pass on a rumour after accepting it.
        self.interest = interest
        self.sharingTendency = interest

        self.openness = 0.5
        self.loyalty = 0.5

        self.visiting = None
        self.stay = 0

        self.infector = -1
        self.generation = -1
        self.corrSource = -1
        self.corrGeneration = -1
        self.changedAt = -2

        self.isSubject = False
        self.ignored = False
        self.believed = False
        self.heardAt = None
        self.shunned = 0

        self.isFriend = False
        self.wasFriend = False
        self.linger = False
        self.friendshipEndedAt = None

        self.avoiding = False
        self.beliefDecided = False
        self.avoidChance = 0.75
        self.routeSide = 1
        self.correctionDuration = 110

    def acceptBelief(self, time):
        """Decide whether a newly convinced agent avoids the subject."""
        if self.beliefDecided:
            return

        self.beliefDecided = True
        self.believed = True

        if self.isFriend:
            # A friend may stop being friends if they are not loyal.
            if np.random.random() >= self.loyalty:
                self.isFriend = False
                self.linger = False
                self.friendshipEndedAt = time
                self.avoiding = True
        else:
            self.avoiding = np.random.random() < self.avoidChance

    def becomeSpreader(self, source=-1, generation=0, time=-1):
        self.state = SPREADER
        self.counter = HOW_LONG
        self.infector = source
        self.generation = generation
        self.changedAt = time

        self.acceptBelief(time)

        if self.heardAt is None:
            self.heardAt = time

    def becomeSilentBeliever(self, source, generation, time):
        # They believe the rumour but do not pass it on.
        self.becomeSpreader(source, generation, time)
        self.state = STIFLER
        self.counter = 0

    def becomeIgnorer(self, source, generation, time):
        self.state = STIFLER
        self.counter = 0
        self.infector = source
        self.generation = generation
        self.changedAt = time

        self.ignored = True
        self.believed = False
        self.avoiding = False

        if self.heardAt is None:
            self.heardAt = time

    def becomeSubjectCorrector(self, source, generation, time):
        self.infector = source
        self.generation = generation

        if self.heardAt is None:
            self.heardAt = time

        self.becomeCorrector(-1, 0, time)

    def becomeCorrector(self, source=-1, generation=0, time=-1):
        self.state = CORRECTOR
        self.counter = self.correctionDuration
        self.corrSource = source
        self.corrGeneration = generation
        self.changedAt = time

        self.believed = False
        self.avoiding = False

    def tick(self):
        """Count down active spreaders and correctors."""
        if self.state in (SPREADER, CORRECTOR):
            self.counter -= 1

            if self.counter <= 0:
                self.state = STIFLER

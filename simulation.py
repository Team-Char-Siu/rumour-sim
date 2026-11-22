"""Serial rumour spread adapted from Le Nguyen"""
import numpy as np
from scipy.spatial import distance_matrix

from agent import Agent, UNAWARE, SPREADER, CORRECTOR, STIFLER, NO_GROUP
from movement import GROUP_CENTRES, randomPointNear, randomPointInBox, moveAgents


def makeAgents(n, seed, noGroupFraction, leash):
    """Make agents and give them random traits"""
    if n <= 0 or not 0 <= noGroupFraction <= 1:
        raise ValueError("Invalid population or no-group fraction")

    # - KEEP RANDOM DRAW ORDER UNCHANGED FOR SEEDED RUNS
    np.random.seed(seed)
    agents = []

    for i in range(n):
        if np.random.random() < noGroupFraction:
            group = NO_GROUP
        else:
            group = i % 4

        if group == NO_GROUP:
            x, y = randomPointInBox()
        else:
            x, y = randomPointNear(GROUP_CENTRES[group], leash)

        agent = Agent(
            x,
            y,
            UNAWARE,
            np.random.random(),
            group,
            interest=np.random.random(),
        )
        agent.openness, agent.loyalty = np.random.uniform(0, 1, 2)

        # - alternate route sides to avoid sending everyone the same way
        agent.routeSide = 1 if i % 2 else -1
        agents.append(agent)

    return agents


def seedSpreaders(agents, howMany, group):
    """Choose agents that start with rumour"""
    options = [
        i for i, agent in enumerate(agents)
        if agent.group == group and not agent.isSubject
    ]

    if howMany < 0 or howMany > len(options):
        raise ValueError("Not enough initial spreader candidates")

    for i in np.random.choice(options, howMany, replace=False):
        agents[i].becomeSpreader()

    return agents


def pickSubject(agents, group, friendCount=12, lingerCount=4, friendRadius=4):
    """Choose subject and give them friends"""
    options = [
        i for i, agent in enumerate(agents)
        if agent.group == group and agent.state == UNAWARE
    ]

    if not options:
        raise ValueError("No subject candidate")

    subject = agents[int(np.random.choice(options))]
    subject.isSubject = True

    candidates = [agent for agent in agents if agent is not subject]
    choices = np.random.choice(
        len(candidates), min(friendCount, len(candidates)), replace=False
    )

    for friendNumber, choice in enumerate(choices):
        friend = candidates[choice]
        friend.isFriend = True
        friend.wasFriend = True

        # - only the first selected friends linger near the subject
        friend.linger = friendNumber < lingerCount

        if friend.linger:
            friend.x, friend.y = randomPointNear(
                (subject.x, subject.y), friendRadius
            )

        if friend.believed:
            # - reassess belief now that this agent is a friend
            friend.beliefDecided = False
            friend.avoiding = False
            friend.acceptBelief(-1)

    return agents


def seedCorrectors(agents, howMany, time):
    """Add correction spreaders"""
    options = [
        i for i, agent in enumerate(agents)
        if agent.state == UNAWARE and not agent.isSubject
    ]

    for i in np.random.choice(options, min(howMany, len(options)), replace=False):
        agents[i].becomeCorrector(-1, 0, time)

    return agents


def getPositions(agents):
    """Agent positions as NumPy array"""
    return np.array([[agent.x, agent.y] for agent in agents])


def getStates(agents):
    return [agent.state for agent in agents]

def findSubjectIndex(agents):
    for index, agent in enumerate(agents):
        if agent.isSubject:
            return index
    return -1

def pickSource(row, oldStates, wantedState):
    """Pick one nearby agent with wanted state"""
    options = np.where(row & (oldStates == wantedState))[0]

    if len(options):
        return int(np.random.choice(options))

    return -1


def rollSpread(
    agents,
    time,
    contactRadius,
    rumourStrength,
    correctionStrength,
    minInterest=1.0,
    subjectDenies=1.0,
    correctionRadius=None,
):
    """Decide which agents hear rumour or correction"""
    positions = getPositions(agents)
    distances = distance_matrix(positions, positions)

    close = distances < contactRadius

    if correctionRadius is None:
        correctionRadius = contactRadius

    correctionClose = distances < correctionRadius

    # - exclude self contacts so agents cannot tell themselves
    np.fill_diagonal(close, False)
    np.fill_diagonal(correctionClose, False)

    # - snapshot states before deciding any new transitions
    oldStates = np.array(getStates(agents))
    generations = [agent.generation for agent in agents]
    correctionGenerations = [agent.corrGeneration for agent in agents]

    # - count each message type using its own contact radius
    nearbySpreaders = close[:, oldStates == SPREADER].sum(axis=1)
    nearbyCorrectors = correctionClose[:, oldStates == CORRECTOR].sum(axis=1)

    events = []

    for i, agent in enumerate(agents):
        rumourChance = 1 - (
            1 - agent.gullibility * rumourStrength
        ) ** nearbySpreaders[i]
        correctionChance = 1 - (
            1 - agent.openness * correctionStrength
        ) ** nearbyCorrectors[i]

        if oldStates[i] == UNAWARE:
            hearsRumour = np.random.random() < rumourChance
            hearsCorrection = np.random.random() < correctionChance

            # - choose one message if both succeed this step
            if hearsRumour and hearsCorrection:
                if np.random.random() < 0.5:
                    hearsRumour = False
                else:
                    hearsCorrection = False

            if hearsRumour:
                source = pickSource(close[i], oldStates, SPREADER)

                # - the subject can deny the rumour instead of sharing it
                if agent.isSubject:
                    if np.random.random() < subjectDenies:
                        event = "subject"
                    else:
                        event = "ignore"
                else:
                    shareChance = (
                        minInterest
                        + (1 - minInterest) * agent.sharingTendency
                    )

                    if np.random.random() < shareChance:
                        event = "spread"
                    else:
                        event = "silent"

                events.append((i, event, source, generations[source] + 1))

            elif hearsCorrection:
                source = pickSource(correctionClose[i], oldStates, CORRECTOR)
                events.append(
                    (i, "correct", source, correctionGenerations[source] + 1)
                )

        elif oldStates[i] in (SPREADER, STIFLER):
            notCorrectedYet = agent.corrGeneration < 0

            if notCorrectedYet and np.random.random() < correctionChance:
                source = pickSource(correctionClose[i], oldStates, CORRECTOR)
                events.append(
                    (i, "correct", source, correctionGenerations[source] + 1)
                )

    # - APPLY CHANGES ONLY AFTER EVERY AGENT IS CHECKED
    # - new spreaders cannot trigger another pass in this same step
    for i, event, source, generation in events:
        agent = agents[i]

        if event == "spread":
            agent.becomeSpreader(source, generation, time)
        elif event == "silent":
            agent.becomeSilentBeliever(source, generation, time)
        elif event == "ignore":
            agent.becomeIgnorer(source, generation, time)
        elif event == "subject":
            agent.becomeSubjectCorrector(source, generation, time)
        elif event == "correct":
            agent.becomeCorrector(source, generation, time)

    return agents


def stepSimulation(agents, time, settings):
    """Run movement timers and rumour spread for one step"""
    subject = None

    subjectIndex = findSubjectIndex(agents)
    subject = agents[subjectIndex] if subjectIndex >= 0 else None

    # - caller settings override this fallback duration
    correctionDuration = settings.get("correctionDuration", 110)
    avoidChance = settings.get("avoidChance", 0.75)

    for agent in agents:
        agent.correctionDuration = correctionDuration

        if not agent.beliefDecided:
            agent.avoidChance = avoidChance

    avoidRadius = settings.get("avoidRadius", 7)

    if subject is not None and subject.state == UNAWARE and avoidRadius > 0:
        nearbyAvoiders = []

        for agent in agents:
            if not agent.avoiding:
                continue

            dx = agent.x - subject.x
            dy = agent.y - subject.y
            distanceSquared = dx * dx + dy * dy

            if distanceSquared < (avoidRadius + 2) ** 2:
                nearbyAvoiders.append(agent)

        subject.shunned += len(nearbyAvoiders)

        # - notice builds across steps from nearby avoiders
        if nearbyAvoiders and subject.shunned >= settings.get("noticeAfter", 20):
            subject.becomeSubjectCorrector(-1, -1, time)

    moveAgents(
        agents,
        settings["stepSize"],
        settings["travelChance"],
        settings["travelSpeed"],
        settings["leash"],
        settings["stayLength"],
        subject,
        avoidRadius,
        avoidVisualBuffer=settings.get("avoidVisualBuffer", 1.15),
    )

    # - tick timers after movement and before new messages
    for agent in agents:
        agent.tick()

    rollSpread(
        agents,
        time,
        settings["contactRadius"],
        settings["rumourStrength"],
        settings["correctionStrength"],
        settings.get("minInterest", 0.5),
        settings.get("subjectDenies", 1.0),
        settings.get("correctionRadius"),
    )

    # - add scheduled correctors after normal spread for this step
    if time == settings["correctionStart"]:
        seedCorrectors(agents, settings["correctionSeeds"], time)

    return agents


def countStates(agents):
    """Count agents in each state"""
    states = getStates(agents)
    return [states.count(state) for state in range(4)]


def countSpreadersByGroup(agents):
    """Count active spreaders in each group plus no group"""
    counts = [0] * 5

    for agent in agents:
        if agent.state == SPREADER:
            counts[agent.group + 1] += 1

    return counts


def nearSubject(agents, radius):
    """Count agents near subject and believers near subject"""
    subjectIndex = findSubjectIndex(agents)
    subject = agents[subjectIndex] if subjectIndex >= 0 else None

    if subject is None:
        return [0, 0]

    nearby = []

    for agent in agents:
        if agent is subject:
            continue

        dx = agent.x - subject.x
        dy = agent.y - subject.y

        if dx * dx + dy * dy < radius ** 2:
            nearby.append(agent)

    return [len(nearby), sum(agent.believed for agent in nearby)]


def transmissionStats(agents):
    """Collect final rumour statistics"""
    everHadRumour = [agent for agent in agents if agent.generation >= 0]

    # - count direct recipients rather than downstream reach
    children = {}

    for agent in agents:
        if agent.infector >= 0:
            children[agent.infector] = children.get(agent.infector, 0) + 1

    # - existing tie handling is unchanged
    if children:
        biggestSpreader = max(children, key=children.get)
        mostPassedOn = children[biggestSpreader]
    else:
        biggestSpreader = -1
        mostPassedOn = 0

    maxGeneration = max(
        [agent.generation for agent in everHadRumour], default=0
    )

    generationSizes = []

    for generation in range(maxGeneration + 1):
        generationSizes.append(
            sum(agent.generation == generation for agent in everHadRumour)
        )

    passedOnToNobody = sum(
        i not in children
        for i, agent in enumerate(agents)
        if agent.generation >= 0
    )

    subjectIndex = findSubjectIndex(agents)
    subject = agents[subjectIndex] if subjectIndex >= 0 else None

    if subject is None:
        subjectHeardAt = None
        subjectHops = None
        heardBeforeSubject = None
    else:
        subjectHeardAt = subject.heardAt

        if subject.generation >= 0:
            subjectHops = subject.generation
        else:
            subjectHops = None

        if subjectHeardAt is None:
            heardBeforeSubject = None
        else:
            heardBeforeSubject = sum(
                agent.heardAt is not None and agent.heardAt <= subjectHeardAt
                for agent in agents
            )

    return {
        "everHadRumour": len(everHadRumour),
        "maxGeneration": maxGeneration,
        "generationSizes": generationSizes,
        "passedOnToNobody": passedOnToNobody,
        "mostPassedOn": mostPassedOn,
        "biggestSpreader": biggestSpreader,
        "ignoredIt": sum(agent.ignored for agent in agents),
        "believers": sum(agent.believed for agent in agents),
        "subjectHeardAtStep": subjectHeardAt,
        "subjectHops": subjectHops,
        "heardBeforeSubject": heardBeforeSubject,
        "friends": sum(agent.isFriend for agent in agents),
        "lostFriends": sum(
            agent.wasFriend and not agent.isFriend for agent in agents
        ),
        "silentBelievers": sum(
            agent.believed and agent.state == STIFLER for agent in agents
        ),
        "everCorrected": sum(agent.corrGeneration >= 0 for agent in agents),
    }


def runSimulation(agents, steps, settings):
    """Run model and save counts after every step"""
    counts = []
    groupCounts = []
    nearCounts = []

    nearRadius = settings.get("nearRadius", 10)

    # - record counts after each completed step
    for time in range(steps):
        stepSimulation(agents, time, settings)
        counts.append(countStates(agents))
        groupCounts.append(countSpreadersByGroup(agents))
        nearCounts.append(nearSubject(agents, nearRadius))

    return (
        np.array(counts),
        np.array(groupCounts),
        np.array(nearCounts),
    )

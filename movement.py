"""Movement for agents, group visits and avoidance"""
import math

import numpy as np

from agent import NO_GROUP

BOX = 100
GROUP_CENTRES = [(25, 25), (75, 25), (25, 75), (75, 75)]
GROUP_NAMES = ["A", "B", "C", "D"]


def configureGroups(edge):
    """Move group centres closer to or further from edges"""
    if not 0 < edge < 50:
        raise ValueError("group spread must be between 0 and 50")

    GROUP_CENTRES[:] = [
        (edge, edge),
        (100 - edge, edge),
        (edge, 100 - edge),
        (100 - edge, 100 - edge),
    ]


def randomPointNear(centre, radius):
    """Pick a random point inside a circle

    square root stops points bunching at centre
    """
    angle = np.random.uniform(0, 2 * math.pi)
    distance = radius * math.sqrt(np.random.random())

    x = centre[0] + distance * math.cos(angle)
    y = centre[1] + distance * math.sin(angle)

    return x, y


def randomPointInBox():
    """Pick a random point inside box"""
    return tuple(np.random.uniform(0, BOX, 2))


def clampToBox(agent):
    """Keep agent inside box"""
    agent.x = min(BOX, max(0, agent.x))
    agent.y = min(BOX, max(0, agent.y))


def randomWalk(agent, stepSize):
    """Move agent by small random amount"""
    agent.x += stepSize * np.random.uniform(-1, 1)
    agent.y += stepSize * np.random.uniform(-1, 1)
    clampToBox(agent)


def currentTarget(agent):
    """Group agent is heading to"""
    if agent.visiting is not None:
        return agent.visiting

    return agent.group


def moveAgent(agent, stepSize, travelChance, travelSpeed, leash, stayLength):
    """Move one agent around its group or towards visited group"""
    canTravel = (
        agent.group != NO_GROUP
        and agent.visiting is None
        and np.random.random() < travelChance
    )

    if canTravel:
        otherGroups = [
            group for group in range(4) if group != agent.group
        ]
        agent.visiting = int(np.random.choice(otherGroups))
        agent.stay = stayLength

    target = currentTarget(agent)

    if target == NO_GROUP:
        randomWalk(agent, stepSize)
        return

    centre = GROUP_CENTRES[target]
    changeX = centre[0] - agent.x
    changeY = centre[1] - agent.y
    distance = math.hypot(changeX, changeY)

    if distance > leash:
        # move back to group
        speed = min(distance, travelSpeed)
        agent.x += speed * changeX / distance
        agent.y += speed * changeY / distance
    else:
        randomWalk(agent, stepSize)

        # keep agent inside group circle
        changeX = agent.x - centre[0]
        changeY = agent.y - centre[1]
        distance = math.hypot(changeX, changeY)

        if distance > leash:
            agent.x = centre[0] + changeX * leash / distance
            agent.y = centre[1] + changeY * leash / distance

        if agent.visiting is not None:
            agent.stay -= 1

            if agent.stay <= 0:
                agent.visiting = None

    clampToBox(agent)


def segmentDistance(start, end, centre):
    """Shortest distance from centre to movement path"""
    changeX = end[0] - start[0]
    changeY = end[1] - start[1]
    lengthSquared = changeX * changeX + changeY * changeY

    if lengthSquared == 0:
        return math.hypot(
            start[0] - centre[0],
            start[1] - centre[1],
        )

    # closest point on path to centre
    progress = (
        (centre[0] - start[0]) * changeX
        + (centre[1] - start[1]) * changeY
    ) / lengthSquared
    progress = max(0, min(1, progress))

    closestX = start[0] + progress * changeX
    closestY = start[1] + progress * changeY

    return math.hypot(
        closestX - centre[0],
        closestY - centre[1],
    )


def safeMove(start, desired, centre, radius, side=1):
    """Move agent without crossing subject"""
    if radius <= 0:
        return desired

    # keep destination inside box
    desiredX = min(BOX, max(0, desired[0]))
    desiredY = min(BOX, max(0, desired[1]))
    desired = (desiredX, desiredY)

    safeRadius = radius + 1e-6
    changeX = start[0] - centre[0]
    changeY = start[1] - centre[1]
    distance = math.hypot(changeX, changeY)

    # agent too close so put just outside radius
    if distance < safeRadius:
        if distance == 0:
            angle = 0
        else:
            angle = math.atan2(changeY, changeX)

        escapeX = centre[0] + safeRadius * math.cos(angle)
        escapeY = centre[1] + safeRadius * math.sin(angle)
        escape = (escapeX, escapeY)

        if 0 <= escapeX <= BOX and 0 <= escapeY <= BOX:
            return escape

        # try around edge if direct escape fails
        for angleStep in range(72):
            angle = angleStep * math.pi / 36
            x = centre[0] + safeRadius * math.cos(angle)
            y = centre[1] + safeRadius * math.sin(angle)

            if 0 <= x <= BOX and 0 <= y <= BOX:
                return (x, y)

        raise ValueError("No feasible avoidance point")

    # normal move is safe
    if segmentDistance(start, desired, centre) >= radius:
        return desired

    # try sideways around subject
    normalX = changeX / distance
    normalY = changeY / distance
    moveLength = min(2, math.dist(start, desired))

    directions = [
        (-side * normalY, side * normalX),
        (side * normalY, -side * normalX),
        (normalX, normalY),
    ]

    for directionX, directionY in directions:
        x = start[0] + moveLength * directionX
        y = start[1] + moveLength * directionY
        candidate = (
            min(BOX, max(0, x)),
            min(BOX, max(0, y)),
        )

        if segmentDistance(start, candidate, centre) >= radius:
            return candidate

    # no safe direction so stay put
    return start


def moveAgents(
    agents,
    stepSize,
    travelChance,
    travelSpeed,
    leash,
    stayLength,
    subject=None,
    avoidRadius=0,
    avoidVisualBuffer=1.15,
):
    """Move agents then apply friendship and avoidance"""
    if subject is not None:
        moveAgent(
            subject,
            stepSize,
            travelChance,
            travelSpeed,
            leash,
            stayLength,
        )

    if subject is None:
        centre = None
    else:
        centre = (subject.x, subject.y)

    for agent in agents:
        if agent is subject:
            continue

        start = (agent.x, agent.y)
        moveAgent(
            agent,
            stepSize,
            travelChance,
            travelSpeed,
            leash,
            stayLength,
        )

        if centre is None:
            continue

        changeX = agent.x - centre[0]
        changeY = agent.y - centre[1]
        distance = math.hypot(changeX, changeY)

        # keep lingering friends close to subject
        lingerDistance = max(1, avoidRadius * 0.8)

        if agent.isFriend and agent.linger and distance > lingerDistance:
            agent.x = centre[0] + changeX * lingerDistance / distance
            agent.y = centre[1] + changeY * lingerDistance / distance

        if not agent.avoiding or avoidRadius <= 0:
            continue

        # avoid based on start position
        changeX = start[0] - centre[0]
        changeY = start[1] - centre[1]
        distance = math.hypot(changeX, changeY)

        outerRadius = avoidRadius * avoidVisualBuffer
        desired = (agent.x, agent.y)
        target = currentTarget(agent)

        # - blocked group centre should not become a ring destination
        if target != NO_GROUP:
            groupCentre = GROUP_CENTRES[target]
            centreBlocked = (
                math.dist(groupCentre, centre) < outerRadius + stepSize
            )
            insideGroup = math.dist(start, groupCentre) <= leash

            if centreBlocked and insideGroup:
                # - wander through safe space within the current group
                # - reject blocked moves instead of circling the subject
                desired = start

                for attempt in range(16):
                    candidate = (
                        start[0] + stepSize * np.random.uniform(-1, 1),
                        start[1] + stepSize * np.random.uniform(-1, 1),
                    )

                    if not (
                        0 <= candidate[0] <= BOX
                        and 0 <= candidate[1] <= BOX
                    ):
                        continue

                    if math.dist(candidate, groupCentre) > leash:
                        continue

                    if math.dist(candidate, centre) < outerRadius:
                        continue

                    if segmentDistance(start, candidate, centre) < avoidRadius:
                        continue

                    desired = candidate
                    break
               

        # gentle push away in soft avoidance zone
        if avoidRadius < distance < outerRadius:
            pressure = stepSize * (outerRadius - distance)
            pressure /= max(outerRadius - avoidRadius, 1e-9)

            desired = (
                desired[0] + pressure * changeX / distance,
                desired[1] + pressure * changeY / distance,
            )

        agent.x, agent.y = safeMove(
            start,
            desired,
            centre,
            avoidRadius,
            agent.routeSide,
        )

    return agents

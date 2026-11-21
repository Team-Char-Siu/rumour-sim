"""Drawing only helpers for arrows and avoidance rings"""
import math

AVOID_RING_COL = (255, 95, 95, 210)
AVOID_RING_WIDTH = 1.4
AVOID_RING_GAP = 4.5


def showsAvoidance(agent):
    """Check if agent has red avoidance ring"""
    return bool(agent.avoiding) and not agent.isSubject


def drawThinArrow(start, end, colour, width):
    """Draw thin arrow between two points"""
    import arcade

    changeX = end[0] - start[0]
    changeY = end[1] - start[1]
    length = math.hypot(changeX, changeY)

    if length < 1e-6:
        return

    unitX = changeX / length
    unitY = changeY / length

    # keep arrow away from agent edges
    inset = min(6.0, length * 0.2)
    lineStart = (
        start[0] + inset * unitX,
        start[1] + inset * unitY,
    )
    lineEnd = (
        end[0] - inset * unitX,
        end[1] - inset * unitY,
    )

    highlight = tuple(colour[:3]) in (
        (255, 214, 10),
        (255, 255, 255),
    )
    stroke = 1.5 if highlight else 1.0
    alpha = colour[3] if len(colour) > 3 else 255

    arrowColour = (
        *colour[:3],
        round(alpha * (0.85 if highlight else 0.65)),
    )

    arcade.draw_line(
        *lineStart,
        *lineEnd,
        arrowColour,
        stroke,
    )

    # draw arrow head
    head = min(5.0, length * 0.22)
    wing = head * 0.32
    baseX = lineEnd[0] - head * unitX
    baseY = lineEnd[1] - head * unitY

    arcade.draw_triangle_filled(
        *lineEnd,
        baseX - wing * unitY,
        baseY + wing * unitX,
        baseX + wing * unitY,
        baseY - wing * unitX,
        arrowColour,
    )

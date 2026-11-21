"""Headless plots for the rumour simulation"""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from movement import GROUP_NAMES

# unaware spreader corrector stifler
COLOURS = ["#9aa5b1", "#d62828", "#2a9d8f", "#264653"]
NAMES = ["Unaware", "Spreader", "Corrector", "Stifler"]
GROUP_COLOURS = ["#f4a261", "#4361ee", "#9d4edd", "#8d6e63"]


def plotCurve(counts, name, rumour):
    """Plot how many agents are in each state"""
    plt.figure()

    for state in range(4):
        plt.plot(counts[:, state], color=COLOURS[state], label=NAMES[state])

    plt.xlabel("Time")
    plt.ylabel("Agents")
    plt.title("Rumour Curve\n" + textwrap.fill('"' + rumour + '"', 50))
    plt.legend()
    plt.savefig(name, bbox_inches="tight")
    plt.close()


def plotGroupSpreaders(groupCounts, name):
    """Plot spreaders in each group"""
    plt.figure()

    plt.plot(groupCounts[:, 0], color="grey", linestyle=":", label="No group")

    for group in range(len(GROUP_NAMES)):
        plt.plot(
            groupCounts[:, group + 1],
            color=GROUP_COLOURS[group],
            label="Group " + GROUP_NAMES[group],
        )

    plt.xlabel("Time")
    plt.ylabel("Spreaders")
    plt.title("Spreaders per group")
    plt.legend()
    plt.savefig(name, bbox_inches="tight")
    plt.close()


def plotNearSubject(near, name, heardAt, radius):
    """Plot agents close to subject"""
    plt.figure()

    plt.plot(near[:, 0], color="#264653", label="everyone near the subject")
    plt.plot(near[:, 1], color="#d62828", label="believers near the subject")

    if heardAt is not None:
        plt.axvline(
            heardAt,
            color="#ff69b4",
            linestyle="--",
            label="subject finds out",
        )

    plt.xlabel("Time")
    plt.ylabel("Agents within " + str(radius) + " units")
    plt.title("Isolation of the subject")
    plt.legend()
    plt.savefig(name, bbox_inches="tight")
    plt.close()


def plotTree(agents, name):
    """Plot who told who"""
    agentsWithRumour = [
        i for i in range(len(agents)) if agents[i].generation >= 0
    ]

    if len(agentsWithRumour) == 0:
        return

    maxGeneration = max(
        agents[i].generation for i in agentsWithRumour
    )
    positions = {}

    for generation in range(maxGeneration + 1):
        row = [
            i for i in agentsWithRumour
            if agents[i].generation == generation
        ]

        # put children beside parent so lines cross less
        row.sort(
            key=lambda i: positions[agents[i].infector][0]
            if agents[i].infector in positions
            else 0
        )

        for position, i in enumerate(row):
            positions[i] = ((position + 0.5) / len(row), -generation)

    plt.figure(figsize=(10, 5))

    for i in agentsWithRumour:
        parent = agents[i].infector

        if parent >= 0:
            plt.plot(
                [positions[parent][0], positions[i][0]],
                [positions[parent][1], positions[i][1]],
                color="grey",
                alpha=0.35,
                linewidth=0.7,
            )

    for i in agentsWithRumour:
        agent = agents[i]

        if agent.group >= 0:
            colour = GROUP_COLOURS[agent.group]
        else:
            colour = "black"

        plt.scatter(
            positions[i][0],
            positions[i][1],
            color=colour,
            s=14,
            zorder=3,
        )

    starters = [
        i for i in agentsWithRumour if agents[i].infector < 0
    ]

    plt.scatter(
        [positions[i][0] for i in starters],
        [positions[i][1] for i in starters],
        color="red",
        marker="*",
        s=160,
        zorder=4,
        label="Started with it",
    )

    plt.yticks(
        range(0, -maxGeneration - 1, -1),
        ["hop " + str(generation) for generation in range(maxGeneration + 1)],
    )
    plt.xticks([])
    plt.title("Who told who (colour = home group, black = no group)")
    plt.legend(loc="lower right")
    plt.savefig(name, bbox_inches="tight")
    plt.close()

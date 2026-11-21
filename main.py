"""Command line entry point"""
import argparse
import math
import time
from pathlib import Path


def positiveInt(value):
    """Turn command line value into positive whole number"""
    number = int(value)

    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")

    return number


def makeSettings(
    n,
    correctionStrength=0.03,
    groupSpread=33,
    leash=15,
    avoidVisualBuffer=1.15,
    correctionDuration=50,
    correctionRadius=None,
):
    """Make settings used by simulation"""
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("population must be a positive integer")

    # keep contact radius similar as population changes
    contactRadius = 4 * math.sqrt(500 / n)

    if correctionRadius is None:
        correctionRadius = contactRadius

    values = [
        correctionStrength,
        groupSpread,
        leash,
        avoidVisualBuffer,
        correctionDuration,
        correctionRadius,
    ]

    if not all(math.isfinite(value) for value in values):
        raise ValueError("settings must be finite")

    if not 0 <= correctionStrength <= 1:
        raise ValueError("invalid correction strength")

    if correctionDuration <= 0 or correctionRadius <= 0:
        raise ValueError("invalid correction duration or radius")

    if not 0 < groupSpread < 50:
        raise ValueError("invalid group spread")

    if not 0 < leash <= min(groupSpread, 50 - groupSpread):
        raise ValueError("invalid leash")

    if avoidVisualBuffer < 1:
        raise ValueError("invalid avoidance buffer")

    return {
        "stepSize": 1.5,
        "contactRadius": contactRadius,
        "rumourStrength": 0.06,
        "correctionStrength": correctionStrength,
        "correctionStart": 60,
        "correctionSeeds": 0,
        "correctionDuration": correctionDuration,
        "correctionRadius": correctionRadius,
        "minInterest": 0.5,
        "subjectDenies": 1.0,
        "avoidRadius": 7,
        "avoidChance": 0.75,
        "noticeAfter": 20,
        "nearRadius": 10,
        "leash": leash,
        "travelChance": 0.003,
        "travelSpeed": 2.0,
        "stayLength": 40,
        "groupSpread": groupSpread,
        "avoidVisualBuffer": avoidVisualBuffer,
    }


def parseArgs(argv=None):
    """Read command line options"""
    parser = argparse.ArgumentParser(
        description="Team Char Siu rumour simulation"
    )

    parser.add_argument("rumour", nargs="?")
    parser.add_argument("--n", type=positiveInt, default=500)
    parser.add_argument("--steps", type=positiveInt, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--headless", action="store_true")

    parser.add_argument("--correction-strength", type=float, default=0.03)
    parser.add_argument("--group-spread", type=float, default=33)
    parser.add_argument("--leash", type=float, default=15)
    parser.add_argument("--avoid-visual-buffer", type=float, default=1.15)
    parser.add_argument("--correction-radius", type=float, default=None)
    parser.add_argument("--correction-duration", type=positiveInt, default=50)

    args = parser.parse_args(argv)

    if not 0 <= args.seed < 2 ** 32:
        parser.error("seed must be between 0 and 4294967295")

    try:
        settingsFromArgs(args)
    except ValueError as error:
        parser.error(str(error))

    return args


def settingsFromArgs(args):
    """Turn command line arguments into simulation settings"""
    return makeSettings(
        args.n,
        args.correction_strength,
        args.group_spread,
        args.leash,
        args.avoid_visual_buffer,
        args.correction_duration,
        args.correction_radius,
    )


def buildAgents(n, seed, settings):
    """Make agents patient zero and subject"""
    from movement import configureGroups
    from simulation import makeAgents, seedSpreaders, pickSubject

    configureGroups(settings["groupSpread"])

    agents = makeAgents(n, seed, 0.2, settings["leash"])

    for agent in agents:
        agent.correctionDuration = settings["correctionDuration"]

    seedSpreaders(agents, 1, 0)

    friendRadius = min(4, settings["avoidRadius"] * 0.7)

    return pickSubject(
        agents,
        3,
        friendCount=12,
        lingerCount=4,
        friendRadius=friendRadius,
    )


def main(argv=None):
    args = parseArgs(argv)

    if args.rumour is None:
        rumour = input("Type the rumour: ").strip()
    else:
        rumour = args.rumour

    if rumour == "":
        rumour = "The canteen is closing next week"

    settings = settingsFromArgs(args)

    def build():
        return buildAgents(args.n, args.seed, settings)

    from simulation import runSimulation, transmissionStats

    try:
        agents = build()
    except ValueError as error:
        raise SystemExit(str(error)) from error

    if args.headless:
        from plots import (
            plotCurve,
            plotGroupSpreaders,
            plotNearSubject,
            plotTree,
        )

        Path("results").mkdir(exist_ok=True)

        startTime = time.perf_counter()
        counts, groups, near = runSimulation(agents, args.steps, settings)
        stats = transmissionStats(agents)

        plotCurve(counts, "results/curve.png", rumour)
        plotGroupSpreaders(groups, "results/group_spreaders.png")
        plotNearSubject(
            near,
            "results/near_subject.png",
            stats["subjectHeardAtStep"],
            settings["nearRadius"],
        )
        plotTree(agents, "results/tree.png")

        print("final counts:", counts[-1])
        print("transmission:", stats)
        print("seconds:", time.perf_counter() - startTime)
    else:
        from viewer_friendships import runViewer

        agents, history = runViewer(build, args.steps, settings, rumour)

        print("stopped at step", len(history))
        print("transmission:", transmissionStats(agents))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

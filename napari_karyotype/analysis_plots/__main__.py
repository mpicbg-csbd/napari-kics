#!/usr/bin/env python3

# pylint: disable=missing-class-docstring,missing-function-docstring,no-else-return,no-else-break

import pdb  # pylint: disable=unused-import
import sys
from pulp import GLPK, LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable
import numpy as np
from importlib import import_module


module_fqn = "napari_karyotype.analysis_plots"


def find_optimal_assignment(estimates, scaffs, *, unmatched_penalty=2.0):
    n, m = len(estimates), len(scaffs)
    # Absolute value of difference between each pair of estimate and scaffold
    # estimates = np.log(estimates) / np.log(unmatched_penalty)
    # scaffs = np.log(scaffs) / np.log(unmatched_penalty)
    abs_diffs = np.log(np.abs(estimates.reshape(-1, 1) - scaffs))
    model = LpProblem(name="estimate-matching", sense=LpMinimize)
    xs = np.array(
        [
            [
                LpVariable(
                    name=f"match_{i:02d}_{j:02d}", lowBound=0, upBound=1, cat="Integer"
                )
                for j in range(m)
            ]
            for i in range(n)
        ],
        dtype=np.object_,
    )
    # Minimum abs. difference per scaffold
    mu = np.amin(abs_diffs, axis=0)
    assert mu.shape == (m,)
    model += np.sum(xs * abs_diffs) + np.sum((1 + mu) * (1 - np.sum(xs, axis=0)))

    for i in range(n):
        model += (np.sum(xs[i, :]) <= 1, f"max_matches_per_estimate_{i:02d}")

    for j in range(m):
        model += (np.sum(xs[:, j]) <= 1, f"at_most_one_match_per_scaffold_{j:02d}")

    if model.solve():
        return np.array(
            [(i, j) for j in range(m) for i in range(n) if xs[i, j].value() > 0],
            dtype=np.int_,
        )

    return np.zeros((0, 2), dtype=np.int_)


def analysis_plots(
    scaffold_sizes, estimates, *, max_deviation=30e6, plotlib="pyqtgraph"
):
    # sort in descending order
    estimates.sort()
    estimates = np.flip(estimates)
    # sort in descending order
    scaffold_sizes.sort()
    scaffold_sizes = np.flip(scaffold_sizes)

    # matching = []
    matching = find_optimal_assignment(estimates, scaffold_sizes, unmatched_penalty=2.0)

    if "." in plotlib:
        raise ValueError("plotlib must not contains dots ('.')")

    try:
        plot_backend = import_module(f".backends.{plotlib}", package=module_fqn)
    except ModuleNotFoundError:
        raise ValueError(f"Unrecognized plotlib: {plotlib}")

    plot_backend.do_plot(estimates, scaffold_sizes, matching)


def main():
    args = _parse_args()

    if args.scaffold_sizes.name.endswith(".fai"):
        scaffold_names = [line.split("\t")[0] for line in args.scaffold_sizes]
        args.scaffold_sizes.seek(0)
        scaffold_sizes = np.loadtxt(
            args.scaffold_sizes, usecols=(1,), dtype=np.int_, delimiter="\t"
        )
    else:
        scaffold_names = [str(i) for i in range(len(args.scaffold_sizes))]
        scaffold_sizes = np.loadtxt(args.scaffold_sizes, dtype=np.int_)

    estimates = np.loadtxt(args.estimates, dtype=np.int_)

    analysis_plots(
        scaffold_sizes,
        estimates,
        max_deviation=args.max_deviation,
        plotlib=args.plotlib,
    )


def _parse_args(args=sys.argv[1:]):
    import argparse

    prog = sys.argv[0]
    if prog == "__main__":
        prog = "python -m {module_fqn}"

    parser = argparse.ArgumentParser(
        prog="analysis_plots",
        description=(
            "Generate plots that allow comparing chromosome"
            " size estimates and actual scaffold sizes in a meaningful manner."
        ),
    )
    parser.add_argument(
        "scaffold_sizes",
        type=argparse.FileType("r"),
        help="Scaffold sizes either one per line or a FASTA-index",
    )
    parser.add_argument(
        "estimates",
        type=argparse.FileType("r"),
        help="Estimated chromosome sizes, one per line",
    )
    parser.add_argument(
        "--max-deviation",
        "-d",
        type=float,
        default=30e6,
        help="Maximum allowed deviation from estimate (default: 3σ = 30Mb)",
    )
    parser.add_argument(
        "--plotlib",
        "-l",
        choices=["pyqtgraph", "matplotlib"],
        default="pyqtgraph",
        help="Plotting library to use (default: {default})",
    )

    return parser.parse_args(args)


if __name__ == "__main__":
    from logging import basicConfig

    basicConfig()

    main()

#!/usr/bin/env python3

# pylint: disable=missing-class-docstring,missing-function-docstring,no-else-return,no-else-break

import pdb  # pylint: disable=unused-import
import sys
from pulp import GLPK, LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable
import numpy as np
import pandas as pd
from importlib import import_module

from logging import basicConfig, getLogger

log = getLogger(__name__)


module_fqn = "napari_karyotype.analysis_plots"


def find_optimal_assignment(estimates, scaffs, *, unmatched_penalty=2.0):
    estimates = pd.Series(estimates).values
    scaffs = pd.Series(scaffs).values

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
    scaffold_sizes = pd.Series(scaffold_sizes)
    scaffold_sizes.sort_values(ascending=False, inplace=True)
    estimates = pd.Series(estimates)
    estimates.sort_values(ascending=False, inplace=True)

    # matching = []
    matching = find_optimal_assignment(estimates, scaffold_sizes, unmatched_penalty=2.0)

    if "." in plotlib:
        raise ValueError("plotlib must not contain dots ('.')")

    try:
        plot_backend = import_module(f".backends.{plotlib}", package=module_fqn)
    except ModuleNotFoundError:
        raise ValueError(f"Unrecognized plotlib: {plotlib}")

    plot_backend.do_plot(estimates, scaffold_sizes, matching)


def main():
    args = _parse_args()

    if args.scaffold_sizes.name.endswith(".fai"):
        scaffold_sizes = _read_fasta_index(args.scaffold_sizes)
    else:
        scaffold_sizes = _read_tsv_data(args.scaffold_sizes, name="scaffold_sizes")

    estimates = _read_tsv_data(args.estimates, "chromosome_estimates")

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


def _read_fasta_index(fai_file):
    fai = pd.read_table(
        fai_file,
        header=None,
        index_col=0,
        names=("scaffold", "size"),
        usecols=(0, 1),
    )
    fai = fai.loc[:, "size"]
    fai.name = "scaffold_sizes"

    return fai


def _read_tsv_data(tsv_file, name=None):
    tsv = pd.read_table(tsv_file, header=None)

    if tsv.shape[1] == 1:
        # no names provided
        tsv = tsv.loc[:, 0]
        tsv.name = name
    elif tsv.shape[1] >= 2:
        if tsv.shape[1] > 2:
            log.warning(f"ignoring additional columns in {tsv_file.name}")

        # names in first column, sizes in second column
        tsv = pd.Series(
            tsv.iloc[:, 1].values,
            index=tsv.iloc[:, 0],
            name=name,
        )
    else:
        raise Exception(f"empty file: {tsv_file.name}")

    return tsv


if __name__ == "__main__":
    from logging import basicConfig

    basicConfig()

    main()

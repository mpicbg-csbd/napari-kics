from importlib import import_module
from logging import getLogger

import numpy as np
import pandas as pd
from pulp import LpMinimize, LpProblem, LpVariable

log = getLogger(__name__)


def size_correlation(estimates, scaffs):
    return np.exp(np.abs(np.log(estimates) - np.log(scaffs), dtype=np.float_))


def get_initial_bounds(correlation_matrix):
    return (1, 4)


def find_optimal_assignment(estimates, scaffs, *, unmatched_penalty=2.0):
    estimates = pd.Series(estimates).values
    scaffs = pd.Series(scaffs).values

    n, m = len(estimates), len(scaffs)
    # Absolute value of difference between each pair of estimate and scaffold
    # estimates = np.log(estimates) / np.log(unmatched_penalty)
    # scaffs = np.log(scaffs) / np.log(unmatched_penalty)
    correlation_matrix = size_correlation(estimates.reshape(-1, 1), scaffs)
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
    mu = unmatched_penalty * 1 / np.amin(correlation_matrix, axis=0)
    assert mu.shape == (m,)
    model += np.sum(xs * correlation_matrix) + np.sum(mu * (1 - np.sum(xs, axis=0)))

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
    scaffold_sizes,
    estimates,
    *,
    unmatched_penalty=2.0,
    min_scaffold_size=0,
    max_scaffolds=-1,
    by_name=False,
    no_optimize=False,
    plotlib="pyqtgraph",
):
    scaffold_sizes = pd.Series(scaffold_sizes)
    if min_scaffold_size > 0:
        scaffold_sizes = scaffold_sizes.loc[scaffold_sizes >= min_scaffold_size]
    scaffold_sizes.sort_values(ascending=False, inplace=True)
    if max_scaffolds is not None and max_scaffolds < len(scaffold_sizes):
        scaffold_sizes = scaffold_sizes.iloc[0:max_scaffolds]
    estimates = pd.Series(estimates)
    estimates.sort_values(ascending=False, inplace=True)

    if by_name:
        estimates_map = pd.Series(
            range(len(estimates)), index=estimates.index, name="estimate"
        )
        scaffolds_map = pd.Series(
            range(len(scaffold_sizes)), index=scaffold_sizes.index, name="scaffold"
        )
        matching = pd.merge(
            estimates_map, scaffolds_map, left_index=True, right_index=True
        )
    elif no_optimize:
        matching = np.array([(i, i) for i in range(len(estimates))])
    else:
        matching = find_optimal_assignment(
            estimates, scaffold_sizes, unmatched_penalty=unmatched_penalty
        )

    if matching.shape[0] == 0:
        matching_size = min(len(estimates), len(scaffold_sizes))
        matching = np.vstack((np.arange(matching_size), np.arange(matching_size))).T
        log.warning(
            "could not find an optimal matching; resorting to identity matching"
        )

    if "." in plotlib:
        raise ValueError("plotlib must not contain dots ('.')")

    try:
        plot_backend = import_module(f".backends.{plotlib}", package=__name__)
    except ModuleNotFoundError:
        raise ValueError(f"Unrecognized plotlib: {plotlib}")

    return plot_backend.do_plot(estimates, scaffold_sizes, matching)


def get_argument_parser():
    import argparse
    import os
    import sys

    class ArgumentParser(argparse.ArgumentParser):
        def remove_argument(self, dest):
            self._actions = [action for action in self._actions if action.dest != dest]

        def get_argument(self, dest):
            found = [action for action in self._actions if action.dest == dest]
            if len(found) == 0:
                raise IndexError("no argument found")
            return found[0]

        def __getitem__(self, dest):
            return self.get_argument(dest)

    class LoadExampleAction(argparse.Action):
        def __init__(self, option_strings, dest, nargs=0, **kwargs):
            if nargs != 0:
                raise ValueError("nargs must be zero")
            super().__init__(option_strings, dest, nargs=nargs, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            if len(values) != 0:
                raise ValueError("values not allowed")

            module_root = os.path.dirname(__file__)

            namespace.scaffold_sizes = f"{module_root}/resources/data/mMyoMyo.fasta.fai"
            namespace.scaffold_sizes = argparse.FileType("r")(namespace.scaffold_sizes)
            parser.remove_argument("scaffold_sizes")

            namespace.estimates = f"{module_root}/resources/data/mMyoMyo.estimates.tsv"
            namespace.estimates = argparse.FileType("r")(namespace.estimates)
            parser.remove_argument("estimates")

            setattr(namespace, self.dest, True)

    prog = os.path.basename(sys.argv[0])
    if prog == "__main__.py":
        prog = f"{sys.executable} -m napari_kics.analysis_plots"

    parser = ArgumentParser(
        prog=prog,
        description=(
            "Generate plots that allow comparing chromosome"
            " size estimates and actual scaffold sizes in a meaningful manner."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        "--by-name",
        action="store_true",
        help="Match sizes by names",
    )
    parser.add_argument(
        "--example",
        action=LoadExampleAction,
        nargs=0,
        help="Load example data",
    )
    parser.add_argument(
        "--plotlib",
        "-l",
        choices=["pyqtgraph", "matplotlib"],
        default="pyqtgraph",
        help="Plotting library to use.",
    )
    parser.add_argument(
        "--unmatched-penalty",
        "-p",
        type=float,
        default=2.0,
        help="Penalty multiplier for unmatched scaffolds.",
    )
    parser.add_argument(
        "--min-scaffold-size",
        "-m",
        type=int,
        default=100_000,
        help="Minimum size of a scaffold to be included.",
    )
    parser.add_argument(
        "--max-scaffolds",
        "-M",
        type=int,
        default=50,
        metavar="NUM",
        help="Take only the NUM largest scaffolds into account.",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help=(
            "Do not run optimization in matching, i.e. match by independent sort order"
        ),
    )

    return parser


def read_fasta_index(fai_file):
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


def read_tsv_data(tsv_file, name=None):
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

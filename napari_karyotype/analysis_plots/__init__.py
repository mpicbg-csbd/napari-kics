import numpy as np
import pandas as pd
from pulp import GLPK, LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable
from importlib import import_module

from logging import basicConfig, getLogger

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
    scaffold_sizes, estimates, *, unmatched_penalty=2.0, plotlib="pyqtgraph"
):
    scaffold_sizes = pd.Series(scaffold_sizes)
    scaffold_sizes.sort_values(ascending=False, inplace=True)
    estimates = pd.Series(estimates)
    estimates.sort_values(ascending=False, inplace=True)

    # matching = []
    matching = find_optimal_assignment(
        estimates, scaffold_sizes, unmatched_penalty=unmatched_penalty
    )

    if "." in plotlib:
        raise ValueError("plotlib must not contain dots ('.')")

    try:
        plot_backend = import_module(f".backends.{plotlib}", package=__name__)
    except ModuleNotFoundError:
        raise ValueError(f"Unrecognized plotlib: {plotlib}")

    plot_backend.do_plot(estimates, scaffold_sizes, matching)


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

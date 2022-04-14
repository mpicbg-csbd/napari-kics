import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from logging import basicConfig, getLogger

log = getLogger(__name__)


def do_plot(estimates, scaffold_sizes, matching, **kwargs):
    log.warning("this backend is currently not maintained")

    matplotlib.use("qt5agg")

    estimates = pd.Series(estimates).values
    scaffold_sizes = pd.Series(scaffold_sizes).values

    fig = plt.figure(constrained_layout=False)

    matrix_ax, pairs_ax = fig.subplots(2, 1, gridspec_kw={"height_ratios": [3, 1]})

    diffs = np.abs(np.atleast_2d(estimates).T - scaffold_sizes)
    aximg = matrix_ax.imshow(diffs[:, : len(estimates)], cmap="magma", norm=LogNorm())
    matrix_ax.axline((0, 0), slope=1, color="grey", ls=":")
    fig.colorbar(aximg, ax=matrix_ax)
    if len(matching) > 0:
        matrix_ax.scatter(matching[:, 1], matching[:, 0], marker=".", color="w")

        unmatched_estimates = set(range(len(estimates))) - set(matching[:, 0])
        unmatched_scaffolds = set(range(len(scaffold_sizes))) - set(matching[:, 1])

        for y in unmatched_estimates:
            matrix_ax.axhline(y, color="gray", ls="--")
        for x in unmatched_scaffolds:
            if x < len(estimates):
                matrix_ax.axvline(x, color="gray", ls="--")
    matrix_ax.set_xlabel("scaffs")
    matrix_ax.set_ylabel("estimates")

    if len(matching) > 0:
        bar_width = 0.35
        chr_locations = np.arange(estimates.shape[0])
        pairs_ax.bar(
            chr_locations - bar_width / 2, estimates, bar_width, label="estimates"
        )
        pairs_ax.bar(
            matching[:, 0] + bar_width / 2,
            scaffold_sizes[matching[:, 1]],
            bar_width,
            label="scaffold_sizes",
        )
        if False:
            pairs_ax.scatter(
                matching[:, 0],
                scaffold_sizes[matching[:, 1]]
                + scaffold_sizes[matching[:, 1].max() + 1],
                label="scaffold_sizes + largest_free_scaff",
                marker="+",
            )
    pairs_ax.set_yscale("log")
    pairs_ax.set_ylabel("size")
    pairs_ax.legend()

    plt.show()

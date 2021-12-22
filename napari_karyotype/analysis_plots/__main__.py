#!/usr/bin/env python3

# pylint: disable=missing-class-docstring,missing-function-docstring,no-else-return,no-else-break

import pdb  # pylint: disable=unused-import
import sys
from pulp import GLPK, LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable
import numpy as np
import pandas as pd
from importlib import import_module
from napari_karyotype.analysis_plots import *
import logging

log = logging.getLogger(__name__)


def main():
    args = _parse_args()

    if args.scaffold_sizes.name.endswith(".fai"):
        scaffold_sizes = read_fasta_index(args.scaffold_sizes)
    else:
        scaffold_sizes = read_tsv_data(args.scaffold_sizes, name="scaffold_sizes")

    estimates = read_tsv_data(args.estimates, "chromosome_estimates")

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
        prog = "python -m napari_karyotype.analysis_plots"

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
    logging.basicConfig()
    main()

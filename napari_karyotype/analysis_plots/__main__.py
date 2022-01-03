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
        unmatched_penalty=args.unmatched_penalty,
        plotlib=args.plotlib,
    )


def _parse_args(args=sys.argv[1:]):
    import argparse
    import os

    class ArgumentParser(argparse.ArgumentParser):
        def remove_argument(self, dest):
            self._actions = [action for action in self._actions if action.dest != dest]

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

    prog = sys.argv[0]
    if prog == "__main__":
        prog = "python -m napari_karyotype.analysis_plots"

    parser = ArgumentParser(
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
        help="Plotting library to use (default: {default})",
    )
    parser.add_argument(
        "--unmatched-penalty",
        "-p",
        type=float,
        default=2.0,
        help="Penalty multiplier for unmatched scaffolds (default: {default})",
    )

    return parser.parse_args(args)


if __name__ == "__main__":
    logging.basicConfig()
    main()

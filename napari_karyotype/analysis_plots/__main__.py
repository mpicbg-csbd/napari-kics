#!/usr/bin/env python3

# pylint: disable=missing-class-docstring,missing-function-docstring,no-else-return,no-else-break

import pdb  # pylint: disable=unused-import
import sys
import os.path
from pulp import GLPK, LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable
import numpy as np
import pandas as pd
from importlib import import_module
from napari_karyotype.analysis_plots import *
import logging

log = logging.getLogger(__name__)


def main():
    logging.basicConfig()
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
        min_scaffold_size=args.min_scaffold_size,
        max_scaffolds=args.max_scaffolds,
        plotlib=args.plotlib,
    )


def _parse_args():
    parser = get_argument_parser()
    args = sys.argv[1:]

    return parser.parse_args(args)


if __name__ == "__main__":
    main()

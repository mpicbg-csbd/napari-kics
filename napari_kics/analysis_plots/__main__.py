#!/usr/bin/env python3

import logging
import sys

from ..analysis_plots import (
    analysis_plots,
    get_argument_parser,
    read_fasta_index,
    read_tsv_data,
)

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
        by_name=args.by_name,
        no_optimize=args.no_optimize,
        plotlib=args.plotlib,
    )


def _parse_args():
    parser = get_argument_parser()
    args = sys.argv[1:]

    return parser.parse_args(args)


if __name__ == "__main__":
    main()

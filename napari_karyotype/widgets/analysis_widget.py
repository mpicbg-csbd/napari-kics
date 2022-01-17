from skimage import io
import numpy as np
import pandas as pd
import math
import sys

from napari_karyotype.analysis_plots import (
    analysis_plots,
    get_argument_parser,
    read_fasta_index,
    read_tsv_data,
)
from napari_karyotype.utils import ChromosomeLabel
from napari_karyotype.widgets import ClickableLineEdit
from ..global_signals import signals
from pathlib import Path
from qtpy.QtWidgets import (
    QVBoxLayout,
    QFormLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
)


class AnalysisWidget(QVBoxLayout):
    def __init__(self, viewer, table):
        super().__init__()

        self.viewer = viewer
        self.table = table

        self.compare_options_layout = QFormLayout()
        self.cmp_arg_parser = get_argument_parser()

        self.scaffold_sizes_path_line_edit = ClickableLineEdit(
            placeholderText="Select scaffold sizes file (*.fai *.tsv)",
            mode="openFile",
            filter="Tabular data (*.fai *.tsv)",
        )
        self.scaffold_sizes_path_line_edit.sigAccepted.connect(
            lambda p: self.read_scaffold_sizes(p)
        )
        signals().sampleLoaded.connect(lambda p: self.set_sample_data(p))

        self.add_cmp_option("scaffold_sizes", widget=self.scaffold_sizes_path_line_edit)
        self.add_cmp_option("unmatched_penalty", min=0.0, max=math.inf, step=0.1)
        self.add_cmp_option(
            "min_scaffold_size",
            min=0,
            max=1_000_000_000,
            stepType=QSpinBox.AdaptiveDecimalStepType,
        )
        self.add_cmp_option("max_scaffolds", min=0, max=1_000)

        self.start_comparison_btn = QPushButton("Start comparison")
        self.start_comparison_btn.clicked.connect(lambda x: self.start_comparison())

        self.descr_label = QLabel("6. Compare estimates to scaffold sizes:")

        self.addWidget(self.descr_label)
        self.addLayout(self.compare_options_layout)
        self.addWidget(self.start_comparison_btn)
        self.setSpacing(5)

    def add_cmp_option(
        self,
        prop,
        min=None,
        max=None,
        step=None,
        stepType=None,
        label=None,
        widget=None,
    ):
        arg_action = self.cmp_arg_parser[prop]

        if widget is None:
            if arg_action.type == int:
                widget = QSpinBox()
            elif arg_action.type == float:
                widget = QDoubleSpinBox()
            else:
                raise ValueError(f"unsupported type: {arg_action.type}")

        if min is not None:
            widget.setMinimum(min)
        if max is not None:
            widget.setMaximum(max)
        if arg_action.default is not None:
            widget.setValue(arg_action.default)
        if step is not None:
            widget.setSingleStep(step)
        if stepType is not None:
            widget.setStepType(stepType)
        if label is None:
            label = prop.replace("_", " ").capitalize() + ":"

        self.compare_options_layout.addRow(label, widget)

        tooltip = arg_action.help
        widget.setToolTip(tooltip)
        label = self.compare_options_layout.labelForField(widget)
        label.setToolTip(tooltip)

    def set_sample_data(self, data_base):
        fasta_index = f"{data_base}.fasta.fai"

        self.scaffold_sizes_path_line_edit.setText(fasta_index)
        self.read_scaffold_sizes(f"{data_base}.fasta.fai")

    def read_scaffold_sizes(self, scaffold_sizes):
        if scaffold_sizes is None or len(scaffold_sizes) == 0:
            return

        if scaffold_sizes.endswith(".fai"):
            self.scaffold_sizes = read_fasta_index(scaffold_sizes)
        else:
            self.scaffold_sizes = read_tsv_data(scaffold_sizes, name="scaffold_sizes")

    def start_comparison(self):
        if not self.table.isEnabled():
            raise Exception("Complete the above steps before comparison.")

        self.estimates = self.table.model().dataframe["area"][1:]
        self.estimates.index = self.table.model().dataframe["label"][1:]
        print(self.estimates)

        mean_estimates = dict()
        for chr_label, estimate in self.estimates.items():
            key = (
                chr_label.major if isinstance(chr_label, ChromosomeLabel) else chr_label
            )
            current = mean_estimates.get(key, (0, 0))
            mean_estimates[key] = (
                current[0] + estimate,
                current[1] + 1,
            )
        for key, (est_sum, est_count) in mean_estimates.items():
            mean_estimates[key] = est_sum / est_count

        self.estimates = pd.Series(mean_estimates, name="chromosome_estimates")
        print(mean_estimates)
        print(self.estimates)
        self.estimates /= sum(self.estimates)
        self.estimates *= sum(self.scaffold_sizes)

        self.analysis_result = analysis_plots(
            self.scaffold_sizes,
            self.estimates,
            min_scaffold_size=10_000,
            max_scaffolds=2 * len(self.estimates),
        )

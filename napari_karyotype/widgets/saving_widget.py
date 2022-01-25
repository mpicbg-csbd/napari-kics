from skimage import io
import pandas as pd

from napari_karyotype.widgets import ClickableLineEdit
from napari_karyotype.utils.export_annotated_karyotype import export_svg
from pathlib import Path
from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel
from napari.utils import progress


class SavingWidget(QVBoxLayout):
    def __init__(self, viewer, table, analysis_widget):
        super().__init__()

        self.viewer = viewer
        self.table = table
        self.analysis_widget = analysis_widget

        self.save_path_line_edit = ClickableLineEdit(
            placeholderText="Select output directory", mode="directory"
        )

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.onClick)

        self.descr_label = QLabel("6. Save results to the the following directory:")

        self.addWidget(self.descr_label)
        self.addWidget(self.save_path_line_edit)
        self.addWidget(self.save_btn)
        self.setSpacing(5)

    def onClick(self, event):
        if (
            len(self.save_path_line_edit.text()) > 0
            or self.save_path_line_edit.showDialog()
        ):
            self.save_output(self.save_path_line_edit.text())

    def save_output(self, path):
        if len(path) == 0:
            path = "."

        for method in progress(
            (
                "_save_images",
                "_save_table",
                "_save_matching",
                "_save_screenshot",
                "_save_annotated_karyotype",
            )
        ):
            getattr(self, method)(path)

    def _save_images(self, path):
        for name in ("blurred", "thresholded", "labelled"):
            if name in self.viewer.layers:
                img = self.viewer.layers[name].data
                io.imsave(f"{path}/{name}.png", img)

        if "labelled" in self.viewer.layers:
            io.imsave(
                f"{path}/labelled_color.png",
                self.viewer.layers["labelled"].get_color(
                    list(self.viewer.layers["labelled"].data)
                ),
            )

    def _save_table(self, path):
        if self.table.isEnabled():
            table = pd.DataFrame()
            table["tag"] = self.table.model().dataframe["label"].to_list()
            table["label"] = self.table.model().dataframe.index.to_list()
            table["area"] = self.table.model().dataframe["area"].to_list()
            table["size"] = self.table.model().dataframe["size"].to_list()

            table.to_csv(f"{path}/data.csv", index=False)

    def _save_matching(self, path):
        if hasattr(self.analysis_widget, "analysis_result") and hasattr(
            self.analysis_widget.analysis_result, "matching"
        ):
            self.analysis_widget.analysis_result.matching.to_csv(
                f"{path}/matching.csv", index=False
            )

    def _save_screenshot(self, path):
        self.viewer.screenshot(f"{path}/screenshot.png")

    def _save_annotated_karyotype(self, path):
        if self.table.isEnabled():
            table = self.table.model()
            nrows = table.rowCount()
            label_col = table.columns.get_loc("label")
            size_col = table.columns.get_loc("size")
            anno_tags = [table.data(row=i, column=label_col) for i in range(nrows)]
            anno_sizes = [table.data(row=i, column=size_col) for i in range(nrows)]
            anno_bboxes = table.dataframe["_bbox"].to_list()

            export_svg(
                f"{path}/annotated.svg",
                karyotype=self.viewer.layers[0].data,
                tags=anno_tags,
                sizes=anno_sizes,
                bboxes=anno_bboxes,
            )

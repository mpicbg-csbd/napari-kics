import pandas as pd
from napari.utils import progress
from qtpy.QtWidgets import QLabel, QPushButton, QVBoxLayout
from skimage import io

from ..utils.export_annotated_karyotype import export_svg
from ..widgets import ClickableLineEdit


class SavingWidget(QVBoxLayout):
    def __init__(self, viewer, table, analysis_widget, preprocessing_widget):
        super().__init__()

        self.viewer = viewer
        self.table = table
        self.analysis_widget = analysis_widget
        self.preprocessing_widget = preprocessing_widget

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
                "_save_params",
                "_save_table",
                "_save_matching",
                "_save_screenshot",
                "_save_annotated_karyotype",
            )
        ):
            getattr(self, method)(path)

    def _save_images(self, path):
        for name in ("inverted", "blurred", "thresholded", "labelled"):
            if name in self.viewer.layers:
                layer = self.viewer.layers[name]
                img = layer.data
                if name == "labelled":
                    # save exact labels
                    io.imsave(f"{path}/{name}.tiff", img, check_contrast=False)
                    # save visual labels
                    io.imsave(f"{path}/{name}_color.png", layer.get_color(list(img)))
                else:
                    io.imsave(f"{path}/{name}.png", img)

    def _save_params(self, path):
        params = pd.Series(
            {
                "invert_image": self.preprocessing_widget.invert_image(),
                "threshold": self.preprocessing_widget.threshold(),
                "blur": self.preprocessing_widget.sigma(),
                "genome_size": self.table.model().genomeSize,
            }
        )

        params.to_csv(f"{path}/params.csv", header=False)

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

from skimage import io
import pandas as pd

from napari_karyotype.widgets import ClickableLineEdit
from napari_karyotype.utils.export_annotated_karyotype import export_svg
from pathlib import Path
from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel


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
        self.save_btn.clicked.connect(
            lambda x: print(f"path is {self.save_path_line_edit.text()}")
        )

        self.save_btn.clicked.connect(
            lambda e: self.save_output(self.save_path_line_edit.text())
        )

        self.descr_label = QLabel("7. Save results to the the following directory:")

        self.addWidget(self.descr_label)
        self.addWidget(self.save_path_line_edit)
        self.addWidget(self.save_btn)
        self.setSpacing(5)

    def save_output(self, path):
        if len(path) == 0:
            path = "."

        self._save_images(path)
        self._save_table(path)
        self._save_matching(path)
        self._save_screenshot(path)
        self._save_annotated_karyotype(path)

    def _save_images(self, path):
        for name in ("blurred", "thresholded", "labelled"):
            img = self.viewer.layers[name].data
            io.imsave(f"{path}/{name}.png", img)
        io.imsave(
            f"{path}/labelled_color.png",
            self.viewer.layers["labelled"].get_color(
                list(self.viewer.layers["labelled"].data)
            ),
        )

    def _save_table(self, path):
        table = pd.DataFrame()
        table["tags"] = list(self.table.model().dataframe["label"])
        table["labels"] = list(self.table.model().dataframe.index)
        table["area"] = list(self.table.model().dataframe["area"])
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
        anno_tags = self.table.model().dataframe["label"].to_list()
        anno_sizes = self.table.model().dataframe["area"].to_list()
        anno_bboxes = self.table.model().dataframe["_bbox"].to_list()

        # do not annotate background
        bg_index = self.table.model().dataframe.index.to_list().index(0)
        del anno_tags[bg_index]
        del anno_sizes[bg_index]
        del anno_bboxes[bg_index]

        export_svg(
            f"{path}/annotated.svg",
            karyotype=self.viewer.layers[0].data,
            tags=anno_tags,
            sizes=anno_sizes,
            bboxes=anno_bboxes,
        )

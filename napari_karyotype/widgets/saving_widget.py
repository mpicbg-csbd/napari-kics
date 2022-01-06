from skimage import io
import pandas as pd

from napari_karyotype.widgets import ClickableLineEdit
from pathlib import Path
from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel


class SavingWidget(QVBoxLayout):
    def __init__(self, viewer, table):
        super().__init__()

        self.viewer = viewer
        self.table = table

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
        # images

        imgs_dict = self.get_imgs_dict()
        [io.imsave(f"{path}/{name}.png", img) for (name, img) in imgs_dict.items()]

        # dataframe
        dataframe = pd.DataFrame()
        dataframe["tags"] = list(self.table.model().dataframe["label"])
        dataframe["labels"] = list(self.table.model().dataframe.index)
        dataframe["area"] = list(self.table.model().dataframe["area"])
        dataframe.to_csv(f"{path}/data.csv", index=False)

        # screenshot
        self.viewer.screenshot(f"{path}/screenshot.png")

    def get_imgs_dict(self):
        res = {}
        names = [layer.name for layer in self.viewer.layers]
        res["blurred"] = self.viewer.layers[names.index("blurred")].data
        res["thresholded"] = self.viewer.layers[names.index("thresholded")].data
        res["labelled"] = self.viewer.layers[names.index("labelled")].data

        res["labelled_color"] = self.viewer.layers[names.index("labelled")].get_color(
            list(res["labelled"])
        )

        return res

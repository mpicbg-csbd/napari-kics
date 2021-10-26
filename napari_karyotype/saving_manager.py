from skimage import io
import pandas as pd

from qtpy.QtWidgets import QVBoxLayout, QPushButton
from pathlib import Path


class SavingManager(QVBoxLayout):

    def __init__(self, viewer, table):

        super().__init__()

        self.viewer = viewer
        self.table = table

        from napari_karyotype.utils import ClickableLineEdit
        self.save_path_line_edit = ClickableLineEdit(f"{Path(__file__).absolute().parent}/resources/example_output")

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(lambda x: print(f"path is {self.save_path_line_edit.text()}"))

        self.save_btn.clicked.connect(lambda e: self.save_output(self.save_path_line_edit.text()))

        self.addWidget(self.save_path_line_edit)
        self.addWidget(self.save_btn)

    def save_output(self, path):
        # images

        imgs_dict = self.get_imgs_dict()
        [io.imsave(f"{path}/{name}.png", img) for (name, img) in imgs_dict.items()]

        # dataframe
        dataframe = pd.DataFrame()
        dataframe["tags"] = list(self.table.model().dataframe[1])
        dataframe["labels"] = list(self.table.model().dataframe.index)
        dataframe["area"] = list(self.table.model().dataframe[2])
        dataframe.to_csv(f"{path}/data.csv", index=False)

        # screenshot
        self.viewer.screenshot(f"{path}/screenshot.png")

    def get_imgs_dict(self):
        res = {}
        names = [layer.name for layer in self.viewer.layers]
        res[self.input_img_name] = self.viewer.layers[names.index(self.input_img_name)].data
        res["thresholded"] = self.viewer.layers[names.index("thresholded")].data
        res["labelled"] = self.viewer.layers[names.index("labelled")].data

        res["labelled_color"] = self.viewer.layers[names.index("labelled")].get_color(list(res["labelled"]))

        return res

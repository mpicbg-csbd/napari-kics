from qtpy.QtWidgets import *
from qtpy.QtGui import QFont
from qtpy.QtSvg import QSvgWidget
from PyQt5.QtCore import Qt
from qtpy import QtWidgets

import napari, json, os
from napari_karyotype.utils import create_widget

from pathlib import Path
import magicgui

from qtpy import QtCore
import pandas as pd
import numpy as np

# ------------------------------------------------------------------------
# Main pipeline widget
# ------------------------------------------------------------------------
class KaryotypeWidget(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # svg widget
        logo_size = 85
        logoSvgWidget = QSvgWidget(f"{Path(__file__).absolute().parent}/resources/artwork/logo.svg")
        logoSvgWidget.setGeometry(0, 0, logo_size, logo_size)
        logoSvgWidget.setMaximumSize(logo_size, logo_size)
        logoSvgWidget.setMinimumSize(logo_size, logo_size)

        # name and description labels
        name_label = QLabel("Karyotype")
        name_label.setFont(QFont("Palatino", 20))
        description_label = QLabel("relative chromosome size evaluation from the karyotype images.")
        description_label.setFont(QFont("Palatino", 13))

        # text label layout
        label_layout = QVBoxLayout()
        label_layout.addWidget(name_label)
        label_layout.addWidget(description_label)
        label_layout.setAlignment(Qt.AlignVCenter)

        # head layout
        self.head_layout = QHBoxLayout()
        self.head_layout.addWidget(logoSvgWidget)
        self.head_layout.addLayout(label_layout)
        self.head_layout.setAlignment(Qt.AlignBottom)


        # state
        self.state = {}

        self.generate_gui_from_config()


    def generate_gui_from_config(self, config_file_path=f"{Path(__file__).absolute().parent}/resources/config/config.json"):

        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)

            # widgets
            widgets = []

            # ----------------------------------------------------------------------
            # thresholding widget
            # ----------------------------------------------------------------------

            def threshold(input_image, threshold_value=0.5):
                from skimage.color import rgb2gray
                if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                    img = rgb2gray(input_image)
                else:
                    img = input_image
                return ((1 - img) > threshold_value).astype(int)

            threshold_config = {

                "threshold_value": {
                    "widget_type": "FloatSlider",
                    "min": 0.00,
                    "max": 1.00,
                    "step": 0.01,
                    "value": 0.5
                },
                "auto_call": True
            }

            def threshold_updater(img_name, img, viewer):
                # print(f"[update_layer]: updating layers with data of shape {img.shape} and name {img_name}")
                try:
                    viewer.layers[img_name].data = img
                except KeyError:
                    viewer.add_image(img, name=img_name, opacity=0.7, colormap="red")
                    viewer.layers.select_previous()

            def threshold_wrapper(threshold_value=0.5):
                input_image = self.viewer.layers.selection.active.data
                thresholded = threshold(input_image, threshold_value)
                threshold_updater("thresholded", thresholded, self.viewer)

            # ----------------------------------------------------------------------
            # thresholding widget
            # ----------------------------------------------------------------------

            def label(input_image):
                from scipy.ndimage import label
                return label(input_image)[0]

            label_config = {
                "call_button": "Label"
            }

            def labelled_updater(img_name, img, viewer):
                # print(f"[update_layer]: updating layers with data of shape {img.shape} and name {img_name}")
                try:
                    viewer.layers[img_name].data = img
                except KeyError:
                    viewer.add_labels(img, name=img_name)


            def label_wrapper():
                input_image = self.viewer.layers.selection.active.data
                labelled_img = label(input_image).astype(int)
                labelled_updater("labelled", labelled_img, self.viewer)


            widgets.append(magicgui.magicgui(threshold_wrapper, **threshold_config).native)
            widgets.append(magicgui.magicgui(label_wrapper, **label_config).native)

            self.curr = 0

            self.layout.addLayout(self.head_layout)
            self.layout.addSpacing(10)
            [self.layout.addWidget(widget) for widget in widgets]

            self.layout.setAlignment(Qt.AlignTop)

            # ----------------------------------------------------------------------
            # table widget
            # ----------------------------------------------------------------------



            self.table = QtWidgets.QTableView()
            # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.table.clicked.connect(lambda e: print(f"selection changed to {e.row()}"))

            def change_handler():
                pass

            self.table.clicked.connect(change_handler)

            self.generate_table_btn = QtWidgets.QPushButton("Generate Table")

            self.summary_frame = pd.DataFrame()

            def generate_new_model():
                label_layer = self.viewer.layers.selection.active
                labels = np.unique(label_layer.data)
                
                l = [(f"{ind}", labels[ind], label_layer.get_color(labels[ind])) for ind in range(len(labels))]
                frame = pd.DataFrame(l)
                self.table.setModel(MyTableModel(frame))

            def foo():
                print("foo")

            self.generate_table_btn.clicked.connect(foo)
            # self.table.setModel(MyTableModel(loop_data))

            self.layout.addWidget(self.generate_table_btn)
            self.layout.addWidget(self.table)
            self.generate_table_btn.clicked.connect(generate_new_model)






class MyTableModel(QtCore.QAbstractTableModel):

    def __init__(self, pandas_dataframe):
        super().__init__()

        self.dataframe = pandas_dataframe


    def rowCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[1]

    def data(self, QModelIndex, role=None):

        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        return str(self.dataframe.iloc[QModelIndex.row()][QModelIndex.column()])

    def headerData(self, p_int, Qt_Orientation, role=None):

        if role == QtCore.Qt.DisplayRole:
            if Qt_Orientation == QtCore.Qt.Horizontal:
                return self.dataframe.columns[p_int]
            else:
                return p_int
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
from qtpy.QtGui import QColor

from napari.qt import thread_worker
from copy import deepcopy
from napari_karyotype.utils import get_img
from napari_karyotype.table_model import PandasTableModel
from napari_karyotype.label_manager import LabelManager
from napari_karyotype.order_manager import OrderManager
from napari_karyotype.annotation_manager import AnnotationManager
from napari_karyotype.saving_manager import SavingManager

from napari_karyotype.head_layout import HeadLayout


# ------------------------------------------------------------------------
# Main pipeline widget
# ------------------------------------------------------------------------
class KaryotypeWidget(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.head_layout = HeadLayout()

        # ----------------------------------------------------------------------
        # 1. Blur step
        # ----------------------------------------------------------------------

        # actual function
        def blur(input_image, sigma=1.0):

            from skimage.color import rgb2gray
            if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                img = rgb2gray(input_image)
            else:
                img = input_image

            from skimage.filters import gaussian
            return gaussian(img, sigma)

        def blur_wrapper(sigma):

            input_image = self.viewer.layers.selection.active.data
            self.input_img_name = self.viewer.layers.selection.active.name
            print(f"[blur_wrapper]: input img name is {self.input_img_name}")
            blurred = blur(input_image, sigma)

            try:
                self.viewer.layers["blurred"].data = blurred
            except KeyError:
                self.viewer.add_image(blurred, name="blurred")
            self.viewer.layers.select_previous()

        # blur step description label
        blur_descr_label = QLabel(
            "1. Select the appropriate sigma value to denoise the image with a Gaussian blur:")

        # blur slider label
        blur_sl_label = QLabel("sigma:")

        # sigma slider
        sigma_slider = QSlider(Qt.Horizontal)
        sigma_slider.setMinimum(0)
        sigma_slider.setMaximum(100)
        sigma_slider.setSingleStep(1)
        sigma_slider.setTickInterval(20)
        sigma_slider.setTickPosition(QSlider.TicksBelow)
        sigma_slider.setValue(50)
        sigma_slider.setFixedWidth(400)

        # sigma slider value
        sigma_sl_val = QLabel(f"{sigma_slider.value() / 20:0.2f}")
        sigma_slider.valueChanged.connect(lambda e: sigma_sl_val.setText(f"{sigma_slider.value() / 20:0.2f}"))
        sigma_slider.valueChanged.connect(lambda e: blur_wrapper(sigma_slider.value() / 20))

        # threshold box
        blur_box_ = QHBoxLayout()
        blur_box_.addWidget(blur_sl_label)
        blur_box_.addWidget(sigma_slider)
        blur_box_.addWidget(sigma_sl_val)
        blur_box_.setSpacing(0)
        blur_box_.setContentsMargins(0, 0, 0, 0)

        blur_box = QVBoxLayout()
        blur_box.addWidget(blur_descr_label)
        blur_box.addLayout(blur_box_)
        blur_box.setSpacing(5)

        # ----------------------------------------------------------------------
        # 2. Thresholding step
        # ----------------------------------------------------------------------

        # the actual function
        def threshold(input_image, threshold_value=0.5):

            from skimage.color import rgb2gray
            if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                img = rgb2gray(input_image)
            else:
                img = input_image

            return ((1 - img) > threshold_value).astype(int)

        # wrapper with napari updates
        def threshold_wrapper(threshold_value=0.5):
            input_image = get_img("blurred", self.viewer).data

            print(f"[threshold_wrapper]: input img name is {self.input_img_name}")
            thresholded = threshold(input_image, threshold_value)
            # threshold_updater("thresholded", thresholded, self.viewer)
            try:
                self.viewer.layers["thresholded"].data = thresholded
            except KeyError:
                self.viewer.add_image(thresholded, name="thresholded", opacity=0.7, colormap="red")

        # thresholding step description label
        th_descr_label = QLabel("2. Select the appropriate threshold value to segment the image.")

        # threshold slider label
        th_sl_label = QLabel("th_val:")

        # threshold slider
        threshold_slider = QSlider(Qt.Horizontal)
        threshold_slider.setMinimum(0)
        threshold_slider.setMaximum(100)
        threshold_slider.setSingleStep(1)
        threshold_slider.setTickInterval(20)
        threshold_slider.setTickPosition(QSlider.TicksBelow)
        threshold_slider.setValue(50)
        threshold_slider.setFixedWidth(400)

        # threshold slider value
        th_sl_val = QLabel(f"{threshold_slider.value() / 100:0.2f}")
        threshold_slider.valueChanged.connect(lambda e: th_sl_val.setText(f"{threshold_slider.value() / 100:0.2f}"))
        threshold_slider.valueChanged.connect(lambda e: threshold_wrapper(threshold_slider.value() / 100))

        # threshold box
        threshold_box_ = QHBoxLayout()
        threshold_box_.addWidget(th_sl_label)
        threshold_box_.addWidget(threshold_slider)
        threshold_box_.addWidget(th_sl_val)
        threshold_box = QVBoxLayout()
        threshold_box.addWidget(th_descr_label)
        threshold_box.addLayout(threshold_box_)
        threshold_box.setSpacing(5)

        # ----------------------------------------------------------------------
        # 3. Labeling step
        # ----------------------------------------------------------------------

        # the actual function
        def label(img):
            from scipy.ndimage import label
            return label(img)[0]

        # wrapper with napari updates
        def label_wrapper():

            input_image = get_img("thresholded", self.viewer).data
            labelled = label(input_image)

            try:
                self.viewer.layers["labelled"].data = labelled
            except KeyError:
                self.viewer.add_labels(labelled, name="labelled", opacity=0.7)

        labeling_descr_label = QLabel(
            "3. Apply label function to assign a unique integer id to each connected component:")
        label_btn = QPushButton("Label")
        label_btn.clicked.connect(lambda e: label_wrapper())

        label_box = QVBoxLayout()
        label_box.addWidget(labeling_descr_label)
        label_box.addWidget(label_btn)
        label_box.setSpacing(5)

        self.layout.addLayout(self.head_layout)
        self.layout.addLayout(blur_box)
        self.layout.addLayout(threshold_box)
        self.layout.addLayout(label_box)

        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(20)

        # ----------------------------------------------------------------------
        # table widget
        # ----------------------------------------------------------------------

        self.table = QtWidgets.QTableView()
        self.table.setSortingEnabled(True)
        # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        def delete_label(viewer):

            indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
            coords = [np.where(self.label_layer.data == label) for label in
                      self.table.model().dataframe.index[indices]]
            coords_to_fill = [(co[0][0], co[1][0]) for co in coords]

            print(f"[backspace]: removing indices {indices}")

            [self.label_layer.fill(coord, 0) for coord in coords_to_fill]

        self.viewer.bind_key("Backspace", delete_label)

        self.generate_table_btn = QtWidgets.QPushButton("Generate Table")

        self.label_layer = None

        self.history_queue_length = 0
        self.history_last_step_length = 0

        self.label_manager = None

        def upd_table_new():

            res_dict = self.label_manager.process_history_step()

            print(f"res_dict is {res_dict}")

            for (label, increment) in res_dict.items():

                if not (label in self.table.model().dataframe.index):
                    print(f"label {label} is not in the dataframe")
                    self.table.model().dataframe = self.table.model().dataframe.append(
                        pd.DataFrame([["", label, increment]], index=[label]))
                    print(f"now it is \n{self.table.model().dataframe}")

                else:
                    self.table.model().dataframe.loc[label, 2] += increment

                    if (self.table.model().dataframe.loc[label, 2] == 0):
                        self.table.model().dataframe.drop(label, inplace=True)
                        print(f"label {label} is set to 0")
                self.table.update()
                self.table.sortByColumn(2, Qt.DescendingOrder)

        def initialize_table(label_layer):

            from skimage.measure import regionprops
            rp = regionprops(label_layer.data + 1)

            res = np.array([(r.label - 1, r.area, r.coords[0]) for r in rp], dtype=object)
            res = np.array(sorted(res, key=lambda x: x[0]))
            l = [("", res[ind, 0], res[ind, 1]) for ind in range(len(res))]

            frame = pd.DataFrame(l)
            self.table.setModel(PandasTableModel(frame, label_layer.get_color))
            self.table.sortByColumn(2, Qt.DescendingOrder)

        order_button = QPushButton("Adjust labelling order")
        order_button.setCheckable(True)

        annotate_btn = QPushButton("Annotate")

        from napari_karyotype.utils import ClickableLineEdit
        save_path_line_edit = ClickableLineEdit(f"{Path(__file__).absolute().parent}/resources/example_output")

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda x: print(f"path is {save_path_line_edit.text()}"))

        def generate_new_model():

            self.label_layer = self.viewer.layers.selection.active
            initialize_table(get_img("labelled", self.viewer))
            self.label_manager = LabelManager(get_img("labelled", self.viewer))
            self.label_layer.events.set_data.connect(lambda x: upd_table_new())

            def sync_selection_table2viewer(e):
                indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
                self.label_layer.selected_label = self.table.model().dataframe.index[indices[0]]

            self.table.clicked.connect(sync_selection_table2viewer)

            def sync_selection_viewer2table(e):
                sl = self.label_layer.selected_label
                ind = self.table.model().dataframe.index.get_loc(sl)
                self.table.selectRow(ind)

            self.label_layer.events.selected_label.connect(sync_selection_viewer2table)

            order_button.clicked.connect(lambda e: order_button.setDown(order_button.isChecked()))
            order_manager = OrderManager(self.viewer, self.label_layer, self.table)

            def toggle_ordering_mode(flag):
                if flag:
                    order_manager.activate_ordering_mode()
                else:
                    order_manager.deactivate_ordering_mode()

            order_button.clicked.connect(lambda e: toggle_ordering_mode(order_button.isChecked()))

            # -------------------------------------------------------
            # annotation
            # -------------------------------------------------------

            annotation_manager = AnnotationManager(self.viewer, self.label_layer)
            annotate_btn.clicked.connect(annotation_manager.annotate)

            # -------------------------------------------------------
            # saving
            # -------------------------------------------------------

            saving_manager = SavingManager(self.viewer, self.table)
            save_btn.clicked.connect(lambda e: saving_manager.save_output(save_path_line_edit.text()))

        # -------------------------------------------------------
        # adding widgets to the global layout
        # -------------------------------------------------------
        self.layout.addWidget(self.generate_table_btn)

        self.layout.addWidget(order_button)
        self.layout.addWidget(annotate_btn)
        self.layout.addWidget(save_path_line_edit)
        self.layout.addWidget(save_btn)
        self.layout.addWidget(self.table)

        self.generate_table_btn.clicked.connect(generate_new_model)

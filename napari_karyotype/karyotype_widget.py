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
from napari_karyotype.BlurWidget import BlurWidget
from napari_karyotype.table_widget import LabelWidget


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

        self.blur_widget = BlurWidget(self.viewer)

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
        # table widget
        # ----------------------------------------------------------------------

        self.label_widget = LabelWidget(self.viewer)
        self.order_manager = OrderManager(self.viewer, self.label_widget.table)
        self.annotation_manager = AnnotationManager(self.viewer)
        self.saving_manager = SavingManager(self.viewer, self.label_widget.table)


        # -------------------------------------------------------
        # adding widgets to the global layout
        # -------------------------------------------------------
        self.layout.addLayout(self.head_layout)
        self.layout.addLayout(self.blur_widget)
        self.layout.addLayout(threshold_box)
        self.layout.addLayout(self.label_widget)
        self.layout.addLayout(self.order_manager)
        self.layout.addLayout(self.annotation_manager)
        self.layout.addLayout(self.saving_manager)


        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(20)


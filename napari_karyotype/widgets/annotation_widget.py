import numpy as np
from skimage.measure import regionprops

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel, QSpinBox, QHBoxLayout, QDial
from napari_karyotype.utils import get_img
from qtpy.QtCore import Qt


class AnnotationWidget(QVBoxLayout):
    def __init__(self, parent, viewer, table):
        super().__init__()
        self.parent = parent
        self.viewer = viewer
        self.table = table

        # text size
        self.text_size_label = QLabel("Text size: ")
        self.text_size_spinner = QSpinBox()
        self.text_size_spinner.setRange(1, 20)
        self.text_size_spinner.setValue(5)
        self.text_size_hbox = QHBoxLayout()
        self.text_size_hbox.addWidget(self.text_size_label)
        self.text_size_hbox.addWidget(self.text_size_spinner)
        self.text_size_spinner.valueChanged.connect(
            lambda value: setattr(get_img("annotations", self.viewer).text, "size", value)
        )
        self.text_size_hbox.setAlignment(Qt.AlignLeft)

        # text rotation
        self.text_rotation_label = QLabel("Text rotation: ")
        self.text_rotation_dial = QDial()
        self.text_rotation_dial.setRange(0,360)
        self.text_rotation_dial.setValue(0)
        self.text_rotation_dial.valueChanged.connect(
            lambda value: setattr(get_img("annotations", self.viewer).text, "rotation", value)
        )
        self.text_rotation_hbox = QHBoxLayout()
        self.text_rotation_hbox.addWidget(self.text_rotation_label)
        self.text_rotation_hbox.addWidget(self.text_rotation_dial)
        self.text_rotation_hbox.setAlignment(Qt.AlignLeft)

        self.annotate_btn = QPushButton("Annotate")
        self.annotate_btn.clicked.connect(lambda _: self.parent.annotate())

        self.descr_label = QLabel(
            "4. Annotate the image with bounding boxes and areas:"
        )
        self.addWidget(self.descr_label)
        self.addLayout(self.text_size_hbox)
        self.addLayout(self.text_rotation_hbox)
        self.addWidget(self.annotate_btn)
        self.setSpacing(5)

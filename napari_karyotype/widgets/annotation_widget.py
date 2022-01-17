import numpy as np
from skimage.measure import regionprops

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel
from napari_karyotype.utils import get_img


class AnnotationWidget(QVBoxLayout):
    def __init__(self, parent, viewer, table):
        super().__init__()
        self.parent = parent
        self.viewer = viewer
        self.table = table

        self.annotate_btn = QPushButton("Annotate")
        self.annotate_btn.clicked.connect(lambda _: self.parent.annotate())

        self.descr_label = QLabel(
            "5. Annotate the image with bounding boxes and areas:"
        )
        self.addWidget(self.descr_label)
        self.addWidget(self.annotate_btn)
        self.setSpacing(5)

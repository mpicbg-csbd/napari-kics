from PyQt5.QtCore import Qt
from qtpy.QtWidgets import *

from napari_karyotype.annotation_widget import AnnotationWidget
from napari_karyotype.blur_widget import BlurWidget
from napari_karyotype.head_layout import HeadLayout
from napari_karyotype.order_widget import OrderWidget
from napari_karyotype.saving_widget import SavingWidget
from napari_karyotype.label_widget import LabelWidget
from napari_karyotype.threshold_widget import ThresholdWidget


# main widget
class KaryotypeWidget(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        # layout settings
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(20)
        self.setMaximumWidth(550)

        # head
        self.head_layout = HeadLayout()
        self.layout.addLayout(self.head_layout)

        # blur
        self.blur_widget = BlurWidget(self.viewer)
        self.layout.addLayout(self.blur_widget)

        # thresholding
        self.threshold_widget = ThresholdWidget(self.viewer)
        self.layout.addLayout(self.threshold_widget)

        # labelling
        self.label_widget = LabelWidget(self.viewer)
        self.layout.addLayout(self.label_widget)

        # ordering
        self.order_widget = OrderWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.order_widget)

        # annotation
        self.annotation_widget = AnnotationWidget(self.viewer)
        self.layout.addLayout(self.annotation_widget)

        # saving
        self.saving_widget = SavingWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.saving_widget)

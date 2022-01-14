from PyQt5.QtCore import Qt
from qtpy.QtWidgets import *

from .annotation_widget import AnnotationWidget
from .blur_widget import BlurWidget
from .head_layout import HeadLayout
from .label_widget import LabelWidget
from .order_widget import OrderWidget
from .saving_widget import SavingWidget
from .threshold_widget import ThresholdWidget
from .analysis_widget import AnalysisWidget


# main widget
class KaryotypeWidget(QScrollArea):
    def __init__(self, napari_viewer):
        super().__init__()
        # add scroll bars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setWidget(KaryotypeContentWidget(napari_viewer))


class KaryotypeContentWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        # layout settings
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(20)
        self.setMinimumWidth(400)
        self.setMaximumWidth(800)

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
        self.annotation_widget = AnnotationWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.annotation_widget)

        # analysis
        self.analysis_widget = AnalysisWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.analysis_widget)

        # saving
        self.saving_widget = SavingWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.saving_widget)

from PyQt5.QtCore import Qt
from qtpy.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .analysis_widget import AnalysisWidget
from .annotation_widget import AnnotationWidget
from .head_layout import HeadLayout
from .label_widget import LabelWidget
from .order_widget import OrderWidget
from .preprocessing_widget import PreprocessingWidget
from .saving_widget import SavingWidget


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
        self.preprocessing_widget = PreprocessingWidget(self.viewer)
        self.layout.addLayout(self.preprocessing_widget)

        # labelling
        self.label_widget = LabelWidget(
            self.viewer, self.preprocessing_widget.preprocess
        )

        self.layout.addLayout(self.label_widget)

        # ordering
        self.order_widget = OrderWidget(self.viewer, self.label_widget.table)

        self.layout.addLayout(self.order_widget)

        # annotation
        self.annotation_widget = AnnotationWidget(
            self, self.viewer, self.label_widget.table
        )
        self.order_widget.sigOrderChanged.connect(self.annotation_widget.annotate)
        self.label_widget.table.model().sigChange.connect(
            lambda where, old, new: self.annotation_widget.annotate(update_only=True)
        )
        self.layout.addLayout(self.annotation_widget)

        # analysis
        self.analysis_widget = AnalysisWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.analysis_widget)

        # saving
        self.saving_widget = SavingWidget(
            self.viewer,
            self.label_widget.table,
            self.analysis_widget,
            self.preprocessing_widget,
        )
        self.layout.addLayout(self.saving_widget)

        self._console_populated = False
        self.viewer.window.qt_viewer.dockConsole.visibilityChanged.connect(
            self._ensure_populate_console
        )

    def _ensure_populate_console(self):
        if not self._console_populated:
            self.viewer.update_console(
                {
                    "karyotype_widget": self,
                    "karyotype_table": self.label_widget.table.model(),
                }
            )
            self._console_populated = True

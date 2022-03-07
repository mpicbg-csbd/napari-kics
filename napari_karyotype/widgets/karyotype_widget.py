from PyQt5.QtCore import Qt
from qtpy.QtWidgets import *

from .annotation_widget import AnnotationWidget
from .preprocessing_widget import PreprocessingWidget
from .head_layout import HeadLayout
from .label_widget import LabelWidget
from .order_widget import OrderWidget
from .saving_widget import SavingWidget
from .analysis_widget import AnalysisWidget
from ..utils import bbox2shape


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
        self.label_widget.table.model().sigChange.connect(
            lambda where, old, new: self.annotate(update_only=True)
        )
        self.layout.addLayout(self.label_widget)

        # ordering
        self.order_widget = OrderWidget(self.viewer, self.label_widget.table)
        self.order_widget.sigOrderChanged.connect(self.annotate)
        self.layout.addLayout(self.order_widget)

        # annotation
        self.annotation_widget = AnnotationWidget(
            self, self.viewer, self.label_widget.table
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

    def annotate(
        self,
        *,
        update_only=False,
        name="annotations",
        color="red",
        edge_width=2,
        font_size=6,
    ):
        tableModel = self.label_widget.table.model()
        if not tableModel.hasData():
            return

        dataframe = tableModel.dataframe
        nrows = tableModel.rowCount()
        labelCol = dataframe.columns.get_loc("label")
        sizeCol = dataframe.columns.get_loc("size")

        labels = [tableModel.data(row=i, column=labelCol) for i in range(nrows)]
        sizes = [tableModel.data(row=i, column=sizeCol) for i in range(nrows)]
        bboxes = [bbox2shape(b) for b in dataframe.loc[:, "_bbox"]]

        # print(
        #     f"[annotate] bboxes, labels and sizes have lengths {len(bboxes), len(labels), len(sizes)}"
        # )
        # print(f"[annotate] bboxes, labels and sizes are {bboxes, labels, sizes}")

        # https://napari.org/tutorials/applications/annotate_segmentation.html
        properties = {"label": labels, "size": sizes}
        text_parameters = {
            "text": "{label}: {size}",
            "size": font_size,
            "color": color,
            "anchor": "upper_left",
        }

        if name in self.viewer.layers:
            annotation_layer = self.viewer.layers[name]
            annotation_layer.data = bboxes
            annotation_layer.properties = properties
            annotation_layer.refresh()
        elif not update_only:
            self.viewer.add_shapes(
                bboxes,
                name=name,
                face_color="transparent",
                edge_width=edge_width,
                edge_color=color,
                properties=properties,
                text=text_parameters,
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

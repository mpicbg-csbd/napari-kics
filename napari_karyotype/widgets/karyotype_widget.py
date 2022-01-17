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
        self.annotation_widget = AnnotationWidget(
            self, self.viewer, self.label_widget.table
        )
        self.layout.addLayout(self.annotation_widget)

        # analysis
        self.analysis_widget = AnalysisWidget(self.viewer, self.label_widget.table)
        self.layout.addLayout(self.analysis_widget)

        # saving
        self.saving_widget = SavingWidget(
            self.viewer, self.label_widget.table, self.analysis_widget
        )
        self.layout.addLayout(self.saving_widget)

    def annotate(
        self,
        *,
        update_only=False,
        name="annotations",
        color="red",
        edge_width=2,
        font_size=6,
    ):
        table = self.label_widget.table.model().dataframe
        labels = [str(l) for l in table.loc[:, "label"]]
        areas = [str(a) for a in table.loc[:, "area"]]
        bboxes = [bbox2shape(b) for b in table.loc[:, "_bbox"]]

        # do not annotate background
        bg_index = table.index.to_list().index(0)
        del labels[bg_index]
        del areas[bg_index]
        del bboxes[bg_index]

        print(
            f"[annotate] bboxes, labels and areas have lengths {len(bboxes), len(labels), len(areas)}"
        )
        print(f"[annotate] bboxes, labels and areas are {bboxes, labels, areas}")

        # https://napari.org/tutorials/applications/annotate_segmentation.html
        properties = {"label": labels, "area": areas}
        text_parameters = {
            "text": "{label}: {area}",
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

import numpy as np
from skimage.measure import regionprops

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel
from napari_karyotype.utils import get_img


class AnnotationWidget(QVBoxLayout):
    def __init__(self, viewer, table):
        super().__init__()
        self.viewer = viewer
        self.table = table

        self.annotate_btn = QPushButton("Annotate")
        self.annotate_btn.clicked.connect(self.annotate)

        self.descr_label = QLabel(
            "5. Annotate the image with bounding boxes and areas:"
        )
        self.addWidget(self.descr_label)
        self.addWidget(self.annotate_btn)
        self.setSpacing(5)

    def bbox2shape(self, bbox):
        return np.array(
            [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
            ]
        )

    def annotate(self, e):
        self.label_layer = get_img("labelled", self.viewer)
        labels = [str(l) for l in self.table.model().dataframe.loc[:, "label"]]
        areas = [str(a) for a in self.table.model().dataframe.loc[:, "area"]]
        bboxes = [
            self.bbox2shape(bbox)
            for bbox in self.table.model().dataframe.loc[:, "_bbox"]
        ]

        print(
            f"bboxes labels and areas have lengths {len(bboxes), len(labels), len(areas)}"
        )
        print(f"bboxes labels and areas are {bboxes, labels, areas}")

        # https://napari.org/tutorials/applications/annotate_segmentation.html
        properties = {"label": labels, "area": areas}
        text_parameters = {
            "text": "{label}: {area}",
            "size": 6,
            "color": "red",
            "anchor": "upper_left",
        }

        self.viewer.add_shapes(
            list(bboxes),
            name="annotations",
            face_color="transparent",
            edge_width=2,
            edge_color="red",
            properties=properties,
            text=text_parameters,
        )

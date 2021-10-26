import numpy as np
from skimage.measure import regionprops

from qtpy.QtWidgets import QVBoxLayout, QPushButton
from napari_karyotype.utils import get_img

class AnnotationManager(QVBoxLayout):

    def __init__(self, viewer):

        super().__init__()
        self.viewer = viewer


        self.annotate_btn = QPushButton("Annotate")
        self.annotate_btn.clicked.connect(self.annotate)

        self.addWidget(self.annotate_btn)

    def bbox2shape(self, bbox):
        return np.array([[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]])

    def annotate(self, e):
        self.label_layer = get_img("labelled", self.viewer)

        rp = regionprops(self.label_layer.data)
        boxes, labels, areas = zip(*[(self.bbox2shape(r.bbox), r.label, r.area) for r in rp])
        print(f"boxes labels and areas have lengths {len(boxes), len(labels), len(areas)}")
        print(f"boxes labels and areas are {boxes, labels, areas}")

        properties = {"label": list(labels), "area": list(areas)}

        # https://napari.org/tutorials/applications/annotate_segmentation.html
        text_parameters = {
            'text': '{area}',
            'size': 6,
            'color': 'red',
            'anchor': 'upper_left',
            # 'anchor': 'lower_left',
            # 'anchor': 'center',
            # 'translation': [75, 0],
            # 'rotation': -90
        }

        self.viewer.add_shapes(list(boxes), face_color=[0.0, 0.0, 0.0, 0.0], edge_width=2, edge_color='red',
                               properties=
                               properties, text=text_parameters)
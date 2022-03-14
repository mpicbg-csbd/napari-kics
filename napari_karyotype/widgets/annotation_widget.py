import numpy as np
from skimage.measure import regionprops
import napari

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel, QSpinBox, QHBoxLayout, QDial, QFormLayout, QComboBox
from napari_karyotype.utils import get_img
from qtpy.QtCore import Qt


class AnnotationWidget(QFormLayout):
    def __init__(self, parent, viewer, table):
        super().__init__()
        self.parent = parent
        self.viewer = viewer
        self.table = table

        self.default_text_config = {
            "size": 5,
            "anchor": napari.layers.utils._text_constants.Anchor.UPPER_LEFT,
            "translation": np.array([0.0, 0.0]),
            "rotation": 0
        }

        # ----- text size -----
        self.text_size_label = QLabel("- size: ")
        self.text_size_spinner = QSpinBox()
        self.text_size_spinner.setRange(1, 20)
        self.text_size_spinner.setValue(5)
        self.text_size_spinner.valueChanged.connect(
            lambda value: setattr(get_img("annotations", self.viewer).text, "size", value)
        )

        # ----- text rotation -----
        self.text_rotation_label = QLabel("- rotation: ")
        self.text_rotation_dial = QDial()
        self.text_rotation_dial.setRange(0, 360)
        self.text_rotation_dial.setValue(0)
        self.text_rotation_dial.valueChanged.connect(
            lambda value: setattr(get_img("annotations", self.viewer).text, "rotation", value)
        )
        self.text_rotation_hbox = QHBoxLayout()
        self.text_rotation_hbox.addWidget(self.text_rotation_label)
        self.text_rotation_hbox.addWidget(self.text_rotation_dial)
        self.text_rotation_hbox.setAlignment(Qt.AlignLeft)

        # ----- text translation -----
        self.text_translation_label = QLabel("- translation: ")
        self.text_translation_x_spinner = QSpinBox()
        self.text_translation_x_spinner.setRange(-200, 200)
        self.text_translation_y_spinner = QSpinBox()
        self.text_translation_y_spinner.setRange(-200, 200)

        def upd_translation(x, y):
            x_, y_ = get_img("annotations", self.viewer).text.translation
            if x is not None:
                x_ = x
            if y is not None:
                y_ = y

            translation = np.array([x_, y_])
            setattr(get_img("annotations", self.viewer).text, "translation", translation)

        self.text_translation_x_spinner.valueChanged.connect(
            lambda value: upd_translation(value, None)
        )
        self.text_translation_y_spinner.valueChanged.connect(
            lambda value: upd_translation(None, value)
        )

        self.text_translation_hbox = QHBoxLayout()
        self.text_translation_hbox.addWidget(self.text_translation_x_spinner)
        self.text_translation_hbox.addWidget(self.text_translation_y_spinner)

        # ----- text anchor -----
        self.text_anchor_label = QLabel("- anchor: ")
        self.text_anchor_combo_box = QComboBox()
        for anchor in napari.layers.utils._text_constants.Anchor:
            self.text_anchor_combo_box.addItem(str(anchor))
        self.text_anchor_combo_box.currentTextChanged.connect(
            lambda value: setattr(get_img("annotations", self.viewer).text, "anchor",
                                  getattr(napari.layers.utils._text_constants.Anchor, value.upper()))
        )
        self.text_anchor_combo_box.setCurrentIndex(2)

        self.annotate_btn = QPushButton("Annotate")
        self.annotate_btn.clicked.connect(lambda _: self.parent.annotate())

        self.descr_label = QLabel(
            "4. Annotate the image with bounding boxes and areas:"
        )
        self.addRow(self.descr_label)
        self.addRow(self.text_size_label, self.text_size_spinner)
        self.addRow(self.text_translation_label, self.text_translation_hbox)
        self.addRow(self.text_rotation_label, self.text_rotation_dial)
        self.addRow(self.text_anchor_label, self.text_anchor_combo_box)
        self.addRow(self.annotate_btn)
        self.setLabelAlignment(Qt.AlignLeft)
        self.setSpacing(5)

from math import sqrt
from os import environ

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QFormLayout, QLabel, QVBoxLayout
from skimage.color import rgb2gray, rgba2rgb
from skimage.filters import gaussian

from .input_double_slider import InputDoubleSlider


class PreprocessingWidget(QVBoxLayout):
    inverted_opts = {"name": "inverted"}
    blurred_opts = {"name": "blurred"}
    thresholded_opts = {
        "name": "thresholded",
        "opacity": 0.7,
        "colormap": "red",
    }

    def __init__(self, viewer):

        super().__init__()

        self.viewer = viewer
        self.input_layer = None
        self.input_image = None

        options_layout = QFormLayout()

        # blur step description label
        blur_descr_label = QLabel(
            "1. Select an appropriate threshold and blur to segment the image:"
        )

        options_layout.addRow(blur_descr_label)

        # invert option
        self.invert_option = QCheckBox()
        # self.invert_option.setText()
        invert_option_label = QLabel("- invert:")
        # invert_option_label.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignCenter)
        invert_option_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.invert_option.stateChanged.connect(lambda _: self.preprocess())
        options_layout.addRow(invert_option_label, self.invert_option)

        # threshold slider
        self.threshold_slider = InputDoubleSlider(
            from_slider=lambda x: (x / 100) ** 2, to_slider=lambda x: 100 * sqrt(x)
        )
        self.threshold_slider.setMinimum(0.0)
        self.threshold_slider.setMaximum(1.0)
        self.threshold_slider.setTickInterval(20)
        self.threshold_slider.setTickPosition(InputDoubleSlider.TicksBelow)
        self.threshold_slider.setValue(float(environ.get("kt_threshold", 0.5)))
        self.threshold_slider.setDecimals(3)
        self.threshold_slider.setSingleStep(0.01)
        self.threshold_slider.setOrientation(Qt.Horizontal)
        self.threshold_slider.valueChanged.connect(lambda _: self.preprocess())

        threshold_label = QLabel("- threshold:")
        threshold_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        options_layout.addRow(threshold_label, self.threshold_slider)

        # sigma slider
        self.sigma_slider = InputDoubleSlider(scale=1 / 20)
        self.sigma_slider.setMinimum(0)
        self.sigma_slider.setMaximum(10)
        self.sigma_slider.setTickInterval(20)
        self.sigma_slider.setTickPosition(InputDoubleSlider.TicksBelow)
        self.sigma_slider.setValue(float(environ.get("kt_blur", 0.5)))
        self.sigma_slider.setDecimals(2)
        self.sigma_slider.setSingleStep(0.1)
        self.sigma_slider.setOrientation(Qt.Horizontal)
        self.sigma_slider.valueChanged.connect(lambda _: self.preprocess())
        blur_label = QLabel("- blur:")
        blur_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        options_layout.addRow(blur_label, self.sigma_slider)

        options_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.addLayout(options_layout)
        self.setSpacing(5)

        # options_layout.addRow(dummy_button1, dummy_button2)
        options_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        options_layout.setContentsMargins(0, 0, 0, 0)

        self.layout().setContentsMargins(0, 0, 0, 0)

    def invert_image(self):
        return self.invert_option.isChecked()

    def sigma(self):
        return self.sigma_slider.value()

    def threshold(self):
        return self.threshold_slider.value()

    def _assert_input_image(self, force_update=False):
        if force_update or self.input_image is None:
            if self.viewer.layers.selection.active is None:
                raise Exception(
                    "No available images found. Please import a karyotype first."
                )

            self.input_layer = self.viewer.layers.selection.active
            self.input_image = self._to_gray(self.input_layer.data)
            self.last_sigma = None
            self.last_threshold = None
            self.last_invert_image = None
            self.viewer.layers.events.removed.connect(
                lambda e: self.reset_input_layer()
                if e.value == self.input_layer
                else print(f"removed layer {e.value.name} at {e.index}")
            )

    def reset_input_layer(self):
        self.input_layer = None
        self.input_image = None

    @staticmethod
    def _to_gray(img):
        if len(img.shape) == 3 and img.shape[-1] == 4:
            return rgb2gray(rgba2rgb(img))
        elif len(img.shape) == 3 and img.shape[-1] == 3:
            return rgb2gray(img)
        elif (
            (len(img.shape) == 3 and img.shape[-1] == 1) or (len(img.shape) == 2)
        ) and img.dtype.kind in "uif":
            if img.dtype.kind in "ui":
                return img / 255.0
            elif img.dtype.kind == "f":
                return img
            else:
                assert False, "unreachable"
        else:
            raise Exception(
                f"Cannot process image with type {img.dtype} and shape {img.shape}."
            )

    def _apply_invert(self):
        self._assert_input_image()

        if self.last_invert_image == self.invert_image():
            print(
                f"[PreprocessingWidget] skipping invert (invert={self.invert_image()})"
            )
            return

        print(f"[PreprocessingWidget] applying invert (invert={self.invert_image()})")

        if self.invert_image():
            inverted_image = 1 - self.input_image
        else:
            inverted_image = self.input_image

        try:
            self.viewer.layers[self.inverted_opts["name"]].data = inverted_image
        except KeyError:
            self.viewer.add_image(inverted_image, **self.inverted_opts)

        self.last_invert_image = self.invert_image()
        self.last_sigma = None
        self.last_threshold = None

    def _apply_blur(self):
        self._apply_invert()

        if self.last_sigma == self.sigma():
            print(f"[PreprocessingWidget] skipping blur (sigma={self.sigma()})")
            return

        print(f"[PreprocessingWdget] applying blur (sigma={self.sigma()})")
        inverted_image = self.viewer.layers[self.inverted_opts["name"]].data
        blurred_img = gaussian(inverted_image, self.sigma())

        try:
            self.viewer.layers[self.blurred_opts["name"]].data = blurred_img
        except KeyError:
            self.viewer.add_image(blurred_img, **self.blurred_opts)

        self.last_sigma = self.sigma()
        self.last_threshold = None

    def _apply_threshold(self):
        self._apply_blur()

        if self.last_threshold == self.threshold():
            print(
                "[PreprocessingWidget] skipping threshold",
                f"(threshold={self.threshold()})",
            )
            return

        print(
            f"[PreprocessingWidget] applying threshold (threshold={self.threshold()})"
        )
        blurred_img = self.viewer.layers[self.blurred_opts["name"]].data
        thresholded_img = (blurred_img < 1 - self.threshold()).astype(int)

        try:
            self.viewer.layers[self.thresholded_opts["name"]].data = thresholded_img
        except KeyError:
            self.viewer.add_image(thresholded_img, **self.thresholded_opts)

        self.last_threshold = self.threshold()

        try:
            # label layer is out-of-date => remove it (if present)
            self.viewer.layers.remove("labelled")
        except ValueError:
            pass

    def preprocess(self):
        self._apply_threshold()

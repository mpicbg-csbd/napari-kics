from .input_double_slider import InputDoubleSlider
from math import sqrt
from qtpy.QtWidgets import QLabel, QFormLayout, QVBoxLayout
from qtpy.QtCore import Qt
from skimage.color import rgba2rgb, rgb2gray
from skimage.filters import gaussian
from os import environ


class PreprocessingWidget(QVBoxLayout):
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

        # blur step description label
        blur_descr_label = QLabel(
            "1. Select an appropriate threshold and blur to segment the image."
        )

        options_layout = QFormLayout()

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
        self.threshold_slider.valueChanged.connect(lambda _: self._apply_threshold())
        options_layout.addRow("threshold:", self.threshold_slider)

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
        self.sigma_slider.valueChanged.connect(lambda _: self._apply_threshold())
        options_layout.addRow("blur:", self.sigma_slider)

        self.addLayout(options_layout)
        self.setSpacing(5)

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
            self.input_layer.events.set_data.connect(lambda event: print(event))
            self.input_layer.events.set_data.connect(
                lambda _: self._assert_input_image(force_update=True)
            )

    @staticmethod
    def _to_gray(img):
        if len(img.shape) == 3 and img.shape[-1] == 4:
            return rgb2gray(rgba2rgb(img))
        elif len(img.shape) == 3 and img.shape[-1] == 3:
            return rgb2gray(img)
        elif (len(img.shape) == 3 and img.shape[-1] == 1) or (len(img.shape) == 2):
            return img
        else:
            raise Exception(
                f"Cannot process image with type {img.dtype} and shape {img.shape}."
            )

    def _apply_blur(self):
        self._assert_input_image()

        if self.last_sigma == self.sigma():
            print(f"[PreprocessingWidget] skipping blur (sigma={self.sigma()})")
            return

        print(f"[PreprocessingWidget] applying blur (sigma={self.sigma()})")
        blurred_img = gaussian(self.input_image, self.sigma())

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
                f"[PreprocessingWidget] skipping threshold (threshold={self.threshold()})"
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

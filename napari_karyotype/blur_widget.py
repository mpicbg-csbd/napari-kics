from qtpy.QtWidgets import QLabel, QSlider, QHBoxLayout, QVBoxLayout
from qtpy.QtCore import Qt


class BlurWidget(QVBoxLayout):

    def __init__(self, viewer):

        super().__init__()

        self.viewer = viewer

        # actual function
        def blur(input_image, sigma=1.0):

            from skimage.color import rgb2gray
            if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                img = rgb2gray(input_image)
            elif (len(input_image.shape) == 3 and input_image.shape[-1] == 1) or (len(input_image.shape) == 2):
                img = input_image
            else:
                raise Exception(f"Cannot process image with type f{input_image.dtype} and shape {input_image.shape}.")

            from skimage.filters import gaussian
            return gaussian(img, sigma)

        def blur_wrapper(sigma):

            if self.viewer.layers.selection.active is None:
                raise Exception("No available images found. Please import a karyotype first.")

            input_image = self.viewer.layers.selection.active.data

            blurred = blur(input_image, sigma)

            try:
                self.viewer.layers["blurred"].data = blurred
            except KeyError:
                self.viewer.add_image(blurred, name="blurred")


        # blur step description label
        blur_descr_label = QLabel(
            "1. Select an appropriate sigma value to denoise the image with a Gaussian blur:")

        # blur slider label
        blur_sl_label = QLabel("sigma:")

        # sigma slider
        sigma_slider = QSlider(Qt.Horizontal)
        sigma_slider.setMinimum(0)
        sigma_slider.setMaximum(100)
        sigma_slider.setSingleStep(1)
        sigma_slider.setTickInterval(20)
        sigma_slider.setTickPosition(QSlider.TicksBelow)
        sigma_slider.setValue(50)
        sigma_slider.setFixedWidth(400)

        # sigma slider value
        sigma_sl_val = QLabel(f"{sigma_slider.value() / 20:0.2f}")
        sigma_slider.valueChanged.connect(lambda e: sigma_sl_val.setText(f"{sigma_slider.value() / 20:0.2f}"))
        sigma_slider.valueChanged.connect(lambda e: blur_wrapper(sigma_slider.value() / 20))

        # threshold box
        blur_box_ = QHBoxLayout()
        blur_box_.addWidget(blur_sl_label)
        blur_box_.addWidget(sigma_slider)
        blur_box_.addWidget(sigma_sl_val)
        blur_box_.setSpacing(0)
        blur_box_.setContentsMargins(0, 0, 0, 0)

        self.addWidget(blur_descr_label)
        self.addLayout(blur_box_)
        self.setSpacing(5)

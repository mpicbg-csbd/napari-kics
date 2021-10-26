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
            else:
                img = input_image

            from skimage.filters import gaussian
            return gaussian(img, sigma)

        def blur_wrapper(sigma):

            input_image = self.viewer.layers.selection.active.data
            self.input_img_name = self.viewer.layers.selection.active.name
            print(f"[blur_wrapper]: input img name is {self.input_img_name}")
            blurred = blur(input_image, sigma)

            try:
                self.viewer.layers["blurred"].data = blurred
            except KeyError:
                self.viewer.add_image(blurred, name="blurred")
            self.viewer.layers.select_previous()

        # blur step description label
        blur_descr_label = QLabel(
            "1. Select the appropriate sigma value to denoise the image with a Gaussian blur:")

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
from qtpy.QtWidgets import QLabel, QSlider, QHBoxLayout, QVBoxLayout
from qtpy.QtCore import Qt
from napari_karyotype.utils import get_img


class ThresholdWidget(QVBoxLayout):

    def __init__(self, viewer):

        super().__init__()

        self.viewer = viewer

        # the actual function
        def threshold(input_image, threshold_value=0.5):
            return ((1 - input_image) > threshold_value).astype(int)

        # wrapper with napari updates
        def threshold_wrapper(threshold_value=0.5):
            input_image = get_img("blurred", self.viewer).data
            thresholded = threshold(input_image, threshold_value)

            try:
                self.viewer.layers["thresholded"].data = thresholded
            except KeyError:
                self.viewer.add_image(thresholded, name="thresholded", opacity=0.7, colormap="red")

        # thresholding step description label
        th_descr_label = QLabel("2. Select the appropriate threshold value to segment the image.")

        # threshold slider label
        th_sl_label = QLabel("th_val:")

        # threshold slider
        threshold_slider = QSlider(Qt.Horizontal)
        threshold_slider.setMinimum(0)
        threshold_slider.setMaximum(100)
        threshold_slider.setSingleStep(1)
        threshold_slider.setTickInterval(20)
        threshold_slider.setTickPosition(QSlider.TicksBelow)
        threshold_slider.setValue(50)
        threshold_slider.setFixedWidth(400)

        # threshold slider value
        th_sl_val = QLabel(f"{threshold_slider.value() / 100:0.2f}")
        threshold_slider.valueChanged.connect(lambda e: th_sl_val.setText(f"{threshold_slider.value() / 100:0.2f}"))
        threshold_slider.valueChanged.connect(lambda e: threshold_wrapper(threshold_slider.value() / 100))

        # threshold box
        threshold_box_ = QHBoxLayout()
        threshold_box_.addWidget(th_sl_label)
        threshold_box_.addWidget(threshold_slider)
        threshold_box_.addWidget(th_sl_val)

        self.addWidget(th_descr_label)
        self.addLayout(threshold_box_)
        self.setSpacing(5)

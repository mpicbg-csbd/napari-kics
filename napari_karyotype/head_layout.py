from qtpy.QtSvg import QSvgWidget
from pathlib import Path
from qtpy.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt


class HeadLayout(QHBoxLayout):

    def __init__(self):
        super().__init__()

        # svg widget
        logo_size = 85
        logoSvgWidget = QSvgWidget(f"{Path(__file__).absolute().parent}/resources/artwork/logo.svg")
        logoSvgWidget.setGeometry(0, 0, logo_size, logo_size)
        logoSvgWidget.setMaximumSize(logo_size, logo_size)
        logoSvgWidget.setMinimumSize(logo_size, logo_size)

        # name and description labels
        name_label = QLabel("Karyotype")
        name_label.setFont(QFont("Palatino", 20))
        description_label = QLabel("relative chromosome size evaluation from the karyotype images.")
        description_label.setFont(QFont("Palatino", 13))

        # text label layout
        label_layout = QVBoxLayout()
        label_layout.addWidget(name_label)
        label_layout.addWidget(description_label)
        label_layout.setAlignment(Qt.AlignVCenter)

        # head layout
        self.addWidget(logoSvgWidget)
        self.addLayout(label_layout)
        self.setAlignment(Qt.AlignBottom)

from pathlib import Path

from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtSvg import QSvgWidget
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout


class HeadLayout(QHBoxLayout):
    def __init__(self):
        super().__init__()

        # svg widget
        logo_size = 85
        logoSvgWidget = QSvgWidget(
            f"{Path(__file__).absolute().parent.parent}/resources/artwork/logo.svg"
        )
        logoSvgWidget.setGeometry(0, 0, logo_size, logo_size)
        logoSvgWidget.setMaximumSize(logo_size, logo_size)
        logoSvgWidget.setMinimumSize(logo_size, logo_size)

        # name and description labels
        name_label = QLabel("KICS")
        name_label.setFont(QFont("Palatino", 20))
        description_label = QLabel("Karyotype image-based chromosome size estimation.")
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

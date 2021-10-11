from qtpy.QtWidgets import *
from qtpy.QtGui import QFont
from qtpy.QtSvg import QSvgWidget
from PyQt5.QtCore import Qt

import napari, json, os
from napari_karyotype.utils import create_widget

from pathlib import Path
from napari_karyotype import functions


# ------------------------------------------------------------------------
# Main pipeline widget
# ------------------------------------------------------------------------
class KaryotypeWidget(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

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
        self.head_layout = QHBoxLayout()
        self.head_layout.addWidget(logoSvgWidget)
        self.head_layout.addLayout(label_layout)
        self.head_layout.setAlignment(Qt.AlignBottom)


        # state
        self.state = {}

        self.generate_gui_from_config()


    def generate_gui_from_config(self, config_file_path=f"{Path(__file__).absolute().parent}/resources/config/config.json"):

        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)

            # widgets
            widgets = []
            function_names = []
            for (func_name, func_config) in config.items():
                func = getattr(functions, f"{func_name}")
                widgets.append(create_widget(func, func_config, self.state, self.viewer))
                function_names.append(func_name)


            [widget.layout().setAlignment(Qt.AlignTop) for widget in widgets]

            steps2widget_dict = {f"{i + 1}. {function_names[i].replace('_', ' ').title()}": widgets[i] for i in
                                 range(len(widgets))}


            self.curr = 0

            self.layout.addLayout(self.head_layout)
            self.layout.addSpacing(10)
            [self.layout.addWidget(widget) for widget in widgets]

            self.layout.setAlignment(Qt.AlignTop)
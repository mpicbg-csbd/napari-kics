from qtpy.QtWidgets import *
from qtpy.QtGui import QFont
from qtpy.QtSvg import QSvgWidget
from PyQt5.QtCore import Qt
from qtpy import QtWidgets
from qtpy.QtGui import QBrush

import napari, json, os
from napari_karyotype.utils import create_widget

from pathlib import Path
import magicgui

from qtpy import QtCore
import pandas as pd
import numpy as np
from qtpy.QtGui import QColor

from napari.qt import thread_worker
from copy import deepcopy

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

            # ----------------------------------------------------------------------
            # thresholding widget
            # ----------------------------------------------------------------------

            def threshold(input_image, threshold_value=0.5):
                from skimage.color import rgb2gray
                if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                    img = rgb2gray(input_image)
                else:
                    img = input_image
                return ((1 - img) > threshold_value).astype(int)

            threshold_config = {

                "threshold_value": {
                    "widget_type": "FloatSlider",
                    "min": 0.00,
                    "max": 1.00,
                    "step": 0.01,
                    "value": 0.5
                },
                "auto_call": True
            }

            def threshold_updater(img_name, img, viewer):
                # print(f"[update_layer]: updating layers with data of shape {img.shape} and name {img_name}")
                try:
                    viewer.layers[img_name].data = img
                except KeyError:
                    viewer.add_image(img, name=img_name, opacity=0.7, colormap="red")
                    viewer.layers.select_previous()

            def threshold_wrapper(threshold_value=0.5):
                input_image = self.viewer.layers.selection.active.data
                thresholded = threshold(input_image, threshold_value)
                threshold_updater("thresholded", thresholded, self.viewer)

            # ----------------------------------------------------------------------
            # thresholding widget
            # ----------------------------------------------------------------------

            def label(input_image):
                from scipy.ndimage import label
                return label(input_image)[0]

            label_config = {
                "call_button": "Label"
            }

            def labelled_updater(img_name, img, viewer):
                # # print(f"[update_layer]: updating layers with data of shape {img.shape} and name {img_name}")
                # try:
                #     viewer.layers[img_name].data = img
                # except KeyError:
                    viewer.add_labels(img, name=img_name)


            def label_wrapper():
                input_image = self.viewer.layers.selection.active.data
                labelled_img = label(input_image).astype(int)
                labelled_updater("labelled", labelled_img, self.viewer)


            widgets.append(magicgui.magicgui(threshold_wrapper, **threshold_config).native)
            widgets.append(magicgui.magicgui(label_wrapper, **label_config).native)

            self.curr = 0

            self.layout.addLayout(self.head_layout)
            self.layout.addSpacing(10)
            [self.layout.addWidget(widget) for widget in widgets]

            self.layout.setAlignment(Qt.AlignTop)

            # ----------------------------------------------------------------------
            # table widget
            # ----------------------------------------------------------------------



            self.table = QtWidgets.QTableView()
            self.table.setSortingEnabled(True)
            # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

            # self.table.clicked.connect(lambda e: print(f"selection changed to {e.row()}"))
            # self.table.clicked.connect(lambda e: print(f"selection indices are {self.table.selectedIndexes()}"))
            # self.table.dragMoveEvent().connect(lambda e: print(f"selection indices are {self.table.selectedIndexes()}"))

            def table_key_press_event(viewer):


                indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
                print(f"selection indices are {indices}")

                labels = [self.table.model().dataframe.iloc[i][1] for i in indices]
                print(f"the corresponding labels are {labels}")


                coords_to_fill = [entry[2] for entry in self.res if entry[0] in labels]
                print(f"coords to fill are {coords_to_fill}")

                # print(self.res)

                [self.label_layer.fill(coord, 0) for coord in coords_to_fill]

            def table_key_press_event_wrapper(e):
                if e.key() == Qt.Key_Backspace:
                    table_key_press_event(None)


            self.table.keyPressEvent = table_key_press_event_wrapper
            self.viewer.bind_key("Backspace", table_key_press_event)

            def change_handler():
                pass

            self.table.clicked.connect(change_handler)

            self.generate_table_btn = QtWidgets.QPushButton("Generate Table")

            self.summary_frame = pd.DataFrame()

            self.label_layer = None




            # self.table.sortByColumn()
            # self.table.setSortingEnabled(True)
            # self.table.sor

            # self.table.horizontalHeader().setSortIndicator(2, Qt.AscendingOrder )
            # self.table.setSortingEnabled(True)
            # self.table.sortByColumn(2, Qt.AscendingOrder)


            from skimage.measure import regionprops


            @thread_worker
            def upd_table():
                # labels, counts = np.unique(self.label_layer.data, return_counts=True)
                rp = regionprops(self.label_layer.data+1)
                # self.labels = [r.label-1 for r in rp]
                # counts = [r.area for r in rp]
                # self.coords = [r.coords for r in rp]

                self.res = np.array([(r.label-1, r.area, r.coords[0]) for r in rp], dtype=object)
                self.res = np.array(sorted(self.res, key=lambda x: x[0]))
                # print(res)



                # l = [("", labels[ind], self.label_layer.get_color(labels[ind])) for ind in range(len(labels))]
                l = [("", self.res[ind,0], self.res[ind,1]) for ind in range(len(self.res))]
                colors = [self.label_layer.get_color(label) for label in self.res[:,0]]
                self.summary_frame = pd.DataFrame(l)
                # self.table.setModel(MyTableModel(self.summary_frame, colors))

                return self.summary_frame, colors


            def upd_table_widget(args):
                self.table.setModel(MyTableModel(args[0], args[1]))
                self.table.sortByColumn(2, Qt.DescendingOrder)
                # self.table.

            def abcde(args):
                print(args)

            def launch_upd_worker():
                worker = upd_table()
                worker.returned.connect(upd_table_widget)
                worker.start()


            def generate_new_model():

                self.label_layer = self.viewer.layers.selection.active
                launch_upd_worker()
                self.label_layer.events.set_data.connect(lambda x: launch_upd_worker())

                def synchronize_selection(e):
                     indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
                     self.label_layer.selected_label = self.table.model().dataframe[1].iloc[indices[0]]

                self.table.clicked.connect(synchronize_selection)

                def select_label_updater(e):
                    sl = self.label_layer.selected_label
                    print(f"selecting label {sl}")
                    # ind = self.table.model().dataframe.loc[self.table.model().dataframe[1] == sl].index[0]
                    ind = list(self.table.model().dataframe[1]).index(sl)
                    print(self.table.model().dataframe.loc[self.table.model().dataframe[1] == sl])
                    print(f"selecting row {ind}")
                    self.table.selectRow(ind)

                self.label_layer.events.selected_label.connect(select_label_updater)




            def foo():
                print("foo")

            self.generate_table_btn.clicked.connect(foo)
            # self.table.setModel(MyTableModel(loop_data))

            self.layout.addWidget(self.generate_table_btn)
            self.layout.addWidget(self.table)
            self.generate_table_btn.clicked.connect(generate_new_model)








# https://www.pythonguis.com/faq/editing-pyqt-tableview/
class MyTableModel(QtCore.QAbstractTableModel):

    def __init__(self, pandas_dataframe, colors):
        super().__init__()

        self.dataframe = pandas_dataframe
        self.colors = colors
        self.colors_ordered = deepcopy(self.colors)
        # self.dataframe.insert(3, "colors", self.colors)




    def rowCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[1]

    def data(self, QModelIndex, role=None):

        if role == Qt.BackgroundRole and QModelIndex.column() == 0:

            color = self.colors_ordered[QModelIndex.row()]
            if color is None:
                color = np.array([0.0, 0.0, 0.0, 0.0])
            r,g,b,a = (255*color).astype(int)
            # print(f"Color is {r,g,b,a}")
            return QBrush(QColor(r,g,b, alpha=a))


        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()


        return str(self.dataframe.iloc[QModelIndex.row()][QModelIndex.column()])

    def headerData(self, p_int, Qt_Orientation, role=None):

        if role == QtCore.Qt.DisplayRole:
            if Qt_Orientation == QtCore.Qt.Horizontal:
                return self.dataframe.columns[p_int]
            else:
                return p_int

    def setData(self, index, value, role):
        if role==Qt.EditRole:
            self.dataframe.iloc[index.row(), index.column()] = value
            return True
        return False

    def flags(self, index):
        # label = Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsEditable
        label = Qt.ItemIsEnabled | Qt.ItemIsEditable
        rest = Qt.ItemIsSelectable|Qt.ItemIsEnabled

        if index.column() == 0:
            return Qt.ItemIsEnabled
        elif index.column() == 1:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # https://stackoverflow.com/questions/28660287/sort-qtableview-in-pyqt5
    def sort(self, column, order):

        self.layoutAboutToBeChanged.emit()

        self.merged_frame = pd.concat([self.dataframe, pd.DataFrame({"colors": self.colors})], axis=1)
        self.merged_frame = self.merged_frame.sort_values(by=column, ascending=(order==Qt.AscendingOrder))
        self.dataframe = self.merged_frame.iloc[:,:-1]
        self.colors_ordered = list(self.merged_frame.iloc[:,-1])

        print(self.dataframe)

        self.layoutChanged.emit()
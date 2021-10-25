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
from napari_karyotype.utils import get_img


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

    def get_imgs_dict(self):

        res = {}
        names = [layer.name for layer in self.viewer.layers]
        res[self.input_img_name] = self.viewer.layers[names.index(self.input_img_name)].data
        res["thresholded"] = self.viewer.layers[names.index("thresholded")].data
        res["labelled"] = self.viewer.layers[names.index("labelled")].data

        res["labelled_color"] = self.viewer.layers[names.index("labelled")].get_color(list(res["labelled"]))

        return res

    def generate_gui_from_config(self,
                                 config_file_path=f"{Path(__file__).absolute().parent}/resources/config/config.json"):

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

            def threshold_wrapper(threshold_value=0.5):
                input_image = self.viewer.layers.selection.active.data
                self.input_img_name = self.viewer.layers.selection.active.name
                print(f"[threshold_wrapper]: input img name is {self.input_img_name}")
                thresholded = threshold(input_image, threshold_value)
                # threshold_updater("thresholded", thresholded, self.viewer)
                try:
                    self.viewer.layers["thresholded"].data = thresholded
                except KeyError:
                    self.viewer.add_image(thresholded, name="thresholded", opacity=0.7, colormap="red")
                    self.viewer.layers.select_previous()

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

            # widgets.append(magicgui.magicgui(threshold_wrapper, **threshold_config).native)

            # ----------------------------------------------------------------------
            # 1. Blur step
            # ----------------------------------------------------------------------

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

            blur_box = QVBoxLayout()
            blur_box.addWidget(blur_descr_label)
            blur_box.addLayout(blur_box_)
            blur_box.setSpacing(5)

            # ----------------------------------------------------------------------
            # 2. Thresholding step
            # ----------------------------------------------------------------------

            # the actual function
            def threshold(input_image, threshold_value=0.5):

                from skimage.color import rgb2gray
                if (len(input_image.shape) == 3 and input_image.shape[-1] == 3):
                    img = rgb2gray(input_image)
                else:
                    img = input_image

                return ((1 - img) > threshold_value).astype(int)

            # wrapper with napari updates
            def threshold_wrapper(threshold_value=0.5):
                input_image = get_img("blurred", self.viewer).data

                print(f"[threshold_wrapper]: input img name is {self.input_img_name}")
                thresholded = threshold(input_image, threshold_value)
                # threshold_updater("thresholded", thresholded, self.viewer)
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
            threshold_box = QVBoxLayout()
            threshold_box.addWidget(th_descr_label)
            threshold_box.addLayout(threshold_box_)
            threshold_box.setSpacing(5)

            # ----------------------------------------------------------------------
            # 3. Labeling step
            # ----------------------------------------------------------------------

            # the actual function

            def label(img):
                from scipy.ndimage import label
                return label(img)[0]

            # wrapper with napari updates
            def label_wrapper():

                input_image = get_img("thresholded", self.viewer).data
                labelled = label(input_image)

                try:
                    self.viewer.layers["labelled"].data = labelled
                except KeyError:
                    self.viewer.add_labels(labelled, name="labelled", opacity=0.7)

            labeling_descr_label = QLabel(
                "3. Apply label function to assign a unique integer id to each connected component:")
            label_btn = QPushButton("Label")
            label_btn.clicked.connect(lambda e: label_wrapper())

            label_box = QVBoxLayout()
            label_box.addWidget(labeling_descr_label)
            label_box.addWidget(label_btn)
            label_box.setSpacing(5)

            self.layout.addLayout(self.head_layout)
            self.layout.addLayout(blur_box)
            self.layout.addLayout(threshold_box)
            self.layout.addLayout(label_box)

            self.layout.setAlignment(Qt.AlignTop)
            self.layout.setSpacing(20)

            # ----------------------------------------------------------------------
            # table widget
            # ----------------------------------------------------------------------

            self.table = QtWidgets.QTableView()
            self.table.setSortingEnabled(True)
            # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

            def delete_label(viewer):

                indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
                coords = [np.where(self.label_layer.data == label) for label in
                          self.table.model().dataframe.index[indices]]
                coords_to_fill = [(co[0][0], co[1][0]) for co in coords]

                print(f"[backspace]: removing indices {indices}")

                [self.label_layer.fill(coord, 0) for coord in coords_to_fill]

            self.viewer.bind_key("Backspace", delete_label)


            self.generate_table_btn = QtWidgets.QPushButton("Generate Table")

            self.label_layer = None

            self.history_queue_length = 0
            self.history_last_step_length = 0

            from napari_karyotype.utils import LabelManager
            label_manager = LabelManager(get_img("labelled", self.viewer))

            def upd_table_new():

                res_dict = label_manager.process_history_step()

                print(f"res_dict is {res_dict}")

                for (label, increment) in res_dict.items():

                    if not (label in self.table.model().dataframe.index):
                        print(f"label {label} is not in the dataframe")
                        self.table.model().dataframe = self.table.model().dataframe.append(
                            pd.DataFrame([["", label, increment]], index=[label]))
                        print(f"now it is \n{self.table.model().dataframe}")

                    else:
                        self.table.model().dataframe.loc[label, 2] += increment

                        if (self.table.model().dataframe.loc[label, 2] == 0):
                            self.table.model().dataframe.drop(label, inplace=True)
                            print(f"label {label} is set to 0")
                    self.table.update()
                    self.table.sortByColumn(2, Qt.DescendingOrder)

            from skimage.measure import regionprops
            @thread_worker
            def upd_table():
                # labels, counts = np.unique(self.label_layer.data, return_counts=True)
                rp = regionprops(self.label_layer.data + 1)
                # self.labels = [r.label-1 for r in rp]
                # counts = [r.area for r in rp]
                # self.coords = [r.coords for r in rp]

                self.res = np.array([(r.label - 1, r.area, r.coords[0]) for r in rp], dtype=object)
                self.res = np.array(sorted(self.res, key=lambda x: x[0]))
                # print(res)

                # l = [("", labels[ind], self.label_layer.get_color(labels[ind])) for ind in range(len(labels))]
                l = [("", self.res[ind, 0], self.res[ind, 1]) for ind in range(len(self.res))]
                colors = [self.label_layer.get_color(label) for label in self.res[:, 0]]
                self.summary_frame = pd.DataFrame(l)
                # self.table.setModel(MyTableModel(self.summary_frame, colors))

                return self.summary_frame, colors

            def upd_table_widget(args):
                # self.table.setModel(MyTableModel(args[0], args[1]))
                self.table.setModel(MyTableModel(args[0], self.label_layer.get_color))
                self.table.sortByColumn(2, Qt.DescendingOrder)

            def launch_upd_worker():
                worker = upd_table()
                worker.returned.connect(upd_table_widget)
                worker.start()

            order_button = QPushButton("Adjust labelling order")
            order_button.setCheckable(True)

            annotate_btn = QPushButton("Annotate")

            from napari_karyotype.utils import ClickableLineEdit
            save_path_line_edit = ClickableLineEdit(f"{Path(__file__).absolute().parent}/resources/example_output")

            save_btn = QPushButton("Save")
            save_btn.clicked.connect(lambda x: print(f"path is {save_path_line_edit.text()}"))

            def generate_new_model():

                self.label_layer = self.viewer.layers.selection.active
                launch_upd_worker()
                # self.label_layer.events.set_data.connect(lambda x: launch_upd_worker())
                self.label_layer.events.set_data.connect(lambda x: upd_table_new())

                def synchronize_selection(e):
                    indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
                    # self.label_layer.selected_label = self.table.model().dataframe[1].iloc[indices[0]]
                    self.label_layer.selected_label = self.table.model().dataframe.index[indices[0]]

                self.table.clicked.connect(synchronize_selection)

                def select_label_updater(e):
                    sl = self.label_layer.selected_label
                    print(f"selecting label {sl}")
                    # ind = self.table.model().dataframe.loc[self.table.model().dataframe[1] == sl].index[0]
                    # ind = list(self.table.model().dataframe[1]).index(sl)
                    ind = self.table.model().dataframe.index.get_loc(sl)
                    # print(self.table.model().dataframe.loc[self.table.model().dataframe[1] == sl])
                    print(f"selecting row {ind}")
                    self.table.selectRow(ind)

                self.label_layer.events.selected_label.connect(select_label_updater)

                # -------------------------------------------------------
                # ordering
                # -------------------------------------------------------

                # order = []
                #
                # def order_listener(layer, event):
                #
                #     print(f"order listener: {event.position}")
                #     print(f"event type is {event.type}")
                #
                #     yield
                #
                #     while event.type == "mouse_move":
                #         print(self.label_layer.get_value(event.position))
                #         curr_label = self.label_layer.get_value(event.position)
                #         if (curr_label != 0):
                #             self.label_layer.selected_label = self.label_layer.get_value(event.position)
                #             if curr_label not in order:
                #                 order.append(curr_label)
                #                 self.table.model().dataframe.at[curr_label, 1] = len(order)
                #
                #             # print(f"counter = {counter}")
                #         yield
                #
                #     # while event.type == 'mouse_move':
                #     #     print(f"order listener: {event.position}")
                #
                def change_appearance(e):
                    if order_button.isChecked():
                        order_button.setDown(True)

                        print(f"order button is {order_button.isChecked()}")
                        # self.label_layer.mouse_move_callbacks.append(order_listener)

                        # self.label_layer.mouse_drag_callbacks.append(order_listener)
                    else:
                        order_button.setDown(False)
                        print(f"order button is {order_button.isChecked()}")
                        # self.label_layer.mouse_move_callbacks.remove(order_listener)
                        # self.label_layer.mouse_drag_callbacks.remove(order_listener)

                order_button.clicked.connect(change_appearance)

                order = []

                def order_listener(label_layer, event):

                    print(f"order listener: {event.position}")
                    print(f"event type is {event.type}")

                    yield

                    while event.type == "mouse_move":
                        if "Alt" in event.modifiers:
                            print(label_layer.get_value(event.position))
                            curr_label = label_layer.get_value(event.position)
                            if (curr_label != 0 and curr_label is not None):
                                label_layer.fill(event.position, 0)
                                # order.append(curr_label)
                                print(f"order list is {order}")

                        yield

                def parse_recent_step(layer):

                    print(f"parse recent step")

                    print(f"undo history\n {layer._undo_history}")
                    print(f"redo history\n {layer._redo_history}")

                    if len(layer._undo_history) != 0:
                        recent_step = layer._undo_history[-1][-1]
                        label = recent_step[1][0]

                        if label not in order:
                            order.append(label)
                        else:
                            recent_step = layer._redo_history[-1][-1]
                            label = recent_step[1][0]
                            order.remove(label)


                    else:
                        recent_step = layer._redo_history[-1][-1]
                        label = recent_step[1][0]
                        order.remove(label)

                    print(f"recent label: {label}")
                    print(f"order: {order}")

                def activate_ordering_mode():

                    order.clear()

                    # make all the existing layers invisible
                    for layer in self.viewer.layers:
                        layer.visible = 0

                    # add a new auxiliary ordering layer
                    ordering_label_layer = self.viewer.add_labels(deepcopy(self.label_layer.data), name="ordering")
                    ordering_label_layer.editable = False
                    ordering_label_layer.mouse_drag_callbacks.append(order_listener)

                    # attach the event listener
                    ordering_label_layer.events.set_data.connect(lambda x: parse_recent_step(ordering_label_layer))

                def deactivate_ordering_mode():

                    # delete the auxiliary ordering layer
                    names = [layer.name for layer in self.viewer.layers]
                    ind = names.index("ordering")
                    self.viewer.layers.pop(ind)

                    # make other layers visible
                    for layer in self.viewer.layers:
                        layer.visible = 1

                    print(f"order is {order}")

                    if len(order) > 0:

                        print("relabelling")
                        for ind, label in enumerate(order):
                            self.table.model().dataframe.at[label, 1] = ind + 1

                        unprocessed_labels = set(list(self.table.model().dataframe.index)) - set(order) - {0}

                        for label in unprocessed_labels:
                            self.table.model().dataframe.at[label, 1] = 9999

                    self.table.update()

                def toggle_ordering_mode(flag):
                    if flag:
                        activate_ordering_mode()
                    else:
                        deactivate_ordering_mode()

                order_button.clicked.connect(lambda e: toggle_ordering_mode(order_button.isChecked()))

                # -------------------------------------------------------
                # annotation
                # -------------------------------------------------------

                def bbox2shape(bbox):
                    return np.array([[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]])

                def annotate(e):
                    rp = regionprops(self.label_layer.data)
                    boxes, labels, areas = zip(*[(bbox2shape(r.bbox), r.label, r.area) for r in rp])
                    print(f"boxes labels and areas have lngths {len(boxes), len(labels), len(areas)}")
                    print(f"boxes labels and areas are {boxes, labels, areas}")

                    properties = {"label": list(labels), "area": list(areas)}

                    # https: // napari.org / tutorials / applications / annotate_segmentation.html
                    text_parameters = {
                        'text': '{area}',
                        'size': 6,
                        'color': 'red',
                        'anchor': 'upper_left',
                        # 'anchor': 'lower_left',
                        # 'anchor': 'center',
                        # 'translation': [75, 0],
                        # 'rotation': -90
                    }

                    self.viewer.add_shapes(list(boxes), face_color=[0.0, 0.0, 0.0, 0.0], edge_width=2, edge_color='red',
                                           properties=
                                           properties, text=text_parameters)

                annotate_btn.clicked.connect(annotate)

                # -------------------------------------------------------
                # saving
                # -------------------------------------------------------

                def save_output(path):

                    # images
                    from skimage import io
                    imgs_dict = self.get_imgs_dict()
                    [io.imsave(f"{path}/{name}.png", img) for (name, img) in imgs_dict.items()]

                    # dataframe
                    dataframe = pd.DataFrame()
                    dataframe["tags"] = list(self.table.model().dataframe[1])
                    dataframe["labels"] = list(self.table.model().dataframe.index)
                    dataframe["area"] = list(self.table.model().dataframe[2])
                    dataframe.to_csv(f"{path}/data.csv", index=False)

                    # screenshot
                    self.viewer.screenshot(f"{path}/screenshot.png")

                save_btn.clicked.connect(lambda e: save_output(save_path_line_edit.text()))

            # -------------------------------------------------------
            # adding widgets to the global layout
            # -------------------------------------------------------
            self.layout.addWidget(self.generate_table_btn)

            self.layout.addWidget(order_button)
            self.layout.addWidget(annotate_btn)
            self.layout.addWidget(save_path_line_edit)
            self.layout.addWidget(save_btn)
            self.layout.addWidget(self.table)

            self.generate_table_btn.clicked.connect(generate_new_model)


# https://www.pythonguis.com/faq/editing-pyqt-tableview/
class MyTableModel(QtCore.QAbstractTableModel):

    # def __init__(self, pandas_dataframe, colors):
    def __init__(self, pandas_dataframe, get_color):
        super().__init__()

        self.dataframe = pandas_dataframe
        self.get_color = get_color
        # self.colors = colors
        # self.colors_ordered = deepcopy(self.colors)
        # self.dataframe.insert(3, "colors", self.colors)

    def rowCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[1]

    def data(self, QModelIndex, role=None):

        if role == Qt.BackgroundRole and QModelIndex.column() == 0:

            # color = self.colors_ordered[QModelIndex.row()]
            color = self.get_color(self.dataframe.index[QModelIndex.row()])
            if color is None:
                color = np.array([0.0, 0.0, 0.0, 0.0])
            r, g, b, a = (255 * color).astype(int)
            # print(f"Color is {r,g,b,a}")
            return QBrush(QColor(r, g, b, alpha=a))

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
        if role == Qt.EditRole:
            self.dataframe.iloc[index.row(), index.column()] = value
            return True
        return False

    def flags(self, index):
        # label = Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsEditable
        label = Qt.ItemIsEnabled | Qt.ItemIsEditable
        rest = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if index.column() == 0:
            return Qt.ItemIsEnabled
        elif index.column() == 1:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # https://stackoverflow.com/questions/28660287/sort-qtableview-in-pyqt5
    def sort(self, column, order):

        self.layoutAboutToBeChanged.emit()
        #
        # self.merged_frame = pd.concat([self.dataframe, pd.DataFrame({"colors": self.colors})], axis=1)
        # self.merged_frame = self.merged_frame.sort_values(by=column, ascending=(order == Qt.AscendingOrder))
        # self.dataframe = self.merged_frame.iloc[:, :-1]
        # self.colors_ordered = list(self.merged_frame.iloc[:, -1])
        self.dataframe.sort_values(by=column, ascending=(order == Qt.AscendingOrder), inplace=True)
        print(self.dataframe)

        self.layoutChanged.emit()


def layers2dict(viewer):
    names = [layer.name for layer in viewer.layers]
    res = {}
    for ind, img in enumerate(viewer.layers):
        res[names[ind]] = img

    return res

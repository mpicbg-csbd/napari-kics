from math import hypot

import numpy as np
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from skimage.measure import regionprops

from ..models.estimates_table_model import EstimatesTableModel
from ..utils import ChromosomeLabel, get_img, guess_chromosome_labels, replace_label


class OrderWidget(QVBoxLayout):
    sigOrderChanged = QtCore.Signal()

    def __init__(self, viewer, table):
        super().__init__()

        # basic state
        self.viewer = viewer
        self.table = table

        # list to store the reordering sequence
        self.order = []
        self.order_new = []
        self.order_layer = None

        # button configuration
        self.guess_order_button = QPushButton("Automatically guess order")
        self.guess_order_button.clicked.connect(
            lambda e: self.guess_chromosome_labels()
        )

        self.manual_order_button = QPushButton("Manual labelling")
        self.manual_order_button.setCheckable(True)
        self.manual_order_button.clicked.connect(
            lambda e: self.manual_order_button.setDown(
                self.manual_order_button.isChecked()
            )
        )
        self.manual_order_button.clicked.connect(lambda e: self.toggle_ordering_mode())

        self.buttons_container = QHBoxLayout()
        self.buttons_container.addWidget(self.guess_order_button)
        self.buttons_container.addWidget(self.manual_order_button)

        # description label
        self.descr_label = QLabel("3. Adjust the label order:")

        # layout
        self.addWidget(self.descr_label)
        self.addLayout(self.buttons_container)
        self.setSpacing(5)

    def guess_chromosome_labels(self):
        print("[guess_chromosome_labels]: guessing...")
        self.label_layer = get_img("labelled", self.viewer)
        props = regionprops(self.label_layer.data)
        bounding_boxes = [rp.bbox for rp in props]
        img_labels = [rp.label for rp in props]
        try:
            chr_labels = guess_chromosome_labels(bounding_boxes)
        except Exception as e:
            raise Exception(f"Guessing chromosome labels failed: {e}")

        get_row_index = self.table.model().dataframe.index.get_loc
        label_col = EstimatesTableModel.columns.get_loc("label")
        with self.table.model().bulkChanges() as bulkChanges:
            for img_label, chr_label in zip(img_labels, chr_labels):
                label_row = get_row_index(img_label)
                bulkChanges.setData(value=chr_label, row=label_row, column=label_col)

        self.table.update()
        self.sort_table_by_label()
        self.sigOrderChanged.emit()
        print("[guess_chromosome_labels]: success")

    def order_drag_callback(self, label_layer, event):
        """label layer drag callback to remove the labels that have been
        crossed-out (added to the self.order list)"""

        print("[drag_callback]: drag started")
        curr_order = []

        def maybe_add_label_at(position):
            position = np.array(position, dtype=np.int_)

            if not ((0 < position) & (position < label_layer.data.shape)).all():
                # position out of bounds
                return

            y, x = position
            curr_label = label_layer.data[y, x]

            if (
                curr_label != 0
                and curr_label is not None
                and (len(curr_order) == 0 or curr_order[-1] != curr_label)
            ):
                print(f"[drag_callback]: removing {curr_label} marked at {position}")
                replace_label(label_layer, curr_label, 0)
                curr_order.append(curr_label)

        def add_labels_on_line(from_pos, to_pos):
            # vector pointing from from_pos to to_pos
            delta = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])
            # increment vector that has unit length
            increment = (
                delta[0] / hypot(*delta),
                delta[1] / hypot(*delta),
            )

            # while delta and increment point in the same direction
            while delta[0] * increment[0] + delta[1] * increment[1] > 0:
                # see if we find a new label
                maybe_add_label_at(from_pos)
                # move one step further
                from_pos = (from_pos[0] + increment[0], from_pos[1] + increment[1])
                delta = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])

        yield

        while event.type == "mouse_move":
            if "Shift" in event.modifiers:
                if event.last_event is not None:
                    add_labels_on_line(event.last_event.position, event.position)
                maybe_add_label_at(event.position)
            yield

        print(f"[drag_callback]: curr order is {curr_order}")
        if len(curr_order) > 0:
            self.order_new.append(curr_order)

    def parse_recent_step(self, label_layer):
        """a function to parse the recent history step to extract the recent
        changes in the label layer"""

        print("parse recent step")

        print(f"undo history\n {label_layer._undo_history}")
        print(f"redo history\n {label_layer._redo_history}")

        if len(label_layer._undo_history) != 0:
            recent_step = label_layer._undo_history[-1][-1]
            label = recent_step[1][0]

            if label not in self.order:
                self.order.append(label)
            else:
                recent_step = label_layer._redo_history[-1][-1]
                label = recent_step[1][0]
                self.order.remove(label)

                # order new
                last_list = self.order_new[-1]
                last_list.remove(label)
                if len(last_list) == 0:
                    self.order_new.pop(-1)

        else:
            recent_step = self.label_layer._redo_history[-1][-1]
            label = recent_step[1][0]
            self.order.remove(label)

            # order new
            last_list = self.order_new[-1]
            last_list.remove(label)
            if len(last_list) == 0:
                self.order_new.pop(-1)

        print(f"recent label: {label}")
        print(f"order: {self.order}")
        print(f"order_new: {self.order_new}")

    def activate_ordering_mode(self):
        """create the new label layer and allow relabelling"""

        self.label_layer = get_img("labelled", self.viewer)
        self.order.clear()

        # make all the existing layers invisible
        self.visible_layers = set()
        for layer in self.viewer.layers:
            if layer.visible:
                self.visible_layers.add(layer)
                layer.visible = False

        # add a new auxiliary ordering layer
        self.order_layer = self.viewer.add_labels(
            self.label_layer.data.copy(), name="ordering"
        )
        self.order_layer.editable = False
        self.order_layer.mouse_drag_callbacks.append(self.order_drag_callback)

        # attach the event listener
        self.order_layer.events.set_data.connect(
            lambda x: self.parse_recent_step(self.order_layer)
        )

    def deactivate_ordering_mode(self):
        """remove the auxiliary layer and update the current labels according
        to the generated relabeling"""

        # delete the auxiliary ordering layer
        ind = self.viewer.layers.index(self.order_layer)
        self.viewer.layers.pop(ind)
        self.order_layer = None

        # make other layers visible
        for layer in self.visible_layers:
            layer.visible = True
        self.visible_layers = set()

        print(f"order is {self.order}")

        if len(self.order) > 0:
            print("relabelling")

            get_row_index = self.table.model().dataframe.index.get_loc
            label_col = EstimatesTableModel.columns.get_loc("label")
            with self.table.model().bulkChanges() as bulkChanges:
                for ind, label_list in enumerate(self.order_new):
                    for subind, label in enumerate(label_list):
                        chr_label = ChromosomeLabel(ind + 1, subind, None, None)
                        label_row = get_row_index(label)
                        bulkChanges.setData(
                            value=chr_label, row=label_row, column=label_col
                        )

                unprocessed_labels = (
                    set(list(self.table.model().dataframe.index))
                    - set(self.order)
                    - {0}
                )

                for label in unprocessed_labels:
                    label_row = get_row_index(label)
                    bulkChanges.setData(
                        value="unassigned", row=label_row, column=label_col
                    )

        self.order = []
        self.order_new = []
        self.table.update()
        self.sort_table_by_label()
        self.sigOrderChanged.emit()

    def toggle_ordering_mode(self):
        """switch between the modes"""

        if self.order_layer is None:
            self.activate_ordering_mode()
            self.manual_order_button.setDown(True)
        else:
            self.deactivate_ordering_mode()
            self.manual_order_button.setDown(False)

    def sort_table_by_label(self):
        label_col = EstimatesTableModel.columns.get_loc("label")
        self.table.sortByColumn(label_col, Qt.AscendingOrder)

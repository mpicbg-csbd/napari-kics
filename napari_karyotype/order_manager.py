from copy import deepcopy

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QLabel
from napari_karyotype.utils import get_img


class OrderManager(QVBoxLayout):

    def __init__(self, viewer, table):

        super().__init__()

        self.viewer = viewer

        self.table = table

        self.order = []

        self.order_button = QPushButton("Adjust labelling order")
        self.order_button.setCheckable(True)

        self.order_button.clicked.connect(lambda e: self.order_button.setDown(self.order_button.isChecked()))


        def toggle_ordering_mode(flag):
            if flag:
                self.activate_ordering_mode()
            else:
                self.deactivate_ordering_mode()

        self.order_button.clicked.connect(lambda e: toggle_ordering_mode(self.order_button.isChecked()))

        self.descr_label = QLabel("4. Interactively adjust the label order -\n- activate the button and paint over the image with Alt + Left click:")

        self.addWidget(self.descr_label)
        self.addWidget(self.order_button)
        self.setSpacing(5)

    def order_drag_callback(self, label_layer, event):

        yield

        while event.type == "mouse_move":
            if "Alt" in event.modifiers:
                curr_label = label_layer.get_value(event.position)

                if curr_label != 0 and curr_label is not None:
                    label_layer.fill(event.position, 0)

            yield

    def parse_recent_step(self, label_layer):

        print(f"parse recent step")

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


        else:
            recent_step = self.label_layer._redo_history[-1][-1]
            label = recent_step[1][0]
            self.order.remove(label)

        print(f"recent label: {label}")
        print(f"order: {self.order}")

    def activate_ordering_mode(self):

        self.label_layer = get_img("labelled", self.viewer)

        self.order.clear()

        # make all the existing layers invisible
        for layer in self.viewer.layers:
            layer.visible = 0

        # add a new auxiliary ordering layer
        ordering_label_layer = self.viewer.add_labels(deepcopy(self.label_layer.data), name="ordering")
        ordering_label_layer.editable = False
        ordering_label_layer.mouse_drag_callbacks.append(self.order_drag_callback)

        # attach the event listener
        ordering_label_layer.events.set_data.connect(lambda x: self.parse_recent_step(ordering_label_layer))

    def deactivate_ordering_mode(self):

        # delete the auxiliary ordering layer
        names = [layer.name for layer in self.viewer.layers]
        ind = names.index("ordering")
        self.viewer.layers.pop(ind)

        # make other layers visible
        for layer in self.viewer.layers:
            layer.visible = 1

        print(f"order is {self.order}")

        if len(self.order) > 0:

            print("relabelling")
            for ind, label in enumerate(self.order):
                self.table.model().dataframe.at[label, "label"] = ind + 1

            unprocessed_labels = set(list(self.table.model().dataframe.index)) - set(self.order) - {0}

            for label in unprocessed_labels:
                self.table.model().dataframe.at[label, "label"] = 9999

        self.table.update()

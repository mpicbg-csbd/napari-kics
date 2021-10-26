from copy import deepcopy


class OrderManager():

    def __init__(self, viewer, label_layer, table):

        self.viewer = viewer
        self.label_layer = label_layer
        self.table = table

        self.order = []

    def order_drag_callback(self, event):

        yield

        while event.type == "mouse_move":
            if "Alt" in event.modifiers:
                curr_label = self.label_layer.get_value(event.position)

                if curr_label != 0 and curr_label is not None:
                    self.label_layer.fill(event.position, 0)

            yield

    def parse_recent_step(self):

        print(f"parse recent step")

        print(f"undo history\n {self.label_layer._undo_history}")
        print(f"redo history\n {self.label_layer._redo_history}")

        if len(self.label_layer._undo_history) != 0:
            recent_step = self.label_layer._undo_history[-1][-1]
            label = recent_step[1][0]

            if label not in self.order:
                self.order.append(label)
            else:
                recent_step = self.label_layer._redo_history[-1][-1]
                label = recent_step[1][0]
                self.order.remove(label)


        else:
            recent_step = self.label_layer._redo_history[-1][-1]
            label = recent_step[1][0]
            self.order.remove(label)

        print(f"recent label: {label}")
        print(f"order: {self.order}")

    def activate_ordering_mode(self):

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
                self.table.model().dataframe.at[label, 1] = ind + 1

            unprocessed_labels = set(list(self.table.model().dataframe.index)) - set(self.order) - {0}

            for label in unprocessed_labels:
                self.table.model().dataframe.at[label, 1] = 9999

        self.table.update()

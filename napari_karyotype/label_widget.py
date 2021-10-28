from qtpy.QtWidgets import QTableView, QAbstractItemView, QPushButton, QVBoxLayout, QLabel
from qtpy.QtCore import Qt

import numpy as np
import pandas as pd
from skimage.measure import regionprops

from napari_karyotype.utils import get_img
from napari_karyotype.table_model import PandasTableModel
from napari_karyotype.label_history_processor import LabelHistoryProcessor


class LabelWidget(QVBoxLayout):

    def __init__(self, viewer):
        super().__init__()

        self.viewer = viewer

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

            self.label_layer = get_img("labelled", self.viewer)
            self.label_manager = LabelHistoryProcessor(get_img("labelled", self.viewer))
            self.generate_table()
            self.label_layer.events.set_data.connect(lambda x: self.update_table())

        labeling_descr_label = QLabel(
            "3. Apply label function to assign a unique integer id to each connected component:")
        label_btn = QPushButton("Label")
        label_btn.clicked.connect(lambda e: label_wrapper())

        self.addWidget(labeling_descr_label)
        self.addWidget(label_btn)
        self.setSpacing(5)

        # initializing the table with a dummy (empty) dataframe
        self.table = QTableView()
        self.table.setSortingEnabled(True)
        # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        dummy_frame = pd.DataFrame()
        dummy_frame["0"] = [""] * 10
        dummy_frame["1"] = [""] * 10
        dummy_frame["2"] = [""] * 10
        dummy_frame.columns = ["color", "label", "area"]

        self.table.setModel(PandasTableModel(dummy_frame, lambda x: None))
        self.table.setDisabled(True)

        self.viewer.bind_key("Backspace", self.delete_selected_labels)

        self.addWidget(self.table)

    def generate_table(self):
        rp = regionprops(self.label_layer.data + 1)

        res = np.array([(r.label - 1, r.area, r.coords[0]) for r in rp], dtype=object)
        res = np.array(sorted(res, key=lambda x: x[0]))
        l = [("", res[ind, 0], res[ind, 1]) for ind in range(len(res))]

        frame = pd.DataFrame(l)
        frame.columns = ["color", "label", "area"]
        self.table.setModel(PandasTableModel(frame, self.label_layer.get_color))
        self.table.sortByColumn(2, Qt.DescendingOrder)
        self.table.setDisabled(False)

        def sync_selection_table2viewer(e):
            indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
            self.label_layer.selected_label = self.table.model().dataframe.index[indices[0]]

        self.table.clicked.connect(sync_selection_table2viewer)

        def sync_selection_viewer2table(e):
            sl = self.label_layer.selected_label

            if sl in self.table.model().dataframe.index:
                ind = self.table.model().dataframe.index.get_loc(sl)
                self.table.selectRow(ind)

        self.label_layer.events.selected_label.connect(sync_selection_viewer2table)

    def delete_selected_labels(self, e):
        indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
        coords = [np.where(self.label_layer.data == label) for label in
                  self.table.model().dataframe.index[indices]]
        coords_to_fill = [(co[0][0], co[1][0]) for co in coords]

        print(f"[backspace]: removing indices {indices}")

        [self.label_layer.fill(coord, 0) for coord in coords_to_fill]

    def update_table(self):

        res_dict = self.label_manager.process_history_step()

        print(f"res_dict is {res_dict}")

        for (label, increment) in res_dict.items():

            if not (label in self.table.model().dataframe.index):
                print(f"label {label} is not in the dataframe")
                self.table.model().dataframe = self.table.model().dataframe.append(
                    # pd.DataFrame([["", label, increment]], index=[label]))
                    pd.DataFrame([["", label, increment]], columns=["color", "label", "area"], index=[label]))
                print(f"now it is \n{self.table.model().dataframe}")

            else:
                self.table.model().dataframe.loc[label, "area"] += increment

                if (self.table.model().dataframe.loc[label, "area"] == 0):
                    self.table.model().dataframe.drop(label, inplace=True)
                    print(f"label {label} is set to 0")
            self.table.update()
            self.table.sortByColumn(2, Qt.DescendingOrder)

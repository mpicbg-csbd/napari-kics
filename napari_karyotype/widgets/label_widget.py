from qtpy.QtWidgets import (
    QTableView,
    QAbstractItemView,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSpinBox,
    QFormLayout,
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QBrush

import numpy as np
import pandas as pd
from skimage.measure import regionprops

from napari_karyotype.models.table_model import PandasTableModel
from napari_karyotype.utils import get_img, LabelHistoryProcessor


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

            self.viewer.layers["thresholded"].visible = False

            try:
                self.viewer.layers["labelled"].data = labelled
                self.viewer.layers["labelled"].visible = True
            except KeyError:
                self.viewer.add_labels(labelled, name="labelled", opacity=0.7)

            self.label_layer = get_img("labelled", self.viewer)
            self.label_manager = LabelHistoryProcessor(self.label_layer)
            self.generate_table()
            self.label_layer.events.set_data.connect(lambda x: self.update_table())

        labeling_descr_label = QLabel(
            "3. Apply label function to assign a unique integer id to each connected component:"
        )
        self.addWidget(labeling_descr_label)

        genome_specs_form = QFormLayout()
        genome_size_label = QLabel("genome size:")

        self.genome_size_input = QSpinBox()
        self.genome_size_input.setRange(0, 500_000)
        self.genome_size_input.setStepType(QSpinBox.AdaptiveDecimalStepType)
        self.genome_size_input.setSuffix(" Mb")
        self.genome_size_input.setSpecialValueText("undefined")
        self.genome_size_input.valueChanged.connect(
            lambda value: setattr(self.table.model(), "genomeSize", value)
        )
        genome_specs_form.addRow("genome size:", self.genome_size_input)

        self.ploidy_input = QSpinBox()
        self.ploidy_input.setRange(1, 64)
        self.ploidy_input.setValue(2)
        self.ploidy_input.valueChanged.connect(
            lambda value: setattr(self.table.model(), "ploidy", value)
        )
        genome_specs_form.addRow("ploidy:", self.ploidy_input)

        self.addLayout(genome_specs_form)

        label_btn = QPushButton("Label")
        label_btn.clicked.connect(lambda e: label_wrapper())

        self.addWidget(label_btn)
        self.setSpacing(5)

        # initializing the table with a dummy (empty) dataframe
        self.table = QTableView()
        self.table.setSortingEnabled(True)
        # select rows only: https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        def label2rgba(label):
            if hasattr(self, "label_layer"):
                return self.label_layer.get_color(label)
            else:
                return None

        self.table.setModel(PandasTableModel(label2rgba))
        self.table.setDisabled(True)

        self.viewer.bind_key("Backspace", self.delete_selected_labels)

        self.addWidget(self.table)

    def generate_table(self):
        rp = regionprops(self.label_layer.data)

        res = np.array(
            [(r.label, r.area, r.coords[0], r.bbox) for r in rp],
            dtype=object,
        )
        res = np.array(sorted(res, key=lambda x: x[0]))

        self.table.model().initData(
            ids=res[:, 0],
            labels=[str(label) for label in res[:, 0]],
            areas=res[:, 1],
            coords=res[:, 2],
            bboxes=res[:, 3],
            genomeSize=self.genome_size_input.value(),
            ploidy=self.ploidy_input.value(),
        )

        self.table.sortByColumn(
            PandasTableModel.columns.get_loc("area"), Qt.DescendingOrder
        )
        self.table.setDisabled(False)

        def sync_selection_table2viewer(e):
            indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
            if len(indices) > 0:
                self.label_layer.selected_label = self.table.model().dataframe.index[
                    indices[0]
                ]

        self.table.clicked.connect(sync_selection_table2viewer)

        def sync_selection_viewer2table(e):
            sl = self.label_layer.selected_label

            if sl in self.table.model().dataframe.index:
                ind = self.table.model().dataframe.index.get_loc(sl)
                self.table.selectRow(ind)

        self.label_layer.events.selected_label.connect(sync_selection_viewer2table)

    def delete_selected_labels(self, e, *, new_label=0):
        indices = np.unique([qi.row() for qi in self.table.selectedIndexes()])
        labels = self.table.model().dataframe.index[indices]

        print(f"[backspace]: removing indices {indices}")

        matches = self.label_layer.data == labels[0]
        for label in labels[1:]:
            matches |= self.label_layer.data == label
        match_indices = np.nonzero(matches)
        self.label_layer._save_history(
            (
                match_indices,
                np.array(self.label_layer.data[match_indices], copy=True),
                new_label,
            )
        )
        self.label_layer.data[match_indices] = new_label
        self.label_layer.refresh()

    def update_table(self):
        recent_changes = self.label_manager.recent_changes()
        print(f"[update_table] recent_changes is {recent_changes}")

        for (label, change) in recent_changes.items():
            if label == 0:
                # ignore background label
                continue

            if not (label in self.table.model().dataframe.index):
                print(f"label {label} is not in the dataframe")
                self.table.model().dataframe.loc[label] = {
                    "color": "",
                    "label": str(label),
                    "factor": 1,
                    "area": change.area_diff,
                    "size": 0,
                    "_coord": change.coord(),
                    "_bbox": change.bbox(),
                }
                print(f"now it is \n{self.table.model().dataframe}")

            elif change.area_diff != 0:
                self.table.model().dataframe.loc[label, "area"] += change.area_diff

                if change.area_diff > 0:
                    # label area was extended
                    self.table.model().dataframe.at[label, "_bbox"] = change.bbox(
                        self.table.model().dataframe.loc[label, "_bbox"]
                    )

                elif self.table.model().dataframe.at[label, "area"] > 0:
                    # label area was reduced but still exists
                    new_coords = np.argwhere(self.label_layer.data == label)
                    new_bbox = (
                        *np.amin(new_coords, axis=0),
                        *np.amax(new_coords, axis=0),
                    )

                    self.table.model().dataframe.at[label, "_coord"] = new_coords[0]
                    self.table.model().dataframe.at[label, "_bbox"] = new_bbox
                else:
                    # label area was reduced completely
                    self.table.model().dataframe.drop(label, inplace=True)
                    print(f"label {label} was removed")

        self.table.update()
        self.table.sortByColumn(2, Qt.DescendingOrder)

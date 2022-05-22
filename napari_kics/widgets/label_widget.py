from os import environ

import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QVBoxLayout,
)
from skimage.measure import regionprops

from ..models.estimates_table_model import EstimatesTableModel
from ..utils import LabelHistoryProcessor, get_img, replace_label


class LabelWidget(QVBoxLayout):
    def __init__(self, viewer, make_thresholded_image):
        super().__init__()

        self.viewer = viewer
        self.make_thresholded_image = make_thresholded_image
        self.setAlignment(Qt.AlignLeft)

        # the actual function
        def label(img):
            from scipy.ndimage import label

            return label(img)[0]

        # wrapper with napari updates
        def label_wrapper(refresh=False):
            if not refresh:
                if "thresholded" not in self.viewer.layers:
                    self.make_thresholded_image()

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
                    self.label_layer.events.set_data.connect(
                        lambda x: self.update_table()
                    )

            # self.label_layer = get_img("labelled", self.viewer)
            # self.label_manager = LabelHistoryProcessor(self.label_layer)
            # self.generate_table()
            # self.label_layer.events.set_data.connect(lambda x: self.update_table())

            self.init_table_from_layer()

        # widget head label
        labeling_descr_label = QLabel(
            "2. Apply label function to assign a unique integer id to each            "
            " connected component:"
        )
        self.addWidget(labeling_descr_label)

        # genome size QFormLayout
        genome_specs_form = QFormLayout()

        genome_size_label = QLabel("- genome size:")
        genome_size_label.setAlignment(Qt.AlignLeft)

        self.genome_size_input = QSpinBox()
        self.genome_size_input.setRange(0, 500_000)
        self.genome_size_input.setStepType(QSpinBox.AdaptiveDecimalStepType)
        self.genome_size_input.setSuffix(" Mb")
        self.genome_size_input.setSpecialValueText("undefined")
        if "kt_genome_size" in environ:
            self.genome_size_input.setValue(int(environ["kt_genome_size"]))
        self.genome_size_input.valueChanged.connect(
            lambda value: setattr(self.table.model(), "genomeSize", value)
        )

        self.genome_size_input.setFixedWidth(200)
        self.genome_size_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        genome_specs_form.addRow(genome_size_label, self.genome_size_input)
        genome_specs_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        genome_specs_form.setLabelAlignment(Qt.AlignLeft)
        genome_specs_form.setFormAlignment(Qt.AlignLeft)
        genome_specs_form.setContentsMargins(0, 5, 0, 5)

        self.addLayout(genome_specs_form)

        # label and refresh buttons
        label_btn = QPushButton("Label")
        label_btn.clicked.connect(lambda e: label_wrapper())

        refresh_btn = QPushButton("Refresh table from layer")
        refresh_btn.clicked.connect(lambda e: label_wrapper(refresh=True))

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(label_btn)
        buttons_layout.addWidget(refresh_btn)

        self.addLayout(buttons_layout)
        self.setSpacing(5)

        # initializing the table with a dummy (empty) dataframe
        self.table = QTableView()
        self.table.setSortingEnabled(True)
        # select rows only:
        # https://stackoverflow.com/questions/3861296/how-to-select-row-in-qtableview
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(300)

        def label2rgba(label):
            if hasattr(self, "label_layer"):
                return self.label_layer.get_color(label)
            else:
                return None

        self.table.setModel(EstimatesTableModel(label2rgba))
        self.table.setDisabled(True)

        self.viewer.bind_key("Backspace", self.delete_selected_labels)

        self.addWidget(self.table)

    def init_table_from_layer(self):
        """Initialize the label table with the data from the label layer
        (apply regionprops to layer.data)"""

        rp = regionprops(self.label_layer.data)

        res = np.array(
            [(r.label, r.area, r.bbox) for r in rp],
            dtype=object,
        )
        res = np.array(sorted(res, key=lambda x: x[0]))

        self.table.model().initData(
            ids=res[:, 0],
            labels=[str(label) for label in res[:, 0]],
            areas=res[:, 1],
            bboxes=res[:, 2],
            genomeSize=self.genome_size_input.value(),
        )

    def generate_table(self):

        self.init_table_from_layer()
        self.table.sortByColumn(
            EstimatesTableModel.columns.get_loc("area"), Qt.DescendingOrder
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

        if len(indices) > 0:
            print(f"[backspace]: removing indices {indices}")
            labels = self.table.model().dataframe.index[indices]
            replace_label(self.label_layer, labels, new_label)

    def update_table(self):
        recent_changes = self.label_manager.recent_changes()
        print(f"[update_table] recent_changes is {recent_changes}")

        with self.table.model().bulkChanges() as bulkChanges:
            for label, change in recent_changes.items():
                if label == 0:
                    # ignore background label
                    continue

                if not (label in self.table.model().dataframe.index):
                    print(f"label {label} is not in the dataframe")
                    bulkChanges.insertRow(
                        id=label,
                        area=change.area_diff,
                        bbox=change.bbox(),
                    )
                    print(f"now it is \n{self.table.model().dataframe}")

                elif change.area_diff != 0:
                    # TODO use setData instead
                    curr_value = self.table.model().dataframe.loc[label, "area"]
                    row = self.table.model().dataframe.index.get_loc(label)
                    column = self.table.model().dataframe.columns.get_loc("area")
                    self.table.model().setData(
                        None, curr_value + change.area_diff, row=row, column=column
                    )

                    if change.area_diff > 0:
                        # label area was extended
                        bulkChanges.setData(
                            value=change.bbox(
                                self.table.model().dataframe.loc[label, "_bbox"]
                            ),
                            row=self.table.model().dataframe.index.get_loc(label),
                            column=EstimatesTableModel.columns.get_loc("_bbox"),
                        )

                    elif self.table.model().dataframe.at[label, "area"] > 0:
                        # label area was reduced but still exists
                        new_coords = np.argwhere(self.label_layer.data == label)
                        new_bbox = (
                            *np.amin(new_coords, axis=0),
                            *np.amax(new_coords, axis=0),
                        )

                        bulkChanges.setData(
                            value=new_bbox,
                            row=self.table.model().dataframe.index.get_loc(label),
                            column=EstimatesTableModel.columns.get_loc("_bbox"),
                        )
                    else:
                        # label area was reduced completely
                        bulkChanges.removeRow(label)
                        print(f"label {label} was removed")

        self.table.update()
        # self.table.model()._updateSizeColumn()
        self.table.sortByColumn(
            EstimatesTableModel.columns.get_loc("area"), Qt.DescendingOrder
        )

        # self.layout().setAlignment(Qt.AlignLeft)

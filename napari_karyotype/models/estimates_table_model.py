import numpy as np
import pandas as pd
from qtpy import QtCore
from qtpy.QtGui import QBrush, QColor
from napari_karyotype.utils.guess_chromosome_labels import ChromosomeLabel


# based on https://www.pythonguis.com/faq/editing-pyqt-tableview/
class EstimatesTableModel(QtCore.QAbstractTableModel):
    sigChange = QtCore.Signal(object, object, object)

    columns = pd.Index(["color", "label", "count", "area", "size", "_bbox"])
    num_visible_columns = len([c for c in columns if not c.startswith("_")])
    """Number of empty rows to show before the table is filled with real data."""
    num_sample_rows = 10

    def __init__(self, id2rgba):
        super().__init__()

        self.id2rgba = id2rgba
        self.dataframe = None
        self._genomeSize = 0

    def initData(
        self,
        ids,
        labels,
        areas,
        bboxes,
        counts=1,
        genomeSize=0,
    ):
        n = len(ids)
        self.dataframe = pd.DataFrame(
            {
                # color column has invisible content
                "color": np.empty(n, dtype=np.str_),
                "label": labels,
                "count": np.ones(n, dtype=np.int_)
                if isinstance(counts, int)
                else counts,
                "area": areas,
                # size will be computed from area by `update_size_column`
                "size": np.zeros(n, dtype=np.float_),
                "_bbox": bboxes,
            },
            index=ids,
        )
        self._genomeSize = genomeSize
        self._updateSizeColumn()
        self.sigChange.emit("dataframe", None, None)

    def hasData(self):
        return self.dataframe is not None

    def hasGenomeSize(self):
        return self.genomeSize > 0

    @property
    def genomeSize(self):
        return self._genomeSize

    @genomeSize.setter
    def genomeSize(self, value):
        old_value = self._genomeSize
        self._genomeSize = value
        self._updateSizeColumn()
        self.sigChange.emit("genomeSize", old_value, value)

    def rowCount(self, parent=None, *args, **kwargs):
        if self.hasData():
            return self.dataframe.shape[0]
        else:
            return self.num_sample_rows

    def columnCount(self, parent=None, *args, **kwargs):
        return self.num_visible_columns

    def data(self, modelIndex=None, role=None, row=None, column=None):
        if modelIndex is not None:
            row = modelIndex.row()
            column = modelIndex.column()
        elif row is None or column is None:
            raise ValueError("neither modelIndex nor row and column are given")

        header = self.columns[column]

        if not self.hasData():
            # show empty cells until real data is available
            return QtCore.QVariant()
        elif role == QtCore.Qt.BackgroundRole and header == "color":
            # color column is gets the adequate background color
            color = self.id2rgba(self.dataframe.index[row])
            if color is None:
                color = np.array([0.0, 0.0, 0.0, 0.0])
            r, g, b, a = (255 * color).astype(int)

            return QBrush(QColor(r, g, b, alpha=a))
        elif role is None or role == QtCore.Qt.DisplayRole:
            # other columns are transformed to display strings
            return self._formatValue(header, self.dataframe.iloc[row, column])
        else:
            # invisible
            return QtCore.QVariant()

    def _formatValue(self, column, value):
        assert self.hasData()

        if column == "area":
            return "{:d}".format(value)

        elif column == "size":
            if self.hasGenomeSize():
                return "{:.1f} Mb".format(value)
            else:
                return "{:.2f}%".format(value)

        else:
            return str(value)

    def headerData(self, p_int, Qt_Orientation, role=None):
        if role == QtCore.Qt.DisplayRole:
            if Qt_Orientation == QtCore.Qt.Horizontal:
                return self.columns[p_int]
            else:
                return p_int

    def setData(
        self, index=None, value=None, role=QtCore.Qt.EditRole, row=None, column=None
    ):
        if value is None:
            raise ValueError("value is mandatory")

        if index is not None:
            row = index.row()
            column = index.column()
        elif row is None or column is None:
            raise ValueError("neither index nor row and column are given")

        if self.hasData() and role == QtCore.Qt.EditRole:
            header = self.columns[column]

            old_value = self.dataframe.iat[row, column]
            new_value = self._convert(header, value)
            self.dataframe.iat[row, column] = new_value

            if header in ("area", "count"):
                self._updateSizeColumn()
            elif header == "label":
                self._updateCountColumn()
            self.sigChange.emit((row, column), old_value, new_value)
            return True
        else:
            return False

    def _convert(self, column, value):
        assert self.hasData()

        if column == "label":
            if isinstance(value, ChromosomeLabel):
                return value

            try:
                return ChromosomeLabel.from_string(value)
            except ValueError:
                return value

        elif column == "count":
            try:
                return int(value)
            except ValueError:
                raise ValueError("count must be an integer")
            if value <= 0:
                raise ValueError("count must be at least 1")

        else:
            return value

    def insertRow(self, id, area, bbox, label=None, count=1):
        new_pos = len(self.dataframe)
        self.beginInsertRows(QtCore.QModelIndex(), new_pos, new_pos)
        self.dataframe.loc[id] = {
            "color": "",
            "label": str(id) if label is None else label,
            "count": count,
            "area": area,
            "size": 0,
            "_bbox": bbox,
        }
        self.endInsertRows()
        self._updateSizeColumn()
        self.sigChange.emit("insertRow", None, self.dataframe.loc[id, :])

    def removeRow(self, id):
        rm_pos = self.dataframe.index.get_loc(id)
        deleted_row = self.dataframe.loc[id, :]
        self.beginRemoveRows(QtCore.QModelIndex(), rm_pos, rm_pos)
        self.dataframe.drop(id, inplace=True)
        self.endRemoveRows()
        self._updateSizeColumn()
        self.sigChange.emit("removeRow", deleted_row, None)

    def _updateSizeColumn(self):
        if not self.hasData():
            return

        gs = self.genomeSize if self.hasGenomeSize() else 100
        areas = self.dataframe["area"]
        counts = self.dataframe["count"]
        scaled_areas = areas / counts
        total_area = sum(scaled_areas)

        self.dataframe["size"] = scaled_areas / total_area * gs * counts

    def _updateCountColumn(self):
        if not self.hasData():
            return

        def get_key(label):
            if isinstance(label, ChromosomeLabel):
                return label.major
            else:
                return label

        counts = dict()
        for label in self.dataframe["label"]:
            key = get_key(label)
            count = counts.get(key, 0)
            counts[key] = count + 1

        for id, label in self.dataframe["label"].items():
            key = get_key(label)
            self.dataframe.at[id, "count"] = counts[key]

    def flags(self, index):
        if index.row() < 0 or index.column() < 0:
            return QtCore.Qt.NoItemFlags

        column = index.column()
        header = self.columns[column]

        if header == "color":
            return QtCore.Qt.ItemIsEnabled
        elif header == "label" or header == "count":
            return (
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEditable
            )
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    # https://stackoverflow.com/questions/28660287/sort-qtableview-in-pyqt5
    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        self.dataframe.sort_values(
            by=self.columns[column],
            ascending=(order == QtCore.Qt.AscendingOrder),
            inplace=True,
        )
        self.layoutChanged.emit()

import numpy as np
import pandas as pd
from qtpy import QtCore
from qtpy.QtGui import QBrush, QColor
from napari_karyotype.utils.guess_chromosome_labels import ChromosomeLabel


# based on https://www.pythonguis.com/faq/editing-pyqt-tableview/
class EstimatesTableModel(QtCore.QAbstractTableModel):
    sigChange = QtCore.Signal(object, object, object)

    columns = pd.Index(["color", "label", "factor", "area", "size", "_coord", "_bbox"])
    num_visible_columns = len([c for c in columns if not c.startswith("_")])
    """Number of empty rows to show before the table is filled with real data."""
    num_sample_rows = 10

    def __init__(self, id2rgba):
        super().__init__()

        self.id2rgba = id2rgba
        self.dataframe = None
        self._genomeSize = 0
        self._ploidy = 2

    def initData(
        self,
        ids,
        labels,
        areas,
        coords,
        bboxes,
        factors=1,
        genomeSize=0,
        ploidy=2,
    ):
        n = len(ids)
        self.dataframe = pd.DataFrame(
            {
                # color column has invisible content
                "color": np.empty(n, dtype=np.str_),
                "label": labels,
                "factor": np.ones(n, dtype=np.int_) if factors == 1 else factors,
                "area": areas,
                # size will be computed from area by `update_size_column`
                "size": np.zeros(n, dtype=np.float_),
                # FIXME coord is not used anymore (should be removed at some point)
                "_coord": coords,
                "_bbox": bboxes,
            },
            index=ids,
        )
        self._genomeSize = genomeSize
        self._ploidy = ploidy
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

    @property
    def ploidy(self):
        return self._ploidy

    @ploidy.setter
    def ploidy(self, value):
        old_value = self._ploidy
        self._ploidy = value
        self._updateSizeColumn()
        self.sigChange.emit("ploidy", old_value, value)

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

    def setData(self, index, value, role):
        if self.hasData() and role == QtCore.Qt.EditRole:
            row = index.row()
            column = index.column()
            header = self.columns[column]

            old_value = self.dataframe.iat[row, column]
            new_value = self._fromString(header, value)
            self.dataframe.iat[row, column] = new_value

            if header in ("area", "factor"):
                self._updateSizeColumn()
            self.sigChange.emit((row, column), old_value, new_value)
            return True
        else:
            return False

    def _fromString(self, column, value):
        assert self.hasData()

        if column == "label":
            try:
                return ChromosomeLabel.from_string(value)
            except ValueError:
                return value

        elif column == "factor":
            try:
                return int(value)
            except ValueError:
                raise ValueError("factor must be an integer")
            if value <= 0:
                raise ValueError("factor must be at least 1")

        else:
            return value

    def _updateSizeColumn(self):
        if not self.hasData():
            return

        ploidy = self.ploidy
        gs = self.genomeSize if self.hasGenomeSize() else 100
        areas = self.dataframe["area"]
        factors = self.dataframe["factor"]
        scaled_areas = areas * factors
        total_area = sum(scaled_areas)

        self.dataframe["size"] = scaled_areas / total_area * (gs * ploidy) / factors

    def flags(self, index):
        if index.row() < 0 or index.column() < 0:
            return QtCore.Qt.NoItemFlags

        column = index.column()
        header = self.columns[column]

        if header == "color":
            return QtCore.Qt.ItemIsEnabled
        elif header == "label" or header == "factor":
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

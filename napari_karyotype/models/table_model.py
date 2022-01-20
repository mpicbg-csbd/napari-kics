import numpy as np
from qtpy import QtCore
from qtpy.QtGui import QBrush, QColor


# based on https://www.pythonguis.com/faq/editing-pyqt-tableview/
class PandasTableModel(QtCore.QAbstractTableModel):
    sigChange = QtCore.Signal(int, int, object, object)

    # def __init__(self, pandas_dataframe, colors):
    def __init__(self, pandas_dataframe, get_color, cell_format={}):
        super().__init__()

        self.setDataframe(pandas_dataframe)
        self.get_color = get_color
        self.cell_format = cell_format

    def setDataframe(self, pandas_dataframe):
        self.dataframe = pandas_dataframe
        self._visIndex = [
            i if not col.startswith("_") else -1
            for i, col in enumerate(self.dataframe.columns)
        ]
        self._columnCount = sum(i >= 0 for i in self._visIndex)

    def rowCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self._columnCount

    def _dataIndex(self, visIndex):
        dataIndex = self._visIndex[visIndex]

        if dataIndex < 0:
            raise IndexError("visIndex out of range")

        return dataIndex

    def data(self, modelIndex=None, role=None, row=None, column=None):
        if modelIndex is not None:
            row = modelIndex.row()
            column = self._dataIndex(modelIndex.column())
        elif row is None or column is None:
            raise ValueError("neither modelIndex nor row and column are given")

        header = self.dataframe.columns[column]

        if role == QtCore.Qt.BackgroundRole and header == "color":
            # color column is gets the adequate background color
            color = self.get_color(self.dataframe.index[row])
            if color is None:
                color = np.array([0.0, 0.0, 0.0, 0.0])
            r, g, b, a = (255 * color).astype(int)

            return QBrush(QColor(r, g, b, alpha=a))
        elif role is None or role == QtCore.Qt.DisplayRole:
            # other columns are transformed to display strings
            cell = self.dataframe.iloc[row, column]
            fmt = self.cell_format.get(header, str)
            if isinstance(fmt, str):
                return fmt.format(cell)
            elif callable(fmt):
                return fmt(cell)
            else:
                raise ValueError(f"unexpected type of format: {type(fmt)}")
        else:
            # invisible
            return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, role=None):
        if role == QtCore.Qt.DisplayRole:
            if Qt_Orientation == QtCore.Qt.Horizontal:
                return self.dataframe.columns[self._dataIndex(p_int)]
            else:
                return p_int

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            old_value = self.dataframe.iat[index.row(), self._dataIndex(index.column())]
            self.dataframe.iat[index.row(), self._dataIndex(index.column())] = value
            self.sigChange.emit(
                index.row(), self._dataIndex(index.column()), old_value, value
            )
            return True
        return False

    def flags(self, index):
        if index.column() == 0:
            return QtCore.Qt.ItemIsEnabled
        elif index.column() == 1:
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
            by=self.dataframe.columns[self._dataIndex(column)],
            ascending=(order == QtCore.Qt.AscendingOrder),
            inplace=True,
        )
        self.layoutChanged.emit()

import numpy as np
from qtpy import QtCore
from qtpy.QtGui import QBrush, QColor


# based on https://www.pythonguis.com/faq/editing-pyqt-tableview/
class PandasTableModel(QtCore.QAbstractTableModel):

    # def __init__(self, pandas_dataframe, colors):
    def __init__(self, pandas_dataframe, get_color):
        super().__init__()

        self.dataframe = pandas_dataframe
        self.get_color = get_color

    def rowCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self.dataframe.shape[1]

    def data(self, QModelIndex, role=None):

        if role == QtCore.Qt.BackgroundRole and QModelIndex.column() == 0:

            color = self.get_color(self.dataframe.index[QModelIndex.row()])
            if color is None:
                color = np.array([0.0, 0.0, 0.0, 0.0])
            r, g, b, a = (255 * color).astype(int)

            return QBrush(QColor(r, g, b, alpha=a))

        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        return str(self.dataframe.iloc[QModelIndex.row(), QModelIndex.column()])

    def headerData(self, p_int, Qt_Orientation, role=None):

        if role == QtCore.Qt.DisplayRole:
            if Qt_Orientation == QtCore.Qt.Horizontal:
                return self.dataframe.columns[p_int]
            else:
                return p_int

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.dataframe.iloc[index.row(), index.column()] = value
            return True
        return False

    def flags(self, index):
        if index.column() == 0:
            return QtCore.Qt.ItemIsEnabled
        elif index.column() == 1:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    # https://stackoverflow.com/questions/28660287/sort-qtableview-in-pyqt5
    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        self.dataframe.sort_values(by=self.dataframe.columns[column], ascending=(order == QtCore.Qt.AscendingOrder), inplace=True)
        self.layoutChanged.emit()

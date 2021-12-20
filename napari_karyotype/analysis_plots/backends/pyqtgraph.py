import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, mkQApp, QtGui, QtCore


def do_plot(estimates, scaffoldSizes, matching, **kwargs):
    # TODO show tooltip on hover with scaff/estimate name/index, size diff, abs. sizes, ...
    app = mkQApp("Chromosome size estimation: analysis plots")
    main_window = MainWindow(estimates, scaffoldSizes, matching)
    app.exec_()


class MainWindow(QtWidgets.QMainWindow):
    """example application main window"""

    def __init__(self, estimates, scaffoldSizes, matching, *qtArgs, **qtKwargs):
        super(MainWindow, self).__init__(*qtArgs, **qtKwargs)

        self.estimates = estimates
        self.scaffoldSizes = scaffoldSizes
        self.matching = matching

        gridWidget = pg.GraphicsLayoutWidget(show=True)
        self.setCentralWidget(gridWidget)
        self.setWindowTitle("Chromosome size estimation: analysis plots")
        self.resize(600, 500)
        self.show()

        correlationMatrix = 1 + np.abs(
            np.atleast_2d(self.estimates).T - self.scaffoldSizes
        )
        n, m = correlationMatrix.shape
        # columns = ["A", "B", "C"]

        pg.setConfigOption(
            "imageAxisOrder", "row-major"
        )  # Switch default order to Row-major
        pg.setConfigOptions(antialias=True)

        correlationMatrixItem = CorrelationMatrixItem()
        # create transform to center the corner element on the origin, for any assigned image:
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)
        correlationMatrixItem.setTransform(alignPixelTransform)
        correlationMatrixItem.setImage(correlationMatrix)

        matchingPlotItem = pg.ScatterPlotItem(
            size=10,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(255, 255, 255, 120),
            hoverable=True,
            hoverPen=pg.mkPen("r", width=2),
            hoverBrush=pg.mkBrush(None),
        )
        # spots = [{"pos": (match[1], match[0]), "data": 1} for match in matching]
        matchingPlotItem.addPoints(
            pos=np.fliplr(self.matching), data=list(range(len(self.matching)))
        )
        # matchingPlotItem.sigClicked.connect(clicked)

        plotItem = gridWidget.addPlot()  # add PlotItem to the main GraphicsLayoutWidget
        plotItem.invertY(True)  # orient y axis to run top-to-bottom
        plotItem.setDefaultPadding(0.0)  # plot without padding data range
        plotItem.addItem(correlationMatrixItem)  # display correlationMatrixItem
        correlationMatrixItem.setParent(plotItem)
        # display correlationMatrixItem
        plotItem.addItem(matchingPlotItem)
        centralViewBox = plotItem.getViewBox()
        centralViewBox.setAspectLocked()
        # centralViewBox.setXRange(-0.5, min(n, m) - 0.5)
        # centralViewBox.setYRange(-0.5, min(n, m) - 0.5)

        # show full frame, label tick marks at top and left sides, with some extra space for labels:
        plotItem.showAxes(True, showValues=(True, True, False, False), size=20)

        # define major tick marks and labels:
        # ticks = [(idx, label) for idx, label in enumerate(columns)]
        # for side in ("left", "top", "right", "bottom"):
        #     plotItem.getAxis(side).setTicks(
        #         (ticks, [])
        #     )  # add list of major ticks; no minor ticks
        plotItem.getAxis("bottom").setHeight(
            10
        )  # include some additional space at bottom of figure

        colorMap = pg.colormap.get("magma")
        # generate an adjustabled color bar, initially spanning -1 to 1:
        bar = pg.ColorBarItem(
            values=(np.min(correlationMatrix), np.max(correlationMatrix)),
            colorMap=colorMap,
        )
        # bar.setLogMode(y=True)
        # link color bar and color map to correlationMatrixItem, and show it in plotItem:
        bar.setImageItem(correlationMatrixItem, insert_in=plotItem)

    def keyReleaseEvent(self, e):
        if e.key() == QtCore.Qt.Key.Key_Q:
            self.close()


class CorrelationMatrixItem(pg.ImageItem):
    def setParent(self, parent):
        self.parent = parent
        self.parent.setTitle("")

    def hoverEvent(self, event):
        """Show the position, pixel, and value under the mouse cursor."""
        if self.parent is None:
            return

        if event.isExit():
            self.parent.setTitle("")
            return

        pos = event.pos()
        i, j = pos.y(), pos.x()
        i = int(np.clip(i, 0, self.image.shape[0] - 1))
        j = int(np.clip(j, 0, self.image.shape[1] - 1))
        val = self.image[i, j]
        ppos = self.mapToParent(pos)
        x, y = ppos.x(), ppos.y()
        self.parent.setTitle(
            "pos: (%0.1f, %0.1f)  pixel: (%d, %d)  value: %.3g" % (x, y, i, j, val)
        )

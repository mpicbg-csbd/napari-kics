import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, mkQApp, QtGui, QtCore


def do_plot(estimates, scaffoldSizes, initialMatching, **kwargs):
    # TODO show tooltip on hover with scaff/estimate name/index, size diff, abs. sizes, ...

    app = mkQApp("Chromosome size estimation: analysis plots")

    # Switch default order to Row-major (in accordance with numpy)
    # Enable anti-aliasing for beautiful plots
    pg.setConfigOptions(antialias=True, imageAxisOrder="row-major")

    main_window = MainWindow(estimates, scaffoldSizes, initialMatching)
    app.exec_()


class MainWindow(QtWidgets.QMainWindow):
    """Main window for analysis plots."""

    def __init__(
        self,
        estimates,
        scaffoldSizes,
        initialMatching,
        *qtArgs,
        colorMap="magma",
        **qtKwargs
    ):
        super().__init__(*qtArgs, **qtKwargs)

        # store data that should be displayed
        self.estimates = estimates
        self.scaffoldSizes = scaffoldSizes
        # make a copy of the data and swap X and Y axis for plotting
        self.matching = np.fliplr(initialMatching)
        # compute abs. difference as a correlationmeasure
        self.correlationMatrix = 1 + np.abs(
            np.atleast_2d(self.estimates).T - self.scaffoldSizes
        )
        # store matrix dimensions for concise access
        self.n, self.m = self.correlationMatrix.shape

        self.colorMap = pg.colormap.get(colorMap)

        # setup window appearance
        self.setWindowTitle("Chromosome size estimation: analysis plots")
        self.resize(600, 500)
        self.setCentralWidget(pg.GraphicsLayoutWidget(show=True))

        self._attachMatrixPlot()

        self.show()

    def _attachMatrixPlot(self):
        self.matrixPlotItem = self.centralWidget().addPlot()
        # orient y axis to run top-to-bottom
        self.matrixPlotItem.invertY(True)
        # remove data padding
        self.matrixPlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at top and left sides, with some extra space for labels
        self.matrixPlotItem.showAxes(
            True, showValues=(True, True, False, False), size=20
        )
        # define major tick marks and labels:
        # ticks = [(idx, label) for idx, label in enumerate(columns)]
        # for side in ("left", "top", "right", "bottom"):
        #     self.matrixPlotItem.getAxis(side).setTicks(
        #         (ticks, [])
        #     )  # add list of major ticks; no minor ticks
        # include some additional space at bottom of figure
        # self.matrixPlotItem.getAxis("bottom").setHeight(10)

        # set locked aspect ratio of 1
        centralViewBox = self.matrixPlotItem.getViewBox()
        centralViewBox.setAspectLocked()

        self._attachCorrelationMatrixItem()

    def _attachCorrelationMatrixItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.correlationMatrixItem = CorrelationMatrixItem()
        self.correlationMatrixItem.setTransform(alignPixelTransform)
        self.correlationMatrixItem.setImage(self.correlationMatrix)

        # display plot
        self.matrixPlotItem.addItem(self.correlationMatrixItem)
        # set parent widget for displaying information
        self.correlationMatrixItem.setParent(self.matrixPlotItem)

        # generate an adjustabled color bar, initially spanning min to max data value
        bar = pg.ColorBarItem(
            values=(np.min(self.correlationMatrix), np.max(self.correlationMatrix)),
            colorMap=self.colorMap,
        )
        bar.setImageItem(self.correlationMatrixItem, insert_in=self.matrixPlotItem)

        # create overlayed scatter plot for matching
        self.matchingPlotItem = pg.ScatterPlotItem(
            size=10,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(255, 255, 255, 120),
            hoverable=True,
            hoverPen=pg.mkPen("r", width=2),
            hoverBrush=pg.mkBrush(None),
        )
        matchingIndices = list(range(len(self.matching)))
        self.matchingPlotItem.addPoints(pos=self.matching, data=matchingIndices)

        self.matrixPlotItem.addItem(self.matchingPlotItem)

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

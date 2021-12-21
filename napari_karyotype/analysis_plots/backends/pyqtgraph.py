import numpy as np
import pandas as pd
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

    sigMatchingChanged = QtCore.Signal(object)

    def __init__(
        self,
        estimates,
        scaffoldSizes,
        initialMatching,
        *qtArgs,
        colorMap="magma",
        **qtKwargs,
    ):
        super().__init__(*qtArgs, **qtKwargs)

        # store data that should be displayed
        self.estimates = pd.Series(estimates)
        self.estimates.name = self.estimates.name or "chromosome_estimates"
        self.scaffoldSizes = pd.Series(scaffoldSizes)
        self.scaffoldSizes.name = self.scaffoldSizes.name or "scaffold_sizes"
        # make a copy of the data and swap X and Y axis for plotting
        self.matching = np.fliplr(initialMatching)
        # compute abs. difference as a correlationmeasure
        self.correlationMatrix = pd.DataFrame(
            1
            + np.abs(
                np.atleast_2d(self.estimates.values).T - self.scaffoldSizes.values
            ),
            index=estimates.index,
            columns=scaffoldSizes.index,
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
        self._prepareCorrelationPerChromosomeItem()
        self._populateCorrelationPerChromosomeItem()

        self._prepareMatrixPlotItem()
        self._populateMatrixPlotItem()

        self._prepareColorBarItem()
        self._populateColorBarItem()

        self.updateMatching()

    def _prepareCorrelationPerChromosomeItem(self):
        self.correlationPerChromosomePlotItem = self.centralWidget().addPlot(
            row=0,
            col=0,
            name="correlationPerChromosome",
            axisItems={
                "left": LabelAxisItem("left", self.estimates.index),
                "right": LabelAxisItem("right", self.estimates.index),
                "top": LabelAxisItem("top", self.scaffoldSizes.index),
                "bottom": LabelAxisItem("bottom", self.scaffoldSizes.index),
            },
            enableMenu=False,
        )
        # disable mouse interaction
        self.correlationPerChromosomePlotItem.vb.setMouseEnabled(x=False, y=False)
        # orient y axis to run top-to-bottom
        self.correlationPerChromosomePlotItem.invertY(True)
        # remove data padding
        self.correlationPerChromosomePlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at left side, with some extra space for labels
        self.correlationPerChromosomePlotItem.showAxes(
            True, showValues=(True, False, False, False), size=40
        )
        self.correlationPerChromosomePlotItem.setYLink("matrix")
        self.correlationPerChromosomePlotItem.setLimits(xMin=-0.5, xMax=0.5)
        self.correlationPerChromosomePlotItem.setFixedWidth(80)

    def _populateCorrelationPerChromosomeItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.correlationPerChromosomeItem = pg.ImageItem()
        self.correlationPerChromosomeItem.setTransform(alignPixelTransform)

        # make sure self.correlationPerChromosome is set correctly
        self.udpateMatchingScore()
        dataView = self.correlationPerChromosome.view()
        dataView.shape = (-1, 1)
        self.correlationPerChromosomeItem.setImage(dataView)

        # display plot
        self.correlationPerChromosomePlotItem.addItem(self.correlationPerChromosomeItem)
        self.correlationPerChromosomePlotItem.autoRange()

    def _prepareMatrixPlotItem(self):
        self.matrixPlotItem = self.centralWidget().addPlot(row=0, col=1, name="matrix")
        # orient y axis to run top-to-bottom
        self.matrixPlotItem.invertY(True)
        # remove data padding
        self.matrixPlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at top side, with some extra space for labels
        self.matrixPlotItem.showAxes(True, showValues=False)
        self.matrixPlotItem.setYLink("correlationPerChromosome")
        # set locked aspect ratio of 1
        self.matrixPlotItem.setAspectLocked()

    def _populateMatrixPlotItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.correlationMatrixItem = CorrelationMatrixItem(
            self.estimates.index, self.scaffoldSizes.index
        )
        self.correlationMatrixItem.setTransform(alignPixelTransform)
        self.correlationMatrixItem.setImage(self.correlationMatrix.values)

        # display plot
        self.matrixPlotItem.addItem(self.correlationMatrixItem)
        # set parent widget for displaying information
        # self.correlationMatrixItem.setStatusItem(self.matrixPlotItem)

        # create overlayed scatter plot for matching
        self.matchingPlotItem = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(255, 255, 255, 120),
            hoverable=True,
            hoverPen=pg.mkPen("r", width=2),
            hoverBrush=pg.mkBrush(None),
        )

        # setup data change handlers
        self.sigMatchingChanged.connect(self.updateMatchingScore)
        self.sigMatchingChanged.connect(self.updateMatchingPlotItem)

        # setup click handlers
        self.matchingPlotItem.sigClicked.connect(
            lambda _, ps: self.deleteMatchings([p.index() for p in ps])
        )
        self.correlationMatrixItem.handleMouseClick = lambda i, j: self.addMatching(
            i, j
        )

        # display scatter plot
        self.matrixPlotItem.addItem(self.matchingPlotItem)

    def _prepareColorBarItem(self):
        self.colorBarPlotItem = self.centralWidget().addPlot(row=0, col=2)
        self.colorBarPlotItem.showAxes(False)
        self.colorBarPlotItem.setFixedWidth(120)

    def _populateColorBarItem(self):
        # generate an adjustabled color bar, initially spanning min to max data value
        self.colorBarItem = pg.ColorBarItem(
            values=(
                np.min(self.correlationMatrix.values),
                np.max(self.correlationMatrix.values),
            ),
            colorMap=self.colorMap,
        )
        self.colorBarItem.setImageItem(
            [self.correlationMatrixItem, self.correlationPerChromosomeItem],
            insert_in=self.colorBarPlotItem,
        )
        # add space for axis labels
        self.colorBarItem.getAxis("right").setWidth(80)

        self.sigMatchingChanged.connect(self.updateCorrelationPerChromosomeItem)

    def keyReleaseEvent(self, e):
        if e.key() == QtCore.Qt.Key.Key_Q:
            self.close()

    def updateMatching(self):
        self.udpateMatchingScore()
        self.sigMatchingChanged.emit(self)

    def udpateMatchingScore(self):
        mask = np.ones(self.correlationMatrix.shape, dtype=bool)
        mask[self.matching[:, 1], self.matching[:, 0]] = False
        selectedScaffoldSizes = (
            np.zeros_like(self.scaffoldSizes.values, shape=(self.n, 1))
            + self.scaffoldSizes.values
        )
        selectedScaffoldSizes[mask] = 0
        rowSums = np.sum(selectedScaffoldSizes, axis=1)

        self.correlationPerChromosome = np.abs(self.estimates.values - rowSums)
        self.matchingScore = np.sum(self.correlationPerChromosome)

    def addMatching(self, i, j):
        if np.any((self.matching[:, 0] == j) & (self.matching[:, 1] == i)):
            # matching already exists
            return

        self.matching = np.vstack((self.matching, np.array([j, i])))
        self.updateMatching()

    def deleteMatchings(self, deletedIndices):
        self.matching = np.delete(self.matching, deletedIndices, axis=0)
        self.updateMatching()

    def updateMatchingScore(self):
        self.correlationMatrixItem.matchingScore = self.matchingScore

    def updateMatchingPlotItem(self):
        matchingIndices = list(range(len(self.matching)))
        self.matchingPlotItem.setData(pos=self.matching, data=matchingIndices)

    def updateCorrelationPerChromosomeItem(self):
        # update correlation per chromsome plot
        self.correlationPerChromosomeItem.setImage(
            self.correlationPerChromosome.reshape(-1, 1)
        )

        if hasattr(self, "colorBarItem"):
            # trigger update of coloring
            self.colorBarItem.setLevels()


class CorrelationMatrixItem(pg.ImageItem):
    def __init__(self, chromosomes, scaffoldNames, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.chromosomes = chromosomes
        self.scaffoldNames = scaffoldNames
        self.statusItem = None

    def setStatusItem(self, statusItem):
        self.statusItem = statusItem
        self.statusItem.setTitle("")

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            if self.raiseContextMenu(ev):
                ev.accept()
                return

        if (
            not self.handleMouseClick is None
            and ev.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            i, j = ev.pos().y(), ev.pos().x()
            i = int(np.clip(i, 0, self.image.shape[0] - 1))
            j = int(np.clip(j, 0, self.image.shape[1] - 1))
            self.handleMouseClick(i, j)

    def hoverEvent(self, event):
        """Show the position, pixel, and value under the mouse cursor."""
        if not self.statusItem:
            return

        if event.isExit():
            if self.statusItem:
                self.statusItem.setTitle("")
            return

        pos = event.pos()
        i, j = pos.y(), pos.x()
        i = int(np.clip(i, 0, self.image.shape[0] - 1))
        j = int(np.clip(j, 0, self.image.shape[1] - 1))
        absdiff = self.image[i, j]
        chrom = self.chromosomes[i]
        scaff = self.scaffoldNames[j]

        self.statusItem.setTitle(
            f"chr: {chrom}  scaff: {scaff}  absdiff: {absdiff}  score: {self.matchingScore}"
        )


class LabelAxisItem(pg.AxisItem):
    def __init__(self, orientation, labels, *args, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.labels = labels

    def tickStrings(self, values, scale, spacing):
        """Return the strings that should be placed next to ticks."""
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        def value2str(v):
            idx = int(v * scale)

            if 0 <= idx and idx <= len(self.labels):
                return str(self.labels[idx])
            else:
                return ""

        return [value2str(v) for v in values]

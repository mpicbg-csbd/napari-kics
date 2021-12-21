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
        self.matrixBorderSize = (60, 80)
        self.trSuperDigits = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

        # setup window appearance
        self.setWindowTitle("Chromosome size estimation: analysis plots")
        self.resize(20 * self.m, 20 * self.n)
        self.setCentralWidget(pg.GraphicsLayoutWidget(show=True))

        self._attachMatrixPlot()

        self.show()

    def _attachMatrixPlot(self):
        self._prepareTotalCorrelationItem()
        self._populateTotalCorrelationItem()

        self._prepareSelectionPerScaffoldItem()
        self._populateSelectionPerScaffoldItem()

        self._prepareCorrelationPerChromosomeItem()
        self._populateCorrelationPerChromosomeItem()

        self._prepareMatrixPlotItem()
        self._populateMatrixPlotItem()

        self._prepareColorBarItem()
        self._populateColorBarItem()

        self.updateMatching()

    def _prepareTotalCorrelationItem(self):
        self.totalCorrelationPlotItem = self.centralWidget().addPlot(
            row=0,
            col=0,
            name="totalCorrelation",
            axisItems={
                "left": NoLabelAxisItem("left"),
                "right": NoLabelAxisItem("right"),
                "top": NoLabelAxisItem("top"),
                "bottom": NoLabelAxisItem("bottom"),
            },
            enableMenu=False,
        )
        # disable mouse interaction
        self.totalCorrelationPlotItem.vb.setMouseEnabled(x=False, y=False)
        self.totalCorrelationPlotItem.hideButtons()
        # remove data padding
        self.totalCorrelationPlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at top side, with some extra space for labels
        self.totalCorrelationPlotItem.showAxes(
            True, showValues=(True, True, False, False), size=(40, 20)
        )
        # hide ticks
        self.totalCorrelationPlotItem.getAxis("left").setTicks([])
        self.totalCorrelationPlotItem.getAxis("right").setTicks([])
        self.totalCorrelationPlotItem.getAxis("top").setTicks([])
        self.totalCorrelationPlotItem.getAxis("bottom").setTicks([])
        self.totalCorrelationPlotItem.setLimits(
            xMin=-0.5, xMax=0.5, yMin=-0.5, yMax=0.5
        )
        self.totalCorrelationPlotItem.setFixedHeight(self.matrixBorderSize[0])
        self.totalCorrelationPlotItem.setFixedWidth(self.matrixBorderSize[1])

    def _populateTotalCorrelationItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.totalCorrelationItem = pg.ImageItem()
        self.totalCorrelationItem.setTransform(alignPixelTransform)

        self.totalCorrelationTextItem = pg.TextItem(text="-", anchor=(0.5, 0.5))
        self.totalCorrelationTextItem.setPos(0, 0)
        self.totalCorrelationTextItem.setTextWidth(self.matrixBorderSize[1] - 40)

        # display indicator and text
        self.totalCorrelationPlotItem.addItem(self.totalCorrelationItem)
        self.totalCorrelationPlotItem.addItem(self.totalCorrelationTextItem)

        # Update indicator and text if the matching changes
        self.sigMatchingChanged.connect(self.updateTotalCorrelationItem)

    def _prepareSelectionPerScaffoldItem(self):
        self.selectionPerScaffoldPlotItem = self.centralWidget().addPlot(
            row=0,
            col=1,
            name="selectionPerScaffold",
            axisItems={
                "left": LabelAxisItem("left", self.estimates.index),
                "right": LabelAxisItem("right", self.estimates.index),
                "top": LabelAxisItem("top", self.scaffoldSizes.index),
                "bottom": LabelAxisItem("bottom", self.scaffoldSizes.index),
            },
            enableMenu=False,
        )
        # disable mouse interaction
        self.selectionPerScaffoldPlotItem.vb.setMouseEnabled(x=False, y=False)
        self.selectionPerScaffoldPlotItem.hideButtons()
        # remove data padding
        self.selectionPerScaffoldPlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at top side, with some extra space for labels
        self.selectionPerScaffoldPlotItem.showAxes(
            True, showValues=(False, True, False, False), size=20
        )
        self.selectionPerScaffoldPlotItem.setXLink("matrix")
        self.selectionPerScaffoldPlotItem.setLimits(yMin=-0.5, yMax=0.5)
        self.selectionPerScaffoldPlotItem.setFixedHeight(self.matrixBorderSize[0])

    def _populateSelectionPerScaffoldItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.selectionPerScaffoldItem = pg.ImageItem()
        self.selectionPerScaffoldItem.setTransform(alignPixelTransform)
        cm = pg.ColorMap([0.0, 0.5, 1.0], ["black", "white", "red"])
        self.selectionPerScaffoldItem.setLookupTable(cm.getLookupTable(nPts=3))

        # display plot
        self.selectionPerScaffoldPlotItem.addItem(self.selectionPerScaffoldItem)
        self.selectionPerScaffoldPlotItem.autoRange()

        # Update plot if the matching changes
        self.sigMatchingChanged.connect(self.updateSelectionPerScaffoldItem)

    def _prepareCorrelationPerChromosomeItem(self):
        self.correlationPerChromosomePlotItem = self.centralWidget().addPlot(
            row=1,
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
        self.correlationPerChromosomePlotItem.hideButtons()
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
        self.correlationPerChromosomePlotItem.setFixedWidth(self.matrixBorderSize[1])

    def _populateCorrelationPerChromosomeItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.correlationPerChromosomeItem = pg.ImageItem()
        self.correlationPerChromosomeItem.setTransform(alignPixelTransform)

        # The following will be
        # self.correlationPerChromosomeItem.setImage(self.correlationPerChromosome.reshape(-1, 1))

        # display plot
        self.correlationPerChromosomePlotItem.addItem(self.correlationPerChromosomeItem)
        self.correlationPerChromosomePlotItem.autoRange()

        # Update plot if the matching changes
        self.sigMatchingChanged.connect(self.updateCorrelationPerChromosomeItem)

    def _prepareMatrixPlotItem(self):
        self.matrixPlotItem = self.centralWidget().addPlot(row=1, col=1, name="matrix")
        # orient y axis to run top-to-bottom
        self.matrixPlotItem.invertY(True)
        # remove data padding
        self.matrixPlotItem.setDefaultPadding(0.0)
        # show full frame, label tick marks at top side, with some extra space for labels
        self.matrixPlotItem.showAxes(True, showValues=False)
        self.matrixPlotItem.setXLink("selectionPerScaffold")
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
        self.sigMatchingChanged.connect(self.updateMatchingScoreHandler)
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
        self.colorBarPlotItem = self.centralWidget().addPlot(row=1, col=2)
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
            [
                self.correlationMatrixItem,
                self.correlationPerChromosomeItem,
                self.totalCorrelationItem,
            ],
            insert_in=self.colorBarPlotItem,
        )
        # add space for axis labels
        self.colorBarItem.getAxis("right").setWidth(80)

    def keyReleaseEvent(self, e):
        if e.key() == QtCore.Qt.Key.Key_Q:
            self.close()

    def updateMatching(self):
        self.updateMatchingScore()
        self.updateScaffoldSelection()
        self.sigMatchingChanged.emit(self)

    def updateMatchingScore(self):
        mask = np.ones(self.correlationMatrix.shape, dtype=bool)
        mask[self.matching[:, 1], self.matching[:, 0]] = False
        selectedScaffoldSizes = (
            np.zeros_like(self.scaffoldSizes.values, shape=(self.n, 1))
            + self.scaffoldSizes.values
        )
        selectedScaffoldSizes[mask] = 0
        rowSums = np.sum(selectedScaffoldSizes, axis=1)

        self.correlationPerChromosome = np.abs(self.estimates.values - rowSums)
        self.totalCorrelation = np.mean(self.correlationPerChromosome)

    def updateScaffoldSelection(self):
        self.scaffoldSelection = np.zeros((1, self.m), dtype=int)

        for scaffIdx in self.matching[:, 0]:
            self.scaffoldSelection[0, scaffIdx] += 1

    def addMatching(self, i, j):
        if np.any((self.matching[:, 0] == j) & (self.matching[:, 1] == i)):
            # matching already exists
            return

        self.matching = np.vstack((self.matching, np.array([j, i])))
        self.updateMatching()

    def deleteMatchings(self, deletedIndices):
        self.matching = np.delete(self.matching, deletedIndices, axis=0)
        self.updateMatching()

    def updateMatchingScoreHandler(self):
        self.correlationMatrixItem.matchingScore = self.totalCorrelation

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

    def updateSelectionPerScaffoldItem(self):
        # update selection per scaffold plot
        self.selectionPerScaffoldItem.setImage(self.scaffoldSelection, levels=[0, 2])

    def updateTotalCorrelationItem(self):
        # update selection per scaffold plot
        totalCorrelation = np.array([[self.totalCorrelation]])
        self.totalCorrelationItem.setImage(totalCorrelation)

        m, e = f"{self.totalCorrelation:.1e}".split("e")
        e = e.lstrip("+0").translate(self.trSuperDigits)
        self.totalCorrelationTextItem.setText(m + e)


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


class NoLabelAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        """Return the strings that should be placed next to ticks."""
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        return ["" for v in values]

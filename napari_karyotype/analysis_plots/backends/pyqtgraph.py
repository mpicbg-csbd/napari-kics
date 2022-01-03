import numpy as np
import pandas as pd
import pyqtgraph as pg
import pyqtgraph.exporters
from pyqtgraph.Qt import QtWidgets, mkQApp, QtGui, QtCore
from .. import size_correlation, get_initial_bounds
from collections import namedtuple


def do_plot(estimates, scaffoldSizes, initialMatching, **kwargs):
    # TODO show tooltip on hover with scaff/estimate name/index, size diff, abs. sizes, ...

    app = mkQApp("Chromosome size estimation: analysis plots")

    # Switch default order to Row-major (in accordance with numpy)
    # Enable anti-aliasing for beautiful plots
    pg.setConfigOptions(antialias=True, imageAxisOrder="row-major")

    main_window = MainWindow(estimates, scaffoldSizes, initialMatching)

    fix_initial_scaling_of_matrix_view(main_window)
    app.exec_()


def fix_initial_scaling_of_matrix_view(main_window):
    def update_matrix_scale():
        main_window.matrixPlotItem.autoRange(padding=0)

    QtCore.QTimer.singleShot(0, update_matrix_scale)
    QtCore.QTimer.singleShot(10, update_matrix_scale)
    QtCore.QTimer.singleShot(100, update_matrix_scale)


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
            size_correlation(estimates.values.reshape(-1, 1), scaffoldSizes.values),
            index=estimates.index,
            columns=scaffoldSizes.index,
        )
        # store matrix dimensions for concise access
        self.n, self.m = self.correlationMatrix.shape

        self.colorMap = pg.colormap.get(colorMap)
        self.colorMap.reverse()
        self.matrixBorderSize = (120, 80)
        self.matrixAxisLabelSize = (80, 20)
        self.matrixGridLevels = [(5, -0.5), (1, -0.5)]
        self.legendWidth = 200
        self.barWidth = 0.3
        self.trSuperDigits = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

        # setup window appearance
        self.setWindowTitle("Chromosome size estimation: analysis plots")
        self.resize(20 * self.m, 40 * self.n)
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

        self._addMatrixCrosshair()

        self._prepareDirectComparisonItem()
        self._populateDirectComparisonItem()

        self.updateMatching()

    def _prepareTotalCorrelationItem(self):
        self.totalCorrelationPlotItem = self.centralWidget().addPlot(
            row=0,
            col=0,
            name="totalCorrelation",
            title="",
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
            True, showValues=(True, True, False, False), size=self.matrixAxisLabelSize
        )
        # hide ticks
        self.totalCorrelationPlotItem.getAxis("left").setTicks([])
        self.totalCorrelationPlotItem.getAxis("right").setTicks([])
        self.totalCorrelationPlotItem.getAxis("top").setTicks([])
        self.totalCorrelationPlotItem.getAxis("bottom").setTicks([])
        self.totalCorrelationPlotItem.setLimits(
            xMin=-0.5, xMax=0.5, yMin=-0.5, yMax=0.5
        )
        self.totalCorrelationPlotItem.setFixedWidth(self.matrixBorderSize[0])
        self.totalCorrelationPlotItem.setFixedHeight(self.matrixBorderSize[1])

    def _populateTotalCorrelationItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.totalCorrelationItem = pg.ImageItem()
        self.totalCorrelationItem.setTransform(alignPixelTransform)

        self.totalCorrelationTextItem = pg.TextItem(text="-", anchor=(0.5, 0.5))
        self.totalCorrelationTextItem.setPos(0, 0)
        self.totalCorrelationTextItem.setTextWidth(
            self.matrixBorderSize[0] - self.matrixAxisLabelSize[0]
        )

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
            title="Scaffolds",
            axisItems={
                "left": LabelAxisItem("left", self.estimates.index, offset=0.5),
                "right": LabelAxisItem("right", self.estimates.index, offset=0.5),
                "top": LabelAxisItem("top", self.scaffoldSizes.index, offset=0.5),
                "bottom": LabelAxisItem("bottom", self.scaffoldSizes.index, offset=0.5),
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
            True,
            showValues=(False, True, False, False),
            size=self.matrixAxisLabelSize[1],
        )
        self.selectionPerScaffoldPlotItem.showGrid(x=True, y=False)
        for axis in ("top", "bottom"):
            self.selectionPerScaffoldPlotItem.getAxis(axis).setTickSpacing(
                levels=self.matrixGridLevels
            )
        for axis in ("left", "right"):
            self.selectionPerScaffoldPlotItem.getAxis(axis).setTicks([])

        self.selectionPerScaffoldPlotItem.setXLink("matrix")
        self.selectionPerScaffoldPlotItem.setLimits(yMin=-0.5, yMax=0.5)
        self.selectionPerScaffoldPlotItem.setFixedHeight(self.matrixBorderSize[1])

        self.selectionPerScaffoldLegendItem = self.centralWidget().addViewBox(
            row=0,
            col=2,
            name="selectionPerScaffoldLegend",
            enableMenu=False,
            enableMouse=False,
        )
        self.selectionPerScaffoldLegendItem.setFixedWidth(self.legendWidth)
        self.selectionPerScaffoldLegendItem.setFixedHeight(self.matrixBorderSize[1])

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

        # add a legend
        legend = pg.LegendItem(offset=(1, 1), sampleType=ItemSample)
        legend.setParentItem(self.selectionPerScaffoldLegendItem)
        stateColors = cm.getColors(mode="qcolor")
        stateColors = {
            "unselected": stateColors[0],
            "selected": stateColors[1],
            "overselected": stateColors[2],
        }

        def dummyItem(state):
            return pg.BarGraphItem(
                x=[], height=[], brush=stateColors[state], pen="#88888888"
            )

        legend.addItem(dummyItem("unselected"), "Scaffold unselected")
        legend.addItem(dummyItem("selected"), "Scaffold selected")
        legend.addItem(dummyItem("overselected"), "Scaffold over-selected")

    def _prepareCorrelationPerChromosomeItem(self):
        self.correlationPerChromosomePlotItem = self.centralWidget().addPlot(
            row=1,
            col=0,
            name="correlationPerChromosome",
            axisItems={
                "left": LabelAxisItem("left", self.estimates.index, offset=0.5),
                "right": LabelAxisItem("right", self.estimates.index, offset=0.5),
                "top": LabelAxisItem("top", self.scaffoldSizes.index, offset=0.5),
                "bottom": LabelAxisItem("bottom", self.scaffoldSizes.index, offset=0.5),
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
            True,
            showValues=(True, False, False, False),
            size=self.matrixAxisLabelSize[0],
        )
        self.correlationPerChromosomePlotItem.showGrid(x=False, y=True)

        yAxis = self.correlationPerChromosomePlotItem.getAxis("left")
        yAxis.setLabel("Chromosomes")
        for axis in ("left", "right"):
            self.correlationPerChromosomePlotItem.getAxis(axis).setTickSpacing(
                levels=self.matrixGridLevels
            )
        for axis in ("top", "bottom"):
            self.correlationPerChromosomePlotItem.getAxis(axis).setTicks([])
        self.correlationPerChromosomePlotItem.setYLink("matrix")
        self.correlationPerChromosomePlotItem.setLimits(xMin=-0.5, xMax=0.5)
        self.correlationPerChromosomePlotItem.setFixedWidth(self.matrixBorderSize[0])

    def _populateCorrelationPerChromosomeItem(self):
        # prepare transform to center the corner element on the origin, for any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.correlationPerChromosomeItem = pg.ImageItem()
        self.correlationPerChromosomeItem.setTransform(alignPixelTransform)

        # display plot
        self.correlationPerChromosomePlotItem.addItem(self.correlationPerChromosomeItem)

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
        self.matrixPlotItem.showGrid(x=True, y=True)
        for axis in ("left", "bottom", "right", "top"):
            self.matrixPlotItem.getAxis(axis).setTickSpacing(
                levels=self.matrixGridLevels
            )

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

        # create overlayed scatter plot for matching
        self.matchingPlotItem = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(color="#55555588", width=1),
            brush=pg.mkBrush("#ffffff88"),
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
        self.correlationMatrixItem.handleMouseClick = lambda i, j: self.toggleMatching(
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
            values=get_initial_bounds(self.correlationMatrix),
            colorMap=self.colorMap,
            label="Size correlation",
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

    def _addMatrixCrosshair(self):
        self.__signalProxies = list()
        self.__matrixCrosshairHLines = list()
        self.__matrixCrosshairVLines = list()

        def handleMouseMove(plotItem, *, moveX=True, moveY=True):
            if moveY:
                # create horizontal part of crosshair
                hLine = pg.InfiniteLine(
                    angle=0, movable=False, pen={"color": "#555555ff", "width": 2}
                )
                plotItem.addItem(hLine, ignoreBounds=True)
                self.__matrixCrosshairHLines.append(hLine)

            if moveX:
                # create vertical part of crosshair
                vLine = pg.InfiniteLine(
                    angle=90, movable=False, pen={"color": "#555555ff", "width": 2}
                )
                plotItem.addItem(vLine, ignoreBounds=True)
                self.__matrixCrosshairVLines.append(vLine)

            def mouseMoved(args):
                # using signal proxy turns original arguments into a tuple
                pos = args[0]

                if plotItem.sceneBoundingRect().contains(pos):
                    mousePoint = plotItem.vb.mapSceneToView(pos)
                    if moveY:
                        for hLine in self.__matrixCrosshairHLines:
                            hLine.setPos(mousePoint.y())
                    if moveX:
                        for vLine in self.__matrixCrosshairVLines:
                            vLine.setPos(mousePoint.x())

            proxy = pg.SignalProxy(
                plotItem.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved
            )
            self.__signalProxies.append(proxy)

        handleMouseMove(self.selectionPerScaffoldPlotItem, moveY=False)
        handleMouseMove(self.correlationPerChromosomePlotItem, moveX=False)
        handleMouseMove(self.matrixPlotItem)

    def _prepareDirectComparisonItem(self):
        self.directComparisonPlotItem = self.centralWidget().addPlot(
            row=2,
            col=0,
            colspan=2,
            name="directComparison",
            title="Size comparison of selected matching",
            axisItems={
                "left": pg.AxisItem("left"),
                "right": pg.AxisItem("right"),
                "top": LabelAxisItem("top", self.estimates.index),
                "bottom": LabelAxisItem("bottom", self.estimates.index),
            },
        )
        # show full frame, label tick marks at bottom side, with some extra space for labels
        self.directComparisonPlotItem.showAxes(
            True,
            showValues=(True, False, False, True),
            size=(self.matrixAxisLabelSize[0], None),
        )
        yAxis = self.directComparisonPlotItem.getAxis("left")
        yAxis.enableAutoSIPrefix(False)
        yAxis.setLabel("Size", "bp")
        yAxis.setLogMode(True)
        self.directComparisonPlotItem.showGrid(y=True)

        self.directComparisonLegendItem = self.centralWidget().addViewBox(
            row=2,
            col=2,
            name="directComparisonLegend",
            enableMenu=False,
            enableMouse=False,
        )
        self.directComparisonLegendItem.setFixedWidth(self.legendWidth)

    def _populateDirectComparisonItem(self):
        self.chrIndices = np.arange(len(self.estimates))

        self.chromsomeBarsItem = pg.BarGraphItem(
            x=self.chrIndices - self.barWidth / 2,
            y0=np.log10(np.ones_like(self.estimates)),
            height=np.log10(self.estimates),
            width=self.barWidth,
            brush="#66666688",
            pen="#88888888",
        )
        self.scaffoldBarsItem = pg.BarGraphItem(
            x=[], height=[], width=self.barWidth, brush="#FFFFFF88", pen="#FFFFFFDD"
        )

        # display bars
        self.directComparisonPlotItem.addItem(self.chromsomeBarsItem)
        self.directComparisonPlotItem.addItem(self.scaffoldBarsItem)

        legend = pg.LegendItem(offset=(0, 30), sampleType=ItemSample)
        legend.setParentItem(self.directComparisonLegendItem)
        legend.addItem(self.chromsomeBarsItem, "Chromosome size estimates")
        legend.addItem(self.scaffoldBarsItem, "Combined scaffold sizes")

        # Update indicator and text if the matching changes
        self.sigMatchingChanged.connect(self.updateScaffoldBarsItem)

    def keyReleaseEvent(self, e):
        """Handle key release events for the window"""
        if e == QtGui.QKeySequence.Quit:
            self.close()
        elif e == QtGui.QKeySequence.Print:
            exporter = SVGExporter(self.centralWidget().scene(), parent=self)
            exporter.export()

    def updateMatching(self):
        self._updateMatchingScore()
        self._updateScaffoldSelection()
        self.sigMatchingChanged.emit(self)

    def _updateMatchingScore(self):
        unselectedMask = np.ones(self.correlationMatrix.shape, dtype=bool)
        unselectedMask[self.matching[:, 1], self.matching[:, 0]] = False
        self.selectedScaffoldSizes = (
            np.zeros((self.n, 1), dtype=np.float_) + self.scaffoldSizes.values
        )
        self.selectedScaffoldSizes[unselectedMask] = 0
        self.joinedScaffoldLengths = np.sum(self.selectedScaffoldSizes, axis=1)
        self.assignedChromosomesMask = self.joinedScaffoldLengths >= 1

        self.correlationPerChromosome = size_correlation(
            self.estimates.values, 1 + self.joinedScaffoldLengths
        )
        self.correlationPerChromosome[~self.assignedChromosomesMask] = np.inf
        self.totalCorrelation = np.mean(
            self.correlationPerChromosome[self.assignedChromosomesMask]
        )

    def _updateScaffoldSelection(self):
        self.scaffoldSelection = np.zeros((1, self.m), dtype=int)

        for scaffIdx in self.matching[:, 0]:
            self.scaffoldSelection[0, scaffIdx] += 1

    def toggleMatching(self, i, j):
        existing = np.nonzero((self.matching[:, 0] == j) & (self.matching[:, 1] == i))
        # unpack tuple
        existing = existing[0]

        if len(existing) > 0:
            # matching already exists
            self.deleteMatchings(existing)
        else:
            # matching does not exist
            self.addMatching(i, j)

    def addMatching(self, i, j):
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
        self.totalCorrelationTextItem.setText(f"{self.totalCorrelation:.1f}")

    def updateScaffoldBarsItem(self):
        BarSpec = namedtuple("BarSpec", ["y0", "y1"])

        numMatched = self.matching.shape[0]
        bars = dict()
        for scaffIdx, chrIdx in self.matching:
            lastBars = bars.get(chrIdx, [])
            lastBar = lastBars[-1] if len(lastBars) > 0 else BarSpec(1, 1)
            nextY0 = lastBar.y1
            nextY1 = nextY0 + self.scaffoldSizes[scaffIdx]
            lastBars.append(BarSpec(nextY0, nextY1))
            bars[chrIdx] = lastBars

        xs = list()
        y0s = list()
        y1s = list()
        for chrIdx in sorted(bars.keys()):
            for bar in bars[chrIdx]:
                xs.append(chrIdx)
                y0s.append(bar.y0)
                y1s.append(bar.y1)

        xs = np.array(xs, dtype=np.float_)
        y0s = np.array(y0s, dtype=np.float_)
        y1s = np.array(y1s, dtype=np.float_)

        # update selection per scaffold plot
        self.scaffoldBarsItem.setOpts(
            x=xs + self.barWidth / 2,
            y0=np.log10(y0s),
            height=np.log10(y1s) - np.log10(y0s),
        )

        self.directComparisonPlotItem.setYRange(
            np.min(np.log10(y1s)),
            np.max(np.log10(y1s)),
        )


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
    def __init__(self, orientation, labels, *args, offset=0, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.labels = labels
        self.offset = offset

    def tickStrings(self, values, scale, spacing):
        """Return the strings that should be placed next to ticks."""

        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        def value2str(v):
            vs = v * scale + self.offset
            idx = int(vs)

            if abs(idx - vs) <= 5e-8 and 0 <= idx and idx < len(self.labels):
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


class ItemSample(pg.ItemSample):
    def paint(self, p, *args):
        if isinstance(self.item, pg.BarGraphItem):
            opts = self.item.opts
            if opts.get("antialias"):
                p.setRenderHint(p.RenderHint.Antialiasing)

            visible = self.item.isVisible()
            if not visible:
                icon = invisibleEye.qicon
                p.drawPixmap(QtCore.QPoint(1, 1), icon.pixmap(18, 18))
                return

            p.setPen(pg.mkPen(opts["pen"]))
            p.setBrush(pg.mkBrush(opts["brush"]))
            p.drawRect(QtCore.QRectF(2, 2, 18, 18))
        else:
            super().paint(p, *args)

    def mouseClickEvent(self, event):
        pass


class SVGExporter(pg.exporters.SVGExporter):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

    def fileSaveDialog(self, filter=None, opts=None):
        if opts is None:
            opts = {}
        if not self.parent is None:
            self.fileDialog = pg.FileDialog(self.parent)
        else:
            self.fileDialog = pg.FileDialog()
        self.fileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        self.fileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        if filter is not None:
            if isinstance(filter, str):
                self.fileDialog.setNameFilter(filter)
            elif isinstance(filter, list):
                self.fileDialog.setNameFilters(filter)
        from pyqtgraph.exporters.Exporter import LastExportDirectory

        exportDir = LastExportDirectory
        if exportDir is not None:
            self.fileDialog.setDirectory(exportDir)
        self.fileDialog.opts = opts
        self.fileDialog.accepted.connect(self.fileSaveFinished)
        self.fileDialog.exec_()

    def fileSaveFinished(self):
        fileName = self.fileDialog.selectedFiles()[0]
        super().fileSaveFinished(fileName)

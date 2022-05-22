import logging
from collections import namedtuple

import numpy as np
import pandas as pd
import pyqtgraph as pg
import pyqtgraph.exporters
from pyqtgraph.icons import invisibleEye
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets, mkQApp

from .. import get_initial_bounds, size_correlation

log = logging.getLogger(__name__)


ReturnType = namedtuple("ReturnType", ["matching"])


def do_plot(estimates, scaffoldSizes, initialMatching, **kwargs):
    # TODO show tooltip on hover with scaff/estimate name/index, size diff,
    #   abs. sizes, ...

    app = QtWidgets.QApplication.instance()
    is_running = app is not None

    if not is_running:
        app = mkQApp("Chromosome size estimation: analysis plots")

    # Switch default order to Row-major (in accordance with numpy)
    # Enable anti-aliasing for beautiful plots
    pg.setConfigOptions(antialias=True, imageAxisOrder="row-major")

    main_window = MainWindow(estimates, scaffoldSizes, initialMatching)

    fix_initial_scaling_of_matrix_view(main_window)

    if not is_running:
        app.exec_()
        is_running = True

    # FIXME this returns immediately after creation not when the window is closed
    return ReturnType(main_window.matching_dataframe())


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
        theme="dark",
        **qtKwargs,
    ):
        super().__init__(*qtArgs, **qtKwargs)

        self._colorMap = colorMap
        self.theme = theme
        self.updateTheme()

        self.registerKeyboardActions()

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

        self.matrixBorderSize = (120, 80)
        self.matrixAxisLabelSize = (80, 20)
        self.matrixGridLevels = [(5, -0.5), (1, -0.5)]
        self.legendWidth = 200
        self.barWidth = 0.3
        self.trSuperDigits = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

        # setup window appearance
        self.setWindowTitle("Chromosome size estimation: analysis plots")
        self.resize(20 * self.m, 40 * self.n)
        self.setCentralWidget(pg.GraphicsLayoutWidget(show=True, parent=self))

        self._attachMatrixPlot()

        self.show()

    def switchTheme(self):
        if self.theme == "dark":
            self.theme = "light"
        elif self.theme == "light":
            self.theme = "dark"
        else:
            raise Exception(f"unkown theme: {self.theme}")

        self.updateTheme()

    def updateTheme(self):
        if self.theme == "dark":
            self._setDarkTheme()
        elif self.theme == "light":
            self._setLightTheme()
        else:
            raise Exception(f"unkown theme: {self.theme}")

        if hasattr(self, "colorBarItem"):
            self._applyMatrixColorMap()
        if hasattr(self, "selectionPerScaffoldItem"):
            self._applyTristateColorMap()
        if hasattr(self, "scaffoldBarsItem"):
            self._applyDirectComparisonStyle()
        if self.centralWidget() is not None:
            self._applyDefaultColors()

    def _setLightTheme(self):
        log.info("switching theme to light")

        if not hasattr(self, "_lightColorMap"):
            self._lightColorMap = pg.colormap.get(self._colorMap, skipCache=True)
            self._lightColorMap.reverse()

        pg.setConfigOptions(foreground="d", background="w")
        self.matrixColorMap = self._lightColorMap
        self.tristateColorMap = pg.ColorMap([0.0, 0.5, 1.0], ["white", "black", "red"])
        self.directComparisonChromosomeStyle = {
            "brush": pg.mkBrush("#66666688"),
            "pen": pg.mkPen("#44444488"),
        }
        self.directComparisonScaffoldStyle = {
            "brush": pg.mkBrush("#00000088"),
            "pen": pg.mkPen("#333333DD"),
        }

    def _setDarkTheme(self):
        log.info("switching theme to dark")

        if not hasattr(self, "_darkColorMap"):
            self._darkColorMap = pg.colormap.get(self._colorMap, skipCache=True)
            self._darkColorMap.reverse()

        pg.setConfigOptions(foreground="d", background="k")
        self.matrixColorMap = self._darkColorMap
        self.tristateColorMap = pg.ColorMap([0.0, 0.5, 1.0], ["black", "white", "red"])
        self.directComparisonChromosomeStyle = {
            "brush": pg.mkBrush("#66666688"),
            "pen": pg.mkPen("#88888888"),
        }
        self.directComparisonScaffoldStyle = {
            "brush": pg.mkBrush("#FFFFFF88"),
            "pen": pg.mkPen("#FFFFFFDD"),
        }

    def registerKeyboardActions(self):
        self.registerKeyboardAction(
            QtGui.QKeySequence.HelpContents, self.showHelp, "Show this help dialog"
        )
        self.registerKeyboardAction(
            QtGui.QKeySequence.Print, self.export, "Export current plots as SVG"
        )
        self.registerKeyboardAction(
            QtGui.QKeySequence.Save, self.save, "Save selected matching to file"
        )
        self.registerKeyboardAction(
            QtCore.Qt.Key.Key_T,
            self.switchTheme,
            "Switch theme between light and dark.",
        )
        self.registerKeyboardAction(
            QtGui.QKeySequence.Quit, self.close, "Quit the plotting application."
        )

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
        # show full frame, label tick marks at top side, with some extra space
        # for labels
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
        # prepare transform to center the corner element on the origin, for
        # any assigned image
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
        # show full frame, label tick marks at top side, with some extra space
        # for labels
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
        # prepare transform to center the corner element on the origin, for
        # any assigned image
        alignPixelTransform = QtGui.QTransform().translate(-0.5, -0.5)

        self.selectionPerScaffoldItem = pg.ImageItem()
        self.selectionPerScaffoldItem.setTransform(alignPixelTransform)

        # display plot
        self.selectionPerScaffoldPlotItem.addItem(self.selectionPerScaffoldItem)
        self.selectionPerScaffoldPlotItem.autoRange()

        # Update plot if the matching changes
        self.sigMatchingChanged.connect(self.updateSelectionPerScaffoldItem)

        # add a legend
        self.selectionLegend = pg.LegendItem(offset=(1, 1), sampleType=ItemSample)
        self.selectionLegend.setParentItem(self.selectionPerScaffoldLegendItem)

        self._applyTristateColorMap()

    def _applyTristateColorMap(self):
        self.selectionPerScaffoldItem.setLookupTable(
            self.tristateColorMap.getLookupTable(nPts=3)
        )

        stateColors = self.tristateColorMap.getColors(mode="qcolor")

        if len(self.selectionLegend.items) < 3:
            self.selectionLegend.clear()
            labels = [
                "Scaffold unselected",
                "Scaffold selected",
                "Scaffold over-selected",
            ]
            for color, label in zip(stateColors, labels):
                self.selectionLegend.addItem(
                    pg.BarGraphItem(x=[], height=[], brush=color, pen="#88888888"),
                    label,
                )
        else:
            for legendItem, color in zip(self.selectionLegend.items, stateColors):
                sample = legendItem[0]
                sample.item.setOpts(brush=color)
            self.selectionLegend.updateSize()

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
        # show full frame, label tick marks at left side, with some extra
        # space for labels
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
        # prepare transform to center the corner element on the origin, for
        # any assigned image
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
        # show full frame, label tick marks at top side, with some extra space
        # for labels
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
        # prepare transform to center the corner element on the origin, for
        # any assigned image
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
        self._applyMatrixColorMap()

    def _applyMatrixColorMap(self):
        self.colorBarItem.setColorMap(self.matrixColorMap)

    def _applyDefaultColors(self):
        # FIXME update colors of plot/legend titles
        self.centralWidget().setBackground("default")
        for item in self.centralWidget().ci.items.keys():
            if hasattr(item, "getAxis"):
                for axis in ("left", "bottom", "right", "top"):
                    ax = item.getAxis(axis)
                    ax.setPen()
                    ax.setTextPen()

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
        # show full frame, label tick marks at bottom side, with some extra
        # space for labels
        self.directComparisonPlotItem.showAxes(
            True,
            showValues=(True, False, False, True),
            size=(self.matrixAxisLabelSize[0], None),
        )
        for axis in ("top", "bottom"):
            self.directComparisonPlotItem.getAxis(axis).setTickSpacing(1, 1)
        yAxis = self.directComparisonPlotItem.getAxis("left")
        yAxis.enableAutoSIPrefix(False)
        yAxis.setLabel("Size", "bp")
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

        self.chromosomeBarsItem = pg.BarGraphItem(
            x=self.chrIndices - self.barWidth / 2,
            y0=np.ones_like(self.estimates),
            height=self.estimates,
            width=self.barWidth,
        )
        self.scaffoldBarsItem = pg.BarGraphItem(x=[], height=[], width=self.barWidth)
        self._applyDirectComparisonStyle()

        # display bars
        self.directComparisonPlotItem.addItem(self.chromosomeBarsItem)
        self.directComparisonPlotItem.addItem(self.scaffoldBarsItem)

        legend = pg.LegendItem(offset=(0, 30), sampleType=ItemSample)
        legend.setParentItem(self.directComparisonLegendItem)
        legend.addItem(self.chromosomeBarsItem, "Chromosome size estimates")
        legend.addItem(self.scaffoldBarsItem, "Combined scaffold sizes")

        # Update indicator and text if the matching changes
        self.sigMatchingChanged.connect(self.updateScaffoldBarsItem)

    def _applyDirectComparisonStyle(self):
        self.chromosomeBarsItem.setOpts(**self.directComparisonChromosomeStyle)
        self.scaffoldBarsItem.setOpts(**self.directComparisonScaffoldStyle)

    def registerKeyboardAction(self, key, action, description):
        if not hasattr(self, "_keyboardActions"):
            self._keyboardActions = list()
        self._keyboardActions.append((key, action, description))

    def keyReleaseEvent(self, e):
        """Handle key release events for the window"""
        for key, action, _ in self._keyboardActions:
            if isinstance(key, QtGui.QKeySequence.StandardKey):
                if e == key:
                    action()
                    return
            elif isinstance(key, QtCore.Qt.Key):
                if e.key() == key:
                    action()
                    return

    def export(self):
        self._hideCrossHair(hide=True)
        exporter = SVGExporter(self.centralWidget().scene(), parent=self)
        if self.theme == "light":
            exporter.parameters()["background"] = pg.mkColor(255, 255, 255, 0)
        else:
            exporter.parameters()["background"] = pg.mkColor(0, 0, 0, 255)
        exporter.export()
        self._hideCrossHair(hide=False)

    def matching_dataframe(self):
        chromosome_sizes = self.estimates.iloc[self.matching[:, 1]]
        scaffold_sizes = self.scaffoldSizes.iloc[self.matching[:, 0]]

        return pd.DataFrame(
            {
                "chromosome": chromosome_sizes.index,
                "chromosome_size": chromosome_sizes.array,
                "scaffold": scaffold_sizes.index,
                "scaffold_size": scaffold_sizes.array,
            }
        )

    def save(self):
        fileDialog = pg.FileDialog(self)
        fileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        fileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        fileDialog.setNameFilter(self.tr("Comma-separated values (*.csv)"))
        fileDialog.accepted.connect(
            lambda: self.matching_dataframe().to_csv(
                fileDialog.selectedFiles()[0], index=False
            )
        )
        fileDialog.exec_()

    helpBaseTemplate = """\
<table>
    <tr style="">
        <td style="padding-bottom: 10px; font-style: italic;">Key</td>
        <td style="padding-bottom: 10px; font-style: italic;">Description</td>
    </tr>
    {keys}
</table>"""
    helpKeyTemplate = (
        '<tr><td style="padding-right: 20px">{key}</td><td>{desc}</td></tr>'
    )

    def showHelp(self):
        helpText = self.helpBaseTemplate.format(
            keys="".join(
                self.helpKeyTemplate.format(
                    key=QtGui.QKeySequence(key).toString(), desc=desc
                )
                for key, _, desc in self._keyboardActions
            )
        )

        QtGui.QMessageBox.information(self, "Help", helpText)

    def _hideCrossHair(self, hide=True):
        for hline in self.__matrixCrosshairHLines:
            if hide:
                hline.old_pos = hline.getPos()
                hline.setPos(-100_000)
            else:
                hline.setPos(hline.old_pos)
                del hline.old_pos
        for vline in self.__matrixCrosshairVLines:
            if hide:
                vline.old_pos = vline.getPos()
                vline.setPos(-100_000)
            else:
                vline.setPos(vline.old_pos)
                del vline.old_pos

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
        # update correlation per chromosome plot
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
            y0=y0s,
            height=y1s - y0s,
        )

        self.directComparisonPlotItem.setYRange(
            np.min(y1s),
            np.max(y1s),
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
            self.handleMouseClick is not None
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
            f"chr: {chrom}  scaff: {scaff}  absdiff: {absdiff} ",
            f"score: {self.matchingScore}",
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
        if self.parent is not None:
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

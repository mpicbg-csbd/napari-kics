from math import ceil, floor

from qtpy.QtCore import QSignalBlocker, Signal
from qtpy.QtWidgets import QDoubleSpinBox, QHBoxLayout, QSizePolicy, QSlider, QWidget


class InputDoubleSlider(QWidget):
    valueChanged = Signal(int)

    NoTicks = QSlider.NoTicks
    TicksBothSides = QSlider.TicksBothSides
    TicksAbove = QSlider.TicksAbove
    TicksBelow = QSlider.TicksBelow
    TicksLeft = QSlider.TicksLeft
    TicksRight = QSlider.TicksRight

    def __init__(self, parent=None, scale=None, from_slider=None, to_slider=None):
        super().__init__(parent)

        # create slider component
        self.slider = QSlider(self)
        self.slider.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        # self.slider.setSizePolicy(
        #     QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        # )
        self.slider.setMinimumWidth(100)
        self.slider.valueChanged.connect(lambda v: self._syncValue(self.input, v))
        self.slider.valueChanged.connect(lambda _: self.valueChanged.emit(self.value()))

        # create input component (spin box)
        self.input = QDoubleSpinBox(self)
        self.input.setFixedWidth(100)
        self.input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.input.valueChanged.connect(lambda v: self._syncValue(self.slider, v))
        self.input.valueChanged.connect(lambda _: self.valueChanged.emit(self.value()))

        # set scaling (requires the components)
        if scale is None and from_slider is None and to_slider is None:
            self.setScale(scale=1)
        else:
            self.setScale(scale=scale, from_slider=from_slider, to_slider=to_slider)

        # layout
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.slider)
        self.layout().addWidget(self.input)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    __delegate2slider = {
        "orientation",
        "setOrientation",
        "setTickInterval",
        "setTickPosition",
        "tickInterval",
        "tickPosition",
    }

    __delegate2input = {
        "cleanText",
        "decimals",
        "displayIntegerBase",
        "maximum",
        "minimum",
        "prefix",
        "setDecimals",
        "setDisplayIntegerBase",
        "setPrefix",
        "setSingleStep",
        "setStepType",
        "setSuffix",
        "singleStep",
        "stepType",
        "suffix",
        "value",
    }

    def __getattr__(self, name):
        if name in self.__delegate2input:
            return getattr(self.input, name)
        elif name in self.__delegate2slider:
            return getattr(self.slider, name)
        else:
            raise AttributeError(obj=self, name=name)

    def setScale(self, scale=None, from_slider=None, to_slider=None):
        if scale is not None and from_slider is None and to_slider is None:
            self._scale = scale
            self._from_slider = lambda x: x * scale
            self._to_slider = lambda x: x / scale
        elif scale is None and from_slider is not None and to_slider is not None:
            self._scale = None
            self._from_slider = from_slider
            self._to_slider = to_slider
        else:
            raise ValueError("must provide either scale or from_slider and to_slider")

        self.slider.setMinimum(int(floor(self._to_slider(self.input.minimum()))))
        self.slider.setMaximum(int(ceil(self._to_slider(self.input.maximum()))))

    def scale(self):
        if self._scale is not None:
            return self._scale
        else:
            return {"from_slider": self._from_slider, "to_slider": self._to_slider}

    def setMinimum(self, min_):
        self.slider.setMinimum(int(floor(self._to_slider(min_))))
        self.input.setMinimum(min_)

    def setMaximum(self, max_):
        self.slider.setMaximum(int(ceil(self._to_slider(max_))))
        self.input.setMaximum(max_)

    def setRange(self, min_, max_):
        self.setMinimum(min_)
        self.setMaximum(max_)

    def setValue(self, value):
        self.slider.setValue(int(round(self._to_slider(value))))
        self.input.setValue(value)

    def _syncValue(self, dest, value):
        blocker = QSignalBlocker(dest)
        if dest is self.slider:
            self.slider.setValue(int(round(self._to_slider(value))))
        elif dest is self.input:
            self.input.setValue(self._from_slider(value))
        else:
            raise ValueError()
        blocker.unblock()

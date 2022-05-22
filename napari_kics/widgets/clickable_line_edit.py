# ------------------------------------------------------------------------
# Clickable line edit
# ------------------------------------------------------------------------
# based on https://stackoverflow.com/questions/46671067/clear-qlineedit-on-click-event

import os.path

import qtpy.QtCore as QtCore
from qtpy.QtWidgets import QFileDialog, QLineEdit


class ClickableLineEdit(QLineEdit):
    sigAccepted = QtCore.Signal(str)
    sigRejected = QtCore.Signal()

    def __init__(
        self,
        mode,
        *,
        placeholderText="",
        caption="",
        dir="",
        filter="",
        selectedFilter="",
        options=QFileDialog.Options(),
    ):
        super().__init__()

        self.mode = mode
        self.setPlaceholderText(placeholderText)
        self.caption = caption
        self.dir = dir
        self.filter = filter
        self.selectedFilter = selectedFilter
        self.options = options

    def mousePressEvent(self, event):
        self.showDialog()
        super().mousePressEvent(event)

    def showDialog(self):
        text = None

        if self.mode == "directory":
            text = QFileDialog.getExistingDirectory(
                parent=self,
                caption=self.caption,
                directory=self.dir,
                options=self.options,
            )
        elif self.mode == "openFile":
            text = QFileDialog.getOpenFileName(
                parent=self,
                caption=self.caption,
                directory=self.dir,
                options=self.options,
                filter=self.filter,
                initialFilter=self.selectedFilter,
            )[0]
        elif self.mode == "saveFile":
            text = QFileDialog.getSaveFileName(
                parent=self,
                caption=self.caption,
                directory=self.dir,
                options=self.options,
                filter=self.filter,
                initialFilter=self.selectedFilter,
            )[0]
        else:
            raise ValueError(f"unknown mode: {self.mode}")

        if text is None or len(text) == 0:
            self.sigRejected.emit()
            return False
        else:
            self.setText(text)
            self.dir = os.path.basename(text)
            self.sigAccepted.emit(text)
            return True

    def setText(self, text):
        self.dir = os.path.basename(text)
        super().setText(text)

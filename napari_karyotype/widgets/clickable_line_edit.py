# ------------------------------------------------------------------------
# Clickable line edit
# ------------------------------------------------------------------------
# based on https://stackoverflow.com/questions/46671067/clear-qlineedit-on-click-event

from qtpy.QtWidgets import QLineEdit, QFileDialog


class ClickableLineEdit(QLineEdit):
    def __init__(self, default_text="./"):
        super().__init__()
        self.setText(default_text)
        self.listeners = []

    def mousePressEvent(self, event):
        path = QFileDialog.getExistingDirectory(
            parent=self, caption="Save directory path", directory=self.text()
        )
        self.setText(path)
        [listener(path) for listener in self.listeners]

        super().mousePressEvent(event)

    def add_listener(self, listener):
        self.listeners.append(listener)

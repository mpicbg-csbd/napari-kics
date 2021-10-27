def get_img(name, viewer):
    names = [layer.name for layer in viewer.layers]

    if name in names:
        ind = names.index(name)
        return viewer.layers[ind]
    else:
        raise Exception(
            f"[get_img]: Failed to retrieve the image with the name {name}. "
            f"Make sure the requested data is properly imported/generated and repeat the operation.")


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
        path = QFileDialog.getExistingDirectory(parent=self, caption='Save directory path', directory=self.text())
        self.setText(path)
        [listener(path) for listener in self.listeners]

        super().mousePressEvent(event)

    def add_listener(self, listener):
        self.listeners.append(listener)

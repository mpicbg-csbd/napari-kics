from .guess_chromosome_labels import *
from .label_history_processor import *


def get_img(name, viewer):
    names = [layer.name for layer in viewer.layers]

    if name in names:
        ind = names.index(name)
        return viewer.layers[ind]
    else:
        raise Exception(
            f"[get_img]: Failed to retrieve the image with the name {name}. "
            f"Make sure the requested data is properly imported/generated and repeat the operation."
        )

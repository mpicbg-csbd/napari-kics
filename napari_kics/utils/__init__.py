import numpy as np

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
            "Make sure the requested data is properly imported/generated "
            "and repeat the operation."
        )


def bbox2shape(bbox):
    return np.array(
        [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
        ]
    )


def replace_label(label_layer, old_label, new_label):
    """Replace all occurrences of `old_label` in `label_layer` by `new_label`.

    This method is similar to napari's `fill` method but acts globally and is
    much faster.

    If `old_label` is iterable, all the named labels will be efficiently
    replaced in a single history step.
    """
    labels = label_layer.data
    where = None
    try:
        for label in old_label:
            if where is None:
                where = labels == label
            else:
                where |= labels == label
    except TypeError:
        where = labels == old_label

    where_indices = np.nonzero(where)
    label_layer._save_history(
        (
            where_indices,
            np.array(labels[where_indices], copy=True),
            new_label,
        )
    )
    labels[where_indices] = new_label
    label_layer.refresh()

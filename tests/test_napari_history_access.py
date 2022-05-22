import napari
import numpy as np


def test_napari_history_access():
    # Create some labels layer
    labels = np.array(
        [
            [0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4],
        ]
    )
    viewer = napari.view_labels(labels)
    layer = viewer.layers[0]
    # Create a history entry
    layer.fill((0.5, 0.5), 5)

    # This is the structure we are expecting
    [((xs, ys), old_labels, new_label)] = layer._undo_history[0]
    assert np.array_equiv(xs, [0, 0, 0, 0, 0])
    assert np.array_equiv(ys, [0, 1, 2, 3, 4])
    assert np.array_equiv(old_labels, [0, 0, 0, 0, 0])
    assert new_label == 5

import numpy as np
from collections import namedtuple


class ChangeRecord:
    def __init__(self, area_diff, xs, ys):
        self.area_diff = area_diff
        self.xs = xs
        self.ys = ys

    def coord(self):
        return (self.xs[0], self.ys[0])

    def bbox(self, bbox=None):
        if bbox is None:
            return (
                min(self.xs),
                min(self.ys),
                max(self.xs),
                max(self.ys),
            )
        else:
            _bbox = self.bbox()

            return (
                min(_bbox[0], bbox[0]),
                min(_bbox[1], bbox[1]),
                max(_bbox[2], bbox[2]),
                max(_bbox[3], bbox[3]),
            )


class LabelHistoryProcessor:
    def __init__(self, label_layer):

        self.label_layer = label_layer
        self.history_queue_length = 0
        self.history_last_step_length = 0

    def recent_changes(self):
        # print(f"[recent_changes]: entry")
        # print(f"[recent_changes]: undo history is {self.label_layer._undo_history}")
        # print(f"[recent_changes]: redo history is {self.label_layer._redo_history}")

        # apparently, undo and redo history get erased upon the layer visibility toggle
        # first clause is to account for that, should refactor the entire "if" later on
        if (
            len(self.label_layer._undo_history) == 0
            and len(self.label_layer._redo_history) == 0
        ):
            self.history_queue_length = 0
            self.history_last_step_length = 0
            return {}

        elif len(self.label_layer._undo_history) > self.history_queue_length:
            factor = +1
            step = self.label_layer._undo_history[-1]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = len(step)
            # print(f"self history last step length is {self.history_last_step_length}")

        elif len(self.label_layer._undo_history) < self.history_queue_length:
            factor = -1
            step = self.label_layer._redo_history[-1]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = 0

        elif (
            len(self.label_layer._undo_history) != 0
            and len(self.label_layer._undo_history[-1]) > self.history_last_step_length
        ):
            factor = +1
            step_ = self.label_layer._undo_history[-1]
            new_length = len(step_)
            step = step_[self.history_last_step_length : new_length]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = new_length
            # print(f"self history last step length is {self.history_last_step_length}")

        else:
            return {}

        # print(f"step is {step}")

        changes = {}

        def extend_changes(label, area, xs, ys):
            if label in changes:
                changes[label].area_diff += factor * area
                changes[label].xs = np.concatenate((changes[label].xs, xs))
                changes[label].ys = np.concatenate((changes[label].ys, ys))
            else:
                changes[label] = ChangeRecord(factor * area, xs, ys)

        for (xs, ys), old_labels, new_label in step:
            removed_labels, removed_labels_area = np.unique(
                old_labels, return_counts=True
            )

            total_removed_area = 0
            for label, area in zip(removed_labels, removed_labels_area):
                extend_changes(
                    label,
                    -area,
                    xs[total_removed_area : total_removed_area + area],
                    ys[total_removed_area : total_removed_area + area],
                )
                total_removed_area += area

            extend_changes(new_label, total_removed_area, xs, ys)

        return changes

import numpy as np


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
        for coords, old_labels, new_label in step:
            removed_labels, removed_labels_area = np.unique(
                old_labels, return_counts=True
            )

            for label, area in zip(removed_labels, removed_labels_area):
                if label in changes:
                    changes[label] += -factor * area
                else:
                    changes[label] = -factor * area

            if new_label in changes:
                changes[new_label] += factor * np.sum(removed_labels_area)
            else:
                changes[new_label] = factor * np.sum(removed_labels_area)
            # print(f"dict at the current substep: {changes}")

        return changes

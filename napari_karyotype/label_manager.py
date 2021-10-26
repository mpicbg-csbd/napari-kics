import numpy as np

class LabelManager():

    def __init__(self, label_layer):
        self.label_layer = label_layer
        self.history_queue_length = 0
        self.history_last_step_length = 0

    def process_history_step(self):
        print(f"[process_history_step]: entry")
        print(f"[process_history_step]: undo history is {self.label_layer._undo_history}")
        print(f"[process_history_step]: redo history is {self.label_layer._redo_history}")

        print(f"")

        # apparently, undo and redo history get erased upon the layer visibility toggle
        # first clause is to account for that, should refactor the entire "if" later on
        if (len(self.label_layer._undo_history) == 0 and len(self.label_layer._redo_history) == 0):
            self.history_queue_length = 0
            self.history_last_step_length = 0
            return {}

        elif len(self.label_layer._undo_history) > self.history_queue_length:
            factor = +1
            step = self.label_layer._undo_history[-1]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = len(step)
            print(f"self history last step length is {self.history_last_step_length}")

        elif len(self.label_layer._undo_history) < self.history_queue_length:
            factor = -1
            step = self.label_layer._redo_history[-1]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = 0

        elif len(self.label_layer._undo_history) != 0 and len(
                self.label_layer._undo_history[-1]) > self.history_last_step_length:
            factor = +1
            step_ = self.label_layer._undo_history[-1]
            new_length = len(step_)
            step = step_[self.history_last_step_length:new_length]
            self.history_queue_length = len(self.label_layer._undo_history)
            self.history_last_step_length = new_length
            print(f"self history last step length is {self.history_last_step_length}")


        else:
            return {}

        # print(f"step is {step}")

        res_dict = {}

        for sub_step in step:

            labels_removed, labels_remove_counts = np.unique(sub_step[1], return_counts=True)
            label_added = sub_step[2]

            for ind, label in enumerate(labels_removed):

                if label in res_dict:
                    res_dict[label] += -factor * labels_remove_counts[ind]
                else:
                    res_dict[label] = -factor * labels_remove_counts[ind]

            if label_added in res_dict:
                res_dict[label_added] += factor * np.sum(labels_remove_counts)
            else:
                res_dict[label_added] = factor * np.sum(labels_remove_counts)

            print(f"dict at the current substep: {res_dict}")

        return res_dict
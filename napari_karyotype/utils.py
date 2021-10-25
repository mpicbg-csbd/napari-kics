from functools import wraps
from napari.qt.threading import thread_worker
import numpy as np

DEBUG = True


def get_img(name, viewer):
    names = [layer.name for layer in viewer.layers]

    if name in names:
        ind = names.index(name)
        return viewer.layers[ind]
    else:
        raise Exception(
            f"[get_img]: Failed to retrieve the image with the name {name}. Make sure the requested data is properly imported/generated and repeat the operation.")


# ------------------------------------------------------------------------
# updating napari layers with new data
# ------------------------------------------------------------------------
def update_layer(img_name, img, viewer):
    print(f"[update_layer]: updating layers with data of shape {img.shape} and name {img_name}")
    try:
        viewer.layers[img_name].data = img
    except KeyError:
        viewer.add_image(img, name=img_name)


def update_layer_from_dict(viewer, di):
    [update_layer(name, data, viewer) for (name, data) in di.items()]


def get_updater(viewer):
    def updater(outputs_dict):
        update_layer_from_dict(viewer, outputs_dict)

    return updater


# ------------------------------------------------------------------------
# make a wrapper for the function to be executed on a dedicated thread
# ------------------------------------------------------------------------
def make_async(func, state, viewer, output_names, completion_flag=None):
    @wraps(func)
    def async_wrapper(*args, **kwargs):
        # @thread_worker
        # def worker():
        #     outputs = func(*args, **kwargs)
        #     if type(outputs) != tuple:
        #         outputs = (outputs,)
        #     return dict(zip(output_names, outputs))
        #
        # w = worker()
        # w.returned.connect(get_updater(viewer))

        outputs = func(*args, **kwargs)
        if type(outputs) != tuple:
            outputs = (outputs,)
        # return dict(zip(output_names, outputs))
        updater = get_updater(viewer)
        updater(dict(zip(output_names, outputs)))

        # if not (completion_flag is None):
        #     w.started.connect(lambda: completion_flag.set(False))
        #     w.returned.connect(lambda results: completion_flag.set(True))
        #
        # w.start()

    return async_wrapper


# ------------------------------------------------------------------------
# parsing a config
# ------------------------------------------------------------------------

def parse_config(config, state, viewer):
    magicgui_dict = {}

    def get_callback(v):
        def callback(e):

            if v is None:
                active = viewer.layers.selection.active
                print(f"------ active is {active}----------")
                if active is None:
                    raise Exception("No image selected. Please add an image first.")
                else:
                    res = active.data
            elif v in state.keys():
                res = state[v]
            else:
                raise Exception(f"Failed to retrieve the state entry with the name \"{v}\", "
                                f"please ensure it was properly generated in the previous steps.")
            return res

        return callback

    inputs_dict = config.pop("inputs")
    outputs_list = config.pop("outputs")

    for k, v in config.items():
        magicgui_dict[k] = v

    for k, v in inputs_dict.items():
        magicgui_dict[k] = dict(bind=get_callback(v))

    return magicgui_dict, outputs_list


# ------------------------------------------------------------------------
# creating a widget
# ------------------------------------------------------------------------
def create_widget(func, func_config, state, viewer, verbose=True):
    import magicgui
    magicgui_dict, return_names = parse_config(func_config, state, viewer)

    if verbose:
        import inspect
        print()
        print(f"[create_widget]: parsed magic_gui dict is {magicgui_dict}")
        print()
        print(f"[create_widget]: inspect function signature {inspect.signature(func)}")

    completion_flag = ObservableFlag(True)

    func_async = make_async(func, state, viewer, return_names, completion_flag)
    # func_async = func

    widget = magicgui.magicgui(func_async, **magicgui_dict)

    # run_button = get_run_button(widget.native)

    # listener = lambda v: run_button.setEnabled(v)

    # completion_flag.add_listener(listener)

    return widget.native


# ------------------------------------------------------------------------
# observable boolean flag
# ------------------------------------------------------------------------
class ObservableFlag:

    def __init__(self, value=True):
        self._value = value
        self.listeners = []

    def set(self, value):
        self._value = value
        [listener(value) for listener in self.listeners]

        print(f"[ObservableFlag]: value set to {value}")

    def add_listener(self, listener):
        self.listeners.append(listener)

    def remove_listener(self, listener):
        self.listeners.remove(listener)


# ------------------------------------------------------------------------
# function to access the run button of a widget
# ------------------------------------------------------------------------
def get_run_button(widget):
    names = []
    for w in widget.children():
        try:
            name = w.text()
        except:
            name = None
        names.append(name)
    return widget.children()[names.index("Run")]


# ------------------------------------------------------------------------
# check if array is in the list
# ------------------------------------------------------------------------
def arr_in_list(arr, list):
    return np.sum([(arr == elem).all() for elem in list])


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
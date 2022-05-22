"""
This module is an example of a barebones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    from .widgets import KaryotypeWidget

    return [KaryotypeWidget]


# --------------------------------------------------------
# sample data
# --------------------------------------------------------


def load_sample_data():
    from pathlib import Path

    from skimage import io

    from .global_signals import signals

    data_base = f"{Path(__file__).parent}/resources/data/mHomSap_male"
    data = io.imread(f"{data_base}.jpeg")

    signals().sampleLoaded.emit(data_base)

    return [(data, {"name": "karyotype"})]


@napari_hook_implementation
def napari_provide_sample_data():
    return {"sample": load_sample_data}


# --------------------------------------------------------

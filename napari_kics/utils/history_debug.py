import napari


def print_last_step(history):

    print("--- printing history ---")
    print(f"--- history size: {len(history)} ---")

    if len(history) > 0:
        step = history[-1]
        print(f"---- step {len(history)-1} ----")
        print(f"---- step size: {len(step)} ----")

        for iind, substep in enumerate(step):
            print(f"---- substep {iind} ----")
            print(f"---- substep size: {len(substep)} ----")
            print(f"{substep}")


def print_history(history):

    print("--- printing history ---")
    print(f"--- history size: {len(history)} ---")

    for ind, step in enumerate(history):
        print(f"---- step {ind} ----")
        print(f"---- step size: {len(step)} ----")

        for iind, substep in enumerate(step):
            print(f"---- substep {iind} ----")
            print(f"---- substep size: {len(substep)} ----")
            print(f"{substep}")


if __name__ == "__main__":
    viewer = napari.Viewer()

    from skimage.draw import random_shapes

    image_shape = (256, 256)
    labels, _ = random_shapes(image_shape=image_shape, max_shapes=20, num_channels=1)
    labels = 255 - labels.reshape(image_shape)

    label_layer = viewer.add_labels(labels)
    label_layer.events.set_data.connect(
        lambda x: print_last_step(label_layer._undo_history)
    )
    napari.run()

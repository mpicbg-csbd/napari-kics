from skimage import io
import pandas as pd


class SavingManager():

    def __init__(self, viewer, table):
        self.viewer = viewer
        self.table = table

    def save_output(self, path):
        # images

        imgs_dict = self.get_imgs_dict()
        [io.imsave(f"{path}/{name}.png", img) for (name, img) in imgs_dict.items()]

        # dataframe
        dataframe = pd.DataFrame()
        dataframe["tags"] = list(self.table.model().dataframe[1])
        dataframe["labels"] = list(self.table.model().dataframe.index)
        dataframe["area"] = list(self.table.model().dataframe[2])
        dataframe.to_csv(f"{path}/data.csv", index=False)

        # screenshot
        self.viewer.screenshot(f"{path}/screenshot.png")

    def get_imgs_dict(self):
        res = {}
        names = [layer.name for layer in self.viewer.layers]
        res[self.input_img_name] = self.viewer.layers[names.index(self.input_img_name)].data
        res["thresholded"] = self.viewer.layers[names.index("thresholded")].data
        res["labelled"] = self.viewer.layers[names.index("labelled")].data

        res["labelled_color"] = self.viewer.layers[names.index("labelled")].get_color(list(res["labelled"]))

        return res

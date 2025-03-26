import os

import numpy as np
import pandas as pd


class DataManager:
    def __init__(self, metadata_path, images_base_path, smart_sort):
        self.current_index = 0
        self.images_base_path = images_base_path
        self.df = pd.read_csv(metadata_path)
        if "label" not in self.df.columns:
            try:
                self.df["label"] = np.nan
                self.labels = self.df["prediction"].unique()
            except KeyError:
                raise ("Dataset must contain either a label or prediction column!")
        else:
            self.labels = self.df["label"].unique()
        if "prediction" not in self.df.columns:
            # create blank df for adding labels
            files = os.listdir(self.images_base_path)
            files = [
                file for file in files if os.path.isfile(os.path.join(self.images_base_path, file))
            ]
            self.df = pd.DataFrame(columns=["label", "image_path"], index=range(len(files)))
            self.df["image_path"] = files
        else:
            if smart_sort:
                self.df = self._sort_by_certainty()

    def _sort_by_certainty(self):
        pred_cols = [x for x in self.df.columns if x.startswith("class")]
        self.df["certainty"] = self.df[pred_cols].var(axis="columns")
        return self.df.sort_values(by="certainty", ascending=True).reset_index(drop=True)

    def current_data(self):
        data = self.df.iloc[self.current_index].copy()
        data["image_path"] = "/images/" + data["image_path"]
        return data

    def unique_labels(self):
        return self.labels

    def change_label(self, new_label):
        self.df.loc[self.current_index, "label"] = new_label

    def use_predicted_label(self):
        self.df.loc[self.current_index, "label"] = self.df.loc[self.current_index, "prediction"]

    def next_image(self):
        self.current_index = min(self.current_index + 1, len(self.df) - 1)

    def previous_image(self):
        self.current_index = max(self.current_index - 1, 0)

    def delete_image(self):
        os.remove(self.df.at[self.current_index, "image_path"])
        self.df = self.df.drop(self.df.index[self.current_index])
        self.df = self.df.reset_index(drop=True)
        self.current_index = min(self.current_index, len(self.df) - 1)

    def save_changes(self):
        self.df.to_csv("new_labels.csv", index=False)

    def get_progress(self):
        return {"current": self.current_index + 1, "total": len(self.df)}

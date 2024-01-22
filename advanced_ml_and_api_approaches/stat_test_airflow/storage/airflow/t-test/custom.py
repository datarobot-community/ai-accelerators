import numpy as np
import pandas as pd
from scipy import stats
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datarobot_drum.custom_task_interfaces import TransformerInterface


def text_to_rgba(s, *, dpi, **kwargs):
    fig = Figure(facecolor="none")
    fig.text(0, 0, s, **kwargs)
    with BytesIO() as buf:
        fig.savefig(buf, dpi=dpi, format="png", bbox_inches="tight",
                    pad_inches=0)
        buf.seek(0)
        rgba = plt.imread(buf)
    return rgba



class CustomTask(TransformerInterface):
    def fit(self, X:pd.DataFrame, y:pd.Series, output_dir:str, **kwargs) -> None:
        col_name = kwargs['parameters']['column_name']
        mu = kwargs['parameters']['mu']
        t_stat, p_value = stats.ttest_1samp(X[col_name].values, mu)
        fig = plt.figure()
        rgba1 = text_to_rgba(
            f"t_stat={t_stat}, p_value={p_value}",
            color="blue",
            #fontsize=20,
            dpi=200
        )
        fig.figimage(rgba1, 100, 50)
        plt.savefig(f'{output_dir}/text.png')

    def transform(self, data:pd.DataFrame) -> pd.DataFrame:
        return data
import base64
from io import BytesIO

from PIL import Image
import librosa
import librosa.display
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

plt.style.use("fivethirtyeight")

dr_dark_blue = "#08233F"
dr_blue = "#1F77B4"
dr_orange = "#FF7F0E"
dr_red = "#BE3C28"
dr_green = "#00c96e"


def generate_base64_image(im: Image) -> str:
    # From an image, return base64 encoded PNG image
    with BytesIO() as outfile:
        im.save(outfile, "png")
        image_bytes = outfile.getvalue()
    return base64.b64encode(image_bytes).decode("ascii")


def create_spectrogram_image(
    S: np.ndarray,
    sr: int = 22050,
    resize: bool = True,
    resize_width: int = 224,
    resize_height: int = 224,
    log: bool = True,
) -> Image:
    fig, ax = plt.subplots()
    plt.axis("off")
    plt.margins(0)

    S_db = librosa.amplitude_to_db(S, ref=np.max)
    if log:
        img = librosa.display.specshow(S_db, y_axis="log", sr=sr)
    else:
        img = librosa.display.specshow(S_db, sr=sr)

    buf = BytesIO()
    fig.savefig(buf, bbox_inches="tight", pad_inches=0)
    buf.seek(0)
    img_pil = Image.open(buf)

    if resize:
        img_pil = img_pil.resize((resize_width, resize_height))

    plt.clf()
    plt.close(fig)
    buf.truncate(0)
    buf.close()

    return img_pil


def plot_feature_impacts(model, top_n=100):
    feature_impacts = model.get_or_request_feature_impact()
    percent_tick_fmt = mtick.PercentFormatter(xmax=1.0)

    impact_df = pd.DataFrame(feature_impacts).head(top_n)
    impact_df.sort_values(by="impactNormalized", ascending=True, inplace=True)

    # Positive values are blue, negative are red
    bar_colors = impact_df.impactNormalized.apply(lambda x: dr_red if x < 0 else dr_blue)

    ax = impact_df.plot.barh(
        x="featureName",
        y="impactNormalized",
        legend=False,
        color=bar_colors,
        figsize=(12, 12),
    )
    ax.xaxis.set_major_formatter(percent_tick_fmt)
    ax.xaxis.set_tick_params(labeltop=True)
    ax.xaxis.grid(True, alpha=0.2)
    ax.yaxis.grid(False)
    ax.set_facecolor(dr_dark_blue)

    plt.ylabel("")
    plt.xlabel("Normalized Impact")
    plt.xlim((None, 1))  # Allow for negative impact
    plt.title(f"Feature Impact:\n{model.model_type}", y=1.04)


# Show all 4 spectrogram representations of a 5 sec audio recording
def show_specs(row, figsize=(8, 8)):
    fig = plt.figure(figsize=figsize)
    columns, rows = 2, 2

    specs = [
        "spectrogram",
        "spectrogram_mel",
        "spectrogram_harmonic",
        "spectrogram_percussive",
    ]
    for i in range(1, columns * rows + 1):
        spec_col = specs[i - 1]
        # convert base64 string back to pillow image
        msg = base64.b64decode(row[spec_col])
        buf = BytesIO(msg)
        img = Image.open(buf)

        fig.add_subplot(rows, columns, i)
        plt.imshow(img)
        plt.title(spec_col, fontsize=12)
        plt.xticks([])
        plt.yticks([])
    plt.suptitle(f"Spectrogram Images for {row['category']}", fontsize=14)
    plt.show()


def get_top_of_leaderboard(project, metric="LogLoss", verbose=True):
    # A helper method to assemble a dataframe with Leaderboard results and print a summary:
    leaderboard = []
    for m in project.get_models():
        leaderboard.append(
            [
                m.blueprint_id,
                m.featurelist.id,
                m.id,
                m.model_type,
                m.sample_pct,
                m.metrics[metric]["validation"],
                m.metrics[metric]["crossValidation"],
            ]
        )
    leaderboard_df = pd.DataFrame(
        columns=[
            "bp_id",
            "featurelist",
            "model_id",
            "model",
            "pct",
            "validation",
            "cross_validation",
        ],
        data=leaderboard,
    )

    if verbose == True:
        # Print a Leaderboard summary:
        print("Unique blueprints tested: " + str(len(leaderboard_df["bp_id"].unique())))
        print("Feature lists tested: " + str(len(leaderboard_df["featurelist"].unique())))
        print("Models trained: " + str(len(leaderboard_df)))
        print("Blueprints in the project repository: " + str(len(project.get_blueprints())))

        # Print the essential information for top models, sorted by accuracy from validation data:
        print("\n\nTop models in the leaderboard:")
        leaderboard_top = (
            leaderboard_df.sort_values(by="cross_validation", ascending=True)
            .head()
            .reset_index(drop=True)
        )
        display(leaderboard_top.drop(columns=["bp_id", "featurelist"], inplace=False))

        # # Show blueprints of top models:
        # for index, m in leaderboard_top.iterrows():
        #     Visualize.show_dr_blueprint(dr.Blueprint.get(project.id, m['bp_id']))

        return leaderboard_top

    else:
        return leaderboard_df

from datetime import datetime as dt

import datarobot as dr
import numpy as np
import pandas as pd
import streamlit as st
import toml

pd.options.plotting.backend = "plotly"

# import matplotlib.pyplot as plt
# plt.style.use('fivethirtyeight')

dr_dark_blue = "#08233F"
dr_blue = "#1F77B4"
dr_orange = "#FF7F0E"
dr_red = "#BE3C28"
dr_colors = [dr_orange, dr_blue, dr_red, dr_red]

plotly_legend = dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0.01)

plotly_font = dict(
    size=18,
)


def load_config():
    return toml.load("config/config.toml")


config = load_config()
client = dr.Client(token=config["API_KEY"], endpoint=config["ENDPOINT"])
deployment = dr.Deployment.get(config["DEPLOYMENT_ID"])


def uploaded_data_section(uploaded_file):
    try:
        uploaded_df = pd.read_csv(uploaded_file)
        sids = uploaded_df[config["SERIES_ID"]].nunique()
        periods = uploaded_df[config["DATE_COL"]].unique()
        st.write(f"The dataset contains:")
        st.write(f"- {sids} series;")
        st.write(
            f"- {len(periods)} periods between {periods.min()} and {periods.max()}."
        )
        st.write(uploaded_df.head())
        st.write(uploaded_df.tail())
        return uploaded_df
    except Exception as e:
        print(str(e))
        st.write("Unable to load uploaded data as CSV")


def clear_cache(vals):
    for val in vals:
        if val in st.session_state:
            del st.session_state[val]


def modify_ka_values(
    df: pd.DataFrame, date_col: str, target: str, ka_updates: dict, dates: list
):
    df_tmp = df.copy()

    if "all" in dates:
        target_max_date = df_tmp[df_tmp[target].notna()][date_col].max()
        mask = df_tmp[date_col] > target_max_date
    else:
        mask = df_tmp[date_col].isin(dates)

    for ka_col, ka_col_val in ka_updates.items():
        df_tmp.loc[mask, ka_col] = ka_col_val
        df_tmp["is_updated"] = 0
        df_tmp.loc[mask, "is_updated"] = 1
    return df_tmp


def add_make_predictions_button(
    uploaded_df: pd.DataFrame,
    deployment: dr.Deployment,
    date_col: str,
    series_id: str,
    target: str,
    run_id: str,
    params=["Uploaded data"],
):
    if st.button(
        "Make predictions",
        on_click=clear_cache,
        kwargs={"vals": ["preds"]},
        key="make_predictions",
    ):
        if "preds_hist" not in st.session_state:
            st.session_state.preds_hist = {}

        if st.session_state.preds_hist.get(run_id) is not None:
            preds = st.session_state.preds_hist[run_id].copy()
            return preds
        else:
            try:
                preds = make_predictions(
                    deployment, uploaded_df, date_col, series_id, target
                )
                preds["run_id"] = run_id
                preds["params"] = ";".join(params)
                st.session_state.preds_hist[run_id] = preds.copy()
                return preds
            except Exception as e:
                st.write(str(e))
    else:
        return None


def add_predictions_stats(data, date_col, series_id, preds_cols=None):
    data_tmp = data[data["is_pred_period"] == 1].copy()
    periods = data_tmp[date_col].unique()
    if preds_cols is not None:
        st.sidebar.write(
            f"The file contains predictions based on {len(preds_cols)} datasets:"
        )
        for p in preds_cols:
            st.sidebar.write(f"- {p}")

    st.sidebar.write(f"Predictions were made for:")
    st.sidebar.write(f"- {data_tmp[series_id].nunique()} series;")
    st.sidebar.write(
        f"- {len(periods)} periods between {periods.min()} and {periods.max()}."
    )


@st.cache_data
def make_predictions(
    _deployment, data, date_col, series_id, target, forecast_point=None
):
    """Makes predictions based on the deployment and the provided data

    Args:
        deployment (dr.Deployment):
        data (pd.DataFrame): the dataset to make predictions on
        preds_location (str): path to the folder to store predictions
        forecast_point (str, optional): Defaults to None.

    Returns:
        pd.DataFrame
    """

    preds = make_predictions_from_deployment(
        _deployment, data, forecast_point, wait_for_completion=True
    )

    # data_preds = pd.concat(preds)
    data_preds = preds.copy()

    cols_to_drop = [c for c in data_preds.columns if c.endswith("_y")]
    data_preds.drop(columns=cols_to_drop, inplace=True)
    cols_to_rename = {
        c: c.replace("_x", "") for c in data_preds.columns if c.endswith("_x")
    }
    data_preds.rename(columns=cols_to_rename, inplace=True)
    data_preds["is_pred_period"] = 1

    pred_col = [
        c for c in data_preds.columns if target in c and c.endswith("_PREDICTION")
    ]
    if len(pred_col) == 1:
        data_preds.rename(columns={pred_col[0]: f"{target}_prediction"}, inplace=True)

    perc_cols = [
        c
        for c in data_preds.columns
        if c.startswith("PREDICTION_") and "_PERCENTILE_" in c
    ]
    if len(perc_cols) == 2:
        perc_cols = {c: c.lower() for c in perc_cols}
        data_preds.rename(columns=perc_cols, inplace=True)

    pred_dt = dt.now().strftime("%Y%m%d_%H%M")
    data.to_csv(f"predictions/data_raw_{pred_dt}.csv", index=False)

    data_res = data[data[date_col] < data_preds[date_col].min()].copy()
    data_res["is_pred_period"] = 0
    data_res = pd.concat([data_res, data_preds], axis=0, ignore_index=True, sort=False)
    data_res.sort_values([series_id, date_col], inplace=True)
    data_res.reset_index(drop=True, inplace=True)

    data_res.to_csv(f"predictions/predictions_{pred_dt}.csv", index=False)

    return data_res


def make_predictions_from_deployment(
    deployment, data, forecast_point=None, wait_for_completion=True
):
    """
    Args:
        deployment (dr.Deployment):
        data (dr.Dataset):
        predictions_file (str): a path to a local file to write predictions
        forecast_point (str):

    Returns:
        prediction job
    """
    job, preds = dr.BatchPredictionJob.score_pandas(
        deployment=deployment.id,
        df=data,
        timeseries_settings={
            "type": "forecast",
            "forecast_point": forecast_point,
            "relax_known_in_advance_features_check": True,
        },
    )

    if wait_for_completion:
        job.wait_for_completion()

    return preds


def add_results_download_button(results: pd.DataFrame):
    csv = results.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        "Download predictions",
        csv,
        "predictions.csv",
        "text/csv",
        key="download_csv",
    )


def combine_predictions(preds_dct, date_col, series_id, target):
    preds_keys = list(preds_dct.keys())
    preds = preds_dct[preds_keys[0]].copy()
    pred_col = preds["params"][0]
    preds_cols = [pred_col]
    preds.rename(columns={f"{target}_prediction": pred_col}, inplace=True)
    for k in preds_keys[1:]:
        preds_tmp = preds_dct[k].copy()
        pred_col_tmp = preds_tmp["params"][0]
        preds_cols.append(pred_col_tmp)
        preds_tmp.rename(columns={f"{target}_prediction": pred_col_tmp}, inplace=True)
        preds = preds.merge(
            preds_tmp[[date_col, series_id, pred_col_tmp]],
            how="left",
            on=[date_col, series_id],
        )

    return preds, preds_cols


def plot_predictions_agg_overall(data, date_col, cols_to_plot, func):
    data_agg = data.groupby(date_col)[cols_to_plot].agg(func).replace(0, np.NaN)

    color_map = {}
    for i, (col, color) in enumerate(zip(cols_to_plot, dr_colors)):
        if i == 0 or col.startswith("prediction_") or col.endswith("_prediction"):
            color_map[col] = color
    ymin = data_agg.min().min() * 1.1
    ymin = 0 if ymin > 0 else ymin
    ymax = data_agg.max().max() * 1.1
    ax = data_agg.plot(
        title=f"Actuals and predictions {func}",
        color_discrete_map=color_map,
        markers=True,
    )
    ax.update_yaxes(range=[ymin, ymax])

    ax.update_layout(legend=plotly_legend, font=plotly_font)

    st.plotly_chart(ax)


def plot_predictions_agg_group(data, date_col, group_id, group_val, cols_to_plot, func):
    data_agg = data[data[group_id] == group_val].copy()
    data_agg = data_agg.groupby(date_col)[cols_to_plot].agg(func).replace(0, np.NaN)

    color_map = {}
    for i, (col, color) in enumerate(zip(cols_to_plot, dr_colors)):
        if i == 0 or col.startswith("prediction_") or col.endswith("_prediction"):
            color_map[col] = color
    ymin = data_agg.min().min() * 1.1
    ymin = 0 if ymin > 0 else ymin
    ymax = data_agg.max().max() * 1.1
    ax = data_agg.plot(
        title=f"{group_id} - {group_val}: actuals and predictions {func}",
        color_discrete_map=color_map,
        markers=True,
    )
    ax.update_yaxes(range=[ymin, ymax])

    ax.update_layout(legend=plotly_legend, font=plotly_font)

    st.plotly_chart(ax)


def plot_predictions_series(data, date_col, series_id, series_name, cols_to_plot):
    data_agg = data[data[series_id] == series_name][[date_col] + cols_to_plot].copy()
    data_agg.set_index(date_col, inplace=True)

    color_map = {}
    for i, (col, color) in enumerate(zip(cols_to_plot, dr_colors)):
        if i == 0 or col.startswith("prediction_") or col.endswith("_prediction"):
            color_map[col] = color
    ymin = data_agg.min().min() * 1.1
    ymin = 0 if ymin > 0 else ymin
    ymax = data_agg.max().max() * 1.1
    ax = data_agg.plot(
        title=f"{series_id} - {series_name}: actuals and predictions",
        color_discrete_map=color_map,
        markers=True,
    )
    ax.update_yaxes(range=[ymin, ymax])

    ax.update_layout(legend=plotly_legend, font=plotly_font)

    st.plotly_chart(ax)

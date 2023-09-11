import hashlib

import app_utils as au
from app_utils import config, deployment
import datarobot as dr
import numpy as np
import pandas as pd
import streamlit as st

client = dr.Client(token=config["API_KEY"], endpoint=config["ENDPOINT"])

date_col = config["DATE_COL"]
series_id = config["SERIES_ID"]
target = config["TARGET"]
cols_to_exclude = [
    date_col,
    series_id,
    target,
    "FORECAST_POINT",
    "FORECAST_DISTANCE",
    "DEPLOYMENT_APPROVAL_STATUS",
    "is_pred_period",
    "is_updated",
    "run_id",
    "params",
]

st.sidebar.image("dr_logo.jpg", use_column_width=True)
st.sidebar.title("Upload data to make predictions")

with st.expander("What is this app?", expanded=False):
    st.write(config["APP_INTRO"])

with st.expander("The deployment overview", expanded=False):
    # st.header('The deployment overview')
    st.write(f'Model: {deployment.model["type"]}')
    st.write(f'Target: {deployment.model["target_name"]}')
    st.write(f'Type: {deployment.model["target_type"]}')
    st.write(f"Features:")
    df_feats = pd.DataFrame(deployment.get_features()).drop(
        columns=["importance"], errors="ignore"
    )
    st.write(df_feats)
    # st.write("---")

uploaded_file = st.sidebar.file_uploader(
    "file_uploader", type="csv", label_visibility="hidden"
)

if uploaded_file is not None:
    st.sidebar.write("---")

    with st.expander("The uploaded data overview", expanded=False):
        # st.header('The uploaded data overview')
        df = au.uploaded_data_section(uploaded_file)
        target_max_date = df[df[target].notna()][date_col].max()
        dates_lst = sorted(df[df[date_col] > target_max_date][date_col].unique())
        df_to_preds = df.copy()
        # st.sidebar.write("---")
        # st.write("---")

    st.title("Prediction settings")
    selection = st.radio(
        "Modify known in advance (KA) values:",
        ("Yes", "No"),
        on_change=au.clear_cache,
        kwargs={"vals": ["preds"]},
        index=1,
        key="modify_ka_val_radio",
    )

    if selection == "Yes":
        if config.get("KA_COLS") is None:
            cols_all = df.select_dtypes(include="object").columns
            ka_cols = sorted([c for c in cols_all if c not in cols_to_exclude])
        else:
            ka_cols = config.get("KA_COLS")

        if len(ka_cols) > 0:
            st.header("Update settings")
            ka_cols_selected = st.multiselect(
                "Select KA columns:",
                ka_cols,
                default=None,
                key="ka_msel",
                on_change=au.clear_cache,
                kwargs={"vals": ["preds"]},
            )

            if len(ka_cols_selected) == 0:
                st.stop()

            with st.container():
                ka_cols_dct = {}
                for i, ka_col in enumerate(ka_cols_selected):
                    ka_col_vals = sorted([str(i) for i in df[ka_col].unique()])
                    ka_col_val = st.selectbox(
                        f'Select "{ka_col}" value:',
                        ["<select>", "<new>"] + ka_col_vals,
                        on_change=au.clear_cache,
                        kwargs={"vals": ["preds"]},
                        index=0,
                        key=f"ka_val_selectbox{i}",
                    )
                    if ka_col_val == "<new>":
                        ka_col_val_inp = st.text_input("Input new value:", "")
                    else:
                        ka_col_val_inp = ""

                    if ka_col_val not in ["<select>", "<new>"]:
                        ka_cols_dct[ka_col] = ka_col_val
                    elif ka_col_val == "<new>" and ka_col_val_inp != "":
                        ka_cols_dct[ka_col] = ka_col_val_inp

                    if ka_cols_dct.get(ka_col) is not None:
                        if str(ka_cols_dct[ka_col]) == "nan":
                            ka_cols_dct[ka_col] = np.NaN

                if len(ka_cols_dct) == len(ka_cols_selected):
                    dates_sel = st.multiselect(
                        "Select dates to change the value:",
                        ["all"] + dates_lst,
                        default="all",
                        key="dates_msel",
                        on_change=au.clear_cache,
                        kwargs={"vals": ["preds"]},
                    )
                    if len(dates_sel) == 0:
                        st.stop()

                    if "all" in dates_sel:
                        dates_sel = ["all"]
                    df_to_preds = au.modify_ka_values(
                        df, date_col, target, ka_cols_dct, dates_sel
                    )

                    with st.expander("The updated data overview", expanded=False):
                        # st.header('The updated data')
                        rows = df_to_preds["is_updated"].sum()
                        st.write(f"{rows} rows were updated in the columns:")

                        run_params = []
                        for ka_col, ka_col_val in ka_cols_dct.items():
                            st.write(f'- "{ka_col}" with the value "{ka_col_val}"')
                            run_params.append(ka_col + ":" + ka_col_val)
                        run_params.append("dates" + ":" + ",".join(sorted(dates_sel)))
                        run_params = sorted(run_params)
                        run_id = hashlib.sha256(
                            ";".join(run_params).encode()
                        ).hexdigest()
                        if "params_hist" not in st.session_state:
                            st.session_state.params_hist = {}
                        if st.session_state.params_hist.get(run_id) is None:
                            st.session_state.params_hist[run_id] = run_params

                        st.write(df_to_preds.head())
                        st.write(df_to_preds.tail())

                    preds = au.add_make_predictions_button(
                        df_to_preds,
                        deployment,
                        date_col,
                        series_id,
                        target,
                        run_id,
                        params=run_params,
                    )
                    if preds is not None:
                        st.session_state.preds = preds.copy()

                else:
                    st.stop()

        else:
            preds = au.add_make_predictions_button(
                df_to_preds, deployment, date_col, series_id, target, "Uploaded data"
            )
            if preds is not None:
                st.session_state.preds = preds.copy()

            if "params_hist" not in st.session_state:
                st.session_state.params_hist = {}

    else:
        preds = au.add_make_predictions_button(
            df_to_preds, deployment, date_col, series_id, target, "Uploaded data"
        )
        if preds is not None:
            st.session_state.preds = preds.copy()

        if "params_hist" not in st.session_state:
            st.session_state.params_hist = {}

    if "preds_hist" in st.session_state:
        st.sidebar.header("Download predictions")
        id_params = {
            k: ";".join(st.session_state.params_hist.get(k, ["Uploaded data"]))
            for k in st.session_state.preds_hist.keys()
        }
        param_ids = {v: k for k, v in id_params.items()}

        if len(id_params) > 1:
            param_names = ["<select>", "All predictions"] + sorted(id_params.values())
        else:
            param_names = ["<select>"] + sorted(id_params.values())

        down_name = st.sidebar.selectbox(
            f"Select predictions to download:",
            param_names,
            index=0,
            key="run_down_selectbox",
        )

        if down_name == "<select>":
            down_preds = None
            preds_cols = None
        elif down_name == "All predictions":
            down_preds, preds_cols = au.combine_predictions(
                st.session_state.preds_hist, date_col, series_id, target
            )
            cols_to_drop = ["run_id", "params", "DEPLOYMENT_APPROVAL_STATUS"]
            cols_to_drop += [c for c in down_preds.columns if "_percentile_" in c]
            down_preds.drop(columns=cols_to_drop, inplace=True, errors="ignore")
        else:
            down_id = param_ids[down_name]
            preds_cols = None
            down_preds = st.session_state.preds_hist[down_id].copy()

        if down_preds is not None:
            au.add_results_download_button(down_preds)
            au.add_predictions_stats(down_preds, date_col, series_id, preds_cols)

        st.sidebar.write("---")
        st.write("---")

        st.header("Overview settings")

        col1, col2 = st.columns([1, 2])

        with col1:
            param_name = st.selectbox(
                f"Select predictions:", param_names, index=0, key="run_param_selectbox"
            )

            if param_name == "<select>":
                st.stop()
            elif param_name == "All predictions":
                preds, cols_preds = au.combine_predictions(
                    st.session_state.preds_hist, date_col, series_id, target
                )
                cols_to_plot = [target] + cols_preds
            else:
                run_id = param_ids[param_name]
                preds = st.session_state.preds_hist[run_id].copy()
                cols_to_plot = [target, f"{target}_prediction"]

            if param_name not in ("<select>", "All predictions"):
                pred_int_cols = [
                    c
                    for c in preds.columns
                    if c.startswith("prediction_") and "_percentile_" in c
                ]
                if len(pred_int_cols) == 2:
                    pred_int = st.checkbox("Show prediction intervals")
                    if pred_int:
                        pred_int_cols = [
                            c
                            for c in preds.columns
                            if c.startswith("prediction_") and "_percentile_" in c
                        ]
                        cols_to_plot += pred_int_cols

            agg_granularities = ["<select>", "Total", "Group", "Series"]
            agg_granularity = st.selectbox(
                f"Select aggregation granularity:",
                agg_granularities,
                index=0,
                key="ragg_param_selectbox",
            )

            if agg_granularity == "<select>":
                st.stop()

            elif agg_granularity == "Total":
                # st.write("Aggregated actuals and predictions:")
                plot_agg_func = st.selectbox(
                    "Aggregation:",
                    ["<select>", "sum", "mean"],
                    index=1,
                    key="plot_agg_func_selectbox",
                )
                if plot_agg_func != "<select>":
                    with col2:
                        au.plot_predictions_agg_overall(
                            preds, date_col, cols_to_plot, plot_agg_func
                        )

            elif agg_granularity == "Group":
                # st.write("Group aggregation")
                cols_all = preds.select_dtypes(include="object").columns
                group_cols = sorted([c for c in cols_all if c not in cols_to_exclude])
                group_col = st.selectbox(
                    "Select a group:",
                    ["<select>"] + group_cols,
                    index=0,
                    key="group_selectbox",
                )
                if group_col != "<select>":
                    group_vals = sorted(preds[group_col].unique())
                    group_val = st.selectbox(
                        f'Select "{group_col}" value:',
                        ["<select>"] + group_vals,
                        index=0,
                        key="group_val_selectbox",
                    )
                    if group_val != "<select>":
                        plot_agg_gr_func = st.selectbox(
                            "Aggregation:",
                            ["<select>", "sum", "mean"],
                            index=1,
                            key="plot_agg_func_gr_selectbox",
                        )
                        if plot_agg_gr_func != "<select>":
                            with col2:
                                au.plot_predictions_agg_group(
                                    preds,
                                    date_col,
                                    group_col,
                                    group_val,
                                    cols_to_plot,
                                    plot_agg_gr_func,
                                )

            elif agg_granularity == "Series":
                # st.write("Single series")
                sids = sorted(preds[series_id].unique())
                sid = st.selectbox(
                    "Select a series:",
                    ["<select>"] + sids,
                    index=0,
                    key="sid_selectbox",
                )
                if sid != "<select>":
                    with col2:
                        au.plot_predictions_series(
                            preds, date_col, series_id, sid, cols_to_plot
                        )

        st.write("---")

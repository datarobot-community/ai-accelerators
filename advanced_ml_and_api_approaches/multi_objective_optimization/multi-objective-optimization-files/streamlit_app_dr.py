import gettext
import os
from textwrap import dedent
import warnings

from PIL import Image
from drops import get_deployment_infos, get_prediction
import numexpr
import optuna
import optunahub
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

if not os.getenv("SCRIPT_NAME"):
    from dotenv import load_dotenv

    load_dotenv("../test.env", override=True)
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Multi Objective Optimization App",
    page_icon=":material/instant_mix:",
    layout="wide",
)

# Initialize session state for language
if "language" not in st.session_state:
    st.session_state.language = "en"
if "deployment_infos" not in st.session_state:
    st.session_state.deployment_infos = []
if "trials_num" not in st.session_state:
    st.session_state.trials_num = 100
if "config" not in st.session_state:
    if os.path.isfile("config.csv"):
        st.session_state.config = pd.read_csv("config.csv")
    else:
        st.warning("Please upload config.csv")
        st.stop()
if "df_feature" not in st.session_state:
    st.session_state.df_feature = pd.read_csv("feature.csv")

# Language selection in sidebar
sidebar = st.sidebar
language = sidebar.radio(
    "Select your language",
    ["en", "ja"],
    index=["en", "ja"].index(st.session_state.language),
    key="language",
    horizontal=True,
)

# Load translations
translator = gettext.translation(
    "base", localedir="locales", languages=[st.session_state.language]
)
translator.install()

# Alias for translations
_ = translator.gettext


DATAROBOT_API_TOKEN = os.getenv("DATAROBOT_API_TOKEN")
DATAROBOT_ENDPOINT = os.getenv("DATAROBOT_ENDPOINT")


deploy_ids = st.session_state.config["Deployment ID"].to_list()

st.session_state.deployment_infos = get_deployment_infos(
    deploy_ids, dr_token=DATAROBOT_API_TOKEN, dr_url=DATAROBOT_ENDPOINT
)

API_URL = st.session_state.deployment_infos[0]["api_url"]
API_URL = API_URL + "/predApi/v1.0/deployments/{deployment_id}/predictions"
DATAROBOT_KEY = st.session_state.deployment_infos[0]["datarobot_key"]

st.session_state.trials_num = sidebar.number_input(
    _("Trials Number"), step=10, format="%d", value=100, key=10002
)

# Sampler selection
SAMPLER_OPTIONS = {
    "NSGAII + TPE Warmup": {
        "description_en": "NSGA-II with TPE warmup for efficient initial exploration",
        "description_ja": "TPEウォームアップによる効率的な初期探索 + NSGA-II",
        "type": "optunahub",
        "package": "samplers/nsgaii_with_tpe_warmup",
    },
    "NSGA-II": {
        "description_en": "Standard NSGA-II genetic algorithm for multi-objective optimization",
        "description_ja": "標準的なNSGA-II遺伝的アルゴリズム",
        "type": "builtin",
        "class": "NSGAIISampler",
    },
    "NSGA-III": {
        "description_en": "NSGA-III for many-objective optimization (3+ objectives)",
        "description_ja": "多数目的最適化向けNSGA-III（3目的以上に推奨）",
        "type": "builtin",
        "class": "NSGAIIISampler",
    },
    "TPE": {
        "description_en": "Tree-structured Parzen Estimator (Bayesian optimization)",
        "description_ja": "TPE（ベイズ最適化ベース）",
        "type": "builtin",
        "class": "TPESampler",
    },
    "Random": {
        "description_en": "Random sampling (baseline)",
        "description_ja": "ランダムサンプリング（ベースライン）",
        "type": "builtin",
        "class": "RandomSampler",
    },
    "QMC": {
        "description_en": "Quasi-Monte Carlo for better space coverage",
        "description_ja": "準モンテカルロ法（探索空間の効率的カバー）",
        "type": "builtin",
        "class": "QMCSampler",
    },
}

sampler_names = list(SAMPLER_OPTIONS.keys())
if "sampler_name" not in st.session_state:
    st.session_state.sampler_name = sampler_names[0]

selected_sampler = sidebar.selectbox(
    _("Optimization Algorithm"),
    sampler_names,
    index=sampler_names.index(st.session_state.sampler_name),
    key="sampler_select",
)
st.session_state.sampler_name = selected_sampler

# Show sampler description
sampler_info = SAMPLER_OPTIONS[selected_sampler]
desc_key = "description_ja" if st.session_state.language == "ja" else "description_en"
sidebar.caption(f"ℹ️ {sampler_info[desc_key]}")

# put directions into deployment_infos as initial value
for idx, deploy_info in enumerate(st.session_state.deployment_infos):
    deploy_info["direction"] = st.session_state.config["Optimization Direction"].iloc[
        idx
    ]

# Display radio buttons for each deployment info in sidebar
for idx, deploy_info in enumerate(st.session_state.deployment_infos):
    direction = sidebar.radio(
        deploy_info["label"],
        ["maximize", "minimize", "custom"],
        index=["maximize", "minimize"].index(deploy_info["direction"]),
        horizontal=True,
        key=f"direction_{idx}",
    )
    if direction == "custom":
        custom_value = sidebar.text_input(
            _("no_label"),
            value="abs(x - 10)",
            key=f"custom_direction_{idx}",
            label_visibility="collapsed",
        )

        try:
            # Evaluate with dummy value
            x = 100
            numexpr.evaluate(custom_value)
            st.session_state.deployment_infos[idx]["custom_exp"] = custom_value
        except Exception as e:
            st.sidebar.warning(f"Invalid expression: {str(e)}")
            st.session_state.deployment_infos[idx]["custom_exp"] = ""

    # Weight input for each objective (no min/max restriction)
    weight = sidebar.number_input(
        _("Weight"),
        value=1.0,
        step=0.1,
        format="%.2f",
        key=f"weight_{idx}",
    )
    st.session_state.deployment_infos[idx]["weight"] = weight
    st.session_state.deployment_infos[idx]["direction"] = direction

sidebar.markdown("---")
# Show numpy expression example if any direction is custom
if any(
    deploy_info["direction"] == "custom"
    for deploy_info in st.session_state.deployment_infos
):
    sidebar.markdown(f"### {_('Custom Direction Example:')}")
    sidebar.write(
        dedent(
            f"""
[numexpr](https://numexpr.readthedocs.io/en/latest/user_guide.html#supported-operators)
 {_("for support operators.")}\n
- {_("The custom expression will be **minized**.")}\n
- {_("**Don't change the variable name `x`.**")}\n
"""
        )
    )
    sidebar.code(
        dedent(
            f"""
# {_("make x close to 10")}
abs(x - 10)
# {_("penalize x > 5 and reward smaller x")}
x + (x > 5) * 1000 * log(abs(x) + 1)
# {_("keep x between 5 and 15")}
where((x >= 5) & (x <= 15), 0, where(x < 5, 5 - x, x - 15))
    """
        )
    )


simulate = sidebar.button(_("Simulation Start!"), key="simulate_start")


def get_sampler(sampler_name: str):
    """Create and return the selected sampler instance."""
    sampler_config = SAMPLER_OPTIONS[sampler_name]

    if sampler_config["type"] == "optunahub":
        package_name = sampler_config["package"]
        return optunahub.load_module(package=package_name).NSGAIIWithTPEWarmupSampler()
    else:
        # Built-in Optuna samplers
        sampler_class = sampler_config["class"]
        if sampler_class == "NSGAIISampler":
            return optuna.samplers.NSGAIISampler()
        elif sampler_class == "NSGAIIISampler":
            return optuna.samplers.NSGAIIISampler()
        elif sampler_class == "TPESampler":
            return optuna.samplers.TPESampler()
        elif sampler_class == "RandomSampler":
            return optuna.samplers.RandomSampler()
        elif sampler_class == "QMCSampler":
            return optuna.samplers.QMCSampler()
        else:
            raise ValueError(f"Unknown sampler: {sampler_class}")


def run_optimization(
    trials_num,
    targets,
    deploy_ids,
    directions,
    custom_exprs,
    weights,
    feats_name,
    feats_value_min,
    feats_value_max,
    sampler_name,
    simulated_feats,
):
    def objective(trial):
        df_target = pd.DataFrame(index=[0], columns=feats_name)
        for i, col in enumerate(feats_name):
            low = feats_value_min[i]
            high = feats_value_max[i]
            df_target[col] = trial.suggest_float(col, low, high, step=0.01)

        if not 2 <= len(deploy_ids) <= 30:
            raise ValueError("Number of deployment IDs must be between 2 and 30")

        predictions = []
        for n, (deploy_id, custom_exp, weight) in enumerate(
            zip(deploy_ids, custom_exprs, weights)
        ):
            pred = get_prediction(
                df_target, deploy_id, DATAROBOT_API_TOKEN, DATAROBOT_KEY, API_URL
            )
            trial.set_user_attr(targets[n], pred)
            if custom_exp:
                # since the variable in the expression is x, we need to assign the value to x
                expr = custom_exp.replace("x", "pred")
                pred = numexpr.evaluate(expr)
            # Apply weight to the prediction for optimization
            weighted_pred = pred * weight
            predictions.append(weighted_pred)

        return tuple(predictions)

    sampler = get_sampler(sampler_name)

    study = optuna.create_study(
        sampler=sampler,
        # storage="sqlite:///optuna_study.db",
        directions=directions,
        # load_if_exists=True,
    )

    study.optimize(
        objective,
        n_trials=trials_num,
        timeout=300,
        gc_after_trial=True,
        n_jobs=3,  # Reduced from 10 to avoid API rate limiting
    )

    trial_all = []
    trail_pred = []
    trial_params = []
    for trial in study.get_trials():
        # Skip failed trials (where values is None)
        if trial.values is None:
            continue
        trial_params.append(trial.params)
        trail_pred.append([v for v in trial.user_attrs.values()])
        trial_all.append([trial.number] + [v for v in trial.values])
    trial_all = pd.DataFrame(
        trial_all, columns=["Iteration"] + [f"{t}_opt" for t in targets]
    )
    trail_pred = pd.DataFrame(trail_pred, columns=targets)
    trial_params = pd.DataFrame.from_dict(trial_params)
    trial_all = pd.concat([trial_all, trail_pred, trial_params], axis=1)

    trial_pareto = []
    pareto_params = []
    for trial in study.best_trials:
        trial_pareto.append([trial.number] + [v for v in trial.values])
        pareto_params.append(trial.params)
    trial_pareto = pd.DataFrame(trial_pareto, columns=["Iteration"] + targets)
    pareto_params_df = pd.DataFrame.from_dict(pareto_params)

    # Calculate reliability statistics for Pareto optimal solutions
    # Only include simulated features (exclude fixed/dropped features)
    param_cols = [col for col in simulated_feats if col in pareto_params_df.columns]
    reliability_stats = calculate_reliability_stats(pareto_params_df, param_cols)

    return trial_all, trial_pareto, study, reliability_stats


def calculate_reliability_stats(pareto_params_df: pd.DataFrame, param_cols: list) -> pd.DataFrame:
    """
    Calculate reliability statistics for Pareto optimal parameters.

    Returns DataFrame with:
    - Mean: Average value across Pareto solutions
    - Std: Standard deviation
    - CV: Coefficient of Variation (Std/Mean) - lower is more reliable
    - CI_lower: 95% confidence interval lower bound
    - CI_upper: 95% confidence interval upper bound
    - Range: Max - Min value
    - Stability_Score: 1 - normalized CV (0-1, higher is more stable)
    """
    import numpy as np
    from scipy import stats as scipy_stats

    if len(pareto_params_df) < 2:
        # Not enough data for statistics
        stats_data = []
        for col in param_cols:
            if col in pareto_params_df.columns:
                val = pareto_params_df[col].iloc[0] if len(pareto_params_df) > 0 else np.nan
                stats_data.append({
                    "Parameter": col,
                    "Mean": val,
                    "Std": 0.0,
                    "CV": 0.0,
                    "CI_lower": val,
                    "CI_upper": val,
                    "Min": val,
                    "Max": val,
                    "Range": 0.0,
                    "Stability_Score": 1.0,
                })
        return pd.DataFrame(stats_data)

    stats_data = []
    cv_values = []

    for col in param_cols:
        if col not in pareto_params_df.columns:
            continue

        values = pareto_params_df[col].dropna()
        if len(values) == 0:
            continue

        mean_val = values.mean()
        std_val = values.std()
        min_val = values.min()
        max_val = values.max()
        range_val = max_val - min_val

        # Coefficient of Variation (handle zero mean)
        cv = std_val / abs(mean_val) if mean_val != 0 else 0.0
        cv_values.append(cv)

        # 95% Confidence Interval
        n = len(values)
        if n > 1:
            se = std_val / np.sqrt(n)
            t_val = scipy_stats.t.ppf(0.975, n - 1)
            ci_lower = mean_val - t_val * se
            ci_upper = mean_val + t_val * se
        else:
            ci_lower = ci_upper = mean_val

        stats_data.append({
            "Parameter": col,
            "Mean": mean_val,
            "Std": std_val,
            "CV": cv,
            "CI_lower": ci_lower,
            "CI_upper": ci_upper,
            "Min": min_val,
            "Max": max_val,
            "Range": range_val,
            "Stability_Score": 0.0,  # Will be calculated after
        })

    # Calculate Stability Score (normalized CV, inverted so higher = more stable)
    if cv_values and max(cv_values) > 0:
        max_cv = max(cv_values)
        for stat in stats_data:
            stat["Stability_Score"] = round(1.0 - (stat["CV"] / max_cv), 4)
    else:
        for stat in stats_data:
            stat["Stability_Score"] = 1.0

    return pd.DataFrame(stats_data)


# ======================================== Start Streamlit ========================================#
st.title(_("Multi Objective Optimization App"))

# ======================================== image ========================================#
# image
logo = Image.open("dr.png")
st.image(logo, width=200)

# ======================================== tabs ========================================#
tab1, tab2 = st.tabs([_("Simulation"), _("Visualization")])

with tab1:
    if not os.path.isfile("config.csv"):
        st.warning(_("Please upload config.csv"))
        st.stop()
    df_feature = st.session_state.df_feature.copy()
    targets = [
        deploy_info["label"] for deploy_info in st.session_state.deployment_infos
    ]
    deploy_ids = [
        deploy_info["deployment_id"]
        for deploy_info in st.session_state.deployment_infos
    ]
    ids = ["ID"]
    directions = [
        deploy_info["direction"] for deploy_info in st.session_state.deployment_infos
    ]
    # replace custom with minimize
    directions = ["minimize" if d == "custom" else d for d in directions]
    custom_exprs = [
        deploy_info.get("custom_exp", "")
        for deploy_info in st.session_state.deployment_infos
    ]
    weights = [
        deploy_info.get("weight", 1.0)
        for deploy_info in st.session_state.deployment_infos
    ]
    cols = df_feature.columns.to_list()
    feats = [f for f in cols if f not in targets if f not in ids]

    feats_name = st.multiselect(
        _("Select features to be simulated"), feats, feats, key=1002
    )

    st.markdown(
        f"<h1 style='text-align: center; color: grey;'>{_('Simulated Features')}</h1>",
        unsafe_allow_html=True,
    )
    feats_value_min = []
    feats_value_max = []
    for i in range(len(feats_name)):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(feats_name[i])
        with col2:
            feat_value_min = st.number_input(
                "min",
                step=0.01,
                format="%0.2f",
                value=df_feature[feats_name[i]].values.min(),
                key=i + 400,
            )
            feats_value_min.append(feat_value_min)
        with col3:
            feat_value_max = st.number_input(
                "max",
                step=0.01,
                format="%0.2f",
                value=df_feature[feats_name[i]].values.max(),
                key=i + 500,
            )
            feats_value_max.append(feat_value_max)

    st.markdown(
        f"<h1 style='text-align: center; color: grey;'>{_('Dropped Features')}</h1>",
        unsafe_allow_html=True,
    )

    feats_dropped = [f for f in feats if f not in feats_name]
    feats_value_mean = []
    if len(feats_dropped) == 0:
        st.info(_("No features with fixed values."))
    for i in range(len(feats_dropped)):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(feats_dropped[i])
        with col2:
            feat_value_mean = st.number_input(
                "mean",
                step=0.01,
                format="%0.2f",
                value=df_feature[feats_dropped[i]].values.mean(),
                key=i + 600,
            )
            feats_value_mean.append(feat_value_mean)
    if simulate:
        with col2:
            trial_all, trial_pareto, study, reliability_stats = run_optimization(
                st.session_state.trials_num,
                targets,
                deploy_ids,
                directions,
                custom_exprs,
                weights,
                feats_name + feats_dropped,
                feats_value_min + feats_value_mean,
                feats_value_max + feats_value_mean,
                st.session_state.sampler_name,
                feats_name,  # Only simulated features for reliability stats
            )
            trial_pareto["best_trial"] = 1
            trial_all = trial_all.merge(
                trial_pareto[["Iteration", "best_trial"]],
                on=["Iteration"],
                how="left",
            )
            trial_all = trial_all.fillna(0)
            trial_all.to_csv("trial_all.csv", index=False)
            trial_pareto.to_csv("trial_pareto.csv", index=False)
            reliability_stats.to_csv("reliability_stats.csv", index=False)

            # display the message
            sidebar.write(_("Simulation Finished!"))
            sidebar.info(_("Please go to the Visualization tab to see the results."))
        reference_point = trial_all[targets].iloc[0].values
        fig = optuna.visualization.plot_hypervolume_history(
            study, reference_point=reference_point
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    if os.path.isfile("trial_all.csv"):
        trial_all = pd.read_csv("trial_all.csv")
        trial_pareto = pd.read_csv("trial_pareto.csv").sort_values(targets[0])

        trial_all["color"] = "blue"
        trial_all.loc[trial_all["best_trial"] == 1, "color"] = "red"
        trial_all["size"] = 2
        trial_all.loc[trial_all["best_trial"] == 1, "size"] = 5

        target_map = {f"{t}_opt": t for t in targets}
        target_map_rev = {t: f"{t}_opt" for t in targets}

        x_axis = st.selectbox(_("Select X-axis"), ["Iteration"] + feats, key="x_axis")
        for t in targets:
            fig = px.scatter(
                trial_all,
                x=x_axis,
                y=t,
                color="color",
                color_discrete_map={"blue": "blue", "red": "red"},
                size="size",
                size_max=15,
                symbol="color",
                symbol_map={"blue": "circle", "red": "circle"},
                opacity=0.7,
            )
            fig.update_layout(
                title=t + _(" Scatter Plot"),
                xaxis_title=x_axis,
                yaxis_title=t,
            )

            st.plotly_chart(fig, use_container_width=True)

        # 2d
        target_name = st.multiselect(
            _("Select Two Targets"), targets, targets[:2], key=1003
        )
        if len(target_name) != 2:
            st.error(_("Please select two targets!"))
        else:
            trial_pareto = pd.read_csv("trial_pareto.csv").sort_values(target_name[0])
            target_disp = [f"{t}_opt" for t in target_name]
            fig1 = px.line(trial_pareto, x=target_name[0], y=target_name[1])
            fig1.update_traces(line=dict(color="red"))

            fig2 = px.scatter(
                trial_all,
                x=target_disp[0],
                y=target_disp[1],
                color="color",
                color_discrete_map={"blue": "blue", "red": "red"},
                size="size",
                size_max=15,
                symbol="color",
                symbol_map={"blue": "circle", "red": "circle"},
                opacity=0.7,
            )

            fig = go.Figure(data=fig1.data + fig2.data)
            fig.update_layout(
                title=f"{_('Pareto Curve')}(2D)",
                xaxis_title=target_disp[0],
                yaxis_title=target_disp[1],
            )
            st.plotly_chart(fig, use_container_width=True)

        # 3d
        target_name = st.multiselect(
            _("Select Three Targets"), targets, targets, key=1004
        )
        if len(target_name) != 3:
            st.error(_("Please select three targets!"))
        else:
            target_disp = [f"{t}_opt" for t in target_name]

            fig1 = px.line_3d(
                trial_pareto, x=target_name[0], y=target_name[1], z=target_name[2]
            )
            fig1.update_traces(line=dict(color="red"))
            fig2 = px.scatter_3d(
                trial_all,
                x=target_disp[0],
                y=target_disp[1],
                z=target_disp[2],
                color="color",
                color_discrete_map={"blue": "blue", "red": "red"},
            )

            fig = go.Figure(data=fig1.data + fig2.data)
            fig.update_layout(
                title=f"{_('Pareto Curve')}(3D)",
                scene=dict(
                    xaxis_title=target_disp[0],
                    yaxis_title=target_disp[1],
                    zaxis_title=target_disp[2],
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

        trial_all_sort = trial_all.sort_values(
            ["best_trial"], ascending=False
        ).reset_index(drop=True)
        trial_all_sort.drop(columns=["color", "size"], inplace=True)
        st.dataframe(trial_all_sort)
        data_as_csv = trial_all_sort.to_csv(index=False).encode("utf-8")
        st.download_button(
            _("Download data as CSV"),
            data_as_csv,
            f"{_('optimization_result')}.csv",
            "text/csv",
            key="download-tools-csv",
        )

        # Display reliability statistics
        if os.path.isfile("reliability_stats.csv"):
            st.markdown("---")
            st.markdown(f"### {_('Parameter Reliability Statistics')}")
            st.caption(_("Shows how consistently each parameter appears in Pareto optimal solutions"))

            reliability_stats = pd.read_csv("reliability_stats.csv")

            # Display statistics table
            st.dataframe(
                reliability_stats.style.format({
                    "Mean": "{:.4f}",
                    "Std": "{:.4f}",
                    "CV": "{:.4f}",
                    "CI_lower": "{:.4f}",
                    "CI_upper": "{:.4f}",
                    "Min": "{:.4f}",
                    "Max": "{:.4f}",
                    "Range": "{:.4f}",
                    "Stability_Score": "{:.4f}",
                }),
                use_container_width=True,
            )

            # Stability Score bar chart
            if len(reliability_stats) > 0:
                fig_stability = px.bar(
                    reliability_stats,
                    x="Parameter",
                    y="Stability_Score",
                    title=_("Parameter Stability Score (higher = more consistent)"),
                    color="Stability_Score",
                    color_continuous_scale="RdYlGn",
                    range_color=[0, 1],
                )
                fig_stability.update_layout(
                    xaxis_title=_("Parameter"),
                    yaxis_title=_("Stability Score"),
                    yaxis_range=[0, 1.1],
                )
                st.plotly_chart(fig_stability, use_container_width=True)

            # Download button for reliability stats
            reliability_csv = reliability_stats.to_csv(index=False).encode("utf-8")
            st.download_button(
                _("Download Reliability Statistics as CSV"),
                reliability_csv,
                "reliability_stats.csv",
                "text/csv",
                key="download-reliability-csv",
            )

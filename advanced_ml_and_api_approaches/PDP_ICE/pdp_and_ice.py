from io import StringIO
import os
import random as rd
import re
import sys

import datarobot as dr
import numpy as np
import pandas as pd
import plotly.colors as colors
import plotly.express as px
import plotly.graph_objects as go
import requests

API_KEY = ""
ENDPOINT = "https://app.datarobot.com/api/v2"
DATAROBOT_KEY = ""

DEFAULT_HOVER_LABEL = dict(bgcolor="white", font_size=16, font_family="Rockwell", namelength=-1)


def get_column_name_mappings(project_id) -> list:
    """
    Returns a dictionary of column name mappings based on the project type.

    Returns:
        dict: A dictionary containing the column name mappings.
    """
    project = dr.Project.get(project_id)
    project_type = project.target_type
    positive_class = project.positive_class
    target = project.target

    if project_type == "Regression":
        name_mappings = [
            "prediction",
            f"{target}_PREDICTION",
        ]
    else:
        name_mappings = [
            # f"{target}_{positive_class}_PREDICTION",
            # f"class_{positive_class}",
            f"class_1.0",
        ]
    return name_mappings


def get_batch_predictions(df, deployment_id):
    job = dr.BatchPredictionJob.score(
        deployment_id,
        intake_settings={
            "type": "localFile",
            "file": df,
        },
        output_settings={
            "type": "localFile",
            "path": "./predicted.csv",
        },
        max_explanations=0,
    )

    preds = job.get_result_when_complete()
    s = str(preds, "utf-8")
    s = StringIO(s)
    return pd.read_csv(s)


def get_realtime_predictions(df, deployment_id):
    deployment = dr.Deployment.get(deployment_id)
    project = dr.Project.get(deployment.model["project_id"])

    data = df.to_json(orient="records")

    API_URL = "https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions"
    url = API_URL.format(deployment_id=deployment_id)

    headers = {
        "Authorization": "Bearer {}".format(API_KEY),
        "Content-Type": "application/json; charset=UTF-8",
        "DataRobot-Key": DATAROBOT_KEY,
    }
    params = None  # {"maxExplanations": 10}
    response = requests.post(url, data=data, headers=headers, params=params)

    try:
        scores = pd.json_normalize(response.json()["data"])
        preds = extract_prediction_values(scores, project)
        return preds
    except Exception as e:
        raise f"Prediction request failed {e}"


def get_predicted_label(row):
    try:
        return row[0]["value"]
    except:
        print(row[0])


def extract_prediction_values(df: pd.DataFrame, project) -> pd.DataFrame:
    return (df.assign(value=lambda x: x.predictionValues.apply(get_predicted_label)))[
        ["rowId", "prediction", "value"]
    ].rename(columns={"rowId": "row_id", "value": list(get_column_name_mappings(project.id))[0]})


class PartialDependencePlot:
    """
    A class to calculate 1 or 2-way Partial Dependence Plots (PDP) for DataRobot models.

    Attributes:
    -----------
    df: pd.DataFrame
        Input data frame.
    model: DataRobot Model Object
        The model for which PDP is to be computed.
    project: DataRobot Project Object
        The DataRobot project associated with the model.
    weights: str or None
        The name of the column containing the sample weights.
    sample: int
        Total number of rows to sample.
    k: int
        Total number of values to sample per row.
    colors: list
        List of colors for the PDP plots.
    opacities: list
        List of opacities for the PDP plots.
    features: list
        List of features used in the model.
    scores: pd.DataFrame
        Dataframe containing scores.
    deployment_id: str or None
        DataRobot deployment ID.

    Methods:
    --------
    _create_scoring_data:
        Create a synthetic scoring dataset.
    _score_data:
        Score data using DataRobot API.
    create_and_score_data:
        Create synthetic data and score it using DataRobot API.
    get_features:
        Get informative features from DataRobot project.
    get_feature_impact:
        Get feature impact scores from the DataRobot model.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        model: dr.models.model.Model,
        weight_col: str = None,
        sample: int = 1000,
        k: int = 10,
        deployment_id: str = None,
    ):
        self.df = df
        self.model = model
        self.project = dr.Project.get(self.model.project_id)
        self.positive_class = self.project.positive_class
        self.target = self.project.target
        self.weights = weight_col
        self.sample = sample
        self.target_type = self.project.target_type
        self.k = k
        self.colors = [
            "#1f77b4",  # muted blue
            "#2ca02c",  # cooked asparagus green
            "#d62728",  # brick red
            "#ff7f0e",  # safety orange
            "#9467bd",  # muted purple
            "#8c564b",  # chestnut brown
            "#e377c2",  # raspberry yogurt pink
            "#7f7f7f",  # middle gray
            "#bcbd22",  # curry yellow-green
            "#17becf",  # blue-teal
            "#ff7f0e",  # safety orange
        ]
        self.opacities = [
            "rgba(31, 119, 180, 0.1)",
            "rgba(44, 160, 44, 0.1)",
            "rgba(214, 39, 40, 0.1)",
            "rgba(255, 127, 14, 0.1)",
            "rgba(148, 103, 189, 0.1)",
            "rgba(140, 86, 75, 0.1)",
            "rgba(227, 119, 194, 0.1)",
            "rgba(127, 127, 127, 0.1)",
            "rgba(188, 189, 34, 0.1)",
            "rgba(23, 190, 207, 0.1)",
        ]
        self.features = []
        self.scores = pd.DataFrame()
        self.deployment_id = deployment_id

    def _create_scoring_data(
        self,
        df: pd.DataFrame,
        feature_1: str,
    ):
        """
        Create a synthetic scoring dataset

        Returns:
        --------
        pd.DataFrame
            The synthetic scoring dataset.
        """
        scoring_data = pd.DataFrame()
        sampled_rows = df.sample(n=min(self.df.shape[0], self.sample), replace=False)

        # find unique values
        unique_values = df[feature_1].unique()
        size = min(len(unique_values), self.k)

        # grab the top k most common values
        levels = df[feature_1].value_counts().iloc[0:size].index.values

        # create a copy for each unique value
        for l in levels:
            temp = sampled_rows.copy()
            temp[feature_1] = l
            temp["feature"] = feature_1
            scoring_data = scoring_data.append(temp)

        return scoring_data.reset_index()

    def _score_data(
        self,
        df: pd.DataFrame,
        deployment_id: str,
    ):
        """
        Send pandas df to DataRobot v2 API and return scores merged back with actuals

        Returns:
        --------
        pd.DataFrame
            The dataframe containing scores and actuals.
        """
        if deployment_id is not None:
            # batch predictions
            preds = get_batch_predictions(df, deployment_id)
            self.col = list(get_column_name_mappings(self.project.id))[0]

        else:
            dataset = self.project.upload_dataset(df)
            pred_job = self.model.request_predictions(dataset.id)
            preds = pred_job.get_result_when_complete(max_wait=3600)
            self.col = list(get_column_name_mappings(self.project.id))[0]

        preds = preds.merge(
            df.reset_index(drop=True),
            how="inner",
            left_index=True,
            right_index=True,
            validate="one_to_one",
        )

        return preds

    def create_and_score_data(
        self,
        df: pd.DataFrame,
        feature_1: str,
        deployment_id: str,
    ):
        scoring_data = self._create_scoring_data(df, feature_1)
        preds = self._score_data(scoring_data, deployment_id)
        preds.sort_values(by=feature_1, inplace=True)

        return preds

    def get_feature_impact(self, n=None):
        """
        Get feature impact scores from the DataRobot model.

        Parameters:
        -----------
        n: int, optional
            Number of top features to return. If not provided, all features will be returned.

        Returns:
        --------
        list
            A list of tuples containing feature names and their impact scores.
        """
        try:
            feature_impact = [
                (f["featureName"], round(f["impactUnnormalized"], 2))
                for f in self.model.get_or_request_feature_impact()
            ]

            if n is None:
                n = len(feature_impact)

            return feature_impact[0:n]
        except:
            try:
                # Create a SHAP impact job for the project and model
                shap_impact_job = dr.ShapImpact.create(
                    project_id=self.project.id, model_id=self.model.id
                )
                shap_impact = shap_impact_job.get_result_when_complete()
            except:
                # Retrieve SHAP impact if it already exists
                shap_impact = dr.ShapImpact.get(project_id=self.project.id, model_id=self.model.id)
            return shap_impact

    def create_pdp_plot(
        self,
        feature_1,
        feature_2=None,
        max_bins=3,
        quantiles=False,
        normalize=False,
        include_ice=True,
        n=200,
        error_bars=False,
        height=500,
        tickangle: int = 0,
        showlegend=True,
    ):
        """
        Generate 1 or 2-way PDP plots

        Attributes:
        -----------

        feature_1: str
            Primary feature to be plotted on x-axis
        feature_2: (Optional) str
            Secondary feature used to segment the primary feature
        max_bins: int
            Maximum number of bins used to segment the secondary feature
        quantiles: boolean
            Set to True to segment the secondary feature using pd.qcut versus pd.cut
        normalize: boolean
            Re-index each PDP curve so they all start at the same value
        include_ice:
            Whether to plot ICE curves
        n: int
            Number of ICE curves to plot

        """
        assert isinstance(max_bins, int), "max_bins must be an integer"
        assert 1 < max_bins <= 10, "max_bins must be greater than 1 and less than or equal to 10"
        tickformat = ",.0" if self.project.target_type == "Regression" else ",.0%"
        two_way_pdp = pd.DataFrame()

        # Don't re-score rows if we don't need to
        if feature_1 in self.features:
            preds = self.scores.loc[self.scores["feature"] == feature_1, :].copy()

        else:
            # Create scoring dataset and make predictions
            preds = self.create_and_score_data(self.df, feature_1, self.deployment_id)

            # Keep track of the features already scored
            self.scores = self.scores.append(preds)
            self.features.append(feature_1)

        n = min(n, preds.shape[0])
        title = ""
        legend_title = ""
        col = self.col

        # Calculate one-way Partial Depedence
        if self.weights:
            w_mean = lambda x: np.average(x, weights=preds.loc[x.index, self.weights])
            w_std = lambda x: np.sqrt(np.cov(x, aweights=preds.loc[x.index, self.weights]))

            one_way_pdp = (
                preds.groupby(feature_1)
                .agg(
                    mean=(col, w_mean),
                    std=(col, w_std),
                    count=(self.weights, "sum"),
                )
                .reset_index()
                .sort_values(by=feature_1, ascending=True)
            )
        else:
            one_way_pdp = (
                preds.groupby(feature_1)[col]
                .agg(["mean", "std", "count"])
                .reset_index()
                .sort_values(by=feature_1, ascending=True)
            )

        # Calculate two-way Partial Depedence
        if feature_2:
            two_way_pdp = preds.copy()

            if feature_2 in self.df.select_dtypes(include=["number", "bool"]).columns:
                if quantiles:
                    two_way_pdp[feature_2] = pd.qcut(
                        two_way_pdp[feature_2],
                        max_bins,
                        duplicates="drop",
                    )
                else:
                    two_way_pdp[feature_2] = pd.cut(
                        two_way_pdp[feature_2],
                        max_bins,
                        duplicates="drop",
                    )

            elif feature_2 in self.df.select_dtypes(include=["object"]).columns:
                unique_values = len(two_way_pdp[feature_2].unique())
                if unique_values > max_bins:
                    top_bins = two_way_pdp[feature_2].value_counts()[0 : max_bins - 1].index.values
                    other_bin = two_way_pdp.loc[
                        ~two_way_pdp[feature_2].isin(top_bins), feature_2
                    ].unique()
                    two_way_pdp[feature_2] = [
                        "OTHER" if i in other_bin else i for i in two_way_pdp[feature_2]
                    ]
                else:
                    pass

            else:
                raise ValueError(
                    "feature_2 has to be either Numeric, Boolean, Categorical, Length, Percentage, or Currency"
                )

            if self.weights:
                w_mean = lambda x: np.average(x, weights=two_way_pdp.loc[x.index, self.weights])
                w_std = lambda x: np.sqrt(
                    np.cov(x, aweights=two_way_pdp.loc[x.index, self.weights])
                )

                two_way_pdp = (
                    two_way_pdp.groupby([feature_1, feature_2])
                    .agg(mean=(col, w_mean), std=(col, w_std), count=(self.weights, "sum"))
                    .reset_index()
                    .sort_values(by=feature_1, ascending=True)
                )
            else:
                two_way_pdp = (
                    two_way_pdp.groupby([feature_1, feature_2])[col]
                    .agg(["mean", "std", "count"])
                    .reset_index()
                    .sort_values(by=feature_1, ascending=True)
                )

        # Normalize scores
        if normalize:
            title = " - Normalized"
            preds[col] = preds[col] - preds.groupby("index")[col].transform("first")
            one_way_pdp["mean"] = one_way_pdp["mean"] - one_way_pdp["mean"][0]

            if feature_2:
                two_way_pdp["mean"] = two_way_pdp["mean"] - two_way_pdp.groupby(feature_2)[
                    "mean"
                ].transform("first")

        # Create plots
        fig = go.Figure()
        ice_curves = pd.DataFrame()
        if include_ice & (feature_2 is None):
            ice_curves = preds["index"].unique()[0:n]
            for i in ice_curves:
                t = preds.loc[preds["index"] == i, [feature_1, col]].copy()
                fig.add_trace(
                    go.Scatter(
                        x=t[feature_1],
                        y=t[col],
                        mode="lines+markers",
                        showlegend=False,
                        line=dict(
                            color="rgba(127, 127, 127, 0.25)",
                            width=0.5,
                        ),
                    )
                )

        # ICE Curves
        if include_ice & (feature_2 is not None):
            for idx, f in enumerate(two_way_pdp[feature_2].unique()):
                if isinstance(f, pd._libs.interval.Interval):
                    preds_temp = preds.loc[
                        (preds[feature_2] >= f.left) & (preds[feature_2] < f.right), :
                    ]
                else:
                    preds_temp = preds.loc[preds[feature_2] == f, :]
                ice_curves = ice_curves.append(preds_temp)

                m = min(n, preds_temp.shape[0])
                for i in preds_temp["index"].unique()[0:m]:
                    t = preds_temp.loc[preds_temp["index"] == i, [feature_1, col]].copy()
                    fig.add_trace(
                        go.Scatter(
                            x=t[feature_1],
                            y=t[col],
                            mode="lines",
                            showlegend=False,
                            line=dict(
                                color=self.colors[idx],
                                width=0.5,
                            ),
                        )
                    )

        fillcolor = None
        fill = None

        # Two-way PDP
        if feature_2:
            legend_title = feature_2
            for idx, f in enumerate(two_way_pdp[feature_2].unique()):
                temp = two_way_pdp.loc[two_way_pdp[feature_2] == f, :]

                if error_bars:
                    fillcolor = "rgba(20, 20, 20, 0.3)"
                    fill = "tonexty"
                    fig.add_trace(
                        go.Scatter(
                            name=f"Lower Bound {f}",
                            showlegend=False,
                            x=temp[feature_1],
                            y=temp["mean"] - temp["std"] / np.sqrt(temp["count"]),
                            mode="lines",
                            marker=dict(color="#444"),
                            line=dict(width=0),
                        )
                    )

                fig.add_trace(
                    go.Scatter(
                        x=temp[feature_1],
                        y=temp["mean"],
                        mode="lines+markers",
                        name=str(f),
                        marker=dict(size=6, color=self.colors[idx]),
                        line=dict(
                            color=self.colors[idx],
                            width=3,
                        ),
                        fillcolor=self.opacities[idx],
                        fill=fill,
                    )
                )

                if error_bars:
                    fig.add_trace(
                        go.Scatter(
                            name=f"Upper Bound {f}",
                            showlegend=False,
                            x=temp[feature_1],
                            y=temp["mean"] + temp["std"] / np.sqrt(temp["count"]),
                            mode="lines",
                            marker=dict(color="#444"),
                            line=dict(width=0),
                            fillcolor=self.opacities[idx],
                            fill=fill,
                        )
                    )

        else:
            fillcolor = None
            fill = None

            if error_bars:
                fillcolor = "rgba(20, 20, 20, 0.1)"
                fill = "tonexty"

                fig.add_trace(
                    go.Scatter(
                        name="Lower Bound",
                        showlegend=False,
                        x=one_way_pdp[feature_1],
                        y=one_way_pdp["mean"] - one_way_pdp["std"] / np.sqrt(one_way_pdp["count"]),
                        mode="lines",
                        line=dict(width=0),
                        marker=dict(
                            size=5,
                            color="#444",
                            line=dict(
                                width=0,
                            ),
                        ),
                    )
                )

            fig.add_trace(
                go.Scatter(
                    x=one_way_pdp[feature_1],
                    y=one_way_pdp["mean"],
                    mode="lines+markers",
                    name="Partial Dependence",
                    fillcolor=fillcolor,
                    fill=fill,
                    marker=dict(
                        size=5,
                        color="black",
                        # symbol=symbol,
                        line=dict(
                            color="black",
                            width=2,
                        ),
                    ),
                    line=dict(
                        color="black",
                        width=2,
                    ),
                )
            )

            if error_bars:
                fig.add_trace(
                    go.Scatter(
                        name="Upper Bound",
                        showlegend=False,
                        x=one_way_pdp[feature_1],
                        y=one_way_pdp["mean"] + one_way_pdp["std"] / np.sqrt(one_way_pdp["count"]),
                        mode="lines",
                        marker=dict(color="#444"),
                        line=dict(width=0),
                        fillcolor=fillcolor,
                        fill=fill,
                    )
                )

        fig.update_layout(
            height=height,
            hoverlabel=DEFAULT_HOVER_LABEL,
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=showlegend,
            legend_title=f"{legend_title}",
            legend=dict(
                bgcolor="rgba(255, 255, 255, 0)",
                bordercolor="rgba(255, 255, 255, 0)",
                x=1.1,
                y=1,
                xanchor="left",
                yanchor="top",
            ),
            font_color="black",
        )

        fig.update_xaxes(
            title=feature_1,
            showline=True,
            linewidth=1,
            linecolor="black",
            ticks="inside",
            tickwidth=1,
            tickcolor="black",
            ticklen=6,
            tickangle=tickangle,
        )
        fig.update_yaxes(
            title=self.target,
            showline=True,
            linewidth=1,
            linecolor="black",
            showgrid=True,
            gridwidth=1,
            gridcolor="lightgray",
            tickformat=tickformat,
        )

        return fig

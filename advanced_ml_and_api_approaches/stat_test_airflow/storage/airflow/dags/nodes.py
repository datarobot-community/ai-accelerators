from collections import OrderedDict
import concurrent.futures
import io
import logging
import math
from typing import Any, Dict
import warnings

from PIL import Image

# pyright: reportPrivateImportUsage=false
import datarobot as dr
from datarobot.models.feature_effect import FeatureEffects
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from packaging import version
import pandas as pd
import scipy.stats as spstat
from scipy.stats import somersd
from sklearn import metrics
import statsmodels.api as sm
from statsmodels.genmod import families
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import (
    acorr_ljungbox,
    het_arch,
    het_breuschpagan,
    normal_ad,
)
from statsmodels.stats.gof import chisquare
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.tsa.stattools import adfuller, kpss

plt.switch_backend("Agg")

log = logging.getLogger(__name__)


warnings.filterwarnings("ignore")

if version.parse(dr.__version__) < version.parse("2.29.0"):

    def get_feature_effect(model, source, backtest_index):
        params = {
            "source": source,
            "backtestIndex": backtest_index,
        }
        fe_url = model._get_feature_effect_url()
        server_data = model._client.get(fe_url, params=params).json()
        return FeatureEffects.from_server_data(server_data)

    dr.DatetimeModel.get_feature_effect = get_feature_effect  # type: ignore


def calculate_metrics(predictions_data: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
    df_predictions = predictions_data
    start_dtm = df_predictions.loc[:, parameters["datetime_column"]].min()[:10]
    end_dtm = df_predictions.loc[:, parameters["datetime_column"]].max()[:10]
    n_rows = len(df_predictions)

    actuals = df_predictions.loc[:, parameters["target_column"]]
    predictions_np = df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"]

    actual_sign = np.sign(actuals)
    predict_sign = np.sign(predictions_np)  # type: ignore

    labels = [int(x) for x in np.unique(np.concatenate([actual_sign, predict_sign]))]
    confusion_matrix = pd.DataFrame(
        metrics.confusion_matrix(actual_sign, predict_sign, labels=labels),
        index=labels,
        columns=labels,
    )
    confusion_matrix.index.name = "Actual Sign"
    confusion_matrix.columns.name = "Predicted Sign"

    # print(confusion_matrix)

    res = somersd(confusion_matrix)
    somersd_stat = res.statistic
    gAUC = (somersd_stat + 1) / 2
    accuracy = metrics.accuracy_score(actual_sign, predict_sign)
    signs_without_0 = [
        signs for signs in zip(actual_sign, predict_sign) if signs[0] != 0 and signs[1] != 0  # noqa
    ]

    hit_ratio = metrics.accuracy_score(
        np.array(signs_without_0)[:, 0], np.array(signs_without_0)[:, 1]
    )

    # variance_explained = metrics.explained_variance_score(actuals, predictions_np)
    MAE = metrics.mean_absolute_error(actuals, predictions_np)
    MSE = metrics.mean_squared_error(actuals, predictions_np)
    RMSE = metrics.mean_squared_error(actuals, predictions_np, squared=False)
    R2_Score = metrics.r2_score(actuals, predictions_np)
    # MAPE = metrics.mean_absolute_percentage_error(actuals, predictions_np)

    result = {
        "start": start_dtm,
        "end": end_dtm,
        "records": n_rows,
        "hit ratio": hit_ratio,
        "accuracy": accuracy,
        "generalized AUC": gAUC,
        "somersd_stat": res.statistic,
        "somersd_pvalue": res.pvalue,
        # "Variance_Explained": variance_explained,
        "MAE": MAE,
        "MSE": MSE,
        "RMSE": RMSE,
        # "MAPE": MAPE,
        "R2_Score": R2_Score,
    }

    return result


def rebin_lift_chart(df: pd.DataFrame, bins: int):
    """
    Rebins the lift chart data into a specified number of bins.

    This function takes a lift chart data DataFrame and the desired number of bins as input, and rebins the data by
    averaging the values within each new bin. The rebinned data is returned as a new DataFrame.

    Args:
    df (pd.DataFrame): The lift chart data as a DataFrame with columns "predicted", "actual", and "bin_weight".
    bins (int): The desired number of bins for the rebinned lift chart data.

    Returns:
    pd.DataFrame: A new DataFrame containing the rebinned lift chart data with columns
    "bin", "actual_mean", "predicted_mean", and "bin_weight".
    """

    bin_records = []
    current_prediction_total = 0
    current_actual_total = 0
    current_row_total = 0
    x_index = 1
    bin_size = 60 / bins
    for label, data in df.iterrows():
        rowId = df.index.get_loc(label)
        current_prediction_total += data["predicted"] * data["bin_weight"]
        current_actual_total += data["actual"] * data["bin_weight"]
        current_row_total += data["bin_weight"]

        if (rowId + 1) % bin_size == 0:
            x_index += 1
            bin_properties = {
                "bin": ((round(rowId + 1) / 60) * bins),
                "actual_mean": current_actual_total / current_row_total,
                "predicted_mean": current_prediction_total / current_row_total,
                "bin_weight": current_row_total,
            }

            bin_records.append(bin_properties)

            current_prediction_total = 0
            current_actual_total = 0
            current_row_total = 0

    new_df = pd.DataFrame.from_records(bin_records)

    return new_df


def compute_partial_dependence(s, dr_models):
    model_info = dr_models[s]

    model = dr.DatetimeModel.get(
        project=model_info["project_id"],
        model_id=model_info["model_id"],
    )
    pdp_job = model.request_feature_effect(backtest_index="0")
    pdp_job.wait_for_completion()
    pdp = model.get_feature_effect(source="validation", backtest_index="0")

    return s, pdp


def test_distribution(
    data: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in data:
        df_data = data[s]
        series = df_data.loc[:, parameters["target_column"]]
        dates = pd.to_datetime(df_data.loc[:, parameters["datetime_column"]])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 3), dpi=80)
        fig.suptitle(s.capitalize(), fontsize=18)

        ax1.spines["top"].set_alpha(0.3)
        ax2.spines["top"].set_alpha(0.3)
        ax1.spines["bottom"].set_alpha(0.3)
        ax2.spines["bottom"].set_alpha(0.3)
        ax1.spines["right"].set_alpha(0.3)
        ax2.spines["right"].set_alpha(0.3)
        ax1.spines["left"].set_alpha(0.3)
        ax2.spines["left"].set_alpha(0.3)

        month_locator = mdates.MonthLocator(interval=1)
        year_month_formatter = mdates.DateFormatter("%Y-%m")
        ax1.xaxis.set_major_locator(month_locator)  # Locator for major axis only.
        ax1.xaxis.set_major_formatter(year_month_formatter)
        ax1.plot(dates, series)

        ax2.hist(series, bins=20)

        ax1.tick_params(axis="both", labelsize=8)
        ax2.tick_params(axis="both", labelsize=14)
        fig.tight_layout()
        fig.autofmt_xdate()

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png")
        im = Image.open(img_buf)
        plt.close()
        plt.clf()

    return im


def test_stationarity(
    data: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in data:
        df_data = data[s]
        series = df_data.loc[:, parameters["target_column"]]

        adf = adfuller(series, autolag="AIC")
        adf_summary = {
            "Test": "adfuller",
            "Test Statistic": round(adf[0], 4),
            "p-value": round(adf[1], 4),  # type: ignore
            "n_lags": adf[2],  # type: ignore
        }
        for key, value in adf[4].items():  # type: ignore
            if key in ["1%", "5%", "10%"]:
                adf_summary[f"cv_{key}"] = round(value, 4)
            else:
                pass

        kps = kpss(series, nlags=adf_summary["n_lags"])
        kps_summary = {
            "Test": "kpss",
            "Test Statistic": round(kps[0], 4),
            "p-value": round(kps[1], 4),
            "n_lags": kps[2],
        }
        for key, value in kps[3].items():
            if key in ["1%", "5%", "10%"]:
                kps_summary[f"cv_{key}"] = round(value, 4)
            else:
                pass

        # calculate hurst exponent for the maximum sample length n = 2**power

        returns = series.diff().to_numpy()
        power = int(math.log2(len(returns)))

        n = 2**power
        returns_sub = returns[len(returns) - n : len(returns)]
        X = np.arange(2, power + 1)
        Y = np.array([])
        for p in X:
            m = 2**p
            sub = 2 ** (power - p)
            rs_array = np.array([])
            # moving across subsamples
            for i in np.arange(0, sub):
                subsample = returns_sub[i * m : (i + 1) * m]
                mean = np.nanmean(subsample)
                deviate = np.nancumsum(subsample - mean)
                difference = np.nanmax(deviate) - np.nanmin(deviate)
                stdev = np.nanstd(subsample)
                rescaled_range = difference / stdev
                rs_array = np.append(rs_array, rescaled_range)
            # calculating the log2 of average rescaled range
            Y = np.append(Y, np.log2(np.nanmean(rs_array)))

        reg = sm.OLS(Y, sm.add_constant(X))
        res = reg.fit()
        if len(res.params) > 1:
            hurst = res.params[1]
            tstat = (res.params[1] - 0.5) / res.bse[1]
            pvalue = 2 * (1 - spstat.t.cdf(abs(tstat), res.df_resid))
        else:
            hurst = np.nan
            tstat = np.nan
            pvalue = np.nan

        hurst_exp_summary = {
            "Test": "hurst exponent",
            "Test Statistic": round(hurst, 4),
            "p-value": round(pvalue, 4),  # type: ignore
            "n_lags": np.nan,  # type: ignore
        }
        for key, value in adf[4].items():  # type: ignore
            if key in ["1%", "5%", "10%"]:
                hurst_exp_summary[f"cv_{key}"] = np.nan
            else:
                pass

        results_summary = pd.DataFrame.from_records(
            [
                kps_summary,
                adf_summary,
                hurst_exp_summary,
            ],
        )

    return results_summary


def test_feature_impact(dr_models: Dict[str, Any], parameters: Dict[str, Any]):
    def compute_feature_impact(s, dr_models, parameters):
        model_info = dr_models[s]

        model = dr.Model.get(
            project=model_info["project_id"],
            model_id=model_info["model_id"],
        )

        fi = model.get_or_request_feature_impact()

        df = pd.DataFrame.from_records(fi).sort_values("impactNormalized", ascending=True)

        if parameters["features_to_exclude"]:
            parameters["features_to_exclude"].extend(["Unnamed: 0", parameters["datetime_column"]])
        else:
            parameters["features_to_exclude"] = [
                "Unnamed: 0",
                parameters["datetime_column"],
            ]

        df = df[~df.featureName.isin(parameters["features_to_exclude"])]

        return s, df

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(compute_feature_impact, s, dr_models, parameters) for s in dr_models
        ]
        for _, future in zip(dr_models, futures):
            result_s, df = future.result()
            fig = plt.figure(figsize=(12, 3), dpi=80)
            fig.suptitle(result_s.capitalize(), fontsize=18)

            plt.grid(
                visible=True,
                which="major",
                axis="x",
                c="lightgrey",
                zorder=0,
            )
            plt.barh(
                range(len(df)),
                df["impactNormalized"],
                align="center",
                zorder=3,
            )
            plt.yticks(
                range(len(df)),
                df["featureName"].astype(str).tolist(),
            )

            plt.rc(
                "axes",
                labelsize=14,
            )

            img_buf = io.BytesIO()
            plt.savefig(img_buf, format="png")
            im = Image.open(img_buf)

    return im


def test_partial_dependence(dr_models: Dict[str, Any], parameters: Dict[str, Any]):
    test_results: Dict[str, Any] = {}

    if parameters["features_to_exclude"]:
        parameters["features_to_exclude"].extend(["Unnamed: 0", parameters["datetime_column"]])
    else:
        parameters["features_to_exclude"] = [
            "Unnamed: 0",
            parameters["datetime_column"],
        ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(compute_partial_dependence, s, dr_models) for s in dr_models]
        for _, future in zip(dr_models, futures):
            s, pdp = future.result()

            num_subplots = len(pdp.feature_effects)
            num_columns = 3
            # Calculate the number of rows needed to accommodate the subplots
            num_rows = (num_subplots + num_columns - 1) // num_columns

            # Create a figure and an array of subplots in a grid
            fig, axes = plt.subplots(
                num_rows, num_columns, figsize=(12, 12)
            )  # Adjust figsize as needed
            # Flatten the axes array for easier iteration
            axes = axes.flatten()

            i = 0
            for feature in pdp.feature_effects:
                f_name = feature["feature_name"]

                if f_name not in parameters["features_to_exclude"]:
                    pdp_df = pd.DataFrame.from_dict(feature["partial_dependence"]["data"])
                    pdp_df = pdp_df.loc[~pdp_df["label"].isin(["nan", "=Other Unseen="])]

                    try:
                        pdp_df["label"] = pd.to_numeric(pdp_df.label).round(2)
                        pdp_df.sort_values("label", inplace=True, ignore_index=True)
                    except ValueError:
                        pass

                    if i < len(axes):
                        ax = axes[i]
                        ax.plot(
                            "label",
                            "dependence",
                            data=pdp_df,
                            drawstyle="steps",
                            marker="o",
                        )
                        ax.set_title(f_name)
                    else:
                        pass

                    i += 1

            # Remove any empty subplots
            for k in range(i, len(axes)):
                fig.delaxes(axes[k])

            plt.rc(
                "axes",
                labelsize=8,
            )
            # Adjust spacing between subplots
            plt.tight_layout()

            img_buf = io.BytesIO()
            plt.savefig(img_buf, format="png")
            im = Image.open(img_buf)

            test_results[s].reporting_images.append(
                ResultImage(
                    image=im,
                    name="partial_dependence_test",
                )
            )
            plt.close()
            plt.clf()

    return test_results


def test_autocorrelation(
    predictions: dict[str, pd.DataFrame],
    parameters: dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]

        residuals = df_predictions.loc[:, parameters["target_column"]].subtract(
            df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"]
        )

        d_stat = durbin_watson(residuals)

        results_summary = acorr_ljungbox(residuals, boxpierce=True, return_df=True)
        results_summary["lb_stat"] = round(results_summary["lb_stat"], 4)
        results_summary["bp_stat"] = round(results_summary["bp_stat"], 4)
        results_summary.index.name = "lag"
        results_summary.insert(loc=0, column="d_stat", value=np.nan)
        results_summary.loc[1, "d_stat"] = round(d_stat, 4)
        results_summary.reset_index(inplace=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 3), dpi=80)
        fig.suptitle(s.capitalize(), fontsize=18)

        ax1.spines["top"].set_alpha(0.3)
        ax2.spines["top"].set_alpha(0.3)
        ax1.spines["bottom"].set_alpha(0.3)
        ax2.spines["bottom"].set_alpha(0.3)
        ax1.spines["right"].set_alpha(0.3)
        ax2.spines["right"].set_alpha(0.3)
        ax1.spines["left"].set_alpha(0.3)
        ax2.spines["left"].set_alpha(0.3)

        plot_acf(residuals, ax=ax1, lags=40)
        plot_pacf(residuals, ax=ax2, lags=20, method="ywm")

        ax1.tick_params(axis="both", labelsize=14)
        ax2.tick_params(axis="both", labelsize=14)
        fig.tight_layout()

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png")
        im = Image.open(img_buf)

        plt.close()
        plt.clf()

    return results_summary, im


def test_normality(
    predictions: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]

        residuals = df_predictions.loc[:, parameters["target_column"]].subtract(
            df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"]
        )

        (JB, p_value_jb, _, _) = jarque_bera(residuals)
        jb_summary = {
            "Test": "jarque_bera",
            "Test Statistic": JB,
            "p-value": p_value_jb,
        }

        (ad2, p_value_ad) = normal_ad(residuals)
        ad_summary = {
            "Test": "anderson_darling",
            "Test Statistic": ad2,
            "p-value": p_value_ad,
        }

        results_summary = pd.DataFrame.from_records(
            [jb_summary, ad_summary],
        )

    return results_summary


def test_arch(
    predictions: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]

        residuals = df_predictions.loc[:, parameters["target_column"]].subtract(
            df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"]
        )
        (
            lagrange_multiplier_stat,
            lagrange_multiplier_pval,
            f_stat,
            f_pval,
        ) = het_arch(residuals, maxlag=10)

        results_summary = pd.DataFrame.from_records(
            [
                {
                    "lagrange multiplier statistic": round(lagrange_multiplier_stat, 4),
                    "lagrange multiplier p-value": round(lagrange_multiplier_pval, 4),
                    "f statistic": round(f_stat, 4),
                    "f p-value": round(f_pval, 4),
                }
            ]
        )

    return results_summary


def test_lift_chart(dr_models: Dict[str, Any], parameters: Dict[str, Any]):
    for s in dr_models:
        model_info = dr_models[s]

        model = dr.Model.get(
            project=model_info["project_id"],
            model_id=model_info["model_id"],
        )
        lc = model.get_lift_chart(source="validation")
        lift_chart_df = pd.DataFrame.from_dict(lc.bins)
        df = rebin_lift_chart(lift_chart_df, 30)

        fig = plt.figure(figsize=(12, 3), dpi=80)
        fig.suptitle(s.capitalize(), fontsize=18)

        plt.plot(df.bin, df.predicted_mean, label="Predicted", marker="+")
        plt.plot(df.bin, df.actual_mean, label="Actual", marker="o", fillstyle="none")
        plt.legend()
        # plt.xlabel("Bins based on predicted value")
        plt.ylabel("Average target value")
        plt.rc("axes", labelsize=14)

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png")
        im = Image.open(img_buf)
        plt.close()
        plt.clf()

    return im


def test_goodness_of_fit(
    predictions: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]
        actuals = df_predictions.loc[:, parameters["target_column"]].values
        predicts = df_predictions.loc[
            :, f"{parameters['target_column']}_PREDICTION"
        ].values + np.random.normal(
            0, 1e-10, size=df_predictions.shape[0]
        )  # type: ignore

        bin_size = 100 / 30
        bin_max = 100
        bin_count = round(bin_max / bin_size)
        bins = [0 + (bin_num * bin_size) for bin_num in range(0, bin_count + 1)]

        predict_bin = pd.cut(
            predicts,
            np.percentile(predicts, bins),  # type: ignore
            labels=False,
            include_lowest=True,
            duplicates="drop",
        )

        mean_probs_cl1 = np.zeros(bin_count)
        exp_events_cl1 = np.zeros(bin_count)
        obs_events_cl1 = np.zeros(bin_count)
        mean_probs_cl0 = np.zeros(bin_count)
        exp_events_cl0 = np.zeros(bin_count)
        obs_events_cl0 = np.zeros(bin_count)

        for i in range(bin_count):
            mean_probs_cl1[i] = np.nanmean(predicts[predict_bin == i])
            exp_events_cl1[i] = np.nansum(predict_bin == i) * np.array(mean_probs_cl1[i])
            obs_events_cl1[i] = np.nansum(actuals[predict_bin == i])
            mean_probs_cl0[i] = np.nanmean(1 - predicts[predict_bin == i])
            exp_events_cl0[i] = np.nansum(predict_bin == i) * np.array(mean_probs_cl0[i])
            obs_events_cl0[i] = np.nansum(1 - actuals[predict_bin == i])

        chi_square, p_value = chisquare(obs_events_cl1, exp_events_cl1)
        results_summary = pd.DataFrame.from_records(
            [
                {
                    "chi-square-statistic": round(chi_square, 4),
                    "p-value": round(p_value, 4),  # type: ignore
                }
            ]
        )

    return results_summary


def test_discriminatory_power(
    predictions: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]

        actuals = df_predictions.loc[:, parameters["target_column"]].values
        predictions_np = df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"].values
        actual_sign = np.sign(actuals)
        predict_sign = np.sign(predictions_np)  # type: ignore

        labels = [int(x) for x in np.unique(np.concatenate([actual_sign, predict_sign]))]
        confusion_matrix = pd.DataFrame(
            metrics.confusion_matrix(actual_sign, predict_sign, labels=labels),
            index=labels,
            columns=labels,
        )
        confusion_matrix.index.name = "Actual Sign"
        confusion_matrix.columns.name = "Predicted Sign"

        # print(confusion_matrix)

        res = somersd(confusion_matrix)
        somersd_stat = res.statistic
        gAUC = (somersd_stat + 1) / 2
        accuracy = metrics.accuracy_score(actual_sign, predict_sign)
        signs_without_0 = [
            signs
            for signs in zip(actual_sign, predict_sign)  # noqa
            if signs[0] != 0 and signs[1] != 0
        ]
        hit_ratio = metrics.accuracy_score(
            np.array(signs_without_0)[:, 0], np.array(signs_without_0)[:, 1]
        )
        results_summary = pd.DataFrame.from_records(
            [
                {
                    "hit_ratio": hit_ratio,
                    "accuracy": accuracy,
                    "generalized AUC": gAUC,
                    "somersd_stat": res.statistic,
                    "somersd_pvalue": res.pvalue,
                }
            ]
        )

    return results_summary


def test_outcomes_analysis(
    predictions: Dict[str, pd.DataFrame],
    predictions_out_of_sample: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        insample_result = calculate_metrics(predictions[s], parameters)
        outsample_result = calculate_metrics(predictions_out_of_sample[s], parameters)

        selected_metrics = [
            "start",
            "end",
            "records",
            "hit ratio",
            "MAE",
            "MSE",
            "RMSE",
            "R2_Score",
        ]

        # For the in-sample data
        in_sample_dict = {"sample": "in-sample"}
        for k in selected_metrics:
            if k in insample_result:
                in_sample_dict[k] = insample_result[k]

        # For the out-of-sample data
        out_of_sample_dict = {"sample": "out-of-sample"}
        for k in selected_metrics:
            if k in outsample_result:
                out_of_sample_dict[k] = outsample_result[k]

        # Create the DataFrame
        results_summary = pd.DataFrame.from_records([in_sample_dict, out_of_sample_dict])

    return results_summary


def test_var_inflation(training_data: Dict[str, pd.DataFrame], params: Dict[str, Any]):
    for s in training_data:
        feature_data = training_data[s].drop(columns=params["target_column"])
        value_min_pct = 0.60
        value_min_count = len(feature_data) * value_min_pct
        feature_data = feature_data.dropna(thresh=value_min_count, axis=1)

        data_continuous = feature_data.select_dtypes(include=np.number).copy()
        x_lt = sm.add_constant(data_continuous, prepend=False)

        results_summary = pd.DataFrame()
        results_summary["variables"] = x_lt.columns
        results_summary["VIF"] = [
            variance_inflation_factor(x_lt.values, i) for i in range(x_lt.shape[1])
        ]

    return results_summary


def test_heteroskedasticity(
    predictions: Dict[str, pd.DataFrame],
    parameters: Dict[str, Any],
):
    for s in predictions:
        df_predictions = predictions[s]

        residuals = df_predictions.loc[:, parameters["target_column"]].subtract(
            df_predictions.loc[:, f"{parameters['target_column']}_PREDICTION"]
        )

        feature_data = df_predictions.drop(
            columns=[
                parameters["target_column"],
                f"{parameters['target_column']}_PREDICTION",
            ]
        )

        value_min_pct = 0.60
        value_min_count = len(feature_data) * value_min_pct
        feature_data = feature_data.dropna(thresh=value_min_count, axis=1)

        data_continuous = feature_data.select_dtypes(include=np.number).copy()
        x_lt = sm.add_constant(data_continuous, prepend=False)

        # perform Bresuch-Pagan test
        stat_breuschpagan = het_breuschpagan(residuals.values, np.array(x_lt.values, dtype=float))

        breuschpagan_summary = {
            "Test": "Bresuch-Pagan",
            "F Statistic": stat_breuschpagan[2],
            "p-value": stat_breuschpagan[3],
        }

        results_summary = pd.DataFrame.from_records(
            [breuschpagan_summary],
        )

    return results_summary


def test_box_tidwell(training_data: Dict[str, pd.DataFrame], params: Dict[str, Any]):
    for s in training_data:
        feature_data = training_data[s].drop(columns=params["target_column"])
        value_min_pct = 0.60
        value_min_count = len(feature_data) * value_min_pct
        feature_data = feature_data.dropna(thresh=value_min_count, axis=1)

        data_continuous = feature_data.select_dtypes(include=np.number).copy()
        for var in data_continuous.columns:
            data_continuous[f"{var}:Log_{var}"] = data_continuous[var].apply(
                lambda x: x * np.log(x)
            )
        x_lt = sm.add_constant(data_continuous, prepend=False)
        y_lt = training_data[s][params["target_column"]]
        logit_results = GLM(y_lt, x_lt, family=families.Binomial(), missing="drop").fit()

        results_summary = logit_results.summary()

        t = 0
        for tbl in results_summary.tables:
            df = pd.DataFrame.from_records(tbl)
            if t == 1:
                df.iloc[0, 0] = "interactions"
                df = df.rename(columns=df.iloc[0].astype(str))[1:]
                df = df.rename(columns={"P>|z|": "p-value"})
                df_interactions = df[["log_" in str(s).lower() for s in df.iloc[:, 0]]]
            #                box_tidwell_test[s].reporting_tables.append(
            #                    ResultTable(
            #                        table=df_interactions.loc[:, ["interactions", "p-value"]],
            #                        name="box_tidwell_test",
            #                    )
            #                )
            else:
                pass

            t += 1

    return df_interactions


def test_cooks_distance(training_data: Dict[str, pd.DataFrame], params: Dict[str, Any]):
    for s in training_data:
        feature_data = training_data[s].drop(columns=params["target_column"])
        value_min_pct = 0.60
        value_min_count = len(feature_data) * value_min_pct
        feature_data = feature_data.dropna(thresh=value_min_count, axis=1)
        data_continuous = feature_data.select_dtypes(include=np.number).copy()

        x_lt = sm.add_constant(data_continuous, prepend=False)
        y_lt = training_data[s][params["target_column"]]

        logit_results = GLM(y_lt, x_lt, family=families.Binomial(), missing="drop").fit()

        influence = logit_results.get_influence(observed=False)
        summ_df = influence.summary_frame()

        threshold = 4 / len(y_lt)

        fig = influence.plot_index(y_var="cooks", threshold=threshold)

        plt.gcf().set_size_inches((12, 3))
        plt.title(s.capitalize(), fontsize=18)

        fig.tight_layout(pad=1.0)

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png")
        im = Image.open(img_buf)

        plt.close()
        plt.clf()

    return im


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "a": [
                0,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
            ],
            "b": [
                0,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
                1,
                3,
                11,
                6,
                3,
            ],
            "b_PREDICTION": [
                0,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
                1,
                2,
                4,
                6,
                8,
            ],
        }
    )
    im = test_cooks_distance({"x": df}, {"target_column": "b"})
    im.show()
    summary = test_normality({"X": df}, {"target_column": "b"})
    print(summary)
    summary = test_stationarity({"X": df}, {"target_column": "b"})
    print(summary)
    summary, im = test_autocorrelation({"X": df}, {"target_column": "b"})
    print(summary)
    im.show()
    summary = test_arch({"X": df}, {"target_column": "b"})
    print(summary)

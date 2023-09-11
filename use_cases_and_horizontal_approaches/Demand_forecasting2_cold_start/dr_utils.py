from datetime import datetime as dt
import os
import time

from IPython.display import display
import datarobot as dr
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import snowflake
from snowflake.connector.pandas_tools import write_pandas
import yaml

# we can skip the import snowfalke step entirely https://stephenallwright.com/python-connector-write-pandas-snowflake/
# this causes issues if they install snowflake connector and "snowflake" - https://stackoverflow.com/questions/74223900/snowflake-connector-python-package-not-recognized

plt.style.use("fivethirtyeight")

dr_dark_blue = "#08233F"
dr_blue = "#1F77B4"
dr_orange = "#FF7F0E"
dr_red = "#BE3C28"
dr_green = "#00c96e"

max_wait = 3600


def prepare_demo_tables_in_db(
    db_user=None,  # username to access snowflake database
    db_password=None,  # password
    account=None,  # Snowflake Account Identifier can be found in the db_url
    db=None,  # Database to Write_To
    warehouse=None,  # Warehouse
    schema=None,  # schema
):
    """description: method to prepare demo table in snowflake database
    reads from datasets.yaml

    by: gongoraj, demidov91 and jpgomes
        date: 12/22/2022
    """

    with snowflake.connector.connect(
        user=db_user,
        password=db_password,
        account=account,
        warehouse=warehouse,
        database=db,
        schema=schema,
    ) as con:
        with open("datasets.yaml") as f:
            config = yaml.safe_load(f)
            for _, value in config["datasets"].items():
                print("*" * 30)
                print("table:", value["table_name"])
                try:
                    df = pd.read_csv(value["url"], encoding="utf8")
                except:
                    df = pd.read_csv(value["url"], encoding="cp850")
                display(df.head(2))
                # print("info for ", value['table_name'])
                # print(df.info())
                print(
                    "writing", value["table_name"], "to snowflake from: ", value["url"]
                )
                write_pandas(
                    con, df, value["table_name"], auto_create_table=True, overwrite=True
                )
                con.commit()


def create_dataset_from_data_source(
    data_source_name, query, data_store_id, credential_id
):
    data_sources = [
        ds for ds in dr.DataSource.list() if ds.canonical_name == data_source_name
    ]
    if len(data_sources) > 0:
        data_source = data_sources[0]
        print("existing data source:", data_source)
    else:
        ds_params = dr.DataSourceParameters(data_store_id=data_store_id, query=query)
        data_source = dr.DataSource.create(
            data_source_type="jdbc", canonical_name=data_source_name, params=ds_params
        )
        print("new data source:", data_source)

    dataset = dr.Dataset.create_from_data_source(
        data_source_id=data_source.id,
        credential_id=credential_id,
        max_wait=max_wait,
        do_snapshot=True,
    )
    dataset.modify(name=f'{data_source_name}_{dt.now().strftime("%Y%m%d_%H%M")}')

    return data_source, dataset


#################################################################
# data prep
#################################################################


def make_series_stats(data, date_col, series_id, target, freq=1):

    data_tmp = data.copy()
    data_tmp.sort_values([series_id, date_col], inplace=True)
    data_tmp["gap"] = data_tmp.groupby(series_id)[date_col].diff()
    data_mode = (
        data_tmp.groupby(series_id)[["gap"]]
        .agg(gap_mode=("gap", pd.Series.mode))
        .reset_index()
    )
    data_tmp = data_tmp.merge(data_mode, how="left", on=series_id)
    data_tmp["gap_uncommon"] = (
        (data_tmp["gap"] != data_tmp["gap_mode"])
        & (data_tmp["gap"]).notna()
        & (data_tmp["gap_mode"]).notna()
    ) * 1

    data_agg = data_tmp.groupby(series_id).agg(
        rows=(series_id, "count"),
        date_col_min=(date_col, min),
        date_col_max=(date_col, max),
        target_mean=(target, "mean"),
        nunique=(target, "nunique"),
        missing=(target, lambda x: x.isna().sum()),
        zeros=(target, lambda x: (x == 0).sum()),
        negatives=(target, lambda x: (x < 0).sum()),
        gap_max=("gap", max),
        gap_mode=("gap_mode", pd.Series.mode),
        gap_uncommon_count=("gap_uncommon", sum),
    )

    data_agg["duration"] = (
        (data_agg["date_col_max"] - data_agg["date_col_min"]).dt.days
    ) // freq + 1
    data_agg["rows_to_duration"] = data_agg["rows"] / data_agg["duration"]
    data_agg["missing_rate"] = data_agg["missing"] / data_agg["rows"]
    data_agg["zeros_rate"] = data_agg["zeros"] / data_agg["rows"]

    data_agg.reset_index(inplace=True)

    return data_agg


def identify_spikes(data, date_col, series_id, target, span=5, threshold=4):
    tmp = data[[series_id, date_col, target]].copy()
    tmp.sort_values([series_id, date_col], inplace=True)
    tmp.reset_index(drop=True, inplace=True)

    tmp["EWA"] = (
        tmp.groupby(series_id)[target]
        .transform(lambda x: x.ewm(span=span).mean())
        .fillna(value=1)
    )
    tmp["SD"] = (
        tmp.groupby(series_id)[target]
        .transform(lambda x: x.ewm(span=span).std())
        .fillna(value=1)
    )
    tmp["Threshold"] = threshold * tmp["SD"]
    tmp["Spike"] = np.where(tmp[target] >= tmp["Threshold"], 1, 0)

    return tmp


#################################################################
# modeling, deployment, predictions
#################################################################


def save_project_meta(file_to_save, results):
    df_results = pd.DataFrame(results).T
    df_results.index.name = "project_id"
    cols = [
        "project",
        "project_name",
        "project_type",
        "cluster_id",
        "cluster_name",
        "description",
    ]
    df_results = df_results[cols].copy()
    df_results.to_csv(file_to_save, header=not os.path.isfile(file_to_save), mode="a")


def run_projects(data, params, description=None, file_to_save=None):

    if params.get("cluster_id") is None:
        proj = run_project(data, params)
        results = {
            proj.id: {
                "project": proj,
                "project_name": proj.project_name,
                "project_type": "all series",
                "cluster_id": None,
                "cluster_name": None,
                "description": description,
            }
        }
    elif params.get("cluster_id") is not None and params.get(
        "segmented_project", False
    ):
        proj = run_project(data, params)
        results = {
            proj.id: {
                "project": proj,
                "project_name": proj.project_name,
                "project_type": "segmented",
                "cluster_id": params.get("cluster_id"),
                "cluster_name": None,
                "description": description,
            }
        }
    else:
        results = {}
        cluster_id = params["cluster_id"]
        for cl in sorted(data[cluster_id].unique()):
            try:
                data_tmp = data[data[cluster_id] == cl].copy()
                proj = run_project(data_tmp, params, notes=f"_{cluster_id}_{cl}")
                results[proj.id] = {
                    "project": proj,
                    "project_name": proj.project_name,
                    "project_type": "factory part",
                    "cluster_id": cluster_id,
                    "cluster_name": cl,
                    "description": description,
                }
            except Exception as e:
                print(f"The project creation error for the cluster {cluster_id}: {cl}")
                print()
                print(str(e))
    if file_to_save is not None:
        save_project_meta(file_to_save, results)
    return results


def run_project(data, params, notes=""):
    """Runs a project based on provided data and params

    Args:
        data (dr.Dataset, pd.DataFrame, path to a local file):
        params (dict):

    Returns:
        dr.Project:
    """
    proj_params = params.copy()

    target = proj_params.pop("target")
    metric = proj_params.pop("metric", None)
    mode = proj_params.pop("mode", None)

    cluster_id = proj_params.pop("cluster_id", None)
    segmented_project = proj_params.pop("segmented_project", False)

    try:
        fdws = np.abs(proj_params["feature_derivation_window_start"])
        fdwe = np.abs(proj_params["feature_derivation_window_end"])
        fws = proj_params["forecast_window_start"]
        fwe = proj_params["forecast_window_end"]
        project_name = f'{target}{notes}_fdw_{fdws}_{fdwe}_fw_{fws}_{fwe}_{dt.now().strftime("%Y%m%d_%H%M")}'
    except Exception as e:
        print("DataRobot will define FDW and FD automatically.")
        project_name = f'{target}{notes}_{dt.now().strftime("%Y%m%d_%H%M")}'

    feature_settings = [
        dr.FeatureSettings(c, known_in_advance=True)
        for c in proj_params.pop("features_known_in_advance", [])
    ]
    feature_settings += [
        dr.FeatureSettings(c, do_not_derive=True)
        for c in proj_params.pop("do_not_derive_features", [])
    ]
    proj_params["feature_settings"] = feature_settings

    print(str(dt.now()), "start:", project_name)
    if isinstance(data, dr.Dataset):
        project = dr.Project.create_from_dataset(
            project_name=project_name, dataset_id=data.id
        )
    else:
        project = dr.Project.create(project_name=project_name, sourcedata=data)

    if "calendar_file" in proj_params.keys():
        calendar_file = proj_params.pop("calendar_file")
        if calendar_file is not None:
            proj_params["calendar_id"] = dr.CalendarFile.create(calendar_file).id

    ts_specs = dr.DatetimePartitioningSpecification(**proj_params)

    if cluster_id is not None and segmented_project:
        segmentation_task_results = dr.SegmentationTask.create(
            project_id=project.id,
            target=target,
            use_time_series=True,
            datetime_partition_column=proj_params["datetime_partition_column"],
            multiseries_id_columns=proj_params["multiseries_id_columns"],
            user_defined_segment_id_columns=[cluster_id],
        )
        segm_task_id = segmentation_task_results["completedJobs"][0].id
    else:
        segm_task_id = None

    project.analyze_and_model(
        target=target,
        metric=metric,
        partitioning_method=ts_specs,
        worker_count=-1,
        mode=mode,
        segmentation_task_id=segm_task_id,
        max_wait=3600,
    )

    return project


def get_leaderboard(proj, metrics=[], rename_proj_metric=False):
    """Lists the models from provided project

    Args:
        proj (dr.Project):
        metrics (list, optional): a list of additional metrics to provide. Defaults to [].
        rename_proj_metric (bool, optional): rename the column with the project metric name to just metric. Defaults to False.

    Returns:
        dr.DataFrame:
    """
    proj.unlock_holdout()
    metric = proj.metric
    higher_better = ["Accuracy", "AUC", "Gini", "Gini Norm", "R Squared"]
    ascending = metric not in higher_better

    if metric not in metrics:
        metrics = [metric] + metrics

    parts = [["backtesting", "backtests"], ["validation", "backtest1"]]

    model_scores = []
    for model in proj.get_datetime_models():
        tmp = {
            "project_id": proj.id,
            "blueprint_id": model.blueprint_id,
            "featurelist_id": model.featurelist_id,
            "model_id": model.id,
            "model_n": model.model_number,
            "model_cat": model.model_category,
            "model_type": model.model_type,
            "model": model,
            "duration": model.training_duration,
            "end_date": model.training_end_date,
        }
        for m in metrics:
            for p, n in parts:
                tmp[f"{m}_{n}"] = model.metrics[m][p]
        model_scores.append(tmp)

    model_scores = pd.DataFrame(model_scores)
    model_scores = model_scores.sort_values(
        [f"{metric}_backtests", f"{metric}_backtest1"],
        ascending=ascending,
        na_position="last",
    )
    model_scores.reset_index(drop=True, inplace=True)
    if rename_proj_metric:
        model_scores.rename(
            columns={
                f"{metric}_backtests": "metric_backtests",
                f"{metric}_backtest1": "metric_backtest1",
            },
            inplace=True,
        )
    return model_scores


def make_deployments(
    projects_dct,
    file_to_save=None,
    target_drift_enabled=False,
    feature_drift_enabled=False,
):
    """
    Args:
        projects_dct (dict): the dictionary with projects
        file_to_save (str, optional): Defaults to None.

    Returns:
        dict: dictionary with the projects and related deployments
    """
    deployments_dct = projects_dct.copy()
    for cl, vals in deployments_dct.items():

        project = vals["project"]

        if vals["project_type"] == "segmented":
            model_id = project.get_combined_models()[0].id
        else:
            model_id = None

        deployment = make_deployment(
            project,
            name=project.project_name,
            model_id=model_id,
            target_drift_enabled=target_drift_enabled,
            feature_drift_enabled=feature_drift_enabled,
        )
        deployments_dct[cl]["deployment_id"] = deployment.id
        deployments_dct[cl]["deployment"] = deployment

    if file_to_save is not None:
        df_log = pd.DataFrame(deployments_dct).T
        df_log.index.name = "project_id"
        cols = [
            "project",
            "project_name",
            "project_type",
            "cluster_id",
            "cluster_name",
            "description",
            "deployment_id",
            "deployment",
        ]
        df_log = df_log[cols].copy()
        df_log.to_csv(file_to_save, header=not os.path.isfile(file_to_save), mode="a")

    return deployments_dct


def make_deployment(
    project,
    name=None,
    model_id=None,
    target_drift_enabled=False,
    feature_drift_enabled=False,
):
    """deploys recommended or provided model

    Args:
        project (dr.Project):
        name (str, optional): a name for the depliyment. Defaults to None.
        model_id (str, optional): Defaults to None.

    Returns:
        dr.Deployment
    """
    if model_id is None:
        # model_id = dr.ModelRecommendation.get(project.id).get_model().id
        model_id = project.recommended_model().id
    if name is None:
        name = project.project_name
    pred_serv_id = dr.PredictionServer.list()[0].id
    deployment = dr.Deployment.create_from_learning_model(
        model_id=model_id, label=name, default_prediction_server_id=pred_serv_id
    )

    print(
        f"Deployment ID: {deployment.id}; URL: https://app.datarobot.com/deployments/{deployment.id}/overview"
    )
    print()

    try:
        deployment.update_drift_tracking_settings(
            target_drift_enabled=target_drift_enabled,
            feature_drift_enabled=feature_drift_enabled,
            max_wait=3600,
        )
    except Exception as e:
        print(str(e))

    return deployment


def make_predictions(
    deployments,
    intake_settings,
    output_settings,
    wait_for_completion=True,
    forecast_point=None,
    passthrough_columns_set="all",
    passthrough_columns=None,
):
    jobs = []

    for _, vals in deployments.items():
        print(str(dt.now()), "start:", vals["project_name"], "predictions")
        deployment = vals["deployment"]

        if vals["project_type"] in ("all series", "segmented"):
            jobs.append(
                make_predictions_from_deployment(
                    deployment,
                    intake_settings,
                    output_settings,
                    wait_for_completion,
                    forecast_point,
                    passthrough_columns_set,
                    passthrough_columns,
                )
            )
        else:
            # todo
            pass

    return jobs


def make_predictions_from_deployment(
    deployment,
    intake_settings,
    output_settings,
    wait_for_completion=True,
    forecast_point=None,
    passthrough_columns_set="all",
    passthrough_columns=None,
):

    job = dr.BatchPredictionJob.score(
        deployment=deployment.id,
        intake_settings=intake_settings,
        output_settings=output_settings,
        timeseries_settings={
            "type": "forecast",
            "forecast_point": forecast_point,
            "relax_known_in_advance_features_check": True,
        },
        passthrough_columns_set=passthrough_columns_set,
        passthrough_columns=passthrough_columns,
    )

    if wait_for_completion:
        job.wait_for_completion()

    return job


def create_preds_job_definitions(
    deployments,
    intake_settings,
    output_settings,
    enabled=False,
    schedule=None,
    passthrough_columns_set="all",
    passthrough_columns=None,
):

    for pid, vals in deployments.items():
        print(
            str(dt.now()),
            "start:",
            vals["project_name"],
            "create predictions job definition",
        )
        deployment = vals["deployment"]

        if vals["project_type"] in ("all series", "segmented"):
            preds_job_def = create_preds_job_definition(
                deployment,
                intake_settings,
                output_settings,
                enabled=enabled,
                schedule=schedule,
                passthrough_columns_set=passthrough_columns_set,
                passthrough_columns=passthrough_columns,
            )
            deployments[pid]["preds_job_def"] = preds_job_def
            deployments[pid]["preds_job_def_id"] = preds_job_def.id
        else:
            # todo
            pass

    return deployments


def create_preds_job_definition(
    deployment,
    intake_settings,
    output_settings,
    enabled=False,
    schedule=None,
    passthrough_columns_set="all",
    passthrough_columns=None,
):

    job_specs = {
        "deployment_id": deployment.id,
        "num_concurrent": 16,
        "skip_drift_tracking": True,
        "prediction_warning_enabled": False,
        "timeseries_settings": {
            "type": "forecast",
            "relax_known_in_advance_features_check": True,
        },
        "csv_settings": {"delimiter": ",", "quotechar": '"', "encoding": "utf-8"},
        "chunk_size": "auto",
        "include_prediction_status": False,
        "intake_settings": intake_settings,
        "outputSettings": output_settings,
    }

    if passthrough_columns_set == "all":
        job_specs["passthrough_columns_set"] = "all"
    else:
        job_specs["passthrough_columns"] = passthrough_columns

    if schedule is None:
        schedule = {
            "minute": [0],
            "hour": [23],
            "day_of_week": ["*"],
            "day_of_month": ["*"],
            "month": ["*"],
        }

    preds_job_def = dr.BatchPredictionJobDefinition.create(
        enabled=enabled,
        batch_prediction_job=job_specs,
        name=f'{deployment.label}{dt.now().strftime("%Y%m%d_%H%M")}',
        schedule=schedule,
    )
    return preds_job_def


def get_series_accuracy(project, model, compute_all_series=False):
    project = project.set_worker_count(-1)
    try:
        model_sa = model.get_series_accuracy_as_dataframe()

        if model_sa.shape[0] == model_sa["backtestingScore"].isna().sum():
            _ = model.compute_series_accuracy(compute_all_series=compute_all_series)

            num_jobs = len(
                [j for j in project.get_all_jobs() if j.job_type == "series_accuracy"]
            )
            while num_jobs > 0:
                time.sleep(5 + (num_jobs // 20) * 15)
                num_jobs = len(
                    [
                        j
                        for j in project.get_all_jobs()
                        if j.job_type == "series_accuracy"
                    ]
                )

            model_sa = model.get_series_accuracy_as_dataframe()
            return model_sa
        else:
            return model_sa
    except:
        _ = model.compute_series_accuracy(compute_all_series=compute_all_series)

        num_jobs = len(
            [j for j in project.get_all_jobs() if j.job_type == "series_accuracy"]
        )
        while num_jobs > 0:
            time.sleep(5 + (num_jobs // 20) * 15)
            num_jobs = len(
                [j for j in project.get_all_jobs() if j.job_type == "series_accuracy"]
            )

        model_sa = model.get_series_accuracy_as_dataframe()
        return model_sa


def make_train_preds_from_model(
    project, model, data_subsets=["allBacktests", "holdout"]
):

    pred_jobs = []
    preds_lst = []

    for data_subset in data_subsets:
        if data_subset == "holdout":
            project.unlock_holdout()
        try:
            # request training predictions and get job ids
            pred_jobs.append([model, model.request_training_predictions(data_subset)])
        except Exception as e:
            print(str(e))
            # retrieve training predictions if they were already requested
            train_preds = dr.TrainingPredictions.list(project.id)
            for train_pred in train_preds:
                if (
                    train_pred.model_id == model.id
                    and train_pred.data_subset == data_subset
                ):
                    preds_tmp = dr.TrainingPredictions.get(
                        project.id, train_pred.prediction_id
                    ).get_all_as_dataframe()
                    preds_lst.append(preds_tmp)

    # get training predictions from job ids
    for _, pj in pred_jobs:
        preds_tmp = pj.get_result_when_complete(max_wait=6000).get_all_as_dataframe()
        preds_lst.append(preds_tmp)

    df_preds = pd.concat(preds_lst)

    return df_preds


def make_train_preds_from_projects(
    projects_dct, data_train, date_col, series_id, target
):
    """requests training predictions from the specified projects and
       combines with corresponding training data

    Args:
        projects_dct (dict): the dictionary with projects
        data_train (pd.DataFrame): the training dataset
        date_col (str):
        series_id (str):
        target (str):

    Returns:
        pd.DataFrame
    """
    preds = []
    for _, vals in projects_dct.items():
        print(str(dt.now()), "start:", vals["project_name"], "training predictions")
        project = vals["project"]
        cluster_id = vals["cluster_id"]
        cols_to_select = [date_col, series_id, target]
        if cluster_id is not None:
            cols_to_select += [cluster_id]

        if project.is_segmented:
            combined_model = project.get_combined_models()[0]
            df_segm = combined_model.get_segments_as_dataframe()
            for row in df_segm.itertuples():
                spid = row.project_id
                cluster_name = row.Index
                print(
                    str(dt.now()),
                    "start:",
                    vals["project_name"],
                    f"training predictions: {cluster_name}",
                )

                data_tmp = data_train[data_train[cluster_id] == cluster_name].copy()
                data_tmp = data_tmp[cols_to_select].copy()
                data_tmp["project_type"] = vals["project_type"]
                data_tmp["project_id"] = spid
                data_tmp["description"] = vals["description"]

                proj_tmp = dr.Project.get(spid)
                proj_tmp = proj_tmp.set_worker_count(-1)
                model_tmp = get_leaderboard(proj_tmp)["model"][0]
                preds_tmp = make_train_preds_from_model(proj_tmp, model_tmp)
                preds_tmp.rename(
                    columns={
                        "timestamp": date_col,
                        "series_id": series_id,
                        "prediction": f"{target}_prediction",
                    },
                    inplace=True,
                )
                preds_tmp[date_col] = pd.to_datetime(preds_tmp[date_col].str[:19])
                preds_tmp = data_tmp.merge(preds_tmp, on=[series_id, date_col])
                preds.append(preds_tmp.copy())
        else:
            if vals["project_type"] == "factory part":
                cluster_name = vals["cluster_name"]
                print(
                    str(dt.now()),
                    "start:",
                    vals["project_name"],
                    f"training predictions: {cluster_name}",
                )
                data_tmp = data_train[data_train[cluster_id] == cluster_name].copy()

            else:
                data_tmp = data_train.copy()

            data_tmp = data_tmp[cols_to_select].copy()
            data_tmp["project_type"] = vals["project_type"]
            data_tmp["project_id"] = project.id
            data_tmp["description"] = vals["description"]

            model_tmp = get_leaderboard(project)["model"][0]
            preds_tmp = make_train_preds_from_model(project, model_tmp)
            preds_tmp.rename(
                columns={
                    "timestamp": date_col,
                    "series_id": series_id,
                    "prediction": f"{target}_prediction",
                },
                inplace=True,
            )
            preds_tmp[date_col] = pd.to_datetime(preds_tmp[date_col].str[:19])
            preds_tmp = data_tmp.merge(preds_tmp, on=[series_id, date_col])
            preds.append(preds_tmp.copy())

    return pd.concat(preds, ignore_index=True, sort=False)


def get_target_and_feature_drift(
    deployment, start_time=None, end_time=None, metric=None
):
    """
    deployment : dr.Deployment
    start_time : datetime
        start of the time period
    end_time : datetime
        end of the time period
    metric : str
        The metric used to calculate the drift score. Allowed
        values include `psi`, `kl_divergence`, `dissimilarity`, `hellinger`, and
        `js_divergence`.
    """
    td = deployment.get_target_drift(
        start_time=start_time, end_time=end_time, metric=metric
    )
    depl_drifts = [
        {
            "feature": td.target_name,
            "feature_impact": 1.0,
            "drift_score": td.drift_score,
            "metric": td.metric,
            "start": td.period["start"],
            "end": td.period["end"],
            "is_target": 1,
        }
    ]
    for dd in deployment.get_feature_drift(
        start_time=start_time, end_time=end_time, metric=metric
    ):
        dd_vals = {
            "feature": dd.name,
            "feature_impact": dd.feature_impact,
            "drift_score": dd.drift_score,
            "metric": dd.metric,
            "start": dd.period["start"],
            "end": dd.period["end"],
            "is_target": 0,
        }
        depl_drifts.append(dd_vals)
    return pd.DataFrame(depl_drifts)


#################################################################
# metrics
#################################################################


def rmse(data, target, pred_col):
    return np.sqrt(np.mean((data[target] - data[pred_col]) ** 2))


def mae(data, target, pred_col):
    return np.mean(np.abs((data[target] - data[pred_col])))


def smape(data, target, pred_col):
    return 100.0 * np.mean(
        np.abs(data[pred_col] - data[target])
        / ((np.abs(data[pred_col]) + np.abs(data[target])) / 2)
    )


def get_metrics(data, target, pred_cols):
    res = {}
    metrics = {"rmse": rmse, "mae": mae, "smape": smape}
    for name, metr in metrics.items():
        res[name] = {}
        for col in pred_cols:
            res[name][col] = metr(data, target=target, pred_col=col)
    return pd.DataFrame(res)


#################################################################
# plotting
#################################################################
def plot_series_count_over_time(data, date_col, series_id):
    ax = (
        data.groupby(date_col)[series_id]
        .nunique()
        .plot(figsize=(15, 7), color=[dr_orange], ylim=0)
    )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(True, alpha=0.2)
    ax.yaxis.grid(False)

    plt.title("The number of series over time")
    plt.xlabel("")
    plt.ylabel("The number of series")


def plot_hist(data, col, clip_min=0, clip_max=1000, bins=20):
    ax = data[col].clip(clip_min, clip_max).hist(bins=bins, figsize=(15, 7))
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)

    plt.title(f"{col} histogram")
    plt.xlabel("")
    plt.ylabel("")


def plot_num_col_over_time(data, date_col, num_col, func="sum", freq=None):
    if freq is not None:
        grouper = pd.Grouper(freq=freq, key=date_col, closed="left", label="left")
    else:
        grouper = date_col

    data_agg = data.groupby(grouper)[num_col].agg(func)

    ax = data_agg.plot(figsize=(15, 7), color=[dr_orange])
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)

    plt.title(f"{num_col} over time")
    plt.xlabel("")
    plt.ylabel(num_col)


def plot_series_over_time(data, date_col, series_id, series_name, num_cols):
    data_tmp = data[data[series_id] == series_name].copy()

    ax = data_tmp.plot(
        x=date_col, y=num_cols, figsize=(15, 7), color=[dr_orange, dr_blue]
    )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)

    plt.title(f"{series_name} over time")
    plt.xlabel("")
    plt.ylabel("")


def plot_accuracy_over_time(
    project, model, backtest=0, forecast_distance=None, series_id=None, max_wait=3600
):
    project = project.set_worker_count(-1)
    try:
        job = model.compute_datetime_trend_plots(backtest=backtest)
        job.wait_for_completion()
    except:
        pass

    model_aot = model.get_accuracy_over_time_plot(
        backtest=backtest,
        forecast_distance=forecast_distance,
        series_id=series_id,
        max_wait=max_wait,
    )
    data = pd.DataFrame(model_aot.bins)

    ax = data.plot(
        x="start_date",
        y=["actual", "predicted"],
        ylim=0,
        figsize=(15, 7),
        color=[dr_orange, dr_blue],
        marker="o",
        markersize=10,
    )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(True, alpha=0.2)
    ax.yaxis.grid(False)

    plt.title(f"Accuracy over time:\n{model.model_type}")
    plt.xlabel("")
    plt.ylabel(project.target)


def plot_stability_scores(project, model, metric=None):
    if metric is None:
        metric = project.metric
    scores = model.metrics[metric]["backtestingScores"]
    ind = [f"Backtest{i+1}" for i in range(0, len(scores))]
    scores = pd.Series(scores, index=ind).sort_index(ascending=False)

    ax = scores.plot(
        figsize=(15, 7), ylim=0, color=[dr_orange], marker="o", markersize=10
    )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(True, alpha=0.2)
    ax.yaxis.grid(False)

    plt.title(f"{metric} stability:\n{model.model_type}")
    plt.xlabel("")
    plt.ylabel(metric)


def plot_feature_impacts(model, top_n=100):

    feature_impacts = model.get_or_request_feature_impact()
    percent_tick_fmt = mtick.PercentFormatter(xmax=1.0)

    impact_df = pd.DataFrame(feature_impacts).head(top_n)
    impact_df.sort_values(by="impactNormalized", ascending=True, inplace=True)

    # Positive values are blue, negative are red
    bar_colors = impact_df.impactNormalized.apply(
        lambda x: dr_red if x < 0 else dr_blue
    )

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

    # return ax


def plot_predictions(data, test_start_date, date_col, target, freq):
    data_tmp = data[data[date_col] >= test_start_date].copy()
    grouper = pd.Grouper(freq=freq, key=date_col, closed="left", label="left")
    data_agg = (
        data_tmp.groupby(grouper)[[target, f"{target}_prediction"]]
        .sum()
        .replace(0, np.NaN)
    )

    ax = data_agg.plot(
        figsize=(15, 7),
        ylim=0,
        rot=45,
        color=[dr_orange, dr_blue],
        marker="o",
        markersize=10,
    )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(True, alpha=0.3)
    ax.yaxis.grid(False)

    plt.title("Actuals and predictions")
    plt.xlabel("")
    plt.ylabel("")


def plot_drift_data(data, drift_score_threshold=0.2, feature_impact_threshold=0.5):
    data_tmp = data.copy()
    data_tmp["color"] = np.where(
        data_tmp["drift_score"] >= drift_score_threshold,
        np.where(
            data_tmp["feature_impact"] >= feature_impact_threshold, dr_red, dr_orange
        ),
        dr_green,
    )
    data_tmp["drift_score_rank"] = data_tmp["drift_score"].rank(ascending=False) / 100
    data_tmp["drift_score_orig"] = data_tmp["drift_score"].copy()
    data_tmp["drift_score"] = np.where(
        data_tmp["drift_score_orig"] <= 1,
        data_tmp["drift_score_orig"],
        data_tmp["drift_score_rank"] + 1,
    )

    ax = data_tmp.plot(
        kind="scatter",
        x="feature_impact",
        y="drift_score",
        s=70,
        marker="o",
        color=data_tmp["color"],
        figsize=(15, 7),
    )

    plt.title("Feature Drift vs. Feature Importance")
    plt.xlabel("Importance")
    plt.ylabel("Drift")
    plt.axhline(0.2, color="gray", linewidth=2)
    plt.axvline(0.5, color="gray", linewidth=2)

    for row in data_tmp[
        (data_tmp["color"].isin([dr_red])) | (data_tmp["feature_impact"] == 1.0)
    ].itertuples():
        plt.annotate(
            row.feature,
            (row.feature_impact - 0.1, row.drift_score + 0.02),
            color="white",
        )
    ax.set_facecolor(dr_dark_blue)
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)

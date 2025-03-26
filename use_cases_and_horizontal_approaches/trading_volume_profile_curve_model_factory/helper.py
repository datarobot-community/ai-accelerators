######## Helper Functions ############

# Useful functions for creating a multi window time series


import datetime
from datetime import timedelta
from os.path import join
import time

import datarobot as dr
import numpy as np
import pandas as pd


def prepare_data(data, modelling_choice, aggregation_dictionary=None):
    # this function aggregates the minute data according to the slice size
    # furthermore, it add features based on the neighbouring slices
    # with the neighbourhood size defined by the interest radius:
    # how many slices before and after should be considered
    # we can choose whether we target percentage of daily volume
    # or the volume itself

    slice_size = modelling_choice["window_length"]
    interest_radius = int(modelling_choice["window_radius"])
    percentage = modelling_choice["percentage"]

    # first we make sure that the time features have the correct type:
    data = data.copy()
    data[["date", "date_time"]] = data[["date", "date_time"]].apply(pd.to_datetime)
    data.minute = pd.to_timedelta(data.minute + ":00")

    # we also get the endpoints of the time period
    start = data.date_time.min()
    end = data.date_time.max()

    # Need to check that the slice size makes sense:
    trading_day = data.minute.max() - data.minute.min()
    trading_minutes = trading_day.total_seconds() / 60

    if trading_minutes % slice_size != 0:
        return "The trading day can't be divided using the specified slice size."

    # Now we aggregate according to the slice size

    if aggregation_dictionary == None:
        aggregation_dictionary = {
            "date": "first",
            "minute": "min",
            "TradeVolume": ["sum", "min", "max", "std"],
            "TradePrice": ["mean", "min", "max", "std"],
            "NumTrades": ["sum", "min", "max", "std"],
        }

    aggregate = (
        data.groupby(
            [
                pd.Grouper(key="date_time", freq=str(slice_size) + "min"),
                "Symbol",
                "Sector",
                "Security_Type",
                "Cap",
                "Style",
                "Exchange",
            ]
        )
        .agg(aggregation_dictionary)
        .reset_index()
    )
    aggregate.columns = ["_".join(a) for a in aggregate.columns.to_flat_index()]

    if percentage == True:
        # we add column with daily total for each symbol/date pair
        aggregate = pd.merge(
            aggregate,
            aggregate[["Symbol_", "date_first", "TradeVolume_sum"]]
            .groupby(["Symbol_", "date_first"])
            .sum()
            .reset_index(),
            on=["Symbol_", "date_first"],
        )
        # we calculate percentage volume by diving by daily total
        aggregate["TradeVolume_sum"] = (
            aggregate["TradeVolume_sum_x"] / aggregate["TradeVolume_sum_y"]
        )
        # we drop the volumen and daily volume columns, we only keep the percentage one
        aggregate.drop(columns=["TradeVolume_sum_x", "TradeVolume_sum_y"], inplace=True)

    # Finally, we add columns to reflect the radius at which we would like to look
    # Note that we are happy to look at the previous and following trading days when adding the neighbours
    # It makes sense but the logic can be easily changed if we want to only look within the day

    aggregate.sort_values(["Symbol_", "date_time_"], ascending=True, inplace=True)

    neighbours = []

    for n in range(interest_radius):
        # n slices fwd
        suffix = "_fwd_" + str(n + 1)
        fwd = (
            aggregate.select_dtypes(include="number")
            .drop(columns=["minute_min"])
            .shift(-1)
            .add_suffix(suffix)
        )
        fwd = pd.concat([aggregate[["Symbol_", "date_time_"]], fwd], axis=1)
        fwd_cols = [col for col in fwd.columns if "fwd" in col]
        fwd.loc[
            (fwd.date_time_ > end - (n + 1) * timedelta(minutes=slice_size)), fwd_cols
        ] = None
        neighbours.append(fwd.drop(columns=["Symbol_", "date_time_"]))

        # n slices bwd
        suffix = "_bwd_" + str(n + 1)
        bwd = (
            aggregate.select_dtypes(include="number")
            .drop(columns=["minute_min"])
            .shift(1)
            .add_suffix(suffix)
        )
        bwd = pd.concat([aggregate[["Symbol_", "date_time_"]], bwd], axis=1)
        bwd_cols = [col for col in bwd.columns if "bwd" in col]
        bwd.loc[
            (bwd.date_time_ < start + (n + 1) * timedelta(minutes=slice_size)), bwd_cols
        ] = None
        neighbours.append(bwd.drop(columns=["Symbol_", "date_time_"]))

    appendage = pd.concat(neighbours, axis=1)
    prepared_data = pd.concat([aggregate, appendage], axis=1)

    return prepared_data


def run_ts_project(source_data, project_name, target, calendar, kia_columns):
    # Quickly set up a TS project with standard settings

    date_time_part = "date_time_"
    multiseries_ids = "Symbol_"
    number_of_workers = -1
    metric = "MASE"
    number_of_backtests = 3
    fdw_start = -14
    fdw_end = 0
    fw_start = 1
    fw_end = 1

    data_upload_start = time.time()

    print(
        "Project {} creation started: {}".format(
            project_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
    )
    project = dr.Project.create(project_name=project_name, sourcedata=source_data)

    # Features known in advance

    feature_settings = []
    for column in kia_columns:
        feature_settings.append(dr.FeatureSettings(column, known_in_advance=True))

    partitioning_specs = dr.DatetimePartitioningSpecification(
        datetime_partition_column=date_time_part,
        use_time_series=True,
        multiseries_id_columns=[multiseries_ids],
        feature_settings=feature_settings,
        feature_derivation_window_start=fdw_start,
        feature_derivation_window_end=fdw_end,
        forecast_window_start=fw_start,
        forecast_window_end=fw_end,
        use_cross_series_features=False,
        number_of_backtests=number_of_backtests,
        calendar_id=calendar.id,
    )

    project.analyze_and_model(
        target=target,
        metric=metric,
        partitioning_method=partitioning_specs,
        worker_count=number_of_workers,
        max_wait=6000,
    )
    print(
        "Project creation finished. Elapsed time: {}".format(
            time.time() - data_upload_start
        )
    )
    url = "https://app.datarobot.com/projects/" + project.id + "/eda"
    print(url)

    return project.id, url


def run_ts_project_with_dictionary(source_data, project_name, datetime_dict):
    # Grab TS settings from dictionary
    target = datetime_dict["target"]
    kia_columns = datetime_dict["KIA"]
    calendar = datetime_dict["calendar"]
    date_time_part = datetime_dict["partitioning"]
    multiseries_ids = datetime_dict["seriesID"]
    number_of_workers = datetime_dict["workers"]
    metric = datetime_dict["metric"]
    number_of_backtests = datetime_dict["backtests"]
    fdw_start = datetime_dict["fdw_start"]
    fdw_end = datetime_dict["fdw_end"]
    fw_start = datetime_dict["fw_start"]
    fw_end = datetime_dict["fw_end"]

    data_upload_start = time.time()

    print(
        "Project {} creation started: {}".format(
            project_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
    )
    project = dr.Project.create(project_name=project_name, sourcedata=source_data)

    # Features known in advance

    feature_settings = []
    for column in kia_columns:
        feature_settings.append(dr.FeatureSettings(column, known_in_advance=True))

    # We just need to now bring all the specs into DataRobot

    partitioning_specs = dr.DatetimePartitioningSpecification(
        datetime_partition_column=date_time_part,
        use_time_series=True,
        multiseries_id_columns=[multiseries_ids],
        feature_settings=feature_settings,
        feature_derivation_window_start=fdw_start,
        feature_derivation_window_end=fdw_end,
        forecast_window_start=fw_start,
        forecast_window_end=fw_end,
        use_cross_series_features=False,
        number_of_backtests=number_of_backtests,
        calendar_id=calendar.id,
    )

    project.analyze_and_model(
        target=target,
        metric=metric,
        partitioning_method=partitioning_specs,
        worker_count=number_of_workers,
        max_wait=6000,
    )
    print(
        "Project creation finished. Elapsed time: {}".format(
            time.time() - data_upload_start
        )
    )
    url = "https://app.datarobot.com/projects/" + project.id + "/eda"
    print(url)

    return project, url


def run_all_projects(prepared_data, slices, modelling_choice, datetime_dict):
    # this function just loops through all the time windows (specified by slices)
    # and collects all the projects created in a dataframe

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    project_ids = []
    projects = []
    urls = []
    project_time_window_starts = []

    percentage_str = "percentage"
    if modelling_choice["percentage"] == False:
        percentage_str = "sum"

    for i, s in slices.iterrows():
        df_filtered = prepared_data[prepared_data["minute_min"] == s[0]]

        project_name = (
            "VolPred_"
            + percentage_str
            + "_each_"
            + str(modelling_choice["window_length"])
            + "min_"
            + str(s["hours"])
            + ":"
            + str(s["minutes"])
            + "_v_"
            + today
        )

        print(project_name)

        project, url = run_ts_project_with_dictionary(
            df_filtered, project_name, datetime_dict
        )

        project_time_window_starts.append(str(s["hours"]) + ":" + str(s["minutes"]))
        project_ids.append(project.id)
        projects.append(project)
        urls.append(url)

    projects_df = pd.DataFrame(
        list(zip(project_ids, project_time_window_starts, urls, projects))
    )
    projects_df.columns = ["project_id", "slice", "url", "project"]

    return projects_df


def prepare_data_for_predictions(data, modelling_choice, aggregation_dictionary=None):
    # We prepare data for prediction.

    start = data.date.min()
    end = data.date.max()

    # First we replicate what we did for the training data
    prepared_data = prepare_data(data, modelling_choice, aggregation_dictionary=None)

    # We identify the numeric columns, which won't be know at prediction time

    numeric_cols = list(
        prepared_data.select_dtypes(include="number")
        .drop(columns=["minute_min"])
        .columns
    )
    start = datetime.datetime.fromisoformat(start)
    end = datetime.datetime.fromisoformat(end)

    # We make sure that the rows which we want to predict have blanks on the numeric data

    recent_data = prepared_data[
        prepared_data.date_time_ > (end - (16) * timedelta(days=1))
    ].copy()
    recent_data.loc[
        (recent_data.date_first > end - timedelta(days=1)), numeric_cols
    ] = ""

    return recent_data

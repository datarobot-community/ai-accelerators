import asyncio
from datetime import datetime
import itertools
import re
from sys import displayhook
import time
from typing import List

from dask import compute, delayed  # need to install
import datarobot as dr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pytimeparse.timeparse import timeparse  # !pip install pytimeparse
import seaborn as sns
from tenacity import (  # need to install
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

# from datarobot_bp_workshop import Visualize


####### advanced tuning ##############
def error_retry_decision(x) -> bool:
    """
    Helper for determining when to retry the block of code

    """

    if hasattr(x, "status_code"):
        if x.status_code == 502:
            print("Server error! Waiting and trying again...")
            return True

        if x.status_code == 422:
            if "message" in x.json.keys():
                if "Unable to add jobs to the queue" in x.json["message"]:
                    print(
                        "Unable to add jobs to the queue! Waiting and trying again..."
                    )
                    return True

    else:
        return False


def _delete_model(model: dr.models.model.Model):
    """
    Deletes supplied DataRobot model

    models: DataRobot model

    """

    try:
        model.delete()

    except:
        pass


def _delete_models(models: List[dr.models.model.Model]):
    """
    Delete a batch of models

    models: list of DataRobot models

    """

    # Using dask to delete models faster
    jobs = []
    for model in models:
        jobs.append(delayed(_delete_model)(model))

    jobs = compute(*jobs)


def _sort_models(
    project: dr.models.project.Project,
    models: List[dr.models.model.Model],
    partition: str = "validation",
    metric: str = None,
) -> List[dr.Model]:
    """
    Sorts supplied models by a requested metric and partition

    project: DataRobot project
    models: list of DataRobot models
    partition: string representing which partition to use (see dr.models.model.Model.metrics)
    metric: metric to sort by

    """

    # If metric isn't specified, set to project metric
    if metric is None:
        metric = project.metric

    # If unsupervised project, manually create metrics dict
    if project.unsupervised_mode:
        metrics = {
            "metric_details": [
                {"ascending": False, "metric_name": "Synthetic AUC"},
                {"ascending": True, "metric_name": "Synthetic LogLoss"},
            ],
            "available_metrics": ["Synthetic AUC", "Synthetic LogLoss"],
        }

    else:
        # Pull list of possible metrics
        metrics = project.get_metrics(feature_name=project.target)

    # Capture direction
    ascending = [
        x for x in metrics["metric_details"] if x["metric_name"].startswith(metric)
    ][0]["ascending"]

    # Ensuring we only have models where keys have a value
    models_with_score = [
        model for model in models if model.metrics[metric][partition] is not None
    ]

    # Return sorted models
    return sorted(
        models_with_score,
        key=lambda model: model.metrics[metric][partition],
        reverse=(not ascending),
    )


def _model_cleanup(
    project: dr.models.project.Project,
    model_job_ids: List[str],
    partition: str = "validation",
    metric: str = None,
    max_n_models_to_keep: int = 5,
):
    """
    Sorts supplied models by a requested metric and partition and will keep at most max_n_models_to_keep tuned models

    project: DataRobot project
    partition: string representing which partition to use (see dr.models.model.Model.metrics)
    metric: metric to sort by
    max_n_models_to_keep: maximum number of models to keep

    """

    # Pull updated jobs
    model_jobs = [
        dr.models.job.Job.get(project_id=project.id, job_id=x) for x in model_job_ids
    ]

    # Find the models that were successful
    model_jobs = [
        x for x in model_jobs if x.status == dr.enums.ASYNC_PROCESS_STATUS.COMPLETED
    ]
    models = [x.get_result_when_complete(max_wait=60 * 60 * 24) for x in model_jobs]
    print(f"{len(models)} completed successfully!")

    # Sorting models
    sorted_models = _sort_models(
        project=project, models=models, partition=partition, metric=metric
    )

    # Finding models to delete (if more than <max_n_models_to_keep>)
    n_models = len(sorted_models)
    if n_models > max_n_models_to_keep:
        # Deleting models
        models_to_delete = sorted_models[(max_n_models_to_keep - n_models) :]
        print(f"Deleting {len(models_to_delete)} of {n_models} models...")
        _delete_models(models_to_delete)
        print("Model deletion finished!")


@retry(
    wait=wait_fixed(600),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(lambda x: error_retry_decision(x)),
)
def tuning_hyperparameters(
    model: dr.models.model.Model,
    advanced_tuning_grid: dict,
    partition: str = "validation",
    metric: str = None,
    max_n_models_to_keep: int = 5,
):
    """
    Brute force builds a model for each hyperparameter combination with the ability to delete worst performing models
    Note that if a hyperparameter is shared among tasks, the passed value will be applied to all hyperparameters with a matching name

    model: a DataRobot models
    advanced_tuning_grid: dictionary of hyperparameters to search over
    partition: string representing which partition to use (see dr.models.model.Model.metrics)
    metric: metric to sort by
    max_n_models_to_keep: maximum number of models to keep

    """

    # Get project ID
    project = dr.Project.get(model.project_id)

    # Create list of every possible combination
    keys, values = zip(*advanced_tuning_grid.items())
    hyperparameter_combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
    print(
        f"Number of hyperparameter combinations to evaluate: {len(hyperparameter_combos)}"
    )

    # Pull tuning parameters to pass to model later
    tuning_parameters = model.get_advanced_tuning_parameters()["tuning_parameters"]

    # For each hyperparameter combo, try running the model
    model_job_ids = []
    for hyperparameter_combo in hyperparameter_combos:
        try:
            # Start tuning
            tune = model.start_advanced_tuning_session()

            # Go through each hyperparameter
            for key in hyperparameter_combo.keys():
                # Get id from parameter name
                # This allows you to tune, even when a parameter name is shared
                param_ids = [
                    x["parameter_id"]
                    for x in tuning_parameters
                    if x["parameter_name"] == key
                ]

                # Cycle through parameter IDs (in case there's multiple for a parameter name
                for param_id in param_ids:
                    tune.set_parameter(
                        parameter_name=key,
                        parameter_id=param_id,
                        value=hyperparameter_combo[key],
                    )

            # Execute tuning job
            model_job_ids.append(str(tune.run().id))

            # Sleep to prevent too many API requests at once
            time.sleep(1)

        # If job was already ran, collect the job id
        except dr.errors.JobAlreadyRequested as error:
            if error.json["previousJob"]["status"] == "ABORTED":
                print(
                    f"Combination {hyperparameter_combo} did not complete successfully. Consider running this combination via the GUI."
                )

            else:
                model_job_ids.append(error.json["previousJob"]["id"])

    print(f"Waiting for {len(model_job_ids)} models...")
    model_jobs = [
        dr.models.job.Job.get(project_id=project.id, job_id=x) for x in model_job_ids
    ]
    [x.wait_for_completion(max_wait=60 * 60 * 24) for x in model_jobs]

    # Cleaning things up
    _model_cleanup(
        project=project,
        model_job_ids=model_job_ids,
        partition=partition,
        metric=metric,
        max_n_models_to_keep=max_n_models_to_keep,
    )


######## Bayeisan Optimization ###########


def get_top_of_leaderboard(project, metric="AUC", verbose=True):
    """
    A helper method to assemble a dataframe with leaderboard results and print a summary.
    """
    # list of metrics that get better as their value increases
    desc_metric_list = [
        "AUC",
        "Area Under PR Curve",
        "Gini Norm",
        "Kolmogorov-Smirnov",
        "Max MCC",
        "Rate@Top5%",
        "Rate@Top10%",
        "Rate@TopTenth%",
        "R Squared",
        "FVE Gamma",
        "FVE Poisson",
        "FVE Tweedie",
        "Accuracy",
        "Balanced Accuracy",
        "FVE Multinomial",
        "FVE Binomial",
    ]
    asc_flag = False if metric in desc_metric_list else True

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
            f"validation_{metric}",
            f"cross_validation_{metric}",
        ],
        data=leaderboard,
    )
    leaderboard_top = (
        leaderboard_df[round(leaderboard_df["pct"]) == 64]
        .sort_values(by=f"cross_validation_{metric}", ascending=asc_flag)
        .head()
        .reset_index(drop=True)
    )

    if verbose:
        processes = []
        for bp in project.get_blueprints():
            for p in bp.processes:
                processes.append(p)
        # Print a leaderboard summary:
        print("Unique blueprints tested: " + str(len(leaderboard_df["bp_id"].unique())))
        print(
            "Feature lists tested: " + str(len(leaderboard_df["featurelist"].unique()))
        )
        print("Models trained: " + str(len(leaderboard_df)))
        print(
            "Blueprints in the project repository: "
            + str(len(project.get_blueprints()))
        )
        print("Feature engineering and preprocessing steps ran: ", len(processes))

        # Print key info for top models, sorted by accuracy on validation data:
        print("\n\nTop models in the leaderboard:")
        displayhook(
            leaderboard_top.drop(columns=["bp_id", "featurelist"], inplace=False)
        )

        # # Show blueprints of top models:
        # for index, m in leaderboard_top.iterrows():
        #     Visualize.show_dr_blueprint(dr.Blueprint.get(project.id, m['bp_id']))

    return leaderboard_top


#### BO Tasks #####
# Review Advanced tuning hyperparameters as table


def constraints_unfold(c_dict):
    """Function to unfold nested json with constrants of parameter tuning"""
    ser_ = pd.Series(list(c_dict.values())[0])
    ser_["param_type"] = list(c_dict.keys())[0]
    return ser_


def parameters_to_df(params, keep_duplicates=False):
    """
    function to return tunable paraameters for all blueprint steps from a given modeling blueprint
    inputs: 'params'--> dict - from model.get_advanced_tuning_parameters()
            keep_duplicates-->str,bool, 'first', 'last' or False
    returns: Pandas DataFrame of tunable parameters

    """
    # keep_duplicates is used to drop duplicated parameters that overlap from different tasks of a blueprint.
    # These can be accessed with the task name and paramter_id, and are dropped for this general case

    params = params["tuning_parameters"]
    dat_param = d1 = pd.DataFrame.from_dict(params)
    dat_param = pd.concat(
        [dat_param, dat_param["constraints"].apply(lambda x: constraints_unfold(x))],
        axis=1,
    )
    dat_param.drop(columns=["constraints"], inplace=True)
    dat_param["parameter_name_type"] = (
        dat_param["parameter_name"] + "_" + dat_param["param_type"]
    )
    res = dat_param[
        [
            "task_name",
            "parameter_name",
            "parameter_name_type",
            "current_value",
            "default_value",
            "param_type",
            "supports_grid_search",
            "min",
            "max",
            "values",  #'task_name',
            "parameter_id",
        ]
    ].sort_values("parameter_name_type")
    if keep_duplicates is not None:
        res.drop_duplicates(
            subset="parameter_name_type", keep=keep_duplicates, inplace=True
        )
    return res.reset_index(drop=True).sort_values(by="task_name")


#### Support functions to search the leaderboar for tuned models######
def name_unifier(name):  # needed to fight some legacy in model naming
    reg = re.search("\(.*\)", name)

    if reg:
        span = reg.span()
        name = "".join([name[: span[0]], name[span[1] :]])
    return " ".join(name.split())


def get_models_by_description(
    project, name, sample_pct=None, featurelist_id=None, processes=None
):  # added project
    """
    Searches for similar models by given parameters, this gives an ability to find same models which differ by hyperparameters only.

        Parameters:
            project: DataRobot project where to search for models
            name: filter by similar names that are the same under name_unifier
            sample_pct: filter by amount of data it was trained on
            featurelist_id: filter by feature list was used for training
            processes: filter by processes used in blueprint to match

        Returns:
            list of models that satisfy filters
    """
    models = project.get_models()
    models = [x for x in models if name_unifier(x.model_type) == name]
    if sample_pct is not None:
        models = [x for x in models if x.sample_pct == sample_pct]
    if featurelist_id is not None:
        models = [x for x in models if x.featurelist_id == featurelist_id]
    if processes is not None:
        models = [
            x
            for x in models
            if set([name_unifier(p) for p in x.processes])
            == set([name_unifier(p) for p in processes])
        ]
    return models


def get_models_like(project, mod):  # added project
    """Apply get_models_by_description for particular model
    Params:
        project: DataRobot project
        m: DataRobot model
    Returns:
        list of similar models from get_models_by_description"""

    return get_models_by_description(
        project,
        name_unifier(mod.model_type),
        mod.sample_pct,
        mod.featurelist_id,
        mod.processes,
    )


def get_all_parameters(models, validation_type="crossValidation"):
    """
    Extract all tunable hyperparameters for tuned models along with their performance

        Parameters:
            models: list of tuned models (produced by get_models_like)
            validation_type: reference performance of model

        Returns:
            dataframe with all models and hyperparameters
    """
    all_parameters = []
    for i in models:
        # print(i)
        try:
            prms_temp = parameters_to_df(i.get_advanced_tuning_parameters())
            prms_temp["model_id"] = i.id
            prms_temp["score"] = i.metrics[i.project.metric][
                validation_type
            ]  # project not defined in this helper, used the `m`
            # print(prms_temp)
            all_parameters.append(prms_temp)
        except Exception as e:
            print(e, i.id)
    res_df = None
    # print(f'all_param len is:{len(all_parameters)}')
    if all_parameters:
        res_df = pd.concat(all_parameters)
    return res_df


def get_tuned_parameters(project, model, validation_type):
    """
    Extract only hyperparameters that differ among models - tuned ones

        Params:
            project: DataRobot project
            model: DataRobot model to search similar tuned
            validation_type: reference performance of model

        Returns:
            dataframe with all models and only tuned hyperparameters, record of initial model should appear on top
    """
    mods = get_models_like(project, model)
    print("Similar models found: ", len(mods))
    all_parameters = get_all_parameters(mods, validation_type)
    param_search = all_parameters.groupby("parameter_name_type").apply(
        lambda x: pd.Series({"is_tuned": len(set(x.default_value)) != 1})
    )

    param_search.reset_index(inplace=True)

    list_of_target_parameters = param_search[
        param_search.is_tuned
    ].parameter_name_type.tolist()
    param = None
    if list_of_target_parameters:
        param_space = all_parameters.loc[
            all_parameters.parameter_name_type.isin(
                set(param_search[param_search.is_tuned].parameter_name_type)
            ),
            [
                "parameter_name_type",
                "default_value",
                "current_value",
                "model_id",
                "param_type",
                "score",
            ],
        ].reset_index(drop=True)

        param_pivot = param_space.pivot(
            index="model_id",
            columns="parameter_name_type",
            values=["default_value", "score"],
        )
        score = param_pivot["score"].iloc[:, 0]
        param = param_pivot["default_value"][list_of_target_parameters]
        param[validation_type] = score

    if param is not None:
        param = param.rename_axis(None, axis=1).reset_index()

        # swap record of initial model to first record
        ind_model = np.where(param["model_id"] == model.id)[0][0]
        index = param.index.tolist()
        index[ind_model] = 0
        index[0] = ind_model
        param = param.reindex(index).reset_index(drop=True)
    else:
        print("No tuned models were found")
    return param

from datetime import datetime, timedelta
import os

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook
import datarobot as dr
import datarobot_bp_workshop as bp
from datarobot_kv_helper import DataRobotKeyValueHelper
from datarobot_provider.hooks.datarobot import DataRobotHook
from datarobot_provider.operators.datarobot import ScorePredictionsOperator
from datarobot_provider.sensors.datarobot import ScoringCompleteSensor
import matplotlib.pyplot as plt
from nodes import (
    test_arch,
    test_autocorrelation,
    test_cooks_distance,
    test_normality,
    test_stationarity,
)
import pandas as pd
from pandas.plotting import table


def alert_slack(context: dict):
    last_task: Optional[TaskInstance] = context.get("task_instance")
    dag_id = last_task.dag_id
    task_id = last_task.task_id
    error_message = context.get("exception") or context.get("reason")
    execution_date = context.get("execution_date")
    dag_run = context.get("dag_run")
    task_instances = dag_run.get_task_instances()
    file_and_link_template = "<{log_url}|{name}>"
    failed_tis = [
        file_and_link_template.format(log_url=ti.log_url, name=ti.task_id)
        for ti in task_instances
        if ti.state == "failed"
    ]
    title = (
        f"<@shu.li>\n:red_circle: Dag: *{dag_id}* has failed, with ({len(failed_tis)}) failed tasks"
    )
    messages = {
        "Execution date": execution_date,
        "Failed tasks": ", ".join(failed_tis),
        "Error": error_message,
    }
    message = "\n".join([title, *[f"*{key}*: {value}" for key, value in messages.items()]]).strip()
    SlackWebhookHook(
        webhook_token=SLACK_WEBHOOK,
        message=message,
    ).execute()


def create_custom_task(custom_task_name: str, custom_task_folder: str, custom_task_desc: str = ""):
    datarobot_conn_id = "datarobot_default"
    DataRobotHook(datarobot_conn_id).run()
    transform = dr.CustomTask.create(
        name=custom_task_name,
        target_type="Transform",
        language="python",
        description=custom_task_desc,
    )
    task_version = dr.CustomTaskVersion.create_clean(
        custom_task_id=transform.id,
        base_environment_id="65aabe3fabe8ef70929b4737",
        folder_path=custom_task_folder,
    )
    transform.refresh()


def compose_blueprint(project_id: str, model_id: str = ""):
    datarobot_conn_id = "datarobot_default"
    DataRobotHook(datarobot_conn_id).run()
    client = dr.Client()
    w = bp.Workshop()
    t_test = w.CustomTasks.CUSTOMT_65a9ac05769a6468219b45be(w.TaskInputs.NUM)
    # t_test.set_task_parameters(user_param___column_name='int_rate', user_param___mu=.1)
    resp = client.post(
        "userBlueprintsTaskParameters",
        json={
            "taskCode": "CUSTOMT",
            "outputMethod": "T",
            "projectId": project_id,
            "taskParameters": [
                {"paramName": "np_dtype_fix", "newValue": False},
                {"paramName": "user_param___column_name", "newValue": "int_rate"},
                {"paramName": "user_param___mu", "newValue": ".1"},
                {"paramName": "version_id", "newValue": "65ab0fbc6d209c96789b4600"},
            ],
        },
    )
    # Define the preprocessing path for categorical features
    pdm3 = w.Tasks.PDM3(w.TaskInputs.CAT)  # One-hot encoding
    pdm3.set_task_parameters(cm=50000, sc=10)

    # Define the preprocessing path for numeric features
    ndc = w.Tasks.NDC(w.TaskInputs.NUM)  # Numeric data cleaning
    rdt5 = w.Tasks.RDT5(ndc)  # Smooth ridit transform

    # Define the preprocessing path for text features
    ptm3 = w.Tasks.PTM3(w.TaskInputs.TXT)  # Word-gram occurrence matrix
    ptm3.set_task_parameters(d2=0.2, mxf=20000, d1=5, n="l2", id=True)

    # Define the task relationships
    kerasc = w.Tasks.KERASC(rdt5, t_test, ptm3)
    kerasc_blueprint = w.BlueprintGraph(
        kerasc, name="Custom Keras BP (1 layer: 64 units) with T-test"
    )
    kerasc_blueprint.train(project_id)


def download_artifacts(project_id: str, model_id: str):
    datarobot_conn_id = "datarobot_default"
    DataRobotHook(datarobot_conn_id).run()
    model = dr.Model.get(project_id, model_id)
    model.download_training_artifact("artifact_test.tar.gz")


def stat_tests_arch(fpath: str, title: str, target_column: str):
    df = pd.read_csv(fpath)
    summary = test_arch({title: df}, {"target_column": target_column})
    ax = plt.subplot(111, frame_on=False)  # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    table(ax, summary)  # where df is your data frame
    plt.savefig("./include/test_arch.png")
    return {"test_arch": summary.to_dict()}


def stat_tests_cooks(fpath: str, title: str, target_column):
    df = pd.read_csv(fpath)
    im = test_cooks_distance({title: df}, {"target_column": target_column})
    im.save("include/cooks.png")


def stat_tests_norm(fpath: str, title: str, target_column):
    df = pd.read_csv(fpath)
    summary = test_normality({title: df}, {"target_column": target_column})
    return {"test_normality": summary.to_dict()}


def stat_tests_stationarity(fpath: str, title: str, target_column):
    df = pd.read_csv(fpath)
    summary = test_stationarity({title: df}, {"target_column": target_column})
    return {"test_stationarity": summary.to_dict()}


def stat_tests_autocorrelation(fpath: str, title: str, target_column):
    df = pd.read_csv(fpath)
    summary, im = test_autocorrelation({title: df}, {"target_column": target_column})
    im.save("include/autocorrelation.png")
    return {"test_autocorrelation": summary.to_dict()}


def register_kv(model_package_id: str):
    drkv = DataRobotKeyValueHelper(
        datarobot_uri="https://app.datarobot.com",
        datarobot_token=os.environ.get("DATAROBOT_API_TOKEN"),
        entity_id=model_package_id,
    )
    kv_artifacts = {}
    kv_artifacts["autocorrelation"] = "include/autocorrelation.png"
    kv_artifacts["cooks"] = "include/cooks.png"
    for k, v in kv_artifacts.items():
        drkv.set_artifact(k, v, "image")


def generate_docs(template_id: str, model_package_id):
    doc_type = "AUTOPILOT_SUMMARY"
    file_format = "docx"

    doc = dr.AutomatedDocument(
        document_type="MODEL_COMPLIANCE",
        entity_id=model_package_id,
        output_format="docx",
        locale="EN_US",
        template_id=template_id,
        filepath="include/example.docx",
    )
    doc.generate()
    doc.download()
    print(f"https://staging.datarobot.com/model-registry/model-packages/{model_package_id}")


with DAG(
    dag_id="datarobot_statistical_tests",
    # start_date=datetime(2022,7,28),
    # schedule=timedelta(minutes=30),
    # catchup=False,
    tags=["accelerator"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    on_failure_callback=alert_slack,
):
    title = "LendingClub Loan Default"
    target_column = "is_bad"
    project_id = "657a7c69a2930e16b2ef83a0"
    deployment_id = "657b0f46f3df7e03a1fc728b"
    # t1 = PythonOperator(
    #    task_id="create_statistical_test",
    #    python_callable=create_custom_task,
    #    op_kwargs={
    #        "custom_task_name": 'T-Test',
    #        "custom_task_folder": "./t-test/"
    #    }
    # )
    # t2 = PythonOperator(
    #    task_id='run_t_test',
    #    python_callable=compose_blueprint,
    #    op_kwargs={
    #        "project_id":project_id
    #    }
    # )
    # t3 = PythonOperator(
    #    task_id='download_artifacts',
    #    python_callable=download_artifacts,
    #    op_kwargs={
    #        'project_id':project_id,
    #        'model_id':'65a84eed247c8719f96f14f0',
    #    }
    # )
    # t2 >> t3
    score_predictions_op = ScorePredictionsOperator(
        task_id="score_predictions",
        deployment_id=deployment_id,
        score_settings={
            "intake_settings": {"type": "dataset", "dataset_id": "612d5f31efd8b7c40cf0727c"},
            "output_settings": {
                "type": "localFile",
                "path": "include/10K_LC_predictions.csv",
            },
            "passthrough_columns_set": "all",
        },
    )
    scoring_complete_sensor = ScoringCompleteSensor(
        task_id="check_scoring_complete",
        job_id=score_predictions_op.output,
    )
    t3 = PythonOperator(
        task_id="statistical_tests",
        python_callable=stat_tests_arch,
        op_kwargs={
            "fpath": "include/10K_LC_predictions.csv",
            "title": title,
            "target_column": target_column,
        },
    )
    t4 = PythonOperator(
        task_id="statistical_tests_norm",
        python_callable=stat_tests_norm,
        op_kwargs={
            "fpath": "include/10K_LC_predictions.csv",
            "title": title,
            "target_column": target_column,
        },
    )
    t5 = PythonOperator(
        task_id="statistical_tests_stationarity",
        python_callable=stat_tests_stationarity,
        op_kwargs={
            "fpath": "include/10K_LC_predictions.csv",
            "title": title,
            "target_column": target_column,
        },
    )
    t6 = PythonOperator(
        task_id="statistical_tests_autocorrelation",
        python_callable=stat_tests_autocorrelation,
        op_kwargs={
            "fpath": "include/10K_LC_predictions.csv",
            "title": title,
            "target_column": target_column,
        },
    )
    t7 = PythonOperator(
        task_id="statistical_tests_cooks_distance",
        python_callable=stat_tests_cooks,
        op_kwargs={
            "fpath": "include/10K_LC_predictions.csv",
            "title": "x",
            "target_column": "is_bad",
        },
    )
    register_results = PythonOperator(
        task_id="register_kv",
        python_callable=register_kv,
        op_kwargs={
            "model_package_id": "65a83e8c1ee3ab569914ce95",
        },
    )
    render_docs = PythonOperator(
        task_id="generate_docs",
        python_callable=generate_docs,
        op_kwargs={
            "template_id": "65ac954229b85883b07b3c28",
            "model_package_id": "65a83e8c1ee3ab569914ce95",
        },
    )
    (
        score_predictions_op
        >> scoring_complete_sensor
        >> [t3, t4, t5, t6, t7]
        >> register_results
        >> render_docs
    )

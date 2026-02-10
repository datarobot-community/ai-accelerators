import concurrent.futures
import json
import math
import os

import datarobot as dr
import pandas as pd
import requests
import streamlit as st

# --------------------------------------------------
# ENV VARS & CLIENT INIT
# --------------------------------------------------
DATAROBOT_API_TOKEN = os.environ["DATAROBOT_API_TOKEN"]
DATAROBOT_ENDPOINT = os.environ["DATAROBOT_ENDPOINT"]
client = dr.Client(token=DATAROBOT_API_TOKEN, endpoint=DATAROBOT_ENDPOINT)


# Enable or disable LLM-based capabilities

# Notebook Version
# ENABLE_GENAI = os.environ.get('ENABLE_GENAI', 'FALSE').upper() == 'TRUE'
# if ENABLE_GENAI:
#    import openai
#    import tiktoken
#    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
#    OPENAI_API_VERSION = os.environ["OPENAI_API_VERSION"]
#    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
#    AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
#    azure = openai.AzureOpenAI(
#        api_key=OPENAI_API_KEY,
#        api_version=OPENAI_API_VERSION,
#        azure_endpoint=AZURE_OPENAI_ENDPOINT,
#        azure_deployment=AZURE_OPENAI_DEPLOYMENT
#    )

# App Version
ENABLE_GENAI = (
    os.environ.get("MLOPS_RUNTIME_PARAM_ENABLE_GENAI", "FALSE").upper() == "TRUE"
)
if ENABLE_GENAI:
    import openai
    import tiktoken

    openai_api_key_json = os.environ["MLOPS_RUNTIME_PARAM_OPENAI_API_KEY"]
    OPENAI_API_KEY = json.loads(openai_api_key_json)["payload"]["apiToken"]
    OPENAI_API_VERSION = os.environ["MLOPS_RUNTIME_PARAM_OPENAI_API_VERSION"]
    AZURE_OPENAI_ENDPOINT = os.environ["MLOPS_RUNTIME_PARAM_AZURE_OPENAI_ENDPOINT"]
    AZURE_OPENAI_DEPLOYMENT = os.environ["MLOPS_RUNTIME_PARAM_AZURE_OPENAI_DEPLOYMENT"]
    # Initialize OpenAI for Azure OpenAI
    azure = openai.AzureOpenAI(
        api_key=OPENAI_API_KEY,
        api_version=OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
    )


# Define the sets of capabilities for each model type
# These will be dynamically loaded from config file
STANDARD_CAPS = []
TEXT_GEN_CAPS = []
AGENTIC_CAPS = []

def extract_capabilities_from_config(capability_requirements):
    """
    Extracts all unique capability IDs from the config for each model type.
    Returns sets of capability IDs for Predictive, Generative, and Agentic models.
    """
    standard_caps = set()
    text_gen_caps = set()
    agentic_caps = set()
    
    # Extract from Predictive
    for importance_level in ["Critical", "High", "Moderate", "Low"]:
        for cap in capability_requirements.get("Predictive", {}).get(importance_level, []):
            standard_caps.add(cap["id"])
    
    # Extract from Generative
    for importance_level in ["Critical", "High", "Moderate", "Low"]:
        for cap in capability_requirements.get("Generative", {}).get(importance_level, []):
            text_gen_caps.add(cap["id"])
    
    # Extract from Agentic
    for importance_level in ["Critical", "High", "Moderate", "Low"]:
        for cap in capability_requirements.get("Agentic", {}).get(importance_level, []):
            agentic_caps.add(cap["id"])
    
    return list(standard_caps), list(text_gen_caps), list(agentic_caps)

# --------------------------------------------------
# STREAMLIT PAGE CONFIG & STYLE
# --------------------------------------------------
st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    /* Hide Streamlit's default header and footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# BACKEND PIPELINE: check_deployment_status
# --------------------------------------------------


# Retrieve Capability Requirements Mapping
def load_capability_requirements(path="capability_requirements.json"):
    """
    Reads the JSON file containing the capability requirements
    and returns it as a Python dictionary with separate sections
    for Predictive and Generative models.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot find JSON file: {path}")

    with open(path, "r") as f:
        capability_requirements = json.load(f)

    # Validate the structure
    if not isinstance(capability_requirements, dict):
        raise ValueError(
            "capability_requirements.json must be a dictionary at the top level."
        )

    for model_type in ["Predictive", "Generative", "Agentic"]:
        if model_type not in capability_requirements:
            raise KeyError(
                f"Missing '{model_type}' section in capability_requirements.json."
            )

        for importance_level in ["Critical", "High", "Moderate", "Low"]:
            if importance_level not in capability_requirements[model_type]:
                raise KeyError(
                    f"Missing '{importance_level}' in '{model_type}' section of capability_requirements.json."
                )

            # Ensure each capability entry has 'id' and 'displayName'
            for cap in capability_requirements[model_type][importance_level]:
                if "id" not in cap or "displayName" not in cap:
                    raise KeyError(
                        f"Each capability must have 'id' and 'displayName'. Problematic entry: {cap}"
                    )

    return capability_requirements


# Load config file (can be customized via runtime parameter)
config_file = os.environ.get("MLOPS_RUNTIME_PARAM_CONFIG_FILE", "capability_requirements.json")
capability_requirements = load_capability_requirements(config_file)

# Extract capabilities from config (dynamic based on config file)
STANDARD_CAPS, TEXT_GEN_CAPS, AGENTIC_CAPS = extract_capabilities_from_config(capability_requirements)

# API Helper Functions for Deployment Capabilities


def get_all_deployments(deployment_id=None):
    """
    Retrieves deployments from DataRobot.
    If a deployment_id is provided, returns only that single deployment;
    otherwise returns all deployments.
    """
    if deployment_id:
        try:
            return [dr.Deployment.get(deployment_id)]
        except Exception:
            return []
    else:
        try:
            return dr.Deployment.list()
        except Exception:
            return []


def data_drift(deployment_id):
    """
    Checks whether data drift tracking (target or feature) is enabled.
    """
    try:
        deployment = dr.Deployment.get(deployment_id)
        drift_settings = deployment.get_drift_tracking_settings()
        target_drift_enabled = drift_settings.get("target_drift", {}).get(
            "enabled", False
        )
        feature_drift_enabled = drift_settings.get("feature_drift", {}).get(
            "enabled", False
        )
        return target_drift_enabled or feature_drift_enabled
    except Exception:
        return False


def accuracy_monitoring(deployment_id):
    """
    Checks whether accuracy monitoring is configured for the deployment by looking
    at the association ID settings.
    """
    try:
        deployment = dr.Deployment.get(deployment_id)
        association_id_settings = deployment.get_association_id_settings()
        columns_set = association_id_settings.get("column_names", [])
        required_in_requests = association_id_settings.get(
            "required_in_prediction_requests", False
        )
        return bool(columns_set or required_in_requests)
    except Exception:
        return False


def notifications(deployment_id):
    """
    Checks whether at least one notification policy exists for the deployment.
    """
    try:
        url = f"entityNotificationPolicies/deployment/{deployment_id}/"
        params = {"offset": 0, "limit": 100}
        response = client.get(url, params=params)
        # If status code is 200 and "data" array is non-empty, there is at least one notification policy
        if response.status_code == 200:
            data = response.json().get("data", [])
            return len(data) > 0
        return False
    except Exception:
        return False


def monitoring_job(deployment_id):
    """
    Function to check if there is a monitoring job for a deployment
    """
    monitoring_jobs = dr.BatchMonitoringJobDefinition.list()
    return any(
        getattr(job, "batch_monitoring_job", {}).get("deployment_id") == deployment_id
        for job in monitoring_jobs
    )


def challenger_model(deployment_id):
    """
    Checks if there is at least one challenger model attached to the deployment.
    """
    try:
        url = f"deployments/{deployment_id}/challengers/"
        response = client.get(url)
        if response.status_code == 200:
            data = response.json().get("data", [])
            return len(data) > 0
        return False
    except Exception:
        return False


def retraining_policy(deployment_id):
    """
    Checks if there is a retraining policy for the deployment.
    """
    try:
        url = f"deployments/{deployment_id}/retrainingPolicies/"
        response = client.get(url)
        if response.status_code == 200:
            count = response.json().get("count", 0)
            return count > 0
        return False
    except Exception:
        return False


def custom_metric(deployment_id):
    """
    Checks if there is at least one custom metric attached to the deployment.
    """
    try:
        url = f"deployments/{deployment_id}/customMetrics/"
        response = client.get(url)
        if response.status_code == 200:
            data = response.json().get("data", [])
            return len(data) > 0
        return False
    except Exception:
        return False


def segment_analysis(deployment_id):
    """
    Checks if segment analysis is enabled for the deployment.
    """
    try:
        deployment = dr.Deployment.get(deployment_id)
        segment_analysis_settings = deployment.get_segment_analysis_settings()
        return segment_analysis_settings.get("enabled", False)
    except Exception:
        return False


def humility(deployment_id):
    """
    Checks if humility is enabled for the deployment.
    """
    try:
        url = f"deployments/{deployment_id}/"
        response = client.get(url)
        if response.status_code == 200:
            settings = response.json().get("settings", {})
            return settings.get("humbleAiEnabled", False)
        return False
    except Exception:
        return False


def fairness(deployment_id):
    """
    Checks if fairness/bias monitoring is enabled for the deployment.
    """
    try:
        deployment = dr.Deployment.get(deployment_id)
        fairness_settings = deployment.get_bias_and_fairness_settings()
        if fairness_settings is None:
            return False
        protected_features = fairness_settings.get("protected_features", [])
        fairness_metric_set = fairness_settings.get("fairness_metric_set", None)
        return bool(protected_features or fairness_metric_set)
    except Exception:
        return False


def compliance_report(deployment_id):
    """
    Checks if a MODEL_COMPLIANCE document has been generated (i.e., previously created)
    for the currently active model package used by the given deployment.

    It calls the /api/v2/automatedDocuments endpoint, filtering by:
      - entityId = model_package['id']

    Returns True if one or more matching documents exist, otherwise False.
    """
    try:
        # Get the deployment object
        deployment = dr.Deployment.get(deployment_id)
        # Retrieve the "model package" ID (the model in the registry)
        model_id = deployment.model_package.get("id")
        if not model_id:
            return False
        # Build the endpoint URL (note the /api/v2/automatedDocuments path)
        url = "automatedDocuments"

        # Include filters in query parameters:
        # - entityId=<model_id> (the model for which compliance documents are generated)
        # - offset=0
        # - limit=100 (or however many you need)
        params = {"entityId": model_id, "offset": 0, "limit": 100}
        # Perform the GET request
        response = client.get(url, params=params)
        # If we fail to get a 200 OK, return False
        if response.status_code != 200:
            return False
        # Parse the JSON and examine the "data" array
        data = response.json().get("data", [])
        # If at least one doc is found, return True
        return len(data) > 0
    except Exception:
        return False


def guard_configuration(deployment_id):
    """
    Checks if one or more guard configurations exist for the specified entity
    (e.g., a custom model version) associated with the given deployment.

    This function calls:
      GET /api/v2/guardConfigurations/?entityId=<custom_model_version_id>&entityType=customModelVersion

    Returns:
        - True if at least one guard configuration is found.
        - False if no guard configurations are found or other errors occur.
        - 'NA' if the check couldn't be performed due to insufficient permissions or missing models.
    """
    try:
        # Retrieve the deployment
        deployment = dr.Deployment.get(deployment_id)

        # Extract model package and registered model IDs
        model_package = deployment.model_package
        model_package_id = model_package.get("id")
        reg_model_id = model_package.get("registered_model_id")

        if not reg_model_id:
            return "NA"

        # Fetch the registered model version details
        registered_model_url = (
            f"registeredModels/{reg_model_id}/versions/{model_package_id}/"
        )
        registered_model_resp = client.get(registered_model_url)

        if registered_model_resp.status_code == 404:
            # Registered model not found or access denied
            return "NA"
        elif registered_model_resp.status_code != 200:
            # Other HTTP errors
            return False

        # Parse the registered model details
        reg_model_data = registered_model_resp.json()
        custom_model_details = reg_model_data.get("sourceMeta", {}).get(
            "customModelDetails", {}
        )
        custom_model_id = custom_model_details.get("id")
        version_label = custom_model_details.get("versionLabel")

        if not custom_model_id or not version_label:
            return "NA"

        # Fetch all versions of the custom model
        custom_model_versions_url = f"customModels/{custom_model_id}/versions/"
        custom_model_versions_resp = client.get(custom_model_versions_url)

        if custom_model_versions_resp.status_code != 200:
            return False

        # Identify the custom model version ID matching the version label
        custom_model_versions = custom_model_versions_resp.json().get("data", [])
        custom_model_version_id = next(
            (
                version["id"]
                for version in custom_model_versions
                if version.get("label") == version_label
            ),
            None,
        )

        if not custom_model_version_id:
            return False

        # Fetch guard configurations for the custom model version
        guard_config_url = "guardConfigurations/"
        params = {
            "offset": 0,
            "limit": 100,
            "entityId": custom_model_version_id,
            "entityType": "customModelVersion",
        }
        guard_config_resp = client.get(guard_config_url, params=params)

        if guard_config_resp.status_code != 200:
            return False

        # Determine if at least one guard configuration exists
        guard_configs = guard_config_resp.json().get("data", [])
        return len(guard_configs) > 0

    except dr.errors.APIError as api_err:
        # Handle API-specific errors
        error_message = str(api_err).lower()
        if (
            "registered model not found" in error_message
            or "access denied" in error_message
        ):
            return "NA"
        return False

    except Exception:
        # Handle any other unexpected errors
        return False


def compliance_test(deployment_id):
    """
    Checks if the 'LLM_TEST_SUITE_ID' runtime parameter exists for the model package
    associated with the given deployment.

    Returns:
        - True if 'LLM_TEST_SUITE_ID' is present.
        - False otherwise.
    """
    try:
        # Retrieve the deployment
        deployment = dr.Deployment.get(deployment_id)

        # Extract the model package ID
        model_package_id = deployment.model_package.get("id")
        if not model_package_id:
            return False

        # Construct the endpoint URL for runtime parameters
        url = "keyValues/"
        params = {
            "entityId": model_package_id,
            "entityType": "modelPackage",
            "orderBy": "-createdAt",
            "category": "runtimeParameter",
            "limit": 20,
            "offset": 0,
        }

        # Perform the GET request
        response = client.get(url, params=params)
        if response.status_code != 200:
            return False

        # Parse the response and check for 'LLM_TEST_SUITE_ID'
        data = response.json().get("data", [])
        for param in data:
            if param.get("name") == "LLM_TEST_SUITE_ID":
                return True
        return False

    except Exception:
        # Handle any unexpected errors gracefully
        return False


def tracing(deployment_id):
    """
    Checks if tracing/observability is enabled for agent deployments.
    
    This checks if predictions data collection is enabled, which stores
    incoming prediction requests and results - a fundamental requirement
    for tracing and observability in agent workflows.

    Returns:
        - True if predictions data collection (tracing) is enabled.
        - False otherwise.
    """
    try:
        deployment = dr.Deployment.get(deployment_id)
        
        # Get deployment settings to check predictions data collection
        url = f"deployments/{deployment_id}/settings/"
        response = client.get(url)
        
        if response.status_code == 200:
            settings = response.json()
            
            # Check if predictions data collection is enabled
            # This stores prediction requests and results, enabling tracing
            predictions_data_collection = settings.get("predictionsDataCollection", {})
            if predictions_data_collection.get("enabled", False):
                return True
        
        # Alternative: Check for association ID settings (enables tracking)
        # This is also related to tracing capabilities
        association_id_settings = deployment.get_association_id_settings()
        columns_set = association_id_settings.get("column_names", [])
        required_in_requests = association_id_settings.get(
            "required_in_prediction_requests", False
        )
        if columns_set or required_in_requests:
            return True
        
        return False
        
    except Exception:
        return False


def compute_compliance_score(
    data, capability_requirements, standard_caps, text_gen_caps, agentic_caps
):
    """
    Calculates the compliance score for a deployment.

    Parameters:
    - data: dict with keys 'model_type', 'model_importance', 'checks'
    - capability_requirements: dict loaded from the updated capability_requirements.json
    - standard_caps: list of capability IDs relevant to Predictive models
    - text_gen_caps: list of capability IDs relevant to Generative models
    - agentic_caps: list of capability IDs relevant to Agentic models

    Returns:
    - compliance_score: float representing the compliance percentage
    """

    # 1. Extract model_type and model_importance from data
    model_type = data.get("model_type")
    model_importance = data.get("model_importance") or "Low"
    model_importance = model_importance.capitalize()

    if model_type == "TextGeneration":
        model_type = "Generative"
    elif model_type in ["Agentic", "AgenticWorkflow"]:
        model_type = "Agentic"
    else:
        model_type = "Predictive"

    # 2. Retrieve capabilities based on model_type and model_importance
    if model_type not in capability_requirements:
        # Unknown model_type
        st.warning(
            f"Unknown model_type '{model_type}'. Skipping compliance calculation."
        )
        return 0.0

    mandatory_caps = capability_requirements[model_type].get(model_importance, [])

    if not mandatory_caps:
        # No capabilities required for this model type/importance combination
        # Return 100% compliance (no requirements = fully compliant)
        return 100.0

    # 3. Determine relevant capabilities based on model_type
    if model_type == "Generative":
        relevant_cap_ids = text_gen_caps
    elif model_type == "Agentic":
        relevant_cap_ids = agentic_caps
    else:
        relevant_cap_ids = standard_caps

    # 4. Filter mandatory_caps to include only relevant capabilities
    relevant_mandatory_caps = [
        cap_obj for cap_obj in mandatory_caps if cap_obj["id"] in relevant_cap_ids
    ]

    if not relevant_mandatory_caps:
        # No relevant capabilities required for this model type/importance combination
        # Return 100% compliance (no requirements = fully compliant)
        return 100.0

    # 5. Count enabled mandatory capabilities
    enabled_mandatory = 0
    total_mandatory = len(relevant_mandatory_caps)

    for cap_obj in relevant_mandatory_caps:
        cap_id = cap_obj["id"]
        if data["checks"].get(cap_id) is True:
            enabled_mandatory += 1

    # 6. Compute compliance percentage
    compliance_score = round((enabled_mandatory / total_mandatory) * 100, 2)
    return compliance_score


# Main function to check capabilities for each deployment
def check_deployment_status(deployment_id=None):
    """
    Optimized approach:
      1. Retrieve all deployments (or one, if deployment_id is specified).
      2. Split them by model_type: "TextGeneration", "Agentic" (Agents), vs. others (standard).
      3. For each subset, run concurrency with the relevant checks only.
      4. Merge, compute quality/compliance, and return the results.
    """

    # 1) Retrieve deployments
    deployments = get_all_deployments(deployment_id)

    # 2) Split into text-gen, agentic, and standard
    text_gen_deployments = []
    agentic_deployments = []
    standard_deployments = []
    for dep in deployments:
        target_type = dep.model.get("target_type")
        if target_type == "TextGeneration":
            text_gen_deployments.append(dep)
        elif target_type in ["Agentic", "AgenticWorkflow"]:
            agentic_deployments.append(dep)
        else:
            standard_deployments.append(dep)

    # Define the check sets for standard, text-generation, and agentic
    standard_checks = [
        (data_drift, "data_drift"),
        (accuracy_monitoring, "accuracy_monitoring"),
        (notifications, "notifications"),
        (challenger_model, "challenger_model"),
        (retraining_policy, "retraining_policy"),
        (monitoring_job, "monitoring_job"),
        (custom_metric, "custom_metric"),
        (segment_analysis, "segment_analysis"),
        (humility, "humility"),
        (fairness, "fairness"),
        (compliance_report, "compliance_report"),
    ]
    text_generation_checks = [
        (compliance_report, "compliance_report"),
        (accuracy_monitoring, "accuracy_monitoring"),
        (notifications, "notifications"),
        (guard_configuration, "guard_configuration"),
        (compliance_test, "compliance_test"),
        (custom_metric, "custom_metric"),
    ]
    agentic_checks = [
        (tracing, "tracing"),
        (guard_configuration, "guard_configuration"),
        (notifications, "notifications"),
        (custom_metric, "custom_metric"),
    ]

    # 3) Define helper to run concurrency for a given subset
    def run_checks_for_subset(deps, checks):
        try:
            results_list = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures_map = {}
                for deployment in deps:
                    dep_id = deployment.id
                    model_label = deployment.label
                    model_type = deployment.model.get("target_type", None)

                    # Extract owners
                    model_owners = [
                        owner["email"] for owner in deployment.owners.get("preview", [])
                    ]

                    # Extract importance
                    try:
                        model_importance = deployment.importance
                    except AttributeError:
                        model_importance = "Low"

                    # Create initial results dict
                    results_dict = {
                        "deployment_id": dep_id,
                        "model_label": model_label,
                        "model_type": model_type,
                        "model_owners": model_owners,
                        "model_importance": model_importance,
                        "enabled_capabilities": 0,
                        "checks": {},
                    }

                    # Submit each relevant check
                    for func, check_name in checks:
                        fut = executor.submit(func, dep_id)
                        futures_map[fut] = (check_name, results_dict)

                    results_list.append(results_dict)

                # Collect results
                for fut in concurrent.futures.as_completed(futures_map):
                    check_name, results_dict = futures_map[fut]
                    try:
                        is_enabled = fut.result()  # True/False/'NA'
                        results_dict["checks"][check_name] = is_enabled
                        if is_enabled is True:
                            results_dict["enabled_capabilities"] += 1
                    except Exception:
                        results_dict["checks"][check_name] = False

            return results_list
        except Exception as e:
            # In case there is no deployment
            return []

    # -- Run concurrency for standard, text-gen, and agentic separately
    standard_results = run_checks_for_subset(standard_deployments, standard_checks)
    text_gen_results = run_checks_for_subset(
        text_gen_deployments, text_generation_checks
    )
    agentic_results = run_checks_for_subset(agentic_deployments, agentic_checks)

    # 4) Merge the results
    deployment_status = standard_results + text_gen_results + agentic_results

    # 5) Calculate quality_score & compliance_score for each deployment
    for data in deployment_status:
        # total checks = length of checks dict
        total_checks = len(data["checks"])
        enabled_count = data["enabled_capabilities"]

        if total_checks > 0:
            data["quality_score"] = round((enabled_count / total_checks) * 100, 2)
        else:
            data["quality_score"] = 0.0

        # compliance
        data["compliance_score"] = compute_compliance_score(
            data, capability_requirements, STANDARD_CAPS, TEXT_GEN_CAPS, AGENTIC_CAPS
        )

    return deployment_status


# --------------------------------------------------
# LLM: generate_llm_summary
# --------------------------------------------------
def generate_llm_summary(df, all_caps):
    import tiktoken

    # For the CSV, gather columns
    columns_for_llm = [
        "deployment_id",
        "model_label",
        "model_type",
        "model_importance",
        "enabled_capabilities",
        "quality_score",
        "compliance_score",
    ] + all_caps

    # Ensure columns exist in df
    for col in columns_for_llm:
        if col not in df.columns:
            df[col] = None

    df_for_llm = df[columns_for_llm].copy()

    # Convert boolean columns to int
    for cap in all_caps:
        if cap in df_for_llm.columns:
            df_for_llm[cap] = df_for_llm[cap].astype(int, errors="ignore")

    deployment_data_csv = df_for_llm.to_csv(index=False)

    prompt_template = """
    The following is a CSV data of deployments:

    {deployment_data}

    Columns:
    - deployment_id : Unique ID of the deployment
    - model_label: Name of the model
    - model_type: Type of the model
    - model_importance: The importance of the model (Critical, High, Moderate, Low)
    - enabled_capabilities: Number of capabilities enabled
    - quality_score: Quality score of the deployment
    - compliance_score: Compliance score of the deployment
    - Capabilities: Boolean flags (1 or 0) indicating whether each capability is enabled
    
    You have {total_deployments} deployments in total.

    Provide a brief summary of the current production status and recommend actions to improve deployment quality and compliance.
    """

    # Estimate tokens
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    prompt_without_data = prompt_template.format(
        deployment_data="", total_deployments=0
    )
    prompt_tokens = len(encoding.encode(prompt_without_data))
    data_tokens = len(encoding.encode(deployment_data_csv))

    max_token_limit = 4096
    max_tokens_for_data = max_token_limit - prompt_tokens - 500
    df_included = df_for_llm.copy()

    if data_tokens > max_tokens_for_data:
        # estimate how many rows we can include
        avg_per_row = data_tokens / len(df_for_llm)
        max_rows = int(max_tokens_for_data / avg_per_row)
        df_included = df_included.iloc[:max_rows]
        deployment_data_csv = df_included.to_csv(index=False)
        # st.warning(f"The data has been truncated to {len(df_included)} deployments to fit token limits.")

    trunc_number_deployments = len(df_included)
    prompt = prompt_template.format(
        deployment_data=deployment_data_csv, total_deployments=trunc_number_deployments
    )

    try:
        response = azure.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=AZURE_OPENAI_DEPLOYMENT,
            max_tokens=500,
            temperature=0,
        )
        summary = response.choices[0].message.content.strip()
    except Exception as e:
        summary = f"An error occurred while generating the summary: {e}"

    return summary, deployment_data_csv, trunc_number_deployments


# --------------------------------------------------
# LLM Chatbot
# --------------------------------------------------
def generate_chatbot_response(
    user_question, deployment_data_csv, trunc_number_deployments
):
    prompt = f"""
        The following is a CSV data of deployments:

        {deployment_data_csv}

        Columns:
        - deployment_id : Unique ID of the deployment
        - model_label: Name of the model
        - model_type: Type of the model
        - model_importance: The importance of the model (Critical, High, Moderate, Low)
        - enabled_capabilities: Number of capabilities enabled
        - quality_score: Quality score
        - compliance_score: Compliance score
        - Capabilities: Boolean flags (1 or 0) indicating whether each capability is enabled

        You have {trunc_number_deployments} deployments in total.

        A user asked:
        {user_question}

        As an AI assistant, please provide a concise answer based on the data. If info is not available, say so.
    """
    try:
        response = azure.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"An error occurred while generating the response: {e}"

    return answer


def render_chatbot(deployment_data_csv, trunc_number_deployments):
    with st.expander("Ask Questions About Your Deployments", expanded=False):
        st.markdown("<div class='chatbot-container'>", unsafe_allow_html=True)

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_area("Your question:", height=100)
            submit_button = st.form_submit_button(label="Send")

        if submit_button:
            if user_input:
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input}
                )
                bot_response = generate_chatbot_response(
                    user_input, deployment_data_csv, trunc_number_deployments
                )
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": bot_response}
                )

        chat_history_container = st.container()
        with chat_history_container:
            st.markdown("<div class='chat-history'>", unsafe_allow_html=True)
            for chat in st.session_state.chat_history:
                if chat["role"] == "user":
                    st.markdown(
                        f"<div class='chat-message user-message'>**You:** {chat['content']}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='chat-message bot-message'>**Bot:** {chat['content']}</div>",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------
# CACHE + DATA LOADING
# --------------------------------------------------
@st.cache_data
def load_data():
    """
    Loads the data from the back end pipeline (check_deployment_status).
    Flattens the result into a DataFrame with columns for each capability.
    Also computes LLM summary if ENABLE_GENAI is True.
    """

    # Call the new pipeline
    deployment_list = check_deployment_status()

    # DEBUG: Show checks in Streamlit UI
    # for dep in deployment_list:
    #    st.write(f"**Deployment ID**: {dep['deployment_id']}, **Model Type**: {dep['model_type']}")
    #    st.json(dep['checks'])  # Nicely formatted JSON of the checks

    # Flatten the checks dict
    all_rows = []
    for dep in deployment_list:
        row = {
            "deployment_id": dep["deployment_id"],
            "model_label": dep["model_label"],
            "model_type": dep["model_type"],
            "model_owners": dep["model_owners"],
            "model_importance": dep["model_importance"],
            "enabled_capabilities": dep["enabled_capabilities"],
            "quality_score": dep["quality_score"],
            "compliance_score": dep["compliance_score"],
        }
        # Flatten checks
        for cap_name, value in dep["checks"].items():
            row[cap_name] = value
        all_rows.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)

    # If no deployments returned, handle gracefully
    if df.empty:
        return df, 0, {}, 0, "", "", 0, "", 0

    # Define all possible capabilities from standard, text-generation, and agentic checks
    all_possible_caps = [
        "data_drift",
        "accuracy_monitoring",
        "notifications",
        "challenger_model",
        "retraining_policy",
        "monitoring_job",
        "custom_metric",
        "segment_analysis",
        "humility",
        "fairness",
        "compliance_report",
        "guard_configuration",
        "compliance_test",
        "tracing",
    ]

    # Some stats for entire set
    avg_quality_score = df["quality_score"].mean() if not df.empty else 0
    num_deployments = len(df)
    capability_counts = {}
    for c in all_possible_caps:
        if c in df.columns:
            # Count how many True
            capability_counts[c] = df[c].sum() if df[c].dtype != object else 0
        else:
            capability_counts[c] = 0

    # For LLM summary
    if ENABLE_GENAI:
        (
            summary_text,
            deployment_data_csv,
            trunc_number_deployments,
        ) = generate_llm_summary(df, all_possible_caps)
    else:
        summary_text, deployment_data_csv, trunc_number_deployments = "", "", 0

    return (
        df,
        avg_quality_score,
        capability_counts,
        num_deployments,
        summary_text,
        all_possible_caps,
        trunc_number_deployments,
        deployment_data_csv,
    )


# --------------------------------------------------
# UI STYLING
# --------------------------------------------------
css_style = """
<style>
/* General App Styling */
.stApp {
    background-color: #0a0a0a;
    color: #e0e0e0;
}
header, footer {
    visibility: hidden;
}
/* Header Boxes */
.header-box {
    background: linear-gradient(135deg, #1a0f2e 0%, #2d1b4e 100%);
    border: 1px solid #8b5cf6;
    border-radius: 12px;
    padding: 10px;
    color: #ffffff;
    text-align: left;
    width: 100%;
    height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    margin-bottom: 8px;
    box-shadow: 0 4px 6px rgba(139, 92, 246, 0.2);
}
.header-box p {
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    color: #a78bfa;
    margin: 0;
}
.header-box h3 {
    font-size: 22px;
    margin: 5px 0;
    color: #ffffff;
}
.header-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: start;
    margin-bottom: 15px;
    max-width: 100%;
}
.deployment-table {
    background-color: #0f0f0f;
    border: 1px solid #8b5cf6;
    border-radius: 12px;
    padding: 10px;
    box-shadow: 0 4px 6px rgba(139, 92, 246, 0.15);
}
.table-header {
    display: flex;
    justify-content: space-between;
    font-weight: bold;
    color: #a78bfa;
    padding: 6px 0;
    border-bottom: 2px solid #8b5cf6;
}
.table-row {
    display: flex;
    justify-content: flex-start;
    padding: 6px 0;
    border-bottom: 1px solid #2d1b4e;
    flex-wrap: nowrap;
    gap: 8px; 
}
.table-row:hover {
    background-color: #1a0f2e;
    border-radius: 6px;
}
.table-header div,
.table-row div {
    overflow: hidden;
    white-space: wrap;
}
.capabilities-container {
    display: flex;
    flex-wrap: wrap;
}
.capabilities-line {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
}
.capability-item {
    margin-right: 8px;
    font-size: 12px;
}
.deployment-link {
    font-size: 11px;
    color: #a78bfa;
    text-decoration: none;
    font-weight: 500;
}
.deployment-link:hover {
    color: #c4b5fd;
    text-decoration: underline;
}
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
/* LLM Summary Styling */
.llm-summary {
    background: linear-gradient(135deg, #1a0f2e 0%, #2d1b4e 100%);
    border: 1px solid #8b5cf6;
    padding: 15px;
    border-radius: 12px;
    color: #e0e0e0;
    margin-bottom: 20px;
    max-height: 200px;
    overflow-y: auto;
}
/* Chatbot Styling */
.chatbot-container {
    background: linear-gradient(135deg, #1a0f2e 0%, #2d1b4e 100%);
    border: 1px solid #8b5cf6;
    padding: 15px;
    border-radius: 12px;
    color: #e0e0e0;
    margin-bottom: 20px;
}
.chat-history {
    max-height: 400px; 
    overflow-y: auto;
    margin-bottom: 10px;
}
.chat-message {
    margin-bottom: 10px;
}
.user-message {
    color: #a78bfa;
}
.bot-message {
    color: #e0e0e0;
}
/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid #8b5cf6 !important;
}
.css-1d391kg, .css-1n76uvr, .css-16huue1 {
    color: #ffffff !important;
}
.css-1d391kg input, .css-1n76uvr input {
    background-color: #1a0f2e !important;
    color: #ffffff !important;
    border: 1px solid #8b5cf6 !important;
    height: 30px !important;
    font-size: 12px !important;
}
.css-1d391kg label, .css-1n76uvr label {
    color: #a78bfa !important;
    font-weight: bold;
    font-size: 13px !important;
}
[data-baseweb="select"] > div {
    background-color: #1a0f2e !important;
    color: #ffffff !important;
    border: 1px solid #8b5cf6 !important;
    min-height: 30px !important;
}
[data-baseweb="select"] .css-1dimb5e-singleValue {
    color: #ffffff !important;
    font-size: 12px !important;
}
.css-1aumxhk {
    color: #ffffff !important;
}
.css-1djdyxw {
    color: #ffffff !important;
    font-size: 12px !important;
}
.css-14k83za .css-1gv0vcd {
    height: 4px !important;
}
section[data-testid="stSidebar"] [data-baseweb="slider"] * {
    color: #a78bfa !important;
}
/* Button Styling */
button[kind="primary"] {
    background-color: #8b5cf6 !important;
    color: #ffffff !important;
    border: none !important;
}
button[kind="primary"]:hover {
    background-color: #7c3aed !important;
}
/* Heading Colors */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
}
/* Expander Styling */
.streamlit-expanderHeader {
    background-color: #1a0f2e !important;
    border: 1px solid #8b5cf6 !important;
    border-radius: 8px !important;
    color: #a78bfa !important;
}
</style>
"""
st.markdown(css_style, unsafe_allow_html=True)


# --------------------------------------------------
# Helpers for RENDERING Functions
# --------------------------------------------------
def get_display_name(model_type):
    """
    Retrieves the displayName for a given capability based on model_type.
    """
    importance_levels = ["Critical", "High", "Moderate", "Low"]

    # Build cap_id to displayName mapping
    cap_id_to_display = {}
    for level in importance_levels:
        caps = capability_requirements.get(model_type, {}).get(level, [])
        for cap in caps:
            cap_id = cap.get("id")
            if cap_id and cap_id not in cap_id_to_display:
                cap_id_to_display[cap_id] = cap.get(
                    "displayName", cap_id.replace("_", " ").title()
                )
    return cap_id_to_display


# --------------------------------------------------
# RENDERING: HEADERS
# --------------------------------------------------
def render_header_boxes(df, title_text):
    """
    Render a single row of header boxes for the given DataFrame subset (e.g. standard or textgen).
    """
    # If empty subset, show 0 in metrics
    if df.empty:
        num_deployments = 0
        avg_quality_score = 0.0
        avg_compliance_score = 0.0
    else:
        num_deployments = len(df)
        avg_quality_score = df["quality_score"].mean()
        avg_compliance_score = df["compliance_score"].mean()

    # Calculate total or average
    st.markdown(
        f"<h4 style='margin-bottom:5px;'>{title_text}</h4>", unsafe_allow_html=True
    )
    cols = st.columns(3)
    # 1) Number of Deployments
    cols[0].markdown(
        f"<div class='header-box'><p>Number of Deployments</p><h3>{num_deployments}</h3></div>",
        unsafe_allow_html=True,
    )
    # 2) Avg Quality
    cols[1].markdown(
        f"<div class='header-box'><p>Average Quality Score</p><h3>{avg_quality_score:.2f}%</h3></div>",
        unsafe_allow_html=True,
    )
    # 3) Avg Compliance
    cols[2].markdown(
        f"<div class='header-box'><p>Average Compliance Score</p><h3>{avg_compliance_score:.2f}%</h3></div>",
        unsafe_allow_html=True,
    )


def render_model_capability_summary(
    df, model_type, capabilities, capability_requirements
):
    """
    Displays a row of boxes for the given model_type,
    showing the percentage of deployments with each capability enabled.
    """
    # Get the display name mapping
    cap_id_to_display = get_display_name(model_type)

    # Aggregate capability usage
    capability_usage = {
        cap: df[cap].sum() if cap in df.columns else 0 for cap in capabilities
    }

    # Create Streamlit columns
    cols = st.columns(len(capabilities))
    for i, cap in enumerate(capabilities):
        display_name = cap_id_to_display.get(cap, "N/A")
        total = len(df)
        enabled = capability_usage.get(cap, 0)
        pct = (enabled / total) * 100 if total > 0 else 0

        cols[i].markdown(
            f"""
            <div class='header-box'>
                <p>{display_name}</p>
                <h3>{pct:.1f}%</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# LLM SUMMARY
# --------------------------------------------------
def render_llm_summary(summary_text):
    with st.expander("Summary and Recommendations", expanded=False):
        st.markdown(
            f"<div class='llm-summary'>{summary_text}</div>", unsafe_allow_html=True
        )


# --------------------------------------------------
# Critical Capabilities
# --------------------------------------------------
def render_critical_capabilities(capability_requirements):
    """
    Displays capability requirements for all four importance levels
    in separate sections for Predictive and Generative models.
    Each list item is expected to be an object like:
      { "id": "data_drift", "displayName": "Data Drift" }
    """

    with st.expander("View governance rules", expanded=False):
        st.markdown("<h4>Governance Rules</h4>", unsafe_allow_html=True)

        # Define the model types
        model_types = ["Predictive", "Generative", "Agentic"]
        display_names = {"Predictive": "Predictive Models", "Generative": "Generative Models", "Agentic": "Agents"}

        for model_type in model_types:
            st.markdown(f"### {display_names.get(model_type, model_type)}")

            # Define the known importance levels in desired order:
            importance_levels = ["Critical", "High", "Moderate", "Low"]
            cols = st.columns(4)
            columns = cols  # Assuming 4 importance levels

            for i, level_name in enumerate(importance_levels):
                with columns[i]:
                    # Title for this level
                    st.markdown(f"#### {level_name}")

                    # Retrieve the list of capability objects
                    capability_objects = capability_requirements[model_type].get(
                        level_name, []
                    )

                    if not capability_objects:
                        st.write("No capabilities listed.")
                        continue

                    # Display each capability's displayName as a bullet
                    for cap_obj in capability_objects:
                        disp_name = cap_obj.get("displayName", "Unknown Capability")
                        st.markdown(f"* {disp_name}")

            st.markdown("---")  # Separator between model types


# --------------------------------------------------
# TABLE
# --------------------------------------------------


def render_status_icon(status, caption):
    """
    Renders an emoji icon for capability status: True => "✅", False => "❌", "NA" => "❔"
    """
    if status is True:
        icon = "✅"
    elif status == "NA":
        icon = "❔"
    else:
        icon = "❌"
    return f"<span class='capability-item'>{icon} {caption}</span>"


def render_table_header():
    """
    Renders the table header row with columns:
    Deployment | Type | Importance | Owners | Quality | Compliance | Capabilities
    """
    st.markdown("<div class='deployment-table'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='table-header'>
            <div style="width: 18%">Deployment</div>
            <div style="width: 11%">Type</div>
            <div style="width: 11%">Risk Level</div>
            <div style="width: 14%">Owners</div>
            <div style="width: 7%; text-align: center;">Quality</div>
            <div style="width: 7%; text-align: center;">Compliance</div>
            <div style="width: 32%; text-align: center;">Capabilities</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_table_row(
    deployment, capabilities_line1, capabilities_line2, capabilities_line3=""
):
    """
    Renders a single row for the given deployment.
    capabilities_line1, capabilities_line2, and capabilities_line3
    are HTML strings of icons for each line of capabilities.
    """
    owners = "<br>".join(deployment["model_owners"])
    deployment_id = deployment["deployment_id"]
    base_url = DATAROBOT_ENDPOINT.rstrip('/').split('/api/')[0]
    deployment_url = f"{base_url}/console-nextgen/deployments/{deployment_id}/overview"
    deployment_link = f"<a href='{deployment_url}' target='_blank' class='deployment-link'>View Deployment</a>"

    deployment_label_html = f"""
    <div>
        <span>{deployment['model_label']}</span><br>
        {deployment_link}
    </div>
    """

    # Build capabilities HTML with proper handling of empty third line
    capabilities_html_parts = [
        f"<div class='capabilities-line'>{capabilities_line1}</div>",
        f"<div class='capabilities-line'>{capabilities_line2}</div>"
    ]
    
    # Only add third line if it has content
    if capabilities_line3 and capabilities_line3.strip():
        capabilities_html_parts.append(f"<div class='capabilities-line'>{capabilities_line3}</div>")
    
    capabilities_html = "\n".join(capabilities_html_parts)
    
    html = f"""
        <div class='table-row'>
            <div style="width: 18%;">{deployment_label_html}</div>
            <div style="width: 11%;">{deployment['model_type']}</div>
            <div style="width: 11%;">{deployment['model_importance']}</div>
            <div style="width: 14%; font-size: 12px; color: #a0a0a0;">{owners}</div>
            <div style="width: 7%; text-align: center;">
                <strong>{deployment['quality_score']}%</strong>
            </div>
            <div style="width: 7%; text-align: center;">
                <strong>{deployment['compliance_score']}%</strong>
            </div>
            <div class='capabilities-container' style="width: 32%; text-align: center;">
                {capabilities_html}
            </div>
        </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


def render_deployment_table(
    df, page_number=1, page_size=10, capability_requirements={}
):
    """
    Renders a paginated table of deployments, showing only the relevant capabilities
    for each model type (Predictive vs. Generative), using 'displayName' from JSON.
    """

    if df.empty:
        st.write("No deployments to display.")
        return

    # Pagination
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size
    df_page = df.iloc[start_index:end_index]

    # Render header
    render_table_header()

    # For each deployment in the current page, figure out which capabilities to display
    for _, deployment in df_page.iterrows():
        # Decide whether standard, text-gen, or agentic
        if deployment["model_type"] == "TextGeneration":
            caps_for_model = TEXT_GEN_CAPS
            mapped_model_type = "Generative"
        elif deployment["model_type"] in ["Agentic", "AgenticWorkflow"]:
            caps_for_model = AGENTIC_CAPS
            mapped_model_type = "Agentic"
        else:
            caps_for_model = STANDARD_CAPS
            mapped_model_type = "Predictive"

        # Get the display name mapping
        cap_id_to_display = get_display_name(mapped_model_type)

        # Split them into three lines
        total_caps = len(caps_for_model)
        chunk_size = math.ceil(total_caps / 3)

        caps_line1 = caps_for_model[:chunk_size]
        caps_line2 = caps_for_model[chunk_size : 2 * chunk_size]
        caps_line3 = caps_for_model[2 * chunk_size :]

        # Build HTML for each line using displayName from mapping
        line1_html = " ".join(
            render_status_icon(
                deployment.get(cap, False),
                cap_id_to_display.get(cap, cap.replace("_", " ").title()),
            )
            for cap in caps_line1
        )
        line2_html = " ".join(
            render_status_icon(
                deployment.get(cap, False),
                cap_id_to_display.get(cap, cap.replace("_", " ").title()),
            )
            for cap in caps_line2
        )
        line3_html = " ".join(
            render_status_icon(
                deployment.get(cap, False),
                cap_id_to_display.get(cap, cap.replace("_", " ").title()),
            )
            for cap in caps_line3
        )

        # Render the row with capability display names
        render_table_row(deployment, line1_html, line2_html, line3_html)

    st.markdown("</div>", unsafe_allow_html=True)  # closes .deployment-table


# --------------------------------------------------
# FILTERS
# --------------------------------------------------
def render_filters(df):
    st.sidebar.markdown("### Filter Deployments")

    # Refresh data
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Model type includes "TextGeneration" or "Binary", etc.
    types = sorted(df["model_type"].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect("Select Types", options=types, default=[])

    excluded_types = st.sidebar.multiselect("Exclude Types", options=types, default=[])

    # Model importance
    importances = sorted(df["model_importance"].dropna().unique().tolist())
    selected_importances = st.sidebar.multiselect(
        "Select Importance", options=importances, default=[]
    )
    excluded_importances = st.sidebar.multiselect(
        "Exclude Importance", options=importances, default=[]
    )

    # Owners
    all_owners = sorted(
        set(owner for owners_list in df["model_owners"] for owner in owners_list)
    )
    selected_owners = st.sidebar.multiselect(
        "Select Owners", options=all_owners, default=[]
    )
    excluded_owners = st.sidebar.multiselect(
        "Exclude Owners", options=all_owners, default=[]
    )

    # Quality score range
    min_quality, max_quality = 0, 100
    quality_range = st.sidebar.slider(
        "Quality Score", min_value=min_quality, max_value=max_quality, value=(0, 100)
    )

    # Compliance score range
    compliance_range = st.sidebar.slider(
        "Compliance Score", min_value=min_quality, max_value=max_quality, value=(0, 100)
    )

    # Capabilities filter
    all_caps_cols = [
        c
        for c in df.columns
        if c
        not in [
            "deployment_id",
            "model_label",
            "model_type",
            "model_owners",
            "model_importance",
            "enabled_capabilities",
            "quality_score",
            "compliance_score",
        ]
    ]
    selected_capabilities = st.sidebar.multiselect(
        "Must Have Capabilities", options=all_caps_cols, default=[]
    )
    excluded_capabilities = st.sidebar.multiselect(
        "Exclude Capabilities", options=all_caps_cols, default=[]
    )

    # Deployment name search
    search_term = st.sidebar.text_input("Deployment Name Search")

    # Apply filters
    filtered_df = df.copy()
    if selected_types:
        filtered_df = filtered_df[filtered_df["model_type"].isin(selected_types)]
    if excluded_types:
        filtered_df = filtered_df[~filtered_df["model_type"].isin(excluded_types)]

    if selected_importances:
        filtered_df = filtered_df[
            filtered_df["model_importance"].isin(selected_importances)
        ]
    if excluded_importances:
        filtered_df = filtered_df[
            ~filtered_df["model_importance"].isin(excluded_importances)
        ]

    if selected_owners:
        filtered_df = filtered_df[
            filtered_df["model_owners"].apply(
                lambda owners_list: any(o in owners_list for o in selected_owners)
            )
        ]
    if excluded_owners:
        filtered_df = filtered_df[
            ~filtered_df["model_owners"].apply(
                lambda owners_list: any(o in owners_list for o in excluded_owners)
            )
        ]

    filtered_df = filtered_df[
        (filtered_df["quality_score"] >= quality_range[0])
        & (filtered_df["quality_score"] <= quality_range[1])
    ]

    filtered_df = filtered_df[
        (filtered_df["compliance_score"] >= compliance_range[0])
        & (filtered_df["compliance_score"] <= compliance_range[1])
    ]

    for cap in selected_capabilities:
        if cap in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[cap] == True]

    for cap in excluded_capabilities:
        if cap in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[cap] == False]

    if search_term:
        filtered_df = filtered_df[
            filtered_df["model_label"].str.contains(search_term, case=False, na=False)
        ]

    return filtered_df


# --------------------------------------------------
# PAGINATION
# --------------------------------------------------
def render_page_selector(df, page_size_default=10):
    total_records = len(df)
    total_pages = (
        math.ceil(total_records / page_size_default) if total_records > 0 else 1
    )

    st.markdown("<h2>Deployments</h2>", unsafe_allow_html=True)
    content_col, spacer_col_right = st.columns([0.3, 0.7])

    with content_col:
        col_page, col_page_size = st.columns([1, 1])
        with col_page:
            page_number = st.number_input(
                f"Page (1 - {total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
            )
            st.write(f"Page {page_number} of {total_pages}")

        with col_page_size:
            page_size = st.selectbox(
                "Page Size",
                options=[5, 10, 20, 50, 100],
                index=[5, 10, 20, 50, 100].index(page_size_default)
                if page_size_default in [5, 10, 20, 50, 100]
                else 1,
            )

    return int(page_number), int(page_size)


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    (
        df,
        avg_quality_score,
        capability_counts,
        num_deployments,
        summary_text,
        all_possible_caps,
        trunc_number_deployments,
        deployment_data_csv,
    ) = load_data()

    # Render filters
    filtered_df = render_filters(df)

    # Render three sets of header boxes: Predictive, Generative, and Agents
    predictive_df = filtered_df[
        (filtered_df["model_type"] != "TextGeneration") 
        & (filtered_df["model_type"] != "Agentic")
        & (filtered_df["model_type"] != "AgenticWorkflow")
    ]
    generative_df = filtered_df[filtered_df["model_type"] == "TextGeneration"]
    agentic_df = filtered_df[filtered_df["model_type"].isin(["Agentic", "AgenticWorkflow"])]

    # Show sections only for model types with defined capabilities
    if STANDARD_CAPS:  # Only show Predictive if capabilities are defined
        render_header_boxes(predictive_df, "Predictive Models")
        render_model_capability_summary(
            df=predictive_df,
            model_type="Predictive",
            capabilities=STANDARD_CAPS,
            capability_requirements=capability_requirements,
        )

    if TEXT_GEN_CAPS:  # Only show Generative if capabilities are defined
        render_header_boxes(generative_df, "Generative Models")
        render_model_capability_summary(
            df=generative_df,
            model_type="Generative",
            capabilities=TEXT_GEN_CAPS,
            capability_requirements=capability_requirements,
        )

    if AGENTIC_CAPS:  # Only show Agentic if capabilities are defined
        render_header_boxes(agentic_df, "Agents")
        render_model_capability_summary(
            df=agentic_df,
            model_type="Agentic",
            capabilities=AGENTIC_CAPS,
            capability_requirements=capability_requirements,
        )

    # Optionally show LLM summary & chatbot if enabled
    if ENABLE_GENAI:
        render_llm_summary(summary_text)
        render_chatbot(deployment_data_csv, trunc_number_deployments)

    # Render the critical capabilities
    render_critical_capabilities(capability_requirements)

    # Render the paginated deployment table
    page_number, page_size = render_page_selector(filtered_df, page_size_default=10)
    render_deployment_table(
        filtered_df, page_number, page_size, capability_requirements
    )


if __name__ == "__main__":
    main()

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import logging
import os
import traceback
from typing import Dict, List, Tuple, Union

import datarobot as dr
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import streamlit as st

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 10


def generate_data_prep_code(
    datasets_info, selected_issues, user_instructions, failed_code=None, error_msg=None
):
    sytem_prompt = f"""
    ROLE:
    You are a data cleaning assistant. 
    Write Python code using pandas, numpy, scikit-learn, etc. to fix these data quality improvements specified.
    You will be provided with metadata about the datasets including:
    - Summary statistics for each column
    - Data types of each column
    - Number of unique values in each column
    - Sample values from each column
    - Dataset dimensions
    
    Your job is to write a python function that will take the datasets as input and return the cleaned datasets.
    The response of your function should be a list of dataframes.

    The user will provide:
    1. A dictionary of dataframes (dfs) where keys are dataset names and values are the dataframes
    2. Metadata that describes the columns and statistics across all dataframes

    FORMAT:
    Your response should be a JSON object with the following keys:
    "code": The Python code to fix the data quality issues.       

    EXAMPLE CODE:
    def prepare_data(dfs):
        import pandas as pd
        import numpy as np
        # High level explanation 
        # of what the code does
        # should be included at the top of the function
        
        # Access individual dataframes by name
        df = dfs['dataset_name']  # Access specific dataset
        
        # Perform data prep / cleansing operations
        # Join/merge datasets if needed
        # Compute metrics and aggregations
        
        return list_of_dfs
    
    ERROR MESSAGE:
    It's possible that the code will fail to run for any number of reasons. 
    If the code fails, we will pass you back the failed code as well as the error message. 
    You should review that code and the error message and then generate a new code that fixes the error.
    """

    # Log the user messages with structured metadata
    logger.info("\n=== Generating Data Preparation Code ===")
    logger.info("Dataset Metadata:")
    for dataset_name, metadata in datasets_info.items():
        logger.info(f"\nDataset: {dataset_name}")
        logger.info(f"Shape: {metadata['shape']}")
        logger.info("Columns:")
        for col, col_info in metadata["columns"].items():
            logger.info(f"  {col}: {col_info['dtype']} ({col_info['unique_count']} unique values)")

    logger.info("\nSelected Issues:")
    logger.info(f"{selected_issues}")
    logger.info("\nUser Instructions:")
    logger.info(f"{user_instructions}")

    if failed_code and error_msg:
        logger.info("\nPrevious Attempt Failed:")
        logger.info(f"Error Message: {error_msg}")
        logger.info("Failed Code:")
        logger.info(f"{failed_code}")

    dr_client = dr.Client(
        token=os.getenv("DATAROBOT_API_TOKEN"), endpoint=os.getenv("DATAROBOT_ENDPOINT")
    )
    chat_agent_deployment_id = os.getenv("CHAT_AGENT_DEPLOYMENT_ID")
    deployment_chat_base_url = dr_client.endpoint + f"/deployments/{chat_agent_deployment_id}/"
    client = OpenAI(
        api_key=dr_client.token,
        base_url=deployment_chat_base_url,
        timeout=90,
        max_retries=2,
    )

    completion = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": sytem_prompt},
            {
                "role": "user",
                "content": f"""
            CONTEXT DATA:
            Here is some information about the datasets:\n{datasets_info}\n
            Here is a list of the data munging tasks that must be implemented:\n{selected_issues}\n
            Additional instructions:\n{user_instructions}\n
            Generate Python code using pandas, numpy, scikit-learn, etc. to implement these requests.
            """,
            },
            {
                "role": "user",
                "content": f"""
            ERROR MESSAGE:
            {error_msg}
            """,
            },
            {
                "role": "user",
                "content": f"""
            FAILED CODE:
            {failed_code}
            """,
            },
        ],
    )

    generated_code = json.loads(completion.choices[0].message.content)

    # Store the generated code in session state
    st.session_state["generated_code"] = generated_code

    # Log the generated code
    logger.info("\nGenerated Code:")
    logger.info(f"{generated_code['code']}")
    logger.info("=" * 50)

    return generated_code


def execute_data_prep_code(
    generated_code: Dict[str, str], dfs: Dict[str, pd.DataFrame]
) -> Union[List[pd.DataFrame], Tuple[str, str]]:
    """
    Execute the generated data preparation code and return the cleaned dataframes.

    Args:
        generated_code (Dict[str, str]): JSON object containing the generated code under 'code' key
        dfs (Dict[str, pd.DataFrame]): Dictionary of input dataframes

    Returns:
        Union[List[pd.DataFrame], Tuple[str, str]]: Either a list of cleaned dataframes or a tuple of (code, error_message)
    """
    logger.info("\n=== Executing Data Preparation Code ===")

    # Extract the function code from the JSON response
    try:
        function_code = generated_code["code"]
        logger.debug("Extracted function code successfully")
    except KeyError as e:
        error_msg = "Generated code JSON missing 'code' key"
        logger.error(f"\nError: {error_msg}")
        logger.error("=" * 50)
        return function_code, error_msg

    # Capture stdout and stderr
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        # Import required libraries
        import numpy as np
        from scipy import stats
        import sklearn

        namespace = {
            "pd": pd,
            "np": np,
            "numpy": np,
            "sklearn": sklearn,
            "stats": stats,
            "dfs": dfs,
        }

        # Execute the function definition
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(function_code, namespace)
            logger.info("Successfully defined prepare_data function")

            prepare_data = namespace["prepare_data"]
            logger.info("Executing prepare_data function...")
            result = prepare_data(dfs)

            # Validate the result
            if not isinstance(result, list) or not all(
                isinstance(df, pd.DataFrame) for df in result
            ):
                error_msg = "prepare_data function did not return a list of dataframes"
                logger.error(f"\nValidation Error: {error_msg}")
                logger.error("=" * 50)
                return function_code, error_msg

            logger.info(f"Successfully processed {len(result)} dataframes")
            logger.info("=" * 50)
            return result

    except Exception as e:
        error_msg = f"Error executing data preparation code:\n{traceback.format_exc()}"
        logger.error("\nExecution Error:")
        logger.error(error_msg)

        # Log captured output
        if stdout.getvalue():
            logger.debug("\nFunction stdout:")
            logger.debug(stdout.getvalue())
        if stderr.getvalue():
            logger.debug("\nFunction stderr:")
            logger.debug(stderr.getvalue())

        logger.error("=" * 50)
        return function_code, error_msg

    finally:
        stdout.close()
        stderr.close()


def generate_and_execute_data_prep(
    datasets_info: Dict[str, Dict],  # This is the metadata
    selected_issues: Dict[str, List[str]],
    user_instructions: str,
) -> Union[List[pd.DataFrame], Tuple[str, str]]:
    """
    Generate and execute data preparation code with retry logic.

    Args:
        datasets_info: Dictionary of dataset metadata
        selected_issues: Dictionary of issues to fix for each dataset
        user_instructions: Additional user instructions for data preparation

    Returns:
        Either a list of processed dataframes or a tuple of (failed_code, error_message)
    """
    attempt = 1
    failed_code = None
    error_msg = None

    logger.info("\n=== Starting Data Preparation Process ===")

    while attempt <= MAX_ATTEMPTS:
        logger.info(f"\nAttempt {attempt} of {MAX_ATTEMPTS}")
        logger.info("-" * 50)

        # Generate the code
        generated_code = generate_data_prep_code(
            datasets_info=datasets_info,
            selected_issues=selected_issues,
            user_instructions=user_instructions,
            failed_code=failed_code,
            error_msg=error_msg,
        )

        # Execute the generated code with the actual dataframes from session state
        result = execute_data_prep_code(
            generated_code, st.session_state["datasets"]
        )  # Use actual dataframes here

        # If successful, return the processed dataframes
        if isinstance(result, list):
            logger.info(f"\nSuccess: Data processing completed on attempt {attempt}")
            logger.info("=" * 50)
            return result

        # If failed, prepare for next attempt
        failed_code, error_msg = result
        logger.warning(f"\nAttempt {attempt} failed")
        logger.warning(f"Error: {error_msg}")

        attempt += 1

    # If we've exceeded max attempts, return the last failure
    logger.error(f"\nFailed to process data after {MAX_ATTEMPTS} attempts")
    logger.error("=" * 50)
    return failed_code, error_msg

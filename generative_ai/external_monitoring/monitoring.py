import functools
import time
import json
import asyncio
from typing import Any, Callable, Dict, Optional, Awaitable
import pandas as pd
from datarobot_mlops.common.config import ConfigConstants, set_config
from datarobot_mlops.mlops import MLOps
from uuid import uuid4


def dr_monitor(
    deployment_id: str,
    model_id: str,
    datarobot_api_token: str,
    datarobot_endpoint: str,
    prompt_feature_name: Optional[str] = "promptText",
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    decorator to monitor the performance of an async function that uses a DataRobot model.

    Parameters:
    -----------
    deployment_id : str
        The ID of the DataRobot deployment.
    model_id : str
        The ID of the DataRobot model.
    datarobot_api_token : str
        The API token for DataRobot.
    datarobot_endpoint : str
        The endpoint URL for the DataRobot API.

    Returns:
    --------
    Callable
        The decorated function.

    Example:
    --------
    @dr_monitor(deployment_id="abc123", model_id="def456",
                datarobot_api_token="YOUR_TOKEN", datarobot_endpoint="https://app.datarobot.com/api/v2")
    async def predict_function(data):
        # Your async prediction code here
        return result
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result = None
            error = None

            try:
                # Execute the async function
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                error = str(e)
                success = False
                raise
            finally:
                # Calculate execution time
                execution_time = time.time() - start_time
                set_config(ConfigConstants.MLOPS_API_TOKEN, datarobot_api_token)
                set_config(ConfigConstants.MLOPS_SERVICE_URL, datarobot_endpoint)
                set_config(ConfigConstants.DEPLOYMENT_ID, deployment_id)
                set_config(ConfigConstants.MODEL_ID, model_id)
                mclient = MLOps().set_api_spooler().init()
                mclient.report_deployment_stats(
                    num_predictions=1, execution_time_ms=execution_time * 1000
                )
                mclient.report_predictions_data(
                    features_df=pd.DataFrame(
                        [
                            {
                                prompt_feature_name: (
                                    args[0]
                                    if args
                                    else kwargs.get(prompt_feature_name, None)
                                )
                            }
                        ]
                    ),
                    predictions=[str(result)],
                    association_ids=[str(uuid4())],
                )
                mclient.shutdown()

            # Return the original result or re-raise the exception
            return result

        return wrapper

    return decorator
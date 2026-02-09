# Copyright 2025 DataRobot, Inc.
# Adaptive Agent Demo - Custom Entry Point
"""
Custom entry point that uses the AdaptiveAgent with dynamic think mode toggling.
This file can be used as an alternative to custom.py for the adaptive demo.
"""
# ------------------------------------------------------------------------------
# THIS SECTION OF CODE IS REQUIRED TO SETUP TRACING AND TELEMETRY FOR THE AGENTS.
# REMOVING THIS CODE WILL DISABLE ALL MONITORING, TRACING AND TELEMETRY.
# isort: off
from datarobot_genai.core.telemetry_agent import instrument

instrument(framework="langgraph")
# ruff: noqa: E402
from agent import Config, AdaptiveAgent

# isort: on
# ------------------------------------------------------------------------------
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator, Iterator, Union

from datarobot_genai.core.chat import (
    CustomModelChatResponse,
    CustomModelStreamingResponse,
    resolve_authorization_context,
    to_custom_model_chat_response,
    to_custom_model_streaming_response,
)
from openai.types.chat import CompletionCreateParams
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming,
    CompletionCreateParamsStreaming,
)

# Global state for tracking adaptive agent across requests
_adaptive_agents: dict[str, AdaptiveAgent] = {}


def load_model(code_dir: str) -> tuple[ThreadPoolExecutor, asyncio.AbstractEventLoop]:
    """The agent is instantiated in this function and returned."""
    thread_pool_executor = ThreadPoolExecutor(1)
    event_loop = asyncio.new_event_loop()
    thread_pool_executor.submit(asyncio.set_event_loop, event_loop).result()
    return (thread_pool_executor, event_loop)


def _get_or_create_agent(session_id: str, **kwargs: Any) -> AdaptiveAgent:
    """
    Get existing agent for session or create new one.
    This maintains conversation history across requests in the same session.
    """
    if session_id not in _adaptive_agents:
        _adaptive_agents[session_id] = AdaptiveAgent(**kwargs)
    return _adaptive_agents[session_id]


def _reset_all_agents() -> None:
    """Clear all cached agents (called when starting fresh demo)."""
    global _adaptive_agents
    _adaptive_agents = {}


def chat(
    completion_create_params: CompletionCreateParams
    | CompletionCreateParamsNonStreaming
    | CompletionCreateParamsStreaming,
    load_model_result: tuple[ThreadPoolExecutor, asyncio.AbstractEventLoop],
    **kwargs: Any,
) -> Union[CustomModelChatResponse, Iterator[CustomModelStreamingResponse]]:
    """
    When using the chat endpoint, this function is called.
    
    This version uses the AdaptiveAgent which:
    1. Analyzes conversation history for user corrections
    2. Toggles Qwen3's /think or /no_think mode accordingly
    3. Returns reflection metadata for UI display
    """
    thread_pool_executor, event_loop = load_model_result

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = Config()

    completion_create_params["authorization_context"] = resolve_authorization_context(
        completion_create_params, **kwargs
    )

    incoming_headers = kwargs.get("headers", {}) or {}
    allowed_headers = {"x-datarobot-api-token", "x-datarobot-api-key"}
    forwarded_headers = {
        k: v for k, v in incoming_headers.items() if k.lower() in allowed_headers
    }
    completion_create_params["forwarded_headers"] = forwarded_headers

    # Extract session ID for maintaining conversation state
    # Try to get thread_id from various places
    session_id = kwargs.get("session_id", None)
    if not session_id and "extra_body" in completion_create_params:
        session_id = completion_create_params["extra_body"].get("session_id")
        if not session_id:
            session_id = completion_create_params["extra_body"].get("thread_id")
    if not session_id:
        session_id = completion_create_params.get("thread_id")
    if not session_id:
        # Generate a unique session ID if none provided
        import uuid
        session_id = str(uuid.uuid4())
    
    print(f"[ADAPTIVE] Using session_id: {session_id}")

    # Get or create adaptive agent for this session
    agent = _get_or_create_agent(session_id, **completion_create_params)

    result = thread_pool_executor.submit(
        event_loop.run_until_complete,
        agent.invoke(completion_create_params=completion_create_params),
    ).result()

    if isinstance(result, AsyncGenerator):
        return to_custom_model_streaming_response(
            thread_pool_executor,
            event_loop,
            result,  # type: ignore[arg-type]
            model=completion_create_params.get("model"),
        )
    else:
        # Handle extended result with reflection metadata
        if len(result) >= 4:
            response_text, pipeline_interactions, usage_metrics, adaptive_metadata = result
        else:
            response_text, pipeline_interactions, usage_metrics = result
            adaptive_metadata = None

        response = to_custom_model_chat_response(
            response_text,
            pipeline_interactions,
            usage_metrics,  # type: ignore[arg-type]
            model=completion_create_params.get("model"),
        )

        # Inject adaptive metadata into response for frontend consumption
        if adaptive_metadata and hasattr(response, '__dict__'):
            response.__dict__['adaptive_state'] = adaptive_metadata

        return response

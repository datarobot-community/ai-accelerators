# Copyright 2025 DataRobot, Inc.
# Adaptive Agent Demo - State API
"""
API endpoint to expose the adaptive agent's current state to the frontend.
This allows the UI to display which model is being used and why.
"""

from fastapi import APIRouter
from pydantic import BaseModel

adaptive_router = APIRouter(prefix="/adaptive-state", tags=["adaptive"])

# In-memory state store (in production, use Redis or similar)
_adaptive_state = {
    "think_mode": False,
    "current_model": "datarobot/azure/gpt-4o-mini",
    "turn_count": 0,
    "last_reflection": None,
}


class ReflectionInfo(BaseModel):
    needs_thinking: bool
    reason: str
    confidence: float


class AdaptiveStateResponse(BaseModel):
    thinkMode: bool
    currentModel: str
    turnCount: int
    lastReflection: ReflectionInfo | None = None


class AdaptiveStateUpdate(BaseModel):
    think_mode: bool
    current_model: str
    turn_count: int
    last_reflection: dict | None = None


@adaptive_router.get("", response_model=AdaptiveStateResponse)
async def get_adaptive_state():
    """Get the current adaptive agent state."""
    reflection = None
    if _adaptive_state.get("last_reflection"):
        ref = _adaptive_state["last_reflection"]
        reflection = ReflectionInfo(
            needs_thinking=ref.get("needs_thinking", False),
            reason=ref.get("reason", ""),
            confidence=ref.get("confidence", 0.0),
        )
    
    return AdaptiveStateResponse(
        thinkMode=_adaptive_state.get("think_mode", False),
        currentModel=_adaptive_state.get("current_model", "gpt-4o-mini"),
        turnCount=_adaptive_state.get("turn_count", 0),
        lastReflection=reflection,
    )


@adaptive_router.post("")
async def update_adaptive_state(state: AdaptiveStateUpdate):
    """Update the adaptive agent state (called by the agent)."""
    global _adaptive_state
    _adaptive_state = {
        "think_mode": state.think_mode,
        "current_model": state.current_model,
        "turn_count": state.turn_count,
        "last_reflection": state.last_reflection,
    }
    return {"status": "ok"}


@adaptive_router.delete("")
async def reset_adaptive_state():
    """Reset the adaptive agent state to defaults (for new conversations)."""
    global _adaptive_state
    _adaptive_state = {
        "think_mode": False,
        "current_model": "datarobot/azure/gpt-4o-mini",
        "turn_count": 0,
        "last_reflection": None,
    }
    return {"status": "reset"}

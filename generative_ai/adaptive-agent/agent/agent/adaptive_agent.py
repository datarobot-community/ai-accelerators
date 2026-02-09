# Copyright 2025 DataRobot, Inc.
# Adaptive Agent Demo - Main Agent with Dynamic Model Switching
"""
Adaptive agent that dynamically switches between GPT-4o (for complex reasoning)
and GPT-4o-mini (for fast responses) based on reflection analysis of recent
conversation history.

This is a simple Q&A agent (not a blog writer) that demonstrates adaptive model selection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from datarobot_genai.core.agents import make_system_prompt
from datarobot_genai.langgraph.agent import LangGraphAgent
from langchain_core.prompts import ChatPromptTemplate
from langchain_litellm.chat_models import ChatLiteLLM
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent

from agent.config import Config
from agent.reflection_service import ReflectionResult, ReflectionService


@dataclass
class AdaptiveState:
    """Tracks the adaptive agent's state across conversation turns."""
    think_mode: bool = False  # True = use main_model (GPT-4o), False = use fast_model (GPT-4o-mini)
    history: list[dict[str, Any]] = field(default_factory=list)
    last_reflection: ReflectionResult | None = None
    turn_count: int = 0
    current_model: str = ""


CUSTOMER_SUPPORT_PROMPT = """You are a helpful customer support agent for DataInsight Pro, a SaaS analytics platform.

About DataInsight Pro:
- A cloud-based analytics platform for business intelligence
- Offers three pricing tiers: Starter ($29/mo), Professional ($99/mo), Enterprise (custom)
- Key features: dashboards, data visualization, automated reports, data export (CSV, PDF, Excel)
- Export options: Manual export, scheduled exports (Professional+), API access (Enterprise)

CSV Export Instructions:
1. Open any dashboard or report
2. Click the '...' menu in the top right
3. Select 'Export' > 'CSV'
4. Choose columns to include
5. Click 'Download'

Scheduled Exports (Professional+ only):
1. Go to Settings > Scheduled Exports
2. Click 'New Schedule'
3. Select the dashboard/report
4. Choose format and frequency
5. Add recipients and save

Your role:
- Answer product questions accurately and helpfully
- Guide users through features and troubleshooting
- Be concise but thorough
- If you don't know something, say so

Current date: {current_date}
"""


class AdaptiveAgent(LangGraphAgent):
    """
    Adaptive customer support agent that dynamically switches between models
    based on detected user corrections in conversation history.
    
    When corrections are detected by the reflection model (gpt-4o-mini),
    the agent switches to GPT-4o for more thorough reasoning.
    When the conversation flows smoothly, it uses GPT-4o-mini for faster responses.
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.adaptive_config = Config()
        self.adaptive_state = AdaptiveState()
        
        self.reflection_service = ReflectionService(
            api_base=self.litellm_api_base(self.adaptive_config.llm_deployment_id),
            api_key=self.api_key,
            model=self.adaptive_config.reflection_model,
        )
        
        # Model configuration for adaptive switching
        self._main_model = self.adaptive_config.main_model      # GPT-4o for complex reasoning
        self._fast_model = self.adaptive_config.fast_model      # GPT-4o-mini for quick responses
        self.adaptive_state.current_model = self._fast_model

    @property
    def workflow(self) -> StateGraph[MessagesState]:
        """Simple single-node workflow for Q&A (not blog writing)."""
        langgraph_workflow = StateGraph[
            MessagesState, None, MessagesState, MessagesState
        ](MessagesState)
        langgraph_workflow.add_node("support_agent", self.support_agent)
        langgraph_workflow.add_edge(START, "support_agent")
        langgraph_workflow.add_edge("support_agent", END)
        return langgraph_workflow  # type: ignore[return-value]

    @property
    def prompt_template(self) -> ChatPromptTemplate:
        """Simple prompt that passes user message directly."""
        return ChatPromptTemplate.from_messages([
            ("user", "{question}"),
        ])

    @property
    def support_agent(self) -> Any:
        """Single support agent node for answering questions."""
        system_prompt = CUSTOMER_SUPPORT_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d")
        )
        return create_react_agent(
            self.llm(),
            tools=self.mcp_tools,
            prompt=make_system_prompt(system_prompt),
            name="Support Agent",
        )

    def _get_current_model(self) -> str:
        """Get the appropriate model based on think_mode state."""
        return self._main_model if self.adaptive_state.think_mode else self._fast_model

    def llm(
        self,
        preferred_model: str | None = None,
        auto_model_override: bool = True,
    ) -> ChatLiteLLM:
        """Returns the ChatLiteLLM configured for the current adaptive state."""
        api_base = self.litellm_api_base(self.adaptive_config.llm_deployment_id)
        
        # Use adaptive model selection
        model = self._get_current_model()
        
        # Track which model we're using
        self.adaptive_state.current_model = model
            
        if self.verbose:
            mode_str = "THINKING (GPT-4o)" if self.adaptive_state.think_mode else "FAST (GPT-4o-mini)"
            print(f"[ADAPTIVE] Using model: {model} | Mode: {mode_str}")
            
        return ChatLiteLLM(
            model=model,
            api_base=api_base,
            api_key=self.api_key,
            timeout=self.timeout,
            streaming=True,
            max_retries=3,
        )

    async def _reflect_on_history(self) -> ReflectionResult:
        """Use the reflection service to analyze recent conversation history."""
        reflection = await self.reflection_service.analyze_conversation(
            self.adaptive_state.history,
            max_turns=3,
        )
        self.adaptive_state.last_reflection = reflection
        return reflection

    def _update_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.adaptive_state.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.adaptive_state.turn_count += 1

    async def _push_state_to_backend(self) -> None:
        """Push adaptive state to the FastAPI backend for UI display."""
        import aiohttp
        try:
            state_data = {
                "think_mode": self.adaptive_state.think_mode,
                "current_model": self.adaptive_state.current_model,
                "turn_count": self.adaptive_state.turn_count,
                "last_reflection": {
                    "needs_thinking": self.adaptive_state.last_reflection.needs_thinking,
                    "reason": self.adaptive_state.last_reflection.reason,
                    "confidence": self.adaptive_state.last_reflection.confidence,
                } if self.adaptive_state.last_reflection else None,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8080/api/v1/adaptive-state",
                    json=state_data,
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as resp:
                    pass  # Fire and forget
        except Exception as e:
            if self.verbose:
                print(f"[ADAPTIVE] Failed to push state: {e}")

    async def invoke(
        self,
        completion_create_params: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        """Main invocation method with adaptive model switching."""
        messages = completion_create_params.get("messages", [])
        
        if self.verbose:
            print(f"[ADAPTIVE] Received {len(messages)} messages from backend")
            for i, m in enumerate(messages):
                role = m.get("role", "unknown")
                content = str(m.get("content", ""))[:50]
                print(f"[ADAPTIVE]   [{i}] {role}: {content}...")
        
        # Count turns from the actual messages passed in (more reliable than tracking)
        user_messages = [m for m in messages if m.get("role") == "user"]
        turn_count = len(user_messages)
        
        # Build history from messages for reflection
        self.adaptive_state.history = [
            {"role": m.get("role"), "content": m.get("content", "")}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        self.adaptive_state.turn_count = turn_count
        
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if self.verbose:
            print(f"[ADAPTIVE] Turn count: {turn_count}, History length: {len(self.adaptive_state.history)}")
        
        # Perform reflection after we have enough history (3+ user messages)
        if turn_count >= 3:
            reflection = await self._reflect_on_history()
            old_mode = self.adaptive_state.think_mode
            self.adaptive_state.think_mode = reflection.needs_thinking
            
            # Update current_model based on new think_mode
            self.adaptive_state.current_model = self._get_current_model()
            
            if self.verbose:
                print(f"[ADAPTIVE] Reflection result: {reflection}")
                if old_mode != self.adaptive_state.think_mode:
                    old_model = self._main_model if old_mode else self._fast_model
                    new_model = self._main_model if self.adaptive_state.think_mode else self._fast_model
                    print(f"[ADAPTIVE] Model switched: {old_model} -> {new_model}")
        else:
            # First 2 turns - always use fast model
            self.adaptive_state.think_mode = False
            self.adaptive_state.current_model = self._fast_model
        
        # Push state to backend for UI
        await self._push_state_to_backend()
        
        # Invoke parent workflow
        result = await super().invoke(completion_create_params, **kwargs)
        
        # Push updated state after response
        await self._push_state_to_backend()
        
        return result

    def get_adaptive_state(self) -> dict[str, Any]:
        """Return current adaptive state for API responses."""
        return {
            "think_mode": self.adaptive_state.think_mode,
            "current_model": self.adaptive_state.current_model,
            "turn_count": self.adaptive_state.turn_count,
            "last_reflection": {
                "needs_thinking": self.adaptive_state.last_reflection.needs_thinking,
                "reason": self.adaptive_state.last_reflection.reason,
                "confidence": self.adaptive_state.last_reflection.confidence,
            } if self.adaptive_state.last_reflection else None,
        }

# Copyright 2025 DataRobot, Inc.
# Adaptive Agent Demo - Reflection Service
"""
Reflection service that analyzes conversation history to detect user corrections.
Uses gpt-4o-mini to determine if the agent should enable deep thinking mode.
"""

import json
from dataclasses import dataclass
from typing import Any

from langchain_litellm.chat_models import ChatLiteLLM


@dataclass
class ReflectionResult:
    """Result from the reflection model analysis."""
    needs_thinking: bool
    reason: str
    confidence: float = 0.0


REFLECTION_PROMPT = """You are analyzing the MOST RECENT exchange in a conversation to detect if the user is CURRENTLY correcting the assistant.

Focus ONLY on the last user message. Determine if this specific message:
1. Explicitly corrects the assistant (e.g., "No, I meant...", "That's not what I asked", "You misunderstood")
2. Rephrases a question due to an inadequate response
3. Expresses frustration or confusion about the assistant's last answer
4. Points out errors or incomplete information

Conversation History (focus on the LAST user message):
{conversation_history}

Respond with a JSON object only, no other text:
{{
    "needs_thinking": true/false,
    "reason": "Brief explanation",
    "confidence": 0.0-1.0
}}

IMPORTANT RULES:
- Set needs_thinking to TRUE only if the LAST user message contains a correction or complaint
- Set needs_thinking to FALSE if the last user message is:
  - A new question (not a correction)
  - Positive feedback (e.g., "Thanks!", "That's helpful", "Perfect")
  - A follow-up question that doesn't indicate dissatisfaction
  - Any message that suggests the conversation is going well

Do NOT carry over corrections from earlier in the conversation - only judge the CURRENT exchange.
"""


class ReflectionService:
    """Service to analyze conversation and decide on thinking mode."""

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: int = 30,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout
        self._llm: ChatLiteLLM | None = None

    @property
    def llm(self) -> ChatLiteLLM:
        if self._llm is None:
            self._llm = ChatLiteLLM(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                timeout=self.timeout,
                temperature=0.1,
                max_retries=2,
            )
        return self._llm

    def format_history(self, messages: list[dict[str, Any]]) -> str:
        """Format conversation history for the reflection prompt."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    async def analyze_conversation(
        self,
        history: list[dict[str, Any]],
        max_turns: int = 3,
    ) -> ReflectionResult:
        """
        Analyze the last N turns of conversation to detect corrections.
        
        Args:
            history: Full conversation history as list of message dicts
            max_turns: Number of recent turns to analyze (default 3)
            
        Returns:
            ReflectionResult with thinking mode decision
        """
        recent_messages = history[-(max_turns * 2):]
        
        if len(recent_messages) < 2:
            return ReflectionResult(
                needs_thinking=False,
                reason="Not enough conversation history to analyze",
                confidence=1.0,
            )

        formatted_history = self.format_history(recent_messages)
        prompt = REFLECTION_PROMPT.format(conversation_history=formatted_history)

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            
            return ReflectionResult(
                needs_thinking=result.get("needs_thinking", False),
                reason=result.get("reason", "No reason provided"),
                confidence=result.get("confidence", 0.5),
            )
        except json.JSONDecodeError as e:
            print(f"Failed to parse reflection response: {e}")
            return ReflectionResult(
                needs_thinking=False,
                reason=f"Parse error: {str(e)}",
                confidence=0.0,
            )
        except Exception as e:
            print(f"Reflection service error: {e}")
            return ReflectionResult(
                needs_thinking=False,
                reason=f"Service error: {str(e)}",
                confidence=0.0,
            )

    def analyze_conversation_sync(
        self,
        history: list[dict[str, Any]],
        max_turns: int = 3,
    ) -> ReflectionResult:
        """Synchronous wrapper for analyze_conversation."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.analyze_conversation(history, max_turns)
        )

#!/usr/bin/env python3
"""
Demo script to test the adaptive agent conversation flow locally.
This simulates the demo scenario without needing the full UI.

Usage:
    python scripts/demo_conversation.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

from agent.reflection_service import ReflectionService, ReflectionResult


DEMO_CONVERSATIONS = [
    {
        "name": "Smooth conversation (no corrections)",
        "messages": [
            {"role": "user", "content": "What pricing plans do you offer?"},
            {"role": "assistant", "content": "We offer three plans: Starter ($29/mo), Professional ($99/mo), and Enterprise (custom pricing)."},
            {"role": "user", "content": "What features does the Professional plan include?"},
            {"role": "assistant", "content": "Professional includes unlimited dashboards, scheduled exports, and priority support."},
            {"role": "user", "content": "Thanks, that's helpful!"},
        ],
        "expected_thinking": False,
    },
    {
        "name": "User correction detected",
        "messages": [
            {"role": "user", "content": "How do I export data?"},
            {"role": "assistant", "content": "You can export data by clicking the Export button and selecting PDF format."},
            {"role": "user", "content": "No, I meant export to CSV specifically, not PDF."},
        ],
        "expected_thinking": True,
    },
    {
        "name": "User rephrases question",
        "messages": [
            {"role": "user", "content": "How much does it cost?"},
            {"role": "assistant", "content": "Could you clarify what you're asking about?"},
            {"role": "user", "content": "I'm asking about the monthly subscription price for your service."},
        ],
        "expected_thinking": True,
    },
    {
        "name": "User expresses confusion",
        "messages": [
            {"role": "user", "content": "Can I automate exports?"},
            {"role": "assistant", "content": "Yes, you can set up automated workflows."},
            {"role": "user", "content": "I don't understand. What do you mean by workflows? I just want to schedule a report."},
        ],
        "expected_thinking": True,
    },
    {
        "name": "Recovery after correction",
        "messages": [
            {"role": "user", "content": "No, I meant CSV not PDF"},
            {"role": "assistant", "content": "I apologize for the confusion. Here's how to export to CSV: Go to your dashboard, click the menu, and select Export > CSV."},
            {"role": "user", "content": "Perfect, thanks!"},
            {"role": "assistant", "content": "You're welcome! Let me know if you have any other questions."},
            {"role": "user", "content": "Can I also export to Excel?"},
        ],
        "expected_thinking": False,
    },
]


async def test_reflection_service():
    """Test the reflection service with demo conversations."""
    print("=" * 60)
    print("ADAPTIVE AGENT DEMO - Reflection Service Test")
    print("=" * 60)
    print()
    
    # Note: In real usage, these would come from config
    service = ReflectionService(
        model="gpt-4o-mini",  # Will need actual API setup
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    for i, scenario in enumerate(DEMO_CONVERSATIONS, 1):
        print(f"Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        # Show last 3 messages
        messages = scenario["messages"]
        print("Recent messages:")
        for msg in messages[-6:]:  # Last 3 turns
            role = msg["role"].upper()
            content = msg["content"][:60] + "..." if len(msg["content"]) > 60 else msg["content"]
            print(f"  {role}: {content}")
        
        print()
        print(f"Expected: needs_thinking = {scenario['expected_thinking']}")
        
        # If API key is available, actually test
        if os.environ.get("OPENAI_API_KEY"):
            try:
                result = await service.analyze_conversation(messages)
                print(f"Actual:   needs_thinking = {result.needs_thinking}")
                print(f"Reason:   {result.reason}")
                print(f"Confidence: {result.confidence:.2f}")
                
                if result.needs_thinking == scenario["expected_thinking"]:
                    print("✓ PASS")
                else:
                    print("✗ FAIL (mismatch)")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("(Skipping actual API call - OPENAI_API_KEY not set)")
        
        print()
    
    print("=" * 60)
    print("Demo flow explanation:")
    print("=" * 60)
    print("""
1. User asks simple question → Fast mode (no thinking)
2. Agent provides answer
3. User CORRECTS the agent → Reflection detects correction
4. Thinking mode ACTIVATES → Agent reasons more carefully
5. Better answer provided
6. User satisfied → Fast mode returns

This demonstrates ADAPTIVE behavior based on conversation dynamics.
""")


def main():
    """Run the demo test."""
    asyncio.run(test_reflection_service())


if __name__ == "__main__":
    main()

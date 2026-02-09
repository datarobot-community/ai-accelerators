# Adaptive Agent Demo

## Overview

This demo showcases an agent's ability to **adapt its reasoning behavior** based on conversation dynamics. The agent uses:

- **GPT-4o** for complex reasoning when corrections are detected
- **GPT-4o-mini** for fast responses during smooth conversation flow
- **GPT-4o-mini** as a reflection model to analyze the last 3 conversation turns and detect user corrections

## Key Concept

The agent dynamically switches between models based on conversation analysis:

| Scenario | Model Used | Behavior |
|----------|------------|----------|
| Conversation flowing smoothly | GPT-4o-mini | Fast, direct responses |
| User corrects the agent | GPT-4o | More thorough reasoning |
| User rephrases question | GPT-4o | Agent recognizes confusion |
| Positive feedback received | GPT-4o-mini | Returns to efficient mode |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ Model Mode  │  │      Reflection Log Panel            │  │
│  │  Indicator  │  │  (shows gpt-4o-mini reasoning)       │  │
│  └─────────────┘  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Adaptive Agent                             │
│  1. Store conversation history (last 3 turns)                │
│  2. Call Reflection Model (gpt-4o-mini) before response      │
│  3. Switch model based on correction detection               │
│     - Corrections detected → GPT-4o (thorough)               │
│     - Smooth conversation → GPT-4o-mini (fast)               │
└─────────────────────────────────────────────────────────────┘
```

## Demo Scenario: Customer Support

The agent acts as a customer support representative for "DataInsight Pro" analytics platform.

### Scripted Demo Flow (3-5 minutes)

| Turn | User Says | Expected Behavior | Model |
|------|-----------|-------------------|-------|
| 1 | "What pricing plans do you offer?" | Lists 3 tiers (Starter, Pro, Enterprise) | GPT-4o-mini |
| 2 | "How do I export data?" | General export explanation | GPT-4o-mini |
| 3 | "No, I meant export to CSV specifically, not PDF" | **Correction detected!** Detailed CSV instructions | GPT-4o |
| 4 | "Can I schedule automated exports?" | Thorough answer with plan requirements | GPT-4o |
| 5 | "Thanks, that's helpful!" | Positive acknowledgment | GPT-4o-mini |

## Files Added/Modified

### New Files

| File | Purpose |
|------|---------|
| `agent/agent/reflection_service.py` | GPT-4o-mini reflection model integration |
| `agent/agent/adaptive_agent.py` | Main adaptive agent with think mode logic |
| `agent/custom_adaptive.py` | Entry point using AdaptiveAgent |
| `agent/knowledge/product_kb.json` | Demo product knowledge base |
| `frontend_web/src/components/ThinkModeIndicator.tsx` | UI badge showing think mode status |
| `frontend_web/src/components/ReflectionPanel.tsx` | Collapsible panel showing reflection reasoning |

### Modified Files

| File | Changes |
|------|---------|
| `agent/agent/config.py` | Added Qwen3 and reflection model settings |
| `agent/agent/__init__.py` | Export new classes |
| `.env.template` | Added adaptive demo configuration variables |

## Setup Instructions

### 1. Configure Environment

Copy `.env.template` to `.env` and configure:

```bash
cp .env.template .env
```

Set these adaptive demo variables:
```env
MAIN_MODEL=datarobot/azure/gpt-4o
FAST_MODEL=datarobot/azure/gpt-4o-mini
REFLECTION_MODEL=datarobot/azure/gpt-4o-mini
ENABLE_ADAPTIVE_THINKING=true
```

### 2. Use Adaptive Agent Entry Point

To use the adaptive agent instead of the default, update the agent configuration:

```bash
# Option 1: Rename files
mv agent/custom.py agent/custom_original.py
mv agent/custom_adaptive.py agent/custom.py

# Option 2: Or modify the import in custom.py to use AdaptiveAgent
```

### 3. Run the Demo

```bash
task dev
```

Navigate to http://localhost:5173

## Demo Talking Points

1. **"Watch the indicator"** - Draw attention to the model badge in the header
2. **"The agent starts with GPT-4o-mini"** - Show fast responses for simple questions
3. **"Now I'll correct it"** - Demonstrate the correction detection trigger
4. **"See the reflection panel"** - Expand to show the reflection model's reasoning
5. **"Model switches to GPT-4o"** - The indicator changes, responses become more thorough
6. **"Self-healing behavior"** - After good responses, it returns to GPT-4o-mini

## Technical Details

### Reflection Model Prompt

The reflection model analyzes conversation history with this prompt:

```
Analyze these conversation turns. Did the user correct the assistant's 
misunderstanding or ask for clarification due to an inadequate response?

Return JSON: {"needs_thinking": bool, "reason": str, "confidence": float}
```

### Correction Detection Criteria

- Explicit corrections ("No, I meant...", "That's not what I asked")
- Clarification requests following confusion
- Rephrasing of the same question
- Expressions of frustration

### Model Switching Strategy

The adaptive agent uses two OpenAI models via DataRobot's LLM Gateway:

- **GPT-4o** (`datarobot/azure/gpt-4o`) - More capable model for complex reasoning
- **GPT-4o-mini** (`datarobot/azure/gpt-4o-mini`) - Faster, cheaper model for simple queries

The agent switches between them based on conversation dynamics, demonstrating adaptive resource usage.

## Customization

### Change the Demo Domain

Edit `agent/agent/adaptive_agent.py` and modify `CUSTOMER_SUPPORT_SYSTEM_PROMPT`.

Update `agent/knowledge/product_kb.json` with your product information.

### Adjust Reflection Sensitivity

Modify the prompt in `agent/agent/reflection_service.py` to be more or less sensitive to corrections.

### Change Models

Update in `.env` or `agent/agent/config.py`:
- `MAIN_MODEL` - Complex reasoning model (default: GPT-4o)
- `FAST_MODEL` - Quick response model (default: GPT-4o-mini)
- `REFLECTION_MODEL` - Correction detection model (default: GPT-4o-mini)

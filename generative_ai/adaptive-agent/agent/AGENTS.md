# Agent Development Instructions

## Dependecies Installation

The following command should be run after agent code modification:

```shell
dr task run agent:install
```

## Agent Structure

Agent must be implemented in the following location withing the `agent/agent` directory. None of the other files outside of this directory are related.



Agent must implement the following components:

### 1. Class Definition

```python
from datarobot_genai.langgraph.agent import LangGraphAgent

class MyAgent(LangGraphAgent):
    """Your agent description here."""
```

**Important**: `MyAgent` class should NOT be renamed!

### 2. Required Properties and Methods in Class Definition

#### `llm()` Method

**CRITICAL**: Do NOT modify, delete, or change this method. It MUST be kept exactly as shown below in the agent implementation:

```python
def llm(
    self,
    preferred_model: str | None = None,
    auto_model_override: bool = True,
) -> ChatLiteLLM:
    api_base = self.litellm_api_base(config.llm_deployment_id)
    model = preferred_model
    if preferred_model is None:
        model = config.llm_default_model
    if auto_model_override and not config.use_datarobot_llm_gateway:
        model = config.llm_default_model
    if self.verbose:
        print(f"Using model: {model}")
    return ChatLiteLLM(
        model=model,
        api_base=api_base,
        api_key=self.api_key,
        timeout=self.timeout,
        streaming=True,
        max_retries=3,
    )
```

**Why this is required**: This method handles model configuration, API authentication, and DataRobot LLM Gateway integration. Changing it will break deployment.

#### `workflow` Property
Defines the agent's execution flow using LangGraph's StateGraph.

```python
@property
def workflow(self) -> StateGraph[MessagesState]:
    langgraph_workflow = StateGraph[
        MessagesState, None, MessagesState, MessagesState
    ](MessagesState)

    # Add nodes for each agent component
    langgraph_workflow.add_node("agent_node", self.agent_node)

    # Define edges (workflow connections)
    langgraph_workflow.add_edge(START, "agent_node")
    langgraph_workflow.add_edge("agent_node", END)

    return langgraph_workflow  # type: ignore[return-value]
```

#### `prompt_template` Property

Use it to define how user prompt is formatted for the agent.

```python
@property
def prompt_template(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("user", "{user_prompt_content}"),
    ])
```

**IMPORTANT**: The template must accept `{user_prompt_content}` to receive user prompts.

### 3. Agent Nodes

Agent nodes are typically created using `create_react_agent`.
**IMPORTANT**: Use `create_react_agent` call to create agent's node while passing the preferred LLM, system prompt and required tools into it.

```python
@property
def agent_node(self) -> Any:
    return create_react_agent(
        self.llm(preferred_model="datarobot/azure/gpt-4o-mini"),
        tools=self.tools,  # or [] for no tools
        prompt=make_system_prompt(
            "Your agent's system prompt here."
        ),
    )
```

### 4. Agent tools

**IMPORTANT**: Add required tools in the `agent/agent` directory. Do not add/modify any files outside of this directory. If some of the tools require adding new packages, they should be added to the pyproject.toml and properly installed using command

```shell
dr task run agent:install
```

**IMPORTANT**: Tools must be imported and used in `MyAgent` implementation.


### 5. Preferred LLM model

Preferred model should be set in each ```self.llm(preferred_model="{preffered_model_here}")``` invocation.
**Important**: `preferred_model` parameter must be prefixed with `datarobot/`.

## Agent Testing

Review and update the tests in the `agent/tests` directory after code changes were made to the agent.
Run the following shell commands to run the tests:

```shell
dr task run agent:lint
```

```shell
dr task run agent:test
```

## Post Deployment Validation

Run the following shell command to validate the agent after deployment. If the response has no errors then the deployment is successful.

```shell
task agent:cli -- execute-deployment --user_prompt "Agent specific prompt to validate that it's working" --deployment_id <deployment_id>
```

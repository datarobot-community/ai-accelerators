# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from datetime import datetime
from typing import Any

from datarobot_genai.core.agents import (
    make_system_prompt,
)
from datarobot_genai.langgraph.agent import LangGraphAgent
from langchain_core.prompts import ChatPromptTemplate
from langchain_litellm.chat_models import ChatLiteLLM
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent

from agent.config import Config

config = Config()


class MyAgent(LangGraphAgent):
    """MyAgent is a custom agent that uses Langgraph to plan, write, and edit content.
    It utilizes DataRobot's LLM Gateway or a specific deployment for language model interactions.
    This example illustrates 3 agents that handle content creation tasks, including planning, writing,
    and editing blog posts.
    """

    @property
    def workflow(self) -> StateGraph[MessagesState]:
        langgraph_workflow = StateGraph[
            MessagesState, None, MessagesState, MessagesState
        ](MessagesState)
        langgraph_workflow.add_node("planner_node", self.agent_planner)
        langgraph_workflow.add_node("writer_node", self.agent_writer)
        langgraph_workflow.add_edge(START, "planner_node")
        langgraph_workflow.add_edge("planner_node", "writer_node")
        langgraph_workflow.add_edge("writer_node", END)
        return langgraph_workflow  # type: ignore[return-value]

    @property
    def prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                (
                    "user",
                    f"The topic is {{topic}}. Make sure you find any interesting and "
                    f"relevant information given the current year is {datetime.now().year}.",
                ),
            ]
        )

    def llm(
        self,
        preferred_model: str | None = None,
        auto_model_override: bool = True,
    ) -> ChatLiteLLM:
        """Returns the ChatLiteLLM to use for a given model.

        If a `preferred_model` is provided, it will be used. Otherwise, the default model will be used.
        If auto_model_override is True, it will try and use the model specified in the request
        but automatically back out to the default model if the LLM Gateway is not configured

        Args:
            preferred_model: Optional[str]: The model to use. If none, it defaults to config.llm_default_model.
            auto_model_override: Optional[bool]: If True, it will try and use the model
                specified in the request but automatically back out if the LLM Gateway is
                not available.

        Returns:
            ChatLiteLLM: The model to use.
        """
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

    @property
    def agent_planner(self) -> Any:
        return create_react_agent(
            self.llm(preferred_model="datarobot/azure/gpt-5-mini-2025-08-07"),
            tools=self.mcp_tools,
            prompt=make_system_prompt(
                "You are a content planner. You create brief, structured outlines for blog articles. "
                "You identify the most important points and cite relevant sources. Keep it simple and to the point - "
                "this is just an outline for the writer.\n"
                "\n"
                "You have access to tools that can help you research and gather information. Use these tools when "
                "required to collect accurate and up-to-date information about the topic for your planning and research.\n"
                "\n"
                "Create a simple outline with:\n"
                "1. 10-15 key points or facts (bullet points only, no paragraphs)\n"
                "2. 2-3 relevant sources or references\n"
                "3. A brief suggested structure (intro, 2-3 sections, conclusion)\n"
                "\n"
                "Do NOT write paragraphs or detailed explanations. Just provide a focused list.",
            ),
            name="Planner Agent",
        )

    @property
    def agent_writer(self) -> Any:
        return create_react_agent(
            self.llm(preferred_model="datarobot/azure/gpt-5-mini-2025-08-07"),
            tools=self.mcp_tools,
            prompt=make_system_prompt(
                "You are a content writer working with a planner colleague.\n"
                "You write opinion pieces based on the planner's outline and context. You provide objective and "
                "impartial insights backed by the planner's information. You acknowledge when your statements are "
                "opinions versus objective facts.\n"
                "\n"
                "You have access to tools that can help you verify facts and gather additional supporting information. "
                "Use these tools when required to ensure accuracy and find relevant details while writing.\n"
                "\n"
                "1. Use the content plan to craft a compelling blog post.\n"
                "2. Structure with an engaging introduction, insightful body, and summarizing conclusion.\n"
                "3. Sections/Subtitles are properly named in an engaging manner.\n"
                "4. CRITICAL: Keep the total output under 500 words. Each section should have 1-2 brief paragraphs.\n"
                "\n"
                "Write in markdown format, ready for publication.",
            ),
            name="Writer Agent",
        )

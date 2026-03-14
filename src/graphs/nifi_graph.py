from __future__ import annotations

import asyncio
import json

from contextlib import AsyncExitStack
from typing import Literal
from typing import final

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.messages import AnyMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from langgraph.types import interrupt

from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.middleware.tool_middleware import InterruptRequest
from graphs.prompts.nifi_graph_prompts import oss_sytem_prompt
from graphs.prompts.nifi_graph_prompts import previus_steps
from graphs.services.nifi_client_service import NifiClientService
from graphs.state.nifi_graph_state import FlowState
from logger import logger
from settings import settings


@final
class NifiGraph(StateGraph[FlowState, None, FlowState, FlowState]):
    def __init__(self, checkpointer: BaseCheckpointSaver[str],
                 config_schema: type[None] | None = None) -> None:
        super().__init__(FlowState, config_schema)
        self._checkpointer: BaseCheckpointSaver[str] = checkpointer

    async def _data_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        service: NifiClientService = self._settings(config).service

        log_data: list[str] = await service.log_errors()
        processors_data: list[dict[str, str]] = await service.processors()
        conn_data: list[dict[str, str]] = await service.connections()

        logger.info(errors=log_data)

        return FlowState(error=log_data, processors_data=processors_data, connections=conn_data)

    def _should_continue(self, state: FlowState) -> Literal["prompt_node"] | object:
        if len(state.error) == 1 and not state.error[0]:
            return END

        return "prompt_node"

    async def _prompt_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        _settings = self._settings(config)
        service: NifiClientService = _settings.service

        prompt: str = await service.agent_prompt(
            json.dumps(state.processors_data, indent=2),
            json.dumps(state.error, indent=2),
            json.dumps(state.connections, indent=2),
        )

        messages: list[AnyMessage] = [SystemMessage(oss_sytem_prompt)]

        if state.nifi_flow_fix:
            previous_fixes_json = json.dumps(
                state.nifi_flow_fix, indent=2, ensure_ascii=False)

            messages.append(SystemMessage(content=previus_steps.format(
                previousFixesJson=previous_fixes_json)))

        messages.append(HumanMessage(prompt))
        state.messages.extend(messages)

        return FlowState(error=state.error,
                         processors_data=state.processors_data,
                         connections=state.connections,
                         messages=state.messages)

    async def _flow_correction_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        logger.info(node="flow_correction")

        _settings = self._settings(config)
        service: NifiClientService = _settings.service
        llm: BaseChatModel = _settings.llm
        exit_stack = AsyncExitStack()

        tools = await exit_stack.enter_async_context(service.get_tools_session())
        if not all(isinstance(t, BaseTool) for t in tools):
            raise TypeError(
                f"Expected a list of tools, but got {type(tools).__name__}")

        tools_list: list[BaseTool] = [
            t for t in tools if isinstance(t, BaseTool)]
        tools_list = self._filter_agent_tools(tools_list, service)
        llm_with_tools = llm.bind_tools(tools=tools_list, tool_choice="any")
        response = await llm_with_tools.ainvoke(state.messages)

        if not response.content: #bad boys bad boys
            response.content = '\n'

        state.messages.append(response)
        await exit_stack.aclose()

        return FlowState(connections=state.connections,
                         error=state.error,
                         processors_data=state.processors_data,
                         messages=state.messages)

    def _should_call_tools(self, state: FlowState) -> Literal["tool_call_node"] | Literal["postproc_node"]:
        last_message = state.messages[-1]

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tool_call_node"

        return "postproc_node"

    async def _tool_call_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        logger.info(node="tool_calls")

        _settings = self._settings(config)
        service: NifiClientService = _settings.service
        last_message = state.messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            raise RuntimeError("Could not parse LLM messages")

        tool_calls = last_message.tool_calls
        interrupt_value = InterruptRequest(action_requests=tool_calls,
                                           allowed_decisions=["approve", "reject"])

        human_decision = interrupt(interrupt_value)
        if human_decision == "reject":
            tool_messages: list[ToolMessage] = []
            for tool_call in tool_calls:
                tool_messages.append(ToolMessage(content="Your action was rejected by a human",
                                                 tool_call_id=tool_call["id"]))

            state.messages.extend(tool_messages)
            return FlowState(connections=state.connections,
                             error=state.error,
                             processors_data=state.processors_data,
                             messages=state.messages)

        exit_stack = AsyncExitStack()
        tools = await exit_stack.enter_async_context(service.get_tools_session())
        if not all(isinstance(t, BaseTool) for t in tools):
            raise TypeError(
                f"Expected a list of tools, but got {type(tools).__name__}")
        tools_list: list[BaseTool] = [
            t for t in tools if isinstance(t, BaseTool)]

        for tool_call in tool_calls:
            for tool in tools_list:
                if tool.name == tool_call["name"]:
                    try:
                        result: ToolMessage = await tool.ainvoke(tool_call)
                        state.messages.append(result)
                    except Exception as e:
                        state.messages.append(ToolMessage(
                            content=f"Error executing {tool_call['name']}: {e!s}. Please fix the input and try again.",
                            tool_call_id=tool_call["id"])
                        )

        await exit_stack.aclose()
        return FlowState(connections=state.connections,
                             error=state.error,
                             processors_data=state.processors_data,
                             messages=state.messages)

    async def _postproc_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        _settings = self._settings(config)
        service: NifiClientService = _settings.service

        tool_calls: list[AnyMessage] = self._response_tool_calls(
            state, service)
        await asyncio.sleep(settings.GRAPH_DELAY * 60)

        return FlowState(nifi_flow_fix=tool_calls,
                         connections=state.connections,
                         error=state.error,
                         processors_data=state.processors_data)

    @staticmethod
    def _response_tool_calls(
        state: FlowState, service: NifiClientService
    ) -> list[AnyMessage]:
        tool_calls: list[AnyMessage] = []
        if state.nifi_flow_fix:
            tool_calls = state.nifi_flow_fix

        for msg in state.messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for call in msg.tool_calls:
                    if not service.is_data_tool_call(call["name"]):
                        tool_calls.append(AIMessage(content="", tool_calls=[call]))
                        resp = NifiGraph._response_tool_result(
                            state, call["id"]) if call["id"] else None
                        if resp:
                            tool_calls.append(resp)

        return tool_calls

    @staticmethod
    def _response_tool_result(state: FlowState, c_id: str) -> ToolMessage | None:
        for msg in state.messages:
            if isinstance(msg, ToolMessage) and msg.tool_call_id == c_id:
                return msg

        return None

    @staticmethod
    def _filter_agent_tools(tools: list[BaseTool], service: NifiClientService) -> list[BaseTool]:
        return [t for t in tools if t.name in service.agent_tools_names]

    @staticmethod
    def _settings(config: RunnableConfig) -> NifiAgentSettings:
        _settings = config.get("configurable", {}).get("settings", None)

        if _settings is None:
            raise ValueError(
                "Configuration Error: 'settings' not found in RunnableConfig. "
                "Ensure that NifiAgentSettings is passed during graph invocation."
            )

        if not isinstance(_settings, NifiAgentSettings):
            raise TypeError(
                f"Configuration Error: Expected 'NifiAgentSettings', " f"but received '{type(_settings).__name__}'."
            )

        return _settings

    def create_graph(self) -> CompiledStateGraph[FlowState, None, FlowState, FlowState]:
        self.add_node("data_node", self._data_node)
        self.add_node("prompt_node", self._prompt_node)
        self.add_node(
            "flow_correction",
            self._flow_correction_node,
            retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0),
        )
        self.add_node("tool_call_node", self._tool_call_node)
        self.add_node("postproc_node", self._postproc_node)

        self.add_edge(START, "data_node")
        self.add_conditional_edges("data_node", self._should_continue, {
                                   "prompt_node": "prompt_node", END: END})
        self.add_edge("prompt_node", "flow_correction")
        self.add_conditional_edges("flow_correction", self._should_call_tools, {
            "tool_call_node": "tool_call_node",
            "postproc_node": "postproc_node"
        })
        self.add_edge("tool_call_node", "flow_correction")
        self.add_edge("postproc_node", "data_node")

        return self.compile(checkpointer=self._checkpointer)

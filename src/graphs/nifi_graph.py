from __future__ import annotations

import asyncio
import json

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Literal
from typing import final
from typing import override

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.messages import AnyMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolCall
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph.types import RetryPolicy

from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.prompts.nifi_graph_prompts import oss_sytem_prompt
from graphs.prompts.nifi_graph_prompts import previus_steps
from graphs.services.nifi_server_service import NifiServerService
from graphs.state.nifi_graph_state import FlowState
from logger import logger
from settings import settings


class ToolMonitoringMiddleware(AgentMiddleware):
    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        try:
            return await handler(request)
        except Exception as e:
            return ToolMessage(
                content=f"Error executing {request.tool_call['name']}: {e!s}. " "Please fix the input and try again.",
                tool_call_id=request.tool_call["id"],
            )


@final
class NifiGraph(StateGraph[FlowState, None, FlowState, FlowState]):
    def __init__(self, config_schema: type[None] | None = None) -> None:
        super().__init__(FlowState, config_schema)
        self._middleware = ToolMonitoringMiddleware()

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

    async def _data_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        service: NifiServerService = self._settings(config).service

        log_data: list[str] = await service.get_log_errors()
        processors_data: list[dict[str, str]] = await service.processors()
        conn_data: list[dict[str, str]] = await service.connections()

        return FlowState(error=log_data, processors_data=processors_data, connections=conn_data)

    def _should_continue(self, state: FlowState) -> Literal["flow_correction"] | object:
        if len(state.error) == 1 and not state.error[0]:
            return END

        return "flow_correction"

    async def _flow_correction_node(self, state: FlowState, config: RunnableConfig) -> FlowState:
        _settings = self._settings(config)
        service: NifiServerService = _settings.service
        llm: BaseChatModel = _settings.llm

        prompt: str = await service.agent_prompt(
            json.dumps(state.processors_data, indent=2),
            json.dumps(state.error, indent=2),
            json.dumps(state.connections, indent=2),
        )

        messages: list[AnyMessage] = [SystemMessage(oss_sytem_prompt)]

        if state.nifi_flow_fix:
            previous_fixes_json = json.dumps(state.nifi_flow_fix, indent=2, ensure_ascii=False)
            messages.append(SystemMessage(content=previus_steps.format(previousFixesJson=previous_fixes_json)))

        messages.append(HumanMessage(prompt))

        async with service.get_tools() as tools:
            if not all(isinstance(t, BaseTool) for t in tools):
                raise TypeError(f"Expected a list of tools, but got {type(tools).__name__}")

            tools_list: list[BaseTool] = [t for t in tools if isinstance(t, BaseTool)]

            tools_list = self._filter_agent_tools(tools_list, service)
            agent = create_agent(model=llm, tools=tools_list, middleware=[self._middleware])  # type: ignore[var-annotated]

            response = await agent.ainvoke({"messages": messages})  # type: ignore[arg-type]
            tool_calls: list[ToolCall] = self._response_tool_calls(response, state, service)

        await asyncio.sleep(settings.GRAPH_DELAY * 60) #убрать
        return FlowState(nifi_flow_fix=tool_calls,
                         connections=state.connections,
                         error=state.error,
                         processors_data=state.processors_data)

    def _response_tool_calls(
        self, response: dict[str, Any] | Any, state: FlowState, service: NifiServerService
    ) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        if state.nifi_flow_fix:
            tool_calls = state.nifi_flow_fix

        for msg in response["messages"]:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                logger.info(calls=msg.tool_calls)
                for call in msg.tool_calls:
                    if not service.is_data_tool_call(call["name"]):
                        tool_calls.append(call)
        return tool_calls

    def _filter_agent_tools(self, tools: list[BaseTool], service: NifiServerService) -> list[BaseTool]:
        return [t for t in tools if t.name in service.agent_tools_names]

    def generate_graph(self) -> CompiledStateGraph[FlowState, None, FlowState, FlowState]:
        self.add_node("data_node", self._data_node)
        self.add_node(
            "flow_correction",
            self._flow_correction_node,
            retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0),
        )

        self.add_edge(START, "data_node")
        self.add_conditional_edges("data_node", self._should_continue, {"flow_correction": "flow_correction", END: END})
        self.add_edge("flow_correction", "data_node")

        return self.compile()

from __future__ import annotations

from typing import final
from typing import override

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from graphs.managers.base_manager import BaseManager
from graphs.managers.exceptions.nifi_exception import GraphError
from graphs.managers.exceptions.nifi_exception import NoInterrupt
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.managers.settings.session_settings import GraphExecutionError
from graphs.managers.settings.session_settings import GraphState
from graphs.managers.settings.session_settings import Session
from graphs.middleware.tool_middleware import InterruptRequest
from graphs.state.nifi_graph_state import FlowState


@final
class NifiGraphManager(BaseManager[NifiAgentSettings, FlowState,
                                   InterruptRequest | GraphExecutionError | GraphState]):
    def __init__(self, graph: CompiledStateGraph[FlowState, None, FlowState, FlowState]) -> None:
        super().__init__(graph)

    @override
    async def graph_ainvoke(self, session: Session, settings: NifiAgentSettings,
                            human_input: str | None = None) -> None:
        config: RunnableConfig = RunnableConfig(
            configurable={"thread_id": session.uuid, "settings": settings})
        await self.verify_config(session, settings, human_input)

        if human_input:
            await self._graph.ainvoke(Command(resume=human_input), config=config)
        else:
            await self._graph.ainvoke(FlowState(), config=config)

    async def _get_state(self, config: RunnableConfig) -> InterruptRequest | GraphExecutionError | GraphState:
        state = await self._graph.aget_state(config)
        for task in state.tasks:
            if task.error:
                return GraphExecutionError(
                    msg=(
                        "Произошла ошибка при работе графа, необходим повторный запуск:\n"
                        f"{task.error!s}"
                        )
                    )

        for task in state.tasks:
            if task.interrupts:
                value = task.interrupts[0].value

                if isinstance(value, InterruptRequest):
                    return value

                if isinstance(value, dict):
                    return InterruptRequest(**value)


        return GraphState(is_working=bool(state.next))

    @override
    async def interrupt(self, session: Session,
                        settings: NifiAgentSettings) -> InterruptRequest | GraphExecutionError | GraphState:
        config: RunnableConfig = RunnableConfig(
            configurable={"thread_id": session.uuid, "settings": settings})
        return await self._get_state(config)

    @override
    async def verify_config(self, session: Session, settings: NifiAgentSettings,
                            human_input: str | None = None) -> None:
        config: RunnableConfig = RunnableConfig(
            configurable={"thread_id": session.uuid, "settings": settings})
        state = await self._get_state(config)

        if isinstance(state, GraphExecutionError):
            raise GraphError(
                "Произошла ошибка при работе графа, продолжение выполнения невозможно")

        if human_input and not state:
            raise NoInterrupt(
                "Прерывание графа не было найдено, при этом предоставлено сообщение от пользователя")

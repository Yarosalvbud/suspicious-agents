from __future__ import annotations

from typing import final
from typing import override

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from graphs.managers.base_manager import BaseManager
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.managers.settings.session_settings import Session
from graphs.middleware.tool_middleware import InterruptRequest
from graphs.state.nifi_graph_state import FlowState


@final
class NifiGraphManager(BaseManager[NifiAgentSettings, FlowState, InterruptRequest | None]):
    def __init__(self, graph: CompiledStateGraph[FlowState, None, FlowState, FlowState]) -> None:
        super().__init__(graph)

    @override
    async def graph_ainvoke(self, session: Session, settings: NifiAgentSettings,
                            human_input: str | None = None) -> InterruptRequest | None:
        config: RunnableConfig = RunnableConfig(configurable={"thread_id": session.uuid, "settings": settings})

        if human_input:
            await self._graph.ainvoke(Command(resume=human_input), config=config)
        else:
            await self._graph.ainvoke(FlowState(), config=config)

        state = await self._graph.aget_state(config)
        for task in state.tasks:
            if task.interrupts:
                value = task.interrupts[0].value

                if isinstance(value, InterruptRequest):
                    return value

                if isinstance(value, dict):
                    return InterruptRequest(**value)

        return None

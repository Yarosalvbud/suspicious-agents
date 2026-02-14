from __future__ import annotations

from typing import final
from typing import override

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from graphs.managers.base_manager import BaseManager
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.state.nifi_graph_state import FlowState


@final
class NifiGraphManager(BaseManager[NifiAgentSettings, FlowState, None]):
    def __init__(self, graph: CompiledStateGraph[FlowState, None, FlowState, FlowState]) -> None:
        super().__init__(graph)

    @override
    async def graph_ainvoke(self, settings: NifiAgentSettings) -> None:
        config: RunnableConfig = RunnableConfig(configurable={"settings": settings})

        await self._graph.ainvoke(FlowState(), config=config)

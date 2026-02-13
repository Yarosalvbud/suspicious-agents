from __future__ import annotations

from typing import cast
from typing import final
from typing import override

from graphs.state.state import FlowState
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from managers.base_manager import BaseManager
from managers.settings.nifi_agent_settings import NifiAgentSettings
from pydantic import BaseModel


@final
class NifiGraphManager(BaseManager[NifiAgentSettings]):
    def __init__(self, graph: CompiledStateGraph[FlowState]) -> None:
        super().__init__()

        self._graph = graph

    @override
    async def graph_invoke(self, settings: NifiAgentSettings) -> BaseModel | None:
        config: RunnableConfig = RunnableConfig(configurable={"settings": settings})

        await self._graph.ainvoke(cast(FlowState, {}), config=config)

        return None

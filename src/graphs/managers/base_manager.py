from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import Field
from typing import Any
from typing import ClassVar
from typing import Protocol

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel


class DataclassLike(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class BaseManager[SettingsT: DataclassLike, GraphStateT: BaseModel, ResultT: BaseModel | None](ABC):
    def __init__(self, graph: CompiledStateGraph[GraphStateT, None, GraphStateT, GraphStateT]) -> None:
        self._graph = graph

    @abstractmethod
    async def graph_ainvoke(self, settings: SettingsT) -> ResultT:
        pass

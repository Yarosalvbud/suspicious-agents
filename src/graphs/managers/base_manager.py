from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import Field
from typing import Any
from typing import ClassVar
from typing import Protocol

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from graphs.managers.settings.session_settings import Session


class DataclassLike(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class BaseManager[SettingsT: DataclassLike, GraphStateT: BaseModel, ResultT: BaseModel | None](ABC):
    def __init__(self, graph: CompiledStateGraph[GraphStateT, None, GraphStateT, GraphStateT]) -> None:
        self._graph = graph

    @abstractmethod
    async def graph_ainvoke(self, session: Session, settings: SettingsT, human_input: str | None = None) -> ResultT:
        pass

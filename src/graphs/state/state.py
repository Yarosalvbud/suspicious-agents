from __future__ import annotations

from typing import Any
from typing import TypedDict

from langchain_core.messages import ToolCall
from pydantic import BaseModel
from pydantic import Field


class FlowState(TypedDict):
    nifi_flow_fix: list[ToolCall]
    connections: list[dict[str, Any]]
    error: list[str]
    processors_data: list[dict[str, Any]]


class StructuredIds(BaseModel):
    """
    Identifiers of processors whose properties must be changed.
    """

    ids: list[str] = Field(description="list of identifiers")

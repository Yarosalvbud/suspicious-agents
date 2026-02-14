from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import ToolCall
from pydantic import BaseModel
from pydantic import Field


class FlowState(TypedDict):
    nifi_flow_fix: list[ToolCall]
    connections: list[dict[str, str]]
    error: list[str]
    processors_data: list[dict[str, str]]


class StructuredIds(BaseModel):
    """
    Identifiers of processors whose properties must be changed.
    """

    ids: list[str] = Field(description="list of identifiers")

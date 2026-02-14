from __future__ import annotations

from typing import Any

from langchain_core.messages import ToolCall
from pydantic import BaseModel
from pydantic import Field


class FlowState(BaseModel):
    nifi_flow_fix: list[ToolCall] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    error: list[str] = Field(default_factory=list)
    processors_data: list[dict[str, Any]] = Field(default_factory=list)

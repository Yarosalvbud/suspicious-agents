from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import ToolCall


class FlowState(TypedDict):
    nifi_flow_fix: list[ToolCall]
    connections: list[dict[str, str]]
    error: list[str]
    processors_data: list[dict[str, str]]

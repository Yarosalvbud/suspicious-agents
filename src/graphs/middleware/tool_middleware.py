from __future__ import annotations

from typing import Literal

from langchain_core.messages import ToolCall
from pydantic import BaseModel


class InterruptRequest(BaseModel):
    action_requests: list[ToolCall]
    allowed_decisions: list[Literal["approve"] | Literal["reject"] | Literal["edit"]]

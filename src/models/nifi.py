from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from graphs.middleware.tool_middleware import InterruptRequest as Interrupt


class FixNifiRequest(BaseModel):
    session_token: UUID | None
    allow: Literal["approve", "reject"] | None


class FixNifiResponse(BaseModel):
    session_token: UUID

class InterruptRequest(BaseModel):
    session_token: UUID


class GraphErrorResponse(BaseModel):
    msg: str

class InterruptResponse(BaseModel):
    interrupt: Interrupt | None = Field(default=None)
    graph_errors: GraphErrorResponse | None = Field(default=None)
    is_task_ready: bool

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class FixNifiRequest(BaseModel):
    session_token: UUID | None
    allow: Literal["approve", "reject"] | None


class FixNifiResponse(BaseModel):
    session_token: UUID

class InterruptRequest(BaseModel):
    session_token: UUID


class GraphErrorResponse(BaseModel):
    msg: str


class NoErrorsResponse(BaseModel):
    msg: str

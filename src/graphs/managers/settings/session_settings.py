from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Session:
    uuid: UUID

class GraphExecutionError(BaseModel):
    msg: str

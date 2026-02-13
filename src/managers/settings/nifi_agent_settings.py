from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from services.nifi_server_service import NifiServerService


@dataclass(frozen=True)
class NifiAgentSettings:
    llm: BaseChatModel
    service: NifiServerService

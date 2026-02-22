from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from graphs.services.nifi_client_service import NifiClientService


@dataclass(frozen=True)
class NifiAgentSettings:
    llm: BaseChatModel
    service: NifiClientService

from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers
from langchain_openai import ChatOpenAI

import client as clnt

from graphs.checkpointer.psql_checkpointer import PostgresSaver
from graphs.managers.nifi_manager import NifiGraphManager
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.nifi_graph import NifiGraph
from graphs.services.nifi_client_service import NifiClientService
from settings import settings


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    nifi_client = providers.Coroutine(
        clnt.McpClientSolution.get_client,
        name=config.server.name,
        server_name=config.server.server_name,
        server_script_path=config.server.path,
        cwd=config.server.cwd,
        LOG_FILE_PATH=settings.LOG_FILE_PATH,
        NIFI_FLOW_FILE_PATH=settings.NIFI_FLOW_FILE_PATH,
        LOG_LEVEL=settings.LOG_LEVEL,
        MINUTES_DELTA=settings.MINUTES_DELTA,
        CONTAINER_NAME=settings.CONTAINER_NAME,
        NIFI_BASE_URL=settings.NIFI_BASE_URL,
    )

    checkpointer = providers.Coroutine(
        PostgresSaver.get_saver,
        url = config.checkpointer.url
    )

    nifi_graph_builder = providers.Factory(
        NifiGraph,
        checkpointer=checkpointer,
    )

    graph = providers.Callable(
        lambda g: g.create_graph(),
        nifi_graph_builder,
    )

    llm = providers.Singleton(
        ChatOpenAI,
        model=config.llm.name,
        base_url=config.llm.base_url,
        api_key=settings.TOGETHER_API_KEY.get_secret_value(),
        temperature=config.llm.temperature,
        top_p=config.llm.top_p,
    )

    nifi_client_service = providers.Singleton(NifiClientService,
                                              nifi_client)

    settings = providers.Factory(NifiAgentSettings,
                                 llm=llm,
                                 service=nifi_client_service)

    manager = providers.Singleton(NifiGraphManager, graph)

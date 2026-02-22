from __future__ import annotations

import asyncio
import sys

from uuid import uuid4

from langchain_together import ChatTogether

import client as clnt

from graphs.checkpointer.psql_checkpointer import PostgresSaver
from graphs.managers.nifi_manager import NifiGraphManager
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.managers.settings.session_settings import Session
from graphs.nifi_graph import NifiGraph
from graphs.services.nifi_client_service import NifiClientService
from settings import settings


async def main() -> None:
    num_params: int = len(sys.argv) - 1
    if num_params not in (settings.CLIENT_MIN_PARAMS, settings.CLIENT_MAX_PARAMS):
        raise RuntimeError("Usage: python3 <path-to-client> <nifi-server-path> <nifi-server-working-directory>")

    client: clnt.McpClient | None = None
    if num_params == settings.CLIENT_MIN_PARAMS:
        client = await clnt.McpClientSolution.get_client(
            name="nifi",
            server_name="nifi",
            server_script_path=sys.argv[1],
            cwd=None,
            LOG_FILE_PATH=settings.LOG_FILE_PATH,
            NIFI_FLOW_FILE_PATH=settings.NIFI_FLOW_FILE_PATH,
            LOG_LEVEL=settings.LOG_LEVEL,
            MINUTES_DELTA=settings.MINUTES_DELTA,
            CONTAINER_NAME=settings.CONTAINER_NAME,
            NIFI_BASE_URL=settings.NIFI_BASE_URL,
        )
    else:
        client = await clnt.McpClientSolution.get_client(
            name="nifi",
            server_name="nifi",
            server_script_path=sys.argv[1],
            cwd=sys.argv[2],
            LOG_FILE_PATH=settings.LOG_FILE_PATH,
            NIFI_FLOW_FILE_PATH=settings.NIFI_FLOW_FILE_PATH,
            LOG_LEVEL=settings.LOG_LEVEL,
            MINUTES_DELTA=settings.MINUTES_DELTA,
            CONTAINER_NAME=settings.CONTAINER_NAME,
            NIFI_BASE_URL=settings.NIFI_BASE_URL,
        )

    checkpointer = await PostgresSaver.get_saver(url="postgresql://agent:agent_pass@localhost:5434/agent_storage")
    graph = NifiGraph(checkpointer=checkpointer).create_graph()

    manager: NifiGraphManager = NifiGraphManager(graph)
    service: NifiClientService = NifiClientService(client)

    llm = ChatTogether(
        model=settings.LANGUAGE_MODEL_LINK,
        api_key=settings.TOGETHER_API_KEY.get_secret_value(),
        temperature=1.0,
        top_p=1.0,
    )  # type: ignore[call-arg]

    session = Session(uuid=uuid4())
    _settings = NifiAgentSettings(llm=llm, service=service)
    result = await manager.graph_ainvoke(session, _settings)

    while result:
        print(result)
        response = input()
        result = await manager.graph_ainvoke(session, _settings, human_input=response)


if __name__ == "__main__":
    asyncio.run(main())

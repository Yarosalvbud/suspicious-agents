from __future__ import annotations

import asyncio
import sys

from langchain_together import ChatTogether

from adapters.langchain_adapter import LangchainMcpAdapter
from base_client.base_client import McpClient
from graphs.nifi_graph import NifiGraph
from managers.nifi_manager import NifiGraphManager
from managers.settings.nifi_agent_settings import NifiAgentSettings
from services.nifi_server_service import NifiServerService
from settings import settings


async def main() -> None:
    num_params: int = len(sys.argv) - 1
    if num_params not in (settings.CLIENT_MIN_PARAMS, settings.CLIENT_MAX_PARAMS):
        raise RuntimeError("Usage: python3 <path-to-client> <nifi-server-path> <nifi-server-working-directory>")

    client: McpClient | None = None
    if num_params == settings.CLIENT_MIN_PARAMS:
        client = await LangchainMcpAdapter.connect(
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
        client = await LangchainMcpAdapter.connect(
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

    graph = NifiGraph().generate_graph()
    manager: NifiGraphManager = NifiGraphManager(graph)
    service: NifiServerService = NifiServerService(client)

    llm = ChatTogether(
        model=settings.LANGUAGE_MODEL_LINK,
        api_key=settings.TOGETHER_API_KEY.get_secret_value(),
        temperature=1.0,
        top_p=1.0,
    )  # type: ignore[call-arg]
    _settings = NifiAgentSettings(llm=llm, service=service)

    await manager.graph_invoke(_settings)


if __name__ == "__main__":
    asyncio.run(main())

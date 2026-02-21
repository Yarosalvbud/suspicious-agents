from __future__ import annotations

import json

from contextlib import asynccontextmanager
from typing import Any
from typing import AsyncIterator
from typing import Final
from typing import Sequence
from typing import final

from client.base_client import McpClient


@final
class NifiServerService:
    _LOG_PATH: Final = "file://app-log"
    _PROCESSORS: Final = "list_all_processors"
    _CONNECTIONS: Final = "connections"
    _PROCESSOR: Final = "processor"
    _PROCESSOR_TYPE_DESCRIPTION = "processor_type_description"
    _DATA_TOOLS_NAMES: Final = ["connections", "list_all_processors", "processor", "processor_type_description"]
    _AGENT_PROMPT: Final = "agent_prompt"
    _AGENT_TOOLS_NAMES: Final = [
        "processor_type_description",
        "update_processors_properties",
        "add_processor",
        "add_connection",
        "remove_connection",
        "configure_processor",
    ]

    def __init__(self, client: McpClient) -> None:
        self._client = client

    @property
    def agent_tools_names(self) -> list[str]:
        return self._AGENT_TOOLS_NAMES

    async def get_log_errors(self) -> list[str]:
        log_errors_raw = await self._client.resources([self._LOG_PATH])

        if isinstance(log_errors_raw[0], str):
            return json.loads(log_errors_raw[0])

        raise ValueError("Wrong log data format, expected str")

    async def processors(self) -> list[dict[str, str]]:
        processors_raw = await self._client.call_tool(self._PROCESSORS, {})

        if not isinstance(processors_raw, list):
            raise ValueError("Could not parse processors data."
                             f"Expected type list, got: {type(processors_raw).__name__}")

        return [json.loads(elem["text"]) for elem in processors_raw]

    async def connections(self) -> list[dict[str, str]]:
        connections_raw = await self._client.call_tool(self._CONNECTIONS, {})
        if not isinstance(connections_raw, list):
            raise ValueError("Could not parse processors data."
                             f"Expected type list, got: {type(connections_raw).__name__}")


        return json.loads(connections_raw[0]["text"])["connections"]

    async def agent_prompt(self, processors_desc: str, error: str, connections: str) -> str:
        prompt_args: dict[str, Any] = {
            "processors_desc": processors_desc,
            "error": error,
            "connections": connections,
        }

        prompt: list[str] = await self._client.prompt(self._AGENT_PROMPT, prompt_args)
        return prompt[0]

    def is_data_tool_call(self, tool_name: str) -> bool:
        return any(tool_name == _tool_name for _tool_name in self._DATA_TOOLS_NAMES)

    @asynccontextmanager
    async def get_tools(self) -> AsyncIterator[Sequence[object]]:
        async with self._client.tools() as tools:
            yield tools

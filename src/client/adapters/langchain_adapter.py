from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import Sequence
from typing import override

from langchain_core.documents.base import Blob
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import ToolCall
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.session import ClientSession

from client.base_client import McpClient
from client.base_client import Tool
from client.client_solution.mcp_client_solution import McpClientSolution


@McpClientSolution.register("nifi")
class LangchainMcpAdapter(McpClient):
    def __init__(self, server_name: str) -> None:
        super().__init__(server_name)
        self._client: MultiServerMCPClient | None = None

    @property
    def client(self) -> MultiServerMCPClient:
        if not self._client:
            raise RuntimeError("Client not initialized")

        return self._client

    @classmethod
    @override
    async def connect(
        cls, server_name: str, server_script_path: str, cwd: str | None = None, **kwargs: str
    ) -> McpClient:
        self = cls(server_name)
        self._client = MultiServerMCPClient(
            connections={
                self._server_name: StdioConnection(
                    transport="stdio", command="python", args=[server_script_path], env=kwargs, cwd=cwd
                )
            }
        )

        return self

    @override
    async def list_tools(self) -> list[Tool]:
        langchain_tools: list[BaseTool] = await self.client.get_tools(server_name=self._server_name)

        return [Tool(name=tool.name, description=tool.description, args=tool.args) for tool in langchain_tools]

    @override
    async def resources(self, urls: list[str]) -> list[str | bytes | None]:
        blobs: list[Blob] = await self.client.get_resources(server_name=self._server_name, uris=urls)

        return [blob.data for blob in blobs]

    @override
    async def prompt(self, prompt_name: str, params: dict[str, str]) -> list[str]:
        prompts: list[AIMessage | HumanMessage] = await self.client.get_prompt(
            server_name=self._server_name, prompt_name=prompt_name, arguments=params
        )

        return [str(prompt.content) for prompt in prompts]

    async def _list_tools(self) -> list[BaseTool]:
        return await self.client.get_tools(server_name=self._server_name)

    @override
    async def call_tool(self, tool_name: str, params: dict[str, str]) -> object:
        tools: list[BaseTool] = await self._list_tools()
        tool = next(tool for tool in tools if tool.name == tool_name)

        tool_call = ToolCall(name=tool_name, args=params, id=None, type="tool_call")

        return await tool.ainvoke(tool_call)

    @override
    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        async with self.client.session(self._server_name) as session:
            yield session

    @override
    @asynccontextmanager
    async def tools(self) -> AsyncIterator[Sequence[BaseTool]]:
        async with self.client.session(self._server_name) as session:
            tools = await load_mcp_tools(session)
            yield tools

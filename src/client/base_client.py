from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import Any
from typing import AsyncIterator

from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    args: dict[str, str]


class McpClient(ABC):
    @classmethod
    @abstractmethod
    async def connect(
        cls, server_name: str, server_script_path: str, cwd: str | None = None, **kwargs: str
    ) -> McpClient:
        pass

    @abstractmethod
    async def list_tools(self) -> list[Tool]:
        pass

    @abstractmethod
    async def resources(self, urls: list[str]) -> list[str | bytes | None]:
        pass

    @abstractmethod
    async def prompt(self, prompt_name: str, params: dict[str, str]) -> list[str]:
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: dict[str, str]) -> object:
        pass

    @abstractmethod
    @asynccontextmanager
    async def session(self) -> AsyncIterator[Any]:
        yield

    @abstractmethod
    @asynccontextmanager
    async def tools(self) -> AsyncIterator[list[Any]]:
        yield []

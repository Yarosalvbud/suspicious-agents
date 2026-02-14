from __future__ import annotations

from typing import Callable
from typing import ClassVar

from client.base_client import McpClient


class McpClientSolution:
    _clients: ClassVar[dict[str, type[McpClient]]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[McpClient]], type[McpClient]]:
        def wrapper(client: type[McpClient]) -> type[McpClient]:
            cls._clients[name.lower()] = client
            return client

        return wrapper

    @classmethod
    async def get_client(
        cls,
        name: str,
        server_name: str,
        server_script_path: str,
        cwd: str | None = None,
        **kwargs: str
    ) -> McpClient:
        client = cls._clients.get(name.lower())

        if not client:
            raise KeyError(
                f"Client '{name}' not found."
            )

        return await client.connect(
            server_name=server_name.lower(),
            server_script_path=server_script_path,
            cwd=cwd,
            **kwargs
        )

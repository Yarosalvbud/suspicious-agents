from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Literal
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command
from langgraph.types import interrupt
from pydantic import BaseModel


class ToolInterruptConfig(BaseModel):
    allowed_decisions: list[Literal["approve"] | Literal["reject"] | Literal["edit"]]


class InterruptRequest(BaseModel):
    action_requests: dict[str, Any]
    allowed_decisions: list[Literal["approve"] | Literal["reject"] | Literal["edit"]]

class ToolMonitoringMiddleware(AgentMiddleware):
    def __init__(self, interrupt_on: dict[str, ToolInterruptConfig]):
        super().__init__()
        self._interrupt_on = interrupt_on

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool_call["name"]
        config = self._interrupt_on.get(tool_name)

        if config:
            interrupt_value = InterruptRequest(action_requests=dict(request.tool_call),
                                               allowed_decisions=config.allowed_decisions)
            human_decision = interrupt(interrupt_value)
            if human_decision == "approve":
                return await self._call_tool(request, handler)
            return ToolMessage(
                content="Your action was rejected by a human",
                tool_call_id=request.tool_call["id"],
            )

        return await self._call_tool(request, handler)

    @staticmethod
    async def _call_tool(request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        try:
            return await handler(request)
        except Exception as e:
            return ToolMessage(
                content=f"Error executing {request.tool_call['name']}: {e!s}. Please fix the input and try again.",
                tool_call_id=request.tool_call["id"],
        )

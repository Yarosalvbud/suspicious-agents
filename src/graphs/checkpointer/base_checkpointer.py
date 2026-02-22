from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from langgraph.checkpoint.base import BaseCheckpointSaver


class BaseSaver(ABC):

    @classmethod
    @abstractmethod
    async def get_saver(cls, url: str, **kwargs: int | str | bool) -> BaseCheckpointSaver[str]:
        pass

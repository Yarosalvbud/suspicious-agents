from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TypeVar

from pydantic import BaseModel


SettingsT = TypeVar("SettingsT")


class BaseManager[SettingsT](ABC):
    @abstractmethod
    async def graph_invoke(self, settings: SettingsT) -> BaseModel | None:
        raise NotImplementedError

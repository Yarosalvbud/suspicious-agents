from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TypeVar

from pydantic import BaseModel


SettingsT = TypeVar("SettingsT", bound=object)


class BaseManager[SettingsT](ABC):
    @abstractmethod
    async def graph_ainvoke(self, settings: SettingsT) -> BaseModel | None:
        pass

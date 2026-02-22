from __future__ import annotations

from typing import override

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from graphs.checkpointer.base_checkpointer import BaseSaver
from logger import logger


class _ConnectionCheckpointPool:
    @classmethod
    async def get_connection_pool(cls, url: str,
                                  **kwargs: str | int | bool) -> AsyncConnectionPool[AsyncConnection[DictRow]]:
        try:
            connection_pool: AsyncConnectionPool[AsyncConnection[DictRow]] = AsyncConnectionPool(
                url,
                open=False,
                max_size=int(kwargs.get("max_size", 10)),
                kwargs={
                    "autocommit": kwargs.get("autocommit", True),
                    "row_factory": dict_row,
                },
            )
            await connection_pool.open()
        except Exception as e:
            logger.error("Can not create connection pool", error=str(e))
            raise e

        return connection_pool


class PostgresSaver(BaseSaver):

    @classmethod
    @override
    async def get_saver(cls, url: str, **kwargs: int | str | bool) -> AsyncPostgresSaver:
        pool = await _ConnectionCheckpointPool.get_connection_pool(url, **kwargs)
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        return checkpointer

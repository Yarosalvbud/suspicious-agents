from __future__ import annotations

import json
import logging

from datetime import datetime
from pathlib import Path
from typing import Any
from typing import override

import structlog

from settings import settings


def get_log_file_path() -> Path:
    log_dir = Path(settings.LOG_DIR)
    return log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"


class JsonHandler(logging.Handler):
    def __init__(self, file_path: Path):
        super().__init__()
        self.filePath = file_path

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "filename": record.pathname,
                "line": record.lineno,
            }
            if hasattr(record, "extra"):
                log_entry.update(record.extra)

            with open(self.filePath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        super().close()


def get_structlog_processors() -> list[Any]:
    return [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def setup_logging() -> None:
    file_handler = JsonHandler(get_log_file_path())
    file_handler.setLevel(settings.LOGGER_LOG_LEVEL)

    processors = get_structlog_processors()
    logging.basicConfig(format="%(message)s", level=settings.LOGGER_LOG_LEVEL, handlers=[file_handler])

    structlog.configure(
        processors=[*processors, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


setup_logging()
logger = structlog.get_logger()

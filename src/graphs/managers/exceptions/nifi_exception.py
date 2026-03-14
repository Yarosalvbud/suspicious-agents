from __future__ import annotations


class NifiException(Exception):
    pass


class NoInterrupt(NifiException):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class GraphError(NifiException):
    def __init__(self, message: str) -> None:
        super().__init__(message)

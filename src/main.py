from __future__ import annotations

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from container import Container
from limiter import limiter
from routers.nifi import router


container = Container()
container.config.from_yaml("config.yml")

container.wire(modules=["routers.nifi"])

async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, exc)

app = FastAPI()

app.container = container # type: ignore[attr-defined]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

app.include_router(router, prefix="/nifi")

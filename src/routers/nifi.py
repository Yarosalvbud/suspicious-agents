from __future__ import annotations

from uuid import uuid4

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from container import Container
from graphs.managers.exceptions.nifi_exception import GraphError
from graphs.managers.exceptions.nifi_exception import NoInterrupt
from graphs.managers.nifi_manager import NifiGraphManager
from graphs.managers.settings.nifi_agent_settings import NifiAgentSettings
from graphs.managers.settings.session_settings import GraphExecutionError
from graphs.managers.settings.session_settings import Session
from graphs.middleware.tool_middleware import InterruptRequest as Interrupt
from models.nifi import FixNifiRequest
from models.nifi import FixNifiResponse
from models.nifi import GraphErrorResponse
from models.nifi import InterruptRequest
from models.nifi import NoErrorsResponse


router = APIRouter()



@router.post("/run_agent", response_model=FixNifiResponse, status_code=status.HTTP_202_ACCEPTED)
@inject
async def run_agent(
    request: Request,
    nifi: FixNifiRequest,
    background_tasks: BackgroundTasks,
    manager: NifiGraphManager = Depends(Provide[Container.manager]),  # noqa: B008
    settings: NifiAgentSettings = Depends(Provide[Container.settings])  # noqa: B008
) -> FixNifiResponse:

    session_id = nifi.session_token or uuid4()
    session = Session(uuid=session_id)

    try:
        await manager.verify_config(session, settings, human_input=nifi.allow)
        background_tasks.add_task(
            manager.graph_ainvoke,
            session=session,
            settings=settings,
            human_input=nifi.allow
        )

    except NoInterrupt as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except GraphError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при работе графа"
        )

    return FixNifiResponse(session_token=session_id)


@router.get("/interrupt", response_model=GraphErrorResponse | Interrupt | NoErrorsResponse)
@inject
async def agent_interrupt(
    request: Request,
    interrupt_request: InterruptRequest,
    manager: NifiGraphManager = Depends(Provide[Container.manager]),  # noqa: B008
    settings: NifiAgentSettings = Depends(Provide[Container.settings])  # noqa: B008
) -> GraphErrorResponse | Interrupt | NoErrorsResponse:

    session = Session(uuid=interrupt_request.session_token)

    try:
        response = await manager.interrupt(session, settings)

        if isinstance(response, GraphExecutionError):
            return GraphErrorResponse(msg=response.msg)

        if isinstance(response, Interrupt):
            return response


        return NoErrorsResponse(msg="Nifi flow работает корректно, ошибок не обнаружено")
    except Exception:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )

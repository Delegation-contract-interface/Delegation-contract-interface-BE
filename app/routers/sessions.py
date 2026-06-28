import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from app.models.session import SessionCreate, ConfirmRequest, SessionResponse
from app.services import agent_service, contract_service
from app.dependencies import require_operator_key

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate, background_tasks: BackgroundTasks):
    """위임 계약 기반으로 에이전트 세션을 시작한다."""
    contract = contract_service.get_contract(body.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없다.")

    session_id = agent_service.create_session_id()
    session = agent_service.init_session(session_id, body.contract_id)
    background_tasks.add_task(
        agent_service.run_agent,
        session_id,
        body.contract_id,
        body.user_message,
        contract.allowed_tools,
    )
    return session


@router.get("/{session_id}/events")
async def stream_events(session_id: str):
    """세션의 경계 확인 요청 이벤트를 SSE로 스트리밍한다."""
    async def event_generator():
        for _ in range(60):
            queue = agent_service.get_event_queue(session_id)
            if queue:
                break
            await asyncio.sleep(0.1)
        else:
            yield "data: {\"error\": \"세션을 찾을 수 없다.\"}\n\n"
            return

        while True:
            event = await queue.get()
            if event is None:
                yield "data: {\"type\": \"done\"}\n\n"
                break
            payload = {"type": "confirmation_required", **event.model_dump()}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{session_id}/confirm", dependencies=[Depends(require_operator_key)])
def confirm_session(session_id: str, body: ConfirmRequest):
    """운영자가 경계 초과 작업을 승인하거나 거절한다. X-Operator-Key 헤더 필요."""
    ok = agent_service.resolve_confirmation(session_id, body.approved)
    if not ok:
        raise HTTPException(status_code=404, detail="확인 대기 중인 세션을 찾을 수 없다.")
    return {"approved": body.approved}


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    """세션 상태를 조회한다."""
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없다.")
    return session

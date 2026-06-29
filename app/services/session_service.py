from typing import List, Optional
from app.models.session import SessionResponse
from app.services.contract_service import get_supabase


def save_session(session: SessionResponse, user_message: str) -> None:
    """세션 결과를 Supabase에 저장한다."""
    get_supabase().table("sessions").upsert({
        "session_id": session.session_id,
        "contract_id": session.contract_id,
        "user_message": user_message,
        "status": session.status,
        "result": session.result,
        "logs": [log.model_dump() for log in session.logs],
        "created_at": session.created_at.isoformat(),
    }).execute()


def list_sessions() -> List[dict]:
    """세션 목록을 최신순으로 반환한다."""
    result = (
        get_supabase()
        .table("sessions")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data


def get_session_from_db(session_id: str) -> Optional[dict]:
    """Supabase에서 단일 세션을 조회한다."""
    result = (
        get_supabase()
        .table("sessions")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )
    return result.data[0] if result.data else None

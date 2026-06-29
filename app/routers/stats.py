from fastapi import APIRouter
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats():
    """세션 기반 AI 자율성 통계를 반환한다."""
    return stats_service.get_stats()

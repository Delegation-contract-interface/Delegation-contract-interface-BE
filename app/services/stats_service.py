from collections import Counter
from app.services.contract_service import get_supabase


def get_stats() -> dict:
    """sessions 테이블을 집계해 통계를 반환한다."""
    result = get_supabase().table("sessions").select("status, logs").execute()
    sessions = result.data

    total = len(sessions)
    status_counts: Counter = Counter(s["status"] for s in sessions)

    tool_call_counts: Counter = Counter()
    confirmation_approved = 0
    confirmation_rejected = 0

    for s in sessions:
        for log in s.get("logs") or []:
            if log.get("type") == "tool_call":
                tool_call_counts[log.get("tool_name", "unknown")] += 1
            elif log.get("type") == "confirmation":
                if log.get("approved"):
                    confirmation_approved += 1
                else:
                    confirmation_rejected += 1

    confirmation_total = confirmation_approved + confirmation_rejected

    return {
        "total_sessions": total,
        "status_counts": dict(status_counts),
        "confirmation": {
            "total": confirmation_total,
            "approved": confirmation_approved,
            "rejected": confirmation_rejected,
            "approval_rate": round(confirmation_approved / confirmation_total * 100, 1) if confirmation_total else 0,
        },
        "tool_usage": dict(tool_call_counts.most_common()),
    }

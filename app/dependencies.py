import os
import hmac
from fastapi import Header, HTTPException


def require_operator_key(x_operator_key: str = Header(...)) -> None:
    """운영자 API 키를 검증한다. 환경변수 OPERATOR_API_KEY와 일치해야 한다."""
    expected = os.getenv("OPERATOR_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="운영자 키가 서버에 설정되지 않았다.")
    if not hmac.compare_digest(x_operator_key, expected):
        raise HTTPException(status_code=403, detail="운영자 인증에 실패했다.")

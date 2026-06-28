from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class SessionCreate(BaseModel):
    contract_id: str
    user_message: str = Field(..., min_length=1, max_length=2000)


class ConfirmationEvent(BaseModel):
    session_id: str
    tool_name: str
    tool_args: dict
    reason: str


class ConfirmRequest(BaseModel):
    approved: bool


class SessionResponse(BaseModel):
    session_id: str
    contract_id: str
    status: Literal["running", "waiting_confirmation", "completed", "rejected", "failed"]
    result: Optional[str] = None
    created_at: datetime

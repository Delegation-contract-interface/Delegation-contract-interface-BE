from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    allowed_tools: List[str] = Field(..., min_length=1)


class ContractResponse(BaseModel):
    id: str
    name: str
    description: str
    allowed_tools: List[str]
    created_at: datetime

import os
from typing import Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv
from app.models.contract import ContractCreate, ContractResponse

load_dotenv()

_client: Optional[Client] = None


def get_supabase() -> Client:
    """Supabase 클라이언트 싱글턴을 반환한다."""
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client


def create_contract(data: ContractCreate) -> ContractResponse:
    """새 위임 계약을 저장하고 반환한다."""
    result = get_supabase().table("contracts").insert({
        "name": data.name,
        "description": data.description or "",
        "allowed_tools": data.allowed_tools,
    }).execute()
    return ContractResponse(**result.data[0])


def get_contracts() -> List[ContractResponse]:
    """위임 계약 목록을 최신순으로 반환한다."""
    result = get_supabase().table("contracts").select("*").order("created_at", desc=True).execute()
    return [ContractResponse(**row) for row in result.data]


def get_contract(contract_id: str) -> Optional[ContractResponse]:
    """ID로 단일 위임 계약을 조회한다. 없으면 None을 반환한다."""
    result = get_supabase().table("contracts").select("*").eq("id", contract_id).execute()
    if not result.data:
        return None
    return ContractResponse(**result.data[0])

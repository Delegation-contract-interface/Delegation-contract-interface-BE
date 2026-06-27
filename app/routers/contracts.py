from fastapi import APIRouter, HTTPException
from app.models.contract import ContractCreate, ContractResponse
from app.services import contract_service
from typing import List

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("", response_model=ContractResponse, status_code=201)
def create_contract(body: ContractCreate):
    """새 위임 계약을 생성한다."""
    return contract_service.create_contract(body)


@router.get("", response_model=List[ContractResponse])
def list_contracts():
    """위임 계약 목록을 최신순으로 반환한다."""
    return contract_service.get_contracts()


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: str):
    """ID로 단일 위임 계약을 조회한다."""
    contract = contract_service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없다.")
    return contract

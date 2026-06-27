from fastapi import APIRouter, HTTPException
from app.models.contract import ContractCreate, ContractResponse
from app.services import contract_service
from typing import List

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("", response_model=ContractResponse, status_code=201)
def create_contract(body: ContractCreate):
    return contract_service.create_contract(body)


@router.get("", response_model=List[ContractResponse])
def list_contracts():
    return contract_service.get_contracts()


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: str):
    contract = contract_service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없다.")
    return contract

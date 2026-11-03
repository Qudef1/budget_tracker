from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from schemas.financial_transaction import TransactionCreate, TransactionResponse, TransactionUpdate
from repositories.financial_transaction import FinancialTransactionRepository

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def get_demo_user_id() -> int:
    return 1


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = FinancialTransactionRepository(session)
    async with session.begin():
        obj = await repo.create({**payload.model_dump(), "user_id": user_id})
    return obj


@router.get("/", response_model=list[TransactionResponse])
async def get_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = FinancialTransactionRepository(session)
    return await repo.get_multi(user_id=user_id, skip=skip, limit=limit)


# IMPORTANT: specific /month route must be declared before /{transaction_id}.
@router.get("/month", response_model=list[TransactionResponse])
async def get_transactions_by_month(
    year: int = Query(ge=1, le=9998),
    month: int = Query(ge=1, le=12),
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = FinancialTransactionRepository(session)
    return await repo.get_by_month(user_id=user_id, year=year, month=month)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = FinancialTransactionRepository(session)
    obj = await repo.get_by_id(transaction_id, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    return obj


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    required_fields = {"transaction_type", "amount", "currency", "category", "operation_date"}
    null_fields = required_fields.intersection(data.keys())
    if any(data[field] is None for field in null_fields):
        raise HTTPException(status_code=422, detail="Обязательные поля нельзя устанавливать в null")

    repo = FinancialTransactionRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(transaction_id, user_id)
        if obj is None:
            raise HTTPException(status_code=404, detail="Операция не найдена")
        obj = await repo.update(obj, data)
    return obj


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = FinancialTransactionRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(transaction_id, user_id)
        if obj is None:
            raise HTTPException(status_code=404, detail="Операция не найдена")
        await repo.delete(obj)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from repositories.category import CategoryRepository
from models.financial_transaction import FinancialTransaction
from sqlalchemy import select

router = APIRouter(prefix="/categories", tags=["Categories"])

def get_demo_user_id() -> int:
    return 1


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = CategoryRepository(session)
    async with session.begin():
        obj = await repo.create({**payload.model_dump(), "user_id": user_id})
    return obj


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = CategoryRepository(session)
    return await repo.get_multi(user_id=user_id, skip=skip, limit=limit)

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = CategoryRepository(session)
    obj = await repo.get_by_id(category_id, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return obj

@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    required_fields = {"name", "transaction_type", "category_type", "month_limit"}
    null_fields = required_fields.intersection(data.keys())
    if any(data[field] is None for field in null_fields):
        raise HTTPException(status_code=422, detail="Обязательные поля нельзя устанавливать в null")

    repo = CategoryRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(category_id, user_id, for_update=True)
        if obj is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        if "transaction_type" in data and data["transaction_type"] != obj.transaction_type:
            used = await session.scalar(select(FinancialTransaction.id).where(
                FinancialTransaction.category_id == category_id
            ).limit(1))
            if used is not None:
                raise HTTPException(status_code=409, detail="Нельзя изменить тип категории с привязанными операциями")
        obj = await repo.update(obj, data)
    return obj


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_demo_user_id),
):
    repo = CategoryRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(category_id, user_id, for_update=True)
        if obj is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        await repo.delete(obj)

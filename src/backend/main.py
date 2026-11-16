from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from database import engine
from routers.financial_transactions_router import router as transactions_router
from routers.category_router import router as category_router
from routers.budget_router import router as budget_router
from services.budget import BudgetError
from routers.savings_goal_router import router as savings_goal_router
from routers.analytics_router import router as analytics_router
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from security import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Saldo API", lifespan=lifespan)
app.include_router(transactions_router)
app.include_router(category_router)
app.include_router(budget_router)
app.include_router(savings_goal_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.exception_handler(BudgetError)
async def budget_error_handler(request, exc: BudgetError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
async def health():
    return {"status": "ok"}

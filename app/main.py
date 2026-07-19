from fastapi import FastAPI

from app.api.user_routes import router as user_router
from app.api.sale_routes import router as sale_router
from app.api.wallet_routes import router as wallet_router
from app.api.payout_routes import router as payout_router
from app.api.reconciliation_routes import router as reconciliation_router
from app.api.withdrawal_routes import router as withdrawal_router

app = FastAPI(
    title="Payout Management System API",
    description="Backend API for managing sales, payouts, reconciliation, wallets, and withdrawals.",
    version="1.0.0",
)

app.include_router(user_router)
app.include_router(sale_router)
app.include_router(wallet_router)
app.include_router(payout_router)
app.include_router(reconciliation_router)
app.include_router(withdrawal_router)


@app.get("/")
async def root():
    return {
        "message": "Payout Management System API is running."
    }
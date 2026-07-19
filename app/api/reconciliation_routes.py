from fastapi import APIRouter, HTTPException, status

from app.schemas.sale import ReconciliationRequest
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(
    prefix="/reconciliation",
    tags=["Reconciliation"]
)

reconciliation_service = ReconciliationService()


@router.post("/{sale_id}")
async def reconcile_sale(
    sale_id: str,
    request: ReconciliationRequest
):
    try:
        return await reconciliation_service.reconcile_sale(
            sale_id,
            request.status
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
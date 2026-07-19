from fastapi import APIRouter, HTTPException, status

from app.schemas.sale import SaleCreate, SaleStatusUpdate
from app.services.sale_service import SaleService

router = APIRouter(prefix="/sales", tags=["Sales"])

sale_service = SaleService()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_sale(sale: SaleCreate):
    try:
        return await sale_service.create_sale(
            sale.user_id,
            sale.brand,
            sale.earning
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{sale_id}")
async def get_sale(sale_id: str):
    try:
        return await sale_service.get_sale(sale_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/user/{user_id}")
async def get_user_sales(user_id: str):
    try:
        return await sale_service.get_user_sales(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{sale_id}")
async def update_sale_status(
    sale_id: str,
    request: SaleStatusUpdate
):
    try:
        return await sale_service.update_sale_status(
            sale_id,
            request.status
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
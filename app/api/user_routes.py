from fastapi import APIRouter, HTTPException, status

from app.schemas.user import UserCreate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

user_service = UserService()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    try:
        return await user_service.create_user(user.username)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{user_id}")
async def get_user(user_id: str):
    try:
        return await user_service.get_user(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/")
async def get_all_users():
    return await user_service.get_all_users()
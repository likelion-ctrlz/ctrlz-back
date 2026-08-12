from fastapi import APIRouter, Depends

from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/balance")
def get_token_balance(current_user: User = Depends(get_current_user)):
    return {"status": "success", "data": {"token_balance": current_user.token_balance}}

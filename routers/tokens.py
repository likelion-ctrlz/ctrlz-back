from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.token import TokenTransaction, TokenWallet
from models.user import User

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/balance")
def get_token_balance(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    wallet = db.get(TokenWallet, current_user.user_id)
    return {"status": "success", "data": {"token_balance": wallet.token_balance if wallet else 0}}


@router.get("/history")
def get_token_history(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    txs = (
        db.query(TokenTransaction)
        .filter(TokenTransaction.user_id == current_user.user_id)
        .order_by(TokenTransaction.created_at.desc())
        .all()
    )

    data = [
        {
            "tx_id": str(tx.tx_id),
            "amount": tx.amount,
            "reason": tx.reason,
            "created_at": tx.created_at,
        }
        for tx in txs
    ]

    return {"status": "success", "data": data}

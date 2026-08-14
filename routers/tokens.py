from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from database import get_db
from dependencies import get_current_user
from models.token import TokenTransaction, TokenWallet
from models.user import User

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get(
    "/balance",
    summary="토큰 잔액 조회",
    description="현재 보유 토큰 잔액을 반환합니다. 지갑이 아직 없는 유저는 0으로 반환합니다 (정상적으로는 온보딩 시 자동 생성됨).",
)
def get_token_balance(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    wallet = db.get(TokenWallet, current_user.user_id)
    return {"status": "success", "data": {"token_balance": wallet.token_balance if wallet else 0}}


@router.get(
    "/history",
    summary="토큰 적립·사용 내역 조회",
    description="토큰이 적립되거나(`amount` 양수, 미션 완료 등) 사용된(`amount` 음수, 취미 신청 등) 모든 거래 내역을 최신순으로 반환합니다.",
)
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

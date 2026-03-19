from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transfer import Transfer
from app.schemas import TransferCreate


def create_transfer(db: Session, data: TransferCreate, user_id: int) -> Transfer:
    if data.from_account_id == data.to_account_id:
        raise ValueError("Origem e destino devem ser contas diferentes.")

    from_acc = (
        db.query(Account)
        .filter(Account.id == data.from_account_id, Account.user_id == user_id)
        .first()
    )
    if not from_acc:
        raise ValueError("Conta de origem inválida.")

    to_acc = (
        db.query(Account)
        .filter(Account.id == data.to_account_id, Account.user_id == user_id)
        .first()
    )
    if not to_acc:
        raise ValueError("Conta de destino inválida.")

    # Adjust balances atomically.
    from_acc.current_balance = float(from_acc.current_balance) - float(data.amount)
    to_acc.current_balance = float(to_acc.current_balance) + float(data.amount)

    transfer = Transfer(
        user_id=user_id,
        from_account_id=data.from_account_id,
        to_account_id=data.to_account_id,
        amount=float(data.amount),
        date=data.date,
        notes=data.notes,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer


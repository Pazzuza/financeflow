from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.account import Account
from app.schemas import AccountCreate, AccountOut, AccountUpdate


def get_accounts(db: Session, user_id: int) -> List[Account]:
    return db.query(Account).filter(Account.user_id == user_id).order_by(Account.created_at.desc()).all()


def create_account(db: Session, data: AccountCreate, user_id: int) -> Account:
    current_balance = float(data.initial_balance)
    account = Account(
        user_id=user_id,
        name=data.name,
        type=data.type,
        initial_balance=float(data.initial_balance),
        current_balance=current_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(db: Session, account_id: int, user_id: int, data: AccountUpdate) -> Optional[Account]:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        return None

    account.name = data.name
    account.type = data.type

    if data.initial_balance is not None:
        account.initial_balance = float(data.initial_balance)
        # If current_balance wasn't explicitly provided, we keep it in sync.
        if data.current_balance is None:
            account.current_balance = float(data.initial_balance)

    if data.current_balance is not None:
        account.current_balance = float(data.current_balance)

    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account_id: int, user_id: int) -> bool:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        return False

    # Prevent deleting accounts that still have transactions or transfers.
    has_transactions = len(account.transactions) > 0
    has_transfers = (len(account.transfers_from) if hasattr(account, "transfers_from") else 0) + (
        len(account.transfers_to) if hasattr(account, "transfers_to") else 0
    )
    if has_transactions or has_transfers > 0:
        return False

    db.delete(account)
    db.commit()
    return True


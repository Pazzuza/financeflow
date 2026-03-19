import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas import TransactionCreate, TransactionUpdate


def create_transaction(db: Session, data: TransactionCreate, user_id: int) -> List[Transaction]:
    if data.type not in ("income", "expense"):
        raise ValueError("Invalid transaction type")

    if data.category_id is not None:
        category = db.query(Category).filter(Category.id == data.category_id, Category.user_id == user_id).first()
        if not category:
            raise ValueError("Invalid category")
        if category.type != data.type:
            raise ValueError("Category type mismatch")

    if data.credit_card_id is not None:
        # credit_card_id only allowed for expense in schema, but keep a defensive check.
        if data.type != "expense":
            raise ValueError("credit_card_id is only allowed for expense transactions")
        card = db.query(CreditCard).filter(
            CreditCard.id == data.credit_card_id,
            CreditCard.user_id == user_id,
            CreditCard.is_active == True,  # noqa: E712
        ).first()
        if not card:
            raise ValueError("Invalid credit card")

    account = (
        db.query(Account)
        .filter(Account.id == data.account_id, Account.user_id == user_id)
        .first()
    )
    if not account:
        raise ValueError("Invalid account")

    transactions: List[Transaction] = []
    try:
        total_amount = float(data.amount)
        if data.installment_total and data.installment_total > 1:
            total_amount = float(data.amount) * int(data.installment_total)
        signed_effect = total_amount if data.type == "income" else -total_amount

        if data.installment_total and data.installment_total > 1:
            group_id = str(uuid.uuid4())
            # Semantics: `amount` is per installment.
            for i in range(data.installment_total):
                t = Transaction(
                    description=data.description,
                    amount=data.amount,
                    type=data.type,
                    date=data.date + relativedelta(months=i),
                    notes=data.notes,
                    category_id=data.category_id,
                    account_id=data.account_id,
                    credit_card_id=data.credit_card_id,
                    user_id=user_id,
                    installment_total=data.installment_total,
                    installment_current=i + 1,
                    installment_group=group_id,
                    is_recurring=data.is_recurring,
                )
                db.add(t)
                transactions.append(t)
        else:
            t = Transaction(
                description=data.description,
                amount=data.amount,
                type=data.type,
                date=data.date,
                notes=data.notes,
                category_id=data.category_id,
                account_id=data.account_id,
                credit_card_id=data.credit_card_id,
                user_id=user_id,
                is_recurring=data.is_recurring,
            )
            db.add(t)
            transactions.append(t)

        account.current_balance = float(account.current_balance) + signed_effect
        db.commit()
        return transactions
    except Exception:
        db.rollback()
        raise


def get_transactions(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    type_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Transaction]:
    q = (
        db.query(Transaction)
        .options(joinedload(Transaction.category), joinedload(Transaction.credit_card), joinedload(Transaction.account))
        .filter(Transaction.user_id == user_id)
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)

    if type_filter in ("income", "expense"):
        q = q.filter(Transaction.type == type_filter)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)

    return q.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()


def count_transactions(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    type_filter: Optional[str] = None,
    category_id: Optional[int] = None,
) -> int:
    q = db.query(func.count(Transaction.id)).filter(Transaction.user_id == user_id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    if type_filter in ("income", "expense"):
        q = q.filter(Transaction.type == type_filter)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    return int(q.scalar() or 0)


def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool:
    t = (
        db.query(Transaction)
        .options(joinedload(Transaction.account))
        .filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
        )
        .first()
    )
    if not t:
        return False

    if not t.account:
        return False

    signed_effect = float(t.amount) if t.type == "income" else -float(t.amount)
    # Reverse the effect.
    t.account.current_balance = float(t.account.current_balance) - signed_effect
    db.delete(t)
    db.commit()
    return True


def get_summary(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> dict:
    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "income",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).scalar() or 0.0

    expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).scalar() or 0.0

    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(income - expense, 2),
    }


def get_expense_by_category(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> list:
    results = db.query(
        Category.name,
        Category.color,
        Category.icon,
        func.sum(Transaction.amount).label("total")
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == user_id,
        Category.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).all()
    return [{"name": r.name, "color": r.color, "icon": r.icon, "total": round(r.total, 2)} for r in results]


def get_monthly_trend(db: Session, user_id: int, months: int = 6) -> list:
    from datetime import date

    months = max(1, int(months))
    today = date.today()
    month_start = datetime(today.year, today.month, 1) - relativedelta(months=months - 1)
    month_end = datetime(today.year, today.month, 1) + relativedelta(months=1)

    year_expr = func.extract("year", Transaction.date).label("year")
    month_expr = func.extract("month", Transaction.date).label("month")

    income_expr = func.coalesce(
        func.sum(case((Transaction.type == "income", Transaction.amount), else_=0.0)),
        0.0,
    ).label("income")
    expense_expr = func.coalesce(
        func.sum(case((Transaction.type == "expense", Transaction.amount), else_=0.0)),
        0.0,
    ).label("expense")

    rows = (
        db.query(year_expr, month_expr, income_expr, expense_expr)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= month_start,
            Transaction.date < month_end,
        )
        .group_by(year_expr, month_expr)
        .order_by(year_expr, month_expr)
        .all()
    )

    mapping: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for r in rows:
        mapping[(int(r.year), int(r.month))] = (float(r.income or 0.0), float(r.expense or 0.0))

    result = []
    for i in range(months - 1, -1, -1):
        ref = today - relativedelta(months=i)
        income, expense = mapping.get((ref.year, ref.month), (0.0, 0.0))
        result.append(
            {
                "month": ref.strftime("%b/%y"),
                "income": round(income, 2),
                "expense": round(expense, 2),
            }
        )
    return result


def get_transaction(db: Session, transaction_id: int, user_id: int) -> Optional[Transaction]:
    return (
        db.query(Transaction)
        .options(
            joinedload(Transaction.category),
            joinedload(Transaction.credit_card),
            joinedload(Transaction.account),
        )
        .filter(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .first()
    )


def update_transaction(db: Session, transaction_id: int, user_id: int, data: TransactionUpdate) -> Optional[Transaction]:
    txn = (
        db.query(Transaction)
        .options(joinedload(Transaction.account))
        .filter(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .first()
    )
    if not txn:
        return None

    # Keep edit semantics simple and safe.
    if txn.installment_total and txn.installment_total > 1:
        raise ValueError("Please edit each installment from the original entry (installment edits are disabled).")

    if data.category_id is not None:
        category = db.query(Category).filter(Category.id == data.category_id, Category.user_id == user_id).first()
        if not category:
            raise ValueError("Invalid category")
        if category.type != data.type:
            raise ValueError("Category type mismatch")

    if data.credit_card_id is not None:
        if data.type != "expense":
            raise ValueError("credit_card_id is only allowed for expense transactions")
        card = (
            db.query(CreditCard)
            .filter(CreditCard.id == data.credit_card_id, CreditCard.user_id == user_id, CreditCard.is_active == True)  # noqa: E712
            .first()
        )
        if not card:
            raise ValueError("Invalid credit card")

    try:
        old_account = txn.account
        if not old_account:
            raise ValueError("Transaction account missing")

        old_signed = float(txn.amount) if txn.type == "income" else -float(txn.amount)
        new_signed = float(data.amount) if data.type == "income" else -float(data.amount)

        new_account = (
            db.query(Account)
            .filter(Account.id == data.account_id, Account.user_id == user_id)
            .first()
        )
        if not new_account:
            raise ValueError("Invalid account")

        # Update account balances atomically with the transaction.
        if old_account.id == new_account.id:
            old_account.current_balance = float(old_account.current_balance) + (new_signed - old_signed)
        else:
            old_account.current_balance = float(old_account.current_balance) - old_signed
            new_account.current_balance = float(new_account.current_balance) + new_signed

        txn.description = data.description
        txn.amount = data.amount
        txn.type = data.type
        txn.date = data.date
        txn.notes = data.notes
        txn.category_id = data.category_id
        txn.credit_card_id = data.credit_card_id
        txn.account_id = data.account_id
        txn.is_recurring = data.is_recurring

        db.commit()
        db.refresh(txn)
        return txn
    except Exception:
        db.rollback()
        raise

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.credit_card import CreditCard, Invoice
from app.models.transaction import Transaction
from app.schemas import CreditCardCreate


def create_card(db: Session, data: CreditCardCreate, user_id: int) -> CreditCard:
    card = CreditCard(**data.dict(), user_id=user_id)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_cards(db: Session, user_id: int):
    return db.query(CreditCard).filter(CreditCard.user_id == user_id, CreditCard.is_active == True).all()


def get_card_usage(db: Session, card_id: int, user_id: int) -> dict:
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == user_id).first()
    if not card:
        return {}
    today = datetime.utcnow()
    # Current invoice period
    if today.day <= card.closing_day:
        start = datetime(today.year, today.month, 1)
        end = datetime(today.year, today.month, card.closing_day, 23, 59, 59)
    else:
        from dateutil.relativedelta import relativedelta
        next_m = today + relativedelta(months=1)
        start = datetime(today.year, today.month, card.closing_day + 1)
        end = datetime(next_m.year, next_m.month, card.closing_day, 23, 59, 59)

    used = db.query(func.sum(Transaction.amount)).filter(
        Transaction.credit_card_id == card_id,
        Transaction.type == "expense",
        Transaction.date >= start,
        Transaction.date <= end,
    ).scalar() or 0.0

    return {
        "card": card,
        "used": round(used, 2),
        "available": round(card.limit - used, 2),
        "percent": round((used / card.limit) * 100, 1) if card.limit else 0,
        "period_start": start,
        "period_end": end,
    }


def delete_card(db: Session, card_id: int, user_id: int) -> bool:
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == user_id).first()
    if not card:
        return False
    card.is_active = False
    db.commit()
    return True

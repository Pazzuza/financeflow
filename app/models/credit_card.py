from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CreditCard(Base):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    limit = Column(Float, nullable=False)
    closing_day = Column(Integer, nullable=False)   # dia fechamento
    due_day = Column(Integer, nullable=False)        # dia vencimento
    color = Column(String(7), default="#6366f1")
    last_four = Column(String(4), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_cards")
    transactions = relationship("Transaction", back_populates="credit_card")
    invoices = relationship("Invoice", back_populates="credit_card", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    credit_card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    total = Column(Float, default=0.0)
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)

    credit_card = relationship("CreditCard", back_populates="invoices")

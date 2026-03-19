from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # cash | bank | savings | investment

    initial_balance = Column(Float, nullable=False, default=0.0)
    current_balance = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    transfers_from = relationship(
        "Transfer", foreign_keys="Transfer.from_account_id", back_populates="from_account", cascade="all, delete-orphan"
    )
    transfers_to = relationship(
        "Transfer", foreign_keys="Transfer.to_account_id", back_populates="to_account", cascade="all, delete-orphan"
    )


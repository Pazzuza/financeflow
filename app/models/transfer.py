from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    transfer_group = Column(String(64), nullable=True)  # optional grouping token

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transfers")
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transfers_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transfers_to")


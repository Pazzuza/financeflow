import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# --- User ---
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    monthly_income: float = 0.0


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    monthly_income: Optional[float] = None
    currency: Optional[str] = None
    alert_threshold: Optional[float] = None


# --- Category ---
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Literal["income", "expense"]
    color: str = "#6366f1"
    icon: str = "💰"
    parent_id: Optional[int] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
            raise ValueError("Invalid color")
        return v


class CategoryOut(BaseModel):
    id: int
    name: str
    type: str
    color: str
    icon: str
    parent_id: Optional[int]

    class Config:
        from_attributes = True


# --- Transaction ---
class TransactionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    date: datetime
    notes: Optional[str] = Field(default=None, max_length=2000)
    category_id: Optional[int] = None
    credit_card_id: Optional[int] = None
    installment_total: Optional[int] = Field(default=None, ge=1, le=60)
    is_recurring: bool = False

    @field_validator("installment_total")
    @classmethod
    def normalize_installments(cls, v: Optional[int]) -> Optional[int]:
        # Treat 1 as non-installment.
        if v == 1:
            return None
        return v

    @field_validator("credit_card_id")
    @classmethod
    def credit_card_only_for_expense(cls, v: Optional[int], info) -> Optional[int]:
        if v is None:
            return v
        if info.data.get("type") != "expense":
            raise ValueError("credit_card_id is only allowed for expense transactions")
        return v


class TransactionOut(BaseModel):
    id: int
    description: str
    amount: float
    type: str
    date: datetime
    notes: Optional[str]
    category_id: Optional[int]
    credit_card_id: Optional[int]
    installment_total: Optional[int]
    installment_current: Optional[int]
    installment_group: Optional[str]
    is_recurring: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Credit Card ---
class CreditCardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    limit: float = Field(gt=0)
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    color: str = "#6366f1"
    last_four: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
            raise ValueError("Invalid color")
        return v

    @field_validator("last_four")
    @classmethod
    def normalize_last_four(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\d{4}$", v):
            raise ValueError("last_four must be 4 digits")
        return v


class CreditCardOut(BaseModel):
    id: int
    name: str
    limit: float
    closing_day: int
    due_day: int
    color: str
    last_four: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# --- Goal ---
class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0.0, ge=0)
    deadline: Optional[datetime] = None
    icon: str = "🎯"
    color: str = "#10b981"

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
            raise ValueError("Invalid color")
        return v


class GoalUpdate(BaseModel):
    current_amount: Optional[float] = None
    is_completed: Optional[bool] = None


class TransactionUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    date: datetime
    notes: Optional[str] = Field(default=None, max_length=2000)
    category_id: Optional[int] = None
    credit_card_id: Optional[int] = None
    is_recurring: bool = False

    @field_validator("credit_card_id")
    @classmethod
    def credit_card_only_for_expense(cls, v: Optional[int], info) -> Optional[int]:
        if v is None:
            return v
        if info.data.get("type") != "expense":
            raise ValueError("credit_card_id is only allowed for expense transactions")
        return v


class GoalOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    deadline: Optional[datetime]
    icon: str
    color: str
    is_completed: bool
    progress_percent: float

    class Config:
        from_attributes = True

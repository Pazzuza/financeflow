from sqlalchemy.orm import Session
from app.models.user import User
from app.models.category import Category
from app.schemas import UserCreate
from app.core.security import get_password_hash, verify_password, create_access_token
from typing import Optional

DEFAULT_CATEGORIES = [
    {"name": "Salário", "type": "income", "icon": "💼", "color": "#10b981"},
    {"name": "Freelance", "type": "income", "icon": "💻", "color": "#06b6d4"},
    {"name": "Investimentos", "type": "income", "icon": "📈", "color": "#8b5cf6"},
    {"name": "Outros (receita)", "type": "income", "icon": "💰", "color": "#f59e0b"},
    {"name": "Moradia", "type": "expense", "icon": "🏠", "color": "#ef4444"},
    {"name": "Alimentação", "type": "expense", "icon": "🍔", "color": "#f97316"},
    {"name": "Transporte", "type": "expense", "icon": "🚗", "color": "#eab308"},
    {"name": "Saúde", "type": "expense", "icon": "💊", "color": "#ec4899"},
    {"name": "Educação", "type": "expense", "icon": "📚", "color": "#3b82f6"},
    {"name": "Lazer", "type": "expense", "icon": "🎮", "color": "#a855f7"},
    {"name": "Vestuário", "type": "expense", "icon": "👗", "color": "#14b8a6"},
    {"name": "Contas", "type": "expense", "icon": "💡", "color": "#64748b"},
    {"name": "Outros (despesa)", "type": "expense", "icon": "💸", "color": "#6b7280"},
]


def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        name=data.name,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        monthly_income=data.monthly_income,
    )
    db.add(user)
    db.flush()
    for cat in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user.id, is_default=True, **cat))
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def generate_token(user: User) -> str:
    return create_access_token({"sub": str(user.id)})

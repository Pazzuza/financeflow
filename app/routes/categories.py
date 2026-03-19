from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import re
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.models.category import Category
from app.models.transaction import Transaction
from urllib.parse import quote

router = APIRouter(prefix="/categories", tags=["categories"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_categories(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    categories = db.query(Category).filter(Category.user_id == user.id, Category.parent_id == None).all()
    return templates.TemplateResponse("transactions/categories.html", {
        "request": request,
        "user": user,
        "categories": categories,
        "error": request.query_params.get("error"),
    })


@router.post("/new")
def create_category(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type: str = Form(...),
    color: str = Form("#6366f1"),
    icon: str = Form("💰"),
    parent_id: Optional[int] = Form(None),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    type_lower = (type or "").lower()
    if type_lower not in ("income", "expense"):
        return RedirectResponse(f"/categories?error={quote('Tipo inválido.')}", status_code=302)
    if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", color or ""):
        return RedirectResponse(f"/categories?error={quote('Cor inválida.')}", status_code=302)

    parent = None
    if parent_id is not None:
        parent = db.query(Category).filter(Category.id == parent_id, Category.user_id == user.id).first()
        if not parent:
            return RedirectResponse(f"/categories?error={quote('Categoria pai inválida.')}", status_code=302)
        if parent.type != type_lower:
            return RedirectResponse(f"/categories?error={quote('Tipo da categoria pai não corresponde.')}", status_code=302)

    cat = Category(
        name=name,
        type=type_lower,
        color=color,
        icon=icon[:50],
        parent_id=parent_id,
        user_id=user.id,
    )
    db.add(cat)
    db.commit()
    return RedirectResponse("/categories", status_code=302)


@router.post("/{cat_id}/delete")
def delete_category(cat_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    cat = db.query(Category).filter(Category.id == cat_id, Category.user_id == user.id).first()
    if cat:
        if cat.is_default:
            return RedirectResponse(f"/categories?error={quote('Categorias padrão não podem ser removidas.')}", status_code=302)
        has_transactions = db.query(Transaction.id).filter(Transaction.category_id == cat_id, Transaction.user_id == user.id).first()
        if has_transactions:
            return RedirectResponse(f"/categories?error={quote('Não é possível excluir uma categoria com transações.')}", status_code=302)
        db.delete(cat)
        db.commit()
    return RedirectResponse("/categories", status_code=302)

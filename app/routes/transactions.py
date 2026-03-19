import io
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from pydantic import ValidationError

from app.services.transaction_service import (
    count_transactions,
    create_transaction,
    delete_transaction,
    get_summary,
    get_transaction,
    get_transactions,
    update_transaction,
)
from app.services.export_service import export_transactions_csv
from app.services.card_service import get_cards
from app.models.category import Category
from app.schemas import TransactionCreate, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])
templates = Jinja2Templates(directory="templates")


def _get_user_or_redirect(request, db):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return None, RedirectResponse("/auth/login", status_code=302)
    return user, None


@router.get("", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    start: Optional[str] = None,
    end: Optional[str] = None,
    type_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir

    error: Optional[str] = None
    PAGE_SIZE = 20
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_date = (
            datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            if end
            else None
        )
    except ValueError:
        start_date = None
        end_date = None
        error = "Datas inválidas. Use o formato AAAA-MM-DD."

    if type_filter == "":
        type_filter = None
    if type_filter not in (None, "income", "expense"):
        type_filter = None

    transactions = get_transactions(
        db, user.id, start_date, end_date, type_filter, category_id,
        limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE
    )
    total_count = count_transactions(db, user.id, start_date, end_date, type_filter, category_id)
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    cards = get_cards(db, user.id)

    summary = None
    if start_date or end_date:
        from dateutil.relativedelta import relativedelta
        sd = start_date or datetime(2000, 1, 1)
        ed = end_date or datetime.utcnow()
        summary = get_summary(db, user.id, sd, ed)

    return templates.TemplateResponse("transactions/list.html", {
        "request": request,
        "user": user,
        "error": error,
        "transactions": transactions,
        "categories": categories,
        "cards": cards,
        "start": start,
        "end": end,
        "type_filter": type_filter,
        "category_id": category_id,
        "page": page,
        "total_pages": max(1, math.ceil(total_count / PAGE_SIZE)),
        "summary": summary,
    })


@router.get("/new", response_class=HTMLResponse)
def new_transaction_page(request: Request, db: Session = Depends(get_db)):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    cards = get_cards(db, user.id)
    return templates.TemplateResponse("transactions/form.html", {
        "request": request,
        "user": user,
        "categories": categories,
        "cards": cards,
        "error": None,
    })


@router.post("/new", response_class=HTMLResponse)
def create_transaction_post(
    request: Request,
    db: Session = Depends(get_db),
    description: str = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    category_id: Optional[str] = Form(None),
    credit_card_id: Optional[str] = Form(None),
    installment_total: Optional[str] = Form(None),
    is_recurring: bool = Form(False),
):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir

    def parse_optional_int(v: Optional[str]) -> Optional[int]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        return int(v)
    try:
        tx_date = datetime.strptime(date, "%Y-%m-%d")
        data = TransactionCreate(
            description=description,
            amount=amount,
            type=type,
            date=tx_date,
            notes=notes or None,
            category_id=parse_optional_int(category_id),
            credit_card_id=parse_optional_int(credit_card_id),
            installment_total=parse_optional_int(installment_total),
            is_recurring=is_recurring,
        )
        create_transaction(db, data, user.id)
        return RedirectResponse("/transactions", status_code=302)
    except ValidationError as e:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return templates.TemplateResponse(
            "transactions/form.html",
            {"request": request, "user": user, "categories": categories, "cards": cards, "error": msg},
            status_code=400,
        )
    except ValueError as e:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        return templates.TemplateResponse(
            "transactions/form.html",
            {"request": request, "user": user, "categories": categories, "cards": cards, "error": str(e)},
            status_code=400,
        )
    except Exception:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        return templates.TemplateResponse(
            "transactions/form.html",
            {"request": request, "user": user, "categories": categories, "cards": cards, "error": "Falha ao salvar a transação."},
            status_code=500,
        )


@router.get("/{transaction_id}/edit", response_class=HTMLResponse)
def edit_transaction_page(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir

    txn = get_transaction(db, transaction_id, user.id)
    if not txn:
        return RedirectResponse("/transactions", status_code=302)

    categories = db.query(Category).filter(Category.user_id == user.id).all()
    cards = get_cards(db, user.id)
    error: Optional[str] = None
    if txn.installment_total and txn.installment_total > 1:
        error = "Edição de transações parceladas desativada."

    return templates.TemplateResponse(
        "transactions/edit.html",
        {"request": request, "user": user, "transaction": txn, "categories": categories, "cards": cards, "error": error},
    )


@router.post("/{transaction_id}/edit", response_class=HTMLResponse)
def edit_transaction_post(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    description: str = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    category_id: Optional[str] = Form(None),
    credit_card_id: Optional[str] = Form(None),
    is_recurring: bool = Form(False),
):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir

    def parse_optional_int(v: Optional[str]) -> Optional[int]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        return int(v)

    try:
        txn_update = TransactionUpdate(
            description=description,
            amount=amount,
            type=type,
            date=datetime.strptime(date, "%Y-%m-%d"),
            notes=notes or None,
            category_id=parse_optional_int(category_id),
            credit_card_id=parse_optional_int(credit_card_id),
            is_recurring=is_recurring,
        )
        updated = update_transaction(db, transaction_id, user.id, txn_update)
        if not updated:
            return RedirectResponse("/transactions", status_code=302)
        return RedirectResponse("/transactions", status_code=302)
    except ValidationError as e:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        txn = get_transaction(db, transaction_id, user.id)
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return templates.TemplateResponse(
            "transactions/edit.html",
            {"request": request, "user": user, "transaction": txn, "categories": categories, "cards": cards, "error": msg},
            status_code=400,
        )
    except ValueError as e:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        txn = get_transaction(db, transaction_id, user.id)
        return templates.TemplateResponse(
            "transactions/edit.html",
            {"request": request, "user": user, "transaction": txn, "categories": categories, "cards": cards, "error": str(e)},
            status_code=400,
        )
    except Exception:
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        cards = get_cards(db, user.id)
        txn = get_transaction(db, transaction_id, user.id)
        return templates.TemplateResponse(
            "transactions/edit.html",
            {"request": request, "user": user, "transaction": txn, "categories": categories, "cards": cards, "error": "Falha ao salvar as alterações."},
            status_code=500,
        )


@router.post("/{transaction_id}/delete")
def delete_transaction_route(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir
    delete_transaction(db, transaction_id, user.id)
    return RedirectResponse("/transactions", status_code=302)


@router.get("/export")
def export_csv(
    request: Request,
    db: Session = Depends(get_db),
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    user, redir = _get_user_or_redirect(request, db)
    if redir:
        return redir
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_date = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59) if end else None
    except ValueError:
        start_date = None
        end_date = None
    csv_content = export_transactions_csv(db, user.id, start_date, end_date)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transacoes_{datetime.utcnow().strftime('%Y%m%d')}.csv"},
    )

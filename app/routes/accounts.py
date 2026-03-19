from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.schemas import AccountCreate, AccountUpdate, TransferCreate
from app.services.account_service import create_account, delete_account, get_accounts, update_account
from app.services.transfer_service import create_transfer


router = APIRouter(prefix="/accounts", tags=["accounts"])
templates = Jinja2Templates(directory="templates")


def _get_user(request: Request, db: Session):
    user = get_current_user_from_cookie(request, db)
    return user


@router.get("", response_class=HTMLResponse)
def accounts_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    accounts = get_accounts(db, user.id)
    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse(
        "accounts/list.html",
        {
            "request": request,
            "user": user,
            "accounts": accounts,
            "error": error,
            "success": success,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_account_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    accounts = get_accounts(db, user.id)
    return templates.TemplateResponse(
        "accounts/form.html",
        {"request": request, "user": user, "account": None, "error": None, "accounts": accounts, "mode": "create"},
    )


@router.get("/{account_id}/edit", response_class=HTMLResponse)
def edit_account_page(account_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    accounts = get_accounts(db, user.id)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        return RedirectResponse("/accounts", status_code=302)
    return templates.TemplateResponse(
        "accounts/form.html",
        {"request": request, "user": user, "account": account, "error": None, "accounts": accounts, "mode": "edit"},
    )


@router.post("/new")
def create_account_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type: str = Form(...),
    initial_balance: float = Form(0.0),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        data = AccountCreate(name=name, type=type, initial_balance=initial_balance)
        create_account(db, data, user.id)
        return RedirectResponse("/accounts?success=1", status_code=302)
    except ValidationError as e:
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return RedirectResponse(f"/accounts?error={quote(msg)}", status_code=302)
    except ValueError as e:
        return RedirectResponse(f"/accounts?error={quote(str(e))}", status_code=302)
    except Exception:
        return RedirectResponse(f"/accounts?error={quote('Falha ao salvar a conta.')}", status_code=302)


@router.post("/{account_id}/edit", response_class=HTMLResponse)
def update_account_post(
    account_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type: str = Form(...),
    initial_balance: float = Form(0.0),
    current_balance: Optional[float] = Form(None),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        data = AccountUpdate(name=name, type=type, initial_balance=initial_balance, current_balance=current_balance)
        updated = update_account(db, account_id, user.id, data)
        if not updated:
            return RedirectResponse("/accounts", status_code=302)
        return RedirectResponse("/accounts?success=1", status_code=302)
    except ValidationError as e:
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return RedirectResponse(f"/accounts?error={quote(msg)}", status_code=302)
    except ValueError as e:
        return RedirectResponse(f"/accounts?error={quote(str(e))}", status_code=302)
    except Exception:
        return RedirectResponse(f"/accounts?error={quote('Falha ao salvar a conta.')}", status_code=302)


@router.post("/{account_id}/delete")
def delete_account_post(account_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        ok = delete_account(db, account_id, user.id)
        if not ok:
            return RedirectResponse("/accounts", status_code=302)
        if not ok:
            return RedirectResponse("/accounts?error=1", status_code=302)
        return RedirectResponse("/accounts?success=1", status_code=302)
    except Exception:
        return RedirectResponse(f"/accounts?error={quote('Falha ao excluir a conta.')}", status_code=302)


@router.post("/transfer")
def transfer_post(
    request: Request,
    db: Session = Depends(get_db),
    from_account_id: int = Form(...),
    to_account_id: int = Form(...),
    amount: float = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        transfer_date = datetime.strptime(date, "%Y-%m-%d")
        data = TransferCreate(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            date=transfer_date,
            notes=notes or None,
        )
        create_transfer(db, data, user.id)
        return RedirectResponse("/accounts?success=1", status_code=302)
    except ValidationError as e:
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return RedirectResponse(f"/accounts?error={quote(msg)}", status_code=302)
    except ValueError as e:
        return RedirectResponse(f"/accounts?error={quote(str(e))}", status_code=302)
    except Exception:
        return RedirectResponse(f"/accounts?error={quote('Falha ao realizar transferência.')}", status_code=302)


from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.services.card_service import create_card, get_cards, get_card_usage, delete_card
from app.schemas import CreditCardCreate
from pydantic import ValidationError

router = APIRouter(prefix="/cards", tags=["cards"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_cards(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    cards = get_cards(db, user.id)
    cards_usage = [get_card_usage(db, c.id, user.id) for c in cards]
    return templates.TemplateResponse("cards/list.html", {
        "request": request,
        "user": user,
        "cards_usage": cards_usage,
    })


@router.get("/new", response_class=HTMLResponse)
def new_card_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse("cards/form.html", {"request": request, "user": user})


@router.post("/new")
def create_card_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    limit: float = Form(...),
    closing_day: int = Form(...),
    due_day: int = Form(...),
    color: str = Form("#6366f1"),
    last_four: str = Form(""),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        data = CreditCardCreate(
            name=name,
            limit=limit,
            closing_day=closing_day,
            due_day=due_day,
            color=color,
            last_four=last_four or None,
        )
        create_card(db, data, user.id)
        return RedirectResponse("/cards", status_code=302)
    except ValidationError as e:
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return templates.TemplateResponse(
            "cards/form.html",
            {"request": request, "user": user, "error": msg},
            status_code=400,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "cards/form.html",
            {"request": request, "user": user, "error": str(e)},
            status_code=400,
        )
    except Exception:
        return templates.TemplateResponse(
            "cards/form.html",
            {"request": request, "user": user, "error": "Falha ao salvar o cartão."},
            status_code=500,
        )


@router.get("/{card_id}", response_class=HTMLResponse)
def card_detail(card_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    usage = get_card_usage(db, card_id, user.id)
    if not usage:
        return RedirectResponse("/cards", status_code=302)

    from app.services.transaction_service import get_transactions
    txns = get_transactions(db, user.id, start_date=usage["period_start"], end_date=usage["period_end"])
    txns = [t for t in txns if t.credit_card_id == card_id]
    return templates.TemplateResponse("cards/detail.html", {
        "request": request,
        "user": user,
        "usage": usage,
        "transactions": txns,
    })


@router.post("/{card_id}/delete")
def delete_card_route(card_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    delete_card(db, card_id, user.id)
    return RedirectResponse("/cards", status_code=302)

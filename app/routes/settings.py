from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse("settings/index.html", {"request": request, "user": user, "success": False, "error": None})


@router.post("", response_class=HTMLResponse)
def update_settings(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    monthly_income: float = Form(0.0),
    currency: str = Form("BRL"),
    alert_threshold: float = Form(80.0),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    currency = (currency or "").upper().strip()
    allowed_currencies = {"BRL", "USD", "EUR"}
    if currency not in allowed_currencies:
        return templates.TemplateResponse(
            "settings/index.html",
            {"request": request, "user": user, "success": False, "error": "Moeda inválida."},
            status_code=400,
        )
    if monthly_income < 0:
        return templates.TemplateResponse(
            "settings/index.html",
            {"request": request, "user": user, "success": False, "error": "Renda mensal não pode ser negativa."},
            status_code=400,
        )
    if alert_threshold < 1 or alert_threshold > 100:
        return templates.TemplateResponse(
            "settings/index.html",
            {"request": request, "user": user, "success": False, "error": "Alerta de gasto deve estar entre 1 e 100."},
            status_code=400,
        )
    if not name or len(name) > 100:
        return templates.TemplateResponse(
            "settings/index.html",
            {"request": request, "user": user, "success": False, "error": "Nome inválido."},
            status_code=400,
        )

    user.name = name
    user.monthly_income = monthly_income
    user.currency = currency
    user.alert_threshold = alert_threshold
    db.commit()
    return templates.TemplateResponse("settings/index.html", {"request": request, "user": user, "success": True, "error": None})

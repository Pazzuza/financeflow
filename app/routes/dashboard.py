from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.services.transaction_service import get_summary, get_expense_by_category, get_monthly_trend, get_transactions
from app.services.goal_service import get_alerts
from app.services.card_service import get_cards, get_card_usage

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/auth/login", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    today = datetime.utcnow()
    start_month = datetime(today.year, today.month, 1)
    end_month = start_month + relativedelta(months=1) - relativedelta(seconds=1)

    summary = get_summary(db, user.id, start_month, end_month)
    by_category = get_expense_by_category(db, user.id, start_month, end_month)
    trend = get_monthly_trend(db, user.id, 6)
    recent = get_transactions(db, user.id, limit=5)
    alerts = get_alerts(db, user.id, unread_only=True)
    cards = get_cards(db, user.id)
    cards_usage = [get_card_usage(db, c.id, user.id) for c in cards]

    # Budget alert check
    if user.monthly_income > 0:
        expense_pct = (summary["expense"] / user.monthly_income) * 100
        if expense_pct >= user.alert_threshold:
            from app.models.goal import Alert
            existing = db.query(Alert).filter(
                Alert.user_id == user.id,
                Alert.type == "budget_exceeded",
                Alert.created_at >= start_month,
            ).first()
            if not existing:
                alert = Alert(
                    title="⚠️ Limite de gastos atingido",
                    message=f"Você gastou {expense_pct:.1f}% da sua renda mensal ({user.alert_threshold}% é seu limite).",
                    type="budget_exceeded",
                    user_id=user.id,
                )
                db.add(alert)
                db.commit()
                alerts = get_alerts(db, user.id, unread_only=True)

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "summary": summary,
        "by_category": by_category,
        "trend": trend,
        "recent": recent,
        "alerts": alerts,
        "cards_usage": cards_usage,
        "today": today,
    })

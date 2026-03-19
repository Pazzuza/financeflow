from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.services.transaction_service import get_summary, get_expense_by_category, get_monthly_trend, get_transactions
from app.models.category import Category

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="templates")

PERIODS = {
    "today": "Hoje",
    "week": "Esta semana",
    "month": "Este mês",
    "last_month": "Mês passado",
    "quarter": "Trimestre",
    "year": "Este ano",
    "custom": "Personalizado",
}


def resolve_period(period: str, start: Optional[str], end: Optional[str]):
    today = datetime.utcnow()
    if period == "today":
        return today.replace(hour=0, minute=0, second=0), today.replace(hour=23, minute=59, second=59)
    elif period == "week":
        start_w = today - timedelta(days=today.weekday())
        return start_w.replace(hour=0, minute=0, second=0), today.replace(hour=23, minute=59, second=59)
    elif period == "month":
        return datetime(today.year, today.month, 1), today.replace(hour=23, minute=59, second=59)
    elif period == "last_month":
        last = today - relativedelta(months=1)
        return datetime(last.year, last.month, 1), datetime(today.year, today.month, 1) - timedelta(seconds=1)
    elif period == "quarter":
        return today - relativedelta(months=3), today.replace(hour=23, minute=59, second=59)
    elif period == "year":
        return datetime(today.year, 1, 1), today.replace(hour=23, minute=59, second=59)
    elif period == "custom" and start and end:
        try:
            return (
                datetime.strptime(start, "%Y-%m-%d"),
                datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59),
            )
        except ValueError:
            # If custom range is invalid, fall back to the current month.
            return datetime(today.year, today.month, 1), today.replace(hour=23, minute=59, second=59)
    # default: current month
    return datetime(today.year, today.month, 1), today.replace(hour=23, minute=59, second=59)


@router.get("", response_class=HTMLResponse)
def reports(
    request: Request,
    db: Session = Depends(get_db),
    period: str = Query("month"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if period not in PERIODS:
        period = "month"

    start_date, end_date = resolve_period(period, start, end)
    summary = get_summary(db, user.id, start_date, end_date)
    by_category = get_expense_by_category(db, user.id, start_date, end_date)
    trend = get_monthly_trend(db, user.id, 12)
    transactions = get_transactions(db, user.id, start_date, end_date, limit=500)
    categories = db.query(Category).filter(Category.user_id == user.id).all()

    # Daily breakdown
    daily = {}
    for t in transactions:
        key = t.date.strftime("%Y-%m-%d")
        if key not in daily:
            daily[key] = {"income": 0.0, "expense": 0.0}
        daily[key][t.type] += t.amount
    daily_labels = sorted(daily.keys())
    daily_income = [round(daily[k]["income"], 2) for k in daily_labels]
    daily_expense = [round(daily[k]["expense"], 2) for k in daily_labels]
    daily_labels_fmt = [datetime.strptime(k, "%Y-%m-%d").strftime("%d/%m") for k in daily_labels]

    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "user": user,
        "summary": summary,
        "by_category": by_category,
        "trend": trend,
        "transactions": transactions,
        "period": period,
        "periods": PERIODS,
        "start": start or start_date.strftime("%Y-%m-%d"),
        "end": end or end_date.strftime("%Y-%m-%d"),
        "daily_labels": daily_labels_fmt,
        "daily_income": daily_income,
        "daily_expense": daily_expense,
        "categories": categories,
    })

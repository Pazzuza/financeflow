from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.services.goal_service import create_goal, get_goals, update_goal, delete_goal, get_alerts, mark_alerts_read
from app.schemas import GoalCreate, GoalUpdate
from pydantic import ValidationError
from urllib.parse import quote

router = APIRouter(prefix="/goals", tags=["goals"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_goals(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    goals = get_goals(db, user.id)
    alerts = get_alerts(db, user.id)
    mark_alerts_read(db, user.id)
    return templates.TemplateResponse("goals/list.html", {
        "request": request,
        "user": user,
        "goals": goals,
        "alerts": alerts,
        "error": request.query_params.get("error"),
    })


@router.post("/new")
def create_goal_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(""),
    target_amount: float = Form(...),
    current_amount: float = Form(0.0),
    deadline: str = Form(""),
    icon: str = Form("🎯"),
    color: str = Form("#10b981"),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    try:
        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d") if deadline else None
        data = GoalCreate(
            name=name,
            description=description or None,
            target_amount=target_amount,
            current_amount=current_amount,
            deadline=deadline_dt,
            icon=icon,
            color=color,
        )
        create_goal(db, data, user.id)
        return RedirectResponse("/goals", status_code=302)
    except ValidationError as e:
        msg = e.errors()[0].get("msg") if e.errors() else "Dados inválidos."
        return RedirectResponse(f"/goals?error={quote(msg)}", status_code=302)
    except ValueError as e:
        return RedirectResponse(f"/goals?error={quote(str(e))}", status_code=302)
    except Exception:
        return RedirectResponse(f"/goals?error={quote('Falha ao salvar a meta.')}", status_code=302)


@router.post("/{goal_id}/deposit")
def deposit_goal(
    goal_id: int,
    request: Request,
    db: Session = Depends(get_db),
    amount: float = Form(...),
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    if amount <= 0:
        return RedirectResponse(f"/goals?error={quote('Valor inválido para depósito.')}", status_code=302)
    from app.models.goal import FinancialGoal
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id, FinancialGoal.user_id == user.id).first()
    if goal:
        update_goal(db, goal_id, user.id, GoalUpdate(current_amount=goal.current_amount + amount))
    return RedirectResponse("/goals", status_code=302)


@router.post("/{goal_id}/delete")
def delete_goal_route(goal_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    delete_goal(db, goal_id, user.id)
    return RedirectResponse("/goals", status_code=302)

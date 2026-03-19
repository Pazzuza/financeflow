from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_from_cookie, generate_token
from app.core.config import settings
from app.services.auth_service import create_user, authenticate_user
from app.schemas import UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_post(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "E-mail ou senha inválidos."})
    token = generate_token(user)
    response = RedirectResponse("/dashboard", status_code=302)
    is_secure = bool(
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https"
    )
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=(settings.COOKIE_SECURE or is_secure),
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    monthly_income: float = Form(0.0),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "E-mail já cadastrado."})
    user = create_user(db, UserCreate(name=name, email=email, password=password, monthly_income=monthly_income))
    token = generate_token(user)
    response = RedirectResponse("/dashboard", status_code=302)
    is_secure = bool(
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https"
    )
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=(settings.COOKIE_SECURE or is_secure),
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie("access_token", path=settings.COOKIE_PATH)
    return response

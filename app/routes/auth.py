from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.user_service import create_user, authenticate_user
from app.schemas.schemas import UserCreate, UserLogin
from app.utils.session import create_session, get_current_user, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=401,
        )
    resp = RedirectResponse(url="/dashboard", status_code=302)
    create_session(resp, user.id, user.name, user.is_admin)
    return resp


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user_data = UserCreate(name=name, email=email, phone=phone or None, password=password)
        user = create_user(db, user_data)
        resp = RedirectResponse(url="/dashboard", status_code=302)
        create_session(resp, user.id, user.name, user.is_admin)
        return resp
    except ValueError as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": str(e)},
            status_code=400,
        )


@router.get("/logout")
async def logout(request: Request):
    resp = RedirectResponse(url="/", status_code=302)
    clear_session(resp)
    return resp

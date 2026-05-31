from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json

from app.database.connection import get_db
from app.models.user import User
from app.models.medical_profile import MedicalProfile, EmergencyContact
from app.models.incident import Incident
from app.models.community import CommunityReport
from app.utils.session import get_current_user
from app.services.incident_service import get_user_incidents, get_all_active_incidents
from app.services.user_service import calculate_readiness_score

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def require_auth(request: Request):
    session = get_current_user(request)
    if not session:
        return None
    return session


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    session = get_current_user(request)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "session": session,
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session:
        return RedirectResponse(url="/auth/login")

    user_id = session.get("user_id")
    incidents = get_user_incidents(db, user_id, limit=5)
    readiness = calculate_readiness_score(db, user_id)

    active = [i for i in incidents if i.status == "active"]
    resolved = [i for i in incidents if i.status == "resolved"]

    incidents_data = []
    for i in incidents:
        ai_data = {}
        try:
            if i.ai_analysis:
                ai_data = json.loads(i.ai_analysis)
        except Exception:
            pass
        incidents_data.append({
            "incident_id": i.incident_id,
            "type": i.incident_type,
            "status": i.status,
            "severity_level": i.severity_level,
            "severity_score": i.severity_score,
            "ai_summary": i.ai_summary,
            "created_at": i.created_at.strftime("%d %b %Y, %I:%M %p"),
            "recommended_actions": ai_data.get("recommended_actions", []),
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "session": session,
        "incidents": incidents_data,
        "active_count": len(active),
        "resolved_count": len(resolved),
        "readiness": readiness,
    })


@router.get("/sos", response_class=HTMLResponse)
async def sos_page(request: Request):
    session = get_current_user(request)
    return templates.TemplateResponse("sos.html", {
        "request": request,
        "session": session,
    })


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    community_reports = (
        db.query(CommunityReport)
        .filter(CommunityReport.is_resolved == False)
        .order_by(CommunityReport.reported_at.desc())
        .limit(50)
        .all()
    )
    reports_json = json.dumps([
        {
            "id": r.id,
            "type": r.report_type,
            "title": r.title,
            "lat": r.latitude,
            "lon": r.longitude,
            "severity": r.severity,
        }
        for r in community_reports
    ])
    return templates.TemplateResponse("map.html", {
        "request": request,
        "session": session,
        "community_reports_json": reports_json,
    })


@router.get("/ai-assistant", response_class=HTMLResponse)
async def ai_assistant(request: Request):
    session = get_current_user(request)
    return templates.TemplateResponse("ai_assistant.html", {
        "request": request,
        "session": session,
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session:
        return RedirectResponse(url="/auth/login")

    user_id = session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "session": session,
        "user": user,
        "profile": profile,
        "contacts": contacts,
    })


@router.get("/disaster", response_class=HTMLResponse)
async def disaster_page(request: Request):
    session = get_current_user(request)
    return templates.TemplateResponse("disaster.html", {
        "request": request,
        "session": session,
    })


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session:
        return RedirectResponse(url="/auth/login")

    user_id = session.get("user_id")
    incidents = get_user_incidents(db, user_id, limit=20)

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "session": session,
        "incidents": incidents,
    })


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session or not session.get("is_admin"):
        return RedirectResponse(url="/")

    from app.models.report import Report
    total_incidents = db.query(Incident).count()
    active_incidents = db.query(Incident).filter(Incident.status == "active").count()
    total_users = db.query(User).count()
    total_reports = db.query(Report).count()
    active_list = get_all_active_incidents(db)[:20]

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "session": session,
        "total_incidents": total_incidents,
        "active_incidents": active_incidents,
        "total_users": total_users,
        "total_reports": total_reports,
        "active_list": active_list,
    })


@router.get("/incident/{incident_id}", response_class=HTMLResponse)
async def incident_detail(incident_id: str, request: Request, db: Session = Depends(get_db)):
    from app.services.incident_service import get_incident_by_id
    session = get_current_user(request)
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    ai_data = {}
    resources = []
    try:
        if incident.ai_analysis:
            ai_data = json.loads(incident.ai_analysis)
        if incident.nearby_resources:
            resources = json.loads(incident.nearby_resources)
    except Exception:
        pass

    return templates.TemplateResponse("incident_detail.html", {
        "request": request,
        "session": session,
        "incident": incident,
        "ai_data": ai_data,
        "resources": resources[:10],
    })


@router.get("/track/{incident_id}", response_class=HTMLResponse)
async def track_incident_page(incident_id: str, request: Request, db: Session = Depends(get_db)):
    from app.services.incident_service import get_incident_by_id
    session = get_current_user(request) # might be anonymous, so session can be None
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == incident.user_id).all()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == incident.user_id).first()
    
    ai_data = {}
    resources = []
    try:
        if incident.ai_analysis:
            ai_data = json.loads(incident.ai_analysis)
        if incident.nearby_resources:
            resources = json.loads(incident.nearby_resources)
    except Exception:
        pass

    return templates.TemplateResponse("track.html", {
        "request": request,
        "session": session,
        "incident": incident,
        "profile": profile,
        "contacts": contacts,
        "ai_data": ai_data,
        "resources": resources[:5],
    })

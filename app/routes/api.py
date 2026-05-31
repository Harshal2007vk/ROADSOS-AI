from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.database.connection import get_db
from app.models.incident import Incident
from app.models.user import User
from app.models.medical_profile import MedicalProfile, EmergencyContact
from app.models.blackbox import BlackBoxRecord
from app.models.report import Report
from app.models.evidence import EvidenceFile
from app.models.community import CommunityReport
from app.schemas.schemas import SOSRequest, CommunityReportCreate, MedicalProfileUpdate, EmergencyContactCreate
from app.services.incident_service import (
    create_sos_incident, get_user_incidents, get_incident_by_id,
    resolve_incident, get_all_active_incidents, generate_incident_id
)
from app.services.user_service import (
    update_medical_profile, add_emergency_contact,
    delete_emergency_contact, calculate_readiness_score
)
from app.services.qr_generator import generate_medical_qr
from app.emergency.resource_finder import fetch_nearby_resources
from app.ai.gemini_assistant import analyze_emergency, get_disaster_guidance
from app.services.report_generator import generate_pdf_report, generate_txt_report, generate_json_report
from app.utils.session import get_current_user

router = APIRouter(prefix="/api", tags=["api"])

UPLOADS_DIR = "app/static/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


# ─── SOS ─────────────────────────────────────────────────────────────────────

@router.post("/sos/trigger")
async def trigger_sos(
    request: Request,
    sos_data: SOSRequest,
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1

    acceleration = None
    if sos_data.acceleration_x is not None:
        acceleration = {
            "x": sos_data.acceleration_x,
            "y": sos_data.acceleration_y,
            "z": sos_data.acceleration_z,
        }

    incident = create_sos_incident(
        db=db,
        user_id=user_id,
        latitude=sos_data.latitude,
        longitude=sos_data.longitude,
        description=sos_data.description,
        incident_type=sos_data.incident_type,
        speed_kmh=sos_data.speed_kmh,
        heading=sos_data.heading,
        network_status=sos_data.network_status,
        device_info=sos_data.device_info,
        weather_info=sos_data.weather_info,
        acceleration=acceleration,
    )

    resources = []
    try:
        if incident.nearby_resources:
            resources = json.loads(incident.nearby_resources)
    except Exception:
        pass

    ai_data = {}
    try:
        if incident.ai_analysis:
            ai_data = json.loads(incident.ai_analysis)
    except Exception:
        pass

    return {
        "success": True,
        "incident_id": incident.incident_id,
        "status": incident.status,
        "severity_level": incident.severity_level,
        "severity_score": incident.severity_score,
        "ai_summary": incident.ai_summary,
        "recommended_actions": ai_data.get("recommended_actions", []),
        "required_services": ai_data.get("required_services", []),
        "immediate_steps": ai_data.get("immediate_steps", []),
        "nearest_resources": resources[:5],
        "emergency_numbers": {
            "national": "112",
            "ambulance": "108",
            "police": "100",
            "fire": "101",
        },
    }


@router.get("/incidents")
async def list_incidents(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    incidents = get_user_incidents(db, user_id)
    return [
        {
            "id": i.id,
            "incident_id": i.incident_id,
            "type": i.incident_type,
            "status": i.status,
            "severity_level": i.severity_level,
            "severity_score": i.severity_score,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "ai_summary": i.ai_summary,
            "created_at": i.created_at.isoformat(),
        }
        for i in incidents
    ]


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident_id": incident.incident_id,
        "type": incident.incident_type,
        "status": incident.status,
        "severity_level": incident.severity_level,
        "severity_score": incident.severity_score,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "description": incident.description,
        "ai_summary": incident.ai_summary,
        "ai_analysis": json.loads(incident.ai_analysis) if incident.ai_analysis else {},
        "recommended_actions": json.loads(incident.recommended_actions) if incident.recommended_actions else [],
        "required_services": json.loads(incident.required_services) if incident.required_services else [],
        "nearby_resources": json.loads(incident.nearby_resources) if incident.nearby_resources else [],
        "created_at": incident.created_at.isoformat(),
    }


@router.get("/incidents/by-id/{incident_id}")
async def get_incident_by_slug(incident_id: str, db: Session = Depends(get_db)):
    """Lookup by human-readable incident_id string (e.g. INC-XXXX)."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident_id": incident.incident_id,
        "incident_type": incident.incident_type,
        "status": incident.status,
        "severity_level": incident.severity_level,
        "severity_score": incident.severity_score,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "description": incident.description,
        "ai_summary": incident.ai_summary,
        "recommended_actions": json.loads(incident.recommended_actions) if incident.recommended_actions else [],
        "nearby_resources": json.loads(incident.nearby_resources) if incident.nearby_resources else [],
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


@router.post("/incidents/{incident_id}/resolve")
async def resolve(incident_id: str, db: Session = Depends(get_db)):
    incident = resolve_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"success": True, "status": incident.status}


# ─── RESOURCES ───────────────────────────────────────────────────────────────

@router.get("/resources/nearby")
async def get_nearby_resources(
    lat: float,
    lon: float,
    radius: int = 5000,
    types: Optional[str] = None,
):
    resource_types = types.split(",") if types else None
    resources = fetch_nearby_resources(lat, lon, radius_m=radius, resource_types=resource_types)
    return resources


# ─── AI ──────────────────────────────────────────────────────────────────────

@router.post("/ai/analyze")
async def ai_analyze(request: Request):
    body = await request.json()
    description = body.get("description", "")
    incident_type = body.get("incident_type", "accident")
    lat = body.get("latitude")
    lon = body.get("longitude")
    speed = body.get("speed_kmh")

    if not description:
        raise HTTPException(status_code=400, detail="Description is required")

    result = analyze_emergency(
        description=description,
        incident_type=incident_type,
        latitude=lat,
        longitude=lon,
        speed_kmh=speed,
    )
    return result


@router.post("/ai/chat")
async def ai_chat(request: Request):
    """Chat endpoint used by the AI Assistant page."""
    body = await request.json()
    prompt = body.get("prompt", "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    from app.config.settings import settings
    try:
        import google.generativeai as genai
        if not settings.GEMINI_API_KEY:
            raise ValueError("No API key")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        system_context = (
            "You are ROADSoS AI, an emergency response assistant. "
            "Provide clear, calm, step-by-step guidance for emergency situations. "
            "Always remind users to call 112 for life-threatening emergencies. "
            "Keep responses concise and actionable. Use **bold** for key steps."
        )

        response = model.generate_content(
            f"{system_context}\n\nUser: {prompt}",
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            ),
        )
        return {"response": response.text.strip(), "source": "gemini"}

    except Exception as e:
        logger.warning(f"AI chat fallback: {e}")
        # Offline keyword-based fallback
        p = prompt.lower()
        if any(w in p for w in ["cpr", "cardiac", "heart attack"]):
            reply = (
                "**⚠️ CALL 112 IMMEDIATELY**\n\n"
                "**CPR Steps:**\n"
                "1. Check responsiveness — tap shoulders, shout\n"
                "2. Call 112 or ask someone to call\n"
                "3. Tilt head back, lift chin, check breathing\n"
                "4. Place heel of hand on center of chest\n"
                "5. Push hard & fast — 100–120 compressions/min, 2 inches deep\n"
                "6. Give 2 rescue breaths every 30 compressions\n"
                "7. Continue until help arrives"
            )
        elif any(w in p for w in ["bleed", "bleeding", "blood", "wound"]):
            reply = (
                "**Bleeding Control:**\n"
                "1. Apply firm direct pressure with clean cloth\n"
                "2. Maintain pressure for at least 10 minutes — do not peek\n"
                "3. Add more cloth on top if soaked, do not remove\n"
                "4. Elevate the injured limb above heart level if possible\n"
                "5. If limb bleeding, consider tourniquet 2–3 inches above wound\n\n"
                "**Call 112 if bleeding is severe or does not stop.**"
            )
        elif any(w in p for w in ["chok", "choking", "heimlich"]):
            reply = (
                "**Heimlich Maneuver:**\n"
                "1. Ask 'Are you choking?' — if they can speak/cough, encourage coughing\n"
                "2. Stand behind the person, wrap arms around waist\n"
                "3. Make a fist, place above navel below ribs\n"
                "4. Cover fist with other hand\n"
                "5. Give sharp upward-inward thrusts until object dislodges\n"
                "6. For infants: 5 back blows + 5 chest thrusts\n\n"
                "**Call 112 if person loses consciousness.**"
            )
        elif any(w in p for w in ["burn", "fire", "scald"]):
            reply = (
                "**Burn Treatment:**\n"
                "1. Remove from heat source — ensure your safety first\n"
                "2. Cool with cool (not cold/ice) running water for 10–20 min\n"
                "3. Remove clothing/jewelry near burn unless stuck\n"
                "4. Cover loosely with clean non-fluffy material\n"
                "5. Do NOT apply butter, toothpaste, or ice\n\n"
                "**Call 112 for large, deep, or facial burns.**"
            )
        elif any(w in p for w in ["accident", "crash", "collision"]):
            reply = (
                "**At a Road Accident:**\n"
                "1. Ensure your safety — turn on hazard lights\n"
                "2. **Call 112** immediately\n"
                "3. Do not move injured persons unless in immediate danger\n"
                "4. Check for breathing — start CPR if needed\n"
                "5. Apply pressure to bleeding wounds\n"
                "6. Keep victims warm and calm\n"
                "7. Warn oncoming traffic with warning triangle if safe"
            )
        elif any(w in p for w in ["flood", "earthquake", "cyclone", "disaster"]):
            reply = (
                "**General Disaster Response:**\n"
                "1. Move to safety immediately\n"
                "2. Call 112 or Disaster Helpline: 1077\n"
                "3. Follow local authority instructions\n"
                "4. Stay away from flood water, unstable buildings\n"
                "5. Keep emergency kit ready: water, food, medicines, torch\n\n"
                "Check the **Disaster Alerts** page for specific guidance."
            )
        else:
            reply = (
                "I'm currently in offline mode. For immediate emergencies:\n\n"
                "🚨 **National Emergency: 112**\n"
                "🚑 **Ambulance: 108**\n"
                "🚔 **Police: 100**\n"
                "🔥 **Fire: 101**\n"
                "🌊 **Disaster: 1077**\n\n"
                "Please describe your emergency and I'll guide you as best I can."
            )
        return {"response": reply, "source": "offline"}


@router.get("/ai/disaster/{disaster_type}")
async def get_disaster_info(disaster_type: str):
    guidance = get_disaster_guidance(disaster_type)
    return guidance


# ─── MEDICAL PROFILE ─────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1

    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    profile_data = {}
    if profile:
        profile_data = {
            "full_name": profile.full_name,
            "age": profile.age,
            "blood_group": profile.blood_group,
            "allergies": profile.allergies,
            "medical_conditions": profile.medical_conditions,
            "medications": profile.medications,
            "organ_donor": profile.organ_donor,
            "insurance_provider": profile.insurance_provider,
            "insurance_id": profile.insurance_id,
            "doctor_name": profile.doctor_name,
            "doctor_phone": profile.doctor_phone,
            "notes": profile.notes,
        }

    return {
        "profile": profile_data,
        "emergency_contacts": [
            {"id": c.id, "name": c.name, "phone": c.phone,
             "relationship": c.relation, "is_primary": c.is_primary}
            for c in contacts
        ],
    }


@router.put("/profile")
async def update_profile(
    request: Request,
    profile_data: MedicalProfileUpdate,
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    profile = update_medical_profile(db, user_id, profile_data)
    return {"success": True, "message": "Profile updated successfully"}


# ─── FRONTEND-ALIGNED ALIAS ROUTES ───────────────────────────────────────────
# profile.html calls PUT /api/users/me/medical with {blood_type, allergies,
# medical_conditions, medications, emergency_contacts[]}.
# These aliases translate and delegate to the existing service layer.

@router.put("/users/me/medical")
async def update_my_medical(
    request: Request,
    db: Session = Depends(get_db),
):
    """Alias used by profile.html saveProfile().
    Accepts { blood_type, allergies, medical_conditions, medications,
              emergency_contacts: [{name, phone, relation}] }
    and maps them to the canonical backend schema.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1

    # ── Map field name differences ──────────────────────────────────────────
    mapped = {
        "blood_group":        body.get("blood_type") or body.get("blood_group"),
        "allergies":          body.get("allergies"),
        "medical_conditions": body.get("medical_conditions"),
        "medications":        body.get("medications"),
    }
    # Strip None so model_dump(exclude_none) works correctly
    mapped = {k: v for k, v in mapped.items() if v is not None}

    profile_update = MedicalProfileUpdate(**mapped)
    update_medical_profile(db, user_id, profile_update)

    # ── Sync emergency contacts list ────────────────────────────────────────
    raw_contacts = body.get("emergency_contacts", [])
    if isinstance(raw_contacts, list):
        # Delete all existing contacts for this user, then re-insert
        db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).delete()
        db.commit()
        for idx, c in enumerate(raw_contacts):
            name = (c.get("name") or "").strip()
            phone = (c.get("phone") or "").strip()
            relation = (c.get("relation") or c.get("relationship") or "Family").strip()
            if name and phone:
                contact = EmergencyContact(
                    user_id=user_id,
                    name=name,
                    phone=phone,
                    relation=relation,
                    is_primary=(idx == 0),
                )
                db.add(contact)
        db.commit()

    return {"success": True, "message": "Medical profile updated successfully"}


@router.post("/profile/contacts")
async def add_contact(
    request: Request,
    contact: EmergencyContactCreate,
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    new_contact = add_emergency_contact(db, user_id, contact)
    return {
        "success": True,
        "contact": {
            "id": new_contact.id,
            "name": new_contact.name,
            "phone": new_contact.phone,
            "relationship": new_contact.relation,
            "is_primary": new_contact.is_primary,
        }
    }


@router.delete("/profile/contacts/{contact_id}")
async def remove_contact(
    contact_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    deleted = delete_emergency_contact(db, contact_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"success": True}


# ─── QR CODE ─────────────────────────────────────────────────────────────────

@router.get("/qr/generate")
async def generate_qr(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1

    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    if not profile:
        raise HTTPException(status_code=404, detail="Medical profile not found. Please set up your profile first.")

    b64, file_path = generate_medical_qr(user, profile, contacts)
    return {"success": True, "qr_base64": b64, "file_path": file_path}


@router.post("/users/me/medical/qr")
@router.get("/users/me/medical/qr")
async def generate_my_medical_qr(request: Request, db: Session = Depends(get_db)):
    """Alias used by profile.html generateQR() — POST /api/users/me/medical/qr.
    Generates QR from the user's saved medical profile and returns base64 PNG.
    """
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1

    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    if not profile:
        # Auto-create a blank profile so the QR can still be generated
        profile = MedicalProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    try:
        b64, file_path = generate_medical_qr(user, profile, contacts)
        return {"success": True, "qr_base64": b64, "file_path": file_path}
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"QR generation failed: {str(e)}")


# ─── REPORTS ─────────────────────────────────────────────────────────────────

@router.get("/reports/generate/{incident_id}/pdf")
async def download_pdf_direct(
    incident_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Direct GET endpoint so anchor tags can trigger PDF downloads."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()

    try:
        file_path = generate_pdf_report(incident, user, profile)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"incident_{incident.incident_id}.pdf",
    )


@router.post("/reports/generate/{incident_id}/{format}")
async def generate_report(
    incident_id: str,
    format: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if format not in ("pdf", "txt", "json"):
        raise HTTPException(status_code=400, detail="Format must be pdf, txt, or json")

    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()

    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

    if format == "pdf":
        file_path = generate_pdf_report(incident, user, profile)
    elif format == "txt":
        file_path = generate_txt_report(incident, user, profile)
    else:
        file_path = generate_json_report(incident, user, profile)

    file_size = os.path.getsize(file_path)

    db_report = Report(
        report_id=report_id,
        incident_id=incident.id,
        user_id=user_id,
        report_type="incident",
        format=format,
        file_path=file_path,
        file_size_bytes=file_size,
    )
    db.add(db_report)
    db.commit()

    return {
        "success": True,
        "report_id": report_id,
        "download_url": f"/api/reports/download/{report_id}",
        "format": format,
        "file_size": file_size,
    }


@router.get("/reports/download/{report_id}")
async def download_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    report.download_count += 1
    db.commit()

    media_types = {"pdf": "application/pdf", "txt": "text/plain", "json": "application/json"}
    return FileResponse(
        report.file_path,
        media_type=media_types.get(report.format, "application/octet-stream"),
        filename=os.path.basename(report.file_path),
    )


# ─── EVIDENCE ────────────────────────────────────────────────────────────────

@router.post("/evidence/upload/{incident_id}")
async def upload_evidence(
    incident_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    allowed_types = {
        "image/jpeg", "image/png", "image/webp", "image/gif",
        "video/mp4", "video/quicktime", "video/webm",
        "audio/mpeg", "audio/wav", "audio/webm", "audio/ogg"
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")

    ext = os.path.splitext(file.filename)[1] or ".bin"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    incident_dir = os.path.join(UPLOADS_DIR, incident.incident_id)
    os.makedirs(incident_dir, exist_ok=True)
    file_path = os.path.join(incident_dir, safe_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    evidence = EvidenceFile(
        incident_id=incident.id,
        file_name=file.filename,
        file_type=file.content_type.split("/")[0],
        file_path=file_path,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        description=description,
    )
    db.add(evidence)
    db.commit()

    return {
        "success": True,
        "file_id": evidence.id,
        "file_name": evidence.file_name,
        "file_type": evidence.file_type,
        "file_size": file_size,
    }


# ─── COMMUNITY REPORTS ───────────────────────────────────────────────────────

@router.post("/community/report")
async def submit_community_report(
    report: CommunityReportCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    user_id = session.get("user_id") if session else None

    cr = CommunityReport(
        user_id=user_id,
        report_type=report.report_type,
        title=report.title,
        description=report.description,
        latitude=report.latitude,
        longitude=report.longitude,
        address=report.address,
        severity=report.severity,
    )
    db.add(cr)
    db.commit()
    return {"success": True, "id": cr.id}


@router.get("/community/reports")
async def get_community_reports(db: Session = Depends(get_db)):
    reports = (
        db.query(CommunityReport)
        .filter(CommunityReport.is_resolved == False)
        .order_by(CommunityReport.reported_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "type": r.report_type,
            "title": r.title,
            "description": r.description,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "severity": r.severity,
            "upvotes": r.upvotes,
            "reported_at": r.reported_at.isoformat(),
        }
        for r in reports
    ]


@router.post("/community/reports/{report_id}/upvote")
async def upvote_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(CommunityReport).filter(CommunityReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.upvotes += 1
    db.commit()
    return {"success": True, "upvotes": report.upvotes}


# ─── READINESS SCORE ─────────────────────────────────────────────────────────

@router.get("/readiness")
async def get_readiness(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    return calculate_readiness_score(db, user_id)


@router.post("/user/offline-pack")
async def download_offline_pack_trigger(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    user_id = session.get("user_id", 1) if session else 1
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.offline_pack_ready = True
    db.commit()
    return {"success": True, "message": "Offline pack flag updated in database"}


# ─── ADMIN ───────────────────────────────────────────────────────────────────

@router.get("/admin/stats")
async def admin_stats(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session or not session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    total_incidents = db.query(Incident).count()
    active_incidents = db.query(Incident).filter(Incident.status == "active").count()
    total_users = db.query(User).count()
    total_reports = db.query(Report).count()
    community_reports = db.query(CommunityReport).count()

    recent = get_all_active_incidents(db)[:10]

    return {
        "stats": {
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "total_users": total_users,
            "total_reports": total_reports,
            "community_reports": community_reports,
        },
        "active_incidents": [
            {
                "incident_id": i.incident_id,
                "type": i.incident_type,
                "severity_level": i.severity_level,
                "latitude": i.latitude,
                "longitude": i.longitude,
                "created_at": i.created_at.isoformat(),
            }
            for i in recent
        ],
    }


@router.get("/admin/heatmap")
async def get_heatmap_data(request: Request, db: Session = Depends(get_db)):
    session = get_current_user(request)
    if not session or not session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    incidents = db.query(Incident).all()
    heatmap_points = []
    for i in incidents:
        if i.latitude is not None and i.longitude is not None:
            intensity = (i.severity_score or 50) / 100.0
            heatmap_points.append([i.latitude, i.longitude, intensity])
            
    return heatmap_points

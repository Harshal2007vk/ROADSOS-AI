import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.blackbox import BlackBoxRecord
from app.models.user import User
from app.models.medical_profile import MedicalProfile, EmergencyContact
from app.ai.gemini_assistant import analyze_emergency, generate_incident_summary
from app.emergency.resource_finder import fetch_nearby_resources

logger = logging.getLogger(__name__)


def generate_incident_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short = str(uuid.uuid4())[:6].upper()
    return f"RDS-{ts}-{short}"


def create_sos_incident(
    db: Session,
    user_id: int,
    latitude: float,
    longitude: float,
    description: Optional[str] = None,
    incident_type: str = "accident",
    speed_kmh: Optional[float] = None,
    heading: Optional[float] = None,
    network_status: str = "online",
    device_info: Optional[str] = None,
    weather_info: Optional[str] = None,
    acceleration: Optional[Dict] = None,
) -> Incident:
    """Full SOS workflow: find resources, run AI analysis, create records."""

    incident_id = generate_incident_id()

    # Fetch nearby resources
    resources = []
    try:
        resources = fetch_nearby_resources(latitude, longitude, radius_m=8000)
        resources_summary = resources[:10]  # Top 10 nearest
    except Exception as e:
        logger.error(f"Resource fetch failed: {e}")
        resources_summary = []

    # AI analysis
    ai_result = {}
    try:
        ai_result = analyze_emergency(
            description=description or f"{incident_type} at lat {latitude:.4f}, lon {longitude:.4f}",
            incident_type=incident_type,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            acceleration=acceleration,
        )
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        ai_result = {"severity_score": 60, "severity_level": "high", "risk_level": "HIGH"}

    # Generate AI summary
    nearest = resources[0] if resources else None
    timestamp_str = datetime.utcnow().strftime("%I:%M %p UTC, %d %b %Y")
    location_str = f"Lat {latitude:.4f}, Lon {longitude:.4f}"

    ai_summary = generate_incident_summary(
        incident_type=incident_type,
        location=location_str,
        timestamp=timestamp_str,
        severity_level=ai_result.get("severity_level", "high"),
        nearest_resource=nearest["name"] if nearest else None,
        nearest_distance_km=nearest["distance_km"] if nearest else None,
        description=description,
    )

    # Create incident record
    incident = Incident(
        incident_id=incident_id,
        user_id=user_id,
        incident_type=incident_type,
        status="active",
        latitude=latitude,
        longitude=longitude,
        description=description,
        severity_score=ai_result.get("severity_score", 60),
        severity_level=ai_result.get("severity_level", "high"),
        ai_analysis=json.dumps(ai_result),
        ai_summary=ai_summary,
        recommended_actions=json.dumps(ai_result.get("recommended_actions", [])),
        required_services=json.dumps(ai_result.get("required_services", [])),
        speed_at_incident=speed_kmh,
        heading=heading,
        network_status=network_status,
        device_info=device_info,
        weather_info=weather_info,
        nearby_resources=json.dumps(resources_summary),
    )
    db.add(incident)
    db.flush()  # Get incident.id

    # Create blackbox record
    user = db.query(User).filter(User.id == user_id).first()
    medical = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    medical_snapshot = {}
    if medical:
        medical_snapshot = {
            "blood_group": medical.blood_group,
            "allergies": medical.allergies,
            "medical_conditions": medical.medical_conditions,
            "medications": medical.medications,
            "organ_donor": medical.organ_donor,
        }

    contacts_snapshot = [
        {"name": c.name, "phone": c.phone, "relationship": c.relation}
        for c in contacts
    ]

    blackbox = BlackBoxRecord(
        incident_id=incident.id,
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        heading_degrees=heading,
        acceleration_x=acceleration.get("x") if acceleration else None,
        acceleration_y=acceleration.get("y") if acceleration else None,
        acceleration_z=acceleration.get("z") if acceleration else None,
        network_type=network_status,
        nearby_resources_json=json.dumps(resources_summary),
        medical_snapshot_json=json.dumps(medical_snapshot),
        contacts_snapshot_json=json.dumps(contacts_snapshot),
        ai_analysis_json=json.dumps(ai_result),
        device_model=device_info,
    )
    db.add(blackbox)
    db.commit()
    db.refresh(incident)

    return incident


def get_user_incidents(db: Session, user_id: int, limit: int = 20) -> List[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.user_id == user_id)
        .order_by(Incident.created_at.desc())
        .limit(limit)
        .all()
    )


def get_incident_by_id(db: Session, incident_id: str) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.incident_id == incident_id).first()


def resolve_incident(db: Session, incident_id: str) -> Optional[Incident]:
    incident = get_incident_by_id(db, incident_id)
    if incident:
        incident.status = "resolved"
        incident.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(incident)
    return incident


def get_all_active_incidents(db: Session) -> List[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.status == "active")
        .order_by(Incident.created_at.desc())
        .all()
    )

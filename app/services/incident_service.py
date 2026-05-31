import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.models.incident import Incident
from app.models.blackbox import BlackBoxRecord


def generate_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:10].upper()}"


def create_sos_incident(
    db: Session,
    user_id: Optional[int],
    latitude: float,
    longitude: float,
    description: Optional[str] = None,
    incident_type: str = "accident",
    speed_kmh: Optional[float] = None,
    heading: Optional[float] = None,
    network_status: Optional[str] = None,
    device_info: Optional[str] = None,
    weather_info: Optional[str] = None,
    acceleration: Optional[Dict[str, Any]] = None,
) -> Incident:
    import json
    from app.emergency.resource_finder import fetch_nearby_resources
    from app.ai.gemini_assistant import analyze_emergency, generate_incident_summary

    incident_id = generate_incident_id()

    # AI analysis
    ai_result = analyze_emergency(
        description=description or f"{incident_type} incident reported",
        incident_type=incident_type,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        acceleration=acceleration,
    )

    # Nearby resources
    resources = []
    try:
        resources = fetch_nearby_resources(latitude, longitude)
    except Exception:
        pass

    # AI summary
    nearest = resources[0] if resources else None
    ai_summary = generate_incident_summary(
        incident_type=incident_type,
        location=f"{latitude:.4f}, {longitude:.4f}",
        timestamp=datetime.utcnow().strftime("%d %b %Y %H:%M UTC"),
        severity_level=ai_result.get("severity_level", "moderate"),
        nearest_resource=nearest.get("name") if nearest else None,
        nearest_distance_km=nearest.get("distance_km") if nearest else None,
        description=description,
    )

    new_incident = Incident(
        incident_id=incident_id,
        user_id=user_id,
        incident_type=incident_type,
        status="active",
        latitude=latitude,
        longitude=longitude,
        description=description,
        severity_score=ai_result.get("severity_score", 50),
        severity_level=ai_result.get("severity_level", "moderate"),
        ai_analysis=json.dumps(ai_result),
        ai_summary=ai_summary,
        recommended_actions=json.dumps(ai_result.get("recommended_actions", [])),
        required_services=json.dumps(ai_result.get("required_services", [])),
        speed_at_incident=speed_kmh,
        heading=heading,
        network_status=network_status,
        device_info=device_info,
        weather_info=weather_info,
        nearby_resources=json.dumps(resources),
        created_at=datetime.utcnow(),
    )

    # Also log to blackbox
    blackbox_record = BlackBoxRecord(
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        heading_degrees=heading,
        ai_analysis_json=json.dumps(ai_result),
        recorded_at=datetime.utcnow(),
    )

    db.add(new_incident)
    db.flush()
    blackbox_record.incident_id = new_incident.id  # FK to integer PK
    db.add(blackbox_record)
    db.commit()
    db.refresh(new_incident)
    return new_incident


def get_user_incidents(db: Session, user_id: int, limit: Optional[int] = None) -> List[Incident]:
    query = db.query(Incident).filter(Incident.user_id == user_id).order_by(Incident.created_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_incident_by_id(db: Session, incident_id: str) -> Optional[Incident]:
    """Lookup by the human-readable incident_id string (e.g. INC-XXXX)."""
    return db.query(Incident).filter(Incident.incident_id == incident_id).first()


def resolve_incident(db: Session, incident_id: str, resolution_notes: str = "") -> Optional[Incident]:
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
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


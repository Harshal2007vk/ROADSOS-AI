from sqlalchemy.orm import Session
from app.models import MedicalProfile, EmergencyContact, Incident, BlackBoxRecord, DisasterAlert
from app.schemas import schemas

def get_medical_profile(db: Session, user_id: int):
    return db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()

def create_or_update_medical_profile(db: Session, user_id: int, profile: schemas.MedicalProfileCreate):
    db_profile = get_medical_profile(db, user_id)
    if db_profile:
        for key, value in profile.model_dump().items():
            setattr(db_profile, key, value)
    else:
        db_profile = MedicalProfile(**profile.model_dump(), user_id=user_id)
        db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def get_contacts(db: Session, user_id: int):
    return db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

def create_contact(db: Session, user_id: int, contact: schemas.EmergencyContactCreate):
    db_contact = EmergencyContact(**contact.model_dump(), user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def create_incident(db: Session, incident: schemas.IncidentCreate, user_id: int = None):
    db_incident = Incident(**incident.model_dump(), user_id=user_id)
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident

def update_incident_ai_summary(db: Session, incident_id: int, summary: str, severity: str):
    db_incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if db_incident:
        db_incident.ai_summary = summary
        db_incident.ai_severity_score = severity
        db.commit()
        db.refresh(db_incident)
    return db_incident

def add_blackbox_record(db: Session, incident_id: int, record: schemas.BlackBoxRecordCreate):
    db_record = BlackBoxRecord(**record.model_dump(), incident_id=incident_id)
    db.add(db_record)
    db.commit()
    return db_record

def get_active_disaster_alerts(db: Session):
    return db.query(DisasterAlert).filter(DisasterAlert.active == True).all()

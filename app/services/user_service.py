import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.models.medical_profile import MedicalProfile, EmergencyContact
from app.schemas.schemas import UserCreate, MedicalProfileUpdate, EmergencyContactCreate

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_user(db: Session, user_data: UserCreate) -> User:
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise ValueError("Email already registered")

    user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = MedicalProfile(user_id=user.id, full_name=user_data.name)
    db.add(profile)
    db.commit()

    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def update_medical_profile(
    db: Session, user_id: int, profile_data: MedicalProfileUpdate
) -> MedicalProfile:
    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    if not profile:
        profile = MedicalProfile(user_id=user_id)
        db.add(profile)

    for field, value in profile_data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


def add_emergency_contact(
    db: Session, user_id: int, contact_data: EmergencyContactCreate
) -> EmergencyContact:
    if contact_data.is_primary:
        db.query(EmergencyContact).filter(
            EmergencyContact.user_id == user_id,
            EmergencyContact.is_primary == True
        ).update({"is_primary": False})

    contact = EmergencyContact(
        user_id=user_id,
        name=contact_data.name,
        relation=contact_data.relationship,
        phone=contact_data.phone,
        email=contact_data.email,
        is_primary=contact_data.is_primary,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def delete_emergency_contact(db: Session, contact_id: int, user_id: int) -> bool:
    contact = db.query(EmergencyContact).filter(
        EmergencyContact.id == contact_id,
        EmergencyContact.user_id == user_id
    ).first()
    if contact:
        db.delete(contact)
        db.commit()
        return True
    return False


def calculate_readiness_score(db: Session, user_id: int) -> Dict:
    """Calculate emergency readiness score 0-100."""
    score = 0
    recommendations = []

    profile = db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()
    user = db.query(User).filter(User.id == user_id).first()

    # 1. Medical profile existence (25 pts)
    if profile:
        score += 25
        # 2. Blood group (15 pts)
        if profile.blood_group:
            score += 15
        else:
            recommendations.append("Specify blood group in medical profile (+15 pts)")
        
        # 4. QR generated (15 pts)
        if profile.qr_code_path:
            score += 15
        else:
            recommendations.append("Generate your Medical Profile QR code (+15 pts)")
    else:
        recommendations.append("Set up your Medical Profile (+25 pts)")
        recommendations.append("Specify blood group (+15 pts)")
        recommendations.append("Generate your Medical Profile QR code (+15 pts)")

    # 3. Emergency contacts (25 pts)
    if len(contacts) > 0:
        score += 25
    else:
        recommendations.append("Add at least one Emergency Contact (+25 pts)")

    # 5. Offline pack downloaded (20 pts)
    if user and getattr(user, "offline_pack_ready", False):
        score += 20
    else:
        recommendations.append("Download the Offline Emergency Pack (+20 pts)")

    score = min(100, score)
    level = "Excellent" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "Needs Improvement"

    return {
        "score": score,
        "level": level,
        "recommendations": recommendations,
        "contact_count": len(contacts),
        "profile_complete": profile is not None,
        "has_medical": profile is not None,
        "has_contacts": len(contacts) > 0,
        "offline_pack_ready": user.offline_pack_ready if user else False
    }

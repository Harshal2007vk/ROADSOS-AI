from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class MedicalProfile(Base):
    __tablename__ = "medical_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String(150))
    age = Column(Integer)
    blood_group = Column(String(10))
    allergies = Column(Text, default="")
    medical_conditions = Column(Text, default="")
    medications = Column(Text, default="")
    organ_donor = Column(Boolean, default=False)
    insurance_provider = Column(String(100))
    insurance_id = Column(String(100))
    doctor_name = Column(String(150))
    doctor_phone = Column(String(20))
    notes = Column(Text, default="")
    qr_code_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="medical_profile")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(150), nullable=False)
    relation = Column(String(50))
    phone = Column(String(20), nullable=False)
    email = Column(String(150))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="emergency_contacts")

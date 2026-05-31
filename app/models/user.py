from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    language = Column(String(10), default="en")
    offline_pack_ready = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medical_profile = relationship("MedicalProfile", back_populates="user", uselist=False)
    emergency_contacts = relationship("EmergencyContact", back_populates="user")
    incidents = relationship("Incident", back_populates="user")
    blackbox_records = relationship("BlackBoxRecord", back_populates="user")
    reports = relationship("Report", back_populates="user")
    community_reports = relationship("CommunityReport", back_populates="user")

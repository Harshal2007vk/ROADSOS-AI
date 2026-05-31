from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database.connection import Base


class IncidentType(str, enum.Enum):
    accident = "accident"
    medical = "medical"
    flood = "flood"
    fire = "fire"
    earthquake = "earthquake"
    cyclone = "cyclone"
    other = "other"


class SeverityLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"
    cancelled = "cancelled"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    incident_type = Column(String(50), default="accident")
    status = Column(String(20), default="active")
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(Text)
    description = Column(Text)
    severity_score = Column(Integer, default=0)
    severity_level = Column(String(20), default="moderate")
    ai_analysis = Column(Text)
    ai_summary = Column(Text)
    recommended_actions = Column(Text)
    required_services = Column(Text)
    speed_at_incident = Column(Float)
    heading = Column(Float)
    network_status = Column(String(20))
    device_info = Column(Text)
    weather_info = Column(Text)
    nearby_resources = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)

    user = relationship("User", back_populates="incidents")
    evidence_files = relationship("EvidenceFile", back_populates="incident")
    blackbox_record = relationship("BlackBoxRecord", back_populates="incident", uselist=False)
    reports = relationship("Report", back_populates="incident")

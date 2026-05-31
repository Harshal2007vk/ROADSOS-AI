from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from app.database.connection import Base


class DisasterAlert(Base):
    __tablename__ = "disaster_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, index=True)
    disaster_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(String(20), default="moderate")
    latitude = Column(Float)
    longitude = Column(Float)
    radius_km = Column(Float, default=10.0)
    affected_area = Column(Text)
    safety_guidelines = Column(Text)
    evacuation_routes = Column(Text)
    relief_contacts = Column(Text)
    is_active = Column(Boolean, default=True)
    source = Column(String(100))
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

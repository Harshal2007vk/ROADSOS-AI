from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class BlackBoxRecord(Base):
    __tablename__ = "blackbox_records"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    speed_kmh = Column(Float)
    heading_degrees = Column(Float)
    altitude_m = Column(Float)
    acceleration_x = Column(Float)
    acceleration_y = Column(Float)
    acceleration_z = Column(Float)
    orientation_alpha = Column(Float)
    orientation_beta = Column(Float)
    orientation_gamma = Column(Float)
    network_type = Column(String(20))
    network_strength = Column(String(20))
    battery_level = Column(Integer)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    weather_condition = Column(String(100))
    nearby_resources_json = Column(Text)
    medical_snapshot_json = Column(Text)
    contacts_snapshot_json = Column(Text)
    ai_analysis_json = Column(Text)
    device_model = Column(String(100))
    os_info = Column(String(100))
    app_version = Column(String(20))
    is_synced = Column(Boolean, default=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="blackbox_record")
    user = relationship("User", back_populates="blackbox_records")

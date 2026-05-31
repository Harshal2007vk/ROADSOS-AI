from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(50), unique=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String(20), default="incident")
    format = Column(String(10), default="pdf")
    file_path = Column(String(255))
    file_size_bytes = Column(Integer)
    generated_at = Column(DateTime, default=datetime.utcnow)
    download_count = Column(Integer, default=0)

    incident = relationship("Incident", back_populates="reports")
    user = relationship("User", back_populates="reports")

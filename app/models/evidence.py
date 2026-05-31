from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    file_name = Column(String(255))
    file_type = Column(String(50))
    file_path = Column(String(500))
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))
    description = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="evidence_files")

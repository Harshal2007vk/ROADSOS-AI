from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class CommunityReport(Base):
    __tablename__ = "community_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    report_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text)
    severity = Column(String(20), default="moderate")
    is_verified = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    is_resolved = Column(Boolean, default=False)
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

    user = relationship("User", back_populates="community_reports")

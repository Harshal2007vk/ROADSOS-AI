from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class SOSRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: Optional[str] = None
    incident_type: str = "accident"
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    network_status: Optional[str] = "online"
    device_info: Optional[str] = None
    weather_info: Optional[str] = None
    nearby_resources: Optional[str] = None
    acceleration_x: Optional[float] = None
    acceleration_y: Optional[float] = None
    acceleration_z: Optional[float] = None


class IncidentResponse(BaseModel):
    id: int
    incident_id: str
    incident_type: str
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    description: Optional[str]
    severity_score: Optional[int]
    severity_level: Optional[str]
    ai_summary: Optional[str]
    recommended_actions: Optional[str]
    required_services: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CommunityReportCreate(BaseModel):
    report_type: str
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    severity: str = "moderate"


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    is_admin: bool
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class MedicalProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    organ_donor: Optional[bool] = None
    insurance_provider: Optional[str] = None
    insurance_id: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_phone: Optional[str] = None
    notes: Optional[str] = None


class EmergencyContactCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    relationship: Optional[str] = None
    phone: str = Field(..., min_length=7)
    email: Optional[str] = None
    is_primary: bool = False

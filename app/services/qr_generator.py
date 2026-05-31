import qrcode
import json
import os
from io import BytesIO
import base64
from typing import Optional
from app.models.medical_profile import MedicalProfile
from app.models.user import User


def generate_medical_qr(
    user: User,
    profile: MedicalProfile,
    contacts: list,
    output_dir: str = "app/static/qr",
) -> str:
    """Generate QR code with medical profile data. Returns base64 PNG string."""
    os.makedirs(output_dir, exist_ok=True)

    qr_data = {
        "name": profile.full_name or user.name,
        "age": profile.age,
        "blood_group": profile.blood_group or "Unknown",
        "allergies": profile.allergies or "None",
        "conditions": profile.medical_conditions or "None",
        "medications": profile.medications or "None",
        "organ_donor": profile.organ_donor,
        "emergency_contacts": [
            {"name": c.name, "phone": c.phone, "rel": c.relationship}
            for c in contacts[:3]
        ],
        "app": "ROADSoS AI",
        "version": "1.0",
    }

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(qr_data, ensure_ascii=False))
    qr.make(fit=True)

    img = qr.make_image(fill_color="#dc2626", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = f"qr_{user.id}.png"
    file_path = os.path.join(output_dir, filename)
    img.save(file_path)

    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, file_path

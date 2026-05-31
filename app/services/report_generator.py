import json
import os
import uuid
from datetime import datetime
from typing import Optional
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models.incident import Incident
from app.models.user import User
from app.models.medical_profile import MedicalProfile

REPORTS_DIR = "app/static/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_pdf_report(
    incident: Incident,
    user: User,
    profile: Optional[MedicalProfile] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate a professional PDF incident report. Returns file path."""

    if not output_path:
        filename = f"report_{incident.incident_id}_{uuid.uuid4().hex[:6]}.pdf"
        output_path = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    RED = colors.HexColor("#dc2626")
    DARK = colors.HexColor("#111827")
    GRAY = colors.HexColor("#6b7280")
    LIGHT = colors.HexColor("#f9fafb")

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        textColor=RED, fontSize=22, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        textColor=GRAY, fontSize=10, spaceAfter=12,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        textColor=RED, fontSize=13, spaceBefore=14, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, textColor=DARK,
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=8, textColor=GRAY,
    )

    story = []

    # Header
    story.append(Paragraph("🚨 ROADSoS AI", title_style))
    story.append(Paragraph("Emergency Incident Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=RED))
    story.append(Spacer(1, 12))

    # Incident Meta Table
    meta_data = [
        ["Incident ID", incident.incident_id],
        ["Date & Time", incident.created_at.strftime("%d %B %Y, %I:%M:%S %p UTC")],
        ["Status", incident.status.upper()],
        ["Type", (incident.incident_type or "Accident").title()],
        ["Severity Level", (incident.severity_level or "Unknown").upper()],
        ["Severity Score", f"{incident.severity_score or 0}/100"],
    ]

    meta_table = Table(meta_data, colWidths=[5 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Location
    story.append(Paragraph("📍 Location Information", section_style))
    loc_data = [
        ["Latitude", str(incident.latitude or "N/A")],
        ["Longitude", str(incident.longitude or "N/A")],
        ["Address", incident.address or "Coordinates only"],
        ["Speed at Incident", f"{incident.speed_at_incident:.1f} km/h" if incident.speed_at_incident else "N/A"],
        ["Network Status", (incident.network_status or "Unknown").title()],
    ]
    _render_table(story, loc_data, LIGHT, DARK)

    # Description
    if incident.description:
        story.append(Paragraph("📝 Incident Description", section_style))
        story.append(Paragraph(incident.description, body_style))
        story.append(Spacer(1, 8))

    # AI Analysis
    story.append(Paragraph("🤖 AI Analysis Summary", section_style))
    if incident.ai_summary:
        story.append(Paragraph(incident.ai_summary, body_style))
        story.append(Spacer(1, 8))

    if incident.ai_analysis:
        try:
            ai_data = json.loads(incident.ai_analysis)
            story.append(Paragraph("Recommended Actions:", ParagraphStyle(
                "Bold", parent=body_style, fontName="Helvetica-Bold")))
            for action in ai_data.get("recommended_actions", [])[:6]:
                story.append(Paragraph(f"• {action}", body_style))
        except Exception:
            pass

    # Required Services
    if incident.required_services:
        try:
            services = json.loads(incident.required_services)
            if services:
                story.append(Spacer(1, 8))
                story.append(Paragraph("Required Emergency Services:", ParagraphStyle(
                    "Bold", parent=body_style, fontName="Helvetica-Bold")))
                story.append(Paragraph(", ".join(services), body_style))
        except Exception:
            pass

    # Medical Profile
    if profile:
        story.append(Paragraph("🏥 Medical Information", section_style))
        med_data = [
            ["Full Name", profile.full_name or user.name],
            ["Age", str(profile.age) if profile.age else "N/A"],
            ["Blood Group", profile.blood_group or "Unknown"],
            ["Allergies", profile.allergies or "None"],
            ["Medical Conditions", profile.medical_conditions or "None"],
            ["Medications", profile.medications or "None"],
            ["Organ Donor", "Yes" if profile.organ_donor else "No"],
        ]
        _render_table(story, med_data, LIGHT, DARK)

    # Nearby Resources
    if incident.nearby_resources:
        try:
            resources = json.loads(incident.nearby_resources)
            if resources:
                story.append(Paragraph("🗺️ Nearby Emergency Resources", section_style))
                res_rows = [["Name", "Type", "Distance", "Est. Time"]]
                for r in resources[:8]:
                    res_rows.append([
                        r.get("name", "N/A"),
                        r.get("type", "N/A").replace("_", " ").title(),
                        f"{r.get('distance_km', 0):.1f} km",
                        f"{r.get('travel_time_min', 0)} min",
                    ])
                res_table = Table(res_rows, colWidths=[7 * cm, 4 * cm, 3 * cm, 3 * cm])
                res_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), RED),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ]))
                story.append(res_table)
        except Exception:
            pass

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated by ROADSoS AI | {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')} | "
        f"Emergency Helpline: 112",
        ParagraphStyle("Footer", parent=small_style, alignment=TA_CENTER)
    ))

    doc.build(story)
    return output_path


def generate_txt_report(incident: Incident, user: User, profile: Optional[MedicalProfile] = None) -> str:
    """Generate plain text report. Returns file path."""
    filename = f"report_{incident.incident_id}.txt"
    output_path = os.path.join(REPORTS_DIR, filename)

    ai_data = {}
    resources = []
    try:
        if incident.ai_analysis:
            ai_data = json.loads(incident.ai_analysis)
        if incident.nearby_resources:
            resources = json.loads(incident.nearby_resources)
    except Exception:
        pass

    lines = [
        "=" * 60,
        "   ROADSoS AI - EMERGENCY INCIDENT REPORT",
        "=" * 60,
        f"Incident ID   : {incident.incident_id}",
        f"Date & Time   : {incident.created_at.strftime('%d %B %Y, %I:%M:%S %p UTC')}",
        f"Status        : {incident.status.upper()}",
        f"Type          : {(incident.incident_type or 'Accident').title()}",
        f"Severity      : {(incident.severity_level or 'Unknown').upper()} ({incident.severity_score}/100)",
        "-" * 60,
        "LOCATION",
        f"Latitude      : {incident.latitude}",
        f"Longitude     : {incident.longitude}",
        f"Address       : {incident.address or 'N/A'}",
        f"Speed         : {f'{incident.speed_at_incident:.1f} km/h' if incident.speed_at_incident else 'N/A'}",
        f"Network       : {incident.network_status or 'N/A'}",
        "-" * 60,
        "AI ANALYSIS",
        incident.ai_summary or "No AI summary available.",
        "",
    ]

    if ai_data.get("recommended_actions"):
        lines.append("RECOMMENDED ACTIONS:")
        for i, action in enumerate(ai_data["recommended_actions"], 1):
            lines.append(f"  {i}. {action}")
        lines.append("")

    if profile:
        lines += [
            "-" * 60,
            "MEDICAL INFORMATION",
            f"Name          : {profile.full_name or user.name}",
            f"Age           : {profile.age or 'N/A'}",
            f"Blood Group   : {profile.blood_group or 'Unknown'}",
            f"Allergies     : {profile.allergies or 'None'}",
            f"Conditions    : {profile.medical_conditions or 'None'}",
            f"Medications   : {profile.medications or 'None'}",
            f"Organ Donor   : {'Yes' if profile.organ_donor else 'No'}",
            "",
        ]

    if resources:
        lines += ["-" * 60, "NEARBY RESOURCES"]
        for r in resources[:8]:
            lines.append(
                f"  {r.get('icon', '📍')} {r.get('name')} "
                f"({r.get('type', '').replace('_', ' ').title()}) "
                f"- {r.get('distance_km', 0):.1f} km, ~{r.get('travel_time_min', 0)} min"
            )
        lines.append("")

    lines += [
        "=" * 60,
        f"Generated by ROADSoS AI | {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}",
        "Emergency Helpline: 112 | Ambulance: 108 | Police: 100",
        "=" * 60,
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def generate_json_report(incident: Incident, user: User, profile: Optional[MedicalProfile] = None) -> str:
    """Generate JSON report. Returns file path."""
    filename = f"report_{incident.incident_id}.json"
    output_path = os.path.join(REPORTS_DIR, filename)

    ai_data = {}
    resources = []
    try:
        if incident.ai_analysis:
            ai_data = json.loads(incident.ai_analysis)
        if incident.nearby_resources:
            resources = json.loads(incident.nearby_resources)
    except Exception:
        pass

    report_data = {
        "meta": {
            "generated_by": "ROADSoS AI",
            "generated_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        },
        "incident": {
            "id": incident.incident_id,
            "type": incident.incident_type,
            "status": incident.status,
            "timestamp": incident.created_at.isoformat(),
            "severity": {
                "level": incident.severity_level,
                "score": incident.severity_score,
            },
        },
        "location": {
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "address": incident.address,
            "maps_url": f"https://www.openstreetmap.org/?mlat={incident.latitude}&mlon={incident.longitude}",
        },
        "vehicle_data": {
            "speed_kmh": incident.speed_at_incident,
            "heading": incident.heading,
        },
        "ai_analysis": ai_data,
        "ai_summary": incident.ai_summary,
        "nearby_resources": resources[:10],
        "medical_profile": {
            "blood_group": profile.blood_group if profile else None,
            "allergies": profile.allergies if profile else None,
            "conditions": profile.medical_conditions if profile else None,
            "organ_donor": profile.organ_donor if profile else None,
        } if profile else None,
        "emergency_numbers": {
            "national": "112",
            "police": "100",
            "fire": "101",
            "ambulance": "108",
            "disaster": "1077",
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

    return output_path


def _render_table(story, data, light_color, dark_color):
    table = Table(data, colWidths=[5 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), light_color),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, light_color]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))

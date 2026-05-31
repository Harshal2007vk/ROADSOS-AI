import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_ANALYSIS = {
    "severity_score": 65,
    "severity_level": "high",
    "risk_level": "HIGH",
    "injury_assessment": "Potential injuries detected. Immediate medical evaluation required.",
    "recommended_actions": [
        "Call emergency services (112) immediately",
        "Do not move injured persons unless there is immediate danger",
        "Keep victims warm and calm",
        "Apply first aid if trained to do so",
        "Secure the accident scene to prevent further accidents",
        "Document evidence with photos if safe to do so"
    ],
    "required_services": ["Ambulance", "Police", "Fire Brigade"],
    "immediate_steps": [
        "Ensure scene safety",
        "Check for breathing and pulse",
        "Stop severe bleeding with direct pressure",
        "Keep victim still and reassured"
    ],
    "do_not": [
        "Do not give food or water to injured person",
        "Do not remove helmets without training",
        "Do not leave victim alone"
    ],
    "estimated_response_time_min": 8,
    "ai_confidence": 0.75,
    "disclaimer": "AI analysis is supplementary. Always call 112 for professional emergency response."
}


def analyze_emergency(
    description: str,
    incident_type: str = "accident",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    speed_kmh: Optional[float] = None,
    acceleration: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Analyze emergency using Gemini AI API.
    Returns structured assessment with severity, actions, and required services.
    Falls back to rule-based analysis if API unavailable.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("No Gemini API key configured. Using rule-based fallback analysis.")
        return _rule_based_analysis(description, incident_type, speed_kmh, acceleration)

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""You are an emergency response AI assistant. Analyze this emergency situation and respond ONLY with a valid JSON object.

EMERGENCY DETAILS:
- Type: {incident_type}
- Description: {description}
- Location: {f'Lat {latitude:.4f}, Lon {longitude:.4f}' if latitude and longitude else 'Unknown'}
- Vehicle Speed: {f'{speed_kmh:.1f} km/h' if speed_kmh else 'Unknown'}
- Acceleration Data: {json.dumps(acceleration) if acceleration else 'Not available'}

Respond with ONLY this JSON structure (no markdown, no extra text):
{{
  "severity_score": <integer 0-100>,
  "severity_level": "<low|moderate|high|critical>",
  "risk_level": "<LOW|MODERATE|HIGH|CRITICAL>",
  "injury_assessment": "<detailed assessment string>",
  "recommended_actions": ["<action1>", "<action2>", "<action3>", "<action4>", "<action5>"],
  "required_services": ["<service1>", "<service2>"],
  "immediate_steps": ["<step1>", "<step2>", "<step3>"],
  "do_not": ["<warning1>", "<warning2>"],
  "estimated_response_time_min": <integer>,
  "ai_confidence": <float 0-1>,
  "disclaimer": "AI analysis is supplementary. Always call 112 for professional emergency response."
}}"""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=800,
            )
        )

        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        result = json.loads(text)
        result["source"] = "gemini_ai"
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini response parse error: {e}")
        return _rule_based_analysis(description, incident_type, speed_kmh, acceleration)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _rule_based_analysis(description, incident_type, speed_kmh, acceleration)


def generate_incident_summary(
    incident_type: str,
    location: str,
    timestamp: str,
    severity_level: str,
    nearest_resource: Optional[str] = None,
    nearest_distance_km: Optional[float] = None,
    description: Optional[str] = None,
) -> str:
    """Generate a concise, professional incident summary."""
    if not settings.GEMINI_API_KEY:
        return _generate_fallback_summary(
            incident_type, location, timestamp, severity_level,
            nearest_resource, nearest_distance_km
        )

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""Generate a professional, one-paragraph emergency incident summary (60-80 words) for a first responder briefing.

Facts:
- Incident Type: {incident_type}
- Location: {location}
- Time: {timestamp}
- Severity: {severity_level}
- Nearest Facility: {nearest_resource or 'Unknown'} ({f'{nearest_distance_km:.1f} km' if nearest_distance_km else 'distance unknown'})
- Description: {description or 'No additional description'}

Write only the summary paragraph. No headers, no bullet points."""

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        return _generate_fallback_summary(
            incident_type, location, timestamp, severity_level,
            nearest_resource, nearest_distance_km
        )


def get_disaster_guidance(disaster_type: str, location: str = "your area") -> Dict[str, Any]:
    """Get AI-powered disaster safety guidance."""
    disaster_guides = {
        "flood": {
            "immediate_actions": [
                "Move to higher ground immediately",
                "Avoid walking through flood water",
                "Do not attempt to drive through flooded roads",
                "Disconnect electrical appliances",
                "Keep emergency kit ready"
            ],
            "safety_tips": [
                "Stay informed via radio/TV",
                "Mark your location if trapped",
                "Signal for help from upper floors"
            ],
            "evacuation_priority": "HIGH",
            "estimated_danger_level": "EXTREME"
        },
        "earthquake": {
            "immediate_actions": [
                "DROP to hands and knees",
                "Take COVER under sturdy table or against interior wall",
                "HOLD ON until shaking stops",
                "Stay away from windows and heavy objects",
                "Do not run outside during shaking"
            ],
            "safety_tips": [
                "After shaking: check for injuries",
                "Expect aftershocks",
                "Check for gas leaks",
                "Stay away from damaged buildings"
            ],
            "evacuation_priority": "MODERATE",
            "estimated_danger_level": "HIGH"
        },
        "cyclone": {
            "immediate_actions": [
                "Evacuate coastal and low-lying areas",
                "Board up windows and doors",
                "Store emergency supplies (water, food, medicines)",
                "Keep battery-powered radio",
                "Know your evacuation route"
            ],
            "safety_tips": [
                "Stay indoors during the storm",
                "Eye of cyclone is deceptively calm - stay sheltered",
                "Do not go out until all-clear given"
            ],
            "evacuation_priority": "HIGH",
            "estimated_danger_level": "EXTREME"
        },
        "tsunami": {
            "immediate_actions": [
                "Move to high ground IMMEDIATELY after earthquake",
                "Do not wait for official warning if you feel strong shaking",
                "Stay away from beaches and coastline",
                "Follow tsunami evacuation routes",
                "Go at least 1km inland or 30m above sea level"
            ],
            "safety_tips": [
                "First wave may not be largest",
                "Stay away until officials declare it safe",
                "Tsunami can arrive within minutes"
            ],
            "evacuation_priority": "CRITICAL",
            "estimated_danger_level": "EXTREME"
        },
        "wildfire": {
            "immediate_actions": [
                "Evacuate if ordered by authorities",
                "Close all windows and doors",
                "Remove flammable materials from around home",
                "Wear N95 mask if smoke is heavy",
                "Keep vehicle fueled and facing exit"
            ],
            "safety_tips": [
                "Never shelter in car during wildfire",
                "Stay low to avoid smoke inhalation",
                "Call 101 for fire emergency"
            ],
            "evacuation_priority": "HIGH",
            "estimated_danger_level": "EXTREME"
        },
        "landslide": {
            "immediate_actions": [
                "Evacuate areas prone to sliding",
                "Move away from river channels",
                "Listen for unusual sounds (cracking trees, boulders)",
                "Watch for sudden change in stream water color",
                "Avoid steep slopes and valleys"
            ],
            "safety_tips": [
                "Do not return until area declared safe",
                "Check for gas leaks and structural damage",
                "Report damage to authorities"
            ],
            "evacuation_priority": "HIGH",
            "estimated_danger_level": "HIGH"
        },
        "heatwave": {
            "immediate_actions": [
                "Stay indoors during peak heat (11 AM - 4 PM)",
                "Drink water every 30 minutes",
                "Wear light, loose clothing",
                "Never leave children or elderly in cars",
                "Use wet cloth on neck and wrists"
            ],
            "safety_tips": [
                "Check on elderly neighbors",
                "Avoid strenuous outdoor activities",
                "Know signs of heat stroke: confusion, no sweating"
            ],
            "evacuation_priority": "LOW",
            "estimated_danger_level": "MODERATE"
        }
    }

    guide = disaster_guides.get(disaster_type.lower(), {
        "immediate_actions": ["Follow local authority instructions", "Stay calm and alert"],
        "safety_tips": ["Keep emergency contacts handy"],
        "evacuation_priority": "MODERATE",
        "estimated_danger_level": "MODERATE"
    })

    guide["disaster_type"] = disaster_type
    guide["location"] = location
    guide["emergency_numbers"] = {
        "national_emergency": "112",
        "police": "100",
        "fire": "101",
        "ambulance": "108",
        "disaster_management": "1077"
    }

    return guide


def _rule_based_analysis(
    description: str,
    incident_type: str,
    speed_kmh: Optional[float],
    acceleration: Optional[Dict]
) -> Dict[str, Any]:
    """Rule-based fallback when AI is unavailable."""
    result = FALLBACK_ANALYSIS.copy()
    result["source"] = "rule_based"

    keywords_critical = ["unconscious", "not breathing", "trapped", "fire", "blood", "severe", "critical"]
    keywords_high = ["injured", "hurt", "collision", "crash", "accident", "broken", "pain"]
    keywords_moderate = ["minor", "fender", "small", "slow"]

    desc_lower = description.lower() if description else ""

    if any(kw in desc_lower for kw in keywords_critical):
        result["severity_score"] = 90
        result["severity_level"] = "critical"
        result["risk_level"] = "CRITICAL"
        result["required_services"] = ["Ambulance", "Police", "Fire Brigade", "Trauma Team"]
    elif any(kw in desc_lower for kw in keywords_high):
        result["severity_score"] = 70
        result["severity_level"] = "high"
        result["risk_level"] = "HIGH"
        result["required_services"] = ["Ambulance", "Police"]
    elif any(kw in desc_lower for kw in keywords_moderate):
        result["severity_score"] = 35
        result["severity_level"] = "moderate"
        result["risk_level"] = "MODERATE"
        result["required_services"] = ["Police"]

    if speed_kmh and speed_kmh > 80:
        result["severity_score"] = min(100, result["severity_score"] + 15)

    return result


def _generate_fallback_summary(
    incident_type, location, timestamp, severity_level,
    nearest_resource, nearest_distance_km
) -> str:
    resource_str = ""
    if nearest_resource and nearest_distance_km:
        resource_str = f" Nearest {nearest_resource} is {nearest_distance_km:.1f} km away."
    elif nearest_resource:
        resource_str = f" Nearest facility is {nearest_resource}."

    action = {
        "critical": "Immediate emergency dispatch is strongly recommended.",
        "high": "Prompt emergency response is required.",
        "moderate": "Emergency services should be notified.",
        "low": "Standard emergency procedures apply."
    }.get(severity_level, "Emergency services have been notified.")

    return (
        f"A {incident_type} incident was reported near {location} at {timestamp}. "
        f"Estimated severity is {severity_level}.{resource_str} {action} "
        f"ROADSoS AI has logged the incident and alerted nearby services."
    )

import httpx
import logging
import math
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def estimate_travel_time(distance_km: float, speed_kmh: float = 40.0) -> int:
    """Estimate travel time in minutes at given speed."""
    return max(1, int((distance_km / speed_kmh) * 60))


RESOURCE_QUERIES = {
    "hospital": '["amenity"~"hospital|clinic|doctors"]',
    "police": '["amenity"="police"]',
    "fire_station": '["amenity"="fire_station"]',
    "pharmacy": '["amenity"="pharmacy"]',
    "fuel": '["amenity"="fuel"]',
    "mechanic": '["shop"~"car_repair|tyres|vehicle"]',
    "blood_bank": '["amenity"~"blood_bank|blood_donation"]',
}

RESOURCE_ICONS = {
    "hospital": "🏥",
    "police": "🚔",
    "fire_station": "🚒",
    "pharmacy": "💊",
    "fuel": "⛽",
    "mechanic": "🔧",
    "blood_bank": "🩸",
}


def fetch_nearby_resources(
    latitude: float,
    longitude: float,
    radius_m: int = None,
    resource_types: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Query Overpass API for nearby emergency resources.
    Returns sorted list by distance.
    """
    if radius_m is None:
        radius_m = settings.DEFAULT_SEARCH_RADIUS_M

    if resource_types is None:
        resource_types = list(RESOURCE_QUERIES.keys())

    # Build combined Overpass QL query
    union_parts = []
    for rtype in resource_types:
        if rtype in RESOURCE_QUERIES:
            filter_str = RESOURCE_QUERIES[rtype]
            union_parts.append(f'node{filter_str}(around:{radius_m},{latitude},{longitude});')
            union_parts.append(f'way{filter_str}(around:{radius_m},{latitude},{longitude});')

    query = f"""
[out:json][timeout:25];
(
  {''.join(union_parts)}
);
out center 50;
"""

    results = []
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                settings.OVERPASS_API_URL,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = (
                tags.get("name")
                or tags.get("name:en")
                or tags.get("operator")
                or "Unknown Facility"
            )

            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")

            if not lat or not lon:
                continue

            distance_km = haversine_km(latitude, longitude, lat, lon)

            rtype = _classify_resource(tags)
            icon = RESOURCE_ICONS.get(rtype, "📍")

            resource = {
                "id": element.get("id"),
                "name": name,
                "type": rtype,
                "icon": icon,
                "latitude": lat,
                "longitude": lon,
                "distance_km": round(distance_km, 2),
                "travel_time_min": estimate_travel_time(distance_km),
                "phone": tags.get("phone") or tags.get("contact:phone") or tags.get("emergency:phone"),
                "website": tags.get("website") or tags.get("contact:website"),
                "address": _build_address(tags),
                "is_24h": tags.get("opening_hours") == "24/7",
                "osm_type": element.get("type"),
            }
            results.append(resource)

    except httpx.TimeoutException:
        logger.warning("Overpass API timeout. Returning empty resource list.")
    except httpx.HTTPError as e:
        logger.error(f"Overpass API HTTP error: {e}")
    except Exception as e:
        logger.error(f"Resource finder error: {e}")

    results.sort(key=lambda x: x["distance_km"])
    return results


def _classify_resource(tags: Dict) -> str:
    amenity = tags.get("amenity", "")
    shop = tags.get("shop", "")

    if amenity in ("hospital", "clinic", "doctors"):
        return "hospital"
    elif amenity == "police":
        return "police"
    elif amenity == "fire_station":
        return "fire_station"
    elif amenity == "pharmacy":
        return "pharmacy"
    elif amenity == "fuel":
        return "fuel"
    elif amenity in ("blood_bank", "blood_donation"):
        return "blood_bank"
    elif shop in ("car_repair", "tyres", "vehicle"):
        return "mechanic"
    return "other"


def _build_address(tags: Dict) -> str:
    parts = []
    for key in ("addr:housenumber", "addr:street", "addr:city", "addr:state"):
        val = tags.get(key)
        if val:
            parts.append(val)
    return ", ".join(parts) if parts else tags.get("addr:full", "")


def get_directions_url(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> str:
    """Generate OpenStreetMap/OSRM directions URL."""
    return f"https://www.openstreetmap.org/directions?from={origin_lat},{origin_lon}&to={dest_lat},{dest_lon}"

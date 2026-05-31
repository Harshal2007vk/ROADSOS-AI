import httpx
from typing import List, Dict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Mapping of Overpass tags to a friendly resource type
RESOURCE_TAGS = {
    "hospital": "amenity=hospital",
    "police": "amenity=police",
    "fuel": "amenity=fuel",
    "mechanic": "shop=car",
    "towing": "service=roadside_assistance",
}

def build_overpass_query(lat: float, lon: float, radius: int = 5000) -> str:
    """Construct a single Overpass QL query that fetches all required POIs.
    The query searches within a circular area centred on the given coordinates.
    """
    # Convert radius to meters (Overpass expects meters)
    radius_m = radius
    # Build the OR clause for each tag
    filters = " ".join(
        f"node[{tag}];" for tag in RESOURCE_TAGS.values()
    )
    query = f"""
    [out:json][timeout:25];
    (
        {filters}
    );
    out center {radius_m};
    """
    # Overpass requires the area definition via around
    # Use "around" filter on the centre point
    query = f"""
    [out:json][timeout:25];
    (
        node[{RESOURCE_TAGS['hospital']}](around:{radius_m},{lat},{lon});
        node[{RESOURCE_TAGS['police']}](around:{radius_m},{lat},{lon});
        node[{RESOURCE_TAGS['fuel']}](around:{radius_m},{lat},{lon});
        node[{RESOURCE_TAGS['mechanic']}](around:{radius_m},{lat},{lon});
        node[{RESOURCE_TAGS['towing']}](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    return query.strip()

async def fetch_nearby_resources(lat: float, lon: float, radius: int = 5000) -> List[Dict]:
    """Call Overpass API and return a list of resources.
    Each resource dict contains:
        - id
        - type (hospital, police, fuel, mechanic, towing)
        - name (if available)
        - lat, lon
    """
    query = build_overpass_query(lat, lon, radius)
    async with httpx.AsyncClient() as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        data = response.json()
        elements = data.get("elements", [])
        resources: List[Dict] = []
        for el in elements:
            tags = el.get("tags", {})
            # Determine type based on which tag matched
            res_type = None
            for key, overpass_tag in RESOURCE_TAGS.items():
                k, v = overpass_tag.split("=")
                if tags.get(k) == v:
                    res_type = key
                    break
            if not res_type:
                continue
            resources.append({
                "id": el.get("id"),
                "type": res_type,
                "name": tags.get("name", f"{res_type.title()}"),
                "lat": el.get("lat") or el.get("center", {}).get("lat"),
                "lon": el.get("lon") or el.get("center", {}).get("lon"),
            })
    return resources

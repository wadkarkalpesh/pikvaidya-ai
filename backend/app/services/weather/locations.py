"""
PikVaidya AI — Maharashtra Agricultural Locations & Coordinate Registry
=======================================================================
Maintains geographic centroids, agricultural zones, and major crop profiles
for districts in Maharashtra, India.
"""

from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


# Standard Maharashtra Agricultural District Registry with coordinates and agro-climatic zones
MAHARASHTRA_DISTRICTS: Dict[str, Dict[str, Any]] = {
    "kolhapur": {
        "name": "Kolhapur",
        "name_mr": "कोल्हापूर",
        "name_hi": "कोल्हापुर",
        "latitude": 16.7050,
        "longitude": 74.2433,
        "agro_zone": "Sub-Montane Zone / Western Maharashtra Plain",
        "primary_crops": ["sugarcane", "rice", "soybean", "groundnut"],
        "soil_type": "Deep Black Clay & Lateritic Soils",
    },
    "pune": {
        "name": "Pune",
        "name_mr": "पुणे",
        "name_hi": "पुणे",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "agro_zone": "Transition Zone / Western Ghats Rainshadow",
        "primary_crops": ["sugarcane", "tomato", "onion", "wheat", "grape"],
        "soil_type": "Medium Black Soils",
    },
    "sangli": {
        "name": "Sangli",
        "name_mr": "सांगली",
        "name_hi": "सांगली",
        "latitude": 16.8524,
        "longitude": 74.5815,
        "agro_zone": "Western Maharashtra Scarcity Zone",
        "primary_crops": ["sugarcane", "grape", "turmeric", "soybean"],
        "soil_type": "Medium to Deep Black Clay",
    },
    "satara": {
        "name": "Satara",
        "name_mr": "सातारा",
        "name_hi": "सतारा",
        "latitude": 17.6805,
        "longitude": 73.9935,
        "agro_zone": "Sub-Montane & Transition Zone",
        "primary_crops": ["sugarcane", "strawberry", "ginger", "soybean"],
        "soil_type": "Medium Black and Red Loamy",
    },
    "nashik": {
        "name": "Nashik",
        "name_mr": "नाशिक",
        "name_hi": "नासिक",
        "latitude": 19.9975,
        "longitude": 73.7898,
        "agro_zone": "Western Ghats High Rainfall & Transition Zone",
        "primary_crops": ["onion", "tomato", "grape", "pomegranate"],
        "soil_type": "Medium Black Clay to Sandy Loam",
    },
    "solapur": {
        "name": "Solapur",
        "name_mr": "सोलापूर",
        "name_hi": "सोलापुर",
        "latitude": 17.6599,
        "longitude": 75.9064,
        "agro_zone": "Scarcity Zone of Maharashtra",
        "primary_crops": ["sugarcane", "pomegranate", "jowar", "onion"],
        "soil_type": "Deep Black Heavy Clay",
    },
    "ahmednagar": {
        "name": "Ahmednagar",
        "name_mr": "अहमदनगर",
        "name_hi": "अहमदनगर",
        "latitude": 19.0952,
        "longitude": 74.7496,
        "agro_zone": "Central Scarcity Zone",
        "primary_crops": ["sugarcane", "onion", "pomegranate", "cotton"],
        "soil_type": "Medium Black Loam",
    },
    "chhatrapati_sambhajinagar": {
        "name": "Chhatrapati Sambhajinagar",
        "name_mr": "छत्रपती संभाजीनगर",
        "name_hi": "छत्रपति संभाजीनगर",
        "latitude": 19.8762,
        "longitude": 75.3433,
        "agro_zone": "Marathwada Central Plateau",
        "primary_crops": ["cotton", "soybean", "maize", "sweet lime", "onion"],
        "soil_type": "Medium Deep Black Soils",
        "aliases": ["aurangabad", "sambhajinagar"],
    },
    "nagpur": {
        "name": "Nagpur",
        "name_mr": "नागपूर",
        "name_hi": "नागपुर",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "agro_zone": "Eastern Vidarbha Zone",
        "primary_crops": ["orange", "cotton", "soybean", "paddy"],
        "soil_type": "Black Cotton Soil & Alluvial",
    },
    "amravati": {
        "name": "Amravati",
        "name_mr": "अमरावती",
        "name_hi": "अमरावती",
        "latitude": 20.9374,
        "longitude": 77.7796,
        "agro_zone": "Western Vidarbha Zone",
        "primary_crops": ["cotton", "soybean", "orange", "pigeonpea"],
        "soil_type": "Deep Black Clayey Cotton Soil",
    },
    "jalgaon": {
        "name": "Jalgaon",
        "name_mr": "जळगाव",
        "name_hi": "जलगांव",
        "latitude": 21.0077,
        "longitude": 75.5626,
        "agro_zone": "Khandesh Tapi Basin",
        "primary_crops": ["banana", "cotton", "maize", "pulses"],
        "soil_type": "Deep Alluvial & Black Clay",
    },
}

# Alias mapping for fuzzy or historic names
DISTRICT_ALIASES = {
    "aurangabad": "chhatrapati_sambhajinagar",
    "sambhajinagar": "chhatrapati_sambhajinagar",
    "nasik": "nashik",
    "ahmadnagar": "ahmednagar",
}


def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Validates whether geographic coordinates are mathematically and physically valid.
    Raises ValueError if coordinates fall outside global or regional acceptable bounds.
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid coordinate format: lat={latitude}, lon={longitude}. Must be numeric.")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude out of bounds: {lat}. Must be between -90.0 and +90.0.")

    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude out of bounds: {lon}. Must be between -180.0 and +180.0.")

    return round(lat, 4), round(lon, 4)


def resolve_location(
    location_query: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Tuple[float, float, str]:
    """
    Resolves geographic location using either district/city query or explicit coordinates.
    Prioritizes explicit coordinates when provided; otherwise resolves Maharashtra district centroid.
    Defaults to Kolhapur / Western Maharashtra if unspecified.
    """
    # 1. Explicit Coordinates provided
    if latitude is not None and longitude is not None:
        lat, lon = validate_coordinates(latitude, longitude)
        
        # Check if coordinates closely match any registered Maharashtra district centroid
        matched_name = "Custom Farm GPS Location"
        for key, dist in MAHARASHTRA_DISTRICTS.items():
            if abs(dist["latitude"] - lat) < 0.15 and abs(dist["longitude"] - lon) < 0.15:
                matched_name = f"{dist['name']}, Maharashtra"
                break
        return lat, lon, matched_name

    # 2. Location name or district query provided
    if location_query:
        norm = location_query.strip().lower().replace(" ", "_").replace("-", "_")
        target_key = DISTRICT_ALIASES.get(norm, norm)
        
        # Check direct or substring match
        for key, dist in MAHARASHTRA_DISTRICTS.items():
            if key == target_key or norm in key or norm in dist["name"].lower():
                return dist["latitude"], dist["longitude"], f"{dist['name']}, Maharashtra"

        logger.warning(f"District '{location_query}' not found in registry. Defaulting to Kolhapur, Maharashtra.")

    # 3. Fallback default: Kolhapur, Maharashtra (Sugarcane/Agri hub)
    default_dist = MAHARASHTRA_DISTRICTS["kolhapur"]
    return default_dist["latitude"], default_dist["longitude"], f"{default_dist['name']}, Maharashtra"


def list_supported_districts() -> List[Dict[str, Any]]:
    """Returns a list of all pre-indexed Maharashtra districts and metadata."""
    return [
        {
            "id": key,
            "name": val["name"],
            "name_mr": val["name_mr"],
            "name_hi": val["name_hi"],
            "latitude": val["latitude"],
            "longitude": val["longitude"],
            "agro_zone": val["agro_zone"],
            "primary_crops": val["primary_crops"],
            "soil_type": val["soil_type"],
        }
        for key, val in MAHARASHTRA_DISTRICTS.items()
    ]


get_all_districts = list_supported_districts


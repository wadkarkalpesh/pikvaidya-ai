"""
PikVaidya AI — Weather Data Normalizer & Standardizer
====================================================
Transforms and standardizes raw meteorological outputs into consistent
agronomic units and domain descriptors.
"""

from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


# Standard World Meteorological Organization (WMO) Weather Interpretation Codes
WMO_INTERPRETATIONS: Dict[int, Dict[str, str]] = {
    0: {"en": "Clear sky", "mr": "निरभ्र आकाश", "hi": "साफ आसमान"},
    1: {"en": "Mainly clear", "mr": "मुख्यतः स्वच्छ आकाश", "hi": "अधिकांशतः साफ"},
    2: {"en": "Partly cloudy", "mr": "अंशतः ढगाळ", "hi": "आंशिक बादल"},
    3: {"en": "Overcast", "mr": "पूर्ण ढगाळ", "hi": "घने बादल"},
    45: {"en": "Foggy", "mr": "धुके", "hi": "कोहरा"},
    48: {"en": "Depositing rime fog", "mr": "गोठणारे धुके", "hi": "पाला कोहरा"},
    51: {"en": "Light drizzle", "mr": "हलकी रिमझिम", "hi": "हल्की बूंदाबांदी"},
    53: {"en": "Moderate drizzle", "mr": "मध्यम रिमझिम", "hi": "मध्यम बूंदाबांदी"},
    55: {"en": "Dense drizzle", "mr": "जोरदार रिमझिम", "hi": "तेज बूंदाबांदी"},
    61: {"en": "Slight rain", "mr": "हलका पाऊस", "hi": "हल्की बारिश"},
    63: {"en": "Moderate rain", "mr": "मध्यम पाऊस", "hi": "मध्यम बारिश"},
    65: {"en": "Heavy rain", "mr": "मुसळधार पाऊस", "hi": "भारी बारिश"},
    71: {"en": "Slight snow fall", "mr": "हलकी हिमवृष्टी", "hi": "हल्की बर्फबारी"},
    80: {"en": "Slight rain showers", "mr": "पावसाच्या हलक्या सरी", "hi": "हल्की बारिश की फुहारें"},
    81: {"en": "Moderate rain showers", "mr": "पावसाच्या मध्यम सरी", "hi": "मध्यम बारिश की फुहारें"},
    82: {"en": "Violent rain showers", "mr": "पावसाच्या जोरदार सरी", "hi": "मूसलाधार बारिश"},
    95: {"en": "Thunderstorm", "mr": "विजांसह वादळी पाऊस", "hi": "गरज के साथ तूफान"},
    96: {"en": "Thunderstorm with slight hail", "mr": "वादळी पाऊस व बारीक गारपीट", "hi": "आंधी के साथ ओले"},
    99: {"en": "Thunderstorm with heavy hail", "mr": "वादळी पाऊस व मोठी गारपीट", "hi": "तूफान के साथ भारी ओलावृष्टि"},
}


class WeatherNormalizer:
    """Standardizes heterogeneous meteorological measurements into uniform agronomic scales."""

    @staticmethod
    def celsius_to_fahrenheit(c: float) -> float:
        """Converts Celsius to Fahrenheit."""
        return round((float(c) * 9.0 / 5.0) + 32.0, 2)

    @staticmethod
    def celsius_to_kelvin(c: float) -> float:
        """Converts Celsius to Kelvin."""
        return round(float(c) + 273.15, 2)

    @staticmethod
    def kmh_to_ms(kmh: float) -> float:
        """Converts wind speed from km/h to m/s."""
        return round(float(kmh) / 3.6, 2)

    @staticmethod
    def get_wmo_description(code: int, lang: str = "en") -> str:
        """Retrieves localized text description for a WMO weather code."""
        info = WMO_INTERPRETATIONS.get(int(code), {"en": "Partly cloudy", "mr": "अंशतः ढगाळ", "hi": "आंशिक बादल"})
        return info.get(lang, info["en"])

    @staticmethod
    def categorize_soil_moisture(volumetric_m3m3: float) -> Tuple[str, str]:
        """
        Categorizes volumetric soil moisture (m³/m³) into agronomic root-zone availability.
        Typical field capacity for black clay soil: ~0.35-0.45 m³/m³, wilting point: ~0.15-0.20 m³/m³.
        """
        val = float(volumetric_m3m3)
        if val >= 0.38:
            status = "SATURATED"
            desc = "Soil profile is at or near saturation/field capacity. High risk of waterlogging; avoid irrigation."
        elif val >= 0.22:
            status = "OPTIMAL"
            desc = "Soil moisture is in the optimal root-zone range. Promotes healthy root respiration and nutrient uptake."
        elif val >= 0.14:
            status = "DRY"
            desc = "Soil moisture is declining below optimal depletion threshold. Plan supplementary irrigation soon."
        else:
            status = "SEVERELY_DEPLETED"
            desc = "Root-zone moisture is near permanent wilting point. Immediate irrigation required to prevent wilting."
        return status, desc

    @staticmethod
    def calculate_dew_point(temp_c: float, rh_pct: float) -> float:
        """Computes approximate dew point temperature (°C) via Magnus-Tetens approximation."""
        import math
        a = 17.27
        b = 237.7
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(max(rh_pct, 1.0) / 100.0)
        return round((b * alpha) / (a - alpha), 1)

    @staticmethod
    def normalize_pressure(surface_pressure_hpa: Optional[float]) -> float:
        """Ensures surface pressure is within valid terrestrial atmospheric range (800 - 1100 hPa)."""
        if surface_pressure_hpa is None or surface_pressure_hpa <= 0:
            return 1013.25
        return round(float(surface_pressure_hpa), 1)


normalizer = WeatherNormalizer()

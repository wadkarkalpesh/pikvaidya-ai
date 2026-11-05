"""
PikVaidya AI — Agricultural Microclimate & Weather Service
==========================================================
Provides real-time ambient microclimate retrieval and agrochemical spray window
evaluation for Indian farming operations using Open-Meteo REST API.

Key Capabilities:
1. Microclimate Retrieval: Temperature, Relative Humidity, Wind Speed, Rain Forecast.
2. Agrochemical Spray Window Assessment:
   - Rain Wash-off Hazard Detection (suppresses spraying if rain in next 6h)
   - Wind Drift Risk Assessment (flags drift if wind > 15 km/h)
   - Thermal Scorch & Phytotoxicity Warnings (> 35°C)
3. Fungal Infection Conduciveness Index (temp 20-32°C & RH > 75%)
4. Resilient Fallback: Safe offline/cached defaults when internet is unavailable.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    precipitation_mm: float
    precipitation_probability_6h: float
    weather_condition: str
    is_live: bool = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class SprayWindowAssessment:
    status: str  # "OPTIMAL", "UNFAVOURABLE_RAIN_RISK", "UNFAVOURABLE_DRIFT_RISK", "UNFAVOURABLE_HEAT_STRESS", "MARGINAL"
    is_safe_to_spray: bool
    summary_en: str
    summary_mr: str
    summary_hi: str
    advisory_recommendation_en: str
    advisory_recommendation_mr: str
    advisory_recommendation_hi: str
    fungal_risk_level: str  # "HIGH", "MODERATE", "LOW"


class WeatherService:
    """Manages agricultural microclimate fetching and spray suitability diagnostics."""

    # Default coordinates: Western Maharashtra Sugarcane Belt (Kolhapur/Pune region)
    DEFAULT_LAT = 16.7050
    DEFAULT_LON = 74.2433
    TIMEOUT_SECONDS = 5.0

    # WMO Weather interpretation codes
    WMO_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        80: "Rain showers",
        95: "Thunderstorm",
    }

    async def get_current_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> WeatherData:
        """
        Retrieves real-time weather metrics for the specified geographic location.
        Falls back gracefully to regional historical baseline if external API is unreachable.
        """
        lat = latitude if latitude is not None else self.DEFAULT_LAT
        lon = longitude if longitude is not None else self.DEFAULT_LON

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m",
            "forecast_days": 1,
            "timezone": "auto"
        }

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    current = data.get("current", {})
                    hourly = data.get("hourly", {})

                    # Extract next 6 hours precipitation probability
                    precip_probs = hourly.get("precipitation_probability", [0])
                    next_6h_prob = float(max(precip_probs[:6])) if precip_probs else 0.0

                    wmo_code = current.get("weather_code", 0)
                    condition_text = self.WMO_CODES.get(wmo_code, "Partly cloudy")

                    return WeatherData(
                        temperature_c=round(float(current.get("temperature_2m", 28.0)), 1),
                        relative_humidity_pct=round(float(current.get("relative_humidity_2m", 65.0)), 1),
                        wind_speed_kmh=round(float(current.get("wind_speed_10m", 8.0)), 1),
                        precipitation_mm=round(float(current.get("precipitation", 0.0)), 1),
                        precipitation_probability_6h=round(next_6h_prob, 1),
                        weather_condition=condition_text,
                        is_live=True,
                        latitude=lat,
                        longitude=lon
                    )
        except Exception as exc:
            logger.warning(f"Live weather API unavailable ({exc}). Using regional agronomic fallback.")

        # Agronomic Fallback (typical warm tropical sugarcane climate)
        return WeatherData(
            temperature_c=28.5,
            relative_humidity_pct=68.0,
            wind_speed_kmh=9.0,
            precipitation_mm=0.0,
            precipitation_probability_6h=15.0,
            weather_condition="Regional Seasonal Baseline (Simulated)",
            is_live=False,
            latitude=lat,
            longitude=lon
        )

    def assess_spray_suitability(self, weather: WeatherData) -> SprayWindowAssessment:
        """
        Evaluates microclimate parameters against agronomical and statutory spraying standards.
        Enforces safety rules to prevent chemical wash-off, drift, and foliar phytotoxicity.
        """
        temp = weather.temperature_c
        rh = weather.relative_humidity_pct
        wind = weather.wind_speed_kmh
        precip = weather.precipitation_mm
        rain_prob = weather.precipitation_probability_6h

        # 1. Calculate fungal infection risk level
        if (20.0 <= temp <= 32.0) and (rh >= 75.0):
            fungal_risk = "HIGH"
        elif (18.0 <= temp <= 35.0) and (rh >= 60.0):
            fungal_risk = "MODERATE"
        else:
            fungal_risk = "LOW"

        # 2. Check for Rain Wash-Off Risk (Primary Blocker)
        if precip >= 0.8 or rain_prob >= 50.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_RAIN_RISK",
                is_safe_to_spray=False,
                summary_en=f"Rain Threat Detected (Precipitation probability: {rain_prob}% in next 6h).",
                summary_mr=f"पावसाची शक्यता आढळली (पुढील ६ तासांत पावसाची शक्यता {rain_prob}%).",
                summary_hi=f"बारिश का खतरा (अगले 6 घंटों में {rain_prob}% बारिश की संभावना)।",
                advisory_recommendation_en=(
                    "POSTPONE FOLIAR SPRAYING. Rainfall will wash away active chemical ingredients "
                    "before leaf absorption, resulting in financial loss and watercourse pollution. "
                    "Wait until foliage is completely dry post-rain."
                ),
                advisory_recommendation_mr=(
                    "फवारणी तात्काळ पुढे ढकला. पावसामुळे पानांवर फवारलेले औषध वाहून जाईल, "
                    "ज्यामुळे पैशांचे नुकसान व पाण्याचे प्रदूषण होईल. पाऊस थांबून पाने सुकल्यावरच फवारणी करावी."
                ),
                advisory_recommendation_hi=(
                    "छिड़काव स्थगित करें। बारिश के कारण दवा धुल जाएगी और पौधे इसे अवशोषित नहीं कर पाएंगे। "
                    "मौसम साफ होने और पत्तियां सूखने के बाद ही छिड़काव करें।"
                ),
                fungal_risk_level=fungal_risk
            )

        # 3. Check for High Wind Drift Risk (Secondary Blocker)
        if wind > 15.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_DRIFT_RISK",
                is_safe_to_spray=False,
                summary_en=f"High Wind Speed ({wind} km/h > 15 km/h threshold).",
                summary_mr=f"वाऱ्याचा वेग जास्त आहे ({wind} किमी/तास > १५ किमी/तास मर्यादा).",
                summary_hi=f"हवा की गति अधिक है ({wind} किमी/घंटा)।",
                advisory_recommendation_en=(
                    "AVOID SPRAYING DUE TO CHEMICAL DRIFT. High wind causes droplet drift to non-target crops, "
                    "reduces foliar deposition, and creates inhalation hazards under Insecticides Rules, 1971."
                ),
                advisory_recommendation_mr=(
                    "वाऱ्यामुळे औषधाचा तुषार उडून जाण्याचा धोका आहे. औषध बाजूच्या पिकांवर उडाल्याने नुकसान "
                    "आणि विषबाधेचा धोका संभवतो. वारा शांत झाल्यावरच फवारणी करा."
                ),
                advisory_recommendation_hi=(
                    "हवा तेज होने से दवा उड़कर अन्य फसलों पर जा सकती है। हवा शांत होने पर ही छिड़काव करें।"
                ),
                fungal_risk_level=fungal_risk
            )

        # 4. Check for Thermal Stress / Phytotoxicity Risk
        if temp > 35.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_HEAT_STRESS",
                is_safe_to_spray=False,
                summary_en=f"Extreme Temperature ({temp}°C > 35°C).",
                summary_mr=f"जास्त तापमान ({temp}°C > ३५°C).",
                summary_hi=f"अत्यधिक तापमान ({temp}°C > 35°C)।",
                advisory_recommendation_en=(
                    "AVOID MID-DAY SPRAYING. High ambient temperatures trigger rapid droplet evaporation "
                    "and severe leaf scorch (phytotoxicity). Schedule spraying during early morning (6:00 - 8:30 AM)."
                ),
                advisory_recommendation_mr=(
                    "दुपारच्या उन्हात फवारणी टाळा. जास्त तापमानामुळे औषध वाफ होऊन उडते व पाने करपण्याचा धोका असतो. "
                    "सकाळी ६:०० ते ८:३० दरम्यान किंवा संध्याकाळी ऊन कमी झाल्यावर फवारणी करा."
                ),
                advisory_recommendation_hi=(
                    "दोपहर की कड़ी धूप में छिड़काव न करें। इससे पत्तियां झुलस सकती हैं। सुबह या शाम को छिड़काव करें।"
                ),
                fungal_risk_level=fungal_risk
            )

        # 5. Optimal Spray Window
        return SprayWindowAssessment(
            status="OPTIMAL",
            is_safe_to_spray=True,
            summary_en=f"Optimal Spray Conditions ({temp}°C, {rh}% RH, Wind: {wind} km/h).",
            summary_mr=f"फवारणीसाठी अनुकूल हवामान ({temp}°C, {rh}% आर्द्रता, वारा: {wind} किमी/तास).",
            summary_hi=f"छिड़काव के लिए अनुकूल मौसम ({temp}°C, {rh}% नमी, हवा: {wind} किमी/घंटा)।",
            advisory_recommendation_en=(
                "CONDITIONS SUITABLE FOR FOLIAR SPRAYING. Wind speed and ambient temperature are within safe margins. "
                "Ensure thorough coverage of both upper and lower leaf surfaces. Use clean water with neutral pH."
            ),
            advisory_recommendation_mr=(
                "फवारणीसाठी हवामान अत्यंत योग्य आहे. पानांच्या दोन्ही बाजूंवर (वर व खाली) एकसारखा फवारा बसेल याची काळजी घ्या. "
                "फवारणीसाठी स्वच्छ व गोडे पाणी वापरावे."
            ),
            advisory_recommendation_hi=(
                "मौसम छिड़काव के लिए बहुत अच्छा है। पत्तियों के ऊपर और नीचे दोनों तरफ समान रूप से छिड़काव करें। "
                "साफ पानी का ही प्रयोग करें।"
            ),
            fungal_risk_level=fungal_risk
        )


weather_service = WeatherService()


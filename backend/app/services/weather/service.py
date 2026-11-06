"""
PikVaidya AI — Core Weather Service Orchestrator
===============================================
Orchestrates weather provider adapters, spatial caching, microclimate evaluation,
disease conduciveness indices, and irrigation / spraying safety gating.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from .base_provider import BaseWeatherProvider
from .open_meteo import OpenMeteoProvider
from .imd_provider import IMDWeatherProvider
from .locations import resolve_location, validate_coordinates, MAHARASHTRA_DISTRICTS
from .cache import weather_cache
from .normalizer import normalizer
from .schemas import (
    WeatherData,
    CurrentWeatherPayload,
    SoilTelemetry,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
    SprayWindowAssessment,
    DiseaseRiskAssessment,
    IrrigationAdvisory,
    ComprehensiveWeatherReport,
)

logger = logging.getLogger(__name__)


class WeatherService:
    """Enterprise-grade, resilient weather service orchestrator for PikVaidya AI."""

    DEFAULT_LAT = 16.7050
    DEFAULT_LON = 74.2433
    DEFAULT_LOCATION = "Kolhapur, Maharashtra"

    def __init__(self):
        self.primary_provider: BaseWeatherProvider = OpenMeteoProvider()
        self.alert_provider: BaseWeatherProvider = IMDWeatherProvider()

    async def get_current_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> WeatherData:
        """
        Legacy/Simple Interface: Returns simple WeatherData compatible with existing services and tests.
        """
        lat, lon, loc_name = resolve_location(None, latitude, longitude)
        report = await self.get_comprehensive_weather(lat, lon, loc_name)
        curr = report.current

        return WeatherData(
            temperature_c=curr.temperature_c,
            relative_humidity_pct=curr.relative_humidity_pct,
            wind_speed_kmh=curr.wind_speed_kmh,
            precipitation_mm=curr.precipitation_mm,
            precipitation_probability_6h=curr.precipitation_probability_6h,
            weather_condition=curr.weather_condition,
            is_live=curr.is_live,
            latitude=lat,
            longitude=lon
        )

    async def get_comprehensive_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_query: Optional[str] = None,
        location_name: Optional[str] = None,
        forecast_days: int = 7,
        force_refresh: bool = False,
    ) -> ComprehensiveWeatherReport:
        """
        Primary Weather Engine Method:
        Fetches current weather, soil telemetry, 24h hourly forecast, 7d daily forecast,
        spray window suitability, disease risks, irrigation advisory, and alerts.
        """
        loc_str = location_name or location_query
        lat, lon, loc_name = resolve_location(loc_str, latitude, longitude)


        # 1. Check Spatial Cache
        if not force_refresh:
            cached_data = await weather_cache.get(lat, lon, prefix="weather_comp")
            if cached_data:
                return ComprehensiveWeatherReport.model_validate(cached_data)

        # 2. Fetch Live Telemetry from Primary Provider
        try:
            telemetry = await self.primary_provider.fetch_current_and_forecast(
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                forecast_days=forecast_days,
            )
            current = telemetry["current"]
            soil = telemetry.get("soil")
            hourly_24h = telemetry.get("hourly_24h", [])
            daily_7d = telemetry.get("daily_7d", [])
            data_source = self.primary_provider.provider_name
        except Exception as exc:
            logger.warning(f"Live weather provider error ({exc}). Activating regional baseline fallback.")
            current, soil, hourly_24h, daily_7d = self._build_fallback_weather(lat, lon, loc_name)
            data_source = "fallback"

        # 3. Evaluate Agronomic Assessments
        spray_assessment = self.assess_spray_suitability(current)
        disease_risks = self.assess_disease_risks(current)
        irrigation_advisory = self.assess_irrigation_advisory(current, soil, hourly_24h, daily_7d)
        alerts = await self.generate_weather_alerts(current, hourly_24h, daily_7d, loc_name)

        report = ComprehensiveWeatherReport(
            current=current,
            soil=soil,
            hourly_24h=hourly_24h,
            daily_7d=daily_7d,
            spray_window=spray_assessment,
            disease_risks=disease_risks,
            irrigation=irrigation_advisory,
            alerts=alerts,
            location_name=loc_name,
            latitude=lat,
            longitude=lon,
            data_source=data_source,
            last_updated=current.fetched_at,
        )

        # 4. Cache Valid Result
        await weather_cache.set(lat, lon, report.model_dump(), prefix="weather_comp", ttl_seconds=900)
        return report

    async def get_forecast_only(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_query: Optional[str] = None,
        location_name: Optional[str] = None,
        days: int = 7,
    ) -> Tuple[List[HourlyForecastItem], List[DailyForecastItem]]:
        """Retrieves hourly and daily forecast slices."""
        report = await self.get_comprehensive_weather(
            latitude=latitude,
            longitude=longitude,
            location_query=location_query,
            location_name=location_name,
            forecast_days=days,
        )
        return report.hourly_24h, report.daily_7d

    async def get_weather_alerts(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_query: Optional[str] = None,
        location_name: Optional[str] = None,
    ) -> List[WeatherAlertItem]:
        """Retrieves active meteorological alerts."""
        report = await self.get_comprehensive_weather(
            latitude=latitude,
            longitude=longitude,
            location_query=location_query,
            location_name=location_name,
        )
        return report.alerts

    async def get_historical_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_query: Optional[str] = None,
        location_name: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> Dict[str, Any]:
        """Fetches historical reanalysis weather data via provider."""
        loc_str = location_name or location_query
        lat, lon, _ = resolve_location(loc_str, latitude, longitude)
        return await self.primary_provider.fetch_historical(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
        )

    def assess_spray_suitability(self, weather: Any) -> SprayWindowAssessment:
        """
        Evaluates microclimate parameters against agronomical and statutory spraying standards.
        Enforces safety rules to prevent chemical wash-off, drift, and foliar phytotoxicity.
        """
        temp = getattr(weather, "temperature_c", 25.0)
        rh = getattr(weather, "relative_humidity_pct", 60.0)
        wind = getattr(weather, "wind_speed_kmh", 8.0)
        precip = getattr(weather, "precipitation_mm", 0.0)
        rain_prob = getattr(weather, "precipitation_probability_6h", 10.0)

        # 1. Calculate fungal infection risk level
        if (20.0 <= temp <= 32.0) and (rh >= 75.0):
            fungal_risk = "HIGH"
        elif (18.0 <= temp <= 35.0) and (rh >= 60.0):
            fungal_risk = "MODERATE"
        else:
            fungal_risk = "LOW"

        # 2. Rain Wash-Off Risk (Primary Blocker)
        if precip >= 0.8 or rain_prob >= 50.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_RAIN_RISK",
                is_safe_to_spray=False,
                summary={
                    "en": f"Rain Threat Detected (Precipitation probability: {rain_prob}% in next 6h).",
                    "mr": f"पावसाची शक्यता आढळली (पुढील ६ तासांत पावसाची शक्यता {rain_prob}%).",
                    "hi": f"बारिश का खतरा (अगले 6 घंटों में {rain_prob}% बारिश की संभावना)।",
                },
                advisory_recommendation={
                    "en": (
                        "POSTPONE FOLIAR SPRAYING. Rainfall will wash away active chemical ingredients "
                        "before leaf absorption, resulting in financial loss and watercourse pollution. "
                        "Wait until foliage is completely dry post-rain."
                    ),
                    "mr": (
                        "फवारणी तात्काळ पुढे ढकला. पावसामुळे पानांवर फवारलेले औषध वाहून जाईल, "
                        "ज्यामुळे पैशांचे नुकसान व पाण्याचे प्रदूषण होईल. पाऊस थांबून पाने सुकल्यावरच फवारणी करावी."
                    ),
                    "hi": (
                        "छिड़काव स्थगित करें। बारिश के कारण दवा धुल जाएगी और पौधे इसे अवशोषित नहीं कर पाएंगे। "
                        "मौसम साफ होने और पत्तियां सूखने के बाद ही छिड़काव करें।"
                    ),
                },
                fungal_risk_level=fungal_risk,
            )

        # 3. High Wind Drift Risk (Secondary Blocker)
        if wind > 15.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_DRIFT_RISK",
                is_safe_to_spray=False,
                summary={
                    "en": f"High Wind Speed ({wind} km/h > 15 km/h threshold).",
                    "mr": f"वाऱ्याचा वेग जास्त आहे ({wind} किमी/तास > १५ किमी/तास मर्यादा).",
                    "hi": f"हवा की गति अधिक है ({wind} किमी/घंटा)।",
                },
                advisory_recommendation={
                    "en": (
                        "AVOID SPRAYING DUE TO CHEMICAL DRIFT. High wind causes droplet drift to non-target crops, "
                        "reduces foliar deposition, and creates inhalation hazards under Insecticides Rules, 1971."
                    ),
                    "mr": (
                        "वाऱ्यामुळे औषधाचा तुषार उडून जाण्याचा धोका आहे. औषध बाजूच्या पिकांवर उडाल्याने नुकसान "
                        "आणि विषबाधेचा धोका संभवतो. वारा शांत झाल्यावरच फवारणी करा."
                    ),
                    "hi": (
                        "हवा तेज होने से दवा उड़कर अन्य फसलों पर जा सकती है। हवा शांत होने पर ही छिड़काव करें।"
                    ),
                },
                fungal_risk_level=fungal_risk,
            )

        # 4. Thermal Stress / Phytotoxicity Risk
        if temp > 35.0:
            return SprayWindowAssessment(
                status="UNFAVOURABLE_HEAT_STRESS",
                is_safe_to_spray=False,
                summary={
                    "en": f"Extreme Temperature ({temp}°C > 35°C).",
                    "mr": f"जास्त तापमान ({temp}°C > ३५°C).",
                    "hi": f"अत्यधिक तापमान ({temp}°C > 35°C)।",
                },
                advisory_recommendation={
                    "en": (
                        "AVOID MID-DAY SPRAYING. High ambient temperatures trigger rapid droplet evaporation "
                        "and severe leaf scorch (phytotoxicity). Schedule spraying during early morning (6:00 - 8:30 AM)."
                    ),
                    "mr": (
                        "दुपारच्या उन्हात फवारणी टाळा. जास्त तापमानामुळे औषध वाफ होऊन उडते व पाने करपण्याचा धोका असतो. "
                        "सकाळी ६:०० ते ८:३० दरम्यान किंवा संध्याकाळी ऊन कमी झाल्यावर फवारणी करा."
                    ),
                    "hi": (
                        "दोपहर की कड़ी धूप में छिड़काव न करें। इससे पत्तियां झुलस सकती हैं। सुबह या शाम को छिड़काव करें।"
                    ),
                },
                fungal_risk_level=fungal_risk,
            )

        # 5. Optimal Spray Window
        return SprayWindowAssessment(
            status="OPTIMAL",
            is_safe_to_spray=True,
            summary={
                "en": f"Optimal Spray Conditions ({temp}°C, {rh}% RH, Wind: {wind} km/h).",
                "mr": f"फवारणीसाठी अनुकूल हवामान ({temp}°C, {rh}% आर्द्रता, वारा: {wind} किमी/तास).",
                "hi": f"छिड़काव के लिए अनुकूल मौसम ({temp}°C, {rh}% नमी, हवा: {wind} किमी/घंटा)।",
            },
            advisory_recommendation={
                "en": (
                    "CONDITIONS SUITABLE FOR FOLIAR SPRAYING. Wind speed and ambient temperature are within safe margins. "
                    "Ensure thorough coverage of both upper and lower leaf surfaces. Use clean water with neutral pH."
                ),
                "mr": (
                    "फवारणीसाठी हवामान अत्यंत योग्य आहे. पानांच्या दोन्ही बाजूंवर (वर व खाली) एकसारखा फवारा बसेल याची काळजी घ्या. "
                    "फवारणीसाठी स्वच्छ व गोडे पाणी वापरावे."
                ),
                "hi": (
                    "मौसम छिड़काव के लिए बहुत अच्छा है। पत्तियों के ऊपर और नीचे दोनों तरफ समान रूप से छिड़काव करें। "
                    "साफ पानी का ही प्रयोग करें।"
                ),
            },
            fungal_risk_level=fungal_risk,
        )

    def assess_disease_risks(self, current: CurrentWeatherPayload) -> List[DiseaseRiskAssessment]:
        """
        Evaluates disease-favourable microclimates using verified ICAR pathogen epidemiology.
        Note: Weather risk is an environmental indicator and DOES NOT constitute ground-truth diagnosis.
        """
        temp = current.temperature_c
        rh = current.relative_humidity_pct
        rain_6h = current.precipitation_probability_6h
        risks: List[DiseaseRiskAssessment] = []

        # 1. Sugarcane Red Rot (Colletotrichum falcatum)
        conds_redrot = []
        if 25.0 <= temp <= 31.0:
            conds_redrot.append(f"Temperature {temp}°C in conidial germination range (25-31°C)")
        if rh >= 80.0:
            conds_redrot.append(f"Relative humidity {rh}% exceeds spore dispersal threshold (80%)")
        if rain_6h >= 40.0:
            conds_redrot.append(f"Rainfall probability {rain_6h}% supports splash dispersal")

        if len(conds_redrot) >= 2:
            risks.append(
                DiseaseRiskAssessment(
                    crop="sugarcane",
                    disease="RedRot",
                    risk_level="HIGH" if len(conds_redrot) == 3 else "MODERATE",
                    favourable_conditions_met=conds_redrot,
                    description={
                        "en": "Current warm, humid conditions favor Colletotrichum falcatum fungal sporulation.",
                        "mr": "उबदार व दमट हवामानामुळे उसावरील तांबेरा व लाल कुज (Red Rot) रोगाचा प्रादुर्भाव वाढू शकतो.",
                        "hi": "गर्म और आर्द्र मौसम गन्ने में लाल सड़न रोग के बीजाणुओं के प्रसार के लिए अनुकूल है।",
                    },
                    agronomic_action={
                        "en": "Scout cane stools for spindle-shaped midrib lesions. Maintain field surface drainage.",
                        "mr": "उसाच्या पानांच्या मध्य शिरेची पाहणी करा. शेतात पाणी साचणार नाही याची काळजी घ्या.",
                        "hi": "गन्ने के खेत का निरीक्षण करें। खेत में जलभराव न होने दें।",
                    },
                )
            )

        # 2. Tomato Early Blight (Alternaria solani)
        conds_eb = []
        if 24.0 <= temp <= 30.0:
            conds_eb.append(f"Temperature {temp}°C favorable for Alternaria conidia (24-30°C)")
        if rh >= 75.0:
            conds_eb.append(f"High relative humidity ({rh}%) promotes leaf wetness")

        if len(conds_eb) == 2:
            risks.append(
                DiseaseRiskAssessment(
                    crop="tomato",
                    disease="Early_blight",
                    risk_level="HIGH",
                    favourable_conditions_met=conds_eb,
                    description={
                        "en": "High humidity and moderate warmth accelerate Alternaria solani fungal cycles.",
                        "mr": "जास्त आर्द्रता आणि मध्यम तापमानामुळे टोमॅटोवरील लवकर येणाऱ्या करप्याचा (Early Blight) धोका वाढतो.",
                        "hi": "अधिक नमी और सामान्य तापमान टमाटर के अगेती झुलसा रोग के लिए अनुकूल है।",
                    },
                    agronomic_action={
                        "en": "Inspect lower canopy leaflets for target-like concentric rings. Avoid sprinkler irrigation.",
                        "mr": "खालच्या पानांवर गोलाकार वलयांचे चट्टे तपासा. वरून पाणी देणे टाळा (ठिबक वापरा).",
                        "hi": "निचली पत्तियों की जांच करें। फव्वारा सिंचाई से बचें।",
                    },
                )
            )

        # 3. Onion Purple Blotch (Alternaria porri)
        conds_pb = []
        if 21.0 <= temp <= 30.0:
            conds_pb.append(f"Temperature {temp}°C ideal for purple blotch sporulation")
        if rh >= 80.0:
            conds_pb.append(f"High relative humidity ({rh}%) promotes tubular foliar infection")

        if len(conds_pb) == 2:
            risks.append(
                DiseaseRiskAssessment(
                    crop="onion",
                    disease="Purple_blotch",
                    risk_level="HIGH",
                    favourable_conditions_met=conds_pb,
                    description={
                        "en": "Warm humid microclimate triggers Alternaria porri sporulation on tubular onion leaves.",
                        "mr": "उबदार व दमट हवामानामुळे कांद्याच्या नळीसारख्या पानांवर जांभळा करपा (Purple Blotch) वाढू शकतो.",
                        "hi": "गर्म और अत्यधिक नमी युक्त मौसम प्याज के बैंगनी धब्बा रोग के लिए बहुत अनुकूल है।",
                    },
                    agronomic_action={
                        "en": "Scout onion foliage for sunken purple-centered elliptical lesions. Maintain row aeration.",
                        "mr": "कांद्याच्या पानांवर जांभळट-तपकिरी रंगाचे लांबट चट्टे तपासा. तण नियंत्रण ठेवा.",
                        "hi": "प्याज की पत्तियों पर बैंगनी रंग के धब्बों की जांच करें।",
                    },
                )
            )

        return risks

    def assess_irrigation_advisory(
        self,
        current: CurrentWeatherPayload,
        soil: Optional[SoilTelemetry],
        hourly: List[HourlyForecastItem],
        daily: List[DailyForecastItem],
    ) -> IrrigationAdvisory:
        """
        Formulates soil-moisture and precipitation-aware irrigation advisory.
        """
        rain_48h = sum(d.precipitation_sum_mm for d in daily[:2]) if daily else 0.0
        sm_status = soil.moisture_status if soil else "OPTIMAL"

        if rain_48h >= 15.0 or sm_status == "SATURATED":
            return IrrigationAdvisory(
                status="DEFER_IRRIGATION",
                soil_moisture_status=sm_status,
                rain_forecast_next_48h_mm=round(rain_48h, 1),
                reason={
                    "en": f"Significant rainfall expected ({rain_48h:.1f} mm in 48h) or soil already saturated.",
                    "mr": f"पुढील ४८ तासांत जोरदार पावसाचा अंदाज ({rain_48h:.1f} मिमी) किंवा जमिनीत पुरेसा ओलावा आहे.",
                    "hi": f"अगले 48 घंटों में अच्छी बारिश की संभावना ({rain_48h:.1f} मिमी) या मिट्टी में पर्याप्त नमी है।",
                },
                recommendation={
                    "en": "Suspend irrigation schedules. Ensure excess surface water drainage to prevent root hypoxia.",
                    "mr": "पाणी देणे बंद ठेवा. शेतात पाणी साचणार नाही याची खात्री करा जेणेकरून मुळांना हवा मिळेल.",
                    "hi": "सिंचाई स्थगित रखें। खेत से अतिरिक्त पानी की निकासी सुनिश्चित करें।",
                },
            )
        elif sm_status in ["DRY", "SEVERELY_DEPLETED"] and rain_48h < 5.0:
            return IrrigationAdvisory(
                status="SUPPLEMENTARY_IRRIGATION",
                soil_moisture_status=sm_status,
                rain_forecast_next_48h_mm=round(rain_48h, 1),
                reason={
                    "en": f"Root-zone soil moisture is low and negligible rain expected ({rain_48h:.1f} mm).",
                    "mr": f"जमिनीतील ओलावा कमी झाला असून पावसाची शक्यता नगण्य ({rain_48h:.1f} मिमी) आहे.",
                    "hi": f"मिट्टी में नमी कम है और बारिश की संभावना बहुत कम है।",
                },
                recommendation={
                    "en": "Apply light, targeted drip irrigation during early morning hours to relieve crop moisture stress.",
                    "mr": "पिकाला पाण्याचा ताण पडू नये म्हणून सकाळी ठिबक सिंचनाद्वारे हलके पाणी द्या.",
                    "hi": "फसल को पानी का तनाव न हो, इसके लिए सुबह के समय ड्रिप से हल्की सिंचाई करें।",
                },
            )
        else:
            return IrrigationAdvisory(
                status="NORMAL_IRRIGATION",
                soil_moisture_status=sm_status,
                rain_forecast_next_48h_mm=round(rain_48h, 1),
                reason={
                    "en": "Soil moisture and weather conditions are within normal seasonal range.",
                    "mr": "जमिनीतील ओलावा व हवामान सामान्य मर्यादेत आहे.",
                    "hi": "मिट्टी की नमी और मौसम सामान्य स्थिति में है।",
                },
                recommendation={
                    "en": "Continue routine crop-stage fertigation and irrigation schedules.",
                    "mr": "नियमित खत व पाणी व्यवस्थापन चालू ठेवा.",
                    "hi": "फसल की आवश्यकता अनुसार नियमित सिंचाई जारी रखें।",
                },
            )

    async def generate_weather_alerts(
        self,
        current: CurrentWeatherPayload,
        hourly: List[HourlyForecastItem],
        daily: List[DailyForecastItem],
        district_name: str,
    ) -> List[WeatherAlertItem]:
        """
        Synthesizes official meteorological alerts aligning with IMD severe-weather warning criteria.
        """
        alerts: List[WeatherAlertItem] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. IMD Live Alerts from Provider
        try:
            live_alerts = await self.alert_provider.fetch_weather_alerts(current.latitude, current.longitude, district_name)
            if live_alerts:
                alerts.extend(live_alerts)
        except Exception as e:
            logger.debug(f"Alert provider check error: {e}")

        # 2. Rule: Heavy Rainfall Alert (IMD Criteria: >64.5 mm / day or >20 mm in 6h)
        rain_sum_24h = daily[0].precipitation_sum_mm if daily else 0.0
        if rain_sum_24h >= 64.5:
            alerts.append(
                WeatherAlertItem(
                    severity="WARNING",
                    category="RAIN",
                    title=f"IMD Aligned Heavy Rainfall Warning: {district_name}",
                    title_mr=f"मुसळधार पावसाचा इशारा: {district_name}",
                    title_hi=f"भारी बारिश की चेतावनी: {district_name}",
                    description=f"Forecast indicates heavy precipitation ({rain_sum_24h:.1f} mm). Avoid chemical sprays and clear field furrows.",
                    description_mr=f"पुढील २४ तासांत मुसळधार पावसाचा ({rain_sum_24h:.1f} मिमी) इशारा. फवारणी करू नये व पाण्याचा निचरा करा.",
                    description_hi=f"24 घंटों में भारी बारिश ({rain_sum_24h:.1f} मिमी) की संभावना। छिड़काव न करें।",
                    source="PikVaidya Weather Rules (IMD Criteria)",
                    issued_at=now_iso,
                )
            )

        # 3. Rule: High Wind Squall / Thunderstorm Alert (Wind > 35 km/h or Gusts > 50 km/h)
        if current.wind_speed_kmh > 35.0 or current.wind_gusts_kmh > 50.0:
            alerts.append(
                WeatherAlertItem(
                    severity="WARNING",
                    category="WIND",
                    title=f"Severe Wind Squall Advisory: {district_name}",
                    title_mr=f"तीव्र वाऱ्याचा व वादळाचा इशारा: {district_name}",
                    title_hi=f"तेज हवा और आंधी की चेतावनी: {district_name}",
                    description=f"Strong wind gusts up to {current.wind_gusts_kmh:.1f} km/h detected. Stake tall crops (sugarcane/tomato) to prevent lodging.",
                    description_mr=f"वाऱ्याचा वेग {current.wind_gusts_kmh:.1f} किमी/तास आहे. ऊस व टोमॅटो पिकाला आधार द्या जेणेकरून पीक लोळणार नाही.",
                    description_hi=f"तेज हवा ({current.wind_gusts_kmh:.1f} किमी/घंटा) की संभावना। फसलों को सहारा दें।",
                    source="PikVaidya Weather Rules (IMD Criteria)",
                    issued_at=now_iso,
                )
            )

        # 4. Rule: Severe Heatwave Alert (Temperature > 40°C in Maharashtra plain)
        if current.temperature_c >= 40.0:
            alerts.append(
                WeatherAlertItem(
                    severity="WARNING",
                    category="HEAT",
                    title=f"Heatwave (उष्णतेची लाट) Warning: {district_name}",
                    title_mr=f"उष्णतेच्या लाटेचा इशारा: {district_name}",
                    title_hi=f"लू (हीटवेव) की चेतावनी: {district_name}",
                    description=f"Extreme ambient temperature ({current.temperature_c:.1f}°C). Avoid chemical spraying to prevent severe foliar scorching.",
                    description_mr=f"तापमान {current.temperature_c:.1f}°C वर गेले आहे. दुपारच्या वेळी औषध फवारणी केल्यास पाने करपतील.",
                    description_hi=f"अत्यधिक तापमान ({current.temperature_c:.1f}°C)। दोपहर में कीटनाशक छिड़काव से बचें।",
                    source="PikVaidya Weather Rules (IMD Criteria)",
                    issued_at=now_iso,
                )
            )

        return alerts

    def _build_fallback_weather(
        self, lat: float, lon: float, location_name: str
    ) -> Tuple[CurrentWeatherPayload, SoilTelemetry, List[HourlyForecastItem], List[DailyForecastItem]]:
        """Constructs safe regional baseline weather data when external APIs are uncontactable."""
        now_iso = datetime.now(timezone.utc).isoformat()
        current = CurrentWeatherPayload(
            temperature_c=28.5,
            apparent_temperature_c=29.2,
            relative_humidity_pct=65.0,
            surface_pressure_hpa=1013.2,
            cloud_cover_pct=20.0,
            wind_speed_kmh=8.5,
            wind_direction_deg=80.0,
            wind_gusts_kmh=12.0,
            precipitation_mm=0.0,
            precipitation_probability_6h=10.0,
            weather_condition="Regional Seasonal Baseline (Simulated)",
            weather_code=1,
            is_live=False,
            data_source="fallback",
            fetched_at=now_iso,
            latitude=lat,
            longitude=lon,
            location_name=location_name,
        )

        soil = SoilTelemetry(
            soil_temperature_c=27.0,
            soil_moisture_m3m3=0.250,
            soil_moisture_percentage=25.0,
            is_modeled=True,
            moisture_status="OPTIMAL",
            description="Typical regional baseline root-zone moisture for Maharashtra black cotton soil.",
        )

        # Synthesize 24h hourly baseline
        hourly = [
            HourlyForecastItem(
                time=f"{datetime.now().strftime('%Y-%m-%d')}T{h:02d}:00",
                temperature_c=round(25.0 + 5.0 * (1.0 if 10 <= h <= 16 else 0.0), 1),
                relative_humidity_pct=round(70.0 - 15.0 * (1.0 if 10 <= h <= 16 else 0.0), 1),
                precipitation_probability=10.0,
                precipitation_mm=0.0,
                wind_speed_kmh=8.0,
                weather_condition="Mainly clear",
                weather_code=1,
            )
            for h in range(24)
        ]

        # Synthesize 7d daily baseline
        daily = [
            DailyForecastItem(
                date=f"Day +{d}",
                weather_code=1,
                weather_condition="Mainly clear",
                temp_max_c=31.5,
                temp_min_c=21.0,
                precipitation_sum_mm=0.0,
                precipitation_probability_max=15.0,
                wind_speed_max_kmh=12.0,
            )
            for d in range(7)
        ]

        return current, soil, hourly, daily

    def record_observation(
        self,
        db: Any,
        report: ComprehensiveWeatherReport
    ) -> Any:
        """
        Persists a weather telemetry snapshot to the relational database.
        Safe against database connectivity issues (logs warning and does not crash).
        """
        try:
            from app.models.weather_history import WeatherObservation
            curr = report.current
            soil = report.soil
            obs = WeatherObservation(
                latitude=curr.latitude,
                longitude=curr.longitude,
                location_name=curr.location_name,
                temperature=curr.temperature_c,
                apparent_temperature=curr.apparent_temperature_c,
                humidity=curr.relative_humidity_pct,
                precipitation=curr.precipitation_mm,
                precipitation_probability=curr.precipitation_probability_6h,
                wind_speed=curr.wind_speed_kmh,
                wind_direction=curr.wind_direction_deg,
                wind_gusts=curr.wind_gusts_kmh,
                surface_pressure=curr.surface_pressure_hpa,
                cloud_cover=curr.cloud_cover_pct,
                soil_moisture=soil.soil_moisture_m3m3 if soil else None,
                soil_temperature=soil.soil_temperature_c if soil else None,
                weather_condition=curr.weather_condition,
                weather_code=curr.weather_code,
                is_live=curr.is_live,
                spray_suitability=report.spray_window.status,
                fungal_risk_level=report.spray_window.fungal_risk_level,
                data_source=curr.data_source,
            )
            db.add(obs)
            db.commit()
            db.refresh(obs)
            return obs
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(f"Failed to record weather observation in database: {exc}")
            return None


weather_service = WeatherService()


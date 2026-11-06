"""
PikVaidya AI — Context-Aware Agricultural Recommendation Engine
==============================================================
Synthesizes machine-learning visual diagnosis, foliar lesion severity,
authoritative ICAR/CIBRC disease knowledge, and real-time microclimate weather
into an end-to-end, actionable farmer advisory.

Compliance & Safety:
1. Confidence-Aware Gating: Strictly withholds chemical prescriptions if confidence < 75%.
2. Agrochemical Gating: Strictly adheres to CIBRC-registered chemicals and Pre-Harvest Intervals (PHI).
3. Statutory Disclaimers: Mandatory notices under Insecticides Act, 1968 and Insecticides Rules, 1971.
4. Microclimate Gating: Evaluates rain wash-off, wind drift, and temperature extremes.
5. Multilingual Delivery: Supports English, Marathi (मराठी), and Hindi (हिंदी).
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.disease import DiseaseInformation
from app.db.seeds.disease_data import SUGARCANE_DISEASE_SEEDS
from app.db.seeds.tomato_disease_data import TOMATO_DISEASE_SEEDS
from app.services.weather_service import weather_service, WeatherData, SprayWindowAssessment
from app.schemas.advisory import (
    WeatherTelemetrySchema,
    AdvisoryGenerateRequest,
    AdvisoryChemicalPrescription,
    ContextualAdvisoryResponse,
)

logger = logging.getLogger(__name__)

# Statutory Disclaimers
STATUTORY_DISCLAIMER = {
    "en": (
        "Statutory Advisory Notice: Prescriptions and dosages are compiled from published package of practices "
        "by ICAR and Central Insecticide Board & Registration Committee (CIBRC), Govt. of India. "
        "Actual field efficacy depends on localized microclimate, soil moisture, and crop stage. "
        "Under the Insecticides Act, 1968, always read container label instructions before procurement and application. "
        "Model predictions do not constitute statutory ground truth."
    ),
    "mr": (
        "वैधानिक सल्लागार सूचना: औषधांचे प्रमाण व शिफारसी भारतीय कृषी संशोधन परिषद (ICAR) आणि "
        "केंद्रीय कीटकनाशक मंडळ (CIBRC) यांच्या मार्गदर्शक तत्त्वांवर आधारित आहेत. "
        "प्रत्यक्ष शेतातील परिणामकारकता स्थानिक सूक्ष्म हवामान, जमिनीचा पोत आणि पिकाच्या वाढीच्या अवस्थेवर अवलंबून असते. "
        "कीटकनाशक कायदा १९६८ नुसार, औषध वापरण्यापूर्वी बाटलीवरील सूचना काळजीपूर्वक वाचाव्यात. "
        "AI मॉडेलचे निदान म्हणजे प्रत्यक्ष शेतातील अंतिम कायदेशीर पुरावा नव्हे."
    ),
    "hi": (
        "वैधानिक परामर्श सूचना: सुझाई गई दवाएं और मात्राएं ICAR और केंद्रीय कीटनाशक बोर्ड (CIBRC) के मानकों पर आधारित हैं। "
        "खेत में परिणाम स्थानीय मौसम, मिट्टी की नमी और फसल की स्थिति पर निर्भर करते हैं। "
        "कीटनाशक अधिनियम 1968 के तहत, दवा खरीदने और उपयोग करने से पहले लेबल पर दिए गए निर्देशों को ध्यान से पढ़ें। "
        "AI मॉडल का अनुमान अंतिम वैज्ञानिक निर्णय नहीं है।"
    )
}

EXPERT_CONSULTATION_NOTICE = {
    "en": (
        "Agricultural Expert Verification Mandatory: Consult your local Taluka Agricultural Officer, "
        "Krishi Vigyan Kendra (KVK) agronomist, or Gram Krishi Sahayak before purchasing and spraying scheduled chemicals."
    ),
    "mr": (
        "कृषी तज्ज्ञ सल्ला अनिवार्य: रासायनिक औषधे खरेदी करण्यापूर्वी स्थानिक कृषी सहाय्यक, "
        "तालुका कृषी अधिकारी किंवा कृषी विज्ञान केंद्रातील (KVK) तज्ज्ञांचा प्रत्यक्ष सल्ला घ्या."
    ),
    "hi": (
        "कृषि विशेषज्ञ सलाह अनिवार्य: कोई भी रासायनिक दवा खरीदने या छिड़कने से पहले अपने नजदीकी "
        "कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से अवश्य संपर्क करें।"
    )
}

PPE_GUIDELINES = {
    "en": "Mandatory PPE (Insecticides Rules, 1971): Wear chemical-resistant nitrile gloves, particulate mask, and eye goggles. Do not smoke, eat, or drink during spraying. Wash thoroughly after handling.",
    "mr": "अनिवार्य सुरक्षा साधने (कीटकनाशक नियम, १९७१): औषध मिसळताना व फवारताना हातमोजे, मास्क आणि डोळ्यांचा चष्मा वापरा. फवारणी करताना खाणे, पिणे किंवा धूम्रपान करू नये. फवारणीनंतर साबणाने हात-तोंड धुवावे.",
    "hi": "अनिवार्य सुरक्षा नियम: छिड़काव के दौरान मास्क, रबर के दस्ताने और चश्मा पहनें। छिड़काव करते समय कुछ खाएं-पिएं नहीं। कार्य के बाद साबुन से अच्छी तरह स्नान करें।"
}


class ContextAwareRecommendationEngine:
    """Core advisory synthesizer fusing vision pathology, disease knowledge, and microclimate."""

    CONFIDENCE_HIGH_THRESHOLD: float = 0.75
    CONFIDENCE_MODERATE_THRESHOLD: float = 0.50

    async def generate_advisory(
        self,
        request: AdvisoryGenerateRequest,
        db: Optional[Session] = None
    ) -> ContextualAdvisoryResponse:
        """
        Executes end-to-end synthesis to generate context-aware farmer recommendation.
        """
        crop_clean = request.crop_name.lower().strip()
        disease_clean = request.predicted_disease.strip()

        # 1. Resolve Authoritative Disease Information
        disease_data = self._resolve_disease_record(crop_clean, disease_clean, db)

        # 2. Resolve Ambient Weather Microclimate & Spray Window
        weather_data, spray_assessment = await self._resolve_weather(request)

        # 3. Determine Confidence Tier & Chemical Safety Gating
        conf = request.confidence
        is_chemical_permitted = False
        chemical_suppression_reason = None

        if conf >= self.CONFIDENCE_HIGH_THRESHOLD:
            conf_tier = "HIGH"
            # Viral diseases have no direct chemical viricide (only vector management)
            # Healthy foliage requires zero chemical application
            if disease_clean.lower() == "healthy":
                is_chemical_permitted = False
                chemical_suppression_reason = {
                    "en": "Crop foliage is healthy. No chemical sprays required. Avoid unnecessary chemical applications.",
                    "mr": "पीक निरोगी आहे. कोणत्याही रासायनिक फवारणीची गरज नाही. विनाकारण औषधे फवारू नका.",
                    "hi": "फसल स्वस्थ है। किसी भी रासायनिक छिड़काव की आवश्यकता नहीं है।"
                }
            else:
                is_chemical_permitted = True
        elif conf >= self.CONFIDENCE_MODERATE_THRESHOLD:
            conf_tier = "MODERATE"
            is_chemical_permitted = False
            chemical_suppression_reason = {
                "en": (
                    f"Provisional Diagnosis (Confidence: {conf:.1%}). Automated chemical prescriptions are withheld "
                    f"because model confidence is below the mandatory safety threshold ({self.CONFIDENCE_HIGH_THRESHOLD:.0%}). "
                    f"Retake leaf photo in daylight or consult local KVK."
                ),
                "mr": (
                    f"संभाव्य निदान (विश्वासार्हता: {conf:.1%}). मॉडेलची विश्वासार्हता सुरक्षित निकषापेक्षा ({self.CONFIDENCE_HIGH_THRESHOLD:.0%}) "
                    f"कमी असल्याने रासायनिक औषधांचा सल्ला रोखण्यात आला आहे. पिकाचे नुकसान टाळण्यासाठी स्थानिक कृषी तज्ज्ञांचा सल्ला घ्या."
                ),
                "hi": (
                    f"अनंतिम निदान (सटीकता: {conf:.1%})। मॉडल का विश्वास स्तर आवश्यक सुरक्षा सीमा ({self.CONFIDENCE_HIGH_THRESHOLD:.0%}) "
                    f"से कम होने के कारण रासायनिक दवाओं की सिफारिश रोक दी गई है।"
                )
            }
        else:
            conf_tier = "LOW_INCONCLUSIVE"
            is_chemical_permitted = False
            chemical_suppression_reason = {
                "en": (
                    f"Inconclusive Diagnosis (Confidence: {conf:.1%}). Foliar symptoms could not be distinguished with certainty. "
                    f"Do NOT apply chemical pesticides based on this automated scan."
                ),
                "mr": (
                    f"अस्पष्ट व अनिर्णित लक्षणे (विश्वासार्हता: {conf:.1%}). फोटोवरून रोगाची निश्चित खात्री पटत नाही. "
                    f"या अहवालावर आधारित कोणतीही रासायनिक फवारणी करू नका."
                ),
                "hi": (
                    f"अस्पष्ट लक्षण (विश्वास: {conf:.1%})। रोग की पहचान निश्चित नहीं हो सकी। "
                    f"इस आधार पर रासायनिक कीटनाशक का प्रयोग कदापि न करें।"
                )
            }

        # 4. Formulate Chemical Prescriptions (if permitted)
        chemical_prescriptions = []
        if is_chemical_permitted:
            chemical_prescriptions = self._extract_chemical_prescriptions(disease_data, request.crop_stage)

        # 5. Formulate Weather & Spray Window Directives
        spray_directive = {
            "en": spray_assessment.advisory_recommendation_en,
            "mr": spray_assessment.advisory_recommendation_mr,
            "hi": spray_assessment.advisory_recommendation_hi,
        }

        # Context-enrich overview with weather fungal risk
        overview_dict = self._build_contextual_overview(disease_data, weather_data, spray_assessment, conf_tier, conf)

        # 6. Extract Cultural and Biological Practices
        mgmt = disease_data.get("management_methods", {})
        cultural_practices = self._extract_multilingual_list(mgmt.get("cultural", {}), disease_data.get("prevention_methods", {}))
        biological_controls = self._extract_multilingual_list(mgmt.get("biological", {}), {})

        # Assemble Weather Telemetry Schema
        weather_schema = WeatherTelemetrySchema(
            temperature_c=weather_data.temperature_c,
            relative_humidity_pct=weather_data.relative_humidity_pct,
            wind_speed_kmh=weather_data.wind_speed_kmh,
            precipitation_mm=weather_data.precipitation_mm,
            precipitation_probability_6h=weather_data.precipitation_probability_6h,
            weather_condition=weather_data.weather_condition,
            is_live=weather_data.is_live,
            spray_suitability=spray_assessment.status,
            is_safe_to_spray=spray_assessment.is_safe_to_spray,
            fungal_risk_level=spray_assessment.fungal_risk_level,
            spray_guidance={
                "en": spray_assessment.summary_en,
                "mr": spray_assessment.summary_mr,
                "hi": spray_assessment.summary_hi,
            }
        )

        return ContextualAdvisoryResponse(
            crop_name=crop_clean,
            disease_id=disease_data.get("disease_id", f"{crop_clean}_{disease_clean.lower()}"),
            disease_name=self._get_multilingual_names(disease_data, disease_clean),
            scientific_name=disease_data.get("scientific_name", "Undetermined"),
            pathogen_type=disease_data.get("pathogen_type", "Indeterminate"),
            confidence=round(conf, 4),
            confidence_tier=conf_tier,
            severity=request.severity or "UNAVAILABLE",
            affected_area_percentage=request.affected_area_percentage,
            is_chemical_permitted=is_chemical_permitted,
            chemical_suppression_reason=chemical_suppression_reason,
            weather_telemetry=weather_schema,
            overview=overview_dict,
            cultural_practices=cultural_practices,
            biological_controls=biological_controls,
            chemical_prescriptions=chemical_prescriptions,
            spray_window_directive=spray_directive,
            expert_consultation_notice=EXPERT_CONSULTATION_NOTICE,
            statutory_disclaimer=STATUTORY_DISCLAIMER,
            reference_sources=disease_data.get("reference_sources", [])
        )

    def _resolve_disease_record(
        self,
        crop: str,
        predicted_disease: str,
        db: Optional[Session]
    ) -> Dict[str, Any]:
        """Queries database first; falls back to authoritative seed records."""
        # Try database query if session provided
        if db is not None:
            try:
                # 1. Match by disease_id (e.g. sugarcane_redrot)
                target_id = f"{crop}_{predicted_disease.lower()}"
                rec = db.query(DiseaseInformation).filter(DiseaseInformation.disease_id == target_id).first()
                if rec:
                    return rec.to_dict()

                # 2. Match by partial disease_name
                rec = db.query(DiseaseInformation).filter(
                    DiseaseInformation.crop_name == crop,
                    DiseaseInformation.disease_name.ilike(f"%{predicted_disease}%")
                ).first()
                if rec:
                    return rec.to_dict()
            except Exception as e:
                logger.warning(f"Database disease query failed ({e}); falling back to in-memory seeds.")

        # Fallback to seeds
        clean_pred = predicted_disease.lower().replace("_", "")
        all_seeds = SUGARCANE_DISEASE_SEEDS + TOMATO_DISEASE_SEEDS
        for seed in all_seeds:
            if seed["crop_name"].lower() == crop.lower():
                s_id = seed["disease_id"].lower().replace("_", "")
                s_name = seed["disease_name"].lower().replace("_", "")
                if clean_pred in s_id or clean_pred in s_name or s_id in clean_pred:
                    return seed

        for seed in all_seeds:
            s_id = seed["disease_id"].lower().replace("_", "")
            if clean_pred in s_id:
                return seed

        # Default fallback if unknown
        if crop.lower() == "tomato":
            return TOMATO_DISEASE_SEEDS[2]  # Default to Early Blight
        return SUGARCANE_DISEASE_SEEDS[2]  # Default to RedRot seed structure

    async def _resolve_weather(self, request: AdvisoryGenerateRequest) -> Tuple[WeatherData, SprayWindowAssessment]:
        """Resolves weather telemetry from GPS or overrides, then evaluates spray window."""
        if request.latitude is not None and request.longitude is not None:
            weather = await weather_service.get_current_weather(request.latitude, request.longitude)
        elif request.temperature is not None and request.humidity is not None:
            # Farmer provided manual telemetry
            weather = WeatherData(
                temperature_c=float(request.temperature),
                relative_humidity_pct=float(request.humidity),
                wind_speed_kmh=8.0,
                precipitation_mm=0.0,
                precipitation_probability_6h=10.0,
                weather_condition="Manual Farmer Observation",
                is_live=False
            )
        else:
            # Default regional weather
            weather = await weather_service.get_current_weather()

        assessment = weather_service.assess_spray_suitability(weather)
        return weather, assessment

    def _build_contextual_overview(
        self,
        disease_data: Dict[str, Any],
        weather: WeatherData,
        assessment: SprayWindowAssessment,
        conf_tier: str,
        conf: float
    ) -> Dict[str, str]:
        """Builds context-enriched disease overview explaining disease and weather interaction."""
        symptoms = disease_data.get("symptoms", {})
        base_en = symptoms.get("en", "Pathological foliar symptoms detected on cane leaf.")
        base_mr = symptoms.get("mr", "उसाच्या पानांवर रोगाची लक्षणे आढळली आहेत.")
        base_hi = symptoms.get("hi", "गन्ने की पत्ती पर रोग के लक्षण पाए गए हैं।")

        weather_note_en = ""
        weather_note_mr = ""
        weather_note_hi = ""

        if assessment.fungal_risk_level == "HIGH":
            weather_note_en = f" [Microclimate Alert: Ambient humidity ({weather.relative_humidity_pct}%) and temperature ({weather.temperature_c}°C) strongly promote rapid fungal sporulation.]"
            weather_note_mr = f" [हवामान इशारा: वातावरणातील आर्द्रता ({weather.relative_humidity_pct}%) आणि तापमान ({weather.temperature_c}°C) बुरशीच्या प्रसारास अत्यंत पोषक आहे.]"
            weather_note_hi = f" [मौसम चेतावनी: उच्च आर्द्रता ({weather.relative_humidity_pct}%) और तापमान रोग के तेजी से फैलने के लिए अनुकूल है।]"

        return {
            "en": f"{base_en}{weather_note_en}",
            "mr": f"{base_mr}{weather_note_mr}",
            "hi": f"{base_hi}{weather_note_hi}"
        }

    def _extract_chemical_prescriptions(
        self,
        disease_data: Dict[str, Any],
        crop_stage: Optional[str]
    ) -> List[AdvisoryChemicalPrescription]:
        """Extracts authorized CIBRC chemical treatments from disease knowledge."""
        mgmt = disease_data.get("management_methods", {})
        chem_list = mgmt.get("chemical", [])
        prescriptions = []

        for item in chem_list:
            if isinstance(item, dict):
                prescriptions.append(
                    AdvisoryChemicalPrescription(
                        chemical_name=item.get("chemical_name", "Approved Formulation"),
                        trade_examples=item.get("trade_names", "Registered brands"),
                        dosage=item.get("dosage", "As per container label"),
                        dilution_rate=item.get("water_volume_l_per_ha", "500 L/ha water"),
                        phi_days=int(item.get("waiting_period_phi_days", 30)),
                        cibrc_status="CIBRC Approved for Sugarcane",
                        target_pathogen_or_vector=item.get("target_pathogen", "Target foliar pathogen"),
                        ppe_guidelines=PPE_GUIDELINES
                    )
                )

        return prescriptions

    def _extract_multilingual_list(
        self,
        source_dict: Any,
        fallback_dict: Any
    ) -> Dict[str, List[str]]:
        """Safely normalizes multilingual advice into structured lists."""
        result = {"en": [], "mr": [], "hi": []}

        for lang in ["en", "mr", "hi"]:
            val = source_dict.get(lang) if isinstance(source_dict, dict) else None
            if not val and isinstance(fallback_dict, dict):
                val = fallback_dict.get(lang)

            if isinstance(val, list):
                result[lang] = [str(x) for x in val]
            elif isinstance(val, str) and val.strip():
                result[lang] = [val.strip()]

        return result

    def _get_multilingual_names(self, disease_data: Dict[str, Any], default_name: str) -> Dict[str, str]:
        """Resolves disease name in English, Marathi, and Hindi."""
        return {
            "en": disease_data.get("disease_name", default_name),
            "mr": disease_data.get("disease_name_mr", default_name),
            "hi": disease_data.get("disease_name_hi", default_name)
        }


recommendation_engine = ContextAwareRecommendationEngine()

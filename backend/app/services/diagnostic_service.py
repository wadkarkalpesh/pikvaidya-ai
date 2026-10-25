import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.diagnosis import Diagnosis, DiagnosisStatus, DiagnosisSeverity
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.schemas.diagnosis import PredictResponse
from app.services.storage import storage_service
from app.services.model_service import (
    model_service,
    UnsupportedCropError,
    ModelNotLoadedError,
    InferenceError,
)

logger = logging.getLogger(__name__)

# Mandatory statutory legal disclaimer under Insecticides Act, 1968
STATUTORY_DISCLAIMER_EN = (
    "Advisory Notice: Pesticide dosages and cultural treatments are based on standard ICAR/CIBRC agricultural packages. "
    "Actual field efficacy depends on localized microclimate, soil moisture, and crop stage. "
    "Always read container labels and consult your local Taluka Agricultural Officer or Krishi Vigyan Kendra (KVK) "
    "before applying scheduled chemicals. Model confidence does not establish diagnostic ground truth."
)

STATUTORY_DISCLAIMER_MR = (
    "वैधानिक सूचना: कीटकनाशक आणि बुरशीनाशक प्रमाण ICAR/CIBRC च्या मानकांवर आधारित आहे. "
    "प्रत्यक्ष शेतातील परिणामकारकता स्थानिक हवामान, जमीन आणि पिकाच्या वाढीच्या अवस्थेवर अवलंबून असते. "
    "कोणतीही रासायनिक फवारणी करण्यापूर्वी औषधाच्या वेष्टनावरील सूचना वाचाव्यात व स्थानिक कृषी सहाय्यक किंवा "
    "कृषी विज्ञान केंद्राचा (KVK) सल्ला घ्यावा. मॉडेलची विश्वासार्हता म्हणजे अंतिम खात्री नव्हे."
)

EXPERT_REVIEW_NOTICE_EN = (
    "[Agricultural Expert Verification Required: Confirm foliar symptoms with a certified Taluka Agricultural Officer "
    "or local KVK agronomist prior to chemical procurement or field spraying.]"
)

EXPERT_REVIEW_NOTICE_MR = (
    "[कृषी तज्ज्ञ पडताळणी आवश्यक: रासायनिक औषधे खरेदी करण्यापूर्वी स्थानिक कृषी सहाय्यक किंवा "
    "कृषी विज्ञान केंद्रातील (KVK) शास्त्रज्ञांकडून प्रत्यक्ष पानांची खात्री करून घेणे बंधनकारक आहे.]"
)

# Authoritative agricultural knowledge base for supported sugarcane pathologies
# Citations: ICAR-Sugarcane Breeding Institute (SBI) & CIBRC Approved Package of Practices
SUGARCANE_PATHOLOGY_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "RedRot": {
        "disease_name_en": "Red Rot (Colletotrichum falcatum)",
        "disease_name_mr": "ऊसावरील तांबडे कूज / लाल सड",
        "pathogen_type": "Fungal (Colletotrichum falcatum)",
        "authoritative_source": "ICAR-SBI Disease Management Protocols & CIBRC Fungicide Compendium",
        "symptoms_en": (
            "Red discoloration of internal vascular bundles with transverse white patches; "
            "spindle-shaped lesions along leaf midrib with dark borders."
        ),
        "symptoms_mr": (
            "पानाच्या मधल्या शिरेवर लालसर लांबट ठिपके आणि उसाच्या कांडीच्या आत लाल रंग व पांढरे आडवे पट्टे दिसणे."
        ),
        "cultural_en": (
            "Eradicate and burn affected clumps immediately. Practice 2-3 year crop rotation with non-host crops "
            "(e.g., green manure or paddy). Avoid ratooning infected fields. Use certified disease-free seedcane."
        ),
        "cultural_mr": (
            "बाधित उसाची बेटे मुळासकट उपटून जाळून टाका. २-३ वर्षे पीक फेरपालट करा (उदा. ताग/धैंचा किंवा भात). "
            "बाधित पिकाचा खोडवा ठेवू नका. निरोगी व प्रमाणित बेणे वापरा."
        ),
        "chemical_en": (
            "Treat seed setts prior to planting with Carbendazim 50% WP @ 1g/L water sett dip for 15-20 minutes. "
            "No chemical spray can cure established internal stalk infection in standing cane."
        ),
        "chemical_mr": (
            "लागवडीपूर्वी बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर पाण्यात मिसळून १५-२० मिनिटे बेणे बुडवून ठेवा. "
            "उभ्या उसातील आतील लाल सडवर कोणतीही रासायनिक फवारणी लागू पडत नाही."
        ),
    },
    "Rust": {
        "disease_name_en": "Sugarcane Common Rust (Puccinia kuehnii)",
        "disease_name_mr": "ऊसावरील तांबेरा रोग",
        "pathogen_type": "Fungal (Puccinia kuehnii)",
        "authoritative_source": "CIBRC Registered Fungicide Protocols for Sugarcane & ICAR-SBI",
        "symptoms_en": (
            "Small, elongate yellowish flecks that enlarge, turn reddish-brown, and rupture "
            "into powdery fungal pustules on lower leaf surfaces."
        ),
        "symptoms_mr": (
            "पानांवर सुरुवातीला पिवळसर आणि नंतर तांबूस-तपकिरी रंगाच्या पुटकुळ्या येणे व त्यातून भुकटी बाहेर पडणे."
        ),
        "cultural_en": (
            "Maintain optimal plant spacing to promote canopy aeration. Avoid excessive nitrogen applications. "
            "Ensure proper surface and subsurface field drainage."
        ),
        "cultural_mr": (
            "हवा खेळती राहण्यासाठी योग्य अंतर ठेवा. अवाजवी नत्र खतांचा वापर टाळा. शेतात पाणी साचणार नाही याची काळजी घ्या."
        ),
        "chemical_en": (
            "Apply foliar spray of Mancozeb 75% WP @ 2g/L water or Propiconazole 25% EC @ 1ml/L water at first onset "
            "of rust pustules. Spray volume: 500-750 L/ha using a knapsack sprayer with hollow cone nozzle."
        ),
        "chemical_mr": (
            "तांबेऱ्याची लक्षणे दिसताच मॅन्कोझेब ७५% डब्ल्यूपी २ ग्रॅम/लीटर किंवा प्रोपिकोनाझोल २५% ईसी १ मिली/लीटर फवारा. "
            "फवारणीसाठी प्रति हेक्टरी ५०० ते ७५० लिटर पाणी वापरावे."
        ),
    },
    "Mosaic": {
        "disease_name_en": "Sugarcane Mosaic Virus (SCMV)",
        "disease_name_mr": "ऊसावरील मोझॅक विषाणू रोग",
        "pathogen_type": "Viral (Potyvirus transmitted by aphids)",
        "authoritative_source": "ICAR-SBI Viral Disease Management Protocol",
        "symptoms_en": (
            "Contrasting chlorotic streaks and patches of normal dark green and pale green/yellow on the leaf blade."
        ),
        "symptoms_mr": (
            "पानांवर हिरवट-पिवळसर रंगाचे अनियमित चट्टे आणि पट्टे दिसून येणे, वाढ खुंटणे."
        ),
        "cultural_en": (
            "Rogue out and destroy infected stools early. Use certified virus-free tissue culture plantlets. "
            "Eliminate weed hosts and collateral grass hosts around field bunds."
        ),
        "cultural_mr": (
            "रोगाची लागण झालेली बेटे सुरुवातीलाच उपटून नष्ट करा. विषाणूमुक्त उतिसंवर्धित (टिश्यू कल्चर) बेणे वापरा. "
            "बांधावरील गवताळ तणे नष्ट करा."
        ),
        "chemical_en": (
            "Chemicals cannot cure viral titers in infected plants. To suppress aphid vectors (Rhopalosiphum maidis), "
            "apply Imidacloprid 17.8% SL @ 0.3ml/L water if vector populations exceed economic threshold levels."
        ),
        "chemical_mr": (
            "विषाणू रोगावर कोणतेही रासायनिक औषध नाही. रसशोषक मावा किडीच्या नियंत्रणासाठी इमिडाक्लोप्रिड १७.८% एसएल "
            "०.३ मिली/लीटर पाण्यात मिसळून फवारा."
        ),
    },
    "Yellow": {
        "disease_name_en": "Sugarcane Yellow Leaf Disease (SCYLV)",
        "disease_name_mr": "ऊसावरील पिवळे पान रोग (यलो लीफ)",
        "pathogen_type": "Viral (Luteovirus transmitted by sugarcane aphid)",
        "authoritative_source": "ICAR-SBI Sugarcane Disease Guidelines",
        "symptoms_en": (
            "Intense yellowing of the midrib on leaves 3-6, progressing outwards across the leaf blade "
            "followed by premature drying and canopy decline."
        ),
        "symptoms_mr": (
            "पानांच्या मधल्या शिरा तीव्र पिवळ्या पडणे आणि हळूहळू संपूर्ण पान पिवळे पडून टोकाकडून वाळणे."
        ),
        "cultural_en": (
            "Maintain balanced potassium and nitrogen fertigation. Avoid waterlogging and moisture stress. "
            "Plant resistant commercial varieties and use certified disease-free seedcane."
        ),
        "cultural_mr": (
            "संतुलित पोटॅश आणि नत्र खतांचा वापर करा. पाणी साचू देऊ नका आणि पाण्याचा ताण पडू देऊ नका. "
            "रोगप्रतिकारक वाणांची निवड करा."
        ),
        "chemical_en": (
            "No chemical cure exists for viral yellow leaf disease. Vector suppression (aphids) may be undertaken "
            "as per local KVK guidance during early crop establishment."
        ),
        "chemical_mr": (
            "पिवळे पान रोगावर रासायनिक उपाय नाही. पिकाच्या सुरुवातीच्या काळात मावा नियंत्रणासाठी स्थानिक केव्हीकेच्या "
            "सल्ल्याने उपाययोजना करा."
        ),
    },
    "Healthy": {
        "disease_name_en": "Healthy Crop Foliage",
        "disease_name_mr": "निरोगी पीक पाने",
        "pathogen_type": "None",
        "authoritative_source": "Standard Agronomic Good Agricultural Practices (GAP)",
        "symptoms_en": (
            "No pathological symptoms or foliar lesions detected. Foliage exhibits uniform chlorophyll pigmentation "
            "and normal vascular architecture."
        ),
        "symptoms_mr": (
            "पानांवर कोणत्याही रोगाची किंवा किडीची लक्षणे नाहीत. पाने निरोगी व हिरवीगार आहेत."
        ),
        "cultural_en": (
            "Continue standard nutritional fertigation and routine pest scouting. Maintain optimal soil moisture."
        ),
        "cultural_mr": (
            "नियमित खत व्यवस्थापन आणि पाणी नियोजन चालू ठेवा. वेळोवेळी पिकाची पाहणी करत राहा."
        ),
        "chemical_en": (
            "No chemical fungicides or insecticides required. Avoid unnecessary prophylactic sprays to preserve "
            "beneficial entomopathogenic fauna."
        ),
        "chemical_mr": (
            "कोणत्याही रासायनिक औषधांची गरज नाही. अनावश्यक फवारणी टाळून मित्रकिडींचे रक्षण करा."
        ),
    },
}


@dataclass
class DiagnosticInferenceResult:
    disease_name_en: str
    disease_name_mr: str
    pathogen_type: str
    confidence: float
    severity: DiagnosisSeverity
    affected_area_percentage: Optional[float]
    symptoms_en: str
    symptoms_mr: str
    recommendations_en: str
    recommendations_mr: str
    advisory_status: str
    heatmap_path: Optional[str] = None


class DiagnosticService:
    """Unified, confidence-aware diagnostic service for crop pathology.
    
    Orchestrates:
    1. Multi-tier image file integrity & raster validation.
    2. Crop support checking (only genuine trained models are executed).
    3. PyTorch model inference & Grad-CAM visual lesion explainability.
    4. Conservative confidence threshold gating to suppress risky chemical prescriptions.
    5. Severity estimation safety policy (explicitly reports unvalidated/unavailable).
    6. Authoritative agronomic advisory generation with ICAR/CIBRC citations and statutory disclaimers.
    7. Multi-tenant ownership verification and database persistence.
    """

    SUPPORTED_CROPS: Dict[str, str] = {
        "sugarcane": "models/sugarcane/efficientnet_b0/best_model.pth"
    }

    def check_crop_support(self, crop_name: str) -> str:
        """Verifies that a genuine trained model is configured for the crop.
        
        Raises UnsupportedCropError with structured explanation if unavailable.
        """
        normalized = crop_name.strip().lower()
        # Direct or substring check (e.g., "Sugarcane", "co 86032 sugarcane")
        for supported_key in self.SUPPORTED_CROPS:
            if supported_key in normalized:
                return supported_key

        supported_list = ", ".join(self.SUPPORTED_CROPS.keys())
        raise UnsupportedCropError(
            f"AI diagnosis is currently unavailable for crop '{crop_name}'. "
            f"Model inference is currently only supported for: {supported_list}. "
            f"Model currently only serves sugarcane crop pathology. Received: '{crop_name}'."
        )

    def evaluate_safety_and_advisory(
        self,
        crop: str,
        predicted_class: str,
        confidence: float,
        class_scores: Dict[str, float],
        heatmap_path: Optional[str] = None,
    ) -> DiagnosticInferenceResult:
        """Applies confidence-aware safety evaluation and conservative agronomic gating.
        
        Threshold rules:
        - High Confidence (>= 0.75): Verified diagnosis. CIBRC/ICAR advice with expert review notice.
        - Moderate Confidence (0.50 <= conf < 0.75): Low confidence warning. Chemical prescriptions suppressed.
        - Low Confidence (< 0.50): Inconclusive/uncertain diagnosis. All chemical prescriptions suppressed.
        
        Severity policy:
        - Healthy: HEALTHY (0.0% area).
        - Diseased: UNAVAILABLE (None area), as no image segmentation model is deployed.
        """
        conf_high = settings.CONFIDENCE_THRESHOLD_HIGH
        conf_mod = settings.CONFIDENCE_THRESHOLD_MODERATE

        knowledge = SUGARCANE_PATHOLOGY_KNOWLEDGE.get(
            predicted_class, SUGARCANE_PATHOLOGY_KNOWLEDGE["RedRot"]
        )

        # -------------------------------------------------------------
        # TIER 1: HIGH CONFIDENCE (>= 0.75)
        # -------------------------------------------------------------
        if confidence >= conf_high:
            if predicted_class == "Healthy":
                return DiagnosticInferenceResult(
                    disease_name_en=knowledge["disease_name_en"],
                    disease_name_mr=knowledge["disease_name_mr"],
                    pathogen_type=knowledge["pathogen_type"],
                    confidence=round(confidence, 4),
                    severity=DiagnosisSeverity.HEALTHY,
                    affected_area_percentage=0.0,
                    symptoms_en=knowledge["symptoms_en"],
                    symptoms_mr=knowledge["symptoms_mr"],
                    recommendations_en=(
                        f"{knowledge['cultural_en']} {knowledge['chemical_en']}"
                    ),
                    recommendations_mr=(
                        f"{knowledge['cultural_mr']} {knowledge['chemical_mr']}"
                    ),
                    advisory_status="HEALTHY",
                    heatmap_path=heatmap_path,
                )

            # Diseased foliage with high confidence
            rec_en = (
                f"{EXPERT_REVIEW_NOTICE_EN}\n\n"
                f"• Cultural Management: {knowledge['cultural_en']}\n"
                f"• Chemical Measures ({knowledge['authoritative_source']}): {knowledge['chemical_en']}\n\n"
                f"{STATUTORY_DISCLAIMER_EN}"
            )
            rec_mr = (
                f"{EXPERT_REVIEW_NOTICE_MR}\n\n"
                f"• मशागतीय व प्रतिबंधात्मक उपाय: {knowledge['cultural_mr']}\n"
                f"• रासायनिक उपाययोजना ({knowledge['authoritative_source']}): {knowledge['chemical_mr']}\n\n"
                f"{STATUTORY_DISCLAIMER_MR}"
            )

            return DiagnosticInferenceResult(
                disease_name_en=knowledge["disease_name_en"],
                disease_name_mr=knowledge["disease_name_mr"],
                pathogen_type=knowledge["pathogen_type"],
                confidence=round(confidence, 4),
                # Explicitly unvalidated severity: no pixel-level lesion segmentation model exists
                severity=DiagnosisSeverity.UNAVAILABLE,
                affected_area_percentage=None,
                symptoms_en=knowledge["symptoms_en"],
                symptoms_mr=knowledge["symptoms_mr"],
                recommendations_en=rec_en,
                recommendations_mr=rec_mr,
                advisory_status="HIGH_CONFIDENCE",
                heatmap_path=heatmap_path,
            )

        # -------------------------------------------------------------
        # TIER 2: MODERATE CONFIDENCE (0.50 <= conf < 0.75) — WARNING
        # -------------------------------------------------------------
        elif confidence >= conf_mod:
            symptoms_en = (
                f"Possible foliar indication: {knowledge['disease_name_en']} "
                f"(Provisional classification confidence: {confidence:.1%}). "
                f"Diagnostic symptoms are ambiguous and require physical confirmation."
            )
            symptoms_mr = (
                f"संभाव्य लक्षण: {knowledge['disease_name_mr']} "
                f"(तात्पुरती मॉडेल विश्वासार्हता: {confidence:.1%}). "
                f"पानावरील लक्षणे स्पष्ट नसून प्रत्यक्ष पाहणी आवश्यक आहे."
            )

            # SUPPRESS ALL CHEMICAL PRESCRIPTIONS
            rec_en = (
                f"CHEMICAL PRESCRIPTION SUPPRESSED DUE TO DIAGNOSTIC UNCERTAINTY "
                f"(Model confidence {confidence:.1%} is below the safe threshold of {conf_high:.0%}).\n\n"
                f"Automated chemical recommendations are withheld to prevent misdiagnosis, crop injury, and unnecessary expense.\n\n"
                f"Recommended Next Steps:\n"
                f"1. Cultural Inspection: {knowledge['cultural_en']}\n"
                f"2. Retake Photograph: Capture a well-lit, sharp close-up photo of symptomatic leaves in natural indirect daylight.\n"
                f"3. Expert Consultation: Take a fresh leaf sample to your nearest Krishi Vigyan Kendra (KVK) or consult a certified agronomist.\n\n"
                f"{STATUTORY_DISCLAIMER_EN}"
            )
            rec_mr = (
                f"निदानाच्या अनिश्चिततेमुळे रासायनिक औषध शिफारस तात्पुरती स्थगित करण्यात आली आहे "
                f"(मॉडेल विश्वासार्हता {confidence:.1%} ही सुरक्षित मर्यादेपेक्षा कमी आहे ({conf_high:.0%})).\n\n"
                f"चुकीचे निदान, पिकाचे नुकसान आणि विनाकारण आर्थिक भुर्दंड टाळण्यासाठी औषधांचा सल्ला रोखण्यात आला आहे.\n\n"
                f"पुढील उपाययोजना:\n"
                f"१. मशागतीय दक्षता: {knowledge['cultural_mr']}\n"
                f"२. नवीन फोटो घ्या: चांगल्या नैसर्गिक प्रकाशात, पानांचा स्पष्ट व केंद्रित (in-focus) फोटो पुन्हा अपलोड करा.\n"
                f"३. तज्ज्ञ सल्ला: जवळच्या कृषी विज्ञान केंद्रातील (KVK) शास्त्रज्ञ किंवा तालुका कृषी अधिकाऱ्यांचा प्रत्यक्ष सल्ला घ्या.\n\n"
                f"{STATUTORY_DISCLAIMER_MR}"
            )

            return DiagnosticInferenceResult(
                disease_name_en=f"Provisional: {knowledge['disease_name_en']}",
                disease_name_mr=f"संभाव्य: {knowledge['disease_name_mr']}",
                pathogen_type=knowledge["pathogen_type"],
                confidence=round(confidence, 4),
                severity=DiagnosisSeverity.UNAVAILABLE,
                affected_area_percentage=None,
                symptoms_en=symptoms_en,
                symptoms_mr=symptoms_mr,
                recommendations_en=rec_en,
                recommendations_mr=rec_mr,
                advisory_status="LOW_CONFIDENCE_WARNING",
                heatmap_path=heatmap_path,
            )

        # -------------------------------------------------------------
        # TIER 3: LOW CONFIDENCE (< 0.50) — UNCERTAIN / INCONCLUSIVE
        # -------------------------------------------------------------
        else:
            symptoms_en = (
                f"Image analysis is inconclusive (Highest class probability: {confidence:.1%}). "
                f"The model cannot reliably distinguish whether the symptoms stem from biotic infection, "
                f"nutritional deficiency, insect feeding, or environmental stress."
            )
            symptoms_mr = (
                f"छायाचित्राचे विश्लेषण अनिर्णित आहे (कमाल विश्वासार्हता: {confidence:.1%}). "
                f"पानावरील लक्षणे रोग, अन्नद्रव्यांची कमतरता, कीड किंवा हवामानातील ताण यातील फरक स्पष्ट करू शकले नाहीत."
            )

            # COMPLETE SUPPRESSION
            rec_en = (
                f"DIAGNOSIS UNCERTAIN — CHEMICAL PRESCRIPTION WITHHELD.\n\n"
                f"The image provided does not show distinct pathological features with sufficient probabilistic confidence.\n"
                f"Do NOT apply chemical pesticides based on this automated scan.\n\n"
                f"Recommended Actions:\n"
                f"1. Retake leaf photograph: Ensure leaves are clean, camera is focused on the lesion margins, and lighting is uniform.\n"
                f"2. Physical Diagnostics: Visit the nearest Krishi Vigyan Kendra (KVK) or Taluka Agriculture Office for leaf scraping/microscopic inspection.\n\n"
                f"{STATUTORY_DISCLAIMER_EN}"
            )
            rec_mr = (
                f"निदान अत्यंत अनिश्चित — रासायनिक औषध सल्ला रोखण्यात आला आहे.\n\n"
                f"अपलोड केलेल्या फोटोवरून रोगाची निश्चित खात्री पटत नाही. या अहवालाच्या आधारे कोणतीही रासायनिक औषध फवारणी करू नका.\n\n"
                f"पुढील कृती:\n"
                f"१. नवीन फोटो काढा: कॅमेरा पानावरील ठिपक्यांवर केंद्रित करून चांगल्या प्रकाशात नवीन फोटो घ्या.\n"
                f"२. प्रत्यक्ष तपासणी: पाण्याचा नमुना घेऊन जवळच्या कृषी विज्ञान केंद्रात (KVK) जाऊन प्रत्यक्ष खात्री करा.\n\n"
                f"{STATUTORY_DISCLAIMER_MR}"
            )

            return DiagnosticInferenceResult(
                disease_name_en="Uncertain Foliar Symptoms",
                disease_name_mr="अस्पष्ट पानांवरील लक्षणे",
                pathogen_type="Indeterminate",
                confidence=round(confidence, 4),
                severity=DiagnosisSeverity.UNAVAILABLE,
                affected_area_percentage=None,
                symptoms_en=symptoms_en,
                symptoms_mr=symptoms_mr,
                recommendations_en=rec_en,
                recommendations_mr=rec_mr,
                advisory_status="UNCERTAIN_PREDICTION",
                heatmap_path=heatmap_path,
            )

    async def run_standalone_prediction(
        self,
        file: UploadFile,
        crop: str = "sugarcane",
        generate_gradcam: bool = False,
        save_heatmap: bool = True,
    ) -> PredictResponse:
        """Executes unauthenticated direct model inference with Grad-CAM and safety evaluation.
        
        Does NOT touch the database, does not persist farmer records.
        """
        full_content, ext, filename = await storage_service.validate_upload_content(file)
        normalized_crop = self.check_crop_support(crop)

        # Run inference through PyTorch singleton
        pred = model_service.predict(
            image=full_content,
            crop=normalized_crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=save_heatmap,
        )

        safety_eval = self.evaluate_safety_and_advisory(
            crop=normalized_crop,
            predicted_class=pred["predicted_class"],
            confidence=pred["confidence"],
            class_scores=pred["class_scores"],
            heatmap_path=pred.get("heatmap_path"),
        )

        return PredictResponse(
            crop=normalized_crop,
            predicted_class=pred["predicted_class"],
            confidence=pred["confidence"],
            class_scores=pred["class_scores"],
            model_version=pred["model_version"],
            explanation_status=pred["explanation_status"],
            heatmap_path=pred.get("heatmap_path"),
            advisory_status=safety_eval.advisory_status,
            details={
                "safety_evaluation": safety_eval.advisory_status,
                "disease_name_en": safety_eval.disease_name_en,
                "disease_name_mr": safety_eval.disease_name_mr,
                "pathogen_type": safety_eval.pathogen_type,
                "severity": safety_eval.severity.value,
                "affected_area_percentage": safety_eval.affected_area_percentage,
                "recommendations_en": safety_eval.recommendations_en,
                "recommendations_mr": safety_eval.recommendations_mr,
                "statutory_disclaimer": STATUTORY_DISCLAIMER_EN,
            },
        )

    async def run_authenticated_crop_diagnosis(
        self,
        crop_id: int,
        user_id: int,
        file: UploadFile,
        notes: Optional[str] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        soil_moisture: Optional[float] = None,
        generate_gradcam: bool = False,
        db: Session = None,
    ) -> Diagnosis:
        """Executes full authenticated workflow:
        1. Checks crop cycle ownership.
        2. Validates image integrity and stores media file.
        3. Verifies crop model availability (rejects unsupported crops).
        4. Runs genuine PyTorch inference and optional Grad-CAM explainability.
        5. Applies confidence-aware safety gating.
        6. Persists Diagnosis record to database.
        """
        # 1. Verify crop ownership
        crop = (
            db.query(CropCycle)
            .join(Farm, CropCycle.farm_id == Farm.id)
            .filter(CropCycle.id == crop_id)
            .first()
        )
        if not crop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crop cycle not found.",
            )
        if crop.farm.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this crop cycle.",
            )

        # 2. Check crop support BEFORE saving image or executing inference
        normalized_crop = self.check_crop_support(crop.crop)

        # 3. Validate and store media file
        storage_path, original_filename, image_hash, full_content = (
            await storage_service.save_diagnostic_image(file)
        )

        # 4. Run model inference & safety evaluation
        try:
            pred = model_service.predict(
                image=full_content,
                crop=normalized_crop,
                generate_gradcam=generate_gradcam,
                save_heatmap=True,
            )

            safety_eval = self.evaluate_safety_and_advisory(
                crop=normalized_crop,
                predicted_class=pred["predicted_class"],
                confidence=pred["confidence"],
                class_scores=pred["class_scores"],
                heatmap_path=pred.get("heatmap_path"),
            )

            diagnosis = Diagnosis(
                user_id=user_id,
                crop_cycle_id=crop.id,
                image_path=storage_path,
                image_filename=original_filename,
                image_hash=image_hash,
                heatmap_path=pred.get("heatmap_path"),
                crop_name=crop.crop,
                disease_name_en=safety_eval.disease_name_en,
                disease_name_mr=safety_eval.disease_name_mr,
                pathogen_type=safety_eval.pathogen_type,
                confidence=safety_eval.confidence,
                severity=safety_eval.severity,
                affected_area_percentage=safety_eval.affected_area_percentage,
                advisory_status=safety_eval.advisory_status,
                symptoms_en=safety_eval.symptoms_en,
                symptoms_mr=safety_eval.symptoms_mr,
                recommendations_en=safety_eval.recommendations_en,
                recommendations_mr=safety_eval.recommendations_mr,
                temperature=temperature,
                humidity=humidity,
                soil_moisture=soil_moisture,
                status=DiagnosisStatus.COMPLETED,
                notes=notes,
            )
        except Exception as e:
            logger.error(f"Inference failure during authenticated diagnosis: {e}", exc_info=True)
            # Record failed diagnostic attempt cleanly in database
            diagnosis = Diagnosis(
                user_id=user_id,
                crop_cycle_id=crop.id,
                image_path=storage_path,
                image_filename=original_filename,
                image_hash=image_hash,
                crop_name=crop.crop,
                status=DiagnosisStatus.FAILED,
                notes=f"Diagnostic failure: {str(e)}",
            )

        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)
        return diagnosis


diagnostic_service = DiagnosticService()

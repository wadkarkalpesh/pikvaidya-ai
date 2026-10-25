"""Decoupled AI service adapter.

Maintains backward compatibility while delegating core pathological inference
and safety gating to the unified DiagnosticService.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import settings
from app.models.diagnosis import DiagnosisSeverity
from app.services.model_service import model_service, UnsupportedCropError
from app.services.diagnostic_service import (
    diagnostic_service,
    DiagnosticInferenceResult,
    SUGARCANE_PATHOLOGY_KNOWLEDGE,
)

logger = logging.getLogger(__name__)

# Educational Agronomic Knowledge Base
# PRESERVED FOR DOMAIN REFERENCE ONLY — Must NEVER be returned as automated AI predictions
# for unconfigured crops without trained vision models.
EDUCATIONAL_CROP_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "cotton": {
        "disease_name_en": "Cotton Leaf Curl Virus (CLCuV)",
        "disease_name_mr": "कापूस पांढरी माशी / पर्णकुंचन विषाणू",
        "pathogen_type": "Viral (Transmitted by Whitefly)",
        "symptoms_en": "Upward or downward curling of leaf margins, thickened veins, and enations on undersides of leaves.",
        "symptoms_mr": "पानांच्या कडा वर किंवा खाली वळणे, शिरा जाड होणे आणि पानांच्या मागच्या बाजूला गाठी तयार होणे.",
        "recommendations_en": "Control whitefly vectors using Neem oil (1500 ppm) @ 5ml/L or systemic insecticide like Diafenthiuron. Remove severely infected plants.",
        "recommendations_mr": "पांढऱ्या माशीच्या नियंत्रणासाठी निंबोळी अर्क (१५०० पीपीएम) ५ मिली/लीटर किंवा डायफेंथियुरॉनची फवारणी करा. बाधित रोपे उपटून नष्ट करा.",
    },
    "tomato": {
        "disease_name_en": "Early Blight (Alternaria solani)",
        "disease_name_mr": "टोमॅटोवरील लवकर येणारा करपा (अल्टरनेरिया)",
        "pathogen_type": "Fungal",
        "symptoms_en": "Concentric dark brown rings resembling target boards on older leaves, surrounded by yellow chlorotic halo.",
        "symptoms_mr": "जुन्या पानांवर गोलाकार तपकिरी ठिपके (टार्गेट बोर्ड सारखे) आणि ठिपक्यांभोवती पिवळसर वलय दिसणे.",
        "recommendations_en": "Apply Mancozeb 75% WP @ 2.5g/L or Azoxystrobin 23% SC @ 1ml/L. Avoid overhead irrigation and ensure good aeration.",
        "recommendations_mr": "मँकोझेब ७५% डब्ल्यूपी २.५ ग्रॅम/लीटर किंवा अझोक्सिस्ट्रॉबीन २३% एससी १ मिली/लीटर फवारणी करा. तुषार सिंचन टाळा.",
    },
    "soybean": {
        "disease_name_en": "Soybean Rust (Phakopsora pachyrhizi)",
        "disease_name_mr": "सोयाबीन तांबेरा (रस्ट)",
        "pathogen_type": "Fungal",
        "symptoms_en": "Small, water-soaked lesions that turn into reddish-brown to dark brown pustules primarily on lower leaf surfaces.",
        "symptoms_mr": "पानांच्या खालच्या बाजूला बारीक तांबूस-तपकिरी रंगाचे पुटकुळ्यांसारखे ठिपके दिसणे, पाने पिवळी पडून गळणे.",
        "recommendations_en": "Spray Hexaconazole 5% SC @ 2ml/L or Tebuconazole 25.9% EC @ 1.5ml/L at the first appearance of pustules.",
        "recommendations_mr": "रोगाची लक्षणे दिसताच हेक्झाकोनॅझोल ५% एससी २ मिली/लीटर किंवा टेबुकोनॅझोल २५.९% ईसी १.५ मिली/लीटर पाण्यात मिसळून फवारा.",
    },
    "onion": {
        "disease_name_en": "Purple Blotch (Alternaria porri)",
        "disease_name_mr": "कांद्यावरील जांभळा करपा",
        "pathogen_type": "Fungal",
        "symptoms_en": "Small sunken water-soaked lesions with purple centers that enlarge rapidly on foliage and seed stalks.",
        "symptoms_mr": "पानांवर सुरुवातीला पांढुरके आणि नंतर मध्यभागी जांभळे झालेले लांबट ठिपके पडणे.",
        "recommendations_en": "Spray Difenoconazole 25% EC @ 1ml/L or Chlorothalonil 75% WP @ 2g/L along with a sticker/spreader.",
        "recommendations_mr": "डायफेनोकोनॅझोल २५% ईसी १ मिली/लीटर किंवा क्लोरोथॅलोनिल ७५% डब्ल्यूपी २ ग्रॅम/लीटर सोबत स्टिकर (डिंक) मिसळून फवारणी करा.",
    },
}

# Alias for backward compatibility if imported elsewhere
CROP_DIAGNOSTIC_KNOWLEDGE = EDUCATIONAL_CROP_KNOWLEDGE


class AIServiceAdapter:
    """Decoupled AI service adapter.
    
    Provides genuine crop pathology inference with conservative confidence safety rules.
    Refuses to fabricate predictions for unsupported crops.
    """

    async def analyze_crop_image(
        self,
        image_path: str,
        crop_name: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        soil_moisture: Optional[float] = None,
    ) -> DiagnosticInferenceResult:
        """Executes genuine model inference on the provided image path.
        
        Raises:
            UnsupportedCropError: If crop has no trained model configured.
            FileNotFoundError: If stored image file is not found.
            InferenceError: If model forward pass fails.
        """
        # 1. Enforce strict crop support boundary
        normalized_crop = diagnostic_service.check_crop_support(crop_name)

        # 2. Locate image file
        full_path = Path(image_path)
        if not full_path.is_absolute():
            full_path = Path(settings.UPLOAD_DIR) / image_path

        if not full_path.exists():
            raise FileNotFoundError(f"Diagnostic image file not found at: {full_path}")

        img_bytes = full_path.read_bytes()

        # 3. Execute genuine model inference
        pred = model_service.predict(
            image=img_bytes,
            crop=normalized_crop,
            generate_gradcam=False,
            save_heatmap=False,
        )

        # 4. Evaluate safety and advisory through the unified safety engine
        safety_eval = diagnostic_service.evaluate_safety_and_advisory(
            crop=normalized_crop,
            predicted_class=pred["predicted_class"],
            confidence=pred["confidence"],
            class_scores=pred["class_scores"],
            heatmap_path=None,
        )

        return safety_eval


ai_service = AIServiceAdapter()

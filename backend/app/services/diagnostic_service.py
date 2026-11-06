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
from app.schemas.advisory import AdvisoryGenerateRequest
from app.services.storage import storage_service
from app.services.segmentation_service import segmentation_service
from app.services.weather_service import weather_service
from app.services.recommendation_engine import recommendation_engine
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

PPE_NOTICE_EN = (
    "Mandatory PPE Notice: Wear chemical-resistant nitrile gloves, particulate face mask, and eye protection "
    "during pesticide handling and spraying under Insecticides Rules, 1971."
)

PPE_NOTICE_MR = (
    "अनिवार्य सुरक्षा सूचना: कीटकनाशक नियम १९७१ नुसार औषध मिसळताना व फवारताना रासायनिक हातमोजे, "
    "मास्क आणि संरक्षणात्मक चष्मा वापरणे बंधनकारक आहे."
)

# Authoritative agricultural knowledge base for supported sugarcane pathologies
# Citations: ICAR-Sugarcane Breeding Institute (SBI) & CIBRC Approved Package of Practices
SUGARCANE_PATHOLOGY_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "RedRot": {
        "disease_name_en": "Red Rot (Colletotrichum falcatum)",
        "disease_name_mr": "ऊसावरील तांबडे कूज / लाल सड",
        "pathogen_type": "Fungal (Colletotrichum falcatum)",
        "authoritative_source": "ICAR-SBI Disease Management Protocols & CIBRC Fungicide Compendium",
        "phi_days": 30,
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
            "No chemical spray can cure established internal stalk infection in standing cane. "
            "Pre-Harvest Interval (PHI): 30 days before harvest. "
            f"{PPE_NOTICE_EN}"
        ),
        "chemical_mr": (
            "लागवडीपूर्वी बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर पाण्यात मिसळून १५-२० मिनिटे बेणे बुडवून ठेवा. "
            "उभ्या उसातील आतील लाल सडवर कोणतीही रासायनिक फवारणी लागू पडत नाही. "
            "काढणीपूर्वीचा कालावधी (PHI): किमान ३० दिवस. "
            f"{PPE_NOTICE_MR}"
        ),
    },
    "Rust": {
        "disease_name_en": "Sugarcane Common Rust (Puccinia kuehnii)",
        "disease_name_mr": "ऊसावरील तांबेरा रोग",
        "pathogen_type": "Fungal (Puccinia kuehnii)",
        "authoritative_source": "CIBRC Registered Fungicide Protocols for Sugarcane & ICAR-SBI",
        "phi_days": 30,
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
            "of rust pustules. Spray volume: 500-750 L/ha using a knapsack sprayer with hollow cone nozzle. "
            "Pre-Harvest Interval (PHI): 30 days. "
            f"{PPE_NOTICE_EN}"
        ),
        "chemical_mr": (
            "तांबेऱ्याची लक्षणे दिसताच मॅन्कोझेब ७५% डब्ल्यूपी २ ग्रॅम/लीटर किंवा प्रोपिकोनाझोल २५% ईसी १ मिली/लीटर फवारा. "
            "फवारणीसाठी प्रति हेक्टरी ५०० ते ७५० लिटर पाणी वापरावे. काढणीपूर्वीचा कालावधी (PHI): ३० दिवस. "
            f"{PPE_NOTICE_MR}"
        ),
    },
    "Mosaic": {
        "disease_name_en": "Sugarcane Mosaic Virus (SCMV)",
        "disease_name_mr": "ऊसावरील मोझॅक विषाणू रोग",
        "pathogen_type": "Viral (Potyvirus transmitted by aphids)",
        "authoritative_source": "ICAR-SBI Viral Disease Management Protocol",
        "phi_days": 21,
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
            "apply Imidacloprid 17.8% SL @ 0.3ml/L water if vector populations exceed economic threshold levels. "
            "Pre-Harvest Interval (PHI): 21 days. "
            f"{PPE_NOTICE_EN}"
        ),
        "chemical_mr": (
            "विषाणू रोगावर कोणतेही रासायनिक औषध नाही. रसशोषक मावा किडीच्या नियंत्रणासाठी इमिडाक्लोप्रिड १७.८% एसएल "
            "०.३ मिली/लीटर पाण्यात मिसळून फवारा. काढणीपूर्वीचा कालावधी (PHI): २१ दिवस. "
            f"{PPE_NOTICE_MR}"
        ),
    },
    "Yellow": {
        "disease_name_en": "Sugarcane Yellow Leaf Disease (SCYLV)",
        "disease_name_mr": "ऊसावरील पिवळे पान रोग (यलो लीफ)",
        "pathogen_type": "Viral (Luteovirus transmitted by aphids)",
        "authoritative_source": "ICAR-SBI Yellow Leaf Management Advisory",
        "phi_days": 21,
        "symptoms_en": (
            "Prominent yellowing of the leaf midrib on lower surface, spreading outward to laminar tissue; "
            "shortening of terminal internodes and bunchy top appearance."
        ),
        "symptoms_mr": (
            "पानाच्या मधल्या शिरेचा खालचा भाग ठळक पिवळा पडणे आणि हा पिवळेपणा संपूर्ण पानावर पसरणे; शेंडा आकसणे."
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
        "phi_days": None,
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

TOMATO_PATHOLOGY_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "Healthy": {
        "disease_name_en": "Healthy Tomato Foliage",
        "disease_name_mr": "निरोगी टोमॅटो पीक",
        "pathogen_type": "None",
        "authoritative_source": "ICAR-IIHR Tomato Cultivation Guide & CIBRC",
        "phi_days": None,
        "symptoms_en": "Foliage exhibits vigorous deep-green color, smooth leaflets, with no lesions or chlorosis.",
        "symptoms_mr": "टोमॅटोची पाने गर्द हिरवी, तजेलदार असून पानांवर कोणताही करपा किंवा चट्टे नाहीत.",
        "cultural_en": "Continue routine fertigation, pruning of lower senescent leaves, and trellising.",
        "cultural_mr": "नियमित खत व्यवस्थापन आणि जमिनीला टेकणाऱ्या खालच्या जुन्या पानांची छाटणी करा.",
        "chemical_en": "No chemical fungicides or insecticides required. Protect beneficial predators.",
        "chemical_mr": "कोणत्याही रासायनिक औषधांची गरज नाही. मित्रकिडींचे रक्षण करा.",
    },
    "Bacterial_spot": {
        "disease_name_en": "Tomato Bacterial Spot (Xanthomonas campestris)",
        "disease_name_mr": "टोमॅटोवरील जिवाणूजन्य ठिपके (बॅक्टेरियल स्पॉट)",
        "pathogen_type": "Bacterial (Xanthomonas campestris pv. vesicatoria)",
        "authoritative_source": "ICAR-IIHR Bengaluru & CIBRC Approved Pesticides",
        "phi_days": 15,
        "symptoms_en": "Small, dark brown to black water-soaked lesions with yellow halos on leaves.",
        "symptoms_mr": "पानांवर लहान, काळे-तपकिरी रंगाचे तेलकट डाग पडतात व डागांभोवती पिवळी कडा दिसते.",
        "cultural_en": "Avoid sprinkler irrigation. Sanitize pruning shears. Rogue out blighted plants.",
        "cultural_mr": "तुषार सिंचन टाळा, फक्त ठिबक सिंचन वापरा. छाटणीची अवजारे स्वच्छ ठेवा.",
        "chemical_en": f"Spray Copper Oxychloride 50% WP @ 2.5 g/L + Streptocycline @ 0.1 g/L. PHI: 15 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"कॉपर ऑक्सिक्लोराईड २.५ ग्रॅम/लिटर + स्ट्रेप्टोसायक्लीन ०.१ ग्रॅम/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Early_blight": {
        "disease_name_en": "Tomato Early Blight (Alternaria solani)",
        "disease_name_mr": "टोमॅटोवरील लवकर येणारा करपा (अल्टरनेरिया)",
        "pathogen_type": "Fungal (Alternaria solani)",
        "authoritative_source": "CIBRC Registered Fungicides & ICAR-IIHR",
        "phi_days": 5,
        "symptoms_en": "Concentric ring 'target-board' brown lesions primarily on lower foliage.",
        "symptoms_mr": "पानांवर गोलाकार किंवा लंबगोलाकार एकाआड एक वलये (टार्गेट बोर्डसारखे चट्टे) दिसतात.",
        "cultural_en": "Stake vines securely, prune bottom foliage 30cm above soil, practice crop rotation.",
        "cultural_mr": "झाडांना आधार द्या, खालची पाने वेळोवेळी छाटून टाका, पीक फेरपालट करा.",
        "chemical_en": f"Foliar spray of Azoxystrobin 18.2% + Difenoconazole 11.4% SC @ 1.0 ml/L or Mancozeb 75% WP @ 2.5 g/L. PHI: 5-15 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"अॅझॉक्सीस्ट्रॉबिन + डायफेनोकोनाझोल १.० मिली/लिटर किंवा मॅन्कोझेब २.५ ग्रॅम/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Late_blight": {
        "disease_name_en": "Tomato Late Blight (Phytophthora infestans)",
        "disease_name_mr": "टोमॅटोवरील उशिरा येणारा करपा (लेट ब्लाइट)",
        "pathogen_type": "Oomycete (Phytophthora infestans)",
        "authoritative_source": "ICAR-IIHR Late Blight Advisory & CIBRC",
        "phi_days": 10,
        "symptoms_en": "Rapidly expanding water-soaked dark lesions with white mold on leaf undersides in cool humid weather.",
        "symptoms_mr": "पानांवर वेगाने पसरणारे काळसर पाणथळ डाग, पानाच्या मागील बाजूस पांढुरकी बुरशी दिसते.",
        "cultural_en": "Destroy blighted plants immediately. Space beds 1.2m apart. Avoid evening irrigation.",
        "cultural_mr": "करपलेली झाडे तत्काळ उपटून जमिनीत पुरा. झाडांमध्ये योग्य अंतर ठेवा.",
        "chemical_en": f"Spray Dimethomorph 50% WP @ 1g/L + Mancozeb 75% WP @ 2g/L or Cymoxanil 8% + Mancozeb 64% WP @ 2g/L. PHI: 10 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"डायमेथोमॉर्फ १ ग्रॅम + मॅन्कोझेब २ ग्रॅम/लिटर किंवा सायमोक्सानिल + मॅन्कोझेब २ ग्रॅम/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Leaf_Mold": {
        "disease_name_en": "Tomato Leaf Mold (Passalora fulva)",
        "disease_name_mr": "टोमॅटोवरील पानांवरील मखमली बुरशी",
        "pathogen_type": "Fungal (Passalora fulva)",
        "authoritative_source": "ICAR-IIHR Protected Cultivation Manual",
        "phi_days": 7,
        "symptoms_en": "Pale yellow patches on upper leaf surface with olive-brown velvety mold on undersides.",
        "symptoms_mr": "पानांच्या वर पिवळसर डाग आणि खाली मखमली ऑलिव्ह-तपकिरी रंगाची बुरशी दिसते.",
        "cultural_en": "Increase greenhouse ventilation, reduce humidity, prune lower dense suckers.",
        "cultural_mr": "पॉलीहाऊसचे पडदे उघडून हवा खेळती ठेवा, अतिरिक्त फुटवे छाटा.",
        "chemical_en": f"Apply Chlorothalonil 75% WP @ 2.0 g/L or Difenoconazole 25% EC @ 0.5 ml/L. PHI: 7 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"क्लोरोथॅलोनिल २.० ग्रॅम/लिटर किंवा डायफेनोकोनाझोल ०.५ मिली/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Mosaic_virus": {
        "disease_name_en": "Tomato Mosaic Virus (ToMV)",
        "disease_name_mr": "टोमॅटोवरील मोझॅक विषाणू रोग",
        "pathogen_type": "Viral (Tomato mosaic tobamovirus)",
        "authoritative_source": "ICAR-IIVR Solanaceous Viral Diseases Bulletin",
        "phi_days": None,
        "symptoms_en": "Mottled dark and light green mosaic leaf patterns, leaflet curling, and stunting.",
        "symptoms_mr": "पानांवर फिकट व गर्द हिरवे चट्टे (मोझॅक), पाने आकसणे आणि वाढ खुंटणे.",
        "cultural_en": "Rogue out infected plants early. Disinfect hands and tools with skimmed milk or soap. Prohibit tobacco use.",
        "cultural_mr": "बाधित झाडे उपटून नष्ट करा. अवजारे व हात दुधाच्या द्रावणाने धुवा. तंबाखूचा वापर टाळा.",
        "chemical_en": f"Viruses cannot be cured with chemical fungicides. Suppress secondary spread; rogue infected stools. {PPE_NOTICE_EN}",
        "chemical_mr": f"विषाणू रोगावर कोणतेही रासायनिक औषध नाही. बाधित झाडे उपटून नष्ट करा. {PPE_NOTICE_MR}",
    },
    "Septoria_leaf_spot": {
        "disease_name_en": "Tomato Septoria Leaf Spot (Septoria lycopersici)",
        "disease_name_mr": "टोमॅटोवरील सेप्टोरिया ठिपके रोग",
        "pathogen_type": "Fungal (Septoria lycopersici)",
        "authoritative_source": "TNAU Agritech Portal & CIBRC",
        "phi_days": 7,
        "symptoms_en": "Numerous circular small spots with dark brown margins and grayish-white centers with black pycnidia.",
        "symptoms_mr": "पानांवर लहान गोलाकार डाग ज्यांची कडा गडद व मध्यभाग राखाडी-पांढरा असून बारीक काळे ठिपके दिसतात.",
        "cultural_en": "Destroy solanaceous weeds around borders. Mulch soil to prevent rain splash.",
        "cultural_mr": "बांधावरील तणे नष्ट करा. जमिनीवर आच्छादन करा जेणेकरून पावसाचे शिंतोडे उडणार नाहीत.",
        "chemical_en": f"Apply Chlorothalonil 75% WP @ 2.0 g/L or Tebuconazole 25.9% EC @ 1.0 ml/L. PHI: 5-7 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"क्लोरोथॅलोनिल २.० ग्रॅम/लिटर किंवा टेब्युकोनाझोल १.० मिली/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Spider_mites": {
        "disease_name_en": "Two-Spotted Spider Mites (Tetranychus urticae)",
        "disease_name_mr": "टोमॅटोवरील लाल कोळी (माइट्स)",
        "pathogen_type": "Acari / Pest (Tetranychus urticae)",
        "authoritative_source": "ICAR-IIHR Acarology Guide & CIBRC Acaricide List",
        "phi_days": 3,
        "symptoms_en": "Yellow stippling on leaf surface, bronzing, drying, and fine webbing on leaf undersides.",
        "symptoms_mr": "पानांवर बारीक पिवळे ठिपके, पाने तांबूस होऊन वाळणे आणि पानाच्या मागे बारीक जाळे दिसणे.",
        "cultural_en": "Spray water under high pressure on undersides to break webs. Avoid water stress.",
        "cultural_mr": "पाण्याचा जोरदार फवारा मारून जाळे नष्ट करा. पिकाला पाण्याचा ताण पडू देऊ नका.",
        "chemical_en": f"Apply Spiromesifen 22.9% SC @ 1.0 ml/L or Propargite 57% EC @ 2.0 ml/L. PHI: 3-7 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"स्पायरोमेसिफेन १.० मिली/लिटर किंवा प्रोपारगाइट २.० मिली/लिटर पानांच्या खाली फवारा. {PPE_NOTICE_MR}",
    },
    "Target_Spot": {
        "disease_name_en": "Tomato Target Spot (Corynespora cassiicola)",
        "disease_name_mr": "टोमॅटोवरील टार्गेट स्पॉट रोग",
        "pathogen_type": "Fungal (Corynespora cassiicola)",
        "authoritative_source": "ICAR-IIVR Vegetable Diseases Compendium",
        "phi_days": 3,
        "symptoms_en": "Pinpoint brown spots expanding into concentric target-like lesions on leaves.",
        "symptoms_mr": "पानांवर लहान ठिपके वाढून गोलाकार वलयांचे चट्टे तयार होतात व पाने वाळतात.",
        "cultural_en": "Ensure good row spacing for aeration. Avoid overhead irrigation.",
        "cultural_mr": "हवा खेळती राहण्यासाठी योग्य अंतर ठेवा. वरून पाणी देणे टाळा.",
        "chemical_en": f"Apply Azoxystrobin 23% SC @ 1.0 ml/L or Pyraclostrobin 20% WG @ 1.0 g/L. PHI: 3-5 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"अॅझॉक्सीस्ट्रॉबिन १.० मिली/लिटर किंवा पायराक्लोस्ट्रॉबिन १.० ग्रॅम/लिटर फवारा. {PPE_NOTICE_MR}",
    },
    "Yellow_Leaf_Curl_Virus": {
        "disease_name_en": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "disease_name_mr": "टोमॅटोवरील पानांचा चुरडा-मुरडा (लीफ कर्ल व्हायरस)",
        "pathogen_type": "Viral (Begomovirus transmitted by Whiteflies)",
        "authoritative_source": "ICAR-IIHR Begomovirus Guidelines & CIBRC",
        "phi_days": 5,
        "symptoms_en": "Severe upward leaf cupping, yellow leaflet margins, dwarfing, and flower drop.",
        "symptoms_mr": "पाने वाटीसारखी वरच्या बाजूला वळतात (चुरडा-मुरडा), पाने पिवळी व बारीक होतात आणि फुले गळतात.",
        "cultural_en": "Install yellow sticky traps (25/acre). Net nursery seedlings. Rogue out early infected plants.",
        "cultural_mr": "एकरी २५ पिवळे चिकट सापळे लावा. रोपवाटिकेत नायलॉन जाळी वापरा. बाधित रोपे उपटून टाका.",
        "chemical_en": f"Spray Diafenthiuron 50% WP @ 1.2 g/L or Cyantraniliprole 10.26% OD @ 1.8 ml/L to suppress whitefly vector. PHI: 3-5 days. {PPE_NOTICE_EN}",
        "chemical_mr": f"पांढऱ्या माशीच्या नियंत्रणासाठी डायाफेन्थिरॉन १.२ ग्रॅम किंवा सायांट्रानिलीप्रोल १.८ मिली/लिटर फवारा. {PPE_NOTICE_MR}",
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
    2. Out-of-distribution (OOD) foliar quality verification (rejects non-leaf uploads).
    3. Crop support checking (only genuine trained models are executed).
    4. PyTorch model inference & Grad-CAM visual lesion explainability.
    5. Conservative confidence threshold gating to suppress risky chemical prescriptions.
    6. Empirical foliar lesion segmentation & severity quantification.
    7. Authoritative agronomic advisory generation with ICAR/CIBRC citations and statutory disclaimers.
    8. Multi-tenant ownership verification and database persistence.
    """

    SUPPORTED_CROPS: Dict[str, str] = {
        "sugarcane": "models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth",
        "tomato": "models/tomato/mobilenet_v3/best_model.pth",
        "onion": "models/onion/mobilenet_v3/best_model.pth",
    }

    def check_crop_support(self, crop_name: str) -> str:
        """Verifies that a genuine trained model is configured for the crop.
        
        Raises UnsupportedCropError with structured explanation if unavailable.
        """
        normalized = crop_name.strip().lower()
        for supported_key in self.SUPPORTED_CROPS:
            if supported_key in normalized:
                return supported_key

        supported_list = ", ".join(self.SUPPORTED_CROPS.keys())
        raise UnsupportedCropError(
            f"AI diagnosis is currently unavailable for crop '{crop_name}'. "
            f"Model inference is currently only supported for: {supported_list}. "
            f"Model currently serves {supported_list} crop pathology. Received: '{crop_name}'."
        )

    def evaluate_safety_and_advisory(
        self,
        crop: str,
        predicted_class: str,
        confidence: float,
        class_scores: Dict[str, float],
        heatmap_path: Optional[str] = None,
        severity: Optional[DiagnosisSeverity] = None,
        affected_area_percentage: Optional[float] = None,
    ) -> DiagnosticInferenceResult:
        """Applies confidence-aware safety evaluation and conservative agronomic gating.
        
        Threshold rules:
        - High Confidence (>= 0.75): Verified diagnosis. CIBRC/ICAR advice with expert review notice.
        - Moderate Confidence (0.50 <= conf < 0.75): Low confidence warning. Chemical prescriptions suppressed.
        - Low Confidence (< 0.50): Inconclusive/uncertain diagnosis. All chemical prescriptions suppressed.
        
        Severity policy:
        - Healthy: HEALTHY (0.0% area).
        - Diseased: If provided from empirical segmentation and high confidence, uses computed severity;
          otherwise defaults safely to UNAVAILABLE.
        """
        conf_high = settings.CONFIDENCE_THRESHOLD_HIGH
        conf_mod = settings.CONFIDENCE_THRESHOLD_MODERATE

        if "tomato" in crop.lower():
            knowledge = TOMATO_PATHOLOGY_KNOWLEDGE.get(
                predicted_class, TOMATO_PATHOLOGY_KNOWLEDGE["Early_blight"]
            )
        else:
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

            # Use empirical segmentation if provided, else safe default
            final_severity = severity if severity is not None else DiagnosisSeverity.UNAVAILABLE
            final_area = affected_area_percentage if affected_area_percentage is not None else None

            return DiagnosticInferenceResult(
                disease_name_en=knowledge["disease_name_en"],
                disease_name_mr=knowledge["disease_name_mr"],
                pathogen_type=knowledge["pathogen_type"],
                confidence=round(confidence, 4),
                severity=final_severity,
                affected_area_percentage=final_area,
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

        # 1. Foliar vegetation validation (OOD Defense)
        pil_img = Image.open(io.BytesIO(full_content)).convert("RGB")
        is_valid, cov_ratio, val_msg = segmentation_service.validate_foliar_quality(pil_img)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=val_msg,
            )

        # 2. Run inference through PyTorch singleton
        pred = model_service.predict(
            image=full_content,
            crop=normalized_crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=save_heatmap,
        )

        # 3. Empirically estimate foliar lesion severity
        emp_severity, emp_area = segmentation_service.estimate_foliar_severity(
            image=pil_img,
            predicted_class=pred["predicted_class"],
            crop=normalized_crop,
        )

        safety_eval = self.evaluate_safety_and_advisory(
            crop=normalized_crop,
            predicted_class=pred["predicted_class"],
            confidence=pred["confidence"],
            class_scores=pred["class_scores"],
            heatmap_path=pred.get("heatmap_path"),
        )

        # 4. Synthesize end-to-end Context-Aware Advisory
        advisory_req = AdvisoryGenerateRequest(
            crop_name=normalized_crop,
            predicted_disease=pred["predicted_class"],
            confidence=pred["confidence"],
            severity=emp_severity.value,
            affected_area_percentage=emp_area,
        )
        try:
            adv_res = await recommendation_engine.generate_advisory(advisory_req)
            adv_dict = adv_res.model_dump()
        except Exception as adv_err:
            logger.warning(f"Advisory generation fallback: {adv_err}")
            adv_dict = None

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
                "foliar_segmentation": {
                    "foliar_coverage_ratio": round(cov_ratio, 4),
                    "empirical_affected_area_percentage": emp_area,
                    "empirical_severity": emp_severity.value,
                },
                "recommendations_en": safety_eval.recommendations_en,
                "recommendations_mr": safety_eval.recommendations_mr,
                "contextual_advisory": adv_dict,
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
        3. Verifies crop foliage quality (rejects non-foliar uploads).
        4. Verifies crop model availability (rejects unsupported crops).
        5. Runs genuine PyTorch inference and optional Grad-CAM explainability.
        6. Applies confidence-aware safety gating.
        7. Persists Diagnosis record to database.
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

        # 4. Foliar vegetation validation (OOD Defense)
        pil_img = Image.open(io.BytesIO(full_content)).convert("RGB")
        is_valid, cov_ratio, val_msg = segmentation_service.validate_foliar_quality(pil_img)
        if not is_valid:
            storage_service.remove_file(storage_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=val_msg,
            )

        # 5. Auto-resolve ambient microclimate if not manually supplied
        if temperature is None or humidity is None:
            farm_lat = crop.farm.latitude if crop.farm else None
            farm_lon = crop.farm.longitude if crop.farm else None
            try:
                weather_data = await weather_service.get_current_weather(farm_lat, farm_lon)
                if temperature is None:
                    temperature = weather_data.temperature_c
                if humidity is None:
                    humidity = weather_data.relative_humidity_pct
            except Exception as w_err:
                logger.warning(f"Could not auto-fetch weather for farm: {w_err}")

        # 6. Run model inference & safety evaluation
        try:
            pred = model_service.predict(
                image=full_content,
                crop=normalized_crop,
                generate_gradcam=generate_gradcam,
                save_heatmap=True,
            )

            emp_severity, emp_area = segmentation_service.estimate_foliar_severity(
                image=pil_img,
                predicted_class=pred["predicted_class"],
                crop=normalized_crop,
            )

            safety_eval = self.evaluate_safety_and_advisory(
                crop=normalized_crop,
                predicted_class=pred["predicted_class"],
                confidence=pred["confidence"],
                class_scores=pred["class_scores"],
                heatmap_path=pred.get("heatmap_path"),
            )

            # Synthesize context-aware recommendations fusing microclimate
            rec_en = safety_eval.recommendations_en
            rec_mr = safety_eval.recommendations_mr
            try:
                advisory_req = AdvisoryGenerateRequest(
                    crop_name=normalized_crop,
                    predicted_disease=pred["predicted_class"],
                    confidence=pred["confidence"],
                    severity=emp_severity.value,
                    affected_area_percentage=emp_area,
                    crop_stage=crop.growth_stage,
                    temperature=temperature,
                    humidity=humidity,
                    latitude=crop.farm.latitude if crop.farm else None,
                    longitude=crop.farm.longitude if crop.farm else None,
                )
                adv_res = await recommendation_engine.generate_advisory(advisory_req, db=db)
                if adv_res and adv_res.overview.get("en"):
                    rec_en = f"{adv_res.overview.get('en')}\n\n• Spray Directive: {adv_res.spray_window_directive.get('en')}\n\n{safety_eval.recommendations_en}"
                    rec_mr = f"{adv_res.overview.get('mr')}\n\n• फवारणी सल्ला: {adv_res.spray_window_directive.get('mr')}\n\n{safety_eval.recommendations_mr}"
            except Exception as adv_err:
                logger.warning(f"Context advisory synthesis fallback: {adv_err}")

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
                recommendations_en=rec_en,
                recommendations_mr=rec_mr,
                temperature=temperature,
                humidity=humidity,
                soil_moisture=soil_moisture,
                status=DiagnosisStatus.COMPLETED,
                notes=notes,
            )
        except Exception as e:
            logger.error(f"Inference failure during authenticated diagnosis: {e}", exc_info=True)
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

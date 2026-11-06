"""
PikVaidya AI — Verified Onion Pathology Seed Knowledge Data
===========================================================
Authoritative pathology records for 4 audited Onion categories:
  1. Healthy Foliage (Allium cepa)
  2. Purple Blotch (Alternaria porri)
  3. Stemphylium Leaf Blight (Stemphylium vesicarium)
  4. Iris Yellow Spot Virus (IYSV - Tospovirus)

Authoritative Agricultural Sources:
  - ICAR - Directorate of Onion and Garlic Research (DOGR, Rajgurunagar, Pune)
  - Mahatma Phule Krishi Vidyapeeth (MPKV, Rahuri) - Vegetable Pathology
  - Central Insecticide Board & Registration Committee (CIBRC, Govt. of India)
  - National Horticultural Research and Development Foundation (NHRDF, Nashik)
"""

from typing import List, Dict, Any

PPE_NOTICE_EN = (
    "Mandatory PPE: Wear chemical-resistant nitrile gloves, vapor/particulate mask, "
    "and protective goggles during mixing and spraying under Insecticides Rules, 1971."
)
PPE_NOTICE_MR = (
    "अनिवार्य सुरक्षा: कीटकनाशक नियम १९७१ नुसार औषध मिसळताना व फवारताना हातमोजे, "
    "मास्क आणि संरक्षणात्मक चष्मा वापरणे बंधनकारक आहे."
)
PPE_NOTICE_HI = (
    "अनिवार्य सुरक्षा: कीटनाशक नियम 1971 के अनुसार दवाई मिलाते और छिड़कते समय दस्ताने, "
    "मास्क और सुरक्षा चश्मा जरूर पहनें।"
)

ONION_DISEASE_SEEDS: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. Healthy Foliage (Allium cepa)
    # --------------------------------------------------------------------------
    {
        "disease_id": "onion_healthy_en",
        "crop_name": "onion",
        "disease_name": "Healthy Foliage",
        "scientific_name": "Allium cepa",
        "pathogen_type": "None (Healthy)",
        "language": "en",
        "symptoms": (
            "Vigorous, erect tubular cylindrical leaves with uniform glaucescent blue-green waxy bloom. "
            "Absence of sunken purple zonation, chlorotic flecks, or spindle-shaped straw necrotic lesions."
        ),
        "causes": "Optimal soil moisture, balanced NPK nutrition (100:50:50 kg/ha), and proactive thrips management.",
        "favourable_conditions": "Day temperatures 20–30°C, relative humidity 50–70%, well-drained loamy soil (pH 6.5–7.5).",
        "prevention_methods": (
            "1. Procure certified disease-free sets or seeds treated with Trichoderma viride @ 5 g/kg.\n"
            "2. Follow 2–3 year crop rotation with non-allium crops like maize, soybean, or pulses.\n"
            "3. Install drip irrigation or micro-sprinklers; avoid prolonged overhead sprinkler foliar wetting.\n"
            "4. Maintain field sanitation and eradicate volunteer allium weeds."
        ),
        "management_methods": (
            "Biological & Cultural Measures:\n"
            "- Soil application of FYM enriched with Pseudomonas fluorescens @ 2.5 kg/ha.\n"
            "- Balanced sulphur nutrition (20 kg/ha elemental sulphur) to enhance allicin content and natural disease resilience.\n"
            "- Monitor thrips population using yellow/blue sticky traps (10 traps/acre).\n\n"
            "Chemical Treatments:\n"
            "- No chemical intervention warranted. Continue routine prophylactic monitoring."
        ),
        "reference_sources": "ICAR-DOGR Package of Practices; MPKV Rahuri Vegetable Cultivation Guide.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_healthy_mr",
        "crop_name": "onion",
        "disease_name": "निरोगी पीक",
        "scientific_name": "Allium cepa",
        "pathogen_type": "None (Healthy)",
        "language": "mr",
        "symptoms": "कांद्याची पाने सरळ, नळीसारखी आणि एकसमान निळसर-हिरव्या मेणासारख्या थराने आच्छादलेली असतात. पानांवर कोणताही जांभळा, तपकिरी किंवा पिवळा डाग नसतो.",
        "causes": "योग्य जमिनीचा निचरा, शिफारशीत खत व्यवस्थापन आणि फुलकिड्यांचे (थ्रिप्स) वेळेवर नियंत्रण.",
        "favourable_conditions": "तापमान २० ते ३० अंश से., हवेतील आर्द्रता ५० ते ७०%, उत्तम निचरा असलेली मध्यम ते भारी जमीन.",
        "prevention_methods": (
            "१. ट्रायकोडर्मा व्हिरिडी @ ५ ग्रॅम प्रति किलो बियाण्यास बीजप्रक्रिया करावी.\n"
            "२. तृणधान्य किंवा कडधान्य पिकांसोबत २ ते ३ वर्षांचे पीक फेरपालट करावे.\n"
            "३. तुषार सिंचनाऐवजी ठिबक सिंचनाचा वापर करावा जेणेकरून पानांवर सतत ओलावा राहणार नाही.\n"
            "४. शेतातील तण नियमितपणे काढून टाकावे."
        ),
        "management_methods": (
            "सेंद्रिय व मशागतीय पद्धती:\n"
            "- शेणखतात मिसळून सुडोमोनास फ्लोरोसन्स @ २.५ किलो प्रति हेक्टर जमिनीत द्यावे.\n"
            "- एकरी १० पिवळे/निळे चिकट सापळे लावून किडींचे निरीक्षण करावे.\n\n"
            "रासायनिक फवारणी:\n"
            "- पीक निरोगी असल्याने रासायनिक बुरशीनाशकांची आवश्यकता नाही."
        ),
        "reference_sources": "भाकृअनुप - कांदा व लसूण संशोधन संचालनालय (ICAR-DOGR), राजगुरूनगर, पुणे.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_healthy_hi",
        "crop_name": "onion",
        "disease_name": "स्वस्थ फसल",
        "scientific_name": "Allium cepa",
        "pathogen_type": "None (Healthy)",
        "language": "hi",
        "symptoms": "प्याज की पत्तियां सीधी, बेलनाकार और समान नीले-हरे मोमी आवरण से युक्त होती हैं। पत्तियों पर कोई धब्बे या झुलसा नहीं होता।",
        "causes": "उचित जल निकासी, संतुलित उर्वरक प्रबंधन और कीटों से सुरक्षा।",
        "favourable_conditions": "तापमान 20-30°C, आर्द्रता 50-70%, उपजाऊ दोमट मिट्टी।",
        "prevention_methods": (
            "1. ट्राइकोडर्मा विरिडी 5 ग्राम/किग्रा बीज दर से बीजोपचार करें।\n"
            "2. फसल चक्र अपनाएं और जलभराव से बचें।\n"
            "3. खेत को खरपतवार मुक्त रखें।"
        ),
        "management_methods": "जैविक उपाय जारी रखें। किसी रासायनिक छिड़काव की आवश्यकता नहीं है।",
        "reference_sources": "आईसीएआर-डीओजीआर (ICAR-DOGR) राजगुरुनगर, पुणे।",
        "last_verified": "2026-11-06"
    },

    # --------------------------------------------------------------------------
    # 2. Purple Blotch (Alternaria porri)
    # --------------------------------------------------------------------------
    {
        "disease_id": "onion_purple_blotch_en",
        "crop_name": "onion",
        "disease_name": "Purple Blotch",
        "scientific_name": "Alternaria porri",
        "pathogen_type": "Fungus (Alternaria porri)",
        "language": "en",
        "symptoms": (
            "Small, water-soaked elliptic spots on leaves that rapidly enlarge into sunken purple to dark brown "
            "lesions with distinct concentric zonation and broad chlorotic yellow margins. In severe cases, lesions "
            "girdle the tubular blade, causing stalk collapse, leaf lodging, and failure of bulb development."
        ),
        "causes": "Fungal pathogen Alternaria porri persisting on crop debris, volunteer alliums, and infected bulb sets.",
        "favourable_conditions": "High relative humidity (> 85%), warm temperatures (25–30°C), and extended leaf wetness.",
        "prevention_methods": (
            "1. Hot water bulb/set treatment at 50°C for 30 minutes before transplanting.\n"
            "2. Deep summer ploughing to bury fungal conidia and chlamydospores.\n"
            "3. Wider spacing (15 cm x 10 cm) to facilitate canopy aeration and reduce relative humidity.\n"
            "4. Controlled irrigation; avoid late evening overhead sprinkler passes."
        ),
        "management_methods": (
            "Biological & Cultural Controls:\n"
            "- Prophylactic foliar spray of Trichoderma harzianum @ 5 g/L with sticker at early vegetative stage.\n"
            "- Eradicate and burn severely blighted leaves.\n\n"
            "CIBRC Approved Chemical Formulations:\n"
            "- Mancozeb 75% WP @ 2.5 g/L water (0.25%) with sticker (Sandovit/Spreader @ 0.5 ml/L). PHI: 14 days.\n"
            "- Difenoconazole 25% EC @ 1.0 ml/L water. PHI: 10 days.\n"
            "- Tebuconazole 25.9% m/m EC @ 1.5 ml/L water. PHI: 15 days.\n"
            "- Propiconazole 25% EC @ 1.0 ml/L water. PHI: 14 days.\n\n"
            f"{PPE_NOTICE_EN}"
        ),
        "reference_sources": "ICAR-DOGR Technical Bulletin on Onion Pathology; CIBRC Registered Fungicide Matrix.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_purple_blotch_mr",
        "crop_name": "onion",
        "disease_name": "जांभळा करपा",
        "scientific_name": "Alternaria porri",
        "pathogen_type": "Fungus (Alternaria porri)",
        "language": "mr",
        "symptoms": (
            "पानांवर सुरुवातीला खोलगट, पांढुरके डाग पडतात जे नंतर मध्यभागी जांभळट-तपकिरी होतात. डागांच्या कडा पिवळसर "
            "होतात आणि डाग गोलाकार रिंगसारखे दिसतात. तीव्र प्रादुर्भावात पाने मधोमध वाकतात, सुकतात व गळून पडतात."
        ),
        "causes": "अल्टरनेरिया पोरी (Alternaria porri) या बुरशीचा प्रादुर्भाव. हवेतील आर्द्रता व जुन्या अवशेषांमधून बुरशीचे बीजाणू पसरतात.",
        "favourable_conditions": "हवेतील आर्द्रता ८५% पेक्षा जास्त, तापमान २५ ते ३० अंश से. आणि ढगाळ हवामान.",
        "prevention_methods": (
            "१. पेरणीपूर्वी बियाण्यास थायरम किंवा ट्रायकोडर्मा ५ ग्रॅम/किलोची प्रक्रिया करावी.\n"
            "२. शेतात पाण्याचा निचरा योग्य ठेवावा; जास्त पाणी साचू देऊ नये.\n"
            "३. रोपांची योग्य अंतरावर लागवड करावी (१५ x १० सें.मी.)."
        ),
        "management_methods": (
            "जैविक उपाय:\n"
            "- ट्रायकोडर्मा हरझियानम ५ ग्रॅम प्रति लिटर पाण्यात मिसळून प्रतिबंधात्मक फवारणी करावी.\n\n"
            "CIBRC मान्यताप्राप्त रासायनिक उपाय:\n"
            "- मॅन्कोझेब ७५% डब्ल्यूपी @ २.५ ग्रॅम प्रति लिटर पाण्यात स्टिकरसह मिसळून फवारावे (प्रतीक्षा काळ: १४ दिवस).\n"
            "- डायफेनोकोनॅझोल २५% ईसी @ १ मि.ली. प्रति लिटर पाणी (प्रतीक्षा काळ: १० दिवस).\n"
            "- टेबुकोनॅझोल २५.९% ईसी @ १.५ मि.ली. प्रति लिटर पाणी (प्रतीक्षा काळ: १५ दिवस).\n\n"
            f"{PPE_NOTICE_MR}"
        ),
        "reference_sources": "भाकृअनुप - कांदा व लसूण संशोधन संचालनालय (ICAR-DOGR), राजगुरूनगर.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_purple_blotch_hi",
        "crop_name": "onion",
        "disease_name": "बैंगनी धब्बा (पर्पल ब्लॉच)",
        "scientific_name": "Alternaria porri",
        "pathogen_type": "Fungus (Alternaria porri)",
        "language": "hi",
        "symptoms": "पत्तियों पर छोटे धंसे हुए धब्बे बनते हैं जो बाद में गहरे बैंगनी-भूरे रंग के छल्लेदार आकार ले लेते हैं। पत्तियां बीच से टूटकर गिर जाती हैं।",
        "causes": "अल्टरनेरिया पोरी कवक का संक्रमण।",
        "favourable_conditions": "तापमान 25-30°C, सापेक्ष आर्द्रता 80-90% और बादल छाए रहना।",
        "prevention_methods": (
            "1. रोगमुक्त बीज एवं कंद का चयन करें।\n"
            "2. उचित जल निकास की व्यवस्था करें।"
        ),
        "management_methods": (
            "रासायनिक उपचार:\n"
            "- मैंकोजेब 75% WP @ 2.5 ग्राम/लीटर पानी में स्टीकर मिलाकर छिड़कें।\n"
            "- डाईफेनोकोनाजोल 25% EC @ 1 मिली/लीटर पानी।\n\n"
            f"{PPE_NOTICE_HI}"
        ),
        "reference_sources": "आईसीएआर-डीओजीआर प्याज रोग प्रबंधन संदर्शिका।",
        "last_verified": "2026-11-06"
    },

    # --------------------------------------------------------------------------
    # 3. Stemphylium Leaf Blight (Stemphylium vesicarium)
    # --------------------------------------------------------------------------
    {
        "disease_id": "onion_stemphylium_blight_en",
        "crop_name": "onion",
        "disease_name": "Stemphylium Leaf Blight",
        "scientific_name": "Stemphylium vesicarium",
        "pathogen_type": "Fungus (Stemphylium vesicarium)",
        "language": "en",
        "symptoms": (
            "Small, pale yellow-to-tan water-soaked flecks on the radial leaf blades that rapidly expand into elongated, "
            "spindle-shaped necrotic blights. Lesions turn dark olive-brown to black as velvety fungal conidia emerge. "
            "Leaves turn prematurely yellow from the tip downwards and desiccate completely."
        ),
        "causes": "Fungal pathogen Stemphylium vesicarium. Often co-infects with Alternaria porri or follows thrips lacerations.",
        "favourable_conditions": "Moderate temperatures (18–26°C), prolonged leaf wetness (> 16 hours), and post-rain humidity.",
        "prevention_methods": (
            "1. Proactive management of onion thrips (Thrips tabaci) whose epidermal feeding creates entry wounds.\n"
            "2. Balanced fertilizer application; avoid excessive nitrogen which produces succulent, susceptible leaf tissue.\n"
            "3. Apply elemental sulphur (20–25 kg/ha) during basal fertilization."
        ),
        "management_methods": (
            "Biological & Cultural Controls:\n"
            "- Spray Pseudomonas fluorescens @ 5 g/L with 0.5 ml/L agricultural spreader.\n"
            "- Ensure 3-year crop rotation with non-allium graminaceous hosts.\n\n"
            "CIBRC Approved Chemical Formulations:\n"
            "- Chlorothalonil 75% WP @ 2.0 g/L water (0.2%). PHI: 14 days.\n"
            "- Azoxystrobin 23% SC @ 1.0 ml/L water. PHI: 7 days.\n"
            "- Pyraclostrobin 20% WG @ 1.0 g/L water. PHI: 10 days.\n"
            "- Kresoxim-methyl 44.3% SC @ 1.0 ml/L water. PHI: 10 days.\n\n"
            f"{PPE_NOTICE_EN}"
        ),
        "reference_sources": "ICAR-DOGR Leaf Blight Advisory; CIBRC Fungicide Compendium.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_stemphylium_blight_mr",
        "crop_name": "onion",
        "disease_name": "तपकिरी करपा / स्टेमफिलियम",
        "scientific_name": "Stemphylium vesicarium",
        "pathogen_type": "Fungus (Stemphylium vesicarium)",
        "language": "mr",
        "symptoms": (
            "पानांवर फिकट पिवळे ते तपकिरी रंगाचे लहान ठिपके तयार होतात, जे नंतर लांबट आकाराचे होतात. बुरशी वाढल्यामुळे "
            "डाग काळे किंवा काळपट-तपकिरी दिसतात. पानाच्या शेंड्यापासून सुकण्यास सुरुवात होते व संपूर्ण पान वाळते."
        ),
        "causes": "स्टेमफिलियम व्हेसिकॅरियम (Stemphylium vesicarium) बुरशी. थ्रिप्सच्या जखमांमधून बुरशीचा प्रादुर्भाव वेगाने वाढतो.",
        "favourable_conditions": "तापमान १८ ते २५ अंश से., पानावरील जास्त काळ ओलावा आणि ढगाळ हवामान.",
        "prevention_methods": (
            "१. थ्रिप्स किडीचे वेळेवर नियंत्रण करावे कारण थ्रिप्समुळे पानांवर जखमा होऊन करपा वाढतो.\n"
            "२. नत्रयुक्त खतांचा अतिवापर टाळावा व पोटॅश खताचा संतुलित वापर करावा.\n"
            "३. सेंद्रिय गंधकाचा (सल्फर) वापर करावा."
        ),
        "management_methods": (
            "जैविक नियंत्रण:\n"
            "- सुडोमोनास फ्लोरोसन्स ५ ग्रॅम प्रति लिटर पाण्यात स्टिकरसह मिसळून फवारावे.\n\n"
            "CIBRC मान्यताप्राप्त रासायनिक बुरशीनाशके:\n"
            "- अझॉक्सीस्ट्रॉबिन २३% एससी @ १ मि.ली. प्रति लिटर पाणी (प्रतीक्षा काळ: ७ दिवस).\n"
            "- क्लोरोथॅलोनिल ७५% डब्ल्यूपी @ २ ग्रॅम प्रति लिटर पाणी (प्रतीक्षा काळ: १४ दिवस).\n"
            "- पायराक्लोस्ट्रॉबिन २०% डब्ल्यूजी @ १ ग्रॅम प्रति लिटर पाणी (प्रतीक्षा काळ: १० दिवस).\n\n"
            f"{PPE_NOTICE_MR}"
        ),
        "reference_sources": "भाकृअनुप - कांदा व लसूण संशोधन संचालनालय (ICAR-DOGR).",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_stemphylium_blight_hi",
        "crop_name": "onion",
        "disease_name": "स्टेमफिलियम लीफ ब्लाइट (भूरा झुलसा)",
        "scientific_name": "Stemphylium vesicarium",
        "pathogen_type": "Fungus (Stemphylium vesicarium)",
        "language": "hi",
        "symptoms": "पत्तियों पर पीले से भूरे रंग के धब्बे बनते हैं जो बाद में काले हो जाते हैं। पत्तियां शीर्ष से नीचे की ओर सूखने लगती हैं।",
        "causes": "स्टेमफिलियम वेसिकेरियम कवक का प्रकोप।",
        "favourable_conditions": "तापमान 18-25°C, पत्तियों पर नमी और थ्रिप्स का प्रकोप।",
        "prevention_methods": "थ्रिप्स पर नियंत्रण रखें और संतुलित उर्वरक प्रयोग करें।",
        "management_methods": (
            "रासायनिक उपचार:\n"
            "- एजोक्सीस्ट्रोबिन 23% SC @ 1 मिली/लीटर पानी।\n"
            "- क्लोरोथैलोनिल 75% WP @ 2 ग्राम/लीटर पानी।\n\n"
            f"{PPE_NOTICE_HI}"
        ),
        "reference_sources": "आईसीएआर-डीओजीआर सब्जी रोग प्रबंधन।",
        "last_verified": "2026-11-06"
    },

    # --------------------------------------------------------------------------
    # 4. Iris Yellow Spot Virus (IYSV)
    # --------------------------------------------------------------------------
    {
        "disease_id": "onion_iris_yellow_virus_en",
        "crop_name": "onion",
        "disease_name": "Iris Yellow Spot Virus (IYSV)",
        "scientific_name": "Iris Yellow Spot Virus (Tospovirus)",
        "pathogen_type": "Virus (Tospovirus / IYSV)",
        "language": "en",
        "symptoms": (
            "Characteristic straw-colored, diamond-shaped, chlorotic spindle lesions on leaves and seed scapes. "
            "Lesions frequently contain distinct green islands of living tissue inside the bleached area. As lesions coalesce, "
            "the scape or leaf blade bends at the infection site, causing premature lodging and severe bulb yield loss."
        ),
        "causes": "Iris Yellow Spot Virus (IYSV), family Bunyaviridae, exclusively transmitted by Onion Thrips (Thrips tabaci).",
        "favourable_conditions": "Hot, dry conditions (30–38°C) that favor rapid thrips proliferation; stress from drought.",
        "prevention_methods": (
            "1. Plant barrier crops (2–3 border rows of maize, sorghum, or bajra) around onion plots to impede thrips flight.\n"
            "2. Install blue and yellow sticky traps @ 20 traps/acre at canopy level for mass vector trapping.\n"
            "3. Destroy culled onion bulbs, allium weeds, and post-harvest volunteers harboring thrips and virus.\n"
            "4. Maintain adequate soil moisture through micro-irrigation to alleviate heat and moisture stress."
        ),
        "management_methods": (
            "Statutory Viral Notice:\n"
            "- Viral pathogens cannot be eradicated with chemical viricides. Management relies exclusively on vector control.\n\n"
            "Biological Vector Control:\n"
            "- Foliar spray of entomopathogenic fungus Beauveria bassiana (1x10^8 CFU/g) @ 5 g/L with sticker.\n"
            "- Neem seed kernel extract (NSKE 5%) or Azadirachtin 10000 ppm @ 2 ml/L.\n\n"
            "CIBRC Approved Thrips Insecticides:\n"
            "- Fipronil 5% SC @ 1.5 ml/L water. PHI: 15 days.\n"
            "- Spinetoram 11.7% SC @ 0.9 ml/L water. PHI: 10 days.\n"
            "- Acetamiprid 20% SP @ 0.3 g/L water. PHI: 7 days.\n\n"
            f"{PPE_NOTICE_EN}"
        ),
        "reference_sources": "ICAR-DOGR Technical Guide on Iris Yellow Spot Virus; MPKV Rahuri Thrips Advisory.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_iris_yellow_virus_mr",
        "crop_name": "onion",
        "disease_name": "आयरिस पिवळा व्हायरस (IYSV)",
        "scientific_name": "Iris Yellow Spot Virus (Tospovirus)",
        "pathogen_type": "Virus (Tospovirus / IYSV)",
        "language": "mr",
        "symptoms": (
            "पानांवर व कांद्याच्या दांड्यावर (फुलोऱ्याच्या देठावर) पिवळसर-पांढऱ्या रंगाचे डायमंडच्या आकाराचे (चौकोनी/बदामी) डाग "
            "पडतात. डागांच्या मध्यभागी हिरवट भाग दिसतो. डाग वाढल्यावर पान किंवा दांडा त्या ठिकाणाहून वाकतो व मोडतो."
        ),
        "causes": "आयरिस यलो स्पॉट व्हायरस (विषाणू). हा विषाणू फुलकिडे (थ्रिप्स - Thrips tabaci) द्वारे पसरतो.",
        "favourable_conditions": "उष्ण व कोरडे हवामान (३० ते ३८ अंश से.), पाण्याची कमतरता आणि फुलकिड्यांची जास्त संख्या.",
        "prevention_methods": (
            "१. शेताच्या चोहोबाजूने मका किंवा ज्वारीच्या २ ते ३ ओळींचे संरक्षक कुंपण लावावे जेणेकरून फुलकिड्यांचा प्रसार रोखता येईल.\n"
            "२. शेतात एकरी २० निळे व पिवळे चिकट सापळे लावावेत.\n"
            "३. शेतातील कांद्याचे अवशेष नष्ट करावेत.\n"
            "४. पिकाला पाण्याचा ताण पडू देऊ नये."
        ),
        "management_methods": (
            "विषाणू नियंत्रण सूचना:\n"
            "- विषाणू नष्ट करण्यासाठी कोणतेही रासायनिक औषध नसते. रोगाचा प्रसार रोखण्यासाठी फुलकिड्यांचे (थ्रिप्स) नियंत्रण करणे अनिवार्य आहे.\n\n"
            "जैविक उपाय:\n"
            "- व्हर्टिसिलियम लेकॅनी किंवा बिव्हेरिया बॅसियाना ५ ग्रॅम प्रति लिटर पाण्यात मिसळून फवारावे.\n"
            "- निंबोळी अर्क ५% किंवा अझाडिरॅक्टिन १०००० पीपीएम @ २ मि.ली. प्रति लिटर पाणी.\n\n"
            "CIBRC मान्यताप्राप्त रासायनिक फुलकिडे नियंत्रण:\n"
            "- फिप्रोनिल ५% एससी @ १.५ मि.ली. प्रति लिटर पाणी (प्रतीक्षा काळ: १५ दिवस).\n"
            "- स्पिनिटोरम ११.७% एससी @ ०.९ मि.ली. प्रति लिटर पाणी (प्रतीक्षा काळ: १० दिवस).\n"
            "- ॲसिटामिप्रीड २०% एसपी @ ०.३ ग्रॅम प्रति लिटर पाणी (प्रतीक्षा काळ: ७ दिवस).\n\n"
            f"{PPE_NOTICE_MR}"
        ),
        "reference_sources": "भाकृअनुप - कांदा व लसूण संशोधन संचालनालय (ICAR-DOGR), राजगुरूनगर, पुणे.",
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "onion_iris_yellow_virus_hi",
        "crop_name": "onion",
        "disease_name": "आइरिस पीला धब्बा वायरस",
        "scientific_name": "Iris Yellow Spot Virus (Tospovirus)",
        "pathogen_type": "Virus (Tospovirus / IYSV)",
        "language": "hi",
        "symptoms": "पत्तियों पर बादामी या हीरे (डायमंड) के आकार के पीले धब्बे बनते हैं। पौधे का विकास रुक जाता है।",
        "causes": "विषाणु जनित रोग, जिसका प्रसार थ्रिप्स कीट द्वारा होता है।",
        "favourable_conditions": "गर्म व सूखा मौसम और थ्रिप्स कीट का अधिक प्रकोप।",
        "prevention_methods": (
            "1. खेत के चारों तरफ मक्का या ज्वार की 2-3 पंक्तियां लगाएं।\n"
            "2. नीले एवं पीले चिपचिपे जाल लगाएं।"
        ),
        "management_methods": (
            "वायरस के लिए कोई प्रत्यक्ष रसायन नहीं है, अतः थ्रिप्स का नियंत्रण आवश्यक है:\n"
            "- फिप्रोनिल 5% SC @ 1.5 मिली/लीटर पानी।\n"
            "- स्पिनटोरम 11.7% SC @ 0.9 मिली/लीटर पानी।\n\n"
            f"{PPE_NOTICE_HI}"
        ),
        "reference_sources": "आईसीएआर-डीओजीआर राजगुरुनगर पुणे।",
        "last_verified": "2026-11-06"
    }
]


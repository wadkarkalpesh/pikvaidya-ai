"""
PikVaidya AI — Verified Tomato Pathology Seed Knowledge Data
=============================================================
Authoritative pathology records for 10 audited tomato categories:
  1. Bacterial Spot (Xanthomonas campestris pv. vesicatoria)
  2. Early Blight (Alternaria solani)
  3. Healthy Foliage (Solanum lycopersicum)
  4. Late Blight (Phytophthora infestans)
  5. Leaf Mold (Passalora fulva / Cladosporium fulvum)
  6. Tomato Mosaic Virus (ToMV)
  7. Septoria Leaf Spot (Septoria lycopersici)
  8. Two-Spotted Spider Mites (Tetranychus urticae)
  9. Target Spot (Corynespora cassiicola)
  10. Tomato Yellow Leaf Curl Virus (TYLCV)

Authoritative Agricultural Sources:
  - ICAR - Indian Institute of Horticultural Research (IIHR, Bengaluru)
  - ICAR - Indian Institute of Vegetable Research (IIVR, Varanasi)
  - Central Insecticide Board & Registration Committee (CIBRC, Govt. of India)
  - Mahatma Phule Krishi Vidyapeeth (MPKV, Rahuri) - Vegetable Crop Guides
  - TNAU Agritech Portal - Tomato Pathology
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

TOMATO_DISEASE_SEEDS: List[Dict[str, Any]] = [
    {
        "disease_id": "tomato_healthy",
        "crop_name": "tomato",
        "disease_name": "Healthy Foliage",
        "scientific_name": "Solanum lycopersicum (Healthy)",
        "pathogen_type": "None",
        "symptoms": {
            "en": "Foliage exhibits vigorous deep-green color, smooth turgid leaflets, uniform canopy architecture, with no necrotic margins, chlorotic halos, or curling.",
            "mr": "टोमॅटोची पाने गर्द हिरवी, तजेलदार, एकसारखी वाढलेली असून पानांवर करपा, पिवळे डाग किंवा चट्टे अजिबात नाहीत.",
            "hi": "पत्तियां पूरी तरह हरी, चमकदार और स्वस्थ हैं। किसी भी प्रकार का धब्बा, पीलापन या फफूंद नहीं है।"
        },
        "causes": {
            "en": "Balanced nutrition (NPK + micronutrients like Boron and Calcium), optimal staking, disease-free nursery seedlings, and disciplined drip irrigation.",
            "mr": "संतुलित खत व्यवस्थापन (कॅल्शियम, बोरॉनसह), निरोगी रोपे, योग्य आधार (स्टेकिंग) आणि ठिबक सिंचन.",
            "hi": "संतुलित पोषण, रोगमुक्त नर्सरी पौध, सहारा (स्टेकिंग) और उचित सिंचाई।"
        },
        "favourable_conditions": {
            "temperature_range_c": "18-28°C",
            "humidity_pct": "50-70%",
            "rainfall_trigger": "Controlled drip moisture",
            "en": "Mild sunny weather, well-drained raised beds with silver-black mulch, and good air circulation.",
            "mr": "हवा खेळती राहणारी गादीवाफे, मल्चिंग पेपरचा वापर आणि पुरेसा सूर्यप्रकाश.",
            "hi": "खुली धूप, मल्चिंग युक्त मेड़ और जल निकास वाली भूमि।"
        },
        "prevention_methods": {
            "en": [
                "Install yellow and blue sticky traps (15-20 traps/acre) to monitor sucking pests.",
                "Spray prophylactic 1% Bordeaux mixture or Copper Oxychloride 50% WP @ 2.5g/L once a month.",
                "Ensure balanced fertigation: avoid excessive nitrogen during early vegetative stage to prevent succulent growth prone to pathogens."
            ],
            "mr": [
                "रसशोषक किडींच्या निरीक्षणासाठी एकरी १५-२० पिवळे व निळे चिकट सापळे लावा.",
                "प्रतिबंधात्मक उपाय म्हणून महिन्यातून एकदा कॉपर ऑक्सिक्लोराईड २.५ ग्रॅम/लिटर फवारा.",
                "अवाजवी नत्र खतांचा वापर टाळा, कॅल्शियम नायट्रेट व बोरॉनचा योग्य वापर करा."
            ],
            "hi": [
                "कीटों की निगरानी के लिए पीले और नीले चिपचिपे कार्ड लगाएं।",
                "निवारक के रूप में कॉपर ऑक्सीक्लोराइड 2.5 ग्राम/लीटर का छिड़काव करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Maintain regular weeding, bottom pruning of senescent leaves touching the soil, and uniform staking/trellising.",
                "mr": "जमिनीला टेकणाऱ्या खालच्या जुन्या पानांची छाटणी करा आणि तारा-बांबूच्या साहाय्याने झाडांना आधार द्या.",
                "hi": "निचली पुरानी पत्तियों की कटाई करें और पौधों को सहारा दें।"
            },
            "biological": {
                "en": "Soil drenching with Trichoderma harzianum @ 5 kg/ha mixed with well-rotted FYM at transplanting.",
                "mr": "लागवडीवेळी ट्रायकोडर्मा हरझियानम ५ किलो/हेक्टर शेणखतात मिसळून द्या.",
                "hi": "रोपाई के समय ट्राइकोडर्मा 5 किग्रा/हेक्टेयर गोबर की खाद में मिलाकर डालें।"
            },
            "chemical": []
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIHR Tomato Package of Practices",
                "organization": "ICAR - Indian Institute of Horticultural Research, Bengaluru",
                "citation": "IIHR Vegetable Production Manual 2024"
            },
            {
                "source_name": "MPKV Rahuri Vegetable Cultivation Guide",
                "organization": "Mahatma Phule Krishi Vidyapeeth, Rahuri",
                "citation": "Tomato Production Technology Bulletin"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_bacterial_spot",
        "crop_name": "tomato",
        "disease_name": "Tomato Bacterial Spot",
        "scientific_name": "Xanthomonas campestris pv. vesicatoria",
        "pathogen_type": "Bacterial",
        "symptoms": {
            "en": "Small, dark brown to black, water-soaked, circular to angular lesions on leaves and stems, often surrounded by yellow halos. Foliage may exhibit severe blighting and drop.",
            "mr": "पानांवर लहान, काळे-तपकिरी रंगाचे तेलकट डाग पडतात व डागांभोवती पिवळी कडा दिसते. गंभीर अवस्थेत पाने करपून गळतात.",
            "hi": "पत्तियों पर छोटे, गहरे भूरे या काले, जलसिक्त धब्बे बनते हैं जिनके चारों ओर पीला छल्ला होता है। बाद में पत्तियां सूखकर गिर जाती हैं।"
        },
        "causes": {
            "en": "Seed-borne or rain-splash bacterial inoculum penetrating stomata or micro-wounds created by wind, sand, or mechanical pruning.",
            "mr": "दूषित बियाणे, पावसाच्या पाण्याचे शिंतोडे आणि हवेतील अति ओलाव्यामुळे सूक्ष्म जखमांमधून जीवाणूंचा शिरकाव होतो.",
            "hi": "संक्रमित बीज और वर्षा की फुहारों द्वारा जीवाणु पत्तियों के छिद्रों में प्रवेश करते हैं।"
        },
        "favourable_conditions": {
            "temperature_range_c": "24-30°C",
            "humidity_pct": "85-100%",
            "rainfall_trigger": "Frequent rain showers with high winds",
            "en": "High ambient temperature with frequent rainfall and relative humidity > 85%.",
            "mr": "उष्ण व दमट हवामान (२४ ते ३०° से.), सतत पाऊस आणि हवेतील आर्द्रता ८५% पेक्षा जास्त असणे.",
            "hi": "गर्म और आर्द्र मौसम, लगातार बारिश और उच्च नमी।"
        },
        "prevention_methods": {
            "en": [
                "Use hot-water treated or certified disease-free seeds (50°C for 25 minutes).",
                "Practice 2-3 year crop rotation with non-solanaceous crops (avoid chilli, brinjal, potato).",
                "Avoid overhead sprinkler irrigation; always use drip systems."
            ],
            "mr": [
                "प्रमाणित व प्रक्रिया केलेले बियाणे वापरा (गरम पाण्याच्या प्रक्रियेसह).",
                "सोलेनेसी कुळातील पिकांनंतर (वांगी, मिरची, बटाटा) टोमॅटोची लागवड टाळा.",
                "तुषार सिंचन टाळा, फक्त ठिबक सिंचनाचा वापर करा."
            ],
            "hi": [
                "रोगमुक्त बीजों का उपयोग करें।",
                "टमाटर के बाद बैंगन, मिर्च या आलू की फसल न लगाएं।",
                "फव्वारा सिंचाई से बचें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Sanitize pruning shears with 10% bleach between plants. Rogue out severely blighted plants and burn them.",
                "mr": "छाटणीची अवजारे जंतुनाशकाने स्वच्छ करा. अतिबाधित झाडे उपटून शेताबाहेर नष्ट करा.",
                "hi": "कटाई-छंटाई के औजारों को साफ रखें और गंभीर रूप से ग्रसित पौधों को नष्ट करें।"
            },
            "biological": {
                "en": "Foliar spray of Pseudomonas fluorescens @ 5g/L water at 10-day intervals as a preventive bio-bactericide.",
                "mr": "स्यूडोमोनास फ्ल्यूओरोसन्स ५ ग्रॅम/लिटर पाण्यात मिसळून १० दिवसांच्या अंतराने फवारा.",
                "hi": "स्यूडोमोनास फ्लोरेसेंस 5 ग्राम/लीटर का 10 दिन के अंतराल पर छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Copper Oxychloride 50% WP + Streptocycline (90:10)",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "Copper Oxychloride @ 2.5 g/L + Streptocycline @ 0.1 g/L (1g per 10 L water)",
                    "dilution": "500-750 L/ha water volume",
                    "application_method": "High-volume foliar canopy spray with hollow cone nozzle",
                    "phi_days": 15,
                    "statutory_note": f"Wait 15 days after spray before fruit picking. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Kasugamycin 3% SL",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.5 to 2.0 ml/L water",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Targeted foliar spray on appearance of initial bacterial spots",
                    "phi_days": 10,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 10 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "CIBRC Approved Pesticides Compendium",
                "organization": "Central Insecticide Board & Registration Committee, Faridabad",
                "citation": "Major Uses of Pesticides in Tomato 2024"
            },
            {
                "source_name": "ICAR-IIVR Tomato Pathology Handbook",
                "organization": "ICAR - Indian Institute of Vegetable Research, Varanasi",
                "citation": "Bacterial Diseases of Solanaceous Vegetables"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_early_blight",
        "crop_name": "tomato",
        "disease_name": "Tomato Early Blight",
        "scientific_name": "Alternaria solani",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Target-board or concentric ring lesions with dark brown margins, primarily originating on older lower leaves. Leaves turn yellow, wither, and drop prematurely, causing sunscald on fruits.",
            "mr": "पानांवर गोलाकार किंवा लंबगोलाकार एकाआड एक वलये (टार्गेट बोर्डसारखे चट्टे) दिसतात. प्रथम खालच्या पानांवर प्रादुर्भाव होऊन पाने पिवळी पडून करपतात.",
            "hi": "पुरानी निचली पत्तियों पर भूरे-काले छल्लेदार गोल धब्बे (टार्गेट बोर्ड जैसे) बनते हैं। पत्तियां पीली होकर सूखने लगती हैं।"
        },
        "causes": {
            "en": "Soil-borne fungal conidia splashed by rain or irrigation onto lower leaves, especially when plants are stressed by heavy fruit load or low nitrogen.",
            "mr": "मातीत जिवंत राहिलेले बुरशीचे बीजाणू पाण्याच्या शिंतोड्यांद्वारे खालच्या पानांवर पोहोचून रोगाचा फैलाव करतात.",
            "hi": "मिट्टी में मौजूद फफूंद पानी की बूंदों के साथ निचली पत्तियों पर चिपक कर संक्रमण फैलाती है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "24-30°C",
            "humidity_pct": "80-95%",
            "rainfall_trigger": "Alternating wet and dry periods with morning dew",
            "en": "Warm humid days alternating with dry sunny spells, prolonged leaf wetness > 6 hours.",
            "mr": "उष्ण व दमट हवामान, सकाळी पडणारे धुके आणि पानांवर ६ तासांपेक्षा जास्त वेळ राहिलेला ओलावा.",
            "hi": "गर्म दिन, सुबह का कोहरा और पत्तियों पर लगातार नमी।"
        },
        "prevention_methods": {
            "en": [
                "Stake plants securely to keep foliage well above soil level.",
                "Mulch with silver-black polyethylene film to prevent soil splash onto foliage.",
                "Prune the bottom 25-30 cm of foliage as plants mature to reduce humidity in the under-canopy."
            ],
            "mr": [
                "झाडांना योग्य आधार देऊन पाने जमिनीपासून वर ठेवा.",
                "मातीचे शिंतोडे पानांवर उडू नयेत म्हणून गादीवाफ्यावर प्लास्टिक मल्चिंगचा वापर करा.",
                "खालची पाने वेळोवेळी छाटून टाका जेणेकरून झाडात हवा खेळती राहील."
            ],
            "hi": [
                "पौधों को सहारा देकर जमीन से ऊपर रखें।",
                "मल्चिंग का प्रयोग करें और निचली पत्तियों को काटें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Collect and destroy all diseased crop residues after harvest. Deep summer ploughing to bury fungal resting structures.",
                "mr": "रोगट पाने व फांद्या गोळा करून नष्ट करा. उन्हाळ्यात खोल नांगरट करा.",
                "hi": "संक्रमित पत्तियों को जलाएं और गर्मियों में गहरी जुताई करें।"
            },
            "biological": {
                "en": "Foliar application of Trichoderma viride @ 4g/L water preventively prior to flowering.",
                "mr": "फुलोरा येण्यापूर्वी ट्रायकोडर्मा विरिडी ४ ग्रॅम/लिटर पाण्यात मिसळून प्रतिबंधात्मक फवारणी करा.",
                "hi": "ट्राइकोडर्मा 4 ग्राम/लीटर पानी में मिलाकर छिड़कें।"
            },
            "chemical": [
                {
                    "chemical_name": "Azoxystrobin 18.2% + Difenoconazole 11.4% SC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.0 ml/L water (500 ml/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Foliar spray at initial detection of concentric lesions",
                    "phi_days": 5,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 5 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Mancozeb 75% WP",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "2.0 to 2.5 g/L water",
                    "dilution": "500-750 L/ha water volume",
                    "application_method": "Protective contact foliar canopy spray",
                    "phi_days": 15,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 15 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "CIBRC Registered Fungicides List for Tomato",
                "organization": "Central Insecticide Board & Registration Committee",
                "citation": "Approved Package of Practices 2024"
            },
            {
                "source_name": "ICAR-IIHR Vegetable Pathology",
                "organization": "ICAR-IIHR Bengaluru",
                "citation": "Integrated Management of Tomato Early Blight"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_late_blight",
        "crop_name": "tomato",
        "disease_name": "Tomato Late Blight",
        "scientific_name": "Phytophthora infestans",
        "pathogen_type": "Oomycete / Water Mold",
        "symptoms": {
            "en": "Rapidly expanding water-soaked, dark greenish-black oily lesions on leaves and stems. Under humid conditions, delicate white fuzzy fungal growth appears on leaf undersides. Fruit develops greasy brown firm rot.",
            "mr": "पानांवर वेगाने पसरणारे काळसर-हिरवे पाणथळ डाग, पानाच्या मागील बाजूस पांढुरकी बुरशी दिसते. फळांवर काळपट-तपकिरी रंगाची कडक कूज होते.",
            "hi": "पत्तियों और तनों पर तेजी से फैलने वाले गीले, काले-भूरे धब्बे बनते हैं। नमी में पत्ती के नीचे सफेद फफूंद दिखती है।"
        },
        "causes": {
            "en": "Airborne sporangia of Phytophthora infestans transported by cool moist wind currents, initiating catastrophic blighting under continuous free moisture.",
            "mr": "थंड व ढगाळ हवामानात हवेद्वारे येणारे बुरशीचे बीजाणू पिकावर पडल्यास अवघ्या काही दिवसांत संपूर्ण शेत करपून जाते.",
            "hi": "हवा के जरिए फैलने वाले बीजाणु ठंडे और नम मौसम में तेजी से तबाही मचाते हैं।"
        },
        "favourable_conditions": {
            "temperature_range_c": "12-22°C",
            "humidity_pct": "90-100%",
            "rainfall_trigger": "Continuous drizzle, foggy cool weather, dew persistence > 8h",
            "en": "Cool temperatures (12-22°C), overcast skies, heavy fog/dew, and relative humidity exceeding 90%.",
            "mr": "थंड व ढगाळ हवामान (१२ ते २२° से.), रिमझिम पाऊस किंवा दाट धुके आणि आर्द्रता ९०% पेक्षा जास्त असणे.",
            "hi": "ठंडा व कोहरे वाला मौसम, लगातार रिमझिम बारिश और उच्च नमी।"
        },
        "prevention_methods": {
            "en": [
                "Plant late-blight tolerant hybrids (e.g. Arka Rakshak, Arka Abhed from ICAR-IIHR).",
                "Space rows adequately (min 1.2m between beds) to maximize sunlight penetration and foliage drying.",
                "Apply prophylactic spray of Mancozeb 75% WP @ 2.5g/L immediately upon forecast of cloudy, misty weather."
            ],
            "mr": [
                "रोगास प्रतिकारक्षम वाण (उदा. अर्का रक्षक, अर्का अभेद) ची निवड करा.",
                "झाडांमध्ये योग्य अंतर ठेवा जेणेकरून पानांमधील ओलावा लवकर सुकेल.",
                "ढगाळ व थंड हवामानाचा अंदाज येताच मॅन्कोझेब २.५ ग्रॅम/लिटरची प्रतिबंधात्मक फवारणी करा."
            ],
            "hi": [
                "रोग प्रतिरोधी किस्में लगाएं।",
                "उचित दूरी रखें और मौसम खराब होने पर तुरंत निवारक छिड़काव करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Immediately remove and deeply bury blighted plants. Do not compost late blight tissue.",
                "mr": "करपलेली झाडे तत्काळ उपटून खोल जमिनीत पुरा. शेतातील कचरा उघड्यावर टाकू नका.",
                "hi": "रोगग्रस्त पौधों को उखाड़कर गहरे गड्ढे में दबाएं।"
            },
            "biological": {
                "en": "Apply Bacillus subtilis formulation @ 5 ml/L water in early vegetative stages before disease outbreak.",
                "mr": "रोग येण्यापूर्वी बॅसिलस सबटिलिस ५ मिली/लिटर पाण्यात मिसळून फवारा.",
                "hi": "रोग के पहले बैसिलस सबटिलिस का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Dimethomorph 50% WP + Mancozeb 75% WP",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "Dimethomorph @ 1.0 g/L + Mancozeb @ 2.0 g/L",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Systemic + translaminar curative spray covering upper and lower leaf surfaces",
                    "phi_days": 10,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 10 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Cymoxanil 8% + Mancozeb 64% WP",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "2.0 g/L water (1.5 kg/ha)",
                    "dilution": "500-750 L/ha water volume",
                    "application_method": "High-volume curative foliar spray within 48 hours of infection onset",
                    "phi_days": 10,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 10 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIHR Late Blight Management Advisory",
                "organization": "ICAR-IIHR Bengaluru",
                "citation": "Epidemiology and Control of Phytophthora infestans in Tomato"
            },
            {
                "source_name": "CIBRC Pesticides Compendium",
                "organization": "CIBRC Govt of India",
                "citation": "Registered Fungicides for Solanaceous Crops"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_leaf_mold",
        "crop_name": "tomato",
        "disease_name": "Tomato Leaf Mold",
        "scientific_name": "Passalora fulva (syn. Cladosporium fulvum)",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Pale green or yellowish spots with indefinite margins on upper leaf surfaces; velvety olive-green to grayish-brown fungal sporulation covers the corresponding lower leaf surface. Severe cases cause defoliation.",
            "mr": "पानांच्या वरच्या भागावर फिकट पिवळसर डाग आणि पानाच्या खालच्या भागावर मखमली ऑलिव्ह-तपकिरी रंगाची बुरशी दिसते. पाने वाळून गळतात.",
            "hi": "पत्तियों की ऊपरी सतह पर हल्के पीले धब्बे और निचली सतह पर मखमली जैतूनी-भूरे रंग की फफूंद दिखाई देती है।"
        },
        "causes": {
            "en": "Airborne conidia in poorly ventilated greenhouse/polyhouse conditions or dense shaded open fields.",
            "mr": "पॉलीहाऊस किंवा शेडनेटमध्ये हवा खेळती नसणे व अति आर्द्रतेमुळे बुरशीचा प्रसार होतो.",
            "hi": "पॉलीहाउस या घनी फसल में हवा की कमी और अत्यधिक नमी से फफूंद पनपती है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "20-25°C",
            "humidity_pct": "85-100%",
            "rainfall_trigger": "High relative humidity in enclosed or dense canopies",
            "en": "High relative humidity (> 85%), stagnant air, and temperatures around 20-25°C.",
            "mr": "८५% पेक्षा जास्त आर्द्रता, बंदिस्त वातावरण आणि २० ते २५° से. तापमान.",
            "hi": "85% से अधिक नमी और बंद वातावरण।"
        },
        "prevention_methods": {
            "en": [
                "Increase greenhouse ventilation by operating side curtains and exhaust fans.",
                "Prune lower suckers to open canopy to moving air.",
                "Avoid late evening irrigation that keeps leaves wet throughout the night."
            ],
            "mr": [
                "पॉलीहाऊसचे पडदे उघडून हवा खेळती ठेवा.",
                "झाडांची अनावश्यक पाने छाटून सूर्यप्रकाश खालपर्यंत पोहोचू द्या.",
                "संध्याकाळी उशिरा पाणी देणे टाळा जेणेकरून रात्रभर पानांवर ओलावा राहणार नाही."
            ],
            "hi": [
                "हवा का संचार बढ़ाएं और निचली पत्तियों की छंटाई करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Sterilize greenhouse stakes and trellis twine after every crop cycle. Rogue infected leaves at first sign.",
                "mr": "हंगामाच्या शेवटी बांबू आणि सुतळी निर्जंतुक करा. लक्षणे दिसणारी पाने तोडून नष्ट करा.",
                "hi": "संक्रमित पत्तियों को तुरंत हटा दें।"
            },
            "biological": {
                "en": "Spray Ampelomyces quisqualis or Trichoderma viride @ 5g/L water preventively.",
                "mr": "ट्रायकोडर्मा विरिडी ५ ग्रॅम/लिटर पाण्यात मिसळून फवारा.",
                "hi": "ट्राइकोडर्मा 5 ग्राम/लीटर का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Chlorothalonil 75% WP",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "2.0 g/L water",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Thorough foliar spray ensuring lower leaf underside coverage",
                    "phi_days": 7,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 7 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Difenoconazole 25% EC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "0.5 ml/L water",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Targeted systemic spray on initial symptom appearance",
                    "phi_days": 7,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 7 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIHR Protected Cultivation Manual",
                "organization": "ICAR-IIHR Bengaluru",
                "citation": "Disease Management in Polyhouse Tomato"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_mosaic_virus",
        "crop_name": "tomato",
        "disease_name": "Tomato Mosaic Virus (ToMV)",
        "scientific_name": "Tomato mosaic tobamovirus (ToMV)",
        "pathogen_type": "Viral",
        "symptoms": {
            "en": "Alternating light and dark green mosaic patterns on leaves, leaflet puckering, distortion, fern-like leaf narrowing, and stunted bushy growth. Fruits exhibit internal brown necrosis.",
            "mr": "पानांवर फिकट व गर्द हिरवे चट्टे (मोझॅक), पाने आकसणे, सुरकुतणे किंवा पापुद्र्यासारखी बारीक होणे, झाडांची वाढ खुंटणे.",
            "hi": "पत्तियों पर गहरे व हल्के हरे चित्तीदार चकत्ते (मोज़ेक), पत्तियों का सिकुड़ना और पौधों का बौना होना।"
        },
        "causes": {
            "en": "Highly stable Tobamovirus transmitted mechanically via hands, tools, grafting shears, clothing, and infected seed coats. No common insect vector.",
            "mr": "हा विषाणू माणसांचे हात, शेतीची अवजारे, कपडे आणि दूषित बियाण्यांमधून यांत्रिक पद्धतीने पसरतो.",
            "hi": "यह वायरस हाथों, औजारों और संक्रमित बीज द्वारा फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "22-30°C",
            "humidity_pct": "Variable",
            "rainfall_trigger": "Mechanical handling during pruning and staking",
            "en": "Frequent manual plant handling during pruning, suckering, and trellising under warm conditions.",
            "mr": "उष्ण हवामानात झाडांची जास्त हाताळणी व छाटणी करताना विषाणूचा वेगाने प्रसार होतो.",
            "hi": "गर्म मौसम में अधिक कटाई-छंटाई और पौधों को छूने से फैलाव।"
        },
        "prevention_methods": {
            "en": [
                "Soak seeds in 10% Trisodium Phosphate (TSP) solution for 30 minutes to inactivate coat-borne virus.",
                "Wash hands thoroughly with soap/skimmed milk (20%) before and during pruning operations.",
                "Prohibit tobacco smoking/chewing in tomato fields as tobacco contains cross-infecting TMV/ToMV."
            ],
            "mr": [
                "बियाण्यांवर ट्रायसोडियम फॉस्फेटची प्रक्रिया करा.",
                "झाडांची छाटणी करताना हात साबणाने किंवा दुधाच्या द्रावणाने वारंवार धुवा.",
                "टोमॅटोच्या शेतात विडी, सिगारेट किंवा तंबाखूचा वापर पूर्णपणे बंद ठेवा."
            ],
            "hi": [
                "बीज को उपचारित करें।",
                "औजारों को साबुन से धोएं और खेत में तंबाकू/बीड़ी का प्रयोग न करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Rogue out infected plants immediately into plastic bags and burn them away from the field. Do not prune healthy plants with tools that touched infected sap.",
                "mr": "बाधित झाडे मुळासकट उपटून प्लास्टिक पिशवीत भरा आणि शेताबाहेर जाळून नष्ट करा.",
                "hi": "संक्रमित पौधों को उखाड़कर खेत से दूर जला दें।"
            },
            "biological": {
                "en": "Spray skimmed milk solution (100 ml/L water) on healthy plants prior to pruning to act as a viral transmission barrier.",
                "mr": "छाटणीपूर्वी गाईचे किंवा म्हशीचे दूध (१०० मिली/लिटर पाणी) पानांवर फवारल्यास विषाणूचा प्रसार रोखण्यास मदत होते.",
                "hi": "छांटने से पहले दूध का घोल (100 मिली/लीटर) छिड़कें।"
            },
            "chemical": []  # Zero chemical viricides exist. Statutory suppression enforced.
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIVR Solanaceous Viral Diseases Bulletin",
                "organization": "ICAR - Indian Institute of Vegetable Research",
                "citation": "Mechanically Transmitted Viruses in Tomato"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_septoria_leaf_spot",
        "crop_name": "tomato",
        "disease_name": "Tomato Septoria Leaf Spot",
        "scientific_name": "Septoria lycopersici",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Numerous small, circular spots (1.5-3mm) with dark brown margins and sunken grayish-white centers dotted with tiny black pycnidia (fruiting bodies). Begins on lowest leaves and progresses upward.",
            "mr": "पानांवर लहान, गोलाकार (१.५-३ मिमी) डाग पडतात ज्यांची कडा गडद तपकिरी व मध्यभाग राखाडी-पांढुरका असतो. मध्यभागात बारीक काळे ठिपके (बुरशीचे बीजाणू) दिसतात.",
            "hi": "पत्तियों पर छोटे, गोल धब्बे जिनके किनारे गहरे भूरे और बीच का हिस्सा धूसर-सफेद होता है। बीच में काले बारीक बिंदु दिखते हैं।"
        },
        "causes": {
            "en": "Fungal pycnidia overwintering on diseased solanaceous weeds (e.g. Solanum nigrum) splashed by rain drops onto low-hanging foliage.",
            "mr": "बांधावरील तणांवर राहणारी बुरशी पावसाच्या पाण्यामुळे खालच्या पानांवर उडून रोगाची सुरुवात करते.",
            "hi": "बारिश की बूंदों से फफूंद के बीजाणु निचली पत्तियों तक पहुंचते हैं।"
        },
        "favourable_conditions": {
            "temperature_range_c": "20-25°C",
            "humidity_pct": "85-100%",
            "rainfall_trigger": "Prolonged rainfall with overcast days",
            "en": "Warm, wet weather with frequent rainfall and extended periods of high leaf moisture.",
            "mr": "२० ते २५° से. तापमान, सततचा पाऊस आणि पानांवर दीर्घकाळ राहणारा ओलावा.",
            "hi": "हल्की गर्मी, लगातार बारिश और नमी।"
        },
        "prevention_methods": {
            "en": [
                "Eradicate nightshade and solanaceous weeds along field perimeter.",
                "Do not work in tomato fields when leaves are wet to prevent spreading sticky pycnidiospores.",
                "Apply bottom mulch (straw or plastic) and stake vines."
            ],
            "mr": [
                "शेताच्या बांधावरील कांगणी व इतर तणे नष्ट करा.",
                "पाने ओली असताना शेतात काम करू नका, कारण यामुळे बुरशी हाताला लागून पसरते.",
                "झाडांना आधार द्या आणि वाफ्यावर आच्छादन करा."
            ],
            "hi": [
                "गीली पत्तियों पर काम न करें और खरपतवार नष्ट करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Strip and bag lower infected leaves before the fungus climbs into the upper fruit canopy.",
                "mr": "रोगट झालेली खालची पाने तोडून पिशवीत भरून नष्ट करा.",
                "hi": "निचली बीमार पत्तियों को तोड़कर नष्ट करें।"
            },
            "biological": {
                "en": "Spray Pseudomonas fluorescens @ 5g/L water at first appearance of spots.",
                "mr": "स्यूडोमोनास फ्ल्यूओरोसन्स ५ ग्रॅम/लिटर पाण्यात मिसळून फवारा.",
                "hi": "स्यूडोमोनास फ्लोरेसेंस 5 ग्राम/लीटर का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Chlorothalonil 75% WP",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "2.0 g/L water (1.0 kg/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Preventive canopy cover spray before disease ascends upward",
                    "phi_days": 7,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 7 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Tebuconazole 25.9% EC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.0 ml/L water (500 ml/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Curative systemic spray on lower foliage",
                    "phi_days": 5,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 5 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "TNAU Agritech Portal Tomato Disease Guide",
                "organization": "Tamil Nadu Agricultural University",
                "citation": "Septoria Leaf Spot Diagnostics and Management"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_spider_mites",
        "crop_name": "tomato",
        "disease_name": "Two-Spotted Spider Mites",
        "scientific_name": "Tetranychus urticae",
        "pathogen_type": "Acari / Pest",
        "symptoms": {
            "en": "Fine pale-yellow stippling/speckling on upper leaf surfaces. As infestation advances, leaves become bronze, chlorotic, and dry out. Fine silken webbing covers leaf undersides and terminal shoots.",
            "mr": "पानांच्या वरच्या भागावर बारीक पिवळसर ठिपके दिसतात. प्रादुर्भाव वाढल्यास पाने तांबूस-तपकिरी होऊन वाळतात. पानांच्या खाली व शेंड्यांवर बारीक कोळ्यांचे जाळे दिसते.",
            "hi": "पत्तियों पर बारीक पीले बिंदु बनते हैं। बाद में पत्तियां कांस्य रंग की होकर सूखने लगती हैं और जाले दिखाई देते हैं।"
        },
        "causes": {
            "en": "Microscopic phytophagous acari (mites) feeding on plant sap by piercing epidermal cell walls under hot, dry microclimates.",
            "mr": "अति उष्ण व कोरड्या हवामानात लाल कोळी पानातून रस शोषून घेतात आणि स्वतःच्या संरक्षणासाठी जाळे विणतात.",
            "hi": "गर्म और शुष्क मौसम में लाल मकड़ी पत्तियों का रस चूसती है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "30-38°C",
            "humidity_pct": "30-55%",
            "rainfall_trigger": "Drought stress, hot winds, absence of rain",
            "en": "Hot, dry conditions (> 30°C), low relative humidity (< 50%), and dusty farm roadways.",
            "mr": "उष्ण व कोरडे हवामान (३०° से. पेक्षा जास्त), कमी आर्द्रता आणि शेतातील धुळीचे वातावरण.",
            "hi": "तेज धूप, सूखा और गर्म हवाएं।"
        },
        "prevention_methods": {
            "en": [
                "Maintain adequate irrigation; water-stressed tomato vines are heavily favored by spider mites.",
                "Sprinkle water on field borders and roadways to minimize dust accumulation on foliage.",
                "Conserve natural predators such as predatory mites (Phytoseiidae) and ladybird beetles."
            ],
            "mr": [
                "पिकाला पाण्याचा ताण पडू देऊ नका.",
                "धुळीमुळे कोळ्यांची वाढ वेगाने होते, म्हणून रस्त्यालगतच्या झाडांवर पाण्याचे तुषार मारा.",
                "नैसर्गिक मित्रकिडींचे (लेडीबर्ड बीटल) संरक्षण करा."
            ],
            "hi": [
                "पानी का तनाव न होने दें और धूल से पौधों को बचाएं।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "High-pressure plain water jet sprays onto leaf undersides to dislodge mites and destroy webs.",
                "mr": "पाण्याचा जोरदार फवारा पानांच्या खालील बाजूवर मारून कोळ्यांचे जाळे नष्ट करा.",
                "hi": "पत्तियों के नीचे पानी का तेज फव्वारा मारकर जाले हटाएं।"
            },
            "biological": {
                "en": "Foliar spray of Neem Oil (Azadirachtin 10,000 ppm) @ 2 ml/L water or release Phytoseiulus persimilis predatory mites.",
                "mr": "निमतेल (१०,००० पीपीएम) २ मिली/लिटर पाण्यात मिसळून फवारा.",
                "hi": "नीम का तेल (10,000 ppm) 2 मिली/लीटर छिड़कें।"
            },
            "chemical": [
                {
                    "chemical_name": "Spiromesifen 22.9% SC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.0 ml/L water (500 ml/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Targeted acaricide spray directed thoroughly at leaf undersides",
                    "phi_days": 3,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 3 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Propargite 57% EC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "2.0 ml/L water",
                    "dilution": "500-750 L/ha water volume",
                    "application_method": "Foliar spray under heavy mite pressure",
                    "phi_days": 7,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 7 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIHR Acarology Guide",
                "organization": "ICAR-IIHR Bengaluru",
                "citation": "Integrated Mite Management in Solanaceous Crops"
            },
            {
                "source_name": "CIBRC Acaricides Compendium",
                "organization": "CIBRC Govt of India",
                "citation": "Approved Acaricides for Tomato"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_target_spot",
        "crop_name": "tomato",
        "disease_name": "Tomato Target Spot",
        "scientific_name": "Corynespora cassiicola",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Small, pinpoint brown spots that expand into circular lesions with light brown centers and dark brown concentric margins, resembling targets. Lesions coalesce causing severe foliar necrosis.",
            "mr": "पानांवर सुरुवातीला लहान ठिपके आणि नंतर गोलाकार एकाआड एक वलयांचे चट्टे दिसतात. अनेक चट्टे एकत्र येऊन संपूर्ण पान करपून गळते.",
            "hi": "पत्तियों पर भूरे गोल धब्बे बनते हैं जिनके केंद्र हल्के भूरे होते हैं। बाद में पूरी पत्ती सूख जाती है।"
        },
        "causes": {
            "en": "Fungal conidia surviving on crop debris, weeds, and alternative hosts under warm humid conditions with poor canopy aeration.",
            "mr": "हवेतील अति आर्द्रता आणि शेतातील अस्वच्छतेमुळे जुन्या पिकाच्या अवशेषांवरून बुरशीचा प्रसार होतो.",
            "hi": "हवा में नमी और पुराने फसल अवशेषों से संक्रमण फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "25-32°C",
            "humidity_pct": "80-95%",
            "rainfall_trigger": "Intermittent showers with warm humid nights",
            "en": "Warm temperatures (25-32°C), long periods of leaf wetness (> 12 hours), and relative humidity > 80%.",
            "mr": "उष्ण व दमट हवामान (२५ ते ३२° से.), पाऊस आणि रात्री पानांवर दीर्घकाळ ओलावा राहणे.",
            "hi": "गर्म और नम मौसम, पत्तियों पर 12 घंटे से अधिक गीलापन।"
        },
        "prevention_methods": {
            "en": [
                "Increase row spacing to improve air flow and speed foliage drying.",
                "Avoid overhead irrigation; use drip lines positioned beneath mulch.",
                "Rotate with non-host grass or cereal crops for 2 years."
            ],
            "mr": [
                "दोन ओळींमध्ये योग्य अंतर ठेवून हवा खेळती ठेवा.",
                "ठिबक सिंचनाचा वापर करा, वरून पाणी देणे टाळा.",
                "ज्वारी, बाजरी किंवा मका यांसारख्या तृणधान्य पिकांची फेरपालट करा."
            ],
            "hi": [
                "हवा का संचार बढ़ाएं और ड्रिप सिंचाई का प्रयोग करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Rogue severely diseased lower branches. Burn or bury infected crop residue immediately after season end.",
                "mr": "रोगट फांद्या तोडून नष्ट करा आणि हंगाम संपल्यावर शेताची स्वच्छता करा.",
                "hi": "संक्रमित शाखाओं को काटें और फसल अवशेष जलाएं।"
            },
            "biological": {
                "en": "Apply Trichoderma harzianum @ 5g/L water preventively.",
                "mr": "ट्रायकोडर्मा हरझियानम ५ ग्रॅम/लिटर पाण्यात मिसळून फवारा.",
                "hi": "ट्राइकोडर्मा 5 ग्राम/लीटर का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Azoxystrobin 23% SC",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.0 ml/L water (500 ml/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Foliar canopy spray at initial detection of spots",
                    "phi_days": 3,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 3 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Pyraclostrobin 20% WG",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.0 g/L water",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Systemic protective spray",
                    "phi_days": 5,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 5 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIVR Vegetable Diseases Compendium",
                "organization": "ICAR-IIVR Varanasi",
                "citation": "Target Spot Management in Open Field and Polyhouse"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    },
    {
        "disease_id": "tomato_yellow_leaf_curl_virus",
        "crop_name": "tomato",
        "disease_name": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "scientific_name": "Tomato yellow leaf curl begomovirus (TYLCV)",
        "pathogen_type": "Viral",
        "symptoms": {
            "en": "Severe upward cupping, puckering, and yellowing (chlorosis) of leaflet margins; extreme reduction in leaf size, pronounced internode shortening giving a bushy appearance, and complete flower drop with zero fruit set.",
            "mr": "पाने वरच्या दिशेने वाटीसारखी वळतात (पानगळ / चुरडा-मुरडा), पानांची कडा पिवळी पडते, पानांचा आकार खूप लहान होतो, झाडांची वाढ खुंटून झाड झुडपासारखे दिसते आणि फुले गळून फळे लागत नाहीत.",
            "hi": "पत्तियां ऊपर की ओर मुड़कर कटोरी जैसी हो जाती हैं (चुरड़ा-मुरड़ा), पत्तियां छोटी व पीली पड़ जाती हैं और फूल गिर जाते हैं।"
        },
        "causes": {
            "en": "Geminivirus transmitted persistently by the silverleaf whitefly (Bemisia tabaci). Not seed-transmitted or mechanically transmitted.",
            "mr": "पांढऱ्या माशीद्वारे (बेमिसिया टॅबॅसी) या विषाणूचा एका झाडावरून दुसऱ्या झाडावर वेगाने प्रसार होतो.",
            "hi": "सफेद मक्खी (व्हाइटफ्लाई) द्वारा यह घातक वायरस फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "28-38°C",
            "humidity_pct": "40-65%",
            "rainfall_trigger": "Prolonged dry hot spells favoring whitefly multiplication",
            "en": "Hot, dry conditions favoring whitefly population explosions; presence of alternative weed hosts like Datura.",
            "mr": "उष्ण व कोरडे हवामान ज्यामध्ये पांढऱ्या माशीची झपाट्याने पैदास होते, तसेच शेताभोवतालची तणे.",
            "hi": "गर्म और शुष्क मौसम जिसमें सफेद मक्खी तेजी से बढ़ती है।"
        },
        "prevention_methods": {
            "en": [
                "Grow TYLCV-resistant hybrids (e.g. Arka Rakshak, Arka Samrat, US-440).",
                "Cover nursery seedlings with 40-50 mesh insect-proof nylon net to prevent early viruliferous whitefly feeding.",
                "Erect border rows of tall non-host barrier crops (maize, sorghum, or pearl millet, 3-4 rows) 30 days before transplanting.",
                "Install yellow sticky traps @ 25-30 traps/acre."
            ],
            "mr": [
                "प्रतिकारक्षम वाण (उदा. अर्का रक्षक, अर्का सम्राट) ची लागवड करा.",
                "रोपवाटिकेत ४० ते ५० मेशच्या मच्छरदाणीचा (नायलॉन नेट) वापर करून पांढरी माशी रोपांवर बसू देऊ नका.",
                "शेताभोवती मका किंवा ज्वारीच्या ३-४ ओळींचे संरक्षक कुंपण लावा.",
                "एकरी २५ ते ३० पिवळे चिकट सापळे लावा."
            ],
            "hi": [
                "रोग प्रतिरोधी किस्में लगाएं।",
                "नर्सरी को 40-मेश जाली से ढकें।",
                "खेत के चारों ओर मक्के या ज्वार की 3-4 कतारें लगाएं।",
                "पीले चिपचिपे ट्रैप लगाएं।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Rogue out infected plants immediately within the first 30 days of transplanting and burn them. Destroy solanaceous weeds.",
                "mr": "लागवडीनंतर पहिल्या ३० दिवसांत रोगट झाडे दिसताच मुळासकट उपटून नष्ट करा.",
                "hi": "शुरुआती 30 दिनों में ग्रसित पौधों को तुरंत उखाड़कर नष्ट करें।"
            },
            "biological": {
                "en": "Foliar spray of Lecanicillium lecanii (Verticillium lecanii) @ 5g/L water targeting whitefly nymphs, or 5% Neem Seed Kernel Extract (NSKE).",
                "mr": "पांढऱ्या माशीच्या पिल्लांच्या नियंत्रणासाठी व्हर्टिसिलियम लेकॅनी ५ ग्रॅम/लिटर किंवा ५% निंबोळी अर्क फवारा.",
                "hi": "वर्टिसिलियम लेकेनी 5 ग्राम/लीटर या नीम का काढ़ा छिड़कें।"
            },
            "chemical": [
                {
                    "chemical_name": "Diafenthiuron 50% WP (Targeting Whitefly Vector)",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.2 g/L water (600 g/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "High-volume foliar spray directed thoroughly at leaf undersides where whitefly adults and nymphs shelter",
                    "phi_days": 5,
                    "statutory_note": f"Targeting insect vector only; chemicals cannot cure viral infections. Pre-Harvest Interval: 5 days. {PPE_NOTICE_EN}"
                },
                {
                    "chemical_name": "Cyantraniliprole 10.26% OD",
                    "cibrc_status": "Registered / Approved",
                    "dosage": "1.8 ml/L water (900 ml/ha)",
                    "dilution": "500 L/ha water volume",
                    "application_method": "Foliar spray for early vector suppression",
                    "phi_days": 3,
                    "statutory_note": f"Pre-Harvest Interval (PHI): 3 days. {PPE_NOTICE_EN}"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-IIHR Begomovirus Management Guidelines",
                "organization": "ICAR-IIHR Bengaluru",
                "citation": "Whitefly Vector Management in Protected and Open Cultivation"
            },
            {
                "source_name": "CIBRC Insecticide Compendium",
                "organization": "CIBRC Ministry of Agriculture Govt of India",
                "citation": "Approved Insecticides for Whitefly Control in Tomato"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-06"
    }
]


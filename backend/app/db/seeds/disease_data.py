"""
PikVaidya AI — Verified Agricultural Disease Seed Knowledge Data
================================================================
Authoritative pathology records for sugarcane categories:
  1. Healthy (Healthy Foliage)
  2. Mosaic (Sugarcane mosaic virus - SCMV)
  3. Red Rot (Colletotrichum falcatum)
  4. Common Rust (Puccinia melanocephala)
  5. Yellow Leaf Disease (Sugarcane yellow leaf virus - SCYLV)

Authoritative Agricultural Sources:
  - ICAR - Sugarcane Breeding Institute (SBI, Coimbatore)
  - Central Insecticide Board & Registration Committee (CIBRC, Govt. of India)
  - Mahatma Phule Krishi Vidyapeeth (MPKV, Rahuri)
  - ICAR - Indian Institute of Sugarcane Research (IISR, Lucknow)
  - Tamil Nadu Agricultural University (TNAU) Agritech Portal
"""

from typing import List, Dict, Any

SUGARCANE_DISEASE_SEEDS: List[Dict[str, Any]] = [
    {
        "disease_id": "sugarcane_healthy",
        "crop_name": "sugarcane",
        "disease_name": "Healthy Foliage",
        "scientific_name": "Saccharum officinarum (Healthy)",
        "pathogen_type": "None",
        "symptoms": {
            "en": "Foliage exhibits uniform dark green coloration, vibrant turgidity, clean leaf margins, and absence of chlorotic lesions, necrotic spotting, or pustules.",
            "mr": "पानांचा रंग एकसारखा गर्द हिरवा, पाने ताजी व तजेलदार, पानांवर कोणतेही पिवळे-तांबडे ठिपके किंवा पुटकुळ्या नाहीत.",
            "hi": "पत्तियां पूरी तरह से हरी, स्वस्थ और चमकदार हैं। किसी प्रकार के धब्बे, फफूंद या सड़न के लक्षण नहीं हैं।"
        },
        "causes": {
            "en": "Balanced agronomic nutrition, clean certified seed setts, optimal irrigation scheduling, and absence of biotic pathogen stress.",
            "mr": "संतुलित खत व्यवस्थापन, प्रमाणित बेणे, वेळेवर पाणी व्यवस्थापन आणि रोगांचा प्रादुर्भाव नसणे.",
            "hi": "संतुलित पोषक तत्व, रोगमुक्त बीज और उचित जल प्रबंधन।"
        },
        "favourable_conditions": {
            "temperature_range_c": "25-35°C",
            "humidity_pct": "60-75%",
            "rainfall_trigger": "Adequate seasonal moisture",
            "en": "Adequate sunlight, well-drained loamy soil with pH 6.5-7.5, and balanced NPK nutrition.",
            "mr": "भरपूर सूर्यप्रकाश, पाण्याचा चांगला निचरा होणारी जमीन आणि वेळेवर आंतरमशागत.",
            "hi": "उचित धूप, जल निकासी वाली उपजाऊ भूमि और संतुलित उर्वरक।"
        },
        "prevention_methods": {
            "en": [
                "Maintain integrated pest and disease surveillance every 15 days.",
                "Apply balanced NPK fertilizer according to soil test recommendations (e.g. 250:115:115 kg/ha in Maharashtra).",
                "Ensure proper earthing-up at 90 and 120 days after planting to prevent lodging.",
                "Adopt drip irrigation to prevent excess moisture accumulation around roots."
            ],
            "mr": [
                "दर १५ दिवसांनी शेताची पाहणी करा.",
                "माती परीक्षणानुसार संतुलित रासायनिक व सेंद्रिय खतांचा वापर करा (उदा. २५०:११५:११५ किलो नत्र, स्फुरद, पालाश प्रति हेक्टरी).",
                "लागवडीनंतर ९० व १२० दिवसांनी उसाला योग्य भर द्या.",
                "पाण्याचा अपव्यय टाळण्यासाठी आणि मुळांजवळ जास्त ओलावा राहू नये म्हणून ठिबक सिंचनाचा वापर करा."
            ],
            "hi": [
                "हर 15 दिन में फसल का नियमित निरीक्षण करें।",
                "मृदा परीक्षण के आधार पर संतुलित उर्वरक दें।",
                "गन्ने में समय पर मिट्टी चढ़ाएं।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Continue routine intercultural operations, weed-free cultivation, and trash mulching for soil moisture conservation.",
                "mr": "तणमुक्त शेती ठेवा, उसाच्या पाचटाचे आच्छादन करून जमिनीतील ओलावा टिकवून ठेवा.",
                "hi": "नियमित निराई-गुड़ाई करें और नमी बनाए रखने के लिए सूखी पत्तियों की मल्चिंग करें।"
            },
            "biological": {
                "en": "Incorporate bio-fertilizers: Azotobacter @ 5 kg/ha and Phosphate Solubilizing Bacteria (PSB) @ 5 kg/ha with Farm Yard Manure (FYM).",
                "mr": "अॅझोटोबॅक्टर ५ किलो/हेक्टर आणि पीएसबी ५ किलो/हेक्टर शेणखतात मिसळून द्यावे.",
                "hi": "एजोटोबैक्टर और पीएसबी जैव उर्वरक का उपयोग करें।"
            },
            "chemical": []  # No chemical application required for healthy crops
        },
        "reference_sources": [
            {
                "source_name": "ICAR-SBI Sugarcane Package of Practices",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "SBI Agronomy Technical Bulletin No. 42"
            },
            {
                "source_name": "MPKV Rahuri Krishi Darshani",
                "organization": "Mahatma Phule Krishi Vidyapeeth, Rahuri",
                "citation": "Sugarcane Production Technology Manual 2024"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-01"
    },
    {
        "disease_id": "sugarcane_mosaic",
        "crop_name": "sugarcane",
        "disease_name": "Sugarcane Mosaic",
        "scientific_name": "Sugarcane mosaic virus (SCMV)",
        "pathogen_type": "Viral",
        "symptoms": {
            "en": "Distinct alternating irregular patterns of dark green and pale yellow-green chlorotic patches or stripes on the leaf blade, most conspicuous on younger leaves. Leaf bases show patchy mottling. Stunting occurs in severe cases.",
            "mr": "तरुण पानांवर गडद हिरव्या आणि फिकट पिवळसर-हिरव्या रंगाचे अनियमित पट्टे किंवा ठिपके दिसणे. रोगाची तीव्रता वाढल्यास झाडांची वाढ खुंटते.",
            "hi": "नई पत्तियों पर गहरे हरे और हल्के पीले-हरे रंग के अनियमित धब्बे या धारियां दिखाई देती हैं। पौधों का विकास रुक जाता है।"
        },
        "causes": {
            "en": "Infection caused by Sugarcane Mosaic Potyvirus (SCMV), primarily transmitted by aphid vectors (Rhopalosiphum maidis and Melanaphis sacchari) in a non-persistent manner and perpetuated through vegetative seed setts.",
            "mr": "हा विषाणूजन्य रोग असून उसावरील मावा किडीद्वारे (एफिड्स) एका झाडावरून दुसऱ्या झाडावर पसरतो. बाधित उसाचे बेणे वापरल्याने प्रसार वेगाने होतो.",
            "hi": "यह वायरस एफिड कीटों (माहू) द्वारा और संक्रमित बीज के प्रयोग से फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "24-32°C",
            "humidity_pct": "60-80%",
            "rainfall_trigger": "Pre-monsoon and post-monsoon dry-warm spells with high aphid populations",
            "en": "Warm humid conditions promoting active flight of aphid vectors, presence of alternate grass hosts, and continuous monocropping.",
            "mr": "उबदार व दमट हवामान, मावा किडींची जास्त संख्या आणि शेतात गवत किंवा पर्यायी तणांचे अस्तित्व.",
            "hi": "गर्म और आर्द्र मौसम, माहू कीटों की अधिकता और खेत में खरपतवार का होना।"
        },
        "prevention_methods": {
            "en": [
                "Plant disease-free seed setts sourced from certified tissue culture nurseries.",
                "Subject seed cane to Aerated Steam Therapy (AST) at 54°C for 2.5 hours or hot water treatment at 50°C for 2 hours.",
                "Eradicate alternate grass hosts (e.g. Sorghum halepense, Cynodon dactylon) on field bunds.",
                "Plant mosaic-resistant sugarcane cultivars recommended for the agro-climatic zone."
            ],
            "mr": [
                "नेहमी रोगमुक्त आणि प्रमाणित बेणेमळ्यातील बेणे वापरावे.",
                "लागवडीपूर्वी बेण्यावर उष्ण हवेची प्रक्रिया (५४ अंश सेल्सिअस, २.५ तास) किंवा गरम पाण्याची प्रक्रिया (५० अंश सेल्सिअस, २ तास) करावी.",
                "बांधावरील गवताळ तणे नष्ट करावीत कारण विषाणू तणांवर जिवंत राहतो.",
                "रोगप्रतिकारक उसाच्या जातींची लागवड करावी."
            ],
            "hi": [
                "प्रमाणित नर्सरी से रोगमुक्त बीज गन्ने का चयन करें।",
                "बुवाई से पहले बीज का गर्म पानी से उपचार करें।",
                "खेत की मेड़ों से खरपतवार नष्ट करें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Rogue out infected clumps at the early stage of occurrence (within 30-45 days of germination) and bury or burn outside the field. Avoid taking ratoon crop from severely affected fields.",
                "mr": "लागवडीनंतर ३० ते ४५ दिवसांत बाधित दिसणारी रोपे मुळासकट उपटून नष्ट करावीत. जास्त प्रादुर्भाव असल्यास खोडवा ठेवू नये.",
                "hi": "संक्रमित पौधों को तुरंत उखाड़कर नष्ट कर दें। रोगग्रस्त खेत में पेड़ी की फसल न लें।"
            },
            "biological": {
                "en": "Conserve natural predators of aphids including ladybird beetles (Coccinella septempunctata) and green lacewings (Chrysoperla carnea). Spray Neem Seed Kernel Extract (NSKE) 5% to deter aphid colonization.",
                "mr": "मावा नियंत्रणासाठी ५% निंबोळी अर्क (५० मिली प्रति १० लीटर पाणी) फवारावा. लेडीबर्ड बीटल व क्रायसोपर्ला या मित्रकिटकांचे संवर्धन करावे.",
                "hi": "माहू के प्राकृतिक शत्रु कीटों का संरक्षण करें। 5% नीम के बीज का अर्क छिड़कें।"
            },
            "chemical": [
                {
                    "chemical_name": "Imidacloprid",
                    "formulation": "17.8% SL",
                    "dosage_per_liter": "0.3 ml/L",
                    "cibrc_approved": True,
                    "phi_days": 45,
                    "target": "Aphid vector control (Note: Direct viricides do not exist; chemical control targets insect vectors)"
                },
                {
                    "chemical_name": "Thiamethoxam",
                    "formulation": "25% WG",
                    "dosage_per_liter": "0.4 g/L",
                    "cibrc_approved": True,
                    "phi_days": 30,
                    "target": "Aphid vector control"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-SBI Pathology Monograph: Sugarcane Mosaic",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "ICAR-SBI Disease Bulletin No. 18"
            },
            {
                "source_name": "TNAU Agritech Portal: Sugarcane Crop Protection",
                "organization": "Tamil Nadu Agricultural University",
                "citation": "TNAU Plant Pathology Compendium"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-01"
    },
    {
        "disease_id": "sugarcane_red_rot",
        "crop_name": "sugarcane",
        "disease_name": "Red Rot",
        "scientific_name": "Colletotrichum falcatum Went (Glomerella tucumanensis)",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Known as the 'Cancer of Sugarcane'. The third or fourth leaf from top shows yellowing, withering, and drooping. Longitudinally split cane exhibits characteristic dull red internal tissue interspersed with transverse white patches. Spindle leaf mid-rib develops elongated dark red lesions with straw-colored centers. Distinct sour alcoholic odor in split canes.",
            "mr": "उसाचा 'कॅन्सर' मानला जातो. वरून तिसरे किंवा चौथे पान पिवळे पडून वाळू लागते. ऊस उभा चिरल्यास आत लाल रंग आणि पांढरे आडवे पट्टे दिसतात. पानांच्या मधल्या शिरेवर लालसर लांबट ठिपके पडतात. उसाला आंबट किंवा अल्कोहोलसारखा वास येतो.",
            "hi": "ऊपर से तीसरी या चौथी पत्ती सूखने लगती है। गन्ने को बीच से चीरने पर अंदर का गूदा लाल हो जाता है और उसमें सफेद आड़े धब्बे दिखाई देते हैं। गन्ने से शराब जैसी खट्टी गंध आती है।"
        },
        "causes": {
            "en": "Caused by the fungal pathogen Colletotrichum falcatum. Spores are primarily transmitted through infected seed setts, irrigation water channels, rainy splashes, and soil-borne fungal structures (dormant mycelium and chlamydospores).",
            "mr": "कोलेटोट्रिकम फालकॅटम या बुरशीमुळे होतो. रोगट बेणे, सिंचनाचे पाणी आणि पावसाच्या पाण्यामुळे या बुरशीचा प्रसार होतो.",
            "hi": "कोलेटोट्रिकम फाल्केटम नामक फफूंद से होता है। संक्रमित बीज और सिंचाई के पानी से तेजी से फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "26-32°C",
            "humidity_pct": "80-95%",
            "rainfall_trigger": "Continuous rainy days followed by water stagnation in poorly drained heavy soils",
            "en": "High relative humidity (>80%), waterlogging, continuous warm temperatures, and ill-drained soils with pH > 8.0.",
            "mr": "जास्त आर्द्रता (८०% पेक्षा जास्त), शेतात साचलेले पाणी, दमट हवामान आणि पाण्याचा निचरा नसलेली जमीन.",
            "hi": "अधिक नमी, जलभराव और 26-32 डिग्री सेल्सियस तापमान।"
        },
        "prevention_methods": {
            "en": [
                "Select seed setts exclusively from healthy, certified disease-free nursery plots.",
                "Dip setts before planting in Carbendazim 50% WP @ 1 g/L or Thiophanate-Methyl 70% WP @ 1 g/L for 15-20 minutes.",
                "Implement 2 to 3 years of crop rotation with non-host crops (paddy, legumes, green manure).",
                "Ensure strict drainage arrangements in the field to prevent stagnant water during monsoon.",
                "Plant red-rot resistant varieties recommended by ICAR-SBI (e.g. Co 86032, Co 0238 where resistant)."
            ],
            "mr": [
                "लागवडीसाठी निरोगी बेणेमळ्यातील बेणेच वापरावे.",
                "लागवडीपूर्वी बेणे कार्बेन्डाझिम ५०% डब्ल्यूपी (१ ग्रॅम प्रति लीटर पाणी) किंवा थायोफिनेट मिथाईल (१ ग्रॅम/लीटर) द्रावणात १५-२० मिनिटे बुडवून लावावे.",
                "बाधित शेतात २ ते ३ वर्षे उसाचे पीक न घेता भात किंवा कडधान्य पिकांची फेरपालट करावी.",
                "शेतात पावसाचे पाणी साचून राहणार नाही याची काळजी घ्यावी.",
                "को ८६०३२ सारख्या रोगप्रतिकारक जातींचा वापर करावा."
            ],
            "hi": [
                "रोगमुक्त बीज गन्ने का ही उपयोग करें।",
                "बुवाई से पहले कार्बेन्डाजिम (1 ग्राम/लीटर) के घोल में 15 मिनट तक बीज डुबोएं।",
                "2-3 साल तक फसल चक्र अपनाएं। खेत में जल निकासी की उचित व्यवस्था रखें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Rogue out completely and incinerate infected stools along with roots. Do not allow ratoon crop in red rot affected fields. Avoid furrow irrigation passing from diseased plots to healthy plots.",
                "mr": "बाधित उसाची बेटे मुळांसकट उपटून शेताबाहेर जाळून नष्ट करावीत. रोगट शेतात खोडवा ठेवू नये. एका शेतातून दुसऱ्या शेतात पाटाने पाणी देणे टाळावे.",
                "hi": "रोगग्रस्त पौधों को जड़ सहित उखाड़कर तुरंत जला दें। प्रभावित खेत में पेड़ी न रखें।"
            },
            "biological": {
                "en": "Sett treatment with Trichoderma viride or Trichoderma harzianum @ 10 g/L water, plus soil application of Trichoderma enriched in farmyard manure (FYM) @ 5 kg/ha at planting and earthing-up.",
                "mr": "लागवडीवेळी ट्रायकोडर्मा व्हिरिडी किंवा ट्रायकोडर्मा हरझियानम १० ग्रॅम प्रति लीटर पाण्यात बेणे प्रक्रिया करावी. तसेच ५ किलो ट्रायकोडर्मा १०० किलो शेणखतात मिसळून एकरी द्यावे.",
                "hi": "ट्राइकोडर्मा विरिडी (10 ग्राम/लीटर) से बीज उपचार करें और गोबर की खाद में मिलाकर खेत में डालें।"
            },
            "chemical": [
                {
                    "chemical_name": "Carbendazim",
                    "formulation": "50% WP",
                    "dosage_per_liter": "1.0 g/L (Sett Dip Treatment)",
                    "cibrc_approved": True,
                    "phi_days": 30,
                    "target": "Sett treatment before planting (Note: Foliar spraying is ineffective once internal stalk rot develops)"
                },
                {
                    "chemical_name": "Thiophanate-Methyl",
                    "formulation": "70% WP",
                    "dosage_per_liter": "1.0 g/L (Sett Dip Treatment)",
                    "cibrc_approved": True,
                    "phi_days": 35,
                    "target": "Sett treatment before planting"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-SBI Red Rot Advisory Protocol",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "SBI Technical Circular on Red Rot Management (R. Viswanathan et al.)"
            },
            {
                "source_name": "CIBRC Fungicide Compendium",
                "organization": "Central Insecticide Board & Registration Committee, Directorate of Plant Protection",
                "citation": "CIBRC Approved List of Pesticides for Sugarcane"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-01"
    },
    {
        "disease_id": "sugarcane_rust",
        "crop_name": "sugarcane",
        "disease_name": "Common Rust",
        "scientific_name": "Puccinia melanocephala Syd. & P. Syd.",
        "pathogen_type": "Fungal",
        "symptoms": {
            "en": "Initial symptoms are minute, elongated, chlorotic yellowish flecks on both leaf surfaces. Flecks enlarge into reddish-brown to dark brown pustules (uredinia) running parallel to leaf veins. As pustules mature, the leaf epidermis ruptures, exposing powdery orange-brown spores. Severe infection causes extensive leaf necrosis and premature drying.",
            "mr": "पानांच्या दोन्ही बाजूंवर लहान, लांबट, पिवळसर ठिपके पडतात. नंतर हे ठिपके मोठे होऊन तांबूस-तपकिरी रंगाच्या पुटकुळ्यांमध्ये (रस्ट) रूपांतरित होतात. बोट लावल्यास हाताला तांबडी पावडर लागते. पाने अकाली वाळून गळतात.",
            "hi": "पत्तियों की दोनों सतहों पर छोटे, पीले-भूरे धब्बे बनते हैं जो बाद में नारंगी-लाल रंग की फफोलेदार फुंसियों में बदल जाते हैं। हाथ लगाने पर उंगलियों पर गेरुए रंग का चूर्ण लग जाता है।"
        },
        "causes": {
            "en": "Caused by the obligate biotrophic fungus Puccinia melanocephala. Airborne urediniospores are carried over long distances by wind currents. Spores germinate in the presence of free moisture (dew drops or drizzle).",
            "mr": "पक्सिनिया मेलॅनोसिफाला या बुरशीमुळे हा रोग होतो. बुरशीचे बीजाणू वाऱ्यामार्फत वेगाने दूरवर पसरतात. पानांवर दव किंवा पाण्याचे थेंब असल्यास बुरशी वेगाने वाढते.",
            "hi": "पक्सीनिया मेलानोसेफाला फफूंद से होता है। इसके बीजाणु हवा द्वारा एक खेत से दूसरे खेत में फैलते हैं।"
        },
        "favourable_conditions": {
            "temperature_range_c": "20-28°C",
            "humidity_pct": "75-90%",
            "rainfall_trigger": "Cool night temperatures with heavy morning dew and overcast daytime skies",
            "en": "Moderate cool temperatures, high relative humidity, frequent dew formation, and dense canopies with poor air circulation.",
            "mr": "थंड व दमट हवामान (२०-२८ अंश सेल्सिअस), जास्त आर्द्रता आणि सकाळी पडणारे दाट दव.",
            "hi": "20-28 डिग्री सेल्सियस तापमान, अधिक नमी और सुबह का कोहरा/ओस।"
        },
        "prevention_methods": {
            "en": [
                "Avoid excessive nitrogenous fertilizer application which fosters dense, succulent, susceptible foliage.",
                "Ensure wider row spacing (e.g., 4 to 5 feet) for adequate sunlight penetration and aeration.",
                "Strip off and burn dried, severely infected bottom leaves to lower fungal inoculum load.",
                "Plant rust-tolerant sugarcane cultivars in rust-endemic pockets."
            ],
            "mr": [
                "युरिया किंवा नत्रयुक्त खतांचा अतिवापर टाळावा, कारण यामुळे पाने मऊ पडून रोगाला लवकर बळी पडतात.",
                "उसात मोकळी हवा आणि सूर्यप्रकाश मिळण्यासाठी पट्ट्यामध्ये योग्य अंतर (४ ते ५ फूट) ठेवावे.",
                "खालची वाळलेली व जास्त बाधित पाने काढून नष्ट करावीत.",
                "तांबेरा प्रतिकारक जातींची निवड करावी."
            ],
            "hi": [
                "नाइट्रोजन (यूरिया) का अत्यधिक प्रयोग न करें।",
                "उचित दूरी पर बुवाई करें ताकि धूप और हवा मिल सके।",
                "निचली संक्रमित पत्तियों को तोड़कर नष्ट कर दें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Regularly de-trash old lower leaves at 150 and 210 days to increase air movement and decrease microclimate humidity.",
                "mr": "उसाच्या वाढीच्या ५ व्या व ७ व्या महिन्यात उसाची खालची पाने काढून हवा खेळती ठेवावी.",
                "hi": "समय पर सूखी पत्तियां हटाएं ताकि खेत में हवा का संचार बना रहे।"
            },
            "biological": {
                "en": "Foliar application of bio-agent Pseudomonas fluorescens @ 5 g/L water or Bacillus subtilis @ 5 g/L at the first appearance of chlorotic flecks.",
                "mr": "लक्षणे दिसताच स्युडोमोनास फ्लुरोसन्स ५ ग्रॅम प्रति लीटर पाण्यात मिसळून फवारावे.",
                "hi": "स्यूडोमोनास फ्लोरोसेंस (5 ग्राम/लीटर) का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Mancozeb",
                    "formulation": "75% WP",
                    "dosage_per_liter": "2.5 g/L",
                    "cibrc_approved": True,
                    "phi_days": 30,
                    "target": "Foliar spray at first appearance of pustules; repeat after 15 days if cool humid conditions persist"
                },
                {
                    "chemical_name": "Propiconazole",
                    "formulation": "25% EC",
                    "dosage_per_liter": "1.0 ml/L",
                    "cibrc_approved": True,
                    "phi_days": 30,
                    "target": "Systemic foliar spray for severe rust outbreaks"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-SBI Pathology Guidelines: Rust Disease Management",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "SBI Extension Bulletin No. 36"
            },
            {
                "source_name": "MPKV Krishi Margadarshika: Plant Protection",
                "organization": "Mahatma Phule Krishi Vidyapeeth, Rahuri",
                "citation": "Sugarcane Disease Compendium 2024"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-01"
    },
    {
        "disease_id": "sugarcane_yellow_leaf",
        "crop_name": "sugarcane",
        "disease_name": "Yellow Leaf Disease",
        "scientific_name": "Sugarcane yellow leaf virus (SCYLV)",
        "pathogen_type": "Viral / Phytoplasma",
        "symptoms": {
            "en": "Characterized by prominent, bright yellow discoloration of the midrib on the lower surface of leaves 3 to 6 from the spindle top. The yellowing gradually diffuses into the laminar tissue. In advanced stages, midribs develop pinkish-red discolouration with tissue necrosis, apical internode shortening ('bunchy top'), and significant cane yield and sucrose decline.",
            "mr": "शेंड्याकडून ३ ते ६ क्रमांकाच्या पानाच्या मधल्या शिरेचा रंग खालच्या बाजूने ठळक पिवळा पडतो. हळूहळू संपूर्ण पान पिवळे पडते. नंतर शिरा तांबूस-गुलाबी रंगाच्या होतात. कांडी आखूड होऊन शेंड्याजवळ पानांचा झुपका दिसतो.",
            "hi": "ऊपर से तीसरी से छठी पत्ती की मध्य शिरा (मिडरिब) नीचे की तरफ से चमकीली पीली हो जाती है। बाद में शिरा लाल-गुलाबी हो जाती है और पौधे की बढ़वार रुक जाती है।"
        },
        "causes": {
            "en": "Primarily caused by Sugarcane Yellow Leaf Virus (SCYLV, Polerovirus), occasionally associated with Sugarcane Yellow Leaf Phytoplasma (SCYP). Efficiently transmitted in a persistent, circulative manner by the sugarcane aphid (Melanaphis sacchari) and through vegetative propagation of infected seed cane.",
            "mr": "हा रोग विषाणू (SCYLV) आणि फायटोप्लाझ्मामुळे होतो. उसावरील काळ्या मावा किडीद्वारे (मेलॅनाफिस सॅकारी) आणि बाधित बेण्यामार्फत याचा प्रसार होतो.",
            "hi": "यह रोग वायरस (SCYLV) और फाइटोप्लाज्मा द्वारा गन्ने के माहू कीट और संक्रमित बीज से फैलता है।"
        },
        "favourable_conditions": {
            "temperature_range_c": "25-35°C",
            "humidity_pct": "55-80%",
            "rainfall_trigger": "Prolonged dry spells followed by sudden heavy irrigation or high aphid proliferation",
            "en": "Water stress, high aphid vector density, ratoon cropping without vector control, and nutrient deficiency (especially Zinc and Potassium).",
            "mr": "पाण्याचा ताण, मावा किडींचा जास्त प्रादुर्भाव, वारंवार खोडवा पिके घेणे आणि जमिनीत पालाश व जस्ताची कमतरता.",
            "hi": "सूखा, पानी की कमी, माहू कीटों का प्रकोप और पोषक तत्वों की कमी।"
        },
        "prevention_methods": {
            "en": [
                "Utilize virus-indexed tissue-cultured plantlets or certified seed nursery material.",
                "Subject seed setts to Moist Hot Air Treatment (MHAT) at 54°C for 2.5 hours or Hot Water Treatment at 52°C for 30 minutes.",
                "Avoid taking ratoon crops from fields showing more than 20% YLD incidence.",
                "Ensure balanced plant nutrition including micronutrient spray (Zinc Sulphate 0.5% + Ferrous Sulphate 0.5%)."
            ],
            "mr": [
                "विषाणूमुक्त उतीसंवर्धित (टिश्यू कल्चर) रोपांचा किंवा प्रमाणित बेण्याचा वापर करावा.",
                "बेण्यावर उष्ण बाष्पयुक्त हवेची प्रक्रिया करावी.",
                "२० टक्क्यांपेक्षा जास्त प्रादुर्भाव असल्यास खोडवा पीक घेऊ नये.",
                "संतुलित खतांसोबत सूक्ष्मअन्नद्रव्ये (झिंक सल्फेट ०.५% आणि फेरस सल्फेट ०.५%) फवारावीत."
            ],
            "hi": [
                "टिश्यू कल्चर द्वारा तैयार रोगमुक्त पौधों की रोपाई करें।",
                "बीज गन्ने का गर्म हवा या गर्म पानी से उपचार करें।",
                "20% से अधिक रोगग्रस्त खेत में पेड़ी न रखें।"
            ]
        },
        "management_methods": {
            "cultural": {
                "en": "Provide regular irrigation to avoid drought stress which exacerbates YLD symptoms. Uproot and destroy severely stunted clumps.",
                "mr": "पिकाला पाण्याचा ताण पडू देऊ नये, नियमित पाणी द्यावे. अत्यंत खुंटलेली रोगट झाडे उपटून नष्ट करावीत.",
                "hi": "फसल को समय पर पानी दें ताकि सूखे का तनाव न हो। अत्यधिक रोगी पौधों को उखाड़ दें।"
            },
            "biological": {
                "en": "Encourage natural aphid predators (Syrphid fly larvae, Coccinellids). Spray Verticillium lecanii (Lecanicillium lecanii) @ 5 g/L to manage aphid vector populations biologically.",
                "mr": "मावा किडीच्या जैविक नियंत्रणासाठी व्हर्टिसिलियम लेकॅनी ५ ग्रॅम प्रति लीटर पाण्यात मिसळून फवारावे.",
                "hi": "माहू के जैविक नियंत्रण के लिए वर्टिसिलियम लेकेनी (5 ग्राम/लीटर) का छिड़काव करें।"
            },
            "chemical": [
                {
                    "chemical_name": "Imidacloprid",
                    "formulation": "17.8% SL",
                    "dosage_per_liter": "0.3 ml/L",
                    "cibrc_approved": True,
                    "phi_days": 45,
                    "target": "Aphid vector control (Note: Direct viricides do not exist; chemical control manages aphid vectors)"
                },
                {
                    "chemical_name": "Acetamiprid",
                    "formulation": "20% SP",
                    "dosage_per_liter": "0.3 g/L",
                    "cibrc_approved": True,
                    "phi_days": 30,
                    "target": "Aphid vector control"
                }
            ]
        },
        "reference_sources": [
            {
                "source_name": "ICAR-SBI Disease Monograph: Yellow Leaf Disease of Sugarcane",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "SBI Special Technical Report on SCYLV (R. Viswanathan)"
            },
            {
                "source_name": "TNAU Agritech Crop Protection Portal",
                "organization": "Tamil Nadu Agricultural University",
                "citation": "TNAU Sugarcane Virus Disease Guide"
            }
        ],
        "language": "multilingual",
        "is_verified": True,
        "last_verified": "2026-11-01"
    }
]


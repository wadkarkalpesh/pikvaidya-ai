"""
PikVaidya AI — Scientific Weather-Based Crop Health & Epidemiological Risk Engine
=================================================================================
Evaluates environmental physiological stresses (heat, water deficit, waterlogging, wind)
and computes crop-specific epidemiological disease-conduciveness indices using
established agronomic models (e.g. Tom-Cast DSV, Wallin late-blight criteria, ICAR-SBI, ICAR-DOGR).

Guiding Principles:
1. Weather alone CANNOT confirm a biotic disease; it calculates environmental conduciveness.
2. Grounded in peer-reviewed ICAR and international agronomic epidemiology.
3. Incorporates soil textural characteristics and irrigation method mitigations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from app.schemas.multimodal import (
    HistoricalWeatherProfile,
    HistoricalWindowMetrics,
    AgriculturalContextInput,
    EnvironmentalStressIndices,
    DiseaseConducivenessScore,
    WeatherRiskAssessmentSummary,
)

logger = logging.getLogger(__name__)


class WeatherCropHealthRiskEngine:
    """Evaluates crop physiological stress and pathogen proliferation potential."""

    def evaluate_weather_risk(
        self,
        crop_name: str,
        profile: HistoricalWeatherProfile,
        context: Optional[AgriculturalContextInput] = None,
    ) -> WeatherRiskAssessmentSummary:
        """
        Executes comprehensive environmental crop health assessment across physiological
        stresses and crop-specific pathogen conduciveness profiles.
        """
        crop_clean = crop_name.lower().strip()

        # 1. Evaluate Physiological Environmental Stresses
        stresses = self._compute_environmental_stresses(crop_clean, profile, context)

        # 2. Evaluate Crop-Specific Epidemiological Conduciveness Profiles
        disease_scores = self._compute_disease_conduciveness(crop_clean, profile, context)

        # 3. Identify Dominant Environmental Threat
        dominant_risk = self._resolve_dominant_risk(stresses, disease_scores)

        # 4. Overall Disease Pressure (Maximum of pathogen scores)
        max_disease_score = max([d.conduciveness_score for d in disease_scores], default=0.1)

        # 5. Spray Window Suitability from 24h Telemetry
        w24 = profile.window_24h
        is_safe_to_spray = w24.rainfall_total_mm < 2.0 and w24.wind_speed_avg_kmh < 15.0 and w24.temp_max_c < 35.0
        spray_status = "OPTIMAL" if is_safe_to_spray else "GATED_UNFAVOURABLE"

        spray_guidance = {
            "en": "Weather conditions are within safe margins for foliar spray." if is_safe_to_spray else
                  f"Foliar spraying restricted: High wind ({w24.wind_speed_avg_kmh:.1f} km/h) or recent rain ({w24.rainfall_total_mm:.1f} mm).",
            "mr": "फवारणीसाठी हवामान अनुकूल आहे." if is_safe_to_spray else
                  f"फवारणी पुढे ढकला: जोरदार वारा ({w24.wind_speed_avg_kmh:.1f} किमी/तास) किंवा पाऊस ({w24.rainfall_total_mm:.1f} मिमी).",
            "hi": "छिड़काव के लिए मौसम अनुकूल है।" if is_safe_to_spray else
                  f"छिड़काव स्थगित रखें: तेज हवा या हालिया बारिश।"
        }

        return WeatherRiskAssessmentSummary(
            crop=crop_clean,
            environmental_stresses=stresses,
            disease_conduciveness_profile=disease_scores,
            dominant_weather_risk=dominant_risk,
            overall_disease_pressure=round(max_disease_score, 3),
            spray_suitability=spray_status,
            is_safe_to_spray=is_safe_to_spray,
            spray_guidance=spray_guidance,
            weather_summary={
                "location": profile.location_name,
                "temp_avg_7d": profile.window_7d.temp_avg_c,
                "rainfall_7d_mm": profile.window_7d.rainfall_total_mm,
                "humidity_avg_7d": profile.window_7d.humidity_avg_pct,
                "high_humidity_hours_7d": profile.window_7d.high_humidity_hours,
                "soil_moisture_trend": profile.window_7d.soil_moisture_trend,
            },
        )

    # -------------------------------------------------------------------------
    # 1. Environmental Physiological Stresses
    # -------------------------------------------------------------------------

    def _compute_environmental_stresses(
        self,
        crop: str,
        profile: HistoricalWeatherProfile,
        context: Optional[AgriculturalContextInput],
    ) -> EnvironmentalStressIndices:
        w7 = profile.window_7d
        w24 = profile.window_24h

        # A. Heat Stress
        # Sugarcane: tolerant up to 38°C; Tomato/Onion: sensitive above 32°C
        heat_threshold = 38.0 if crop == "sugarcane" else 32.0
        extreme_heat_threshold = 42.0 if crop == "sugarcane" else 36.0

        if w7.temp_max_c <= heat_threshold:
            heat_stress = 0.0
        elif w7.temp_max_c >= extreme_heat_threshold:
            heat_stress = 1.0
        else:
            heat_stress = (w7.temp_max_c - heat_threshold) / (extreme_heat_threshold - heat_threshold)

        # B. Water Deficit / Drought Stress
        # Evaluate 14d rain, soil moisture, and irrigation mitigation
        rain_14d = profile.window_14d.rainfall_total_mm
        sm_pct = w7.soil_moisture_avg_pct if w7.soil_moisture_avg_pct is not None else 25.0

        if sm_pct >= 28.0 or rain_14d >= 40.0:
            water_stress = 0.0
        elif sm_pct <= 14.0 and rain_14d < 5.0:
            water_stress = 1.0
        else:
            water_stress = max(0.0, (28.0 - sm_pct) / 14.0)

        # Mitigation: Drip irrigation relieves 70% of water stress; sprinkler relieves 40%
        if context:
            irr_method = str(context.irrigation_method).lower()
            if "drip" in irr_method:
                water_stress *= 0.30
            elif "sprinkler" in irr_method:
                water_stress *= 0.60
            elif "flood" in irr_method:
                water_stress *= 0.50

        # C. Excess Moisture / Waterlogging Risk
        rain_3d = profile.window_3d.rainfall_total_mm
        if rain_3d >= 80.0 or sm_pct >= 38.0:
            flood_risk = 1.0
        elif rain_3d >= 40.0 or sm_pct >= 34.0:
            flood_risk = 0.65
        elif rain_3d >= 20.0:
            flood_risk = 0.30
        else:
            flood_risk = 0.0

        # Soil Texture modifier: Black cotton soil has low infiltration and drains poorly
        if context and "black_cotton" in str(context.soil_type).lower():
            flood_risk = min(1.0, flood_risk * 1.25)

        # D. Wind Damage / Spray Drift Risk
        if w24.wind_speed_avg_kmh >= 25.0 or w24.wind_gust_max_kmh >= 40.0:
            wind_risk = 0.90
        elif w24.wind_speed_avg_kmh >= 16.0 or w24.wind_gust_max_kmh >= 28.0:
            wind_risk = 0.50
        elif w24.wind_speed_avg_kmh >= 10.0:
            wind_risk = 0.20
        else:
            wind_risk = 0.05

        # Overall Stress & Environmental Suitability
        overall_stress = min(1.0, max(heat_stress, water_stress, flood_risk, wind_risk) * 0.65 +
                                   ((heat_stress + water_stress + flood_risk + wind_risk) / 4.0) * 0.35)
        suitability_score = max(0.0, 1.0 - overall_stress)

        # Formulate multilingual stress summary
        active_stresses = []
        if heat_stress >= 0.5:
            active_stresses.append("Elevated heat stress" if heat_stress < 0.8 else "Severe heat scorch risk")
        if water_stress >= 0.5:
            active_stresses.append("Soil moisture deficit / water stress")
        if flood_risk >= 0.5:
            active_stresses.append("Root-zone waterlogging risk")
        if wind_risk >= 0.5:
            active_stresses.append("High wind drift hazard")

        summary_en = ", ".join(active_stresses) if active_stresses else "Favorable microclimate; environmental stresses minimal."
        summary_mr = "हवामान पिकास अनुकूल असून वातावरणीय ताण अल्प आहे." if not active_stresses else "हवामानातील ताण: " + ", ".join(active_stresses)
        summary_hi = "मौसम अनुकूल है।" if not active_stresses else "पर्यावरणीय तनाव: " + ", ".join(active_stresses)

        return EnvironmentalStressIndices(
            heat_stress_index=round(heat_stress, 3),
            water_stress_index=round(water_stress, 3),
            excess_water_flood_index=round(flood_risk, 3),
            wind_damage_risk=round(wind_risk, 3),
            overall_environmental_stress=round(overall_stress, 3),
            environmental_suitability_score=round(suitability_score, 3),
            stress_summary={"en": summary_en, "mr": summary_mr, "hi": summary_hi},
        )

    # -------------------------------------------------------------------------
    # 2. Pathogen Conduciveness Models (Tom-Cast, Wallin, ICAR)
    # -------------------------------------------------------------------------

    def _compute_disease_conduciveness(
        self,
        crop: str,
        profile: HistoricalWeatherProfile,
        context: Optional[AgriculturalContextInput],
    ) -> List[DiseaseConducivenessScore]:
        if crop == "tomato":
            return self._compute_tomato_conduciveness(profile)
        elif crop == "onion":
            return self._compute_onion_conduciveness(profile)
        else:  # sugarcane (default)
            return self._compute_sugarcane_conduciveness(profile)

    def _compute_tomato_conduciveness(self, profile: HistoricalWeatherProfile) -> List[DiseaseConducivenessScore]:
        w7 = profile.window_7d
        w3 = profile.window_3d

        scores: List[DiseaseConducivenessScore] = []

        # 1. Early Blight (Alternaria solani) — Tom-Cast DSV Model
        # Favorable: Temp 16-28°C, sustained RH >= 85% for >= 25 hours over 7 days, rainfall
        eb_temp_match = 16.0 <= w7.temp_avg_c <= 28.0
        eb_rh_hrs = w7.high_humidity_hours
        eb_rain = w7.rainfall_total_mm

        eb_score = 0.10
        eb_conds = []
        if eb_temp_match:
            eb_score += 0.30
            eb_conds.append(f"Mean temperature ({w7.temp_avg_c:.1f}°C) in Alternaria optimal sporulation range (16-28°C)")
        if eb_rh_hrs >= 35:
            eb_score += 0.40
            eb_conds.append(f"Extended high humidity ({eb_rh_hrs} hours RH >= 85%) satisfies Tom-Cast DSV thresholds")
        elif eb_rh_hrs >= 18:
            eb_score += 0.20
            eb_conds.append(f"Moderate high-humidity exposure ({eb_rh_hrs} hours RH >= 85%)")
        if eb_rain >= 15.0:
            eb_score += 0.20
            eb_conds.append(f"Recent rainfall ({eb_rain:.1f} mm) facilitates foliar spore splash dispersal")
        eb_score = min(1.0, eb_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Early_blight",
                disease_name_en="Early Blight (Alternaria solani)",
                disease_name_mr="टोमॅटोवरील लवकर येणारा करपा",
                pathogen_type="fungal",
                conduciveness_score=round(eb_score, 3),
                risk_tier=self._score_to_tier(eb_score),
                favourable_conditions_met=eb_conds,
                epidemiological_rationale={
                    "en": "Alternaria solani conidia proliferate rapidly under moderate warmth (16-28°C) paired with prolonged leaf wetness.",
                    "mr": "१६ ते २८ अंश तापमान आणि पानांवर दीर्घकाळ टिकणारा ओलावा अल्टरनेरिया बुरशीच्या वाढीस पोषक ठरतो.",
                    "hi": "सामान्य तापमान और पत्तियों पर नमी अगेती झुलसा के बीजाणुओं को सक्रिय करती है।"
                }
            )
        )

        # 2. Late Blight (Phytophthora infestans) — Wallin / Hyre Criteria
        # Strict requirement: Cool temps (10-22°C), high humidity (RH >= 90%), prolonged rain
        lb_temp_match = 10.0 <= w7.temp_avg_c <= 23.0
        lb_sat_hrs = w7.saturation_humidity_hours
        lb_rain = w7.rainfall_total_mm

        lb_score = 0.05
        lb_conds = []
        if lb_temp_match:
            lb_score += 0.35
            lb_conds.append(f"Cool temperatures ({w7.temp_avg_c:.1f}°C) within Phytophthora sporulation window (10-23°C)")
        if lb_sat_hrs >= 20:
            lb_score += 0.45
            lb_conds.append(f"Persistent saturation humidity ({lb_sat_hrs} hours RH >= 90%)")
        if lb_rain >= 30.0:
            lb_score += 0.15
            lb_conds.append(f"Heavy rainfall ({lb_rain:.1f} mm) creates zoospore motility film")
        
        # Hard suppress late blight if weather is hot and dry (temperature > 30°C or RH < 55%)
        if w7.temp_avg_c > 30.0 or w7.humidity_avg_pct < 55.0:
            lb_score = min(lb_score, 0.05)
            lb_conds.append("Hot, dry conditions are hostile to Phytophthora infestans sporangia.")
        lb_score = min(1.0, lb_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Late_blight",
                disease_name_en="Late Blight (Phytophthora infestans)",
                disease_name_mr="टोमॅटोवरील उशिरा येणारा करपा",
                pathogen_type="oomycete",
                conduciveness_score=round(lb_score, 3),
                risk_tier=self._score_to_tier(lb_score),
                favourable_conditions_met=lb_conds,
                epidemiological_rationale={
                    "en": "Phytophthora infestans requires cool temperatures (<22°C) and near-saturation humidity (>90%) for zoospore germination.",
                    "mr": "उशिरा येणारा करपा (Late Blight) थंड आणि अत्यंत दमट वातावरणात वेगाने पसरतो.",
                    "hi": "ठंडा और अत्यधिक नम मौसम पछेती झुलसा के लिए अत्यंत अनुकूल है।"
                }
            )
        )

        # 3. Bacterial Spot (Xanthomonas perforans)
        # Warm rain splash: Temp > 25°C, high rain, wind
        bs_score = 0.10
        bs_conds = []
        if w7.temp_avg_c >= 24.0:
            bs_score += 0.35
            bs_conds.append(f"Warm daytime warmth ({w7.temp_avg_c:.1f}°C) favors Xanthomonas bacteria")
        if w7.rainfall_total_mm >= 25.0:
            bs_score += 0.40
            bs_conds.append(f"Rain events ({w7.rainfall_total_mm:.1f} mm) provide bacterial ingress through leaf stomata")
        if w7.wind_speed_avg_kmh >= 14.0:
            bs_score += 0.15
            bs_conds.append("Wind-driven rain accelerates foliar micro-wounding")
        bs_score = min(1.0, bs_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Bacterial_spot",
                disease_name_en="Bacterial Spot (Xanthomonas)",
                disease_name_mr="टोमॅटोवरील जिवाणूजन्य ठिपके",
                pathogen_type="bacterial",
                conduciveness_score=round(bs_score, 3),
                risk_tier=self._score_to_tier(bs_score),
                favourable_conditions_met=bs_conds,
                epidemiological_rationale={
                    "en": "Wind-driven warm rainfall causes stomatal congestion and rapid dissemination of Xanthomonas bacteria.",
                    "mr": "उबदार पावसामुळे जिवाणू पानांच्या रंध्रातून आत शिरून काळे ठिपके तयार करतात.",
                    "hi": "हवा के साथ बारिश जीवाणु जनित धब्बों को तेजी से फैलाती है।"
                }
            )
        )

        # 4. Yellow Leaf Curl Virus (TYLCV) — Whitefly Vector Risk
        # Favorable: Dry, warm to hot weather (26-35°C), low rain
        vec_score = 0.10
        vec_conds = []
        if 25.0 <= w7.temp_avg_c <= 35.0:
            vec_score += 0.40
            vec_conds.append(f"Temperature {w7.temp_avg_c:.1f}°C accelerates Bemisia tabaci (whitefly) reproductive rate")
        if w7.rainfall_total_mm < 10.0:
            vec_score += 0.35
            vec_conds.append("Absence of heavy wash-off rain preserves whitefly vector populations on lower leaf surfaces")
        if w7.humidity_avg_pct <= 65.0:
            vec_score += 0.15
            vec_conds.append(f"Moderate humidity ({w7.humidity_avg_pct:.1f}%) optimal for whitefly flight")
        vec_score = min(1.0, vec_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Yellow_Leaf_Curl_Virus",
                disease_name_en="Yellow Leaf Curl Virus (TYLCV)",
                disease_name_mr="टोमॅटोवरील पर्णगुच्छ / चुरडा-मुरडा (व्हायरस)",
                pathogen_type="viral_vector",
                conduciveness_score=round(vec_score, 3),
                risk_tier=self._score_to_tier(vec_score),
                favourable_conditions_met=vec_conds,
                epidemiological_rationale={
                    "en": "Dry, warm microclimates promote explosive whitefly (Bemisia tabaci) populations transmitting geminiviruses.",
                    "mr": "कोरडे व उबदार हवामान पांढऱ्या माशीच्या वाढीस पूरक ठरून व्हायरसचा फैलाव वाढवते.",
                    "hi": "सूखा और गर्म मौसम सफेद मक्खी की आबादी बढ़ाता है जिससे वायरस फैलता है।"
                }
            )
        )

        # 5. Septoria Leaf Spot (Septoria lycopersici)
        # Favorable: 20-26°C, extended leaf wetness (RH >= 80%), frequent rain splash
        sep_score = 0.10
        sep_conds = []
        if 20.0 <= w7.temp_avg_c <= 26.0:
            sep_score += 0.40
            sep_conds.append(f"Mild temperatures ({w7.temp_avg_c:.1f}°C) support Septoria pycnidial sporulation")
        if w7.high_humidity_hours >= 25:
            sep_score += 0.35
            sep_conds.append(f"High relative humidity ({w7.high_humidity_hours} hours) provides wet leaf incubation")
        if w7.rainfall_total_mm >= 12.0:
            sep_score += 0.15
            sep_conds.append("Rain splash disperses conidia from lower canopy upwards")
        sep_score = min(1.0, sep_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Septoria_leaf_spot",
                disease_name_en="Septoria Leaf Spot (Septoria lycopersici)",
                disease_name_mr="टोमॅटोवरील सेप्टोरिया पानावरील ठिपके",
                pathogen_type="fungal",
                conduciveness_score=round(sep_score, 3),
                risk_tier=self._score_to_tier(sep_score),
                favourable_conditions_met=sep_conds,
                epidemiological_rationale={
                    "en": "Septoria lycopersici pycnidia release gelatinous spore tendrils triggered by rainfall and sustained leaf wetness at 20-26°C.",
                    "mr": "२० ते २६ अंश तापमान व दमट हवामानात सेप्टोरिया बुरशी पानांवर बारीक ठिपके तयार करते.",
                    "hi": "मध्यम तापमान और पत्तियों पर नमी सेप्टोरिया पत्ती धब्बा रोग को बढ़ाती है।"
                }
            )
        )

        # 6. Leaf Mold (Passalora fulva)
        # Favorable: RH >= 85%, warm temps (20-25°C), dense foliage microclimates
        lm_score = 0.08
        lm_conds = []
        if 20.0 <= w7.temp_avg_c <= 26.0:
            lm_score += 0.35
            lm_conds.append(f"Optimal temperature range ({w7.temp_avg_c:.1f}°C) for Passalora fulva")
        if w7.high_humidity_hours >= 35:
            lm_score += 0.45
            lm_conds.append(f"Prolonged high humidity ({w7.high_humidity_hours} hours RH >= 85%) satisfies leaf mold trigger")
        lm_score = min(1.0, lm_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Leaf_Mold",
                disease_name_en="Leaf Mold (Passalora fulva)",
                disease_name_mr="टोमॅटोवरील पानावरील बुरशी (लीफ मोल्ड)",
                pathogen_type="fungal",
                conduciveness_score=round(lm_score, 3),
                risk_tier=self._score_to_tier(lm_score),
                favourable_conditions_met=lm_conds,
                epidemiological_rationale={
                    "en": "Passalora fulva sporulates aggressively when relative humidity remains consistently above 85% with warm canopy temperatures.",
                    "mr": "८५ टक्क्यांपेक्षा जास्त आर्द्रता आणि उबदार हवामानात पानांच्या खालच्या बाजूला फिकट पिवळे व जांभळट थर तयार होतात.",
                    "hi": "अत्यधिक नमी और गर्म मौसम में लीफ मोल्ड तेजी से बढ़ता है।"
                }
            )
        )

        # 7. Spider Mites (Tetranychus urticae)
        # Favorable: Hot, dry microclimate (Temp >= 28°C, RH <= 55%, rain < 5mm)
        sm_score = 0.08
        sm_conds = []
        if w7.temp_avg_c >= 28.0 or w7.temp_max_c >= 33.0:
            sm_score += 0.45
            sm_conds.append(f"High temperatures ({w7.temp_max_c:.1f}°C max) accelerate two-spotted spider mite generation cycles")
        if w7.humidity_avg_pct <= 55.0:
            sm_score += 0.35
            sm_conds.append(f"Dry air (mean RH {w7.humidity_avg_pct:.1f}%) suppresses entomopathogenic fungal biocontrols")
        if w7.rainfall_total_mm < 5.0:
            sm_score += 0.15
            sm_conds.append("No overhead rain washing to disrupt mite webbing colonies")
        sm_score = min(1.0, sm_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Spider_mites",
                disease_name_en="Spider Mites (Tetranychus urticae)",
                disease_name_mr="टोमॅटोवरील लाल कोळी (स्पायडर माईट)",
                pathogen_type="pest_acarid",
                conduciveness_score=round(sm_score, 3),
                risk_tier=self._score_to_tier(sm_score),
                favourable_conditions_met=sm_conds,
                epidemiological_rationale={
                    "en": "Hot, drought-stressed canopy conditions (low RH, high temp) trigger exponential spider mite colony growth.",
                    "mr": "उष्ण व कोरड्या हवामानात लाल कोळ्यांची पैदास झपाट्याने वाढून पानांवर जाळे तयार होते.",
                    "hi": "गर्म और शुष्क मौसम लाल मकड़ी (माइट) के प्रकोप को तेजी से बढ़ाता है।"
                }
            )
        )

        # 8. Target Spot (Corynespora cassiicola)
        # Favorable: Warm (24-32°C), high humidity, frequent rain
        ts_score = 0.10
        ts_conds = []
        if 23.0 <= w7.temp_avg_c <= 32.0:
            ts_score += 0.35
            ts_conds.append(f"Warm mean temperature ({w7.temp_avg_c:.1f}°C) matches Corynespora cassiicola growth")
        if w7.high_humidity_hours >= 28:
            ts_score += 0.35
            ts_conds.append("High ambient humidity supports fungal penetration")
        if w7.rainfall_total_mm >= 15.0:
            ts_score += 0.20
            ts_conds.append("Rain splash spreads conidia to upper foliage")
        ts_score = min(1.0, ts_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Target_Spot",
                disease_name_en="Target Spot (Corynespora cassiicola)",
                disease_name_mr="टोमॅटोवरील टार्गेट स्पॉट (चकती चट्टे)",
                pathogen_type="fungal",
                conduciveness_score=round(ts_score, 3),
                risk_tier=self._score_to_tier(ts_score),
                favourable_conditions_met=ts_conds,
                epidemiological_rationale={
                    "en": "Corynespora cassiicola causes circular zonate leaf spots under warm, humid conditions with free moisture.",
                    "mr": "उबदार व दमट हवामानात चकतीसारखे वर्तुळाकार चट्टे पानांवर वेगाने वाढतात.",
                    "hi": "गर्म और नम मौसम में पत्तियों पर गोल छल्लेदार धब्बे बनते हैं।"
                }
            )
        )

        # 9. Tomato Mosaic Virus (ToMV)
        # Favored by vigorous vegetative growth and moderate temperatures (20-30°C)
        tmv_score = 0.10
        tmv_conds = []
        if 20.0 <= w7.temp_avg_c <= 30.0:
            tmv_score += 0.30
            tmv_conds.append(f"Mild to warm temperature ({w7.temp_avg_c:.1f}°C) allows active viral replication")
        if w7.humidity_avg_pct >= 60.0:
            tmv_score += 0.20
            tmv_conds.append("Moderate humidity promotes rapid vegetative tissue expansion susceptible to mechanical transmission")
        tmv_score = min(1.0, tmv_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Mosaic_virus",
                disease_name_en="Tomato Mosaic Virus (ToMV)",
                disease_name_mr="टोमॅटो मोज़ॅक व्हायरस",
                pathogen_type="viral_contact",
                conduciveness_score=round(tmv_score, 3),
                risk_tier=self._score_to_tier(tmv_score),
                favourable_conditions_met=tmv_conds,
                epidemiological_rationale={
                    "en": "ToMV is mechanically and seed-transmitted; rapid vegetative flush under temperate conditions accelerates systemic symptom expression.",
                    "mr": "शाकीय वाढीच्या काळात पानांवर पिवळसर-हिरवे चट्टे (मोज़ॅक) स्पष्ट दिसू लागतात.",
                    "hi": "अनुकूल तापमान में मोज़ेक वायरस के लक्षण पत्तियों पर तेजी से उभरते हैं।"
                }
            )
        )

        # 10. Healthy State Baseline Conduciveness
        # Favorable for healthy crop: moderate temperature, balanced moisture, absence of disease triggers
        healthy_score = max(0.1, 1.0 - max(eb_score, lb_score, bs_score, vec_score, sep_score, lm_score, sm_score, ts_score))
        scores.append(
            DiseaseConducivenessScore(
                disease_id="Healthy",
                disease_name_en="Healthy Foliage Condition",
                disease_name_mr="निरोगी पीक स्थिती",
                pathogen_type="none",
                conduciveness_score=round(healthy_score, 3),
                risk_tier=self._score_to_tier(healthy_score),
                favourable_conditions_met=["Climatic indicators are within normal vegetative development tolerance"],
                epidemiological_rationale={
                    "en": "Environmental factors do not show intense fungal or bacterial proliferation signals.",
                    "mr": "वातावरणात कोणत्याही गंभीर बुरशी किंवा जिवाणूंची तीव्र लक्षणे दिसून येत नाहीत.",
                    "hi": "पर्यावरणीय कारक सामान्य हैं।"
                }
            )
        )

        return scores

    def _compute_sugarcane_conduciveness(self, profile: HistoricalWeatherProfile) -> List[DiseaseConducivenessScore]:
        w7 = profile.window_7d
        scores: List[DiseaseConducivenessScore] = []

        # 1. Red Rot (Colletotrichum falcatum)
        # Favorable: 25-32°C, RH >= 80%, high soil moisture / waterlogging post rain
        rr_temp = 25.0 <= w7.temp_avg_c <= 32.0
        rr_rh = w7.humidity_avg_pct >= 75.0 or w7.high_humidity_hours >= 30
        rr_water = w7.rainfall_total_mm >= 25.0 or (w7.soil_moisture_avg_pct and w7.soil_moisture_avg_pct >= 32.0)

        rr_score = 0.10
        rr_conds = []
        if rr_temp:
            rr_score += 0.35
            rr_conds.append(f"Temperature ({w7.temp_avg_c:.1f}°C) supports Colletotrichum mycelial growth (25-32°C)")
        if rr_rh:
            rr_score += 0.35
            rr_conds.append("High ambient humidity sustains sporulation inside cane internodes")
        if rr_water:
            rr_score += 0.20
            rr_conds.append("Excess soil moisture / waterlogging stresses root system and facilitates fungal entry")
        rr_score = min(1.0, rr_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="RedRot",
                disease_name_en="Red Rot (Colletotrichum falcatum)",
                disease_name_mr="उसावरील तांबडे कूज (लाल सड)",
                pathogen_type="fungal",
                conduciveness_score=round(rr_score, 3),
                risk_tier=self._score_to_tier(rr_score),
                favourable_conditions_met=rr_conds,
                epidemiological_rationale={
                    "en": "Waterlogging coupled with warm, humid monsoon conditions drives systemic vascular colonization of Colletotrichum falcatum.",
                    "mr": "शेतात साचलेले पाणी आणि दमट उबदार हवामान लाल सड रोगाच्या बुरशीचा प्रसार वाढवते.",
                    "hi": "जलभराव और आर्द्र मौसम गन्ने में लाल सड़न के प्रसार को तेज करता है।"
                }
            )
        )

        # 2. Rust (Puccinia kuehnii)
        # Favorable: Cooler/moderate temperatures (18-28°C), prolonged dew periods, RH >= 85%
        rust_temp = 18.0 <= w7.temp_avg_c <= 28.0
        rust_rh = w7.high_humidity_hours >= 35

        rust_score = 0.10
        rust_conds = []
        if rust_temp:
            rust_score += 0.45
            rust_conds.append(f"Mild to moderate temperatures ({w7.temp_avg_c:.1f}°C) ideal for Puccinia urediniospore germination")
        if rust_rh:
            rust_score += 0.40
            rust_conds.append(f"Prolonged high humidity ({w7.high_humidity_hours} hours) provides necessary leaf wetness")
        rust_score = min(1.0, rust_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Rust",
                disease_name_en="Common Rust (Puccinia kuehnii)",
                disease_name_mr="उसावरील तांबेरा (रस्ट)",
                pathogen_type="fungal",
                conduciveness_score=round(rust_score, 3),
                risk_tier=self._score_to_tier(rust_score),
                favourable_conditions_met=rust_conds,
                epidemiological_rationale={
                    "en": "Puccinia rust fungi require moderate temperatures and sustained overnight dew periods for spore tube penetration.",
                    "mr": "थंड व दमट हवामानामुळे उसाच्या पानांवर तांबूस रंगाचे फोड (Pustules) तयार होतात.",
                    "hi": "मध्यम तापमान और ओस की बूंदें रतुआ रोग के संक्रमण के लिए अनुकूल हैं।"
                }
            )
        )

        # 3. Sugarcane Mosaic (SCMV) — Aphid Vector Model
        # Favorable: Moderate temps (22-30°C), moderate RH (55-80%), vigorous vegetative tillering
        mos_score = 0.10
        mos_conds = []
        if 22.0 <= w7.temp_avg_c <= 30.0:
            mos_score += 0.40
            mos_conds.append(f"Temperature ({w7.temp_avg_c:.1f}°C) favors aphid vector flight and transmission")
        if 55.0 <= w7.humidity_avg_pct <= 80.0:
            mos_score += 0.30
            mos_conds.append("Moderate humidity promotes lush foliar tillering susceptible to stylet feeding")
        mos_score = min(1.0, mos_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Mosaic",
                disease_name_en="Sugarcane Mosaic Virus (SCMV)",
                disease_name_mr="उसावरील मोज़ॅक (केवडा/पिवळे चट्टे)",
                pathogen_type="viral_vector",
                conduciveness_score=round(mos_score, 3),
                risk_tier=self._score_to_tier(mos_score),
                favourable_conditions_met=mos_conds,
                epidemiological_rationale={
                    "en": "Aphids (Rhopalosiphum maidis) transmit SCMV non-persistently during warm, temperate flush periods.",
                    "mr": "मावा किडीमुळे उसाच्या कोवळ्या पानांवर मोज़ॅक विषाणूचा प्रसार होतो.",
                    "hi": "माहू कीट के माध्यम से गन्ने में मोज़ेक वायरस फैलता है।"
                }
            )
        )

        # 4. Sugarcane Yellow Leaf Virus (SCYLV) — Melanaphis sacchari Vector Model
        # Favorable: Warm conditions (24-34°C), intermittent dry spells, water stress
        yl_score = 0.10
        yl_conds = []
        if 24.0 <= w7.temp_avg_c <= 34.0:
            yl_score += 0.40
            yl_conds.append(f"Warm daytime temperature ({w7.temp_avg_c:.1f}°C) supports sugarcane aphid colonies")
        if w7.rainfall_total_mm < 15.0:
            yl_score += 0.30
            yl_conds.append("Absence of heavy beating rains allows aphid persistence along midribs")
        yl_score = min(1.0, yl_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Yellow",
                disease_name_en="Yellow Leaf Disease (SCYLV)",
                disease_name_mr="उसावरील पिवळा पान रोग (यलो लीफ)",
                pathogen_type="viral_vector",
                conduciveness_score=round(yl_score, 3),
                risk_tier=self._score_to_tier(yl_score),
                favourable_conditions_met=yl_conds,
                epidemiological_rationale={
                    "en": "Melanaphis sacchari aphids vector SCYLV; moisture stress paired with warm weather enhances midrib yellowing expression.",
                    "mr": "उसावरील पिवळा मावा (Sugarcane aphid) यलो लीफ व्हायरस पसरवतो, ज्यामुळे मुख्य शिरेवर पिवळेपणा येतो.",
                    "hi": "एफिड कीट द्वारा यलो लीफ वायरस का प्रसार होता है।"
                }
            )
        )

        # 5. Healthy Baseline
        healthy_score = max(0.1, 1.0 - max(rr_score, rust_score, mos_score, yl_score))
        scores.append(
            DiseaseConducivenessScore(
                disease_id="Healthy",
                disease_name_en="Healthy Sugarcane Foliage",
                disease_name_mr="निरोगी उसाची पाने",
                pathogen_type="none",
                conduciveness_score=round(healthy_score, 3),
                risk_tier=self._score_to_tier(healthy_score),
                favourable_conditions_met=["No critical fungal sporulation triggers currently active"],
                epidemiological_rationale={
                    "en": "Environmental parameters support normal grand-growth internode elongation without severe fungal pressure.",
                    "mr": "हवामान उसाच्या शाकीय वाढीसाठी अनुकूल आहे.",
                    "hi": "मौसम गन्ने की सामान्य वृद्धि के अनुकूल है।"
                }
            )
        )

        return scores

    def _compute_onion_conduciveness(self, profile: HistoricalWeatherProfile) -> List[DiseaseConducivenessScore]:
        w7 = profile.window_7d
        scores: List[DiseaseConducivenessScore] = []

        # 1. Purple Blotch (Alternaria porri)
        # Favorable: 22-30°C, RH >= 85% for >= 12h, rainfall / dew
        pb_temp = 21.0 <= w7.temp_avg_c <= 31.0
        pb_rh_hrs = w7.high_humidity_hours
        pb_rain = w7.rainfall_total_mm

        pb_score = 0.10
        pb_conds = []
        if pb_temp:
            pb_score += 0.35
            pb_conds.append(f"Temperature ({w7.temp_avg_c:.1f}°C) matches Alternaria porri optimum range (22-30°C)")
        if pb_rh_hrs >= 28:
            pb_score += 0.40
            pb_conds.append(f"High-humidity duration ({pb_rh_hrs} hours RH >= 85%) satisfies foliar incubation needs")
        if pb_rain >= 10.0:
            pb_score += 0.15
            pb_conds.append(f"Rainfall events ({pb_rain:.1f} mm) disperse conidia across tubular leaf surfaces")
        pb_score = min(1.0, pb_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Purple_blotch",
                disease_name_en="Purple Blotch (Alternaria porri)",
                disease_name_mr="कांद्यावरील जांभळा करपा",
                pathogen_type="fungal",
                conduciveness_score=round(pb_score, 3),
                risk_tier=self._score_to_tier(pb_score),
                favourable_conditions_met=pb_conds,
                epidemiological_rationale={
                    "en": "Alternaria porri requires at least 10-12 hours of high relative humidity (>85%) at 25°C to penetrate tubular onion leaves.",
                    "mr": "उबदार व दमट हवामानात पानांवर ओलावा राहिल्यास जांभळ्या करप्याचा प्रादुर्भाव वेगाने वाढतो.",
                    "hi": "उच्च आर्द्रता और सामान्य तापमान प्याज के बैंगनी धब्बा रोग को बढ़ाता है।"
                }
            )
        )

        # 2. Stemphylium Blight (Stemphylium vesicarium)
        # Favorable: 18-26°C, high humidity, cloud cover
        sb_score = 0.10
        sb_conds = []
        if 18.0 <= w7.temp_avg_c <= 26.0:
            sb_score += 0.40
            sb_conds.append(f"Mild temperatures ({w7.temp_avg_c:.1f}°C) favor Stemphylium blight development")
        if w7.high_humidity_hours >= 30:
            sb_score += 0.40
            sb_conds.append(f"Sustained humidity ({w7.high_humidity_hours} hours) triggers foliar lesions")
        sb_score = min(1.0, sb_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Stemphylium_blight",
                disease_name_en="Stemphylium Leaf Blight",
                disease_name_mr="स्टेमफिलीयम करपा (तपकिरी चट्टे)",
                pathogen_type="fungal",
                conduciveness_score=round(sb_score, 3),
                risk_tier=self._score_to_tier(sb_score),
                favourable_conditions_met=sb_conds,
                epidemiological_rationale={
                    "en": "Stemphylium vesicarium establishes secondary infections following cool, overcast, high-humidity periods.",
                    "mr": "ढगाळ व दमट हवामानात स्टेमफिलीयम बुरशी पानांच्या टोकाकडून करपा वाढवते.",
                    "hi": "बादल छाए रहने और अधिक नमी से भूरा झुलसा फैलता है।"
                }
            )
        )

        # 3. Iris Yellow Spot Virus (Tospovirus, Vector: Thrips tabaci)
        # Favorable: Warm (22-34°C), dry microclimates (RH <= 65%), prolonged dry spells without washing rains
        iyv_temp = 22.0 <= w7.temp_avg_c <= 34.0
        iyv_dry = w7.humidity_avg_pct <= 65.0 or w7.high_humidity_hours <= 15
        iyv_norain = w7.rainfall_total_mm < 5.0

        iyv_score = 0.10
        iyv_conds = []
        if iyv_temp:
            iyv_score += 0.35
            iyv_conds.append(f"Warm mean temperature ({w7.temp_avg_c:.1f}°C) accelerates onion thrips reproductive cycles (22-34°C)")
        if iyv_dry:
            iyv_score += 0.35
            iyv_conds.append(f"Dry ambient atmosphere ({w7.humidity_avg_pct:.1f}% RH) supports explosive thrips nymph emergence")
        if iyv_norain:
            iyv_score += 0.20
            iyv_conds.append("Absence of heavy rainfall facilitates unchecked vector feeding and viral inoculation")
        iyv_score = min(1.0, iyv_score)

        scores.append(
            DiseaseConducivenessScore(
                disease_id="Iris_yellow_virus",
                disease_name_en="Iris Yellow Spot Virus (IYSV)",
                disease_name_mr="कांद्यावरील आयरिस यलो स्पॉट व्हायरस (फुलकिडे)",
                pathogen_type="viral_vector",
                conduciveness_score=round(iyv_score, 3),
                risk_tier=self._score_to_tier(iyv_score),
                favourable_conditions_met=iyv_conds,
                epidemiological_rationale={
                    "en": "Hot, dry conditions and prolonged rain deficits accelerate onion thrips (Thrips tabaci) generations, the exclusive vector for IYSV.",
                    "mr": "उष्ण व कोरडे हवामान कांद्यावरील फुलकिड्यांच्या (थ्रिप्स) वाढीस अत्यंत पोषक ठरून आयरिस यलो स्पॉट विषाणूचा प्रादुर्भाव वाढवते.",
                    "hi": "गर्म और सूखा मौसम थ्रिप्स कीटों को बढ़ाता है, जो इस वायरस के मुख्य संवाहक हैं।"
                }
            )
        )

        # 4. Healthy Baseline
        healthy_score = max(0.1, 1.0 - max(pb_score, sb_score, iyv_score))
        scores.append(
            DiseaseConducivenessScore(
                disease_id="Healthy",
                disease_name_en="Healthy Onion Foliage",
                disease_name_mr="निरोगी कांद्याची पात",
                pathogen_type="none",
                conduciveness_score=round(healthy_score, 3),
                risk_tier=self._score_to_tier(healthy_score),
                favourable_conditions_met=["Tubular leaves well-aerated without persistent surface moisture"],
                epidemiological_rationale={
                    "en": "Microclimatic conditions do not support explosive fungal sporulation on onion foliage.",
                    "mr": "कांद्याच्या पातीवर बुरशी वाढीसाठी पोषक वातावरण नाही.",
                    "hi": "प्याज की पत्तियों के लिए मौसम सामान्य है।"
                }
            )
        )

        return scores

    def _resolve_dominant_risk(
        self,
        stresses: EnvironmentalStressIndices,
        diseases: List[DiseaseConducivenessScore],
    ) -> str:
        """Determines the single most acute environmental threat facing the crop."""
        highest_disease = max(diseases, key=lambda d: d.conduciveness_score, default=None)
        
        if stresses.heat_stress_index >= 0.70:
            return "SEVERE_HEAT_STRESS"
        elif stresses.water_stress_index >= 0.70:
            return "CRITICAL_WATER_DEFICIT"
        elif stresses.excess_water_flood_index >= 0.70:
            return "ROOT_ZONE_WATERLOGGING"
        elif highest_disease and highest_disease.conduciveness_score >= 0.65 and highest_disease.disease_id != "Healthy":
            return f"HIGH_EPIDEMIOLOGICAL_RISK_{highest_disease.disease_id.upper()}"
        elif stresses.overall_environmental_stress >= 0.45:
            return "MODERATE_ENVIRONMENTAL_STRESS"
        else:
            return "OPTIMAL_GROWTH_CONDITIONS"

    def _score_to_tier(self, score: float) -> str:
        if score >= 0.75:
            return "CRITICAL"
        elif score >= 0.50:
            return "HIGH"
        elif score >= 0.30:
            return "MODERATE"
        else:
            return "MINIMAL"


# Global singleton instance
weather_crop_health_risk_engine = WeatherCropHealthRiskEngine()

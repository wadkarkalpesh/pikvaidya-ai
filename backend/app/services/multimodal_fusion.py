"""
PikVaidya AI — Multimodal Crop-Health Fusion Engine
===================================================
Combines computer vision pathology inference with multi-window microclimate
telemetry, epidemiological disease conduciveness, and agricultural plot metadata.

Core Principles & Constraints:
1. Non-Override Guarantee: Weather data CANNOT override a high-confidence visual diagnosis (>= 0.75).
2. Calibrated Bayesian Fusion: Moderates ambiguous visual classifications (0.50 <= conf < 0.75).
3. Environmental Anomaly Detection: Detects and flags biologically implausible diseases under hostile microclimates.
4. Asymptomatic Vulnerability: Alerts when visually healthy leaves face severe environmental disease triggers.
5. Multi-Output Transparency: Separates Image Prediction, Weather Risk, and Fused Assessment.
"""

import math
import logging
from typing import Dict, Any, Optional, List, Tuple

from app.schemas.multimodal import (
    ImageDiagnosisSummary,
    WeatherRiskAssessmentSummary,
    MultimodalAssessmentSummary,
    MultimodalExplainability,
    MultimodalPredictResponse,
    AgriculturalContextInput,
    DiseaseConducivenessScore,
    EnvironmentalStressIndices,
)

logger = logging.getLogger(__name__)


class MultimodalFusionEngine:
    """Enterprise fusion synthesizer combining visual pathology and environmental microclimate."""

    CONF_HIGH_THRESHOLD: float = 0.75
    CONF_MODERATE_THRESHOLD: float = 0.50

    def fuse(
        self,
        image_prediction: ImageDiagnosisSummary,
        weather_risk: WeatherRiskAssessmentSummary,
        context: Optional[AgriculturalContextInput] = None,
        strategy: str = "CALIBRATED_BAYESIAN",
    ) -> MultimodalPredictResponse:
        """
        Executes multimodal fusion between image prediction and environmental risk.
        Returns the complete MultimodalPredictResponse with separated outputs and explainability.
        """
        crop = image_prediction.crop.lower()
        vis_pred = image_prediction.predicted_class
        vis_conf = image_prediction.confidence
        vis_scores = image_prediction.class_scores or {vis_pred: vis_conf}

        stresses = weather_risk.environmental_stresses
        conduciveness_list = weather_risk.disease_conduciveness_profile

        # Map disease_id -> conduciveness score with normalized keys to handle label format variations
        def _norm_key(k: str) -> str:
            s = str(k).lower()
            for prefix in ("onion___", "sugarcane___", "tomato___", "onion_", "sugarcane_", "tomato_"):
                if s.startswith(prefix):
                    s = s[len(prefix):]
            return s.replace("_", "").replace(" ", "").replace("-", "")

        conduciveness_map = {d.disease_id: d.conduciveness_score for d in conduciveness_list}
        norm_conduciveness = {_norm_key(d.disease_id): d.conduciveness_score for d in conduciveness_list}
        target_conduciveness = norm_conduciveness.get(_norm_key(vis_pred), conduciveness_map.get(vis_pred, 0.20))

        # ---------------------------------------------------------------------
        # 1. Agronomic Concordance & Anomaly Detection
        # ---------------------------------------------------------------------
        # Check if weather biologically contradicts the claimed visual disease
        anomaly_warning = None
        is_concordant = True
        concordance_score = round(min(1.0, (vis_conf * 0.6) + (target_conduciveness * 0.4)), 3)

        if vis_pred.lower() != "healthy" and vis_conf >= self.CONF_HIGH_THRESHOLD:
            # If weather is severely hostile to this pathogen
            if target_conduciveness <= 0.15:
                is_concordant = False
                concordance_score = round(vis_conf * 0.5, 3)
                anomaly_warning = {
                    "en": (
                        f"Environmental Incongruence Detected: Current microclimate ({weather_risk.weather_summary.get('temp_avg_7d', 0):.1f}°C, "
                        f"low humidity) is biologically hostile to active {vis_pred} sporulation. "
                        f"Visible leaf lesions may represent past/dormant infections, chemical burn, or abiotic stress. "
                        f"Physical agronomist verification recommended before applying fungicides."
                    ),
                    "mr": (
                        f"हवामान विसंगती सूचना: सध्याचे कोरडे व उष्ण हवामान या रोगाच्या प्रसारास अनुकूल नाही. "
                        f"पानावरील चट्टे जुन्या रोगाचे किंवा उन्हाच्या ताणाचे असू शकतात. "
                        f"औषध फवारणीपूर्वी तज्ज्ञ कृषी सहाय्यकांचा प्रत्यक्ष सल्ला घ्या."
                    ),
                    "hi": (
                        f"पर्यावरणीय विसंगति: वर्तमान मौसम इस रोग के प्रसार के लिए प्रतिकूल है। "
                        f"पत्तियों पर मौजूद धब्बे पुराने संक्रमण या धूप के तनाव के हो सकते हैं। "
                        f"दवा खरीदने से पहले विशेषज्ञ सलाह अवश्य लें।"
                    )
                }

        # ---------------------------------------------------------------------
        # 2. Multimodal Posterior Classification (Bayesian / Rule-Based)
        # ---------------------------------------------------------------------
        fused_scores: Dict[str, float] = {}
        fused_pred = vis_pred
        fused_conf = vis_conf

        if strategy == "CALIBRATED_BAYESIAN" and self.CONF_MODERATE_THRESHOLD <= vis_conf < self.CONF_HIGH_THRESHOLD:
            # Ambiguous visual classification: Apply Bayesian updating with environmental prior
            fused_pred, fused_conf, fused_scores = self._bayesian_update(vis_scores, conduciveness_map)
        else:
            # High visual confidence or Rule-Based strategy: Strictly enforce non-override constraint
            # Weather modulates confidence slightly but CANNOT overturn visual diagnosis
            if anomaly_warning:
                # Moderate confidence penalty for hostile environmental incongruence
                fused_conf = round(vis_conf * 0.88, 4)
            elif target_conduciveness >= 0.60:
                # Environmental corroboration bonus (capped at 0.99)
                fused_conf = round(min(0.99, vis_conf + (1.0 - vis_conf) * 0.15), 4)
            else:
                fused_conf = vis_conf
            fused_pred = vis_pred
            fused_scores = dict(vis_scores)

        # Confidence Tier
        if fused_conf >= self.CONF_HIGH_THRESHOLD:
            conf_tier = "HIGH"
        elif fused_conf >= self.CONF_MODERATE_THRESHOLD:
            conf_tier = "MODERATE"
        else:
            conf_tier = "LOW_INCONCLUSIVE"

        # ---------------------------------------------------------------------
        # 3. Composite Crop Health Index & Progression Velocity
        # ---------------------------------------------------------------------
        crop_health_idx, health_label = self._compute_crop_health_index(
            fused_pred=fused_pred,
            fused_conf=fused_conf,
            foliar_severity=image_prediction.foliar_severity,
            affected_area_pct=image_prediction.affected_area_percentage,
            env_stress=stresses.overall_environmental_stress,
            pathogen_conduciveness=target_conduciveness,
        )

        progression_velocity = self._compute_progression_velocity(
            fused_pred=fused_pred,
            target_conduciveness=target_conduciveness,
            env_stress=stresses.overall_environmental_stress,
        )

        # ---------------------------------------------------------------------
        # 4. Multilingual Display Names
        # ---------------------------------------------------------------------
        display_names = self._resolve_display_name(crop, fused_pred)

        multimodal_assessment = MultimodalAssessmentSummary(
            primary_diagnosis=fused_pred,
            display_name=display_names,
            fused_confidence=round(fused_conf, 4),
            confidence_tier=conf_tier,
            crop_health_index=round(crop_health_idx, 1),
            health_status_label=health_label,
            disease_progression_velocity=progression_velocity,
            agronomic_concordance=concordance_score,
            is_environmentally_concordant=is_concordant,
            anomaly_warning=anomaly_warning,
            fusion_strategy_applied=strategy,
        )

        # ---------------------------------------------------------------------
        # 5. Explainability Breakdown
        # ---------------------------------------------------------------------
        explainability = self._synthesize_explainability(
            image_prediction=image_prediction,
            weather_risk=weather_risk,
            multimodal_assessment=multimodal_assessment,
            target_conduciveness=target_conduciveness,
        )

        # ---------------------------------------------------------------------
        # 6. Actionable Agronomic Recommendations
        # ---------------------------------------------------------------------
        recommendations = self._formulate_multimodal_recommendations(
            crop=crop,
            fused_pred=fused_pred,
            fused_conf=fused_conf,
            weather_risk=weather_risk,
            multimodal_assessment=multimodal_assessment,
        )

        statutory_disclaimer = {
            "en": (
                "Statutory Legal Notice under the Insecticides Act, 1968: "
                "Dosages and chemical recommendations are compiled strictly from CIBRC and ICAR packages of practices. "
                "Multimodal assessment combines automated visual analytics with atmospheric modeling; "
                "it does not constitute statutory ground truth. Always inspect container labels before chemical application."
            ),
            "mr": (
                "वैधानिक कायदेशीर सूचना (कीटकनाशक कायदा, १९६८): "
                "सर्व औषधांचे प्रमाण व शिफारसी CIBRC व ICAR च्या मार्गदर्शक तत्त्वांवर आधारित आहेत. "
                "हे बहुपर्यायी (Multimodal) निदान संगणकीय विश्लेषणावर आधारित असून अंतिम पुरावा नाही. "
                "फवारणीपूर्वी बाटलीवरील सूचना वाचाव्यात व कृषी सहाय्यकांचा सल्ला घ्यावा."
            ),
            "hi": (
                "वैधानिक कानूनी सूचना (कीटनाशक अधिनियम, 1968): "
                "सभी रासायनिक दवाएं और मात्राएं CIBRC और ICAR द्वारा अनुशंसित हैं। "
                "यह बहु-मॉडल (Multimodal) अनुमान अंतिम सत्य नहीं है। प्रयोग से पहले विशेषज्ञ सलाह लें।"
            ),
        }

        return MultimodalPredictResponse(
            multimodal_assessment=multimodal_assessment,
            image_prediction=image_prediction,
            weather_risk=weather_risk,
            explainability=explainability,
            agricultural_context=context or AgriculturalContextInput(crop_name=crop),
            recommendations=recommendations,
            statutory_disclaimer=statutory_disclaimer,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _bayesian_update(
        self,
        vis_scores: Dict[str, float],
        conduciveness_map: Dict[str, float],
        beta: float = 0.35,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        Executes bounded Bayesian updating on ambiguous class distribution:
        P_fused(c) proportional to P_img(c) * exp(beta * R_env(c))
        """
        def _norm_key(k: str) -> str:
            return str(k).lower().replace("_", "").replace(" ", "").replace("-", "")

        norm_conduciveness = {_norm_key(k): v for k, v in conduciveness_map.items()}
        unnorm: Dict[str, float] = {}
        for c, p in vis_scores.items():
            r = norm_conduciveness.get(_norm_key(c), conduciveness_map.get(c, 0.20))
            prior_factor = math.exp(beta * r)
            unnorm[c] = p * prior_factor

        total = sum(unnorm.values()) or 1.0
        fused_scores = {c: round(v / total, 4) for c, v in unnorm.items()}

        best_class = max(fused_scores, key=lambda k: fused_scores[k])
        best_conf = fused_scores[best_class]

        return best_class, best_conf, fused_scores

    def _compute_crop_health_index(
        self,
        fused_pred: str,
        fused_conf: float,
        foliar_severity: Optional[str],
        affected_area_pct: Optional[float],
        env_stress: float,
        pathogen_conduciveness: float,
    ) -> Tuple[float, str]:
        """Calculates 0-100% composite health index and categorical health label."""
        if fused_pred == "Healthy":
            # Visually healthy
            base_score = 95.0
            # Deduct for active environmental stress
            health_idx = max(40.0, base_score - (env_stress * 30.0) - (pathogen_conduciveness * 15.0))
            if env_stress >= 0.50 or pathogen_conduciveness >= 0.70:
                label = "VULNERABLE"
            else:
                label = "HEALTHY"
        else:
            # Active disease present
            severity_factor = (affected_area_pct / 100.0) if affected_area_pct is not None else 0.20
            if foliar_severity == "SEVERE":
                severity_factor = max(severity_factor, 0.35)
            elif foliar_severity == "MODERATE":
                severity_factor = max(severity_factor, 0.20)

            base_score = max(10.0, 75.0 - (fused_conf * 40.0) - (severity_factor * 35.0))
            # Additional penalty for environmental stress aggravating the pathology
            health_idx = max(5.0, base_score - (env_stress * 15.0))

            if health_idx >= 60.0:
                label = "MILDLY_INFECTED"
            elif health_idx >= 35.0:
                label = "MODERATELY_INFECTED"
            else:
                label = "SEVERELY_INFECTED"

        return round(health_idx, 1), label

    def _compute_progression_velocity(
        self,
        fused_pred: str,
        target_conduciveness: float,
        env_stress: float,
    ) -> str:
        """Estimates infection expansion rate through canopy."""
        if fused_pred == "Healthy":
            return "ARRESTED" if env_stress < 0.40 else "SLOW"

        if target_conduciveness >= 0.65:
            return "RAPID"
        elif target_conduciveness >= 0.35:
            return "MODERATE"
        else:
            return "SLOW"

    def _resolve_display_name(self, crop: str, disease: str) -> Dict[str, str]:
        mapping = {
            "RedRot": {"en": "Red Rot (Colletotrichum falcatum)", "mr": "उसावरील तांबडे कूज (लाल सड)", "hi": "गन्ने का लाल सड़न रोग"},
            "Rust": {"en": "Common Rust (Puccinia kuehnii)", "mr": "उसावरील तांबेरा (रस्ट)", "hi": "गन्ने का रतुआ रोग"},
            "Mosaic": {"en": "Sugarcane Mosaic Virus", "mr": "उसावरील मोझॅक व्हायरस", "hi": "मोज़ेक वायरस"},
            "Yellow": {"en": "Yellow Leaf Disease", "mr": "उसावरील पिवळे पान रोग", "hi": "पीली पत्ती रोग"},
            "Early_blight": {"en": "Early Blight (Alternaria solani)", "mr": "टोमॅटोवरील लवकर येणारा करपा", "hi": "टमाटर का अगेती झुलसा"},
            "Late_blight": {"en": "Late Blight (Phytophthora infestans)", "mr": "टोमॅटोवरील उशिरा येणारा करपा", "hi": "टमाटर का पछेती झुलसा"},
            "Bacterial_spot": {"en": "Bacterial Spot (Xanthomonas)", "mr": "टोमॅटोवरील जिवाणूजन्य ठिपके", "hi": "जीवाणु जनित धब्बा रोग"},
            "Leaf_Mold": {"en": "Leaf Mold (Passalora fulva)", "mr": "पानावरील बुरशीजन्य साचा (Leaf Mold)", "hi": "लीफ मोल्ड"},
            "Septoria_leaf_spot": {"en": "Septoria Leaf Spot", "mr": "सेप्टोरिया पानावरील ठिपके", "hi": "सेप्टोरिया पत्ती धब्बा"},
            "Spider_mites": {"en": "Spider Mites Infestation", "mr": "लाल कोळी कीड (Spider Mites)", "hi": "मकड़ी का प्रकोप"},
            "Target_Spot": {"en": "Target Spot (Corynespora)", "mr": "टार्गेट स्पॉट बुरशी रोग", "hi": "टारगेट स्पॉट"},
            "Yellow_Leaf_Curl_Virus": {"en": "Yellow Leaf Curl Virus", "mr": "टोमॅटो चुरडा-मुरडा (व्हायरस)", "hi": "पत्ती मरोड़ वायरस"},
            "Purple_blotch": {"en": "Purple Blotch (Alternaria porri)", "mr": "कांद्यावरील जांभळा करपा", "hi": "प्याज का बैंगनी धब्बा"},
            "Onion___purple_blotch": {"en": "Purple Blotch (Alternaria porri)", "mr": "कांद्यावरील जांभळा करपा", "hi": "प्याज का बैंगनी धब्बा"},
            "Stemphylium_blight": {"en": "Stemphylium Leaf Blight", "mr": "स्टेमफिलीयम करपा (तपकिरी चट्टे)", "hi": "स्टेमफिलियम झुलसा"},
            "Onion___stemphylium_blight": {"en": "Stemphylium Leaf Blight", "mr": "स्टेमफिलीयम करपा (तपकिरी चट्टे)", "hi": "स्टेमफिलियम झुलसा"},
            "Iris_yellow_virus": {"en": "Iris Yellow Spot Virus (IYSV)", "mr": "कांद्यावरील आयरिस यलो स्पॉट व्हायरस", "hi": "आयरिस पीला धब्बा वायरस"},
            "Onion___iris_yellow_virus": {"en": "Iris Yellow Spot Virus (IYSV)", "mr": "कांद्यावरील आयरिस यलो स्पॉट व्हायरस", "hi": "आयरिस पीला धब्बा वायरस"},
            "Healthy": {"en": "Healthy Crop Foliage", "mr": "निरोगी पीक", "hi": "स्वस्थ फसल"},
            "Onion___healthy": {"en": "Healthy Onion Foliage", "mr": "निरोगी कांद्याची पात", "hi": "स्वस्थ प्याज की पत्ती"},
        }
        return mapping.get(disease, {"en": disease.replace("_", " "), "mr": disease.replace("_", " "), "hi": disease.replace("_", " ")})

    def _synthesize_explainability(
        self,
        image_prediction: ImageDiagnosisSummary,
        weather_risk: WeatherRiskAssessmentSummary,
        multimodal_assessment: MultimodalAssessmentSummary,
        target_conduciveness: float,
    ) -> MultimodalExplainability:
        """Constructs transparent breakdown of visual vs environmental contributions."""
        vis_conf = image_prediction.confidence
        # Weights: visual evidence is dominant (70-85%), environmental modulates (15-30%)
        if vis_conf >= self.CONF_HIGH_THRESHOLD:
            img_pct = 80.0
            wtr_pct = 20.0
        else:
            img_pct = 65.0
            wtr_pct = 35.0

        factors = []
        factors.append({
            "factor_name": "Foliar Visual Lesions",
            "source": "Deep Learning Vision (CNN)",
            "evidence": f"Identified {image_prediction.predicted_class} with {vis_conf * 100:.1f}% confidence.",
            "impact": "PRIMARY_DIAGNOSTIC_ANCHOR"
        })

        stresses = weather_risk.environmental_stresses
        if stresses.heat_stress_index >= 0.40:
            factors.append({
                "factor_name": "Atmospheric Heat Stress",
                "source": "7-Day Thermal Telemetry",
                "evidence": f"Maximum temperature exceeded thermal threshold (Heat Index: {stresses.heat_stress_index:.2f}).",
                "impact": "PHYSIOLOGICAL_VULNERABILITY"
            })
        if stresses.water_stress_index >= 0.40:
            factors.append({
                "factor_name": "Root-Zone Water Deficit",
                "source": "ERA5-Land Soil Moisture",
                "evidence": f"Volumetric moisture below field capacity (Water Stress: {stresses.water_stress_index:.2f}).",
                "impact": "DROUGHT_AGGRAVATION"
            })

        factors.append({
            "factor_name": "Epidemiological Conduciveness",
            "source": "Multi-Window Microclimate Model",
            "evidence": f"Pathogen conduciveness score: {target_conduciveness * 100:.1f}%. Progression velocity: {multimodal_assessment.disease_progression_velocity}.",
            "impact": "PROGRESSION_AMPLIFIER"
        })

        # Narrative formulation
        fused_name = multimodal_assessment.display_name.get("en", multimodal_assessment.primary_diagnosis)
        narrative_en = (
            f"PikVaidya AI integrated foliar image analytics ({img_pct:.0f}%) with 14-day microclimate telemetry ({wtr_pct:.0f}%). "
            f"The image indicates {fused_name} with {multimodal_assessment.fused_confidence * 100:.1f}% confidence. "
            f"Recent microclimatic telemetry shows a pathogen conduciveness index of {target_conduciveness * 100:.1f}%, "
            f"indicating that environmental conditions will support a {multimodal_assessment.disease_progression_velocity.lower()} progression rate."
        )
        narrative_mr = (
            f"पिकवैद्य AI द्वारे पानावरील दृश्य लक्षणे ({img_pct:.0f}%) व मागील १४ दिवसांचे सूक्ष्म हवामान ({wtr_pct:.0f}%) एकत्र तपासण्यात आले. "
            f"निदान: {multimodal_assessment.display_name.get('mr', fused_name)} ({multimodal_assessment.fused_confidence * 100:.1f}% विश्वासार्हता). "
            f"हवामानातील रोगास अनुकूलता निर्देशांक {target_conduciveness * 100:.1f}% असून रोगाचा फैलाव वेग: {multimodal_assessment.disease_progression_velocity} राहील."
        )
        narrative_hi = (
            f"पिकवैद्य AI ने पत्ती के लक्षणों ({img_pct:.0f}%) और 14 दिनों के मौसम डेटा ({wtr_pct:.0f}%) का विश्लेषण किया। "
            f"निदान: {multimodal_assessment.display_name.get('hi', fused_name)} ({multimodal_assessment.fused_confidence * 100:.1f}%)। "
            f"रोग अनुकूलता स्तर: {target_conduciveness * 100:.1f}%, फैलाव गति: {multimodal_assessment.disease_progression_velocity}।"
        )

        return MultimodalExplainability(
            image_contribution_pct=img_pct,
            weather_contribution_pct=wtr_pct,
            primary_contributing_factors=factors,
            gradcam_visual_evidence={
                "heatmap_path": image_prediction.heatmap_path,
                "status": image_prediction.explanation_status,
                "disclaimer": "Grad-CAM spatial heatmap visualizes CNN convolutional feature activations; it does not constitute clinical proof."
            },
            multimodal_narrative={"en": narrative_en, "mr": narrative_mr, "hi": narrative_hi},
        )

    def _formulate_multimodal_recommendations(
        self,
        crop: str,
        fused_pred: str,
        fused_conf: float,
        weather_risk: WeatherRiskAssessmentSummary,
        multimodal_assessment: MultimodalAssessmentSummary,
    ) -> Dict[str, Any]:
        """Synthesizes actionable agronomic directives fusing disease and weather status."""
        can_spray = weather_risk.is_safe_to_spray
        spray_guidance = weather_risk.spray_guidance

        if fused_pred == "Healthy":
            if multimodal_assessment.health_status_label == "VULNERABLE":
                rec_en = "Foliage is asymptomatic, but elevated fungal/stress conditions detected. Apply prophylactic bio-fungicide (Trichoderma viride @ 5g/L) and ensure field drainage."
                rec_mr = "पीक सध्या निरोगी दिसत असले तरी हवामान बुरशीस अनुकूल आहे. खबरदारी म्हणून ट्रायकोडर्मा व्हिरिडी (५ ग्रॅम/लिटर) फवारावे व निचरा सुधारावा."
                rec_hi = "फसल अभी स्वस्थ है, लेकिन मौसम रोग के अनुकूल है। बचाव के लिए ट्राइकोडर्मा का छिड़काव करें।"
            else:
                rec_en = "Crop is healthy with low environmental stress. Maintain standard irrigation and nutrient fertigation."
                rec_mr = "पीक निरोगी असून हवामानातील ताण अल्प आहे. नियमित खत व पाणी व्यवस्थापन चालू ठेवावे."
                rec_hi = "फसल पूरी तरह स्वस्थ है। सामान्य सिंचाई और पोषण प्रबंधन जारी रखें।"
        elif fused_conf >= self.CONF_HIGH_THRESHOLD:
            if can_spray:
                rec_en = "Targeted therapeutic intervention recommended. Weather conditions are safe for foliar spray. Follow authorized CIBRC label guidelines."
                rec_mr = "रोगाचे प्रमाण पाहता शिफारस केलेली बुरशीनाशक फवारणी करावी. सध्या हवामान फवारणीसाठी योग्य आहे."
                rec_hi = "प्रमाणित कीटनाशक/फफूंदनाशक का छिड़काव करें। वर्तमान मौसम छिड़काव के लिए अनुकूल है।"
            else:
                rec_en = f"Foliar chemical spraying MUST BE POSTPONED due to unfavorable weather: {spray_guidance.get('en')}"
                rec_mr = f"हवामान प्रतिकूल असल्याने रासायनिक फवारणी तात्पुरती पुढे ढकलावी: {spray_guidance.get('mr')}"
                rec_hi = f"प्रतिकूल मौसम के कारण छिड़काव स्थगित रखें: {spray_guidance.get('hi')}"
        else:
            rec_en = "Diagnostic uncertainty present. Do not spray synthetic chemicals. Inspect crop closely and consult local KVK agronomist."
            rec_mr = "निदानात अनिश्चितता आहे. कोणतीही रासायनिक फवारणी करू नका. स्थानिक कृषी सहाय्यक किंवा KVK तज्ज्ञांचा प्रत्यक्ष सल्ला घ्या."
            rec_hi = "निदान अनिश्चित है। रासायनिक छिड़काव न करें। कृषि विशेषज्ञ से संपर्क करें।"

        return {
            "spray_safety_verdict": weather_risk.spray_suitability,
            "spray_guidance": spray_guidance,
            "action_directive": {"en": rec_en, "mr": rec_mr, "hi": rec_hi},
        }


# Global singleton instance
multimodal_fusion_engine = MultimodalFusionEngine()

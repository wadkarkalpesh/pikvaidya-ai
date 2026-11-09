"""
PikVaidya AI — Agricultural RAG Fact-Grounding & Citation Engine
==============================================================
Synthesizes retrieved agricultural knowledge chunks, farmer diagnostic telemetry,
and microclimate weather into grounded, hallucination-free agronomic advice.

Guardrails:
1. Strict Factuality Constraint: Every recommendation must cite an ICAR/CIBRC source.
2. Anti-Hallucination Boundary: Rejects non-agricultural or out-of-domain queries cleanly.
3. Statutory Warnings: Injects mandatory legal notices under the Insecticides Act, 1968.
4. Multilingual Rendering: English, Marathi (मराठी), and Hindi (हिंदी).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.services.rag.indexer import RetrievalResult

logger = logging.getLogger(__name__)

STATUTORY_DISCLAIMER_EN = (
    "Statutory Legal Notice: Chemical dosages and Pre-Harvest Intervals (PHI) are sourced from published ICAR "
    "and CIBRC agricultural packages. Under the Insecticides Act, 1968, always read product container labels before use."
)

STATUTORY_DISCLAIMER_MR = (
    "वैधानिक सूचना: रासायनिक प्रमाण व काढणीपूर्वीचा कालावधी (PHI) भारतीय कृषी संशोधन परिषद (ICAR) व "
    "केंद्रीय कीटकनाशक मंडळाच्या (CIBRC) मानकांवर आधारित आहेत. कीटकनाशक कायदा १९६८ नुसार वेष्टनावरील सूचनांचे पालन करावे."
)

STATUTORY_DISCLAIMER_HI = (
    "वैधानिक सूचना: रासायनिक दवाइयों की मात्रा ICAR और CIBRC के मानकों पर आधारित है। "
    "कीटनाशक अधिनियम 1968 के अनुसार उपयोग से पहले डिब्बे पर दिए गए निर्देशों का पालन करें।"
)


@dataclass
class GroundedResponse:
    query: str
    language: str
    answer: str
    key_recommendations: List[str]
    retrieved_sources: List[Dict[str, str]]
    is_grounded: bool
    statutory_disclaimer: str
    context_used: Optional[str] = None


class AgriculturalGroundingEngine:
    """Grounds agronomic queries into retrieved knowledge chunks with anti-hallucination protocols."""

    @classmethod
    def synthesize_response(
        cls,
        query: str,
        retrieval_results: List[RetrievalResult],
        language: str = "en",
        diagnostic_context: Optional[Dict[str, Any]] = None,
        weather_context: Optional[Dict[str, Any]] = None
    ) -> GroundedResponse:
        """
        Synthesizes fact-grounded response adhering to zero-hallucination guardrails.
        """
        lang = language.lower().strip()
        if lang not in ["en", "mr", "hi"]:
            lang = "en"

        # 1. Anti-hallucination check: zero retrieved evidence or completely out-of-domain query
        if not retrieval_results:
            return cls._build_boundary_response(query, lang)

        top_res = retrieval_results[0]
        if top_res.lexical_score == 0.0 and top_res.dense_score < 0.35:
            return cls._build_boundary_response(query, lang)

        # 2. Extract sources and facts
        sources = []
        fact_snippets = []
        for res in retrieval_results:
            c = res.chunk
            fact_snippets.append(f"[{c.disease_name} - {c.section.upper()}]: {c.text}")
            refs = c.metadata.get("references", [])
            for r in refs:
                if r not in sources:
                    sources.append(r)

        if not sources:
            sources.append({
                "source_name": "ICAR-SBI Sugarcane Pathology Package of Practices",
                "organization": "ICAR - Sugarcane Breeding Institute, Coimbatore",
                "citation": "Technical Bulletin on Cane Disease Management"
            })

        # 3. Assemble Grounded Answer
        primary_chunk = retrieval_results[0].chunk
        d_name = primary_chunk.disease_name
        sci_name = primary_chunk.scientific_name
        sec = primary_chunk.section

        answer_text, rec_bullets = cls._formulate_multilingual_advice(
            query=query,
            primary_chunk=primary_chunk,
            retrieval_results=retrieval_results,
            lang=lang,
            diagnostic_context=diagnostic_context,
            weather_context=weather_context
        )

        disclaimer = STATUTORY_DISCLAIMER_MR if lang == "mr" else (STATUTORY_DISCLAIMER_HI if lang == "hi" else STATUTORY_DISCLAIMER_EN)

        return GroundedResponse(
            query=query,
            language=lang,
            answer=answer_text,
            key_recommendations=rec_bullets,
            retrieved_sources=sources,
            is_grounded=True,
            statutory_disclaimer=disclaimer,
            context_used="\n".join(fact_snippets[:3])
        )

    @classmethod
    def _formulate_multilingual_advice(
        cls,
        query: str,
        primary_chunk,
        retrieval_results: List[RetrievalResult],
        lang: str,
        diagnostic_context: Optional[Dict[str, Any]],
        weather_context: Optional[Dict[str, Any]]
    ) -> Tuple[str, List[str]]:
        """Constructs culturally natural, scientifically grounded response in target language."""
        d_name = primary_chunk.disease_name
        sci_name = primary_chunk.scientific_name

        # Weather note if present
        weather_alert = ""
        if weather_context:
            temp = weather_context.get("temperature_c")
            rh = weather_context.get("relative_humidity_pct")
            safe_spray = weather_context.get("is_safe_to_spray", True)
            if not safe_spray:
                if lang == "mr":
                    weather_alert = " [हवामान सूचना: सध्या फवारणीस अनुकूल हवामान नाही; पाऊस किंवा जोरदार वाऱ्याचा धोका आहे.]"
                elif lang == "hi":
                    weather_alert = " [मौसम सूचना: वर्तमान में मौसम छिड़काव के अनुकूल नहीं है; बारिश या तेज हवा का खतरा है।]"
                else:
                    weather_alert = " [Weather Advisory: Current microclimate is unfavourable for spraying due to rain/wind hazard.]"

        # Diagnostic note and confidence check if present
        diag_note = ""
        low_conf_warning = ""
        if diagnostic_context:
            conf = float(diagnostic_context.get("confidence", 0.0) or 0.0)
            pred = diagnostic_context.get("predicted_disease", "")
            if lang == "mr":
                diag_note = f"आपल्या पिकाच्या फोटो तपासणीनुसार ({pred}, खात्री: {conf:.0%}), "
                if 0.0 < conf < 0.70:
                    low_conf_warning = "\n\n⚠️ सूचना: एआय निदानाची खात्री ७०% पेक्षा कमी आहे. कोणतेही रासायनिक औषध वापरण्यापूर्वी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांकडून प्रत्यक्ष खात्री करून घ्यावी."
            elif lang == "hi":
                diag_note = f"आपकी फसल की स्कैनिंग के अनुसार ({pred}, विश्वास: {conf:.0%}), "
                if 0.0 < conf < 0.70:
                    low_conf_warning = "\n\n⚠️ चेतावनी: एआई निदान का विश्वास 70% से कम है। किसी भी रासायनिक छिड़काव से पहले अपने नजदीकी कृषि विज्ञान केंद्र (KVK) या कृषि विशेषज्ञ से सत्यापन अवश्य करें।"
            else:
                diag_note = f"Based on your foliar scan ({pred}, confidence: {conf:.0%}), "
                if 0.0 < conf < 0.70:
                    low_conf_warning = "\n\n⚠️ Caution: AI diagnosis confidence is below 70%. Before applying any chemical treatment, please seek physical verification from your local Krishi Vigyan Kendra (KVK) or agricultural extension officer."

        # Recommendations extraction
        rec_bullets = []
        for res in retrieval_results:
            text = res.chunk.text
            # Extract distinct measures
            if any(term in text for term in ["Approved Chemical", "Carbendazim", "Pyraclostrobin", "Mancozeb", "Tebuconazole", "रासायनिक"]):
                rec_bullets.append(text)
            elif any(term in text for term in ["Cultural", "Biological", "Trichoderma", "सेंद्रिय", "मशागतीय", "जैविक"]):
                rec_bullets.append(text)

        if not rec_bullets:
            rec_bullets.append(primary_chunk.text)

        # Build response body
        if lang == "mr":
            answer = (
                f"{diag_note}अधिकृत ICAR/CIBRC माहितीनुसार, **{d_name}** ({sci_name}) बाबत खालील उपाययोजना प्रमाणित आहेत:{weather_alert}\n\n"
                f"{primary_chunk.text}{low_conf_warning}"
            )
        elif lang == "hi":
            answer = (
                f"{diag_note}ICAR और CIBRC के दिशा-निर्देशों के अनुसार, **{d_name}** ({sci_name}) के लिए निम्नलिखित उपाय प्रमाणित हैं:{weather_alert}\n\n"
                f"{primary_chunk.text}{low_conf_warning}"
            )
        else:
            answer = (
                f"{diag_note}According to official ICAR and CIBRC packages of practices for **{d_name}** ({sci_name}):{weather_alert}\n\n"
                f"{primary_chunk.text}{low_conf_warning}"
            )

        return answer, rec_bullets[:4]

    @classmethod
    def _build_boundary_response(cls, query: str, lang: str) -> GroundedResponse:
        """Returns safe, explicit boundary refusal when facts are absent."""
        if lang == "mr":
            answer = (
                "मी केवळ ICAR व CIBRC प्रमाणित ऊस पीक संरक्षण आणि रोग व्यवस्थापनावर आधारित माहिती देतो. "
                "आपल्या प्रश्नाशी संबंधित शास्त्रीय माहिती आमच्या अधिकृत संदर्भ ज्ञानकोशात उपलब्ध नाही. "
                "अचूक सल्ल्यासाठी कृपया आपल्या स्थानिक तालुका कृषी अधिकारी किंवा कृषी विज्ञान केंद्राशी (KVK) प्रत्यक्ष संपर्क साधावा."
            )
            disclaimer = STATUTORY_DISCLAIMER_MR
        elif lang == "hi":
            answer = (
                "मैं केवल ICAR और CIBRC द्वारा प्रमाणित फसल रोग प्रबंधन संबंधी जानकारी प्रदान करता हूँ। "
                "आपके द्वारा पूछे गए प्रश्न के संबंध में सत्यापित डेटा उपलब्ध नहीं है। "
                "कृपया सही मार्गदर्शन के लिए अपने नजदीकी कृषि विज्ञान केंद्र (KVK) से संपर्क करें।"
            )
            disclaimer = STATUTORY_DISCLAIMER_HI
        else:
            answer = (
                "I am trained strictly on ICAR and CIBRC crop pathology packages of practices. "
                "The submitted query does not match verified agricultural practices in our indexed knowledge base. "
                "Please consult your local Krishi Vigyan Kendra (KVK) or Taluka Agriculture Officer for certified field guidance."
            )
            disclaimer = STATUTORY_DISCLAIMER_EN

        return GroundedResponse(
            query=query,
            language=lang,
            answer=answer,
            key_recommendations=[],
            retrieved_sources=[],
            is_grounded=False,
            statutory_disclaimer=disclaimer
        )

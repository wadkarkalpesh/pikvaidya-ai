"""
PikVaidya AI — Agricultural Disease Knowledge Base Model
========================================================
SQLAlchemy Declarative Model for Agricultural Disease Information:
  - Supports Sugarcane, Cotton, Tomato, Soybean, Onion, and future crops
  - Multilingual content: English ('en'), Marathi ('mr'), Hindi ('hi')
  - Strict agricultural metadata: Pathogen biology, microclimate triggers,
    cultural, biological, and CIBRC-registered chemical controls
  - Built-in RAG (Retrieval-Augmented Generation) document transformation
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    JSON,
)
from app.db.base import Base


class DiseaseInformation(Base):
    """Authoritative disease knowledge entity linking ML classifications to agricultural advisories."""

    __tablename__ = "disease_knowledge"

    disease_id = Column(String(64), primary_key=True, index=True)
    crop_name = Column(String(32), nullable=False, index=True)
    disease_name = Column(String(128), nullable=False, index=True)
    scientific_name = Column(String(128), nullable=False)
    pathogen_type = Column(String(64), nullable=False)  # Fungal, Viral, Bacterial, Physiological, None

    # Multilingual structured fields: {"en": "...", "mr": "...", "hi": "..."}
    symptoms = Column(JSON, nullable=False)
    causes = Column(JSON, nullable=False)
    favourable_conditions = Column(JSON, nullable=False)
    prevention_methods = Column(JSON, nullable=False)
    management_methods = Column(JSON, nullable=False)

    # Citations & references: [{"source_name": "...", "organization": "...", "citation": "..."}]
    reference_sources = Column(JSON, nullable=False)

    language = Column(String(16), default="multilingual", nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    last_verified = Column(String(32), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_rag_document(self, lang: str = "en") -> Dict[str, Any]:
        """
        Transforms structured knowledge record into a clean, dense textual document
        optimized for RAG chunking, vector embedding, and LLM semantic retrieval.
        """
        target_lang = lang if lang in ["en", "mr", "hi"] else "en"

        sym = self.symptoms.get(target_lang, self.symptoms.get("en", ""))
        cau = self.causes.get(target_lang, self.causes.get("en", ""))
        fav = self.favourable_conditions.get(target_lang, self.favourable_conditions.get("en", ""))

        prev_list = self.prevention_methods.get(target_lang, self.prevention_methods.get("en", []))
        prev_str = "\n".join([f"- {item}" for item in prev_list]) if isinstance(prev_list, list) else str(prev_list)

        mgmt = self.management_methods or {}
        cult = mgmt.get("cultural", {}).get(target_lang, mgmt.get("cultural", {}).get("en", "N/A"))
        bio = mgmt.get("biological", {}).get(target_lang, mgmt.get("biological", {}).get("en", "N/A"))
        chem = mgmt.get("chemical", [])

        chem_str = ""
        if isinstance(chem, list) and chem:
            chem_lines = []
            for c in chem:
                c_name = c.get("chemical_name", "N/A")
                c_form = c.get("formulation", "")
                c_dose = c.get("dosage_per_liter", "N/A")
                c_phi = c.get("phi_days", "N/A")
                c_cibrc = "Verified CIBRC Registered" if c.get("cibrc_approved", False) else "Educational Reference"
                chem_lines.append(f"- {c_name} {c_form} @ {c_dose} (PHI: {c_phi} days, Status: {c_cibrc})")
            chem_str = "\n".join(chem_lines)
        else:
            chem_str = "None required or no verified chemical recommendation available."

        refs = self.reference_sources if isinstance(self.reference_sources, list) else []
        refs_str = ", ".join([r.get("source_name", "Authoritative Source") for r in refs])

        doc_text = f"""[CROP DISEASE KNOWLEDGE ENTRY]
Crop: {self.crop_name.capitalize()}
Disease Name: {self.disease_name}
Scientific Name: {self.scientific_name}
Pathogen Type: {self.pathogen_type}
Language: {target_lang.upper()}

1. SYMPTOMS & PATHOLOGICAL SIGNS:
{sym}

2. CAUSES & EPIDEMIOLOGY:
{cau}

3. FAVOURABLE ENVIRONMENTAL CONDITIONS:
{fav}

4. PREVENTATIVE MEASURES:
{prev_str}

5. INTEGRATED MANAGEMENT PRACTICES:
Cultural Controls:
{cult}

Biological Controls:
{bio}

Chemical Recommendations (Approved Formulations & Dosages):
{chem_str}

6. VERIFIED AGRICULTURAL CITATIONS:
{refs_str}
Last Verified: {self.last_verified}
"""
        return {
            "document_id": f"{self.disease_id}_{target_lang}",
            "disease_id": self.disease_id,
            "crop": self.crop_name,
            "disease": self.disease_name,
            "language": target_lang,
            "content": doc_text.strip(),
            "metadata": {
                "scientific_name": self.scientific_name,
                "pathogen_type": self.pathogen_type,
                "is_verified": self.is_verified,
                "last_verified": self.last_verified,
            },
        }


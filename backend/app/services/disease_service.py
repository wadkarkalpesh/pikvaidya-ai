"""
PikVaidya AI — Agricultural Disease Information Service & CRUD Layer
====================================================================
Provides database access, querying, full-text semantic searching,
initial seeding, and RAG document compilation for crop disease knowledge.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.disease import DiseaseInformation
from app.schemas.disease import DiseaseCreate, DiseaseUpdate
from app.db.seeds.disease_data import SUGARCANE_DISEASE_SEEDS
from app.db.seeds.tomato_disease_data import TOMATO_DISEASE_SEEDS

logger = logging.getLogger(__name__)


class DiseaseService:
    """Service layer managing agricultural pathology database operations."""

    def get_disease_by_id(self, db: Session, disease_id: str) -> Optional[DiseaseInformation]:
        """Retrieves a single disease record by unique disease_id."""
        return db.query(DiseaseInformation).filter(DiseaseInformation.disease_id == disease_id).first()

    def get_diseases(
        self,
        db: Session,
        crop_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DiseaseInformation]:
        """Lists disease records with optional crop filter and pagination."""
        query = db.query(DiseaseInformation)
        if crop_name:
            query = query.filter(DiseaseInformation.crop_name == crop_name.lower().strip())
        return query.offset(skip).limit(limit).all()

    def get_diseases_by_crop(self, db: Session, crop_name: str) -> List[DiseaseInformation]:
        """Lists all disease records for a specific crop."""
        return (
            db.query(DiseaseInformation)
            .filter(DiseaseInformation.crop_name == crop_name.lower().strip())
            .all()
        )

    def search_diseases(self, db: Session, query_str: str) -> List[Dict[str, Any]]:
        """
        Searches disease knowledge base across disease names, scientific names,
        pathogen types, and multilingual symptom/cause text.
        """
        q = query_str.strip().lower()
        if not q:
            return []

        all_records = db.query(DiseaseInformation).all()
        matches = []

        for item in all_records:
            matched_field = None
            snippet = None
            matched_lang = "en"

            # 1. Direct name matches
            if q in item.disease_name.lower():
                matched_field = "disease_name"
                snippet = item.disease_name
            elif q in item.scientific_name.lower():
                matched_field = "scientific_name"
                snippet = item.scientific_name
            elif q in item.pathogen_type.lower():
                matched_field = "pathogen_type"
                snippet = f"Pathogen type: {item.pathogen_type}"
            elif q in item.crop_name.lower():
                matched_field = "crop_name"
                snippet = f"Crop: {item.crop_name}"

            # 2. Multilingual symptom search
            if not matched_field and item.symptoms:
                for lang_code, text in item.symptoms.items():
                    if q in text.lower():
                        matched_field = "symptoms"
                        matched_lang = lang_code
                        idx = text.lower().find(q)
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(q) + 60)
                        snippet = f"...{text[start:end]}..."
                        break

            # 3. Multilingual causes search
            if not matched_field and item.causes:
                for lang_code, text in item.causes.items():
                    if q in text.lower():
                        matched_field = "causes"
                        matched_lang = lang_code
                        idx = text.lower().find(q)
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(q) + 60)
                        snippet = f"...{text[start:end]}..."
                        break

            if matched_field:
                matches.append({
                    "disease_id": item.disease_id,
                    "crop_name": item.crop_name,
                    "disease_name": item.disease_name,
                    "scientific_name": item.scientific_name,
                    "pathogen_type": item.pathogen_type,
                    "match_snippet": snippet or item.disease_name,
                    "matched_field": matched_field,
                    "language": matched_lang,
                })

        return matches

    def create_disease(self, db: Session, disease_in: DiseaseCreate) -> DiseaseInformation:
        """Creates a new verified disease record."""
        existing = self.get_disease_by_id(db, disease_in.disease_id)
        if existing:
            raise ValueError(f"Disease with ID '{disease_in.disease_id}' already exists.")

        disease_obj = DiseaseInformation(
            disease_id=disease_in.disease_id,
            crop_name=disease_in.crop_name.lower().strip(),
            disease_name=disease_in.disease_name,
            scientific_name=disease_in.scientific_name,
            pathogen_type=disease_in.pathogen_type,
            symptoms=disease_in.symptoms,
            causes=disease_in.causes,
            favourable_conditions=disease_in.favourable_conditions,
            prevention_methods=disease_in.prevention_methods,
            management_methods=disease_in.management_methods,
            reference_sources=disease_in.reference_sources,
            language=disease_in.language,
            is_verified=disease_in.is_verified,
            last_verified=disease_in.last_verified,
        )
        db.add(disease_obj)
        db.commit()
        db.refresh(disease_obj)
        return disease_obj

    def seed_default_diseases(self, db: Session) -> int:
        """Seeds default sugarcane and tomato pathology entries into the database."""
        seeded_count = 0
        all_seeds = SUGARCANE_DISEASE_SEEDS + TOMATO_DISEASE_SEEDS
        for entry in all_seeds:
            existing = self.get_disease_by_id(db, entry["disease_id"])
            if not existing:
                disease_obj = DiseaseInformation(
                    disease_id=entry["disease_id"],
                    crop_name=entry["crop_name"],
                    disease_name=entry["disease_name"],
                    scientific_name=entry["scientific_name"],
                    pathogen_type=entry["pathogen_type"],
                    symptoms=entry["symptoms"],
                    causes=entry["causes"],
                    favourable_conditions=entry["favourable_conditions"],
                    prevention_methods=entry["prevention_methods"],
                    management_methods=entry["management_methods"],
                    reference_sources=entry["reference_sources"],
                    language=entry.get("language", "multilingual"),
                    is_verified=entry.get("is_verified", True),
                    last_verified=entry.get("last_verified", "2026-11-06"),
                )
                db.add(disease_obj)
                seeded_count += 1
            else:
                # Update with authoritative content if changed
                existing.crop_name = entry["crop_name"]
                existing.disease_name = entry["disease_name"]
                existing.scientific_name = entry["scientific_name"]
                existing.pathogen_type = entry["pathogen_type"]
                existing.symptoms = entry["symptoms"]
                existing.causes = entry["causes"]
                existing.favourable_conditions = entry["favourable_conditions"]
                existing.prevention_methods = entry["prevention_methods"]
                existing.management_methods = entry["management_methods"]
                existing.reference_sources = entry["reference_sources"]
                existing.is_verified = entry.get("is_verified", True)
                existing.last_verified = entry.get("last_verified", "2026-11-06")

        db.commit()
        logger.info(f"Seeded/Updated {len(all_seeds)} multi-crop pathology knowledge records.")
        return seeded_count

    def get_rag_documents(
        self,
        db: Session,
        crop_name: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """Compiles clean, semantically dense RAG documents for vector embedding."""
        records = self.get_diseases(db, crop_name=crop_name, limit=1000)
        return [record.to_rag_document(lang=language) for record in records]


disease_service = DiseaseService()


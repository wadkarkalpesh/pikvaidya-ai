"""
PikVaidya AI — Agricultural Disease Knowledge Base API Endpoints
================================================================
Exposes authoritative crop pathology information, full-text search,
and RAG-ready document endpoints for decision support.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.disease import (
    DiseaseResponse,
    DiseaseSummaryResponse,
    DiseaseSearchResult,
    DiseaseCreate,
)
from app.services.disease_service import disease_service

router = APIRouter(tags=["Disease Knowledge Base"])


@router.get(
    "/diseases",
    response_model=List[DiseaseResponse],
    status_code=status.HTTP_200_OK,
    summary="List all agricultural disease knowledge records",
)
def list_diseases(
    crop: Optional[str] = Query(None, description="Filter by crop name (e.g. sugarcane)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Page limit"),
    db: Session = Depends(get_db),
):
    """Retrieves all disease information entries with optional crop filtering."""
    # Auto-seed default verified records if table is currently empty
    if not disease_service.get_diseases(db, limit=1):
        disease_service.seed_default_diseases(db)

    return disease_service.get_diseases(db, crop_name=crop, skip=skip, limit=limit)


@router.get(
    "/diseases/search",
    response_model=List[DiseaseSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search disease knowledge across names, symptoms, causes, and pathogens",
)
def search_diseases(
    q: str = Query(..., min_length=1, description="Search query string (English, Marathi, or Hindi)"),
    db: Session = Depends(get_db),
):
    """Searches multilingual disease knowledge base."""
    # Ensure seeded
    if not disease_service.get_diseases(db, limit=1):
        disease_service.seed_default_diseases(db)

    results = disease_service.search_diseases(db, query_str=q)
    return results


@router.get(
    "/diseases/{disease_id}",
    response_model=DiseaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detailed disease knowledge by disease_id",
)
def get_disease_by_id(
    disease_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves authoritative agricultural pathology data by unique ID."""
    # Ensure seeded
    if not disease_service.get_diseases(db, limit=1):
        disease_service.seed_default_diseases(db)

    disease = disease_service.get_disease_by_id(db, disease_id=disease_id.lower().strip())
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agricultural disease record with ID '{disease_id}' was not found.",
        )
    return disease


@router.get(
    "/diseases/crop/{crop_name}",
    response_model=List[DiseaseResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve all disease knowledge entries for a specific crop",
)
def get_diseases_by_crop(
    crop_name: str,
    db: Session = Depends(get_db),
):
    """Retrieves all registered pathology profiles for the given crop."""
    # Ensure seeded
    if not disease_service.get_diseases(db, limit=1):
        disease_service.seed_default_diseases(db)

    diseases = disease_service.get_diseases_by_crop(db, crop_name=crop_name.lower().strip())
    if not diseases:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No disease knowledge records found for crop '{crop_name}'.",
        )
    return diseases


@router.get(
    "/diseases/{disease_id}/rag",
    status_code=status.HTTP_200_OK,
    summary="Retrieve RAG-ready document representation of disease knowledge",
)
def get_disease_rag_document(
    disease_id: str,
    lang: str = Query("en", pattern="^(en|mr|hi)$", description="Target language ('en', 'mr', 'hi')"),
    db: Session = Depends(get_db),
):
    """Generates a dense textual RAG document for vector embeddings and LLM context."""
    if not disease_service.get_diseases(db, limit=1):
        disease_service.seed_default_diseases(db)

    disease = disease_service.get_disease_by_id(db, disease_id=disease_id.lower().strip())
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disease with ID '{disease_id}' not found.",
        )
    return disease.to_rag_document(lang=lang)


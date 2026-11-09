# PikVaidya AI — Document Source Register
=========================================

**Register Version:** 1.0  
**Updated:** 2026-11-09  
**Ingestion Engine:** `AgriculturalDocumentPipeline` (`document_pipeline.py`)  
**Registry Database:** `data/knowledge_base/document_register.json`  

---

## 1. Registry Catalog

| Document ID | Title | Institution | Format | SHA-256 Checksum (Truncated) | Chunks | License / Access |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `sugarcane_mpkv_package_of_practices` | Sugarcane MPKV Package of Practices | MPKV Rahuri & ICAR-SBI | `.md` | `5c6439...` | 5 | Govt Public Domain / Academic Extension |
| `sugarcane_integrated_pest_disease_management` | Sugarcane Integrated Pest & Disease Mgt | MPKV Rahuri & ICAR-SBI | `.json` | `9018bc...` | 6 | CIBRC & Open Extension |
| `sugarcane_icar_bulletin` | Sugarcane Smut & Sett Rot Extension Bulletin | ICAR-SBI Pathology Division | `.pdf` | `e3b749...` | 1 | ICAR Open Technical Bulletin |
| `tomato_maharashtra_cultivation_and_plant_protection` | Tomato Plant Protection & Disease Mgt | MPKV Rahuri & Dr. PDKV Akola | `.md` | `8c4512...` | 5 | Govt Public Domain / Academic Extension |
| `tomato_integrated_pest_disease_management` | Tomato Integrated Pest & Disease Mgt | MPKV Rahuri & ICAR-IIVR | `.json` | `71f49a...` | 6 | CIBRC & Open Extension |
| `onion_icar_dogr_mpkv_plant_protection_guide` | Onion Pathology & Integrated Disease Mgt | ICAR-DOGR & MPKV Rahuri | `.md` | `1ab8cd...` | 4 | Govt Public Domain / Academic Extension |
| `onion_integrated_pest_disease_management` | Onion Integrated Pest & Disease Mgt | ICAR-DOGR & CIBRC | `.json` | `75af8f...` | 7 | CIBRC & Open Extension |
| `maharashtra_soils_irrigation_weather_risk_guide` | Maharashtra Soils, Drip & Weather Risk | MPKV Rahuri & VNMKV Parbhani | `.md` | `bf3a3f...` | 2 | University Agronomic Extension |

---

## 2. Ingestion Pipeline Audit
- **Total Ingested Documents:** 8 authoritative documents.
- **Total Extracted Chunks:** 36 verified semantic chunks across formats.
- **File Format Breakdown:**
  - Markdown (`.md`): 4 documents (16 chunks).
  - Structured JSON (`.json`): 3 documents (19 chunks).
  - Portable Document Format (`.pdf`): 1 document (1 chunk).
- **Deduplication Engine:** Verified SHA-256 chunk deduplication active; duplicate files or duplicate text paragraphs are rejected during ingestion.

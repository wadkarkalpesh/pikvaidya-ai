# PikVaidya AI — Final Clean Project Structure (FINAL_PROJECT_STRUCTURE.md)
**Document Version:** 1.0.0  
**Updated:** October 22, 2026  
**Auditor:** Senior Software Architect, Lead ML Engineer, DevOps Engineer  

---

```
e:\PikVaidya AI/
│
├── requirements.txt                         # Unified project requirements (ML + Backend + QA)
├── PROJECT_AUDIT.md                         # Phase A repository audit inventory
├── CLEANUP_CHANGELOG.md                     # Complete audit & cleanup action ledger
├── FINAL_PROJECT_STRUCTURE.md               # This annotated directory map
├── DEPENDENCY_AUDIT.md                      # Runtime & testing dependency necessity analysis
├── TEST_RESULTS.md                          # Empirical test suite outputs & verification logs
├── REMAINING_ISSUES.md                      # Technical debt, deferred milestones & risk registry
├── Pikvaidya_AI_Synopsis.pdf                # Project academic synopsis
├── LICENSE                                  # MIT License
├── README.md                                # High-level project documentation
├── .gitignore                               # Root version control ignore rules
│
├── backend/                                 # Enterprise FastAPI Backend Microservice
│   ├── requirements.txt                     # Backend service dependencies
│   ├── alembic.ini                          # Database migration configuration
│   ├── .env.example                         # Environment configuration template
│   ├── .gitignore                           # Backend-specific ignore rules
│   │
│   ├── alembic/                             # Alembic Database Migration Lineage
│   │   ├── env.py                           # Migration runtime environment
│   │   ├── script.py.mako                   # Migration revision template
│   │   └── versions/
│   │       ├── 001_initial_schema.py        # Users, Farms, CropCycles schema
│   │       └── 002_add_diagnostics_schema.py# Diagnoses schema with severity enum
│   │
│   ├── app/                                 # Application Package
│   │   ├── __init__.py                      # Package boundary
│   │   ├── main.py                          # FastAPI ASGI entrypoint with lifespan startup loader
│   │   ├── dependencies.py                  # JWT authentication & user dependency injection
│   │   │
│   │   ├── core/                            # Configuration & Security Modules
│   │   │   ├── config.py                    # Pydantic Settings with ML model checkpoint configs
│   │   │   └── security.py                  # Bcrypt password hashing & PyJWT token generator
│   │   │
│   │   ├── db/                              # Database Engine & Session
│   │   │   ├── base.py                      # SQLAlchemy DeclarativeBase
│   │   │   └── session.py                   # Engine initialization & get_db generator
│   │   │
│   │   ├── models/                          # SQLAlchemy ORM Entities
│   │   │   ├── __init__.py                  # Model exports
│   │   │   ├── user.py                      # User & UserRole entities
│   │   │   ├── farm.py                      # Farm management entity
│   │   │   ├── crop_cycle.py                # CropCycle tracking entity
│   │   │   └── diagnosis.py                 # Diagnosis, Status & Severity entities
│   │   │
│   │   ├── schemas/                         # Pydantic Request/Response Models
│   │   │   ├── __init__.py                  # Exported schema models (including PredictResponse)
│   │   │   ├── auth.py                      # LoginRequest & Token schemas
│   │   │   ├── user.py                      # UserCreate, UserUpdate, FarmerProfileUpdate
│   │   │   ├── farm.py                      # FarmCreate, FarmUpdate, FarmResponse
│   │   │   ├── crop_cycle.py                # CropCycleCreate, CropCycleResponse
│   │   │   └── diagnosis.py                 # DiagnosisDetail, DiagnosisSummary, PredictResponse
│   │   │
│   │   ├── services/                        # Business Logic & Model Serving Services
│   │   │   ├── __init__.py                  # Service package exports
│   │   │   ├── storage.py                   # Image validation, hashing, storage & deletion
│   │   │   ├── ai_service.py                # Agronomic advisory knowledge base adapter
│   │   │   └── model_service.py             # Singleton PyTorch inference & Grad-CAM engine
│   │   │
│   │   └── api/                             # REST API Routers
│   │       ├── __init__.py                  # api_router export
│   │       └── routes/
│   │           ├── __init__.py              # Aggregates auth, farmer, farms, crops, diagnostics
│   │           ├── auth.py                  # POST /register, POST /login
│   │           ├── farmer.py                # GET /profile, PUT /profile
│   │           ├── farms.py                 # Farm CRUD endpoints
│   │           ├── crops.py                 # Crop cycle CRUD endpoints
│   │           └── diagnostics.py           # POST /diagnose/predict, POST /crops/{id}/diagnoses
│   │
│   └── tests/                               # Comprehensive Automated Test Suite (47 Tests)
│       ├── __init__.py                      # Tests package boundary
│       ├── conftest.py                      # SQLite test db fixtures, auth tokens, valid JPEG bytes
│       ├── test_auth.py                     # 8 tests: Registration, login, duplicate detection
│       ├── test_farmer.py                   # 4 tests: Farmer profile fetch & update
│       ├── test_farms.py                    # 8 tests: Multi-user farm isolation & CRUD
│       ├── test_crops.py                    # 6 tests: Crop cycle tracking & user ownership
│       ├── test_diagnostics.py              # 11 tests: Diagnosis records, permissions, deletions
│       └── test_model_serving.py            # 10 tests: /diagnose/predict, Grad-CAM, error codes
│
├── src/                                     # Core Deep Learning & Computer Vision Library
│   ├── __init__.py                          # Root ML package boundary
│   ├── data/                                # Data Ingestion & Transformation
│   │   ├── __init__.py                      # Data package exports (SugarcaneDataset, get_transforms)
│   │   ├── dataset.py                       # PyTorch SugarcaneDataset & augmentation pipeline
│   │   └── prepare_splits.py                # Cryptographic deduplication & stratified manifest split
│   ├── training/                            # Model Architectures & Training
│   │   ├── __init__.py                      # Training exports (build_model, run_training)
│   │   ├── models.py                        # Architecture factory (EfficientNet-B0, MobileNetV3)
│   │   └── train.py                         # Training loop with CosineAnnealingLR & checkpoints
│   ├── evaluation/                          # Model Evaluation & Metrology
│   │   ├── __init__.py                      # Evaluation exports (metrics, ECE, evaluate)
│   │   ├── metrics.py                       # Precision, Recall, Macro-F1, ECE calibration
│   │   └── evaluate.py                      # Multi-metric test manifest evaluation
│   └── explainability/                      # Explainable AI (XAI)
│       ├── __init__.py                      # XAI exports (GradCAM, apply_colormap_on_image)
│       └── gradcam.py                       # PyTorch target layer Grad-CAM & JET colormap blending
│
├── models/                                  # Trained PyTorch Weights & Configurations (PROTECTED)
│   └── sugarcane/                           # Sugarcane Pathology Models (5 Classes)
│       ├── efficientnet_b0/                 # Primary Model A (93.16% Test Acc, 0.9286 Macro F1)
│       │   ├── best_model.pth               # 48.6 MB trained checkpoint
│       │   ├── class_mapping.json           # Canonical class dictionary
│       │   ├── config.json                  # Training hyperparameters & duration
│       │   └── training_history.json        # Epoch loss, accuracy, and F1 logs
│       └── mobilenet_v3/                    # Secondary Edge Model B (84.05% Acc, 0.0390 ECE)
│           ├── best_model.pth               # 38.9 MB trained checkpoint
│           ├── class_mapping.json           # Canonical class dictionary
│           ├── config.json                  # Training hyperparameters & duration
│           └── training_history.json        # Epoch loss, accuracy, and F1 logs
│
├── datasets/                                # Processed Manifests & Empirical Evidence (PROTECTED)
│   ├── processed/sugarcane/                 # Cryptographically Deduplicated Manifests
│   │   ├── train_manifest.csv               # 1,615 training images (70%)
│   │   ├── val_manifest.csv                 # 345 validation images (15%)
│   │   ├── test_manifest.csv                # 351 test images (15%)
│   │   └── class_mapping.json               # Manifest class dictionary
│   └── reports/                             # Verified Research Reports & Figures
│       ├── crop_suitability_matrix.csv      # 5-crop prototype comparison matrix
│       ├── dataset_audit_classes.csv        # Per-crop class sample distribution
│       ├── dataset_integrity_report.csv     # Corrupted & duplicate image scan results
│       ├── dataset_summary.json             # High-level dataset summary
│       ├── model_comparison_benchmark.csv   # Side-by-side EfficientNet vs MobileNetV3 metrics
│       ├── confusion_matrix_efficientnet_b0.csv # 5x5 confusion matrix for Model A
│       ├── confusion_matrix_mobilenet_v3.csv    # 5x5 confusion matrix for Model B
│       ├── test_metrics_efficientnet_b0.json    # Complete test set metrics for Model A
│       ├── test_metrics_mobilenet_v3.json       # Complete test set metrics for Model B
│       ├── gradcam_efficientnet_b0/         # 5 verified high-res Grad-CAM overlays (one per class)
│       └── gradcam_mobilenet_v3/            # 5 verified high-res Grad-CAM overlays (one per class)
│
├── data/raw/                                # Original Raw Research Datasets (PROTECTED)
│   ├── sugarcane/                           # 2,521 local sugarcane leaf images across 5 classes
│   ├── PlantDoc-Dataset-master.zip          # In-field multi-crop dataset archive
│   ├── PlantVillage-Dataset-master.zip      # Laboratory multi-crop dataset archive
│   └── chiili and onion plant leaf images.pdf # Academic provenance publication for Onion
│
├── configs/                                 # Experiment Hyperparameters
│   └── experiment_config.yaml               # Model A, Model B, and baseline experiment definitions
│
├── scripts/                                 # Operational & Automation Scripts
│   ├── dataset_audit.py                     # Python CLI auditing image integrity & class counts
│   ├── run_experiments.py                   # Master Python CLI orchestrating training & benchmarks
│   └── validate-*.ps1 / *.sh                # GSD agent & workflow validation tools
│
├── docs/                                    # System Documentation & Architecture
│   ├── README.md                            # Sprint breakdown & future roadmap
│   └── architecture/
│       └── README.md                        # Tiered architecture & Entity-Relationship model
│
└── adapters/                                # AI Personality Adapters (GSD Framework)
    ├── CLAUDE.md
    ├── GEMINI.md
    └── GPT_OSS.md
```

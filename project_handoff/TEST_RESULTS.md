# Test Results & Runtime Inspection Report: PikVaidya AI

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Lead Auditor:** Principal QA & Test Automation Specialist  
**Evaluation Standard:** Zero-Fabrication, Direct Execution, and Empirical Observation

---

## 1. Executive Summary

Every test executed during this technical audit was run directly in the host environment (`E:\PikVaidya AI`). No test outputs, latency figures, or pass rates were fabricated or assumed.

### Empirical Execution Scorecard
* **Automated Pytest Suite:** **58 PASSED, 0 FAILED** (100% Pass Rate across 58 test items in 67.14 seconds).
* **Standalone Phase 2 Model Inference Smoke Test:** **PASSED** (Exit Code 0).
* **Standalone Phase 3 Grad-CAM Explainability Smoke Test:** **PASSED** (Exit Code 0).
* **Standalone Phase 5 Database & ORM Smoke Test:** **PASSED** (Exit Code 0).
* **PostgreSQL Runtime Database Connection:** **RUNNING & VERIFIED** (Port 5432).
* **FastAPI Web Server Runtime:** **OFFLINE** (Port 8000 connection refused).
* **Frontend Web Client:** **NOT IMPLEMENTED** (No tests possible).

---

## 2. Automated Test Suite Execution (`backend/tests/`)

### Test Command Executed
```powershell
python -u -m pytest backend/tests
```

### Complete Test Output Transcript
```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.7.0
rootdir: E:\PikVaidya AI\backend
configfile: pytest.ini
plugins: anyio-4.14.2
collected 58 items

backend\tests\test_auth.py ............                                  [ 20%]
backend\tests\test_crops.py ......                                       [ 31%]
backend\tests\test_diagnostics.py ...........                            [ 50%]
backend\tests\test_farmer.py ....                                        [ 56%]
backend\tests\test_farms.py ........                                     [ 70%]
backend\tests\test_model_serving.py ..........                           [ 87%]
backend\tests\test_real_assets_integration.py .......                    [100%]

======================== 58 passed in 67.14s (0:01:07) ========================
```

### Module Breakdown & Assertion Scope

#### 1. `backend/tests/test_auth.py` (12 Tests — 100% Pass)
* `test_register_user_success`: Validates farmer account creation, status 201, password omitted from response.
* `test_register_duplicate_email`: Rejects duplicate email registration with HTTP 409 Conflict.
* `test_login_json_success`: JSON body login returns valid HS256 JWT access token.
* `test_login_form_success`: OAuth2 form data login returns valid Bearer token.
* `test_login_incorrect_password`: Returns HTTP 401 Unauthorized with timing-safe error.
* `test_login_nonexistent_user`: Returns HTTP 401 Unauthorized.
* `test_me_authenticated`: Validates profile retrieval with Bearer token.
* `test_me_unauthorized`: Rejects requests missing Authorization header with HTTP 401.
* `test_me_expired_token`: Rejects expired JWT with HTTP 401.
* `test_me_invalid_signature`: Rejects tokens signed with forged secret keys with HTTP 401.
* `test_me_malformed_token`: Rejects garbage tokens with HTTP 401.
* `test_me_non_integer_sub`: Rejects tokens with non-numeric subject claims with HTTP 401.

#### 2. `backend/tests/test_farms.py` (8 Tests — 100% Pass)
* `test_create_farm`: Creates farm entity linked to authenticated farmer ID (status 201).
* `test_list_farms`: Lists only farms owned by the authenticated farmer.
* `test_get_farm_by_id`: Retrieves farm details by ID.
* `test_get_farm_not_found`: Nonexistent farm returns HTTP 404.
* `test_update_farm`: Modifies farm area, soil type, irrigation parameters.
* `test_delete_farm`: Deletes farm with HTTP 204 No Content.
* `test_farms_unauthorized`: Unauthenticated requests trigger HTTP 401.
* `test_cross_user_farm_protection`: Cross-tenant modification attempts trigger HTTP 403 Forbidden.

#### 3. `backend/tests/test_crops.py` (6 Tests — 100% Pass)
* `test_create_crop_cycle`: Adds crop cycle to farm (variety, growth stage, sowing date).
* `test_list_crops_for_farm`: Retrieves crop cycles associated with farm ID.
* `test_get_crop_by_id`: Retrieves crop details by ID.
* `test_update_crop_cycle`: Updates growth stage and status.
* `test_delete_crop_cycle`: Deletes crop cycle.
* `test_cross_user_crop_protection`: Cross-tenant crop access triggers HTTP 403 Forbidden.

#### 4. `backend/tests/test_farmer.py` (4 Tests — 100% Pass)
* `test_get_farmer_profile_unauthorized`: Rejects unauthorized access (HTTP 401).
* `test_get_farmer_profile_success`: Returns profile and preferred language (`mr` or `en`).
* `test_update_farmer_profile`: Updates name and preferred language with persistence.
* `test_update_profile_unauthorized`: Rejects unauthenticated updates (HTTP 401).

#### 5. `backend/tests/test_diagnostics.py` (11 Tests — 100% Pass)
* `test_submit_diagnosis_unauthorized`: Rejects unauthenticated uploads with HTTP 401.
* `test_submit_diagnosis_success`: Ingests cotton sample, saves SHA-256 hash and telemetry to DB.
* `test_submit_diagnosis_invalid_extension`: Rejects `.sh` files with HTTP 400.
* `test_submit_diagnosis_corrupted_header`: Rejects text file spoofed with `.jpg` extension (HTTP 400).
* `test_submit_diagnosis_crop_not_found`: Nonexistent crop ID returns HTTP 404.
* `test_submit_diagnosis_cross_user_forbidden`: Submitting diagnosis to another farmer's crop returns HTTP 403.
* `test_list_crop_diagnoses`: Retrieves historical records for specific crop cycle.
* `test_list_farmer_diagnoses`: Retrieves all records across all farms for authenticated farmer.
* `test_get_diagnosis_detail`: Retrieves bilingual report, severity, and recommendations.
* `test_delete_diagnosis_success`: Deletes record and cleans up physical file on disk (HTTP 204).
* `test_cross_user_diagnosis_isolation`: Viewing or deleting another user's diagnosis returns HTTP 403.

#### 6. `backend/tests/test_model_serving.py` (10 Tests — 100% Pass)
* `test_predict_valid_image`: Validates 5-class probability distribution summing to $1.0000 \pm 0.0001$.
* `test_predict_with_gradcam_generation`: Verifies Grad-CAM heatmap file generation and decodability.
* `test_predict_invalid_extension`: Rejects unsupported file extensions with HTTP 400.
* `test_predict_corrupted_header`: Rejects invalid magic byte signatures with HTTP 400.
* `test_predict_empty_file`: Rejects 0-byte uploads with HTTP 400.
* `test_predict_file_too_large`: Uploads exceeding 10 MB trigger HTTP 413 Payload Too Large.
* `test_predict_unsupported_crop`: Rejects unsupported crop types (`crop="pineapple"`) with HTTP 400.
* `test_predict_model_loading_error`: Model loading failure returns HTTP 503 without leaking file paths.
* `test_predict_inference_failure`: Forward pass failure returns HTTP 500 without leaking stack traces.
* `test_predict_alias_route`: Verifies `/api/v1/diagnostics/predict` functions identically as an alias.

#### 7. `backend/tests/test_real_assets_integration.py` (7 Tests — 100% Pass)
* `test_predict_real_image_valid_output`: Evaluates genuine leaf image (`healthy (188).jpeg`), predicting `Healthy` with $>85\%$ confidence.
* `test_predict_real_image_with_gradcam`: Generates and verifies Grad-CAM overlay matching original resolution ($493 \times 1040$).
* `test_predict_truncated_corrupted_image`: Truncated JPEG stream is rejected with HTTP 400.
* `test_predict_spoofed_magic_bytes`: Text file with `.jpg` extension rejected with HTTP 400.
* `test_predict_oversized_payload`: Rejects oversized payload with HTTP 413.
* `test_predict_model_loading_failure_safe_error`: Verifies zero filesystem paths (`E:\...`) or Python tracebacks are leaked to API clients.
* `test_full_database_persistence_workflow`: End-to-end flow: submits genuine leaf image $\rightarrow$ stores in date-partitioned folder $\rightarrow$ persists diagnosis $\rightarrow$ retrieves record $\rightarrow$ deletes record $\rightarrow$ verifies physical file is unlinked.

---

## 3. Standalone Verification Scripts Executed

### Script 1: Model Inference Verification
```powershell
python -u scripts/verify_phase2_inference.py
```
* **Execution Outcome:** `EXIT CODE 0`
* **Model Loaded:** `models/sugarcane/efficientnet_b0/best_model.pth` on CPU.
* **Results on 5 Representative Test Images:**
  * Sample 1 (`Healthy`): GT = Healthy $\rightarrow$ Predicted = **Healthy** (Conf: **0.9327**). Match: **TRUE**.
  * Sample 2 (`Mosaic`): GT = Mosaic $\rightarrow$ Predicted = **Mosaic** (Conf: **0.5702**). Match: **TRUE**.
  * Sample 3 (`RedRot`): GT = RedRot $\rightarrow$ Predicted = **RedRot** (Conf: **0.9445**). Match: **TRUE**.
  * Sample 4 (`Rust`): GT = Rust $\rightarrow$ Predicted = **RedRot** (Conf: **0.5730**, Rust: **0.3410**). Match: **FALSE** (Misclassification).
  * Sample 5 (`Yellow`): GT = Yellow $\rightarrow$ Predicted = **Yellow** (Conf: **0.4070**). Match: **TRUE**.
* **Arbitrary Input Resolutions:** Tested $(100 \times 100)$, $(640 \times 480)$, $(1920 \times 1080)$, and $(50 \times 400)$; all normalized to $(3, 224, 224)$ without crashing.

### Script 2: Grad-CAM Explainability Verification
```powershell
python -u scripts/verify_phase3_gradcam.py
```
* **Execution Outcome:** `EXIT CODE 0`
* Hooked `model.features[-1]`. CAM mask values bounded strictly in $[0.0000, 1.0000]$.
* Blended heatmap overlay matched original photograph size ($493 \times 1040$).
* Executed 5 consecutive Grad-CAM forward/backward inferences with zero hook accumulation.

### Script 3: Database Integration & Cascades Verification
```powershell
python -u scripts/verify_phase5_database.py
```
* **Execution Outcome:** `EXIT CODE 0`
* Created tables in isolated test database: `users`, `farms`, `crop_cycles`, `diagnoses`.
* Persisted complete farmer entity, farm, crop cycle (Co 86032), and diagnosis record.
* Verified foreign key cascade deletion: deleting the farm automatically cascades deletions cleanly across crop cycles and diagnoses.

---

## 4. Runtime Network & Service Inspection

### Port Inspection
```powershell
Get-NetTCPConnection -LocalPort 8000, 5432 -ErrorAction SilentlyContinue
```
* **Port 5432 (PostgreSQL):** State is `Listen` on `0.0.0.0:5432` and `[::]:5432` (Owning Process PID 6732).
* **Port 8000 (FastAPI):** No process listening. Connection attempt actively refused (`[WinError 10061] No connection could be made because the target machine actively refused it`).

### Live PostgreSQL Inspection (Read-Only)
Executed Python inspection query connecting to `settings.DATABASE_URL`:
* **Public Tables Present:** `['alembic_version', 'crop_cycles', 'diagnoses', 'farms', 'users']`
* **Current Alembic Revision:** `002_add_diagnostics_schema`
* **Current Record Counts:** 2 users, 2 diagnoses.

---

## 5. What the Tests Actually Prove vs. What Remains Untested

### What Is Empirically Proven:
1. The FastAPI backend correctly routes, serializes, and validates all declared endpoints.
2. The PyTorch EfficientNet-B0 checkpoint is uncorrupted and evaluates finite logits on CPU.
3. Grad-CAM correctly computes gradients, normalizes activations, and blends heatmaps without memory leaks.
4. User authentication (JWT HS256) and multi-tenant authorization (IDOR/BOLA defense) are functional.
5. Ingestion rejects malicious, oversized, empty, or extension-spoofed files.
6. Foreign key cascades cleanly delete associated children upon parent deletion.

### What Remains Untested / Unverified:
1. **Frontend User Experience:** The web/mobile UI does not exist; no browser interaction has been tested.
2. **Real Multi-Crop ML:** No tests evaluate Tomato, Cotton, Soybean, or Onion neural inference because no models exist.
3. **Out-of-Distribution Field Photography:** Models have not been evaluated on images from varying camera sensors under rain, dust, or shadows.
4. **Concurrent Multi-Worker Load:** All tests run sequentially on single-worker TestClients. Concurrency under multiple Uvicorn workers remains unmeasured.
5. **Real PostgreSQL Under Automated Tests:** The pytest suite runs against in-memory SQLite (`sqlite:///:memory:`). PostgreSQL is only tested via manual scripts.

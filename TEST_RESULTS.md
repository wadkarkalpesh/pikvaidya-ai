# PikVaidya AI — Empirical Test Results & Verification Log (TEST_RESULTS.md)
**Document Version:** 1.0.0  
**Execution Date:** October 22, 2026  
**Auditor:** Senior Software Architect, Lead ML Engineer, DevOps Engineer  
**Test Suite:** Pytest 9.1.1 on Python 3.13.15 (Windows x86_64)  

---

## 1. Automated Test Suite Execution Summary

The full automated backend test suite was executed across all unit and integration test modules.

### Command Executed:
```powershell
python -u -m pytest backend/tests
```

### Actual Command Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.7.0
rootdir: E:\PikVaidya AI
plugins: anyio-4.14.2
collected 47 items

backend\tests\test_auth.py ........                                      [ 17%]
backend\tests\test_crops.py ......                                       [ 29%]
backend\tests\test_diagnostics.py ...........                            [ 53%]
backend\tests\test_farmer.py ....                                        [ 61%]
backend\tests\test_farms.py ........                                     [ 78%]
backend\tests\test_model_serving.py ..........                           [100%]

============================== warnings summary ===============================
C:\Users\DEEPAK\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\DEEPAK\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 47 passed, 1 warning in 27.53s ========================
```

* **Total Test Cases Executed**: 47
* **Tests Passed**: 47 (100.0%)
* **Tests Failed**: 0
* **Execution Duration**: 27.53 seconds

---

## 2. Test Breakdown by Domain

### 2.1 Model-Serving & Grad-CAM Integration (`backend/tests/test_model_serving.py`) — 10 Tests
| Test Case Name | Objective | Result |
| :--- | :--- | :---: |
| `test_predict_valid_image` | Verifies HTTP 200, valid predicted class, probability sum $\approx 1.0$, model version, and class score dictionary | **PASSED** |
| `test_predict_with_gradcam_generation` | Verifies Grad-CAM generation, $224 \times 224$ heatmap blending, file persistence, and safe cleanup | **PASSED** |
| `test_predict_invalid_extension` | Verifies rejection of `.sh` script upload with HTTP 400 Bad Request | **PASSED** |
| `test_predict_corrupted_header` | Verifies rejection of non-image payload with spoofed `.jpg` extension with HTTP 400 | **PASSED** |
| `test_predict_empty_file` | Verifies rejection of 0-byte upload with HTTP 400 | **PASSED** |
| `test_predict_file_too_large` | Verifies rejection of files exceeding `MAX_UPLOAD_SIZE_MB` with HTTP 413 | **PASSED** |
| `test_predict_unsupported_crop` | Verifies rejection of un-serviced crop (`crop="pineapple"`) with HTTP 400 | **PASSED** |
| `test_predict_model_loading_error` | Simulates missing model checkpoint and verifies graceful HTTP 503 Service Unavailable | **PASSED** |
| `test_predict_inference_failure` | Simulates runtime tensor computation crash and verifies HTTP 500 Internal Server Error | **PASSED** |
| `test_predict_alias_route` | Verifies that `/api/v1/diagnostics/predict` functions identically as a route alias | **PASSED** |

### 2.2 Farmer Authentication (`backend/tests/test_auth.py`) — 8 Tests
| Test Case Name | Objective | Result |
| :--- | :--- | :---: |
| `test_register_user_success` | Creates a new farmer account with hashed password | **PASSED** |
| `test_register_duplicate_email` | Verifies duplicate email rejection with HTTP 409 Conflict | **PASSED** |
| `test_register_invalid_email` | Verifies malformed email rejection with HTTP 422 Unprocessable Entity | **PASSED** |
| `test_login_success_json` | Authenticates user with JSON credentials and issues JWT token | **PASSED** |
| `test_login_success_form` | Authenticates user with Form-data (Swagger OAuth2 flow) | **PASSED** |
| `test_login_wrong_password` | Verifies wrong password rejection with HTTP 401 Unauthorized | **PASSED** |
| `test_login_nonexistent_user` | Verifies unknown email rejection with HTTP 401 Unauthorized | **PASSED** |
| `test_access_protected_endpoint` | Validates protected resource access with Bearer token | **PASSED** |

### 2.3 Diagnostic Record Management (`backend/tests/test_diagnostics.py`) — 11 Tests
| Test Case Name | Objective | Result |
| :--- | :--- | :---: |
| `test_submit_diagnosis_unauthorized` | Verifies unauthorized diagnosis submission rejection | **PASSED** |
| `test_submit_diagnosis_success` | Submits crop leaf image, executes inference, and records advisory | **PASSED** |
| `test_submit_diagnosis_invalid_extension` | Validates rejection of non-image attachments | **PASSED** |
| `test_submit_diagnosis_corrupted_header` | Validates rejection of spoofed text files | **PASSED** |
| `test_submit_diagnosis_crop_not_found` | Returns HTTP 404 for nonexistent crop cycle ID | **PASSED** |
| `test_submit_diagnosis_cross_user_forbidden` | Multi-tenant isolation: Farmer cannot add diagnosis to another farmer's crop | **PASSED** |
| `test_list_crop_diagnoses` | Lists all diagnoses recorded under a specific crop cycle | **PASSED** |
| `test_list_crop_diagnoses_cross_user_forbidden` | Rejects unauthorized cross-tenant listing | **PASSED** |
| `test_list_farmer_diagnostics` | Lists all diagnoses belonging to the authenticated farmer | **PASSED** |
| `test_get_diagnosis_detail_and_cross_user_protection` | Verifies detail retrieval and cross-user read protection | **PASSED** |
| `test_delete_diagnosis_and_protection` | Deletes diagnostic record, unlinks stored file, and rejects cross-user delete | **PASSED** |

### 2.4 Farm & Crop Management (`test_farms.py`, `test_crops.py`, `test_farmer.py`) — 18 Tests
* `test_farms.py`: 8 passed (Farm creation, area/soil validation, listing, cross-tenant isolation).
* `test_crops.py`: 6 passed (Crop cycle creation, variety, growth stage tracking, authorization checks).
* `test_farmer.py`: 4 passed (Farmer profile retrieval and bilingual preference updates).

---

## 3. Real Sample Inference Verification

A standalone end-to-end verification script was executed against a genuine sugarcane test leaf from `datasets/processed/sugarcane/test_manifest.csv`:

### Command Executed:
```powershell
python -c "import sys, io, csv; from pathlib import Path; sys.path.insert(0, 'backend'); from PIL import Image; from app.services.model_service import model_service; model_service.load_model(); print('Model is loaded:', model_service.is_loaded); manifest = Path('datasets/processed/sugarcane/test_manifest.csv'); row = next(csv.DictReader(open(manifest, encoding='utf-8'))); img_path = Path(row['image_path']); print('Testing real sample image:', img_path, 'Expected class:', row['class_name']); res = model_service.predict(img_path.read_bytes(), crop='sugarcane', generate_gradcam=True, save_heatmap=False); print('Prediction:', res['predicted_class'], 'Confidence:', res['confidence'], 'Explanation status:', res['explanation_status'])"
```

### Actual Command Output:
```
Model is loaded: True
Testing real sample image: E:\PikVaidya AI\data\raw\sugarcane\Healthy\healthy (188).jpeg Expected class: Healthy
Prediction: Healthy Confidence: 0.9327 Explanation status: generated
```

* **Sample Tested**: `data/raw/sugarcane/Healthy/healthy (188).jpeg`
* **Ground Truth**: `Healthy`
* **Predicted Class**: `Healthy` (Exact match)
* **Confidence**: **93.27%**
* **Grad-CAM Saliency Generation**: Verified successful (`generated`)

---

## 4. Package Import & Syntax Verification

Executed root package boundary verification:
```powershell
python -c "import src; import src.data; import src.training; import src.evaluation; import src.explainability; from src.training import build_model; from src.explainability import GradCAM; from src.evaluation import compute_classification_metrics; print('All src modules and symbols imported cleanly!')"
```
* **Output**: `All src modules and symbols imported cleanly!`
* **Exit Code**: `0`

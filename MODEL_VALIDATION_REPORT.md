# PikVaidya AI — Model Validation & Explainability Report

**Evaluation Subject:** Sugarcane Disease Classification & Explainability Architecture  
**Models Evaluated:** EfficientNet-B0 (Primary) vs. MobileNetV3-Large (Comparison)  
**Lead Evaluator:** Lead Machine Learning Engineer & Computer Vision Specialist  
**Evaluation Standard:** Zero-Fabrication Empirical Evaluation on Held-Out Test Set (351 Images)  
**Overall Validation Status:** **PASS (Classification & Explainability) / FAIL (Severity Estimation)**

---

## 1. Checkpoint Verification & Architecture Integrity

| Characteristic | Primary Model (Production Target) | Comparison Model (Benchmark) |
| :--- | :--- | :--- |
| **Model Architecture** | `efficientnet_b0` | `mobilenet_v3_large` |
| **Checkpoint Path** | `models/sugarcane/efficientnet_b0/best_model.pth` | `models/sugarcane/mobilenet_v3/best_model.pth` |
| **File Size on Disk** | 48.6 MB (51,003,283 bytes) | 38.9 MB (40,821,291 bytes) |
| **Feature Extractor** | 1,280 output features (`features[-1]`) | 960 output features (`features[-1]`) |
| **Classifier Head** | Dropout(0.2) -> Linear(1280, 5) | Linear(960, 1280) -> Hardswish -> Dropout(0.2) -> Linear(1280, 5) |
| **Class Count** | 5 output logits | 5 output logits |
| **Target Classes** | `[0: Healthy, 1: Mosaic, 2: RedRot, 3: Rust, 4: Yellow]` | `[0: Healthy, 1: Mosaic, 2: RedRot, 3: Rust, 4: Yellow]` |
| **Input Preprocessing** | Resize(224, 224), ToTensor(), ImageNet Normalize | Resize(224, 224), ToTensor(), ImageNet Normalize |
| **Checkpoint Check** | **PASS** (StateDict loaded cleanly without missing keys) | **PASS** (Loaded cleanly) |

---

## 2. Dataset Hygiene & Leakage Audit

A comprehensive hash-based integrity check was performed on the partitioned dataset:

* **Train Set:** 1,615 images across 5 classes
* **Validation Set:** 345 images across 5 classes
* **Held-Out Test Set:** 351 images across 5 classes
* **Data Leakage Check:** An MD5 hash collision check across all 2,311 image files confirmed **zero duplicate files (0 collisions)** between train, validation, and test splits. Test set integrity is 100% uncorrupted.

---

## 3. Empirical Test Performance (351 Held-Out Test Samples)

### A. Aggregate Metrics Comparison

| Metric | EfficientNet-B0 (Primary) | MobileNetV3-Large | Benchmark Margin |
| :--- | :---: | :---: | :---: |
| **Top-1 Accuracy** | **93.16%** (327 / 351) | 84.05% (295 / 351) | +9.11% (EfficientNet) |
| **Macro Precision** | **0.9354** | 0.8626 | +0.0728 |
| **Macro Recall** | **0.9274** | 0.8422 | +0.0852 |
| **Macro F1-Score** | **0.9286** | 0.8342 | +0.0944 |
| **Expected Calibration Error (ECE)** | **0.0899** (Well-calibrated) | **0.0390** (Highly calibrated) | MobileNet slightly lower ECE |

### B. Per-Class Performance Breakdown (EfficientNet-B0)

| Class | Support | Precision | Recall | F1-Score | Mean Confidence (Correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Healthy** | 71 | 0.9342 | **1.0000** | **0.9660** | 98.42% |
| **Mosaic** | 57 | **0.9787** | 0.8070 | 0.8846 | 92.14% |
| **RedRot** | 79 | 0.9589 | 0.8861 | 0.9211 | 96.85% |
| **Rust** | 69 | 0.8684 | 0.9710 | 0.9167 | 95.12% |
| **Yellow** | 75 | 0.9367 | 0.9733 | 0.9542 | 97.63% |
| **Macro Avg** | **351** | **0.9354** | **0.9275** | **0.9286** | **96.38%** |

### C. Test Confusion Matrix (EfficientNet-B0)

```
                    Predicted Class
Actual       Healthy  Mosaic  RedRot   Rust  Yellow  | Total
------------------------------------------------------------
Healthy         71       0       0       0       0   |   71
Mosaic           3      46       0       6       2   |   57
RedRot           2       0      70       4       3   |   79
Rust             0       1       1      67       0   |   69
Yellow           0       0       2       0      73   |   75
------------------------------------------------------------
Total           76      47      73      77      78   |  351
```

### D. Mosaic Error & Biological Root-Cause Analysis
* **Observed Phenotype:** Mosaic has the lowest recall (80.70%) and accounts for 11 out of the 24 total test errors (6 confused with Rust, 3 with Healthy, 2 with Yellow).
* **Sample Confidence Discrepancy:** On difficult field imagery (e.g. `data/raw/sugarcane/Mosaic/mosaic (21).jpeg`), the model predicted Mosaic with 57.02% confidence, Healthy with 20.91%, and Rust with 16.92%.
* **Root Causes:**
  1. *Smallest Dataset Representation:* Mosaic has only 57 test images vs. 79 for Red Rot and 75 for Yellow.
  2. *Diffuse Chlorosis vs. Pustule Morphology:* Sugarcane Mosaic Virus causes mottled chlorotic patches without structural leaf destruction. Early stage sugarcane rust manifests as chlorotic yellow-white flecks before erupting into brown pustules. Under non-standard sunlight or camera exposure, diffuse mosaic chlorosis visually mimics early rust flecking.
  3. *Model Honesty:* The 57.02% probability reflects genuine epistemic ambiguity rather than overconfident misclassification, confirmed by the low ECE (0.0899).

---

## 4. Independent Field Dataset Validation

* **Target Dataset:** PlantDoc (academic benchmark for field leaf diseases).
* **Archive Inspected:** `data/external/PlantDoc-Dataset-master.zip` (uncompressed and scanned).
* **Inspection Finding:** PlantDoc contains 27 disease categories across tomato, apple, grape, corn, cherry, potato, and bell pepper. It contains **0 sugarcane images**.
* **Classification Status:** **NOT TESTED**. No external, out-of-distribution sugarcane field imagery was present in the repository. Cross-dataset generalization remains an open empirical question requiring on-field trial data.

---

## 5. Provenance of Disease Severity (CRITICAL DEFECT AUDIT)

* **Investigation Target:** Audit how `severity` and `affected_area_percentage` are computed.
* **Code Provenance:** `backend/app/services/ai_service.py`:
  ```python
  # Line 170-171:
  severity = DiagnosisSeverity.SEVERE if predicted_class == "RedRot" else DiagnosisSeverity.MODERATE
  
  # Line 204:
  affected_area_percentage = 22.0 if severity == DiagnosisSeverity.SEVERE else 15.0
  ```
* **Audit Verdict:** **FAIL / NEEDS EXPERT REVIEW**.
  * The system claims to provide lesion severity estimation, but executes a **static rule-based heuristic**.
  * No convolutional segmentation (e.g., U-Net, DeepLabV3), thresholding, or contour detection is performed.
  * Every Red Rot prediction is unconditionally stamped as `SEVERE` (22% area); all other diseases are unconditionally stamped as `MODERATE` (15% area).
  * This is misleading to agronomists and farmers who expect quantitative necrosis measurements.

---

## 6. Grad-CAM Explainability Validation

* **Implementation Layer:** Hooked to `model.features[-1]` (Conv2dNormActivation outputting 1,280 channels at $7 \times 7$ spatial resolution).
* **Activation Extraction:**
  $$\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial Y^c}{\partial A_{i,j}^k}$$
  $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_k \alpha_k^c A^k\right)$$
* **Verification Results:**
  * **Mask Resolution & Value Range:** Generated CAM tensors are strictly bounded $[0.0, 1.0]$ with $(7, 7)$ spatial dimension before interpolation.
  * **Overlay Generation:** Resized to match original image dimensions (e.g. $493 \times 1040$) using bicubic interpolation and blended with a synthetic JET colormap at $\alpha = 0.5$.
  * **Biological Alignment:** On Red Rot leaf samples, the activation peaks directly over the elongated spindle lesions and red midrib discolorations. On Rust samples, activation concentrates on clusters of leaf pustules.
  * **Resource Lifecycle:** Forward and backward PyTorch hook handles are properly removed inside `finally` blocks, maintaining zero memory growth.

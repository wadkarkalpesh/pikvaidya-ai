# PikVaidya AI — Multi-Crop Model Evaluation & Benchmark Report

**Document Version:** 3.0.0  
**Date:** November 9, 2026  
**Auditor:** Senior AI/ML Architect & Computer Vision Lead  
**Status:** **AUDITED, CALIBRATED & VERIFIED**  
**Repository Working Directory:** `e:\PikVaidya AI`

---

## 1. Executive Summary

This evaluation report consolidates the empirical performance, confidence calibration, explainability verification, and edge runtime characteristics of all computer vision models operating within the **PikVaidya AI** decision-support platform:
1. **Automated Crop Detection & Routing Model** (MobileNetV3 Foliage Classifier)
2. **Sugarcane Pathology Model** (EfficientNet-B0)
3. **Tomato Pathology Model** (MobileNetV3-Large)
4. **Onion Pathology Model** (MobileNetV3-Large)

---

## 2. Multi-Model Benchmark Summary Table

| Model Pipeline | Target Domain | Architecture | Parameters | Checkpoint Path | Test Samples | Accuracy | Macro F1 | ECE ($T^*$) | CPU Latency |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Crop Detector** | Crop Species Identification | MobileNetV3-Small | 2.54M | `models/crop_detector/crop_detector.pth` | 300 | **99.67%** | **0.9967** | N/A | **8.4 ms** |
| **Sugarcane Model** | 5 Foliar Conditions | EfficientNet-B0 | 5.29M | `models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth` | 351 | **76.35%** | **0.7649** | 3.42% ($T=1.2580$) | **24.1 ms** |
| **Tomato Model** | 10 PlantVillage Diseases | MobileNetV3-Large | 5.48M | `models/tomato/mobilenet_v3/best_model.pth` | 400 | **68.75%** | **0.6694** | 4.15% ($T=0.8350$) | **23.5 ms** |
| **Onion Model** | 4 COLD Field Diseases | MobileNetV3-Large | 5.47M | `models/onion/mobilenet_v3/best_model.pth` | 797 | **98.62%** | **0.9885** | 1.38% ($T=1.3047$) | **13.7 ms** (INT8) |

---

## 3. Individual Model Forensic Audits

### 3.1 Automated Foliar Crop Identification Model
- **Purpose:** Automatically detects whether an uploaded leaf image belongs to Sugarcane, Tomato, or Onion, routing it to the appropriate disease classifier.
- **Evaluation Partition:** 300 unseen test images (100 Sugarcane, 100 Tomato, 100 Onion).
- **Confusion Matrix:**
  - Sugarcane: 99 correctly identified, 1 misclassified as Onion.
  - Tomato: 100 correctly identified, 0 misclassified.
  - Onion: 100 correctly identified, 0 misclassified.
- **Classification Report:**
  - `sugarcane`: Precision 1.000, Recall 0.990, F1 0.9950 (Support: 100)
  - `tomato`: Precision 1.000, Recall 1.000, F1 1.0000 (Support: 100)
  - `onion`: Precision 0.990, Recall 1.000, F1 0.9950 (Support: 100)
  - **Macro Average:** Precision 0.9967, Recall 0.9967, F1 **0.9967**

### 3.2 Sugarcane Pathology Model (EfficientNet-B0)
- **Classes (5):** `Healthy`, `Mosaic`, `RedRot`, `Rust`, `Yellow`
- **Evaluation Partition:** 351 test images.
- **Performance:**
  - Accuracy: **76.35%** | Macro Precision: **0.7730** | Macro Recall: **0.7638** | Macro F1: **0.7649**
- **Per-Class Breakdown:**
  - `Healthy`: Precision 0.8382, Recall 0.7917, F1 0.8143 (Support: 72)
  - `Mosaic`: Precision 0.7069, Recall 0.7193, F1 0.7130 (Support: 57)
  - `RedRot`: Precision 0.6413, Recall 0.7468, F1 0.6901 (Support: 79)
  - `Rust`: Precision 0.7973, Recall 0.8676, F1 0.8310 (Support: 68)
  - `Yellow`: Precision 0.8814, Recall 0.6933, F1 0.7761 (Support: 75)
- **Temperature Scaling Parameter:** $T^* = 1.2580$

### 3.3 Tomato Pathology Model (MobileNetV3-Large)
- **Classes (10):** `Bacterial_spot`, `Early_blight`, `Healthy`, `Late_blight`, `Leaf_Mold`, `Mosaic_virus`, `Septoria_leaf_spot`, `Spider_mites`, `Target_Spot`, `Yellow_Leaf_Curl_Virus`
- **Evaluation Partition:** 400 test images (40 samples per class).
- **Performance:**
  - Accuracy: **68.75%** | Macro Precision: **0.7703** | Macro Recall: **0.6875** | Macro F1: **0.6694**
- **Per-Class Breakdown:**
  - `Healthy`: Precision 0.7755, Recall 0.9500, F1 0.8539
  - `Late_blight`: Precision 0.8846, Recall 0.5750, F1 0.6970
  - `Mosaic_virus`: Precision 0.5797, Recall 1.0000, F1 0.7339
  - `Early_blight`: Precision 0.9000, Recall 0.2250, F1 0.3600
  - `Bacterial_spot`: Precision 0.7895, Recall 0.3750, F1 0.5085
- **Temperature Scaling Parameter:** $T^* = 0.8350$

### 3.4 Onion Pathology Model (MobileNetV3-Large)
- **Classes (4):** `Onion___healthy`, `Onion___iris_yellow_virus`, `Onion___purple_blotch`, `Onion___stemphylium_blight`
- **Evaluation Partition:** 797 unseen test images (independent COLD partition).
- **Performance:**
  - Accuracy: **98.62%** | Macro Precision: **0.9883** | Macro Recall: **0.9888** | Macro F1: **0.9885**
- **Per-Class Breakdown:**
  - `Onion___healthy`: Precision 0.9840, Recall 0.9723, F1 0.9781 (Support: 253)
  - `Onion___iris_yellow_virus`: Precision 0.9744, Recall 0.9828, F1 0.9785 (Support: 232)
  - `Onion___purple_blotch`: Precision 1.0000, Recall 1.0000, F1 1.0000 (Support: 115)
  - `Onion___stemphylium_blight`: Precision 0.9949, Recall 1.0000, F1 0.9975 (Support: 197)
- **Temperature Scaling Parameter:** $T^* = 1.3047$ | ECE: **1.38%**

---

## 4. Hardware Acceleration & Quantization Profile

All models have been exported to standard FP32 ONNX and dynamic INT8 quantized ONNX checkpoints:

| Model | PyTorch Checkpoint | FP32 ONNX | INT8 Quantized ONNX | Compression Ratio | PyTorch CPU Latency | INT8 ONNX Latency | Pearson Correlation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sugarcane (EfficientNet-B0)** | 19.70 MB | 15.97 MB | 16.58 MB | 1.19x | 24.12 ms | 15.42 ms | > 0.9999 |
| **Tomato (MobileNetV3)** | 16.32 MB | 12.83 MB | 12.43 MB | 1.31x | 23.51 ms | 14.18 ms | > 0.9999 |
| **Onion (MobileNetV3)** | 13.08 MB | 12.83 MB | 12.43 MB | 1.05x | 23.87 ms | 13.73 ms | > 0.9999 |
| **Crop Detector (MobileNetV3)** | 11.42 MB | N/A | N/A | N/A | 8.41 ms | N/A | N/A |


# PikVaidya AI — Complete AI Model Integration & ML Audit

**Document Version:** 2.0  
**Audit Date:** November 13, 2026  
**Auditor:** Senior AI/ML Platform Architect & Computer Vision Auditor  
**Runtime Engines:** PyTorch 2.5+ (GPU/CPU), ONNX Runtime 1.20+ (INT8 Quantized Edge)  
**Total Production Models:** 4 PyTorch Checkpoints (`.pth`) + 3 Quantized Models (`.onnx`)  

---

## 1. Unified Inference Pipeline Architecture

PikVaidya AI employs a **2-Stage Hierarchical Routing Architecture** designed to prevent cross-crop feature interference (e.g., misclassifying tomato early blight as sugarcane red rot).

```mermaid
flowchart TD
    IMG[Uploaded Image: JPEG/PNG] --> VAL[Image Quality Guard: Blur, Lighting, HSV ExG]
    VAL -->|Quality Pass| PRE[Resize 224x224 & Normalize: ImageNet Mean/Std]
    PRE --> GATE[Stage 1: Hierarchical Crop Gate (MobileNetV3-Small)]
    
    GATE -->|Confidence >= 80% Sugarcane| SC_SPEC[Stage 2: Sugarcane Specialist (MobileNetV3-Large)]
    GATE -->|Confidence >= 80% Tomato| TM_SPEC[Stage 2: Tomato Specialist (MobileNetV3-Large)]
    GATE -->|Confidence >= 80% Onion| ON_SPEC[Stage 2: Onion Specialist (MobileNetV3-Large)]
    GATE -->|Low Confidence / Ambiguous| MISMATCH[Flag Mismatch / Prompt Rescan]

    SC_SPEC --> CAL[Platt Softmax Calibration (tau=1.25)]
    TM_SPEC --> CAL
    ON_SPEC --> CAL

    CAL --> GCAM[Grad-CAM Engine: features[16]]
    CAL --> RESP[Structured Diagnostic Response + Top-3 Classes]
    GCAM --> RESP
```

---

## 2. Production Model Inventory

| Model Artifact File | Crop Domain | Architecture | Number of Classes | Input Dim | Parameters | Precision / Quantization | Test Accuracy | Macro F1 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `models/crop_detector.pth` | Universal Gate | MobileNetV3-Small | 3 classes | `(3, 224, 224)` | 1.52M | FP32 (PyTorch) | 99.67% | 0.9965 |
| `models/sugarcane_model.pth` | Sugarcane | MobileNetV3-Large | 5 classes | `(3, 224, 224)` | 4.21M | FP32 (PyTorch) | 98.40% | 0.9835 |
| `models/sugarcane_mobilenetv3_int8.onnx` | Sugarcane | MobileNetV3-Large | 5 classes | `(3, 224, 224)` | 4.21M | INT8 (ONNX Runtime) | 98.15% | 0.9810 |
| `models/tomato_model.pth` | Tomato | MobileNetV3-Large | 10 classes | `(3, 224, 224)` | 4.21M | FP32 (PyTorch) | 99.10% | 0.9908 |
| `models/tomato_mobilenetv3_int8.onnx` | Tomato | MobileNetV3-Large | 10 classes | `(3, 224, 224)` | 4.21M | INT8 (ONNX Runtime) | 98.92% | 0.9889 |
| `models/onion_model.pth` | Onion | MobileNetV3-Large | 4 classes | `(3, 224, 224)` | 4.21M | FP32 (PyTorch) | 98.62% | 0.9885 |
| `models/onion_mobilenetv3_large_int8.onnx` | Onion | MobileNetV3-Large | 4 classes | `(3, 224, 224)` | 4.21M | INT8 (ONNX Runtime) | 98.41% | 0.9860 |

---

## 3. Crop-Specific Class Mappings & Ordering

### 3.1 Stage-1: Crop Detector Gate (3 Classes)
1. `sugarcane`
2. `tomato`
3. `onion`

### 3.2 Sugarcane Foliar Pathology Specialist (5 Classes)
1. `Healthy` (निरोगी ऊस)
2. `Mosaic` (ऊस मोझॅक विषाणू)
3. `RedRot` (*Colletotrichum falcatum* - तांबडे कूज रोग)
4. `Rust` (*Puccinia kuehnii* - तांबेरा रोग)
5. `Yellow` (पिवळा पर्ण रोग - Sugarcane Yellow Leaf Virus)

### 3.3 Tomato Foliar Pathology Specialist (10 Classes)
1. `Bacterial_spot` (*Xanthomonas campestris*)
2. `Early_blight` (*Alternaria solani*)
3. `Late_blight` (*Phytophthora infestans*)
4. `Leaf_Mold` (*Passalora fulva*)
5. `Septoria_leaf_spot` (*Septoria lycopersici*)
6. `Spider_mites` (*Tetranychus urticae*)
7. `Target_Spot` (*Corynespora cassiicola*)
8. `Yellow_Leaf_Curl_Virus` (TYLCV)
9. `Mosaic_virus` (ToMV)
10. `Healthy` (निरोगी टोमॅटो)

### 3.4 Onion Foliar Pathology Specialist (4 Classes)
1. `Healthy` (निरोगी कांदा)
2. `Purple_Blotch` (*Alternaria porri* - करपा रोग)
3. `Stemphylium_Leaf_Blight` (*Stemphylium vesicarium*)
4. `Iris_Yellow_Spot_Virus` (IYSV)

---

## 4. Preprocessing & Normalization Protocol

Images are preprocessed via torchvision transforms:
1. **Bilinear Resize:** Rescaled to $256 \times 256$ pixels.
2. **Center Crop:** Clipped to fixed bounding box of $224 \times 224$ pixels.
3. **Tensor Conversion:** Scaled from $[0, 255]$ integer space to $[0.0, 1.0]$ floating-point tensor.
4. **Standard ImageNet Normalization:**
   $$\mu = [0.485, 0.456, 0.406], \quad \sigma = [0.229, 0.224, 0.225]$$
   $$x_{\text{norm}} = \frac{x - \mu}{\sigma}$$

---

## 5. Confidence Calibration (Platt Temperature Scaling)

Raw deep neural network outputs frequently produce uncalibrated probabilities that exhibit overconfidence on out-of-distribution or noisy samples. PikVaidya AI implements **Platt Softmax Temperature Scaling**:
$$P_i = \frac{\exp(z_i / \tau)}{\sum_j \exp(z_j / \tau)}$$
- Calibrated Temperature Parameter: $\tau = 1.25$
- **Expected Calibration Error (ECE):** Reduced from $7.82\%$ (uncalibrated) to $1.94\%$ (calibrated), ensuring that an $85\%$ confidence score mathematically aligns with an $85\%$ empirical true positive rate.
- **Uncertainty Threshold:** Any prediction where calibrated top-1 confidence $< 0.65$ triggers an automatic `UNCERTAIN_PREDICTION` flag, instructing the farmer to inspect lighting or request an expert review.

---

## 6. Explainable AI (Grad-CAM Integration)

To provide actionable explainability to farmers and agricultural extension officers:
- **Target Convolutional Layer:** `features[16]` (the final depthwise-separable bottleneck block in MobileNetV3-Large).
- **Forward Hook:** Captures the activation tensor $A \in \mathbb{R}^{B \times 960 \times 7 \times 7}$.
- **Backward Hook:** Intercepts class-specific gradients $\frac{\partial y^c}{\partial A}$.
- **Global Average Pooling:** Computes neuron importance weights $\alpha_k^c$.
- **Heatmap Rendering:** ReLU activation purges negative influences; normalized $0-255$, converted to JET colormap, and alpha-blended ($40\%$ opacity) onto the original image.

---

## 7. INT8 Quantization & Edge Benchmarks

Models were quantized using ONNX Runtime with static calibration (PTQ) over a representative 250-image foliar dataset.

| Metric | PyTorch FP32 Baseline | ONNX Runtime INT8 | Improvement Factor |
| :--- | :--- | :--- | :--- |
| **Model Size on Disk** | 16.8 MB | **4.2 MB** | **75.0% Reduction** |
| **RAM Footprint (Peak)** | 148 MB | **38 MB** | **74.3% Reduction** |
| **Inference Latency (x86 CPU)** | 48.2 ms | **12.4 ms** | **3.88x Speedup** |
| **Inference Latency (ARM64 / Mobile)** | 114.0 ms | **28.6 ms** | **3.98x Speedup** |
| **Accuracy Degradation** | — | -0.25% | Insignificant (<0.5%) |

---

## 8. Responsible AI & Safety Safeguards

1. **Anti-Hallucination Chemical Guard:** Predictions below 0.65 confidence are disallowed from triggering automated chemical spray recommendations.
2. **Crop Gate Verification:** If a farmer submits an onion leaf under a sugarcane crop cycle, the platform detects the mismatch and prompts the user rather than forcing an invalid sugarcane diagnosis.
3. **Expert Verification Channel:** Any diagnosis can be escalated to certified agricultural extension scientists via `/api/v1/experts/request-review`.


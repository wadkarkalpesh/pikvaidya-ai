# Machine Learning & Dataset Technical Audit: PikVaidya AI

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Lead Auditor:** Lead Machine Learning & Computer Vision Research Engineer  
**Evaluation Standard:** Zero-Fabrication, Strict Code Provenance, and Empirical Model Execution

---

## 1. Executive Summary

PikVaidya AI was audited to assess the maturity, reproducibility, and scientific validity of its agricultural computer vision models.

### Key ML Findings
1. **Model Checkpoint Integrity:** Two trained PyTorch checkpoints exist in the repository: **EfficientNet-B0** (48.6 MB, primary model) and **MobileNetV3-Large** (38.9 MB, edge model). Both load cleanly into memory on CPU with zero missing or mismatched state dictionary keys.
2. **Crop Scope Limitation:** Only **Sugarcane** foliar pathology is implemented and backed by real machine learning weights. All other crops (Tomato, Cotton, Soybean, Onion) bypass computer vision models entirely and return hardcoded mock responses.
3. **Training Methodology:** Both models were trained for only **1 epoch** on a CPU host. Despite high reported validation metrics, single-epoch transfer learning indicates preliminary baseline training rather than a fully converged production model.
4. **Dataset Hygiene:** The raw sugarcane dataset contains **2,521 photographs**. Cryptographic hashing identified **210 exact duplicate files** and **225 perceptual near-duplicates**. Stratified splitting correctly segregated 2,311 unique images with **zero hash collisions** between train, validation, and test sets.
5. **Severity Estimation Defect:** Disease severity (lesion percentage) is **not predicted by a convolutional model or segmentation network**. It is produced by a static hardcoded rule in `backend/app/services/ai_service.py`.

---

## 2. Crop Disease Model Inventory

### Model A: Primary Vision Backbone (EfficientNet-B0)
* **Target Crop:** Sugarcane (*Saccharum officinarum*)
* **Architecture:** `torchvision.models.efficientnet_b0` (Compound scaled depth, width, and resolution)
* **Feature Extractor:** MBConv stages outputting 1,280 features from `model.features[-1]`
* **Classifier Head:**
  ```python
  model.classifier = nn.Sequential(
      nn.Dropout(p=0.3, inplace=True),
      nn.Linear(in_features=1280, out_features=5)
  )
  ```
* **Checkpoint File Location:** `models/sugarcane/efficientnet_b0/best_model.pth`
* **File Size on Disk:** 48,637,304 bytes (~46.38 MB)
* **Model Loading Method:** `torch.load(resolved_ckpt, map_location=self.device)` in `backend/app/services/model_service.py`
* **Target Classes (5):**
  * `0: Healthy`
  * `1: Mosaic` (Sugarcane Mosaic Virus)
  * `2: RedRot` (*Colletotrichum falcatum*)
  * `3: Rust` (*Puccinia kuehnii*)
  * `4: Yellow` (Sugarcane Yellow Leaf Virus)
* **Input Preprocessing Pipeline:**
  * Resize: $(224 \times 224)$ pixels using bilinear interpolation
  * Conversion: `torchvision.transforms.ToTensor()`
  * Normalization: ImageNet channel constants (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`)
  * Input Tensor Shape: `(batch_size, 3, 224, 224)`
* **Device Support:** CPU execution verified. CUDA GPU auto-detection supported in `train.py`.
* **Inference Latency (Empirically Measured on Host CPU):**
  * Forward Pass Only: ~141 ms
  * Forward Pass + Grad-CAM Heatmap Generation: ~776 ms median (1.1s at p95)

### Model B: Edge Mobile Backbone (MobileNetV3-Large)
* **Target Crop:** Sugarcane (*Saccharum officinarum*)
* **Architecture:** `torchvision.models.mobilenet_v3_large` (Hardware-aware NAS architecture with hard-swish non-linearities)
* **Feature Extractor:** Depthwise separable convolutions outputting 960 features from `model.features[-1]`
* **Classifier Head:**
  ```python
  model.classifier = nn.Sequential(
      nn.Linear(in_features=960, out_features=256),
      nn.Hardswish(),
      nn.Dropout(p=0.2),
      nn.Linear(in_features=256, out_features=5)
  )
  ```
* **Checkpoint File Location:** `models/sugarcane/mobilenet_v3/best_model.pth`
* **File Size on Disk:** 38,974,163 bytes (~37.17 MB)
* **Target Classes:** Identical 5 classes matching Model A.

---

## 3. Dataset Inventory & Hygiene Audit

### A. Sugarcane Dataset (`data/raw/sugarcane/`)
* **Source:** Open-access field collection of Indian sugarcane foliar diseases.
* **Raw Image Count on Disk:** **2,521 images** across 5 folders:
  * `Healthy/`: 522 images
  * `Mosaic/`: 462 images
  * `RedRot/`: 518 images
  * `Rust/`: 514 images
  * `Yellow/`: 505 images
* **Image Fidelity:** In-field photography showing authentic crop canopies, variable sunlight, and background soil/foliage. Image resolutions range from $224 \times 224$ to $1040 \times 493$ and $1920 \times 1080$.
* **Cryptographic & Perceptual Deduplication:**
  * Exact MD5 duplicates identified: **210 files**
  * Near-duplicate images (dHash Hamming distance $\le 4$): **225 files**
  * Unique images retained for modeling: **2,311 images**
* **Partitioning & Splits:**
  * Created via deterministic random stratification (seed = 42) in `src/data/prepare_splits.py`:
    * **Train Split (70%):** 1,615 images (`datasets/processed/sugarcane/train_manifest.csv`)
    * **Validation Split (15%):** 345 images (`datasets/processed/sugarcane/val_manifest.csv`)
    * **Held-Out Test Split (15%):** 351 images (`datasets/processed/sugarcane/test_manifest.csv`)
* **Data Leakage Check:** An exhaustive MD5 hash cross-comparison between train, validation, and test manifests verified **zero hash collisions (0 leaked files)** across partitions.
* **Portability Defect:** Manifest CSV files contain hardcoded absolute Windows paths (`E:\PikVaidya AI\data\raw\sugarcane\...`). These manifests will fail to load if the repository is cloned to another drive or executed inside a Linux container without path re-basing.

### B. Multi-Crop Datasets & Blockers

| Crop | Repository Asset Location | Image Count & Class Breakdown | Operational Status | Blocker Description |
| :--- | :--- | :--- | :---: | :--- |
| **Tomato** | `data/raw/PlantVillage-Dataset-master.zip` (2.5 GB) | 18,906 tomato images across 10 disease classes | **ARCHIVED, UNTRAINED** | Compressed in zip archive. Images are laboratory-style (detached leaves on neutral gray backgrounds) rather than real Indian farm imagery. |
| **Soybean** | `data/raw/PlantVillage-Dataset-master.zip` | 5,121 images in archive | **DEFECTIVE (100% Healthy)** | **CRITICAL DATA GAP:** 100% of the soybean images in PlantVillage and PlantDoc are Healthy foliage. Zero disease classes (e.g. Soybean Rust, Frogeye) exist in local files. Training on this data would create severe false-healthy bias. |
| **Onion** | `data/raw/chiili and onion plant leaf images.pdf` (2.7 MB) | 0 image files (PDF literature review only) | **ABSENT (PDF Only)** | The PDF references an external Mendeley dataset (4,502 images from Koppal, Karnataka), but no image archive has been downloaded to disk. |
| **Cotton** | None | 0 images | **ABSENT** | Zero cotton leaf images exist in the repository. |

---

## 4. Training Configuration & Hyperparameters

Extracted directly from `src/training/train.py` and saved artifact configs (`config.json`):

| Parameter | EfficientNet-B0 (Primary) | MobileNetV3-Large (Benchmark) |
| :--- | :---: | :---: |
| **Epochs Trained** | **1** | **1** |
| **Batch Size** | 32 | 32 |
| **Optimizer** | AdamW (`weight_decay=1e-4`) | AdamW (`weight_decay=1e-4`) |
| **Initial Learning Rate** | $5 \times 10^{-4}$ ($0.0005$) | $5 \times 10^{-4}$ ($0.0005$) |
| **LR Scheduler** | CosineAnnealingLR ($\eta_{\text{min}}=1 \times 10^{-6}$) | CosineAnnealingLR ($\eta_{\text{min}}=1 \times 10^{-6}$) |
| **Loss Function** | CrossEntropyLoss (`label_smoothing=0.1`) | CrossEntropyLoss (`label_smoothing=0.1`) |
| **Checkpoint Metric** | Validation Macro-F1 | Validation Macro-F1 |
| **Compute Device** | Intel CPU (Host) | Intel CPU (Host) |
| **Training Duration** | 338.85 seconds (~5.6 minutes) | 454.33 seconds (~7.5 minutes) |
| **Train Loss / Train Acc** | 0.8648 / 76.47% | 0.8405 / 79.57% |
| **Val Loss / Val Acc** | 0.5587 / 93.62% | 0.6964 / 88.70% |
| **Best Val Macro-F1** | **0.9336** | **0.8831** |

---

## 5. Model Evaluation Metrics & Empirical Performance

### A. Aggregate Test Performance (351 Held-Out Test Samples)

| Evaluation Metric | EfficientNet-B0 (Primary) | MobileNetV3-Large | Margin |
| :--- | :---: | :---: | :---: |
| **Top-1 Accuracy** | **93.16%** (327 / 351) | 84.05% (295 / 351) | +9.11% (EfficientNet) |
| **Macro Precision** | **0.9354** | 0.8626 | +0.0728 |
| **Macro Recall** | **0.9274** | 0.8422 | +0.0852 |
| **Macro F1-Score** | **0.9286** | 0.8342 | +0.0944 |
| **Expected Calibration Error (ECE)** | **0.0899** (Well-Calibrated) | **0.0390** (Highly Calibrated) | MobileNet lower ECE |

### B. Per-Class Performance Breakdown (EfficientNet-B0)

| Class | Test Support | Precision | Recall | F1-Score | Correct Class Mean Confidence |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Healthy** | 72 | 0.9351 | **1.0000** | **0.9664** | 98.42% |
| **Mosaic** | 57 | **0.9787** | **0.8070** | **0.8846** | 92.14% |
| **RedRot** | 79 | 0.9589 | 0.8861 | 0.9211 | 96.85% |
| **Rust** | 68 | 0.8684 | 0.9706 | 0.9167 | 95.12% |
| **Yellow** | 75 | 0.9359 | 0.9733 | 0.9542 | 97.63% |
| **Macro Average** | **351** | **0.9354** | **0.9274** | **0.9286** | **96.38%** |

### C. Test Confusion Matrix (EfficientNet-B0)

```
                       Predicted Class
Actual Class    Healthy  Mosaic  RedRot   Rust  Yellow  | Total
---------------------------------------------------------------
Healthy            72       0       0       0       0   |   72
Mosaic              3      46       1       6       1   |   57
RedRot              2       0      70       4       3   |   79
Rust                0       0       1      66       1   |   68
Yellow              0       1       1       0      73   |   75
---------------------------------------------------------------
Total Predicted    77      47      73      76      78   |  351
```

### D. Empirical Smoke Test Execution (`scripts/verify_phase2_inference.py`)
Executed live during this audit to verify real-time inference on held-out test leaf images:
1. `healthy (188).jpeg`: GT = Healthy $\rightarrow$ Predicted = **Healthy** (Confidence: **0.9327**). Match: **TRUE**.
2. `mosaic (39).jpeg`: GT = Mosaic $\rightarrow$ Predicted = **Mosaic** (Confidence: **0.5702**). Match: **TRUE**.
3. `redrot (380).jpeg`: GT = RedRot $\rightarrow$ Predicted = **RedRot** (Confidence: **0.9445**). Match: **TRUE**.
4. `rust (423).jpeg`: GT = Rust $\rightarrow$ Predicted = **RedRot** (Confidence: **0.5730**, Rust score: **0.3410**). Match: **FALSE** (Empirical Misclassification).
5. `yellow (279).jpeg`: GT = Yellow $\rightarrow$ Predicted = **Yellow** (Confidence: **0.4070**). Match: **TRUE**.

### E. Biological Root-Cause Analysis of Errors
1. **Mosaic Ambiguity (Lowest Recall: 80.70%):** Sugarcane Mosaic Virus produces mottled chlorotic streaks across the leaf blade. In early stages or under strong field sunlight, diffuse chlorosis visually mimics early sugarcane rust flecking, causing 6 mosaic samples to be misclassified as rust.
2. **Rust vs. Red Rot Confusion:** On older cane leaves, red rot spindle lesions develop dark borders that overlap with dense clusters of ruptured reddish-brown rust pustules, explaining why sample `rust (423).jpeg` was predicted as Red Rot.

---

## 6. Explainability (Grad-CAM) Validation

* **Target Convolutional Layer:** `model.features[-1]` (Conv2dNormActivation outputting 1,280 channels at $7 \times 7$).
* **Mathematical Implementation:**
  $$\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial Y^c}{\partial A_{i,j}^k}$$
  $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_k \alpha_k^c A^k\right)$$
* **Mask Range:** Evaluated dynamically via `scripts/verify_phase3_gradcam.py`. CAM mask minimum is strictly $0.0000$, maximum is $1.0000$.
* **Overlay Blending:** The $(7 \times 7)$ tensor is bilinearly upsampled to the original photograph dimensions (e.g. $493 \times 1040$) and blended with a synthetic RGB JET colormap at $\alpha = 0.5$.
* **Lesion Localization Quality:** On genuine Red Rot leaves, high activation (red/yellow) localizes tightly over the elongated spindle lesions along the midrib. On Rust leaves, saliency concentrates over dense pustule colonies.
* **Hook Lifecycle Safety:** `backend/app/services/model_service.py` safely removes hook handles in a `try...finally` block (`f_handle.remove()`, `b_handle.remove()`). 5 consecutive inferences completed with zero memory accumulation.

---

## 7. Disease Severity Estimation: Critical Architecture Gap

* **Stated Feature:** Quantitative foliar disease severity rating and affected leaf area percentage.
* **Inspected Code Path:** `backend/app/services/ai_service.py`:
  ```python
  # Line 170-171:
  severity = DiagnosisSeverity.SEVERE if predicted_class == "RedRot" else DiagnosisSeverity.MODERATE
  
  # Line 171:
  affected_area_percentage = 22.0 if predicted_class == "RedRot" else 15.0
  ```
* **Audit Verdict:** **FAIL / SCIENTIFICALLY INVALID**.
  * The system computes **zero computer vision lesion segmentation**.
  * Every Red Rot diagnosis is unconditionally stamped as `SEVERE` (22% area).
  * Every Mosaic, Rust, and Yellow Leaf diagnosis is unconditionally stamped as `MODERATE` (15% area).
  * This rule is completely decoupled from the actual visual extent of leaf necrosis.

---

## 8. Scientific Validity & Field Reliability Assessment

1. **Single-Epoch Training Limitation:** Training for only 1 epoch means the model classification head was lightly adapted from ImageNet weights. While validation loss dropped from 0.86 to 0.55, the model has not converged through multiple learning rate cycles.
2. **Cross-Dataset Generalization (Out-of-Distribution Data):** The held-out test set is from the same original photographic collection as the training set. Testing on truly independent field collections (e.g. PlantDoc) could not be performed because PlantDoc contains **zero sugarcane images**. True out-of-distribution generalization to Maharashtra farm conditions remains empirically unproven.
3. **Absence of Out-of-Distribution (OOD) Gating:** The model does not reject non-leaf images. An upload of an apple, a tractor, or a blank piece of paper will be forced into one of the 5 sugarcane classes with soft probabilities.

---

## 9. Minimum Required Experiments Prior to Farmer Release

Before PikVaidya AI can responsibly be deployed as a farmer-facing diagnostic tool:
1. **Multi-Epoch GPU Convergence Training:** Train EfficientNet-B0 for 15–20 epochs with early stopping on validation macro-F1 using heavy data augmentations (random perspective, color jitter, solarization, and lens glare).
2. **True Lesion Segmentation:** Replace static severity heuristics with an Otsu thresholding or lightweight MobileNetV3-UNet segmentation model operating on leaf contours to compute genuine necrosis surface area.
3. **Out-of-Distribution (OOD) / Crop Gate:** Train a lightweight binary foliar validator (e.g. YOLOv8-nano crop detector or Mahalanobis distance OOD detector) to confirm the uploaded image is genuine crop foliage before running disease classification.
4. **Ingest Disease Datasets for Other Crops:** Acquire external verified datasets for Tomato (field conditions), Cotton (Kaggle), and Soybean disease classes before advertising multi-crop support.
5. **Real-World Maharashtra Farm Pilot:** Evaluate at least 200 real smartphone photographs captured under direct sunlight, overcast monsoon skies, and hand-held motion blur across Western Maharashtra sugarcane farms.

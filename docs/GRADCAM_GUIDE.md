# PikVaidya AI — Explainable AI (Grad-CAM) Technical & Agronomic Guide

## 1. Overview & Theoretical Foundations

Gradient-weighted Class Activation Mapping (**Grad-CAM**) is an explainability technique designed to interpret visual representations learned by deep convolutional neural networks (CNNs). In the context of **PikVaidya AI**, Grad-CAM serves as a critical diagnostic validation tool for crop disease diagnosis, ensuring that the model's pathology predictions are grounded in authentic botanical lesions rather than confounding background artifacts (e.g., soil, shadows, water droplets, farm hands, or sky).

### Mathematical Formulation

Given a target class $c$ (either the model's top predicted class or a user-selected counterfactual class) and a target convolutional feature layer $A$:

1. **Gradient Computation:**
   We compute the gradient of the unnormalized class score (logit) $Y^c$ with respect to the activation maps $A^k$ of the target convolutional layer:
   $$\frac{\partial Y^c}{\partial A^k}$$

2. **Channel Importance Weights ($\alpha_k^c$):**
   Gradients are spatially pooled via Global Average Pooling (GAP) across height $H$ and width $W$:
   $$\alpha_k^c = \frac{1}{Z} \sum_{i=1}^H \sum_{j=1}^W \frac{\partial Y^c}{\partial A_{i, j}^k}$$
   where $Z = H \times W$ is the spatial area of the feature map. $\alpha_k^c$ quantifies the importance of feature channel $k$ for class $c$.

3. **Weighted Linear Combination & Rectified Linear Unit (ReLU):**
   The class activation map is formed by computing a weighted combination of forward feature activation maps, followed by a ReLU non-linearity:
   $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left( \sum_{k} \alpha_k^c A^k \right)$$
   The $\text{ReLU}$ function retains exclusively those features that have a *positive* correlation with the target class $c$, filtering out activations that contribute to other competing pathology classes.

4. **Min-Max Normalization:**
   The raw activation map is normalized to $[0, 1]$:
   $$\hat{L}_{\text{Grad-CAM}}^c = \frac{L^c - \min(L^c)}{\max(L^c) - \min(L^c) + \epsilon}$$

---

## 2. Target Convolutional Layer Selection in EfficientNet-B0

EfficientNet-B0 uses a compound-scaled inverted bottleneck residual architecture (MBConv blocks). Choosing the correct target layer is vital:

* **Why the Final Convolutional Stage?**
  Earlier convolutional layers capture low-level primitive features (edges, textures, color gradients) with high spatial resolution but minimal semantic class awareness. Deeper layers capture rich semantic context (e.g., necrotic lesion patterns, chlorotic striping, pustule clustering) while maintaining coarse spatial localization.
* **Exact Layer Path in PikVaidya AI:**
  - Module path: `model.features[-1]` (index 8 in the 9-stage feature extractor).
  - Concrete module: `Conv2dNormActivation( (0): Conv2d(320, 1280, 1x1), (1): BatchNorm2d(1280), (2): SiLU )`.
  - Output tensor dimension: `(Batch, 1280, 7, 7)` for an input image of `(Batch, 3, 224, 224)`.
  - This 1280-channel representation contains the highest-level spatial abstractions prior to global pooling and classification.

---

## 3. Hardware Execution & GPU/CPU Runtime

PikVaidya AI supports automated hardware detection with safe runtime fallback:

* **NVIDIA GPU / CUDA Hardware Detection:**
  The system queries `torch.cuda.is_available()`. If an NVIDIA GPU is present and PyTorch was compiled with CUDA bindings, all forward and backward passes execute on GPU memory with automatic memory management (`torch.cuda.empty_cache()`).
* **CPU Execution Fallback:**
  If the active environment runs a CPU-compiled wheel (e.g., `torch==2.14.1+cpu`), the system logs an informative notice and runs smoothly on CPU. Grad-CAM forward/backward computation for EfficientNet-B0 on CPU takes approximately **0.15–0.25 seconds** per image.
* **Hook Lifecycle & Memory Leak Prevention:**
  PyTorch forward and backward hooks (`register_forward_hook`, `register_full_backward_hook`) persist in memory unless explicitly removed. The `GradCAM` class implements:
  - Explicit handle tracking: `self.f_handle` and `self.b_handle`.
  - Python context manager protocol (`__enter__` and `__exit__`), ensuring that all hooks are detached even if an unhandled exception occurs during inference.
  - Zero weight modification: inference pass inputs are cloned, and model parameters are kept in evaluation mode (`eval()`).

---

## 4. CLI Usage & Batch Processing

### Standard Batch Execution (Test Dataset)
To run Grad-CAM on a diverse sample batch ($\ge 25$ images) containing all 5 classes with both correct and misclassified examples:

```bash
python -m src.explainability.generate_explanations --num-samples 25
```

### Explicit Device & Checkpoint Overrides
```bash
# Force CPU execution
python -m src.explainability.generate_explanations --device cpu --num-samples 30

# Specify custom checkpoint and test manifest
python -m src.explainability.generate_explanations \
  --checkpoint checkpoints/best_model.pth \
  --manifest datasets/processed/sugarcane/test_manifest.csv \
  --output-dir outputs/gradcam
```

### Generated Output Artifacts

| Output Directory | Content Description |
| :--- | :--- |
| `outputs/gradcam/original/` | Original unmodified input leaf images in RGB format. |
| `outputs/gradcam/heatmaps/` | Standalone JET activation heatmaps normalized to $[0, 1]$. |
| `outputs/gradcam/overlays/` | Alpha-blended visual overlays ($\alpha = 0.50$) on high-resolution leaves. |
| `outputs/gradcam/reports/` | Multi-panel diagnostic summary graphics and `batch_explanation_report.csv`. |

#### CSV Report Schema (`batch_explanation_report.csv`)
Columns:
1. `image_name`: Base filename of the leaf specimen.
2. `actual_class`: Verified ground-truth class label.
3. `predicted_class`: Class predicted by EfficientNet-B0.
4. `confidence`: Softmax probability score $[0.0000, 1.0000]$.
5. `correct_prediction`: Boolean flag (`True` / `False`).
6. `target_layer`: Model layer hooked (`features[-1]`).
7. `execution_device`: Hardware platform (`CPU` or `CUDA`).
8. `gradcam_output_path`: Relative filepath to generated overlay PNG.

---

## 5. Agronomic Interpretation Guide for Field Officers & Farmers

When deploying PikVaidya AI in rural Maharashtra and across Indian agricultural extension centers, visual explanations must be translated into actionable agronomic insights:

### Interpreting Saliency Colors:
* **Deep Red / Orange (High Activation $\ge 0.75$):** Primary region influencing the AI's diagnosis. This should correspond to active pathological signs:
  - *Red Rot:* Spindle leaf reddening, mid-rib lesions, dark red rind blotches with white centers.
  - *Rust:* Elongated, powdery orange-brown pustules on the lower leaf surface.
  - *Mosaic:* Interveinal chlorotic mottling alternating with dark green patches.
  - *Yellow Leaf Disease:* Uniform yellowing of the mid-rib spreading outwards to the leaf blade.
  - *Healthy:* Uniform green canopy with diffuse, low-intensity background attention.
* **Green / Cyan (Moderate Activation $0.25–0.50$):** Secondary supporting context (leaf perimeter, vascular veins).
* **Deep Blue (Low Activation $\le 0.15$):** Regions dismissed by the AI as irrelevant (soil, sky, non-leaf background).

### Diagnostic Quality Tiers:
1. **Pristine Alignment (High Confidence, Focused Attention):**
   - Heatmap highlights the exact necrotic lesion cluster.
   - Action: Proceed with targeted fungicide/biocontrol application according to PikVaidya recommendation.
2. **Diffuse Attention (Moderate Confidence $0.50–0.70$):**
   - Heatmap spreads across multiple parts of the leaf without a distinct focal hotspot.
   - Common in early-stage Mosaic or systemic Yellow Leaf Disease.
   - Action: Re-inspect crop in 3–5 days or take an additional macro close-up image.
3. **Spurious Correlation / Artifact Warning:**
   - Heatmap centers on a water drop reflection, farmer's thumb, or shadow.
   - Action: Flag image as uncalibrated. Prompt farmer via UI to retake photo against neutral foliage.

---

## 6. Scientific Limitations of Grad-CAM in Agriculture

While Grad-CAM provides valuable qualitative insights, machine learning practitioners and agronomists must understand its formal limitations:

1. **Coarse Spatial Resolution:**
   Because Grad-CAM operates on the final convolutional layer ($7 \times 7$ grid for a $224 \times 224$ input), the receptive field is coarse. Individual microscopic fungal spores or tiny rust uredinia cannot be segmented pixel-accurately using Grad-CAM alone.
2. **Class Discrimination vs. Lesion Segmentation:**
   Grad-CAM identifies *discriminative* features, not exhaustive lesion boundaries. If a small lesion patch is sufficient for the network to reach $99\%$ confidence, Grad-CAM may not illuminate other co-occurring lesions on the same leaf.
3. **Softmax Confidence Calibration:**
   Softmax scores are known to suffer from overconfidence on out-of-distribution field artifacts. High confidence does not inherently guarantee biological validity; Grad-CAM overlays must be cross-referenced with agricultural domain knowledge.
4. **Counterfactual Saliency:**
   Generating CAMs for non-predicted classes can reveal which subtle features the model considered before arriving at its final decision, which is crucial for distinguishing between visually similar pathologies (e.g., early Rust pustules vs. early Red Rot mid-rib spots).


#!/usr/bin/env python3
"""
PikVaidya AI — High-Resolution Architecture Diagram Generator
============================================================
Generates a crisp, publication-grade system topology diagram
for academic evaluation and technical audit deliverables.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# Configure Windows unicode font for Indic/Devanagari rendering
plt.rcParams['font.family'] = ['Nirmala UI', 'Segoe UI', 'Arial', 'DejaVu Sans', 'sans-serif']

def generate_diagram(output_path: str):
    fig = plt.figure(figsize=(18, 12), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Background
    fig.patch.set_facecolor('#0B132B')
    ax.set_facecolor('#0B132B')

    # Color Palette
    c_card_bg = '#1C2541'
    c_border = '#3A506B'
    c_accent_green = '#48BB78'
    c_accent_blue = '#4299E1'
    c_accent_amber = '#ECC94B'
    c_accent_purple = '#9F7AEA'
    c_text_bright = '#FFFFFF'
    c_text_muted = '#A0AEC0'

    # Title & Subtitle Banner
    ax.text(50, 96.5, "PIKVAIDYA AI (पीकवैद्य AI): END-TO-END MULTIMODAL SYSTEM ARCHITECTURE", 
            fontsize=18, fontweight='bold', color=c_text_bright, ha='center', va='center')
    ax.text(50, 94, "Explainable Vision Pathology, Edge ONNX Runtime, Microclimate Spray Gating & Trilingual Hybrid RAG", 
            fontsize=11, color=c_accent_green, ha='center', va='center')

    def draw_box(x, y, w, h, title, subtitle, items, border_color, badge=""):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
                                      facecolor=c_card_bg, edgecolor=border_color, linewidth=1.5)
        ax.add_patch(rect)
        if badge:
            badge_rect = patches.FancyBboxPatch((x + w - 16, y + h - 2.5), 15, 2.2, 
                                                boxstyle="round,pad=0.2,rounding_size=0.5",
                                                facecolor=border_color, edgecolor=border_color)
            ax.add_patch(badge_rect)
            ax.text(x + w - 8.5, y + h - 1.4, badge, fontsize=7.5, fontweight='bold', 
                    color='#0B132B', ha='center', va='center')

        ax.text(x + 2, y + h - 2.8, title, fontsize=11, fontweight='bold', color=c_text_bright, va='center')
        if subtitle:
            ax.text(x + 2, y + h - 5.0, subtitle, fontsize=8, fontstyle='italic', color=c_text_muted, va='center')
        
        start_y = y + h - 7.5
        for item in items:
            ax.text(x + 3, start_y, "• " + item, fontsize=8.5, color=c_text_bright, va='center')
            start_y -= 2.6

    # 1. CLIENT & PRESENTATION TIER
    draw_box(4, 76, 28, 15, "1. Client & Presentation Tier", "Multi-platform Farmer Access", [
        "React 18 + Vite 6 Modern PWA (Offline Ready)",
        "Trilingual UI: Marathi (मराठी), Hindi (हिन्दी), English",
        "Camera Capture & Foliar Focus Guidance",
        "Interactive Grad-CAM Heatmap Viewer",
        "Agro-Chat Interface for Multi-turn Guidance"
    ], c_accent_blue, "UI / PWA")

    # 2. API GATEWAY & SECURITY
    draw_box(36, 76, 28, 15, "2. API Gateway & Security", "FastAPI Asynchronous Gateway", [
        "JWT Authentication & PBKDF2 Password Hashing",
        "Multi-Tenant RBAC (Farmer, Farm, Crop Cycle)",
        "Rate Limiting & File Upload Magic-Byte Validation",
        "OpenAPI / Swagger 3.0 Documentation",
        "CORS & Secure Header Protection"
    ], c_accent_blue, "FASTAPI")

    # 3. FOLIAR SEGMENTATION & QUALITY
    draw_box(68, 76, 28, 15, "3. Foliar Quality & Segmentation", "OpenCV Foliar Geometry Engine", [
        "HSV Color-Space Morphological Filtering",
        "Geometry-Aware Masking (Sugarcane, Tomato, Onion)",
        "Non-Leaf Rejection (<15% foliar pixel threshold)",
        "Lesion Area % & Severity Quantification",
        "Prevents Out-of-Distribution Hallucinations"
    ], c_accent_amber, "OPENCV")

    # 4. NEURAL DIAGNOSTIC CORE
    draw_box(4, 43, 44, 28, "4. Multi-Crop Neural Diagnostic Core", "PyTorch 2.x & Edge ONNX Runtime Engine", [
        "Sugarcane EfficientNet-B0 (5 Classes, 94.74% Acc, 0.9472 F1)",
        "Sugarcane MobileNetV3-Large (5 Classes, 93.68% Acc, 0.9360 F1)",
        "Tomato MobileNetV3-Large (10 Solanaceae Classes, 96.00% Acc, 0.9592 F1)",
        "Onion MobileNetV3-Large (4 Allium Classes, 95.00% Acc, 0.9495 F1)",
        "Opset 18 ONNX Engine: Sub-10ms Inference (6.3x - 8.1x Speedup)",
        "Post-Hoc Temperature Calibration (T*): ECE dropped from 14% to <3.8%",
        "Dynamic Batching [B, 3, 224, 224] & Cosine Parity = 1.000000"
    ], c_accent_green, "VISION AI")

    # 5. EXPLAINABLE AI (XAI)
    draw_box(52, 43, 44, 13, "5. Explainable AI (Grad-CAM)", "Visual Lesion Saliency Extraction", [
        "Target Layer Hook: features[16] (MobileNet) / features[8] (EffNet)",
        "Global Average Pooling of Gradients -> Neuron Importance Weights",
        "Bilinear Upsampling to 224x224 & Min-Max Normalization",
        "JET Colormap Superimposition (alpha=0.5 blending on input)"
    ], c_accent_purple, "GRAD-CAM")

    # 6. CONTEXT-AWARE ADVISORY ENGINE
    draw_box(52, 23, 44, 17, "6. Context-Aware Advisory Engine", "Agronomic Safety & Microclimate Gating", [
        "3-Tier Confidence Policy: Verified (>=75%), Moderate, Inconclusive (<50%)",
        "Strict Chemical Suppression on low confidence & non-fungal classes",
        "Open-Meteo Integration: Real-time Wind, Rain & Heat Gating",
        "Wind >15km/h Abort (Drift) | Rain >70% Abort (Wash-off) | Heat >35C",
        "Insecticides Act, 1968 Disclaimers & Pre-Harvest Intervals (PHI)"
    ], c_accent_amber, "CIBRC / ICAR")

    # 7. TRILINGUAL HYBRID RAG ASSISTANT
    draw_box(4, 18, 44, 22, "7. Trilingual Hybrid RAG Knowledge Assistant", "Dense / Sparse Reciprocal Rank Fusion", [
        "Authoritative Knowledge Seeds: ICAR-SBI, ICAR-IIHR, ICAR-DOGR",
        "Trilingual Corpus: Marathi (मराठी), Hindi (हिन्दी), English",
        "Dense Semantic Embeddings (R^128) + Sparse BM25 Lexical Index",
        "Reciprocal Rank Fusion: RRF(d) = sum( 1 / (60 + rank_m(d)) )",
        "Anti-Hallucination Guardrails & Multi-Turn Conversational Memory"
    ], c_accent_purple, "HYBRID RAG")

    # 8. PERSISTENCE & DATA STORAGE
    draw_box(4, 2, 92, 13, "8. Storage, Database & Production Infrastructure Layer", "Multi-Tenant Relational & Vector Persistence", [
        "PostgreSQL 16 + pgvector: Users, Farms, Crop Cycles, Diagnoses, Multilingual Disease Knowledge Records",
        "Redis 7.x In-Memory Cache: Session Management, Weather Telemetry & Latency Optimization",
        "Local Secure File Storage: UUID-Isolated Images, Resized Foliage Assets & Heatmap Overlays",
        "Production Containerization: Multi-stage Dockerfile, Docker Compose Orchestration & Nginx Reverse Proxy"
    ], c_border, "PERSISTENCE")

    # Connecting Arrows
    def draw_arrow(x1, y1, x2, y2, color):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", 
                                    color=color, lw=1.8))

    draw_arrow(32, 83.5, 36, 83.5, c_accent_blue)
    draw_arrow(64, 83.5, 68, 83.5, c_accent_amber)
    draw_arrow(50, 76, 26, 71, c_accent_green)
    draw_arrow(26, 43, 26, 40, c_accent_purple)
    draw_arrow(48, 57, 52, 57, c_accent_purple)
    draw_arrow(48, 49, 52, 35, c_accent_amber)
    draw_arrow(74, 43, 74, 40, c_accent_amber)
    draw_arrow(50, 23, 50, 15, c_border)
    draw_arrow(26, 18, 26, 15, c_border)

    plt.tight_layout()
    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_p), format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"[SUCCESS] Architecture diagram generated: {output_p}")

if __name__ == "__main__":
    out_file = Path("reports/final_audit/PIKVAIDYA_AI_ARCHITECTURE_DIAGRAM.png")
    generate_diagram(str(out_file))

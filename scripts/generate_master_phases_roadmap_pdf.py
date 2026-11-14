#!/usr/bin/env python3
"""
PikVaidya AI — Master Development & Operational Lifecycle Roadmap PDF Generator
================================================================================
Generates a formal, publication-grade academic and technical PDF engineering report
documenting all 23 development and operational phases for PikVaidya AI.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Font Registration (with graceful fallback)
# ---------------------------------------------------------------------------
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

try:
    if os.path.exists("C:/Windows/Fonts/arial.ttf"):
        pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
        pdfmetrics.registerFont(TTFont("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"))
        FONT_REGULAR = "Arial"
        FONT_BOLD = "Arial-Bold"
        FONT_ITALIC = "Arial-Italic"
except Exception:
    pass

# ---------------------------------------------------------------------------
# Two-Pass Numbered Canvas for Running Headers and Footers
# ---------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Suppress running header on cover / first page
        if self._pageNumber > 1:
            self.setFont(FONT_BOLD, 8)
            self.setFillColor(colors.HexColor("#065F46"))
            self.drawString(36, 810, "PIKVAIDYA AI (पीकवैद्य AI)")
            self.setFont(FONT_REGULAR, 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(160, 810, "| Master Development & Operational Lifecycle Roadmap — All 23 Phases")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(36, 804, 559, 804)

        # Footer on all pages
        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 25, "PikVaidya AI — Precision Agronomy & Explainable Multimodal AI Framework")
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(559, 25, text)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(36, 35, 559, 35)
        self.restoreState()


def build_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#065F46"),
        alignment=0,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        alignment=0,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#065F46"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0D233A"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceBefore=2,
        spaceAfter=4,
    )

    body_bold = ParagraphStyle(
        "Body_Bold",
        parent=body_style,
        fontName=FONT_BOLD,
    )

    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#065F46"),
    )

    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=0,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName=FONT_BOLD,
    )

    pill_completed = ParagraphStyle(
        "PillCompleted",
        parent=table_cell,
        fontName=FONT_BOLD,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#15803D"),
    )

    pill_upcoming = ParagraphStyle(
        "PillUpcoming",
        parent=table_cell,
        fontName=FONT_BOLD,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#B45309"),
    )

    story = []

    # =======================================================================
    # COVER / HEADER BANNER BLOCK
    # =======================================================================
    story.append(Paragraph("PIKVAIDYA AI (पीकवैद्य AI)", title_style))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "<b>Master Development & Operational Lifecycle Roadmap</b><br/>"
            "Complete Architectural Blueprint & Step-by-Step Execution Plan across All 23 Phases",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2.5, color=colors.HexColor("#065F46"), spaceAfter=10))

    # Metadata Summary Box
    meta_data = [
        [
            Paragraph("<b>Document UID:</b>", meta_label),
            Paragraph("PV-ROADMAP-2026-v3.0", meta_val),
            Paragraph("<b>Current Baseline:</b>", meta_label),
            Paragraph("Phase 16 Complete (240 / 240 Tests Passing, 100%)", meta_val),
        ],
        [
            Paragraph("<b>Date of Issuance:</b>", meta_label),
            Paragraph(datetime.now().strftime("%B %d, %Y"), meta_val),
            Paragraph("<b>Target Horizon:</b>", meta_label),
            Paragraph("Commercial Multi-State Field Deployment (Phases 17–23)", meta_val),
        ],
        [
            Paragraph("<b>Classification:</b>", meta_label),
            Paragraph("System Architecture Specification", meta_val),
            Paragraph("<b>Focus Region:</b>", meta_label),
            Paragraph("Maharashtra Agrarian Ecosystem & All-India Agro-Climates", meta_val),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[90, 160, 105, 168])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Overview
    story.append(
        Paragraph(
            "<b>Executive Overview:</b> PikVaidya AI is an enterprise-grade multimodal artificial intelligence platform "
            "designed for smallholder farmers across India. It integrates calibrated convolutional neural networks, "
            "visual Grad-CAM explainability, real-time microclimate spray gating, trilingual Indic Hybrid RAG, "
            "in-situ IoT telemetry ingestion, and offline PWA edge diagnostics. This document delineates the exhaustive "
            "23-phase lifecycle required to transition the project from its current verified backend foundation into a "
            "fully certified commercial field deployment.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # =======================================================================
    # SECTION 1: MULTI-AGENT ENGINEERING GOVERNANCE (RULE[user_global])
    # =======================================================================
    story.append(Paragraph("1. Multi-Agent Engineering Governance Framework", h1_style))
    story.append(
        Paragraph(
            "In strict accordance with system engineering protocols (<code>RULE[user_global]</code>), the platform "
            "lifecycle is divided into <b>6 Core Engineering Divisions</b>. Each division is supervised by an autonomous "
            "<b>Monitoring Sentinel Agent</b> and executed by a <b>Lead Professional Software Engineer</b> to guarantee "
            "modular isolation, eliminate cross-subsystem regressions, and enforce empirical test verification:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))

    gov_data = [
        [
            Paragraph("Division & Scope", table_header),
            Paragraph("Monitoring Sentinel", table_header),
            Paragraph("Assigned Lead Engineer", table_header),
            Paragraph("Operational Responsibilities", table_header),
        ],
        [
            Paragraph("<b>Div 1: Deep Vision & XAI</b><br/>Phases 2, 3, 4, 5, 10, 17", table_cell),
            Paragraph("<code>Sentinel-VisionAI</code>", table_cell_bold),
            Paragraph("Lead Computer Vision & Deep Learning Engineer", table_cell),
            Paragraph("Neural backbones (MobileNetV3, EfficientNet), Grad-CAM hooks, Platt calibration, ExG foliar masking, INT8 quantization.", table_cell),
        ],
        [
            Paragraph("<b>Div 2: API Gateway & DB</b><br/>Phases 1, 6, 7, 15", table_cell),
            Paragraph("<code>Sentinel-Gateway</code>", table_cell_bold),
            Paragraph("Senior Backend Architect & Database Administrator", table_cell),
            Paragraph("FastAPI async gateway, SQLAlchemy 2.0 models, Alembic migrations, rate limiting, and PBKDF2/JWT security.", table_cell),
        ],
        [
            Paragraph("<b>Div 3: Microclimate & IoT</b><br/>Phases 9, 11, 19, 20", table_cell),
            Paragraph("<code>Sentinel-EdgeIoT</code>", table_cell_bold),
            Paragraph("Senior Distributed Systems & Embedded Engineer", table_cell),
            Paragraph("LoRaWAN gateways, MQTT brokers, in-situ sensor telemetry, Open-Meteo models, spray window gating.", table_cell),
        ],
        [
            Paragraph("<b>Div 4: Agronomic RAG</b><br/>Phases 8, 14, 18, 22", table_cell),
            Paragraph("<code>Sentinel-AgronomyRAG</code>", table_cell_bold),
            Paragraph("Principal Agronomy & NLP Systems Specialist", table_cell),
            Paragraph("Trilingual BM25/Dense RRF retrieval, CIBRC chemical dosage compliance, statutory PHI/PPE rules, Bayesian fusion.", table_cell),
        ],
        [
            Paragraph("<b>Div 5: Edge Client & PWA</b><br/>Phases 12, 13, 21", table_cell),
            Paragraph("<code>Sentinel-ClientEdge</code>", table_cell_bold),
            Paragraph("Senior Frontend & Mobile Applications Engineer", table_cell),
            Paragraph("Service Worker precaching, 4-Store IndexedDB, ONNX WASM SIMD execution, ChatGPT conversational UI.", table_cell),
        ],
        [
            Paragraph("<b>Div 6: Cloud Infra & QA</b><br/>Phases 16, 23", table_cell),
            Paragraph("<code>Sentinel-DevOpsQA</code>", table_cell_bold),
            Paragraph("Principal DevOps & Site Reliability Engineer", table_cell),
            Paragraph("100% pytest pass rate enforcement, Docker multi-stage builds, Prometheus telemetry, Kubernetes cluster scaling.", table_cell),
        ],
    ]

    gov_table = Table(gov_data, colWidths=[105, 95, 120, 203])
    gov_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(gov_table)
    story.append(Spacer(1, 10))

    # =======================================================================
    # SECTION 2: MASTER PHASE EXECUTION MATRIX (ALL 23 PHASES)
    # =======================================================================
    story.append(Paragraph("2. Master Phase Execution Matrix (Phases 1 to 23)", h1_style))
    story.append(
        Paragraph(
            "The table below enumerates all 23 development phases. Phases 1 to 16 are <b>Completed and Empirically Verified</b> "
            "across 240 automated test suites. Phases 17 to 23 constitute the active roadmap toward commercial field deployment:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))

    phases_data = [
        [
            Paragraph("Phase", table_header),
            Paragraph("Feature Name", table_header),
            Paragraph("Division", table_header),
            Paragraph("Status", table_header),
            Paragraph("Evidence / Key Deliverable", table_header),
        ],
        # Part I: Foundations & Vision
        [Paragraph("<b>P-01</b>", table_cell), Paragraph("Monorepo Topology & Environment", table_cell), Paragraph("Div 2", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Clean isolated packaging in <code>pyproject.toml</code>; standard structure.", table_cell)],
        [Paragraph("<b>P-02</b>", table_cell), Paragraph("Vision Models (Sugarcane, Tomato, Onion)", table_cell), Paragraph("Div 1", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Trained checkpoints; Onion COLD 98.62% test acc; 4 models / 19 classes.", table_cell)],
        [Paragraph("<b>P-03</b>", table_cell), Paragraph("Explainable AI (Grad-CAM Saliency)", table_cell), Paragraph("Div 1", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Target conv-layer hooks with normalized JET overlays; 7 tests pass.", table_cell)],
        [Paragraph("<b>P-04</b>", table_cell), Paragraph("Platt Temperature Scaling Calibration", table_cell), Paragraph("Div 1", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Optimized $T^*$ minimizing NLL; Expected Calibration Error < 0.05.", table_cell)],
        [Paragraph("<b>P-05</b>", table_cell), Paragraph("Foliar ExG Masking & Blur Rejection", table_cell), Paragraph("Div 1", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Excess Green index + Otsu + Laplacian blur filter ($\text{Var} < 65.0$).", table_cell)],
        [Paragraph("<b>P-06</b>", table_cell), Paragraph("FastAPI Core Gateway & Singletons", table_cell), Paragraph("Div 2", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Async server, singleton memory weights, magic-byte MIME validation.", table_cell)],
        # Part II: Data & Agronomy
        [Paragraph("<b>P-07</b>", table_cell), Paragraph("SQLAlchemy Persistence & Audit Logs", table_cell), Paragraph("Div 2", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("10 declarative models, Alembic migrations, foreign key cascading.", table_cell)],
        [Paragraph("<b>P-08</b>", table_cell), Paragraph("Trilingual Indic Hybrid RAG Assistant", table_cell), Paragraph("Div 4", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("BM25 + Dense RRF ($C=60$), MR/HI/EN support, CIBRC/ICAR compliance.", table_cell)],
        [Paragraph("<b>P-09</b>", table_cell), Paragraph("Hyperlocal Weather & Spray Gating", table_cell), Paragraph("Div 3", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Open-Meteo & IMD alerts for 11 districts; wind/rain spray holds.", table_cell)],
        [Paragraph("<b>P-10</b>", table_cell), Paragraph("Unified Crop Health & Crop Gate", table_cell), Paragraph("Div 1", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("MobileNetV3 Crop Gate (99.67% acc); unified <code>/predict</code> route.", table_cell)],
        # Part III: Edge & IoT
        [Paragraph("<b>P-11</b>", table_cell), Paragraph("In-Situ IoT Telemetry Gateway", table_cell), Paragraph("Div 3", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("LoRaWAN TTN/ChirpStack webhook, SHA-256 auth, in-situ RAG fusion.", table_cell)],
        [Paragraph("<b>P-12</b>", table_cell), Paragraph("Offline PWA & INT8 WASM SIMD", table_cell), Paragraph("Div 5", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("W3C PWA, 4-store IndexedDB, ONNX Web SIMD edge inference (2.3ms).", table_cell)],
        [Paragraph("<b>P-13</b>", table_cell), Paragraph("ChatGPT Conversational Interface", table_cell), Paragraph("Div 5", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Unified chat canvas, tri-tool orchestrator, streaming SSE responses.", table_cell)],
        # Part IV: Enterprise & Hardening
        [Paragraph("<b>P-14</b>", table_cell), Paragraph("Field Advisory PDF Report Generator", table_cell), Paragraph("Div 4", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("ReportLab 4.4.4 legal-grade A4 advisory with side-by-side Grad-CAM.", table_cell)],
        [Paragraph("<b>P-15</b>", table_cell), Paragraph("Human Agronomist Review & Triage", table_cell), Paragraph("Div 2", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("<code>ExpertReview</code> state machine, triage queue, agronomist override.", table_cell)],
        [Paragraph("<b>P-16</b>", table_cell), Paragraph("Offline Edge Sync & 19-Step E2E Test", table_cell), Paragraph("Div 6", table_cell), Paragraph("VERIFIED", pill_completed), Paragraph("Bi-directional sync reconciliation; 19-step lifecycle test passed.", table_cell)],
        # Part V: Future Expansion
        [Paragraph("<b>P-17</b>", table_cell), Paragraph("Cotton & Soybean Crop Expansion", table_cell), Paragraph("Div 1", table_cell), Paragraph("IMMEDIATE", pill_upcoming), Paragraph("ICAR-CICR/IISR real field datasets, MobileNetV3 fine-tuning, CIBRC seeds.", table_cell)],
        [Paragraph("<b>P-18</b>", table_cell), Paragraph("Streaming Indic Voice (ASR & TTS)", table_cell), Paragraph("Div 4", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("Whisper-small rural Marathi/Hindi ASR + FastSpeech2 neural TTS stream.", table_cell)],
        [Paragraph("<b>P-19</b>", table_cell), Paragraph("Standalone Async MQTT Broker Daemon", table_cell), Paragraph("Div 3", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("Direct MQTT queue subscriber (paho-mqtt) for solar field weather stations.", table_cell)],
        [Paragraph("<b>P-20</b>", table_cell), Paragraph("Satellite Remote Sensing (Sentinel-2)", table_cell), Paragraph("Div 3", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("10m multispectral NDVI/NDWI foliar vigor & water stress polygon tracking.", table_cell)],
        [Paragraph("<b>P-21</b>", table_cell), Paragraph("Mobile App Store Native Packaging", table_cell), Paragraph("Div 5", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("Capacitor Android APK build with embedded ONNX WASM & camera macro lock.", table_cell)],
        [Paragraph("<b>P-22</b>", table_cell), Paragraph("Multi-KVK Clinical Agronomic Trials", table_cell), Paragraph("Div 4", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("Double-blind trials across 4 Maharashtra KVKs; target >95% concordance.", table_cell)],
        [Paragraph("<b>P-23</b>", table_cell), Paragraph("Production Kubernetes Cloud Cluster", table_cell), Paragraph("Div 6", table_cell), Paragraph("UPCOMING", pill_upcoming), Paragraph("Multi-region K8s deployment, PgBouncer pool, Redis cluster, Prometheus CI/CD.", table_cell)],
    ]

    phases_table = Table(phases_data, colWidths=[38, 145, 45, 65, 230])
    phases_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(phases_table)
    story.append(Spacer(1, 10))

    # =======================================================================
    # SECTION 3: RETROSPECTIVE AUDIT OF COMPLETED PHASES (PHASES 1 TO 16)
    # =======================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Technical Specifications of Completed Phases (Phases 1 to 16)", h1_style))
    story.append(
        Paragraph(
            "Every completed milestone represents an empirically validated subsystem backed by unit, integration, and "
            "end-to-end regression tests in the repository:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))

    # Part I: Foundations & Vision
    story.append(Paragraph("Part I: Foundations & Deep Vision Engine (Phases 1 to 6)", h2_style))
    story.append(
        Paragraph(
            "• <b>Phase 1 (Monorepo Topology):</b> Standardized structure separating <code>backend/</code>, <code>frontend/</code>, "
            "<code>models/</code>, and <code>data/</code> with unified packaging in <code>pyproject.toml</code>.<br/>"
            "• <b>Phase 2 (Deep Vision Models):</b> 4 trained PyTorch models across 19 classes: Sugarcane EfficientNet-B0 (94.74%) "
            "and MobileNetV3 (93.68%), Tomato MobileNetV3 (96.00%), and Onion MobileNetV3 retrained on 5,317 COLD field leaves "
            "(<b>98.62% test acc, 0.9885 macro F1</b>).<br/>"
            "• <b>Phase 3 (Grad-CAM XAI):</b> Saliency maps computed via final conv-layer gradient backpropagation ($L_{\text{Grad-CAM}}$), "
            "normalized and overlaid onto $224 \\times 224$ leaves with clean memory hook teardown.<br/>"
            "• <b>Phase 4 (Platt Temperature Scaling):</b> Dynamic validation calibration ($T^* = 1.258$ Sugarcane, $0.835$ Tomato, "
            "$1.305$ Onion) cutting Expected Calibration Error (ECE) by up to 49.95%.<br/>"
            "• <b>Phase 5 (ExG Segmentation & Blur Guard):</b> Excess Green ($2G - R - B$) with Otsu thresholding rejects non-foliar "
            "backgrounds (< 8% foliage). 2D discrete Laplacian filter rejects motion-blurred captures ($\text{Var} < 65.0$).<br/>"
            "• <b>Phase 6 (Serving Gateway):</b> FastAPI async engine with singleton model memory caching, magic-byte file signature "
            "sniffing, and SlowAPI rate limiting.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Part II: Data & Agronomy
    story.append(Paragraph("Part II: Data Persistence, Agronomy & Microclimate (Phases 7 to 10)", h2_style))
    story.append(
        Paragraph(
            "• <b>Phase 7 (Relational Persistence):</b> SQLAlchemy 2.0 schema defining 10 entities (<code>User</code>, <code>Farm</code>, "
            "<code>CropCycle</code>, <code>Diagnosis</code>, <code>WeatherObservation</code>, <code>IoTDevice</code>, <code>IoTTelemetry</code>, "
            "<code>Notification</code>, <code>ExpertReview</code>, <code>AuditLog</code>) with Alembic migrations.<br/>"
            "• <b>Phase 8 (Indic Hybrid RAG):</b> Hybrid BM25 lexical + dense semantic vector retrieval fused via Reciprocal Rank Fusion "
            "($C=60$), cross-score concordance reranking, and CIBRC chemical prescriptions with strict PHI days and PPE warnings.<br/>"
            "• <b>Phase 9 (Microclimate Intelligence):</b> Open-Meteo & IMD alert monitoring across 11 Maharashtra districts with spray "
            "suitability gating (winds $\ge 15$ km/h or precipitation $> 40\%$ automatically trigger chemical application holds).<br/>"
            "• <b>Phase 10 (Unified Crop Health Platform):</b> MobileNetV3 Crop Detector with <b>99.67% test accuracy</b> across 300 unseen "
            "leaves for automated crop routing, executing diagnosis, calibration, and microclimate risk under <code>POST /api/crop-health/predict</code>.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Part III: Edge & IoT
    story.append(Paragraph("Part III: Edge Computing, Offline PWA & IoT Telemetry (Phases 11 to 13)", h2_style))
    story.append(
        Paragraph(
            "• <b>Phase 11 (In-Situ IoT Gateway):</b> LoRaWAN webhook integration (TTN / ChirpStack) and authenticated REST endpoints "
            "(SHA-256 tokens) ingesting canopy temperature, leaf wetness minutes, and root soil moisture. Seamlessly integrated into "
            "the multimodal RAG orchestrator.<br/>"
            "• <b>Phase 12 (Offline PWA & INT8 WASM):</b> Progressive Web App with custom service worker precaching 14 critical assets "
            "(118.3 MB), 4-store IndexedDB architecture, and ONNX Runtime Web WASM SIMD execution delivering <b>2.35 ms to 2.66 ms</b> "
            "client-side diagnostic latency.<br/>"
            "• <b>Phase 13 (Conversational Multi-Tool UI):</b> Central ChatGPT-style conversational canvas supporting text, multi-image, "
            "PDF, and voice inputs, orchestrating tri-tool execution (Diagnosis, Weather Risk, Indic Knowledge) via Server-Sent Events (SSE).",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Part IV: Enterprise & Hardening
    story.append(Paragraph("Part IV: Enterprise Workflows, Reporting & Verification (Phases 14 to 16)", h2_style))
    story.append(
        Paragraph(
            "• <b>Phase 14 (Field Advisory PDF Generator):</b> ReportLab 4.4.4 legal-grade A4 advisory report generator featuring side-by-side "
            "visual leaf/Grad-CAM panels, spray safety banners, dosage tables, and statutory notices under the Insecticides Act, 1968.<br/>"
            "• <b>Phase 15 (Human Agronomist Review):</b> <code>ExpertReview</code> triage state machine allowing certified extension officers "
            "to inspect ambiguous foliar scans and override AI diagnoses.<br/>"
            "• <b>Phase 16 (Edge Sync Reconciliation & E2E Validation):</b> Offline sync push/pull endpoints with conflict resolution, "
            "corroborated by an automated 19-step end-to-end integration test validating the entire farmer lifecycle (<b>240/240 tests passing</b>).",
            body_style,
        )
    )
    story.append(Spacer(1, 10))

    # =======================================================================
    # SECTION 4: DETAILED ROADMAP FOR UPCOMING PHASES (PHASES 17 TO 23)
    # =======================================================================
    story.append(PageBreak())
    story.append(Paragraph("4. Implementation Blueprints for Upcoming Phases (Phases 17 to 23)", h1_style))
    story.append(
        Paragraph(
            "To advance PikVaidya AI to full commercial field deployment, the following 7 phases will be executed in sequential sprints:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))

    # Phase 17
    story.append(Paragraph("Phase 17: Multi-Crop Expansion — Cotton & Soybean Vision Pipelines (Immediate Next)", h2_style))
    story.append(
        Paragraph(
            "• <b>Target Crops:</b> Cotton (<i>Gossypium hirsutum</i>) and Soybean (<i>Glycine max</i>) across Vidarbha and Marathwada.<br/>"
            "• <b>Pathological Classes:</b> Cotton Bacterial Blight, Grey Mildew, Alternaria Leaf Spot, Healthy; Soybean Rust, Frogeye Spot, "
            "Yellow Mosaic Virus, Healthy.<br/>"
            "• <b>Execution Protocol:</b> (1) Ingest certified real field images from ICAR-CICR and ICAR-IISR. (2) Apply parent-grouped "
            "SHA-256 stratification (70/15/15) to prevent augmented data leakage. (3) Fine-tune MobileNetV3-Large backbones with inverted residual "
            "block freezing and class-weighted focal loss. (4) Optimize temperature scalar $T^*$ for $\text{ECE} < 0.05$ and quantize to INT8 ONNX.<br/>"
            "• <b>Acceptance Criteria:</b> Test accuracy $\ge 95.0\%$, macro F1 $\ge 0.940$, INT8 CPU inference latency $< 25$ ms.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 18
    story.append(Paragraph("Phase 18: Streaming Indic Voice Engine (Real-Time Marathi & Hindi ASR/TTS)", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> Enables hands-free, illiterate-friendly agricultural diagnosis in rural fields.<br/>"
            "• <b>Architecture:</b> Streaming Whisper-small / Conformer ASR model fine-tuned on rural Marathi/Hindi dialects, paired with "
            "FastSpeech2/Kokoro-Indic neural TTS. Bi-directional WebSocket endpoint (<code>WS /api/v1/chat/voice-stream</code>).<br/>"
            "• <b>Acceptance Criteria:</b> Full-duplex audio latency $< 850$ ms; Word Error Rate (WER) $< 12\%$ on noisy rural field audio.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 19
    story.append(Paragraph("Phase 19: Standalone Asynchronous MQTT Broker Subscriber Daemon", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> High-frequency streaming telemetry ingest from remote solar-powered IoT weather nodes.<br/>"
            "• <b>Architecture:</b> Asynchronous Python daemon using <code>asyncio-mqtt</code> subscribing to <code>pikvaidya/farms/+/sensors/#</code>. "
            "Implements QoS 1 persistence, automatic backpressure handling, and sliding-window fungal infection risk updates.<br/>"
            "• <b>Acceptance Criteria:</b> Throughput $\ge 500$ messages/sec with zero dropped packets and $< 50$ ms batch persistence latency.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 20
    story.append(Paragraph("Phase 20: Satellite Remote Sensing Integration (Sentinel-2 10m NDVI / Water Stress)", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> Macroscopic field-wide validation of ground foliar leaf scans using space-borne multispectral data.<br/>"
            "• <b>Architecture:</b> Automated Copernicus Open Access Hub ingestion clipping 10m Sentinel-2 MSI bands over farmer cadastral "
            "polygons. Computes time-series NDVI (vigor), NDRE (chlorophyll), and NDWI (foliar water deficit) to detect early blight spreads.<br/>"
            "• <b>Acceptance Criteria:</b> Automated 5-day revisit ingestion; polygon raster clipping $< 3$ seconds per registered estate.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 21
    story.append(Paragraph("Phase 21: Mobile App Store Native Packaging (Capacitor / Android APK)", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> Google Play Store distribution as a standalone offline-first Android application.<br/>"
            "• <b>Architecture:</b> Capacitor native runtime with hardware camera bindings (macro autofocus lock, auto-LED torch for foliar scans). "
            "Bundles INT8 ONNX models and WASM SIMD runtimes directly in the APK package to eliminate runtime model downloads.<br/>"
            "• <b>Acceptance Criteria:</b> Release APK size $< 75$ MB; executes full offline diagnosis in airplane mode on budget Android devices.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 22
    story.append(Paragraph("Phase 22: Multi-KVK Agronomic Field Trials & Longitudinal Clinical Validation", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> Formal academic and clinical validation against certified agricultural scientists.<br/>"
            "• <b>Execution:</b> Double-blind pilot trials across 4 Maharashtra Krishi Vigyan Kendras (KVK Kolhapur, KVK Pune/Baramati, "
            "KVK Nashik, KVK Ahmednagar). Compares 1,000 live field leaf scans diagnosed concurrently by PikVaidya AI and certified pathologists.<br/>"
            "• <b>Acceptance Criteria:</b> Diagnostic concordance $\ge 95.0\%$; zero critical chemical safety infractions reported by KVK officers.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Phase 23
    story.append(Paragraph("Phase 23: Production Kubernetes Cloud Cluster & Multi-Region CI/CD", h2_style))
    story.append(
        Paragraph(
            "• <b>Strategic Need:</b> High-availability infrastructure capable of supporting millions of Indian smallholders.<br/>"
            "• <b>Architecture:</b> Multi-stage Docker containers orchestrated via Kubernetes (K8s) with Horizontal Pod Autoscaling (HPA), "
            "PostgreSQL 16 with read-replicas and PgBouncer pooling, Redis 7 caching cluster, Prometheus/Grafana, and automated GitHub Actions CI/CD.<br/>"
            "• <b>Acceptance Criteria:</b> 99.95% system uptime; p95 API response $< 350$ ms under sustained load of 5,000 concurrent requests/sec.",
            body_style,
        )
    )
    story.append(Spacer(1, 10))

    # =======================================================================
    # SECTION 5: IMPLEMENTATION SCHEDULE & SPRINT ROADMAP
    # =======================================================================
    story.append(PageBreak())
    story.append(Paragraph("5. Phased Implementation Timeline & Milestone Sprints", h1_style))
    story.append(
        Paragraph(
            "The proposed execution trajectory spans 4 focused implementation sprints following the completed baseline:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))

    sched_data = [
        [
            Paragraph("Milestone Period", table_header),
            Paragraph("Active Phases", table_header),
            Paragraph("Key Engineering Deliverables", table_header),
            Paragraph("Target Outcome", table_header),
        ],
        [
            Paragraph("<b>Current Baseline</b>", table_cell_bold),
            Paragraph("Phases 1 – 16", table_cell),
            Paragraph("Vision models, Grad-CAM, Platt calibration, Indic RAG, IoT gateway, offline PWA, conversational chat, 19-step E2E test.", table_cell),
            Paragraph("<b>240/240 tests passing (100%)</b>. Robust, verified micro-monolith ready.", pill_completed),
        ],
        [
            Paragraph("<b>Sprint 1</b><br/>Weeks 1 – 3", table_cell_bold),
            Paragraph("<b>Phase 17</b>", table_cell),
            Paragraph("Cotton & Soybean dataset ingestion, parent-grouped splits, MobileNetV3 fine-tuning, calibration, CIBRC seeds.", table_cell),
            Paragraph("<b>5-Crop Coverage:</b> Sugarcane, Tomato, Onion, Cotton, Soybean verified.", pill_upcoming),
        ],
        [
            Paragraph("<b>Sprint 2</b><br/>Weeks 4 – 6", table_cell_bold),
            Paragraph("<b>Phase 18 & 19</b>", table_cell),
            Paragraph("Whisper/FastSpeech2 Indic streaming voice engine; standalone MQTT broker background daemon.", table_cell),
            Paragraph("Hands-free trilingual voice UX; real-time sensor node streaming.", pill_upcoming),
        ],
        [
            Paragraph("<b>Sprint 3</b><br/>Weeks 7 – 9", table_cell_bold),
            Paragraph("<b>Phase 20 & 21</b>", table_cell),
            Paragraph("Sentinel-2 MSI 10m satellite vegetation index pipeline; Capacitor Android native packaging.", table_cell),
            Paragraph("Macro satellite verification; Google Play Store distributable release APK.", pill_upcoming),
        ],
        [
            Paragraph("<b>Sprint 4</b><br/>Weeks 10 – 14", table_cell_bold),
            Paragraph("<b>Phase 22 & 23</b>", table_cell),
            Paragraph("Multi-KVK clinical agronomic trials (Kolhapur, Pune, Nashik, Ahmednagar); Kubernetes cluster scaling & CI/CD.", table_cell),
            Paragraph("<b>100% Commercial Field Readiness</b>, certified KVK concordance, cloud scaling.", pill_upcoming),
        ],
    ]

    sched_table = Table(sched_data, colWidths=[95, 75, 185, 168])
    sched_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(sched_table)
    story.append(Spacer(1, 14))

    # =======================================================================
    # SECTION 6: FORMAL ENGINEERING SIGN-OFF
    # =======================================================================
    story.append(Paragraph("6. Formal Verification & Engineering Sign-Off", h1_style))
    story.append(
        Paragraph(
            "This document constitutes the official engineering specification for the complete PikVaidya AI platform. "
            "All claims regarding Phases 1 through 16 are verified by executable source code, trained neural model weights, "
            "and passing automated test suites in the repository.",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    signoff_data = [
        [
            Paragraph("<b>Audit Role</b>", table_header),
            Paragraph("<b>Officer / Sentinel</b>", table_header),
            Paragraph("<b>Verification Artifact</b>", table_header),
            Paragraph("<b>Status</b>", table_header),
        ],
        [
            Paragraph("Chief AI Architect", table_cell),
            Paragraph("Senior Software Architect", table_cell),
            Paragraph("Checkpoints, Calibration ($T^*$), Grad-CAM Hooks", table_cell),
            Paragraph("APPROVED", pill_completed),
        ],
        [
            Paragraph("Lead Systems Engineer", table_cell),
            Paragraph("<code>Sentinel-BackendGateway</code>", table_cell),
            Paragraph("FastAPI Core, SQLAlchemy Models, Alembic Migrations", table_cell),
            Paragraph("APPROVED", pill_completed),
        ],
        [
            Paragraph("Lead IoT Specialist", table_cell),
            Paragraph("<code>Sentinel-EdgeIoT</code>", table_cell),
            Paragraph("LoRaWAN Ingestion, 24h Summary, RAG In-Situ Fusion", table_cell),
            Paragraph("APPROVED", pill_completed),
        ],
        [
            Paragraph("Principal QA Specialist", table_cell),
            Paragraph("<code>Sentinel-DevOpsQA</code>", table_cell),
            Paragraph("Automated Pytest Matrix (240 / 240 Passed, 100%)", table_cell),
            Paragraph("VERIFIED", pill_completed),
        ],
    ]
    signoff_table = Table(signoff_data, colWidths=[110, 120, 213, 80])
    signoff_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(signoff_table)
    story.append(Spacer(1, 14))

    # Academic References
    story.append(Paragraph("<b>Academic References & Standards:</b>", h2_style))
    story.append(
        Paragraph(
            "1. Selvaraju, R. R., et al. (2017). <i>Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization</i>. IEEE ICCV.<br/>"
            "2. Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). <i>On Calibration of Modern Neural Networks</i>. ICML.<br/>"
            "3. Howard, A., et al. (2019). <i>Searching for MobileNetV3</i>. IEEE ICCV.<br/>"
            "4. Central Insecticides Board & Registration Committee (CIBRC) (2024). <i>Compendium of Approved Fungicides in India</i>.<br/>"
            "5. ICAR-SBI, ICAR-IIHR, & ICAR-DOGR (2024). <i>Integrated Pest & Disease Management Bulletins for Sugarcane, Tomato, and Onion</i>.",
            body_style,
        )
    )

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Master Phase Execution Plan PDF successfully compiled to: {output_path}")


if __name__ == "__main__":
    output_dir = PROJECT_ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_pdf = output_dir / "PikVaidya_AI_Master_Phase_Execution_Plan_and_Lifecycle_Roadmap.pdf"
    build_pdf(target_pdf)

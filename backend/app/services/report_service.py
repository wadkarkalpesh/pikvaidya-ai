"""
PikVaidya AI — Automated Agricultural Advisory PDF Field Report Generator
========================================================================
Generates publication-quality, authoritative PDF diagnostic field reports
for farmers, agronomists, and Krishi Vigyan Kendra (KVK) extension officers.

Compliance & Standards:
1. ICAR & CIBRC Agronomic Prescriptions
2. Insecticides Act, 1968 & Insecticides Rules, 1971 Statutory Disclaimers
3. Microclimate Telemetry & Weather Gating Rules
4. Bilingual terminology (English and Marathi transliterations)
"""

import io
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.schemas.advisory import ContextualAdvisoryResponse, AdvisoryChemicalPrescription
from app.models.diagnosis import Diagnosis

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page numbering and official footer."""

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

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 40, A4[0] - 36, 40)

        # Footer text
        footer_text = "PikVaidya AI — Explainable Multimodal Crop Diagnostic System | ICAR & CIBRC Aligned"
        page_str = f"Page {self._pageNumber} of {page_count}"

        self.drawString(36, 28, footer_text)
        self.drawRightString(A4[0] - 36, 28, page_str)
        self.restoreState()


class FieldAdvisoryReportService:
    """Enterprise report generator compiling diagnostic findings and microclimate advisories."""

    def __init__(self):
        self._init_styles()

    def _init_styles(self):
        self.styles = getSampleStyleSheet()

        self.style_banner_title = ParagraphStyle(
            "BannerTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#FFFFFF"),
        )
        self.style_banner_subtitle = ParagraphStyle(
            "BannerSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#D1FAE5"),
        )
        self.style_section_heading = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#065F46"),
            spaceBefore=10,
            spaceAfter=6,
        )
        self.style_body = ParagraphStyle(
            "Body",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1E293B"),
        )
        self.style_body_bold = ParagraphStyle(
            "BodyBold",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        )
        self.style_th = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#FFFFFF"),
            alignment=1,  # Centered
        )
        self.style_td = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        self.style_disclaimer = ParagraphStyle(
            "Disclaimer",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#475569"),
        )

    def generate_advisory_pdf(
        self,
        advisory: Union[ContextualAdvisoryResponse, Dict[str, Any]],
        farmer_name: str = "Registered Farmer",
        farm_location: str = "Maharashtra, India",
        farm_coordinates: Optional[str] = None,
        original_image_path: Optional[str] = None,
        heatmap_image_path: Optional[str] = None,
        report_id: Optional[str] = None,
        issue_date: Optional[datetime] = None,
    ) -> bytes:
        """Generates a complete, professional PDF report as bytes."""
        if isinstance(advisory, ContextualAdvisoryResponse):
            adv_dict = advisory.model_dump()
        else:
            adv_dict = advisory

        if not report_id:
            report_id = f"PV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not issue_date:
            issue_date = datetime.now()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=48,
        )

        story = []
        usable_width = A4[0] - 72  # 523.27 pt

        # 1. Header Banner
        story.append(self._build_header_banner(report_id, issue_date, usable_width))
        story.append(Spacer(1, 10))

        # 2. Metadata Table
        story.append(
            self._build_metadata_table(
                adv_dict, farmer_name, farm_location, farm_coordinates, report_id, issue_date, usable_width
            )
        )
        story.append(Spacer(1, 10))

        # 3. Diagnostic Vision Findings
        story.append(Paragraph("1. AI Diagnostic Pathology Assessment", self.style_section_heading))
        story.append(self._build_diagnostic_summary_table(adv_dict, usable_width))
        story.append(Spacer(1, 10))

        # 4. Visual Evidence (Original Image & Heatmap)
        story.append(Paragraph("2. Visual Lesion & Saliency Analysis", self.style_section_heading))
        story.append(self._build_visual_evidence_block(original_image_path, heatmap_image_path, usable_width))
        story.append(Spacer(1, 10))

        # 5. Microclimate Telemetry & Spray Window Status
        story.append(Paragraph("3. Real-Time Microclimate & Spray Window Status", self.style_section_heading))
        story.append(self._build_weather_telemetry_block(adv_dict, usable_width))
        story.append(Spacer(1, 10))

        # 6. Agronomic Prescriptions
        story.append(Paragraph("4. Recommended Agronomic Management & Interventions", self.style_section_heading))
        story.append(self._build_management_practices_block(adv_dict, usable_width))
        story.append(Spacer(1, 10))

        # 7. Chemical Treatments Table (if applicable)
        chemicals = adv_dict.get("chemical_prescriptions", [])
        if chemicals and adv_dict.get("is_chemical_permitted", False):
            story.append(Paragraph("5. CIBRC-Approved Chemical Prescriptions", self.style_section_heading))
            story.append(self._build_chemical_table(chemicals, usable_width))
            story.append(Spacer(1, 10))
        elif not adv_dict.get("is_chemical_permitted", False):
            suppression = adv_dict.get("chemical_suppression_reason", {})
            reason_msg = suppression.get("en", "Chemical treatments with-held pending diagnostic certainty or healthy condition.")
            story.append(self._build_suppression_alert(reason_msg, usable_width))
            story.append(Spacer(1, 10))

        # 8. Statutory Disclaimers & Signoff
        story.append(self._build_disclaimer_block(adv_dict, usable_width))

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_from_diagnosis(
        self,
        diagnosis: Diagnosis,
        advisory: Union[ContextualAdvisoryResponse, Dict[str, Any]],
        farmer_name: Optional[str] = None,
        farm_location: Optional[str] = None,
        farm_coordinates: Optional[str] = None,
    ) -> bytes:
        """Helper to generate PDF directly from a database Diagnosis record."""
        farmer = farmer_name or (diagnosis.user.name if diagnosis.user else "Registered Farmer")
        location = farm_location or "Maharashtra, India"
        coords = farm_coordinates
        if not coords and hasattr(diagnosis, "crop_cycle") and diagnosis.crop_cycle and diagnosis.crop_cycle.farm:
            farm = diagnosis.crop_cycle.farm
            if farm.latitude and farm.longitude:
                coords = f"{farm.latitude:.4f}° N, {farm.longitude:.4f}° E"

        return self.generate_advisory_pdf(
            advisory=advisory,
            farmer_name=farmer,
            farm_location=location,
            farm_coordinates=coords,
            original_image_path=diagnosis.image_path,
            heatmap_image_path=diagnosis.heatmap_path,
            report_id=f"PV-DIAG-{diagnosis.id:06d}",
            issue_date=diagnosis.created_at,
        )

    # -------------------------------------------------------------------------
    # Internal Layout Builders
    # -------------------------------------------------------------------------

    def _build_header_banner(self, report_id: str, issue_date: datetime, width: float) -> Table:
        title_p = Paragraph("PikVaidya AI — Agricultural Diagnostic Field Report", self.style_banner_title)
        subtitle_p = Paragraph(
            "Explainable Multimodal Crop Health & Context-Aware Smart Farming Advisory<br/>"
            "Compliant with ICAR & CIBRC Agronomic Guidelines | Maharashtra Agricultural Cluster",
            self.style_banner_subtitle,
        )

        header_table = Table([[title_p], [subtitle_p]], colWidths=[width])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#065F46")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        return header_table

    def _build_metadata_table(
        self, adv: Dict[str, Any], farmer: str, location: str, coords: Optional[str], report_id: str, date: datetime, width: float
    ) -> Table:
        crop_name = adv.get("crop_name", "Crop").capitalize()
        col_w = width / 4.0

        data = [
            [
                Paragraph("<b>Report ID:</b>", self.style_body),
                Paragraph(f"<font color='#059669'><b>{report_id}</b></font>", self.style_body),
                Paragraph("<b>Date / Time:</b>", self.style_body),
                Paragraph(date.strftime("%d-%b-%Y %I:%M %p"), self.style_body),
            ],
            [
                Paragraph("<b>Farmer Name:</b>", self.style_body),
                Paragraph(farmer, self.style_body),
                Paragraph("<b>Location:</b>", self.style_body),
                Paragraph(location, self.style_body),
            ],
            [
                Paragraph("<b>Target Crop:</b>", self.style_body),
                Paragraph(f"<b>{crop_name}</b>", self.style_body),
                Paragraph("<b>GPS Coordinates:</b>", self.style_body),
                Paragraph(coords or "Not Provided", self.style_body),
            ],
        ]

        table = Table(data, colWidths=[col_w * 0.9, col_w * 1.1, col_w * 0.9, col_w * 1.1])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_diagnostic_summary_table(self, adv: Dict[str, Any], width: float) -> Table:
        disease_names = adv.get("disease_name", {})
        name_en = disease_names.get("en", adv.get("disease_id", "Unknown"))
        name_mr = disease_names.get("mr", "")
        display_name = f"<b>{name_en}</b>"
        if name_mr:
            display_name += f" ({name_mr})"

        conf = adv.get("confidence", 0.0)
        tier = adv.get("confidence_tier", "MODERATE")
        severity = adv.get("severity", "UNAVAILABLE")
        area = adv.get("affected_area_percentage")
        area_str = f"{area:.1f}% Foliar Area" if area is not None else "Not Measured"
        pathogen = adv.get("pathogen_type", "Pathogen").capitalize()
        scientific = adv.get("scientific_name", "N/A")

        # Confidence color badge
        if tier == "HIGH":
            conf_badge = f"<font color='#059669'><b>{conf * 100:.2f}% (HIGH CONFIDENCE)</b></font>"
        elif tier == "MODERATE":
            conf_badge = f"<font color='#D97706'><b>{conf * 100:.2f}% (MODERATE CONFIDENCE)</b></font>"
        else:
            conf_badge = f"<font color='#DC2626'><b>{conf * 100:.2f}% (INCONCLUSIVE)</b></font>"

        col_w = width / 4.0
        data = [
            [
                Paragraph("<b>Identified Condition:</b>", self.style_body),
                Paragraph(display_name, self.style_body),
                Paragraph("<b>Scientific Name:</b>", self.style_body),
                Paragraph(f"<i>{scientific}</i>", self.style_body),
            ],
            [
                Paragraph("<b>Calibrated Confidence:</b>", self.style_body),
                Paragraph(conf_badge, self.style_body),
                Paragraph("<b>Pathogen Type:</b>", self.style_body),
                Paragraph(pathogen, self.style_body),
            ],
            [
                Paragraph("<b>Foliar Severity:</b>", self.style_body),
                Paragraph(f"<b>{severity}</b>", self.style_body),
                Paragraph("<b>Lesion Surface Area:</b>", self.style_body),
                Paragraph(area_str, self.style_body),
            ],
        ]

        table = Table(data, colWidths=[col_w * 0.9, col_w * 1.1, col_w * 0.9, col_w * 1.1])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_visual_evidence_block(
        self, original_path: Optional[str], heatmap_path: Optional[str], width: float
    ) -> Table:
        half_w = (width - 10) / 2.0
        img_h = 130  # Height in points

        col1_elements = [Paragraph("<b>Field Leaf Photograph</b>", self.style_body)]
        if original_path and os.path.exists(original_path):
            try:
                col1_elements.append(Image(original_path, width=half_w - 12, height=img_h))
            except Exception as e:
                logger.warning(f"Failed to embed original leaf image: {e}")
                col1_elements.append(Paragraph("<i>[Image Rendering Unavailable]</i>", self.style_body))
        else:
            col1_elements.append(Paragraph("<i>[Original leaf photograph submitted via ephemeral upload]</i>", self.style_body))

        col2_elements = [Paragraph("<b>Grad-CAM Lesion Saliency Heatmap</b>", self.style_body)]
        if heatmap_path and os.path.exists(heatmap_path):
            try:
                col2_elements.append(Image(heatmap_path, width=half_w - 12, height=img_h))
            except Exception as e:
                logger.warning(f"Failed to embed Grad-CAM heatmap: {e}")
                col2_elements.append(Paragraph("<i>[Heatmap Rendering Unavailable]</i>", self.style_body))
        else:
            col2_elements.append(Paragraph("<i>[Grad-CAM feature activation map generated during evaluation]</i>", self.style_body))

        data = [[col1_elements, col2_elements]]
        table = Table(data, colWidths=[half_w, half_w])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def _build_weather_telemetry_block(self, adv: Dict[str, Any], width: float) -> Table:
        weather = adv.get("weather_telemetry")
        if not weather:
            msg = Paragraph("<i>Live microclimate telemetry not linked for this assessment. Standard weather precautions apply.</i>", self.style_body)
            t = Table([[msg]], colWidths=[width])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1"))]))
            return t

        temp = f"{weather.get('temperature_c', 0.0):.1f} °C"
        humidity = f"{weather.get('relative_humidity_pct', 0.0):.1f}%"
        wind = f"{weather.get('wind_speed_kmh', 0.0):.1f} km/h"
        rain_prob = f"{weather.get('precipitation_probability_6h', 0.0):.0f}%"
        condition = weather.get("weather_condition", "Clear")
        suitability = weather.get("spray_suitability", "OPTIMAL")
        is_safe = weather.get("is_safe_to_spray", True)
        fungal_risk = weather.get("fungal_risk_level", "LOW")

        # Spray Window Badge
        if is_safe:
            status_badge = "<font color='#059669'><b>[OPTIMAL SPRAY WINDOW: GO]</b></font> Atmospheric conditions favorable."
            bg_color = colors.HexColor("#ECFDF5")
            box_color = colors.HexColor("#10B981")
        else:
            status_badge = f"<font color='#DC2626'><b>[SPRAY WINDOW GATED: CAUTION / NO-GO ({suitability})]</b></font> Rain or wind risk present."
            bg_color = colors.HexColor("#FEF2F2")
            box_color = colors.HexColor("#EF4444")

        guidance_dict = weather.get("spray_guidance", {})
        guidance_text = guidance_dict.get("en", "Check local forecast before foliar application.")

        col_w = width / 4.0
        data = [
            [
                Paragraph("<b>Temperature:</b>", self.style_body),
                Paragraph(temp, self.style_body),
                Paragraph("<b>Relative Humidity:</b>", self.style_body),
                Paragraph(humidity, self.style_body),
            ],
            [
                Paragraph("<b>Wind Speed:</b>", self.style_body),
                Paragraph(wind, self.style_body),
                Paragraph("<b>6h Rain Probability:</b>", self.style_body),
                Paragraph(rain_prob, self.style_body),
            ],
            [
                Paragraph("<b>Condition:</b>", self.style_body),
                Paragraph(condition, self.style_body),
                Paragraph("<b>Fungal Risk:</b>", self.style_body),
                Paragraph(f"<b>{fungal_risk}</b>", self.style_body),
            ],
            [
                Paragraph("<b>Spray Suitability:</b>", self.style_body),
                Paragraph(status_badge, self.style_body),
                Paragraph("<b>Agronomic Advice:</b>", self.style_body),
                Paragraph(guidance_text, self.style_body),
            ],
        ]

        table = Table(data, colWidths=[col_w * 0.9, col_w * 1.1, col_w * 0.9, col_w * 1.1])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -2), colors.HexColor("#FFFFFF")),
                    ("BACKGROUND", (0, 3), (-1, 3), bg_color),
                    ("BOX", (0, 0), (-1, -1), 0.5, box_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_management_practices_block(self, adv: Dict[str, Any], width: float) -> Table:
        cultural = adv.get("cultural_practices", {}).get("en", [])
        biological = adv.get("biological_controls", {}).get("en", [])

        cultural_str = "<br/>".join([f"• {p}" for p in cultural]) if cultural else "• Maintain regular field sanitation and adequate plant spacing."
        biological_str = "<br/>".join([f"• {p}" for p in biological]) if biological else "• Apply beneficial bio-fungicides (e.g. Trichoderma viride) where indicated."

        half_w = (width - 6) / 2.0
        data = [
            [
                Paragraph("<b>Cultural & Preventative Management</b>", self.style_body_bold),
                Paragraph("<b>Biological & Organic Options</b>", self.style_body_bold),
            ],
            [
                Paragraph(cultural_str, self.style_body),
                Paragraph(biological_str, self.style_body),
            ],
        ]

        table = Table(data, colWidths=[half_w, half_w])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def _build_chemical_table(self, chemicals: List[Dict[str, Any]], width: float) -> Table:
        headers = [
            Paragraph("Active Ingredient", self.style_th),
            Paragraph("Trade Formulation", self.style_th),
            Paragraph("Dosage", self.style_th),
            Paragraph("Dilution", self.style_th),
            Paragraph("PHI", self.style_th),
            Paragraph("PPE", self.style_th),
        ]
        rows = [headers]

        # Width distribution: Total = width (523 pt)
        col_w = [width * 0.22, width * 0.20, width * 0.16, width * 0.14, width * 0.08, width * 0.20]

        for chem in chemicals:
            c_name = chem.get("chemical_name", "")
            c_trade = chem.get("trade_examples", "")
            c_dose = chem.get("dosage", "")
            c_dil = chem.get("dilution_rate", "")
            c_phi = f"{chem.get('phi_days', 0)} days"
            ppe_dict = chem.get("ppe_guidelines", {})
            c_ppe = ppe_dict.get("en", "Gloves, mask, goggles required.")
            # truncate ppe for table readability
            if len(c_ppe) > 65:
                c_ppe = c_ppe[:62] + "..."

            rows.append(
                [
                    Paragraph(f"<b>{c_name}</b>", self.style_td),
                    Paragraph(c_trade, self.style_td),
                    Paragraph(c_dose, self.style_td),
                    Paragraph(c_dil, self.style_td),
                    Paragraph(c_phi, self.style_td),
                    Paragraph(c_ppe, self.style_td),
                ]
            )

        table = Table(rows, colWidths=col_w)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#065F46")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def _build_suppression_alert(self, reason: str, width: float) -> Table:
        p = Paragraph(
            f"<b>Notice on Chemical Interventions:</b> {reason} "
            f"Per ICAR/CIBRC protocol, synthetic chemical spraying is restricted until verified by an agronomist.",
            self.style_body,
        )
        table = Table([[p]], colWidths=[width])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F59E0B")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_disclaimer_block(self, adv: Dict[str, Any], width: float) -> KeepTogether:
        disclaimer_dict = adv.get("statutory_disclaimer", {})
        statutory_text = disclaimer_dict.get(
            "en",
            "Statutory Notice: Prescriptions and dosages are compiled from published package of practices "
            "by ICAR and Central Insecticide Board & Registration Committee (CIBRC), Govt. of India. "
            "Under the Insecticides Act, 1968, always read container label instructions before procurement and application.",
        )
        expert_dict = adv.get("expert_consultation_notice", {})
        expert_text = expert_dict.get(
            "en",
            "Agricultural Expert Verification Mandatory: Consult your local Taluka Agricultural Officer, "
            "Krishi Vigyan Kendra (KVK) agronomist, or Gram Krishi Sahayak before purchasing and spraying scheduled chemicals.",
        )

        elements = [
            Paragraph("<b>Statutory Regulatory Compliance & Verification Notice:</b>", self.style_body_bold),
            Paragraph(statutory_text, self.style_disclaimer),
            Spacer(1, 4),
            Paragraph(f"<b>Expert Verification:</b> {expert_text}", self.style_disclaimer),
            Spacer(1, 8),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1")),
            Spacer(1, 4),
        ]

        # Official Signoff line
        col_w = width / 2.0
        signoff_data = [
            [
                Paragraph("<b>Authorized Verification Seal:</b><br/>PikVaidya AI Diagnostic System", self.style_disclaimer),
                Paragraph("<b>Krishi Sahayak / Extension Officer Signature:</b><br/>____________________________", self.style_disclaimer),
            ]
        ]
        sign_table = Table(signoff_data, colWidths=[col_w, col_w])
        sign_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elements.append(sign_table)

        return KeepTogether(elements)


# Global singleton instance
report_service = FieldAdvisoryReportService()


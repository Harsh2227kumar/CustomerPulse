import asyncio
import html
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.exports.repositories.export_repository import ExportRepository
from app.exports.schemas.export_schemas import ComplaintPDFExportQuery

logger = logging.getLogger(__name__)


class PDFExportService:
    HEADER_COLOR = colors.HexColor("#1B2A4A")
    ALT_ROW_COLOR = colors.HexColor("#F5F5F5")

    def __init__(self, repository: ExportRepository | None = None) -> None:
        self.repository = repository or ExportRepository()
        self.styles = self._build_styles()

    async def build_complaints_report_pdf(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> bytes:
        logger.info("Generating complaint PDF export.")
        generated_at = datetime.now(UTC)
        report_data = {
            "summary": await self.repository.get_pdf_summary(db, filters),
            "sentiment_distribution": await self.repository.get_sentiment_distribution(db, filters),
            "top_products": await self.repository.get_top_products(db, filters),
            "top_channels": await self.repository.get_top_channels(db, filters),
            "urgency_distribution": await self.repository.get_urgency_distribution(db, filters),
            "churn_risk_summary": await self.repository.get_churn_risk_summary(db, filters),
        }
        return await asyncio.to_thread(self._render_pdf, report_data, filters, generated_at)

    def _render_pdf(
        self,
        report_data: dict[str, Any],
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> bytes:
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )
        story = self._build_story(report_data, filters, generated_at)
        document.build(
            story,
            onFirstPage=lambda canvas, doc: self._draw_footer(canvas, doc, generated_at),
            onLaterPages=lambda canvas, doc: self._draw_footer(canvas, doc, generated_at),
        )
        return buffer.getvalue()

    def _build_story(
        self,
        report_data: dict[str, Any],
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> list[Any]:
        story: list[Any] = []
        story.extend(self._build_cover_page(filters, generated_at))
        story.append(PageBreak())
        story.extend(self._build_executive_summary(report_data["summary"]))
        story.extend(self._build_sentiment_distribution(report_data["sentiment_distribution"]))
        story.extend(self._build_top_products(report_data["top_products"]))
        story.extend(self._build_top_channels(report_data["top_channels"]))
        story.extend(self._build_urgency_distribution(report_data["urgency_distribution"]))
        story.extend(self._build_churn_risk_summary(report_data["churn_risk_summary"]))
        return story

    async def build_regulatory_report_pdf(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> bytes:
        logger.info("Generating regulatory PDF export.")
        generated_at = datetime.now(UTC)
        report_data = {
            "summary": await self.repository.get_regulatory_summary(db, filters),
            "sentiment_distribution": await self.repository.get_sentiment_distribution(db, filters),
            "urgency_distribution": await self.repository.get_urgency_distribution(db, filters),
            "complaints_list": await self.repository.get_regulatory_complaints_list(db, filters),
        }
        return await asyncio.to_thread(self._render_regulatory_pdf, report_data, filters, generated_at)

    def _render_regulatory_pdf(
        self,
        report_data: dict[str, Any],
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> bytes:
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )
        story = self._build_regulatory_story(report_data, filters, generated_at)
        document.build(
            story,
            onFirstPage=lambda canvas, doc: self._draw_footer(canvas, doc, generated_at),
            onLaterPages=lambda canvas, doc: self._draw_footer(canvas, doc, generated_at),
        )
        return buffer.getvalue()

    def _build_regulatory_story(
        self,
        report_data: dict[str, Any],
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> list[Any]:
        story: list[Any] = []
        story.extend(self._build_regulatory_cover_page(filters, generated_at))
        story.append(PageBreak())
        story.extend(self._build_regulatory_summary(report_data["summary"]))
        story.extend(self._build_sentiment_distribution(report_data["sentiment_distribution"]))
        story.extend(self._build_urgency_distribution(report_data["urgency_distribution"]))
        story.append(PageBreak())
        story.extend(self._build_regulatory_log(report_data["complaints_list"]))
        return story

    def _build_regulatory_cover_page(
        self,
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> list[Any]:
        return [
            Spacer(1, 50),
            Paragraph("CustomerPulse AI — Banking Compliance Audit Report", self.styles["cover_title"]),
            Spacer(1, 18),
            Paragraph(
                f"Generated: {self._format_datetime(generated_at)}",
                self.styles["cover_meta"],
            ),
            Spacer(1, 8),
            Paragraph(
                f"Audit period: {self._format_report_period(filters)}",
                self.styles["cover_meta"],
            ),
            Spacer(1, 8),
            Paragraph(
                "Classification: CONFIDENTIAL / FOR REGULATORY AUDIT",
                self.styles["cover_meta"],
            ),
            Spacer(1, 18),
            Paragraph(
                "This report aggregates ML annotations, SLA breach risks, human review outcomes, and timeline escalation logs in compliance with regulatory reporting mandates.",
                self.styles["cover_meta"],
            ),
        ]

    def _build_regulatory_summary(self, summary: dict[str, Any]) -> list[Any]:
        rows = [
            ["Regulatory Audit Metric", "Value / Volume"],
            ["Total Complaints Intake", self._format_integer(summary.get("total_complaints"))],
            ["AI-Processed (Completed) Count", self._format_integer(summary.get("completed_count"))],
            ["Human Reviewed Count", self._format_integer(summary.get("reviewed_count"))],
            ["Escalated Count", self._format_integer(summary.get("escalated_count"))],
            ["Average Urgency Score", self._format_number(summary.get("avg_urgency_score"))],
            ["Timely Response Rate %", self._format_percent(summary.get("timely_response_pct"))],
        ]
        return self._section("Audit Executive Summary", rows, (220, 100))

    def _build_regulatory_log(self, complaints: list[dict[str, Any]]) -> list[Any]:
        cell_style = ParagraphStyle(
            "cell_style",
            parent=self.styles.get("cover_meta"),
            fontSize=7,
            leading=9
        )

        rows = [["ID", "Product", "Timely", "Urgency", "Review Reason", "Reviewer / Notes", "Resolution"]]
        for item in complaints:
            comp_id = self._safe_text(item.get("complaint_id"))
            comp_id_disp = comp_id[:8] + "..." if comp_id else "N/A"
            prod = Paragraph(self._escape(self._safe_text(item.get("product"))), cell_style)
            timely = "Yes" if item.get("timely_response") else "No"
            urgency = self._format_integer(item.get("urgency_score"))
            reason = Paragraph(self._escape(self._safe_text(item.get("human_review_reason") or "None")), cell_style)

            reviewer = self._safe_text(item.get("reviewer"))
            notes = self._safe_text(item.get("review_notes"))
            reviewer_notes = f"{reviewer}: {notes}" if reviewer and notes else (reviewer or notes or "N/A")
            rev_notes_p = Paragraph(self._escape(reviewer_notes), cell_style)

            resolution = Paragraph(self._escape(self._safe_text(item.get("review_resolution") or "Pending")), cell_style)

            rows.append([comp_id_disp, prod, timely, urgency, reason, rev_notes_p, resolution])

        if len(rows) == 1:
            rows.append(["No records found", "", "", "", "", "", ""])

        return self._section("Compliance Review & Escalation Log (Top 50)", rows, (50, 80, 40, 40, 80, 150, 60))


    def _build_cover_page(
        self,
        filters: ComplaintPDFExportQuery,
        generated_at: datetime,
    ) -> list[Any]:
        return [
            Spacer(1, 50),
            Paragraph("CustomerPulse AI — Executive Complaint Report", self.styles["cover_title"]),
            Spacer(1, 18),
            Paragraph(
                f"Generated: {self._format_datetime(generated_at)}",
                self.styles["cover_meta"],
            ),
            Spacer(1, 8),
            Paragraph(
                f"Report period: {self._format_report_period(filters)}",
                self.styles["cover_meta"],
            ),
            Spacer(1, 8),
            Paragraph(
                "Powered by CustomerPulse AI export reporting.",
                self.styles["cover_tagline"],
            ),
        ]

    def _build_executive_summary(self, summary: dict[str, Any]) -> list[Any]:
        rows = [
            ["Metric", "Value"],
            ["Total complaints", self._format_integer(summary.get("total_complaints"))],
            ["Completed count", self._format_integer(summary.get("completed_count"))],
            ["Pending count", self._format_integer(summary.get("pending_count"))],
            ["Failed count", self._format_integer(summary.get("failed_count"))],
            ["Avg urgency score", self._format_number(summary.get("avg_urgency_score"))],
            ["Timely response %", self._format_percent(summary.get("timely_response_pct"))],
            ["High churn risk count", self._format_integer(summary.get("high_churn_risk_count"))],
        ]
        return self._section("Executive Summary", rows, (170, 120))

    def _build_sentiment_distribution(self, items: list[dict[str, Any]]) -> list[Any]:
        rows = [["Sentiment", "Count", "Percentage"]]
        for item in items:
            rows.append(
                [
                    item["sentiment"],
                    self._format_integer(item["count"]),
                    self._format_percent(item["percentage"]),
                ]
            )
        return self._section("Sentiment Distribution", rows, (120, 80, 100))

    def _build_top_products(self, items: list[dict[str, Any]]) -> list[Any]:
        rows = [["Product", "Count", "Timely rate %", "Avg urgency"]]
        for item in items:
            product_text = self._escape(self._safe_text(item.get("product")))
            product_p = Paragraph(product_text, self.styles["table_cell"])
            rows.append(
                [
                    product_p,
                    self._format_integer(item.get("count")),
                    self._format_percent(item.get("timely_rate_pct")),
                    self._format_number(item.get("avg_urgency")),
                ]
            )
        if len(rows) == 1:
            rows.append(["", "0", "0.00%", "0.00"])
        return self._section("Top 10 Products by Volume", rows, (180, 60, 90, 80))

    def _build_top_channels(self, items: list[dict[str, Any]]) -> list[Any]:
        rows = [["Channel", "Count", "Timely rate %"]]
        for item in items:
            channel_text = self._escape(self._safe_text(item.get("channel")))
            channel_p = Paragraph(channel_text, self.styles["table_cell"])
            rows.append(
                [
                    channel_p,
                    self._format_integer(item.get("count")),
                    self._format_percent(item.get("timely_rate_pct")),
                ]
            )
        if len(rows) == 1:
            rows.append(["", "0", "0.00%"])
        return self._section("Top 5 Channels", rows, (180, 70, 100))

    def _build_urgency_distribution(self, items: list[dict[str, Any]]) -> list[Any]:
        labels = {
            "Low": "0-25 (Low)",
            "Medium": "26-50 (Medium)",
            "High": "51-75 (High)",
            "Critical": "76-100 (Critical)",
        }
        rows = [["Bucket", "Count"]]
        for item in items:
            rows.append([labels[item["bucket"]], self._format_integer(item["count"])])
        return self._section("Urgency Distribution", rows, (210, 90))

    def _build_churn_risk_summary(self, items: list[dict[str, Any]]) -> list[Any]:
        rows = [["Churn Risk", "Count"]]
        for item in items:
            rows.append([item["churn_risk"], self._format_integer(item["count"])])
        return self._section("Churn Risk Summary", rows, (180, 80))

    def _section(
        self,
        title: str,
        rows: list[list[str]],
        col_widths: tuple[int, ...],
    ) -> list[Any]:
        return [
            Spacer(1, 12),
            Paragraph(title, self.styles["section_title"]),
            Spacer(1, 8),
            self._build_table(rows, col_widths),
        ]

    def _build_table(self, rows: list[list[str]], col_widths: tuple[int, ...]) -> Table:
        table = Table(rows, colWidths=list(col_widths), repeatRows=1)
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), self.HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7DCE5")),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
        ]
        for index in range(1, len(rows)):
            if index % 2 == 0:
                style_commands.append(("BACKGROUND", (0, index), (-1, index), self.ALT_ROW_COLOR))
        table.setStyle(TableStyle(style_commands))
        return table

    def _draw_footer(self, canvas, doc, generated_at: datetime) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        footer_text = (
            f"Page {canvas.getPageNumber()}    "
            f"CONFIDENTIAL — CustomerPulse AI    "
            f"{self._format_datetime(generated_at)}"
        )
        canvas.setFillColor(colors.HexColor("#4A5568"))
        canvas.drawString(doc.leftMargin, 12 * mm, footer_text)
        canvas.restoreState()

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        base_styles = getSampleStyleSheet()
        return {
            "cover_title": ParagraphStyle(
                "cover_title",
                parent=base_styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=22,
                leading=28,
                textColor=self.HEADER_COLOR,
                spaceAfter=12,
            ),
            "cover_meta": ParagraphStyle(
                "cover_meta",
                parent=base_styles["BodyText"],
                fontName="Helvetica",
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#334155"),
            ),
            "cover_tagline": ParagraphStyle(
                "cover_tagline",
                parent=base_styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#0F172A"),
            ),
            "section_title": ParagraphStyle(
                "section_title",
                parent=base_styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=18,
                textColor=self.HEADER_COLOR,
            ),
            "table_cell": ParagraphStyle(
                "table_cell",
                parent=base_styles["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#334155"),
            ),
        }

    def _escape(self, text: str) -> str:
        return html.escape(text)

    def _format_report_period(self, filters: ComplaintPDFExportQuery) -> str:
        start = self._format_datetime(filters.date_from) if filters.date_from else "Beginning"
        end = self._format_datetime(filters.date_to) if filters.date_to else "Present"
        return f"{start} to {end}"

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return ""
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _format_integer(self, value: Any) -> str:
        if value is None:
            return "0"
        return str(int(value))

    def _format_number(self, value: Any) -> str:
        if value is None:
            return "0.00"
        if isinstance(value, Decimal):
            value = float(value)
        return f"{float(value):.2f}"

    def _format_percent(self, value: Any) -> str:
        return f"{self._format_number(value)}%"

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)


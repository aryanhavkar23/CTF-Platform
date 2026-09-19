"""
Professional PDF Generator for BACKEND_FEATURES.md
Converts the authoritative CTF Platform technical specification into a publication-grade PDF.
"""

import os
import sys
import re
import html
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Flowable,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# Register TrueType fonts from Windows Fonts for superior typography and unicode support
has_custom_fonts = False
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    win_fonts = r"C:\Windows\Fonts"
    if os.path.exists(os.path.join(win_fonts, "segoeui.ttf")):
        pdfmetrics.registerFont(TTFont("SegoeUI", os.path.join(win_fonts, "segoeui.ttf")))
        pdfmetrics.registerFont(TTFont("SegoeUI-Bold", os.path.join(win_fonts, "segoeuib.ttf")))
        pdfmetrics.registerFont(TTFont("SegoeUI-Italic", os.path.join(win_fonts, "segoeuii.ttf")))
        pdfmetrics.registerFont(TTFont("Consolas", os.path.join(win_fonts, "consola.ttf")))
        pdfmetrics.registerFont(TTFont("Consolas-Bold", os.path.join(win_fonts, "consolab.ttf")))
        has_custom_fonts = True
except Exception:
    has_custom_fonts = False

FONT_BODY = "SegoeUI" if has_custom_fonts else "Helvetica"
FONT_BOLD = "SegoeUI-Bold" if has_custom_fonts else "Helvetica-Bold"
FONT_ITALIC = "SegoeUI-Italic" if has_custom_fonts else "Helvetica-Oblique"
FONT_CODE = "Consolas" if has_custom_fonts else "Courier"
FONT_CODE_BOLD = "Consolas-Bold" if has_custom_fonts else "Courier-Bold"


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count
    along with running headers and footers on all content pages.
    """
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
        # Suppress running header and footer on cover page (Page 1)
        if self._pageNumber > 1:
            self.saveState()
            self.setFont(FONT_BOLD, 7.5)
            self.setFillColor(colors.HexColor("#0f172a"))

            # Running Header
            self.drawString(36, letter[1] - 28, "OWASP CTF PLATFORM")
            self.setFont(FONT_BODY, 7.5)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(140, letter[1] - 28, "—  Backend Feature & API Specification (Phases 1–17)")
            self.drawRightString(letter[0] - 36, letter[1] - 28, "STITCH & UI SPECIFICATION")

            # Header dividing line
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(36, letter[1] - 32, letter[0] - 36, letter[1] - 32)

            # Footer dividing line
            self.line(36, 36, letter[0] - 36, 36)

            # Running Footer
            self.setFont(FONT_BODY, 7.5)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(36, 24, "CONFIDENTIAL — COLLEGE OWASP CLUB & DEVELOPER REFERENCE")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(letter[0] - 36, 24, page_text)

            self.restoreState()


class BookmarkHook(Flowable):
    """Inserts a PDF bookmark into the document outline hierarchy."""
    def __init__(self, key, title, level=0):
        super().__init__()
        self.key = key
        self.title = title
        self.level = level

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=(self.level > 0))


def clean_markdown_inline(text: str) -> str:
    """Safely converts markdown inline formatting into ReportLab HTML-compatible tags."""
    # Replace math/unicode syntax
    text = text.replace(r"\rightarrow", "→")
    text = text.replace(r"\text{px}", "px")
    text = text.replace(r"$< 15$", "&lt; 15")
    text = text.replace(r"$1440\text{px}$", "1440px")
    text = text.replace(r"$1024\text{px}$", "1024px")
    text = text.replace(r"$768\text{px}$", "768px")
    text = text.replace(r"$375\text{px}$", "375px")
    text = text.replace("$", "")

    # Tokenize backticks
    tokens = re.split(r"(`[^`]+`)", text)
    result = []
    for token in tokens:
        if token.startswith("`") and token.endswith("`") and len(token) >= 2:
            code_str = html.escape(token[1:-1])
            result.append(f'<font name="{FONT_CODE}" size="7" color="#0369a1"><b>{code_str}</b></font>')
        else:
            t = html.escape(token)
            # Bold **text**
            t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
            # Italic *text*
            t = re.sub(r"\*([^*]+?)\*", r"<i>\1</i>", t)
            result.append(t)
    return "".join(result)


def format_code_line(line: str, max_len: int = 95) -> list:
    """Soft-wraps code lines if they exceed max_len, preserving indentation."""
    if not line.strip():
        return ["&nbsp;"]

    # Calculate leading indentation
    leading_spaces = len(line) - len(line.lstrip(" "))
    indent_prefix = "&nbsp;" * leading_spaces
    content = line.lstrip(" ")

    def preserve_spaces(s):
        esc = html.escape(s)
        return esc.replace("  ", "&nbsp;&nbsp;")

    wrapped = []
    while len(content) > max_len:
        chunk = content[:max_len]
        wrapped.append(indent_prefix + preserve_spaces(chunk))
        content = content[max_len:]
        indent_prefix = indent_prefix + "&nbsp;&nbsp;&nbsp;&nbsp;"
    wrapped.append(indent_prefix + preserve_spaces(content))
    return wrapped


def get_table_col_widths(raw_headers: list, total_width: float = 540.0) -> list:
    """Calculates proportional column widths tailored to specific table layouts."""
    num_cols = len(raw_headers)
    hdr_str = " ".join(raw_headers).lower()

    if num_cols == 7:
        # Section 2 Database Models: Model Class, Database Table, Purpose, Key Fields, Relationships, Constraints, Frontend Mapping
        return [62.0, 68.0, 70.0, 85.0, 80.0, 80.0, 95.0]
    elif num_cols == 5:
        # API Endpoints: Method, Endpoint, Auth, Role, Description
        return [42.0, 148.0, 65.0, 65.0, 220.0]
    elif num_cols == 4:
        if "phase" in hdr_str:
            # Phase, Functional Area, Architecture / Service, Status
            return [75.0, 115.0, 210.0, 140.0]
        else:
            # Platform Feature, Student, Moderator, Admin
            return [210.0, 110.0, 110.0, 110.0]
    elif num_cols == 3:
        if "page" in hdr_str or "modal" in hdr_str:
            # Frontend Page / Modal, Backend API Endpoints Consumed, Main Data & Visual Elements
            return [110.0, 160.0, 270.0]
        else:
            # UI State, Backend Condition, Required Visual Representation
            return [115.0, 160.0, 265.0]
    else:
        w = total_width / num_cols
        return [w] * num_cols


def build_pdf(md_file_path: str, pdf_file_path: str):
    """Parses BACKEND_FEATURES.md and compiles the professional PDF."""
    with open(md_file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    doc = SimpleDocTemplate(
        pdf_file_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=42,
    )

    # Styles
    styles = getSampleStyleSheet()

    # Custom typography styles
    style_cover_brand = ParagraphStyle(
        "CoverBrand",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0284c7"),
        alignment=TA_LEFT,
        spaceAfter=15,
    )
    style_cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    style_cover_subtitle = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#475569"),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    style_cover_tagline = ParagraphStyle(
        "CoverTagline",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#7c3aed"),
        alignment=TA_LEFT,
        spaceAfter=25,
    )

    style_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=13.5,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=5,
        keepWithNext=True,
    )
    style_h2 = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    style_h3 = ParagraphStyle(
        "SectionH3",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )
    style_body = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )
    style_bullet = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )
    style_code_block = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName=FONT_CODE,
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#e2e8f0"),
    )
    style_callout = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    style_th = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    style_td = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_LEFT,
    )
    style_toc_item = ParagraphStyle(
        "TOCItem",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
    )

    story = []

    # =========================================================================
    # 1. Professional Cover Page
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("OWASP STUDENT CHAPTER &bull; CYBERLAB PLATFORM", style_cover_brand))
    story.append(Paragraph("OWASP CTF PLATFORM", style_cover_title))
    story.append(Paragraph("Backend Feature &amp; API Specification", style_cover_subtitle))
    story.append(Paragraph("Frontend Design &amp; Development Reference", style_cover_tagline))

    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284c7"), spaceBefore=5, spaceAfter=20))

    cover_meta = [
        [
            Paragraph("<b>DOCUMENT CLASSIFICATION:</b>", style_td),
            Paragraph("Engineering Specification &amp; UI Architecture Reference", style_td),
        ],
        [
            Paragraph("<b>TARGET INTERFACE SYSTEM:</b>", style_td),
            Paragraph("Google Stitch / Modern CTF Frontend UI", style_td),
        ],
        [
            Paragraph("<b>IMPLEMENTATION SCOPE:</b>", style_td),
            Paragraph("Phases 1–17 Complete (233/233 Automated Tests Passing)", style_td),
        ],
        [
            Paragraph("<b>BACKEND ARCHITECTURE:</b>", style_td),
            Paragraph("FastAPI, SQLAlchemy 2.0, PostgreSQL (Supabase), Docker Engine", style_td),
        ],
        [
            Paragraph("<b>AUTHOR &amp; GOVERNANCE:</b>", style_td),
            Paragraph("College OWASP Student Chapter Core Development Team", style_td),
        ],
        [
            Paragraph("<b>PUBLICATION DATE:</b>", style_td),
            Paragraph("September 2026 &bull; Version 1.0 Production Release", style_td),
        ],
    ]
    meta_table = Table(cover_meta, colWidths=[160, 380])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(meta_table)

    story.append(Spacer(1, 30))

    callout_cover = [
        [
            Paragraph(
                "<b>PRIMARY DIRECTIVE FOR GOOGLE STITCH &amp; UI ENGINEERS:</b><br/>"
                "This document is derived directly from the live, fully implemented backend codebase. "
                "All endpoints, database fields, roles, constraints, scoring rules, and data structures "
                "are production-authoritative. The frontend must consume existing FastAPI endpoints without "
                "duplicating scoring calculations or inventing unauthorized interfaces.",
                style_callout
            )
        ]
    ]
    cover_callout_table = Table(callout_cover, colWidths=[540])
    cover_callout_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
            ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#0284c7")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ])
    )
    story.append(cover_callout_table)

    story.append(PageBreak())

    # =========================================================================
    # 2. Clickable Table of Contents (Page 2)
    # =========================================================================
    story.append(BookmarkHook("toc", "Table of Contents", 0))
    story.append(Paragraph("TABLE OF CONTENTS", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284c7"), spaceBefore=2, spaceAfter=10))

    toc_sections = [
        ("1", "Backend Project Structure", "sec-1"),
        ("2", "Database Model Overview", "sec-2"),
        ("3", "Authentication & Authorization", "sec-3"),
        ("4", "API Endpoint Reference", "sec-4"),
        ("5", "Challenge System", "sec-5"),
        ("6", "Scoring System", "sec-6"),
        ("7", "Leaderboards", "sec-7"),
        ("8", "Teams", "sec-8"),
        ("9", "Events & Tournaments", "sec-9"),
        ("10", "Profiles & Activity", "sec-10"),
        ("11", "Badges & Achievements", "sec-11"),
        ("12", "Discussions & Forum", "sec-12"),
        ("13", "Notifications", "sec-13"),
        ("14", "Admin Analytics", "sec-14"),
        ("15", "Security & Anti-Cheat", "sec-15"),
        ("16", "Live Challenge System", "sec-16"),
        ("17", "Security & Deployment", "sec-17"),
        ("18", "Required Frontend Pages", "sec-18"),
        ("19", "Frontend Page → Backend API Mapping", "sec-19"),
        ("20", "Reusable Frontend Components", "sec-20"),
        ("21", "Important User Flows", "sec-21"),
        ("22", "Required UI States", "sec-22"),
        ("23", "Role Permission Matrix", "sec-23"),
        ("24", "Stitch Frontend Design Context", "sec-24"),
        ("25", "Backend Implementation Status", "sec-25"),
    ]

    toc_rows = []
    # Split TOC into 2 columns for neat layout
    mid = (len(toc_sections) + 1) // 2
    col1 = toc_sections[:mid]
    col2 = toc_sections[mid:]

    for i in range(mid):
        item1 = col1[i]
        c1 = Paragraph(f'<a href="#{item1[2]}"><b>{item1[0]}.</b> {item1[1]}</a>', style_toc_item)
        if i < len(col2):
            item2 = col2[i]
            c2 = Paragraph(f'<a href="#{item2[2]}"><b>{item2[0]}.</b> {item2[1]}</a>', style_toc_item)
        else:
            c2 = Paragraph("", style_toc_item)
        toc_rows.append([c1, c2])

    toc_table = Table(toc_rows, colWidths=[270, 270])
    toc_table.setStyle(
        TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(toc_table)
    story.append(Spacer(1, 15))
    story.append(PageBreak())

    # =========================================================================
    # 3. Document Content Parser
    # =========================================================================
    lines = md_content.split("\n")
    i = 0
    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []

    # Map major section numbering to anchors
    section_counter = 0

    while i < len(lines):
        line = lines[i].rstrip("\r\n")

        # Handle fenced code block
        if line.strip().startswith("```"):
            if in_code_block:
                # End of code block
                in_code_block = False
                code_rows = []
                for cl in code_lines:
                    formatted_parts = format_code_line(cl, max_len=95)
                    for fp in formatted_parts:
                        code_rows.append([Paragraph(fp, style_code_block)])

                if code_rows:
                    code_table = Table(code_rows, colWidths=[540])
                    code_table.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#1e293b")),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ])
                    )
                    story.append(Spacer(1, 3))
                    story.append(code_table)
                    story.append(Spacer(1, 5))
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Markdown Tables
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            table_lines.append(line.strip())
            # Lookahead: is next line also a table line?
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("|") and "|" in lines[i + 1].strip()[1:]:
                i += 1
                continue
            else:
                # Compile table
                raw_rows = []
                for tl in table_lines:
                    # Skip markdown separator row |---|---|
                    if re.match(r"^\|[\s\-\:\.\\]+\|$", tl.replace(" ", "").replace("|", "| |")):
                        continue
                    parts = [c.strip() for c in tl.split("|")[1:-1]]
                    if parts and not all(p == "" or set(p).issubset({"-", ":"}) for p in parts):
                        raw_rows.append(parts)

                if raw_rows:
                    num_cols = len(raw_rows[0])
                    col_widths = get_table_col_widths(raw_rows[0])

                    formatted_table_data = []
                    for r_idx, row in enumerate(raw_rows):
                        # Pad row if incomplete
                        while len(row) < num_cols:
                            row.append("")
                        row = row[:num_cols]

                        row_cells = []
                        is_header = (r_idx == 0)
                        for cell_text in row:
                            cell_text_clean = cell_text.replace("<br>", " ").replace("<br/>", " ")
                            cell_html = clean_markdown_inline(cell_text_clean)
                            if is_header:
                                row_cells.append(Paragraph(f"<b>{cell_html}</b>", style_th))
                            else:
                                row_cells.append(Paragraph(cell_html, style_td))
                        formatted_table_data.append(row_cells)

                    t = Table(formatted_table_data, colWidths=col_widths, repeatRows=1)
                    t_style = [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                    # Alternating zebra rows
                    for row_num in range(1, len(formatted_table_data)):
                        if row_num % 2 == 0:
                            t_style.append(("BACKGROUND", (0, row_num), (-1, row_num), colors.HexColor("#f8fafc")))
                        else:
                            t_style.append(("BACKGROUND", (0, row_num), (-1, row_num), colors.white))

                    t.setStyle(TableStyle(t_style))
                    story.append(Spacer(1, 4))
                    story.append(t)
                    story.append(Spacer(1, 6))

                table_lines = []
                i += 1
                continue

        # Blank lines
        if not line.strip():
            i += 1
            continue

        # Horizontal Rule
        if line.strip() in ("---", "___", "***"):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#e2e8f0"), spaceBefore=4, spaceAfter=8))
            i += 1
            continue

        # Callouts (> [!IMPORTANT], > ...)
        if line.strip().startswith(">"):
            callout_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                raw_cl = lines[i].strip()[1:].strip()
                callout_lines.append(raw_cl)
                i += 1
            full_callout = " ".join(callout_lines)
            full_callout_clean = clean_markdown_inline(full_callout)
            callout_table = Table([[Paragraph(full_callout_clean, style_callout)]], colWidths=[540])
            callout_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("LINELEFT", (0, 0), (0, -1), 3, colors.HexColor("#0284c7")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ])
            )
            story.append(Spacer(1, 3))
            story.append(callout_table)
            story.append(Spacer(1, 5))
            continue

        # Major Section Headings (## X. Title)
        if line.startswith("## "):
            h_text = line[3:].strip()
            m = re.match(r"^(\d+)\.\s*(.*)", h_text)
            if m:
                sec_num = int(m.group(1))
                anchor_key = f"sec-{sec_num}"
            else:
                section_counter += 1
                anchor_key = f"sec-{section_counter}"
            story.append(BookmarkHook(anchor_key, h_text, 0))
            story.append(Paragraph(f'<a name="{anchor_key}"/>' + clean_markdown_inline(h_text), style_h1))
            story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#0284c7"), spaceBefore=1, spaceAfter=6))
            i += 1
            continue

        # Subsections (### X.Y Title)
        if line.startswith("### "):
            h_text = line[4:].strip()
            anchor_key = f"subsec-{i}"
            story.append(BookmarkHook(anchor_key, h_text, 1))
            story.append(Paragraph(f'<a name="{anchor_key}"/>' + clean_markdown_inline(h_text), style_h2))
            i += 1
            continue

        # Sub-subsections (#### Title)
        if line.startswith("#### "):
            h_text = line[5:].strip()
            story.append(Paragraph(clean_markdown_inline(h_text), style_h3))
            i += 1
            continue

        # Document Root Title (# Title)
        if line.startswith("# "):
            # Handled by cover page, skip repeating
            i += 1
            continue

        # Bullet Lists
        if re.match(r"^(\*|-)\s+", line.strip()):
            bullet_text = re.sub(r"^(\*|-)\s+", "", line.strip())
            story.append(Paragraph(f"&bull;&nbsp; {clean_markdown_inline(bullet_text)}", style_bullet))
            i += 1
            continue

        # Numbered Lists
        if re.match(r"^\d+\.\s+", line.strip()):
            num_match = re.match(r"^(\d+\.)\s+(.*)", line.strip())
            if num_match:
                prefix = num_match.group(1)
                text_part = num_match.group(2)
                story.append(Paragraph(f"<b>{prefix}</b>&nbsp; {clean_markdown_inline(text_part)}", style_bullet))
            i += 1
            continue

        # Standard Body Paragraph
        p_html = clean_markdown_inline(line.strip())
        story.append(Paragraph(p_html, style_body))
        i += 1

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[*] PDF Build Complete: {pdf_file_path}")


if __name__ == "__main__":
    src = os.path.abspath("BACKEND_FEATURES.md")
    dest = os.path.abspath("BACKEND_FEATURES.pdf")
    build_pdf(src, dest)

import os
import re
import fitz  # PyMuPDF — for extraction/summarization
from datetime import datetime
from pathlib import Path

# ── ReportLab Platypus imports for PDF creation ──
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# ── Color scheme ──
PRIMARY = colors.HexColor('#00FFCC')  # NOVA Cyan
ACCENT = PRIMARY
BACKGROUND = colors.HexColor('#0a1111')
TEXT = colors.HexColor('#E2E8F0')
MUTED = colors.HexColor('#8892b0')
LIGHT = colors.HexColor('#112222')
WHITE = colors.white

# ── Documents output directory ──
DOCS_DIR = Path(__file__).resolve().parent.parent / "documents"
DOCS_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════════════
#  CUSTOM STYLES
# ════════════════════════════════════════════════════════════

def _build_styles():
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'NovaTitle',
        parent=base['Title'],
        fontSize=28,
        textColor=PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
        leading=34,
        fontName='Courier-Bold',
    )

    subtitle_style = ParagraphStyle(
        'NovaSubtitle',
        parent=base['Normal'],
        fontSize=14,
        textColor=TEXT,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
        leading=18,
        fontName='Courier',
    )

    heading_style = ParagraphStyle(
        'NovaHeading',
        parent=base['Heading1'],
        fontSize=16,
        textColor=PRIMARY,
        fontName='Courier-Bold',
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
        leading=20,
    )

    body_style = ParagraphStyle(
        'NovaBody',
        parent=base['Normal'],
        fontSize=11,
        textColor=TEXT,
        alignment=TA_JUSTIFY,
        leading=16,
        spaceAfter=3 * mm,
        fontName='Courier',
    )

    bullet_style = ParagraphStyle(
        'NovaBullet',
        parent=base['Normal'],
        fontSize=11,
        textColor=TEXT,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=2 * mm,
        leading=15,
        fontName='Courier',
    )

    toc_style = ParagraphStyle(
        'NovaTOC',
        parent=base['Normal'],
        fontSize=12,
        textColor=TEXT,
        leftIndent=10,
        spaceAfter=3 * mm,
        leading=16,
        fontName='Courier',
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'heading': heading_style,
        'body': body_style,
        'bullet': bullet_style,
        'toc': toc_style,
        'base': base,
    }


# ════════════════════════════════════════════════════════════
#  HEADER / FOOTER CALLBACKS
# ════════════════════════════════════════════════════════════

def _header_footer(canvas, doc, topic: str):
    """Draw header and footer on every page."""
    canvas.saveState()
    width, height = A4

    # ── Background Fill ──
    canvas.setFillColor(BACKGROUND)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)

    # ── Header ──
    canvas.setFont('Courier', 9)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, height - 12 * mm, "N.O.V.A // SYS.DOC")
    canvas.drawRightString(width - 20 * mm, height - 12 * mm, f"[{topic.upper()}]")

    # Accent line below header
    canvas.setStrokeColor(PRIMARY)
    canvas.setLineWidth(1)
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)

    # ── Footer ──
    canvas.setFont('Courier', 9)
    canvas.setFillColor(MUTED)
    page_num = f"PAGE {doc.page}"
    canvas.drawCentredString(width / 2, 10 * mm, page_num)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    canvas.drawRightString(
        width - 20 * mm, 10 * mm,
        f"NOVA CORE // {date_str}"
    )

    canvas.restoreState()


# ════════════════════════════════════════════════════════════
#  CONTENT PARSER
# ════════════════════════════════════════════════════════════

def _parse_sections(content: str):
    """Split content into (heading, body_lines) sections."""
    sections = []
    current_heading = "Overview"
    current_body = []

    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue

        # Detect markdown headings
        if stripped.startswith('## '):
            if current_body:
                sections.append((current_heading, current_body))
            current_heading = stripped.lstrip('#').strip()
            current_body = []
        elif stripped.startswith('# '):
            if current_body:
                sections.append((current_heading, current_body))
            current_heading = stripped.lstrip('#').strip()
            current_body = []
        else:
            current_body.append(stripped)

    if current_body:
        sections.append((current_heading, current_body))

    # If no sections were detected, create one from full content
    if not sections:
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) <= 1:
            sections = [("Overview", content.split('\n'))]
        else:
            for i, para in enumerate(paragraphs):
                heading = f"Section {i + 1}"
                sections.append((heading, para.split('\n')))

    return sections


def _extract_takeaways(content: str, count: int = 5):
    """Extract key sentences from content for summary box."""
    # Heuristic: if it's heavily structured markdown, skip auto-summarization
    headers = re.findall(r'^\s*#{1,3}\s+', content, flags=re.MULTILINE)
    if len(headers) > 3:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', content)
    # Filter out very short or bullet-like fragments, OR overly long parsing failures
    good = [s.strip() for s in sentences if 20 < len(s.strip()) < 300 and not s.strip().startswith('-')]
    
    # If we couldn't find at least 2 good sentences, don't force it
    if len(good) < 2:
        return []
        
    # Take evenly spaced samples
    if len(good) <= count:
        return good
    step = max(1, len(good) // count)
    return [good[i] for i in range(0, len(good), step)][:count]


# ════════════════════════════════════════════════════════════
#  CONTENT PREPROCESSOR
# ════════════════════════════════════════════════════════════

def preprocess_content(text: str) -> list:
    """
    Convert markdown-style text into reportlab Paragraph objects.
    Returns a list of flowables.
    """
    styles = _build_styles()
    flowables = []

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            flowables.append(Spacer(1, 6))
            continue

        if line == '---' or line == '***':
            flowables.append(Spacer(1, 8 * mm))
            continue

        # Extract prefix and content
        style_key = 'body'
        prefix = ''
        content = line

        if line.startswith('#### '):
            style_key = 'heading'
            content = line[5:]
        elif line.startswith('### '):
            style_key = 'heading'
            content = line[4:]
        elif line.startswith('## '):
            style_key = 'heading'
            content = line[3:]
        elif line.startswith('# '):
            style_key = 'heading'
            content = line[2:]
        elif line.startswith('• ') or line.startswith('- ') or line.startswith('* '):
            style_key = 'bullet'
            content = line[2:].strip()
            prefix = '• '

        # Now apply inline formatting to the content only (prevents consuming bullet points as italics)
        content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
        content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', content)
        content = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', content)

        flowables.append(Paragraph(f"{prefix}{content}", styles[style_key]))

    return flowables


# ════════════════════════════════════════════════════════════
#  CREATE PDF  (main public function)
# ════════════════════════════════════════════════════════════

def create_pdf(topic: str, content: str, include_takeaways: bool = True) -> str:
    """
    Create a professional multi-page PDF using ReportLab Platypus.

    Returns: absolute file path of the generated PDF.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')[:60]
    filename = f"{safe_name}_{date_str}.pdf"
    filepath = str(DOCS_DIR / filename)

    styles = _build_styles()
    story = []

    # Bind topic into header/footer callback
    def on_page(canvas, doc):
        _header_footer(canvas, doc, topic)

    # ── PAGE 1: Cover Page ──
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph(topic, styles['title']))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("A Comprehensive Overview", styles['subtitle']))
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(
        width="60%", thickness=2, color=ACCENT,
        spaceAfter=8 * mm, spaceBefore=4 * mm,
        hAlign='CENTER'
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        styles['subtitle']
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Generated by N.O.V.A — Autonomous Productivity Operator",
        ParagraphStyle('Brand', parent=styles['base']['Normal'],
                       fontSize=10, textColor=colors.HexColor('#888888'),
                       alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    # ── PAGE 2: Table of Contents ──
    sections = _parse_sections(content)

    story.append(Paragraph("Table of Contents", styles['heading']))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(
        width="100%", thickness=1, color=ACCENT,
        spaceAfter=6 * mm
    ))
    for idx, (heading, _) in enumerate(sections, 1):
        toc_line = f"{idx}. {heading}"
        story.append(Paragraph(toc_line, styles['toc']))
    story.append(PageBreak())

    # ── PAGES 3+: Content ──
    for idx, (heading, body_lines) in enumerate(sections):
        story.append(Paragraph(heading, styles['heading']))
        story.append(Spacer(1, 4 * mm))

        # Use preprocessor for rich markdown→flowable conversion
        section_text = '\n'.join(body_lines)
        story.extend(preprocess_content(section_text))

        # Page break every 3-4 sections
        if (idx + 1) % 3 == 0 and idx < len(sections) - 1:
            story.append(PageBreak())

    # ── LAST PAGE: Key Takeaways Summary Box ──
    if include_takeaways:
        takeaways = _extract_takeaways(content)
        if takeaways:
            story.append(PageBreak())
            story.append(Paragraph("Key Takeaways", styles['heading']))
            story.append(Spacer(1, 4 * mm))

            takeaway_data = [[Paragraph(
                f"• {t}",
                ParagraphStyle('TakeawayBullet', parent=styles['base']['Normal'],
                               fontSize=10, leading=14, textColor=PRIMARY)
            )] for t in takeaways]

            summary_table = Table(takeaway_data, colWidths=[150 * mm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
                ('TEXTCOLOR', (0, 0), (-1, -1), PRIMARY),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, ACCENT),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(summary_table)

    # ── BUILD DOCUMENT ──
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=topic,
        author="N.O.V.A",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    print(f"[PDFTool] ✓ PDF created: {filepath}")
    return filepath


# ════════════════════════════════════════════════════════════
#  EXISTING FUNCTIONALITY — PDF extraction & summarization
# ════════════════════════════════════════════════════════════

class PDFTool:
    """Extracts text from PDF files and summarizes using local LLM."""

    def extract_text(self, file_path: str) -> str:
        """Read all pages of a PDF and return concatenated text."""
        if not os.path.exists(file_path):
            return None

        doc = fitz.open(file_path)
        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()
        return text.strip()

    # Maximum characters of source text to send to LLM
    MAX_INPUT_CHARS = 3000

    def summarize_text(self, text: str) -> str:
        """Two-pass summarization: extract topics, then synthesize briefing."""
        trimmed = text[:self.MAX_INPUT_CHARS]

        # Pass 1: Extract key topics from document
        print("[PDFTool] Pass 1: Extracting key topics...")
        topics = self._extract_topics(trimmed)

        # Pass 2: Synthesize topics into executive briefing
        print("[PDFTool] Pass 2: Writing executive briefing...")
        briefing = self._synthesize_briefing(topics, strict=False)
        cleaned = self._clean_summary(briefing)

        # If procedural language still detected, retry with stronger constraint
        if self._has_procedural_language(cleaned):
            print("[PDFTool] Procedural language detected, retrying...")
            briefing = self._synthesize_briefing(topics, strict=True)
            cleaned = self._clean_summary(briefing)

        # Fallback if output is too thin
        if len(cleaned.split()) < 15:
            cleaned = (
                "This document provides technical guidance covering "
                "multiple components and implementation details. "
                "Please review the original file for full content."
            )

        return cleaned

    def _extract_topics(self, text: str) -> str:
        prompt = (
            "Read the document below carefully.\n\n"
            "Answer these 3 questions in plain short sentences:\n"
            "1. What is the main purpose of this document?\n"
            "2. What are the 3 to 5 most important topics or components it covers?\n"
            "3. How do these components relate to each other?\n\n"
            "Keep your answer under 80 words. No code. No markdown.\n\n"
            f"Document:\n{text}\n\nAnswers:"
        )

        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from llm import _chat
        from core.personality import get_system_prefix
        try:
            return _chat(system=get_system_prefix(), user=prompt).strip()
        except Exception as e:
            print(f"[PDFTool] LLM Error: {e}")
            return "Failed to extract topics."

    def _synthesize_briefing(self, topics: str, strict: bool) -> str:
        if not strict:
            prompt = (
                "Using ONLY the information below, write a professional "
                "executive briefing in exactly 2 paragraphs.\n\n"
                "Paragraph 1: What is this document about and why does it matter.\n"
                "Paragraph 2: What are the key components and how they connect.\n\n"
                "Rules:\n"
                "- Maximum 150 words.\n"
                "- Write complete flowing sentences.\n"
                "- Describe the system as an integrated workflow.\n"
                "- Do NOT list steps or instructions.\n"
                "- Do NOT use bullet points, headings, or markdown.\n"
                "- Do NOT use code or technical commands.\n"
                "- Do NOT use step numbers or sequential indicators.\n"
                "- Professional tone, plain text only.\n\n"
                f"Key information:\n{topics}\n\nExecutive briefing:"
            )
        else:
            prompt = (
                "Rewrite the following information as a conceptual system overview.\n\n"
                "Absolutely no procedural language. No steps. No sequences.\n"
                "Describe WHAT the system is and WHY it matters.\n"
                "Write exactly 2 paragraphs. Maximum 120 words. Plain text only.\n\n"
                f"Information:\n{topics}\n\nSystem overview:"
            )

        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from llm import _chat
        from core.personality import get_system_prefix
        try:
            return _chat(system=get_system_prefix(), user=prompt).strip()
        except Exception as e:
            print(f"[PDFTool] LLM Error: {e}")
            return "Failed to synthesize briefing."

    def _has_procedural_language(self, text: str) -> bool:
        procedural_patterns = [
            r"\bstep\s+\d",
            r"\bfirst\b", r"\bsecond\b", r"\bthird\b",
            r"\bnext\b", r"\bthen\b", r"\bfinally\b", r"\bsubsequently\b",
            r"\bafterwards?\b", r"\bfollowed by\b",
        ]
        for pattern in procedural_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _clean_summary(self, text: str) -> str:
        # Remove fenced code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = text.replace("`", "")
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*{1,3}", "", text)
        text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r":\s*$", ".", text, flags=re.MULTILINE)
        text = re.sub(r"[^.]*\bStep\s+\d[^.]*\.\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bFirst(?:ly)?,?\s+", "The system ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bNext,?\s+", "Additionally, ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bThen,?\s+", "The workflow also ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bFinally,?\s+", "These components work together as ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bSubsequently,?\s+", "Furthermore, ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAfterwards?,?\s+", "In addition, ", text, flags=re.IGNORECASE)

        lines = text.split("\n")
        merged = []
        buffer = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                continue
            if buffer:
                buffer += " " + stripped
            else:
                buffer = stripped
        if buffer:
            merged.append(buffer)

        text = "\n\n".join(merged)
        text = re.sub(r"  +", " ", text).strip()

        words = text.split()
        if len(words) > 150:
            text = " ".join(words[:150]) + "..."

        return text

    def execute(self, action: str, parameters: dict = None) -> dict:
        """Route PDF actions."""
        parameters = parameters or {}

        if action == "summarize":
            file_path = parameters.get("file_path")
            if not file_path:
                return {"status": "error", "message": "Missing required parameter: file_path", "data": None}
            return self._summarize_pdf(file_path)

        elif action == "extract":
            file_path = parameters.get("file_path")
            if not file_path:
                return {"status": "error", "message": "Missing required parameter: file_path", "data": None}
            text = self.extract_text(file_path)
            if text is None:
                return {"status": "error", "message": f"File not found: {file_path}", "data": None}
            return {"status": "success", "message": "Text extracted successfully.", "data": text}

        elif action == "create":
            topic = parameters.get("topic", "Untitled")
            content = parameters.get("content", "")
            filepath = create_pdf(topic, content)
            return {"status": "success", "message": f"PDF created: {filepath}", "data": filepath}

        else:
            return {"status": "error", "message": f"Unknown PDF action: {action}", "data": None}

    def _summarize_pdf(self, file_path: str) -> dict:
        print(f"[PDFTool] Processing: {file_path}")
        text = self.extract_text(file_path)
        if text is None:
            return {"status": "error", "message": f"File not found: {file_path}", "data": None}
        if text == "":
            return {"status": "error", "message": "PDF contains no extractable text.", "data": None}

        print("[PDFTool] Extracting text... done.")
        print("[PDFTool] Summarizing with LLM...")
        summary = self.summarize_text(text)
        print("[PDFTool] Summarization complete.")
        return {"status": "success", "message": "PDF summarized successfully.", "data": summary}

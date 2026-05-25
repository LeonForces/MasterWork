from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "build" / "reference_gost.docx"


def set_font(style, size_pt: int, bold: bool = False) -> None:
    font = style.font
    font.name = "Times New Roman"
    font.size = Pt(size_pt)
    font.bold = bold
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "Times New Roman")
    rfonts.set(qn("w:cs"), "Times New Roman")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    normal = doc.styles["Normal"]
    set_font(normal, 14)
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    for style_name in ("Title", "Subtitle"):
        if style_name in doc.styles:
            set_font(doc.styles[style_name], 14, bold=True)
            doc.styles[style_name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[style_name]
        set_font(style, 14, bold=True)
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.space_before = Pt(18 if style_name == "Heading 1" else 12)
        style.paragraph_format.space_after = Pt(12 if style_name == "Heading 1" else 6)
        if style_name == "Heading 1":
            style.paragraph_format.page_break_before = True

    for style_name in ("Caption", "Table Caption"):
        if style_name in doc.styles:
            style = doc.styles[style_name]
            set_font(style, 14, bold=False)
            style.paragraph_format.first_line_indent = Cm(0)
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            style.paragraph_format.line_spacing = 1.0
            style.paragraph_format.space_before = Pt(12)
            style.paragraph_format.space_after = Pt(6)

    if "Table" in doc.styles:
        set_font(doc.styles["Table"], 12)

    p = doc.add_paragraph("Текст эталонного стиля")
    p.style = normal
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()

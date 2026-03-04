"""
pdf_gen.py — генерація PDF через reportlab з підтримкою кирилиці
"""
from pathlib import Path
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# ── Шрифт з кирилицею ────────────────────────────────────────────────────────
# Порядок пошуку: поруч зі скриптом → системні шляхи
_FONT_CANDIDATES = [
    Path(__file__).parent.parent / "FreeSans.ttf",
    Path(__file__).parent.parent / "DejaVuSans.ttf",
    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

_FONT_NAME = "CyrFont"
_font_registered = False


def _ensure_font():
    global _font_registered, _FONT_NAME
    if _font_registered:
        return
    for path in _FONT_CANDIDATES:
        if path.exists():
            pdfmetrics.registerFont(TTFont(_FONT_NAME, str(path)))
            _font_registered = True
            return
    # Fallback: Helvetica (без кирилиці — краще ніж crash)
    _FONT_NAME = "Helvetica"
    _font_registered = True
    print("[PDF] ⚠ TTF-шрифт з кирилицею не знайдено. Використовується Helvetica.")


# ── Назви документів ──────────────────────────────────────────────────────────
DOC_TITLES = {
    "аналізи":        "НАПРАВЛЕННЯ НА АНАЛІЗИ",
    "влк":            "НАПРАВЛЕННЯ НА ВЛК",
    "стаціонар":      "НАПРАВЛЕННЯ НА СТАЦІОНАР",
    "характеристика": "МЕДИЧНА ХАРАКТЕРИСТИКА",
    "рапорт":         "РАПОРТ",
}


# ── Версіонування файлів ──────────────────────────────────────────────────────
def get_versioned_path(pib: str, doc_type: str, base_dir: Path) -> Path:
    """
    Формує шлях ДАТА/ПІБ_тип.pdf
    Якщо файл існує — додає _v2, _v3...
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder = base_dir / date_str
    folder.mkdir(parents=True, exist_ok=True)

    safe_pib = pib.replace(" ", "_").replace("/", "-")
    base = folder / f"{safe_pib}_{doc_type}"
    path = base.with_suffix(".pdf")

    version = 2
    while path.exists():
        path = Path(f"{base}_v{version}.pdf")
        version += 1

    return path


# ── Генерація PDF ─────────────────────────────────────────────────────────────
def generate_pdf(record: dict, diagnosis: str, doc_type: str, file_path: Path):
    """
    record: dict з полями pib, rank, birth_date, phone, location, enroll_date
    """
    _ensure_font()

    width, height = A4  # 595 × 842 pt

    c = canvas.Canvas(str(file_path), pagesize=A4)

    # ── Шапка ────────────────────────────────────────────────────────────────
    c.setFont(_FONT_NAME, 11)
    c.drawRightString(width - 20*mm, height - 15*mm, "В/Ч А7020")

    c.setFont(_FONT_NAME, 14)
    title = DOC_TITLES.get(doc_type, doc_type.upper())
    c.drawCentredString(width / 2, height - 35*mm, title)

    # ── Горизонтальна лінія ───────────────────────────────────────────────────
    c.setLineWidth(0.5)
    c.line(20*mm, height - 40*mm, width - 20*mm, height - 40*mm)

    # ── Поля документа ────────────────────────────────────────────────────────
    c.setFont(_FONT_NAME, 11)
    fields = [
        ("П.І.Б.",            record.get("pib", "—")),
        ("Військове звання",  record.get("rank", "—")),
        ("Дата народження",   record.get("birth_date", "—")),
        ("Номер телефону",    record.get("phone", "—")),
        ("Розміщення о/с",    record.get("location", "—")),
        ("Дата зарахування",  record.get("enroll_date", "—")),
        ("Діагноз",           diagnosis),
    ]

    y = height - 55*mm
    line_h = 10*mm

    for label, value in fields:
        c.setFont(_FONT_NAME, 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(20*mm, y + 3*mm, label + ":")

        c.setFont(_FONT_NAME, 11)
        c.setFillColorRGB(0, 0, 0)

        # Довгий текст — перенос
        max_width = width - 80*mm
        words = value.split()
        line, lines = "", []
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, _FONT_NAME, 11) < max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        c.drawString(55*mm, y, lines[0] if lines else "—")
        for extra_line in lines[1:]:
            y -= 6*mm
            c.drawString(55*mm, y, extra_line)

        # Лінія під полем
        c.setLineWidth(0.3)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(20*mm, y - 2*mm, width - 20*mm, y - 2*mm)
        c.setStrokeColorRGB(0, 0, 0)

        y -= line_h

    # ── Підписи ───────────────────────────────────────────────────────────────
    y_sign = 55*mm
    c.setFont(_FONT_NAME, 11)
    c.drawString(20*mm, y_sign, "Лікар: ___________________________")
    c.drawString(20*mm, y_sign - 10*mm, "Дата: " + datetime.now().strftime("%d.%m.%Y"))
    c.drawRightString(width - 20*mm, y_sign, "М.П.")

    c.save()

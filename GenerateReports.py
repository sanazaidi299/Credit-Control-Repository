import math
from datetime import date
import pandas as pd

# ReportLab - bases
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ReportLab - styles et composants Platypus
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

# Flowables supplémentaires
from reportlab.platypus.flowables import HRFlowable

# ── Couleurs ───────────────────────────────────────────────────────────────────
BRAND   = colors.HexColor("#0d6b5f")   # --brand
GOLD    = colors.HexColor("#bba96f")   # --gold (headers)
MUTED   = colors.HexColor("#6d6d6d")   # --muted
BG      = colors.white                 # --bg
CELL_BG = colors.HexColor("#f0f0f0")   # fond ligne des valeurs
BOX_BG  = colors.HexColor("#f6f6f6")   # boîtes texte
BORDER  = colors.HexColor("#e6e6e6")   # bordures
TEXT    = colors.HexColor("#1f2937")   # texte principal
WHITE   = colors.white

# Couleurs pour Level
LEVEL_RED    = colors.HexColor("#c83a3a")  # Liquidation
LEVEL_ORANGE = colors.HexColor("#d98a00")  # Notification

PAGE_W, PAGE_H = A4
MARGIN_H = 14 * mm
MARGIN_V = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_H

# ── Styles paragraphe ─────────────────────────────────────────────────────────
def make_styles():
    def st(name, **kw):
        cfg = dict(fontName="Helvetica", fontSize=8, leading=10, textColor=TEXT)
        cfg.update(kw)
        return ParagraphStyle(name, **cfg)

    s_normal  = st("Normal")
    s_small   = st("Small",   fontSize=7,   textColor=MUTED)
    s_th      = st("TH",      fontSize=7,   textColor=WHITE, fontName="Helvetica-Bold")
    s_td      = st("TD",      fontSize=7.5, textColor=TEXT)
    s_td_r    = st("TDRight", fontSize=7.5, alignment=TA_RIGHT)
    s_td_c    = st("TDCtr",   fontSize=7.5, alignment=TA_CENTER)
    s_band    = st("Band",    fontSize=7.5, textColor=WHITE, fontName="Helvetica-Bold")
    s_box     = st("Box",     fontSize=7.5, leading=10)
    s_status  = st("Status",  fontSize=7,   textColor=WHITE, fontName="Helvetica-Bold")
    s_title   = st("Title",   fontName="Helvetica-Bold", fontSize=16, textColor=BRAND, leading=20)
    s_sub     = st("Subtitle",fontSize=8, textColor=MUTED, leading=11)
    return dict(normal=s_normal, small=s_small, th=s_th, td=s_td,
                td_r=s_td_r, td_c=s_td_c, band=s_band, box=s_box,
                status=s_status, title=s_title, sub=s_sub)

ST = make_styles()

# ── Colonnes tableau ──────────────────────────────────────────────────────────
# Level passe de 1.0 → 1.6 pour éviter le retour à la ligne
COL_FRACTIONS = [1.6, 1.3, 1.6, 1.2, 0.7, 1.0, 1.0, 1.0, 1.2, 1.1, 1.1, 1.2, 0.9]
COL_NAMES     = ["Level","Entity","Name","Banker","Ccy",
                 "Limit","Mv","Lv","Exposure","Excess","Nav","Excess Date","Delay"]
NUMERIC_COLS  = {"Limit","Mv","Lv","Exposure","Excess","Nav"}
DATE_COLS     = {"Excess Date"}

def col_widths(total=None):
    total = total or CONTENT_W
    total_fr = sum(COL_FRACTIONS)
    return [total * f / total_fr for f in COL_FRACTIONS]

# ── Formatters ────────────────────────────────────────────────────────────────
def fmt_num(v):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return ""
        return f"{int(round(float(v))):,}".replace(",", "'")
    except Exception:
        return str(v) if v else ""

def fmt_str(v):
    return "" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v)

def fmt_date(v):
    if v is None:
        return ""
    try:
        if isinstance(v, float) and math.isnan(v):
            return ""
    except Exception:
        pass
    try:
        if hasattr(v, 'strftime'):
            return v.strftime("%d/%m/%y")
        return pd.to_datetime(v).strftime("%d/%m/%y")
    except Exception:
        return str(v) if v else ""

# ── Un record (bloc) ──────────────────────────────────────────────────────────
def build_record(row, cw):
    flowables = []

    # Labels
    label_data = [Paragraph(c, ST["th"]) for c in COL_NAMES]

    # Valeurs
    value_row = []
    for col in COL_NAMES:
        raw = row.get(col, "")
        if col in NUMERIC_COLS:
            p = Paragraph(fmt_num(raw), ST["td"])
        elif col in DATE_COLS:
            p = Paragraph(fmt_date(raw), ST["td"])
        else:
            p = Paragraph(fmt_str(raw), ST["td"])
        value_row.append(p)

    tbl_header = Table([label_data, value_row], colWidths=cw, rowHeights=[14, 18])

    numeric_start_idx = COL_NAMES.index("Limit")
    numeric_end_idx   = COL_NAMES.index("Nav")

    tbl_header.setStyle(TableStyle([
        # En-têtes
        ("BACKGROUND",   (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 7),
        ("VALIGN",       (0, 0), (-1, 0), "MIDDLE"),
        ("ALIGN",        (0, 0), (-1, 0), "LEFT"),

        # Valeurs
        ("BACKGROUND",   (0, 1), (-1, 1), CELL_BG),
        ("TEXTCOLOR",    (0, 1), (-1, 1), TEXT),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, 1), 7),
        ("VALIGN",       (0, 1), (-1, 1), "MIDDLE"),
        ("ALIGN",        (0, 1), (-1, 1), "LEFT"),
        ("ALIGN",        (numeric_start_idx, 1), (numeric_end_idx, 1), "RIGHT"),

        # Bordures / padding / grille
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#a0956a")),
    ]))
    flowables.append(tbl_header)

    # Coloration conditionnelle: Level
    try:
        lvl_idx = COL_NAMES.index("Level")
        level_val = (row.get("Level") or "").strip().lower()
        if level_val == "liquidation":
            tbl_header.setStyle(TableStyle([
                ("TEXTCOLOR", (lvl_idx, 1), (lvl_idx, 1), LEVEL_RED),
                ("FONTNAME",  (lvl_idx, 1), (lvl_idx, 1), "Helvetica-Bold"),
            ]))
        elif level_val == "notification":
            tbl_header.setStyle(TableStyle([
                ("TEXTCOLOR", (lvl_idx, 1), (lvl_idx, 1), LEVEL_ORANGE),
                ("FONTNAME",  (lvl_idx, 1), (lvl_idx, 1), "Helvetica-Bold"),
            ]))
    except ValueError:
        pass

    # Optionnel: couleurs pour Excess négatif & Excess Date
    try:
        excess_idx = COL_NAMES.index("Excess")
        v = row.get("Excess", None)
        if v is not None:
            try:
                if float(v) < 0:
                    tbl_header.setStyle(TableStyle([
                        ("TEXTCOLOR", (excess_idx, 1), (excess_idx, 1), colors.HexColor("#c83a3a"))
                    ]))
            except Exception:
                pass
    except ValueError:
        pass

    try:
        exd_idx = COL_NAMES.index("Excess Date")
        if fmt_str(row.get("Excess Date", "")).strip():
            tbl_header.setStyle(TableStyle([
                ("TEXTCOLOR", (exd_idx, 1), (exd_idx, 1), colors.HexColor("#0aa778"))
            ]))
    except ValueError:
        pass

    # Band
    band_data = [[Paragraph("Watchlist Reason", ST["band"]),
                  Paragraph("Resolution Description", ST["band"])]]
    tbl_band = Table(band_data, colWidths=[CONTENT_W * 0.54, CONTENT_W * 0.46], rowHeights=[14])
    tbl_band.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GOLD),
        ("TEXTCOLOR",    (0, 0), (-1, -1), WHITE),
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 7),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    flowables.append(tbl_band)

    # Boîtes: raison / résolution
    reason     = fmt_str(row.get("Watchlist Reason", ""))
    resolution = fmt_str(row.get("Resolution Description", ""))
    text_data = [[Paragraph(reason, ST["box"]), Paragraph(resolution, ST["box"])]]
    tbl_text = Table(text_data, colWidths=[CONTENT_W * 0.54, CONTENT_W * 0.46])
    tbl_text.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), BOX_BG),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LINEAFTER",    (0, 0), (0, -1), 0.5, BORDER),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    flowables.append(tbl_text)

    # Status
    status_val   = fmt_str(row.get("Status", ""))
    status_label = Paragraph("Status", ST["status"])
    status_value = Paragraph(status_val, ST["box"])
    status_data = [[status_label, status_value]]
    tbl_status = Table(status_data, colWidths=[18 * mm, CONTENT_W - 18 * mm], rowHeights=[16])
    tbl_status.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, 0), GOLD),
        ("BACKGROUND",   (1, 0), (1, 0), CELL_BG),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    flowables.append(tbl_status)
    flowables.append(Spacer(1, 8))

    return KeepTogether(flowables)

# ── En-tête de page ───────────────────────────────────────────────────────────
def build_page_header(title, subtitle):
    items = []
    bar_data = [["", Paragraph(title, ST["title"])]]
    bar_tbl = Table(bar_data, colWidths=[4, CONTENT_W - 4])
    bar_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, 0), BRAND),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (1, 0), (1, 0), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    items.append(bar_tbl)
    items.append(Spacer(1, 3))
    items.append(Paragraph(subtitle, ST["sub"]))
    items.append(Spacer(1, 10))
    return items

# ── Pied de page ──────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    footer_text = "UNION BANCAIRE PRIVÉE, Union Bancaire Privée (UBP) SA"
    canvas.drawCentredString(PAGE_W / 2, MARGIN_V - 8 * mm, footer_text)
    canvas.restoreState()

# ── Génération PDF ────────────────────────────────────────────────────────────
def generate_pdf(input_xlsx: str, output_pdf: str):
    df = pd.read_excel(input_xlsx)

    # Normaliser les en-têtes (Title Case)
    df.columns = [c.strip() for c in df.columns]
    df.rename(columns={c: c.title() for c in df.columns}, inplace=True)

    # Trier: Liquidation d'abord, Notification ensuite
    def _order_level(s):
        if pd.isna(s):
            return 2
        s = str(s).strip().lower()
        if s == "liquidation":
            return 0
        if s == "notification":
            return 1
        return 2

    if "Level" in df.columns:
        df = df.sort_values(by="Level", key=lambda col: col.map(_order_level))
    else:
        print("Avertissement: colonne 'Level' absente, tri non appliqué.")

    # KPIs
    nb_cases        = len(df)
    nb_liquidation  = len(df[df["Level"].str.lower() == "liquidation"]) if "Level" in df.columns else 0
    nb_notification = len(df[df["Level"].str.lower() == "notification"]) if "Level" in df.columns else 0

    today = date.today()
    report_title    = f"Credit Risk / {today.strftime('%B %Y')} - Lombard Watch List"
    report_subtitle = f"Figures {today.strftime('%d/%m/%Y')}, in 000's"

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=MARGIN_V,
        bottomMargin=MARGIN_V + 5 * mm,
    )

    cw    = col_widths(CONTENT_W)
    story = []

    # Entête
    story.extend(build_page_header(report_title, report_subtitle))

    # KPI summary box (gras comme les labels)
    kpi_text = (
        f"<b>KPIs:</b>  "
        f"<b>Cases:</b> <b>{nb_cases}</b>  |  "
        f"<b>Liquidation:</b> <b>{nb_liquidation}</b>  |  "
        f"<b>Notification:</b> <b>{nb_notification}</b>"
    )
    kpi_style = ParagraphStyle(
        "KPI",
        fontName="Helvetica-Bold",  # gras
        fontSize=9,
        textColor=TEXT,
        leading=12,
        borderColor=BORDER,
        borderWidth=0.5,
        borderPadding=6,
        backColor=BOX_BG,
    )
    story.append(Paragraph(kpi_text, kpi_style))
    story.append(Spacer(1, 10))

    # Un bloc par ligne
    for _, row in df.iterrows():
        story.append(build_record(row.to_dict(), cw))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF généré : {output_pdf}  ({len(df)} enregistrements)")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    xlsx = r"C:\Users\zsa\Desktop\Data\watchlist_input.xlsx"
    pdf  = r"C:\Users\zsa\Desktop\Data\report.pdf"
    generate_pdf(xlsx, pdf)

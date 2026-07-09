import math
from datetime import date, datetime, timedelta
import pandas as pd

# ReportLab - bases
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

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
from reportlab.platypus.flowables import HRFlowable

# Polices: Georgia (fallback Times)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('Georgia',      r'C:\fonts\Georgia\Georgia.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia-Bold', r'C:\fonts\Georgia\Georgia Bold.ttf'))
    TITLE_FONT = 'Georgia-Bold'
    SUB_FONT   = 'Georgia'
    BASE_FONT  = 'Georgia'
    BASE_BOLD  = 'Georgia-Bold'
except Exception:
    TITLE_FONT = 'Times-Bold'     # fallback standard PDF
    SUB_FONT   = 'Times-Roman'
    BASE_FONT  = 'Times-Roman'
    BASE_BOLD  = 'Times-Bold'

# ── Paramètres d’orientation ───────────────────────────────────────────────────
LANDSCAPE_MODE = True

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

# Couleurs pour Excess Date
EXD_GREEN  = colors.HexColor("#0aa778")    # > aujourd'hui
EXD_ORANGE = colors.HexColor("#d98a00")    # <= aujourd'hui

# ── Dimensions de page ────────────────────────────────────────────────────────
if LANDSCAPE_MODE:
    PAGE_W, PAGE_H = landscape(A4)
else:
    PAGE_W, PAGE_H = A4

MARGIN_H = 14 * mm
MARGIN_V = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_H

# ── Styles paragraphe ─────────────────────────────────────────────────────────
def make_styles():
    def st(name, **kw):
        # Style de base
        cfg = dict(fontName=BASE_FONT, fontSize=8, leading=10, textColor=TEXT)
        cfg.update(kw)
        return ParagraphStyle(name, **cfg)

    # Corps
    s_normal  = st("Normal")
    s_small   = st("Small",   fontSize=7,   textColor=MUTED)
    s_th      = st("TH",      fontSize=7,   textColor=WHITE, fontName=BASE_BOLD)
    s_td      = st("TD",      fontSize=7.5, textColor=TEXT,  fontName=BASE_FONT)
    s_td_r    = st("TDRight", fontSize=7.5, alignment=TA_RIGHT,  fontName=BASE_FONT)
    s_td_c    = st("TDCtr",   fontSize=7.5, alignment=TA_CENTER, fontName=BASE_FONT)
    s_band    = st("Band",    fontSize=7.5, textColor=WHITE, fontName=BASE_BOLD)
    s_box     = st("Box",     fontSize=7.5, leading=10, fontName=BASE_FONT)
    s_status  = st("Status",  fontSize=7,   textColor=WHITE, fontName=BASE_BOLD)

    # Titre en Georgia-Bold plus grand
    s_title   = st("Title",   fontName=TITLE_FONT, fontSize=28, leading=32, textColor=BRAND)

    # Sous-titre en Georgia italique
    s_sub     = ParagraphStyle(
        "Subtitle",
        parent=st("SubtitleBase", fontName=SUB_FONT, fontSize=9.5, leading=13, textColor=MUTED),
        italic=True
    )

    return dict(
        normal=s_normal, small=s_small, th=s_th, td=s_td, td_r=s_td_r, td_c=s_td_c,
        band=s_band, box=s_box, status=s_status, title=s_title, sub=s_sub
    )

ST = make_styles()

# ── Colonnes tableau ──────────────────────────────────────────────────────────
COL_FRACTIONS = [1.0, 1.0, 2.7, 2.5, 0.7, 0.7, 0.7, 0.7, 0.9, 0.9, 0.9, 1.2, 1.2]
COL_NAMES     = ["Level","Entity","Name","Banker","CCY",
                 "Limit","MV","LV","Exposure","Excess","NAV","Excess Date","Delay"]
NUMERIC_COLS  = {"Limit","MV","LV","Exposure","Excess","NAV"}
DATE_COLS     = {"Excess Date"}  # Delay reste texte pour affichage simple JJ/MM/AA

def col_widths(total=None):
    total = total or CONTENT_W
    total_fr = sum(COL_FRACTIONS)
    return [total * f / total_fr for f in COL_FRACTIONS]

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
        # dayfirst=True et errors=coerce pour robustesse
        dt = pd.to_datetime(v, dayfirst=True, errors="coerce")
        return "" if pd.isna(dt) else dt.strftime("%d/%m/%y")
    except Exception:
        return str(v) if v else ""

# ── Un record (bloc) ──────────────────────────────────────────────────────────
def build_record(row, cw):
    flowables = []

    # Labels
    label_data = [Paragraph(c, ST["th"]) for c in COL_NAMES]

    # Valeurs (coloration Level imbriquée dans le Paragraph)
    value_row = []
    for col in COL_NAMES:
        raw = row.get(col, "")
        if col == "Level":
            level_val = fmt_str(raw)
            lv_norm = level_val.strip().lower()
            if lv_norm == "liquidation":
                p = Paragraph(f'<font color="{LEVEL_RED.hexval()}"><b>{level_val}</b></font>', ST["td"])
            elif lv_norm == "notification":
                p = Paragraph(f'<font color="{LEVEL_ORANGE.hexval()}"><b>{level_val}</b></font>', ST["td"])
            else:
                p = Paragraph(level_val, ST["td"])

        elif col in NUMERIC_COLS:
            if col in ("Excess","NAV"):
                # normaliser pour test de signe
                raw_str = str(raw).strip().replace("\u2212", "-")
                raw_str = (raw_str
                           .replace("'", "")
                           .replace(" ", "")
                           .replace("\u00A0", "")
                           .replace(",", "."))
                neg = False
                try:
                    neg = float(raw_str) < 0
                except Exception:
                    neg = False
                txt = fmt_num(raw)
                p = Paragraph(f'<font color="#c83a3a">{txt}</font>', ST["td"]) if neg else Paragraph(txt, ST["td"])
            else:
                p = Paragraph(fmt_num(raw), ST["td"])            

        elif col in DATE_COLS:
            # Affichage
            disp = fmt_date(raw)

            # Coloration au niveau du texte (pas de conflit TableStyle)
            color_hex = None
            try:
                exd_parsed = row.get("Excess Date Parsed", None) if col == "Excess Date" else None
                exd_dt = None
                if exd_parsed is not None and str(exd_parsed) not in ("NaT", ""):
                    exd_dt = pd.to_datetime(exd_parsed, errors="coerce")
                else:
                    exd_str = fmt_str(raw).strip()
                    if exd_str:
                        exd_str_norm = exd_str.replace(".", "/").replace("-", "/")
                        exd_dt = pd.to_datetime(exd_str_norm, dayfirst=True, errors="coerce")

                if exd_dt is not None and not pd.isna(exd_dt):
                    if hasattr(exd_dt, "to_pydatetime"):
                        exd_dt = exd_dt.to_pydatetime()
                    exd_dt = exd_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    color_hex = "#0aa778" if exd_dt > today_dt else "#d98a00"
            except Exception:
                color_hex = None

            p = Paragraph(f'<font color="{color_hex}">{disp}</font>', ST["td"]) if color_hex else Paragraph(disp, ST["td"])

        else:
            # Delay (et autres colonnes non numériques, non dates) comme texte brut
            p = Paragraph(fmt_str(raw), ST["td"])

        value_row.append(p)

    tbl_header = Table([label_data, value_row], colWidths=cw, rowHeights=[14, 18])

    # Indices pour alignement à droite des numériques
    numeric_start_idx = COL_NAMES.index("Limit")
    numeric_end_idx   = COL_NAMES.index("NAV")

    # Styles Table (Georgia)
    tbl_header.setStyle(TableStyle([
        # En-têtes
        ("BACKGROUND",   (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), BASE_BOLD),
        ("FONTSIZE",     (0, 0), (-1, 0), 7),
        ("VALIGN",       (0, 0), (-1, 0), "MIDDLE"),
        ("ALIGN",        (0, 0), (-1, 0), "LEFT"),

        # Valeurs
        ("BACKGROUND",   (0, 1), (-1, 1), CELL_BG),
        ("TEXTCOLOR",    (0, 1), (-1, 1), TEXT),
        ("FONTNAME",     (0, 1), (-1, 1), BASE_FONT),
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

    # Sécurité: coloration Excess < 0 (si besoin)
    try:
        excess_idx = COL_NAMES.index("Excess")
        v = row.get("Excess", None)
        if v is not None:
            vs = str(v).strip()
            if vs:
                vs_norm = (vs.replace("'", "")
                             .replace(" ", "")
                             .replace("\u00A0","")
                             .replace(",", "."))
                v_num = float(vs_norm)
                if v_num < 0:
                    tbl_header.setStyle(TableStyle([
                        ("TEXTCOLOR", (excess_idx, 1), (excess_idx, 1), colors.HexColor("#c83a3a")),
                    ]))
    except Exception:
        pass

    flowables.append(tbl_header)

    # Bandeau raison / résolution
    band_data = [[Paragraph("Watchlist Reason", ST["band"]),
                  Paragraph("Resolution Description", ST["band"])]]
    tbl_band = Table(band_data, colWidths=[CONTENT_W * 0.54, CONTENT_W * 0.46], rowHeights=[14])
    tbl_band.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GOLD),
        ("TEXTCOLOR",    (0, 0), (-1, -1), WHITE),
        ("FONTNAME",     (0, 0), (-1, -1), BASE_BOLD),
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
    bar_w = 8      # épaisseur de la barre verticale
    row_h = 40     # hauteur pour loger le titre 28 pt
    bar_tbl = Table([[ "", Paragraph(title, ST["title"]) ]],
                    colWidths=[bar_w, CONTENT_W - bar_w],
                    rowHeights=[row_h])
    bar_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, 0), BRAND),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    items.append(bar_tbl)

    items.append(Spacer(1, 4))
    items.append(Paragraph(subtitle, ST["sub"]))

    # séparateur fin
    items.append(HRFlowable(color=BORDER, thickness=0.6, width="100%", spaceBefore=6, spaceAfter=10, lineCap='round'))
    return items

# ── Pied de page ──────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(BASE_FONT, 7)
    canvas.setFillColor(MUTED)
    footer_text = "UNION BANCAIRE PRIVÉE, Union Bancaire Privée (Union Bancaire Privée (UBP)) SA"
    canvas.drawCentredString(PAGE_W / 2, MARGIN_V - 8 * mm, footer_text)
    canvas.restoreState()

# ── Génération PDF ────────────────────────────────────────────────────────────
def generate_pdf(input_xlsx: str, output_pdf: str):
    df = pd.read_excel(input_xlsx)

    # Normalisation robuste des en-têtes (1 seul passage)
    def norm_header(h):
        return (
            str(h).strip()
            .replace("\u00A0", " ")
            .replace("-", " ")
            .replace("_", " ")
        )

    df.columns = [norm_header(c) for c in df.columns]

    # Mapping vers EXACT labels attendus par COL_NAMES
    canon_map = {
        "level": "Level",
        "entity": "Entity",
        "name": "Name",
        "banker": "Banker",

        "ccy": "CCY",
        "currency": "CCY",
        "currency iso": "CCY",

        "limit": "Limit",

        "mv": "MV",
        "market value": "MV",
        "marketvalue": "MV",
        "market value entity ccy": "MV",
        "marketvalueentityccy": "MV",

        "lv": "LV",
        "lending value": "LV",
        "available lv": "LV",
        "available lv entity ccy": "LV",
        "availablelventityccy": "LV",

        "exposure": "Exposure",
        "excess": "Excess",

        "nav": "NAV",
        "net assets": "NAV",
        "netassets": "NAV",

        "excess date": "Excess Date",
        "delay": "Delay",
    }

    new_cols = {}
    for c in df.columns:
        key = " ".join(norm_header(c).lower().split())
        if key in canon_map:
            new_cols[c] = canon_map[key]
    df.rename(columns=new_cols, inplace=True)

    # Parsing + formatage Excess Date (supporte ., -, /)
    if "Excess Date" in df.columns:
        tmp = df["Excess Date"].astype(str).str.replace(r"[.\-]", "/", regex=True)
        df["Excess Date Parsed"] = pd.to_datetime(tmp, errors="coerce", dayfirst=True)
        df["Excess Date"] = pd.to_datetime(tmp, errors="coerce", dayfirst=True).dt.strftime("%d/%m/%y")
        df["Excess Date"] = df["Excess Date"].replace("NaT", "")

    # Parsing + formatage Delay (JJ/MM/AA, sans heure)
    if "Delay" in df.columns:
        delay_tmp = df["Delay"].astype(str).str.strip()
        delay_tmp = delay_tmp.replace(r"[.\-]", "/", regex=True)
        delay_dt = pd.to_datetime(delay_tmp, errors="coerce", dayfirst=True)
        df["Delay"] = delay_dt.dt.strftime("%d/%m/%y")
        df["Delay"] = df["Delay"].replace("NaT", "").fillna("")

    # Tri par Level
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
    nb_liquidation  = len(df[df.get("Level","").astype(str).str.lower() == "liquidation"]) if "Level" in df.columns else 0
    nb_notification = len(df[df.get("Level","").astype(str).str.lower() == "notification"]) if "Level" in df.columns else 0

    d = date.today() - timedelta(days=1)
    report_title    = f"Credit Risk / {d.strftime('%B %Y')} - Lombard Watch List"
    report_subtitle = f"Figures {d.strftime('%d/%m/%Y')}, in 000's"

    # Choix de la page
    page_size = landscape(A4) if LANDSCAPE_MODE else A4

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=page_size,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=MARGIN_V,
        bottomMargin=MARGIN_V + 5 * mm,
    )

    # story
    story = []
    story.extend(build_page_header(report_title, report_subtitle))

    # KPI summary box
    kpi_text = (
        f"<b>KPIs:</b>  "
        f"<b>Cases:</b> <b>{nb_cases}</b>  |  "
        f"<b>Liquidation:</b> <b>{nb_liquidation}</b>  |  "
        f"<b>Notification:</b> <b>{nb_notification}</b>"
    )
    kpi_style = ParagraphStyle(
        "KPI",
        fontName=BASE_BOLD,
        fontSize=10,
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
    cw = col_widths(CONTENT_W)
    for _, row in df.iterrows():
        story.append(build_record(row.to_dict(), cw))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF généré : {output_pdf}  ({len(df)} enregistrements)")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    xlsx = r"C:\Users\zsa\Desktop\Data\watchlist_input.xlsx"
    pdf  = r"C:\Users\zsa\Desktop\Data\report.pdf"
    generate_pdf(xlsx, pdf)

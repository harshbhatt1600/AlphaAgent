# tools/report_generator.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# --- Professional Color Palette (print-safe) ---
BLACK = colors.HexColor("#0d1117")
DARK_GRAY = colors.HexColor("#24292f")
MID_GRAY = colors.HexColor("#57606a")
LIGHT_GRAY = colors.HexColor("#f6f8fa")
BORDER_GRAY = colors.HexColor("#d0d7de")
ACCENT_BLUE = colors.HexColor("#0969da")
ACCENT_GREEN = colors.HexColor("#1a7f37")
ACCENT_RED = colors.HexColor("#cf222e")
ACCENT_ORANGE = colors.HexColor("#bc4c00")
ACCENT_PURPLE = colors.HexColor("#6639ba")
WHITE = colors.white
HEADER_BG = colors.HexColor("#0d1117")
SIGNAL_BG_BUY = colors.HexColor("#dafbe1")
SIGNAL_BG_SELL = colors.HexColor("#ffebe9")
SIGNAL_BG_HOLD = colors.HexColor("#f6f8fa")
TABLE_HEADER_BG = colors.HexColor("#f6f8fa")
AI_BG = colors.HexColor("#f0f6ff")
AI_BORDER = colors.HexColor("#0969da")


def generate_report(ticker, stock_data, indicators, anomalies, news, output_path=None):
    if output_path is None:
        os.makedirs("data/reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/reports/{ticker.upper()}_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=16*mm,
        bottomMargin=16*mm
    )

    W = 174*mm  # usable width

    # ── Styles ──────────────────────────────────────────────
    s_logo = ParagraphStyle("logo", fontSize=18, textColor=WHITE,
                            fontName="Helvetica-Bold", leading=22)
    s_header_sub = ParagraphStyle("hsub", fontSize=8, textColor=colors.HexColor("#8b949e"),
                                  fontName="Helvetica", alignment=TA_RIGHT)
    s_company = ParagraphStyle("co", fontSize=15, textColor=BLACK,
                               fontName="Helvetica-Bold", leading=20, spaceBefore=12, spaceAfter=2)
    s_meta = ParagraphStyle("meta", fontSize=8, textColor=MID_GRAY,
                            fontName="Helvetica", spaceAfter=10)
    s_section = ParagraphStyle("sec", fontSize=7, textColor=MID_GRAY,
                               fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
                               borderPad=0)
    s_body = ParagraphStyle("body", fontSize=9, textColor=DARK_GRAY,
                            fontName="Helvetica", leading=14, spaceAfter=4)
    s_news = ParagraphStyle("news", fontSize=8.5, textColor=DARK_GRAY,
                            fontName="Helvetica", leading=13, spaceAfter=5)
    s_footer = ParagraphStyle("foot", fontSize=7, textColor=MID_GRAY,
                              fontName="Helvetica", alignment=TA_CENTER)
    s_ai_title = ParagraphStyle("ait", fontSize=8, textColor=ACCENT_BLUE,
                                fontName="Helvetica-Bold", spaceAfter=6)
    s_ai_body = ParagraphStyle("aib", fontSize=9, textColor=DARK_GRAY,
                               fontName="Helvetica", leading=15)
    s_tbl_hdr = ParagraphStyle("th", fontSize=7, textColor=MID_GRAY,
                               fontName="Helvetica-Bold")
    s_tbl_val = ParagraphStyle("tv", fontSize=9, textColor=DARK_GRAY,
                               fontName="Helvetica-Bold", alignment=TA_RIGHT)
    s_tbl_lbl = ParagraphStyle("tl", fontSize=9, textColor=DARK_GRAY,
                               fontName="Helvetica")

    story = []

    # ── Helper ───────────────────────────────────────────────
    def section_rule(title):
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
        story.append(Paragraph(title.upper(), s_section))

    def colored(text, hex_color):
        return f'<font color="{hex_color}">{text}</font>'

    # ── Gather data ──────────────────────────────────────────
    company = stock_data.get("company_name", ticker.upper())
    currency = stock_data.get("currency", "")
    curr_sym = "Rs." if currency == "INR" else "USD "
    price = stock_data.get("current_price", 0)
    change = stock_data.get("price_change_pct", 0)
    high52 = stock_data.get("52_week_high", "N/A")
    low52 = stock_data.get("52_week_low", "N/A")
    pe = stock_data.get("pe_ratio", "N/A")
    sector = stock_data.get("sector", "N/A")
    period = stock_data.get("period", "N/A")
    ma = indicators.get("moving_averages", {})
    macd = indicators.get("MACD", {})
    bb = indicators.get("bollinger_bands", {})
    rsi_val = indicators.get("RSI", {}).get("value", "N/A")
    anomaly_list = anomalies.get("anomalies", []) if isinstance(anomalies, dict) else []
    anomaly_count = len(anomaly_list)
    headlines = news.get("latest_headlines", []) if isinstance(news, dict) else []

    def fmt(v, sym=""):
        if isinstance(v, float): return f"{sym}{v:,.2f}"
        return str(v)

    rsi_str = fmt(rsi_val)
    price_str = fmt(price, curr_sym)
    change_str = f"{change:+.2f}%" if isinstance(change, float) else "N/A"

    # Signal
    signals = []
    if isinstance(rsi_val, float):
        if rsi_val < 30: signals.append("BULL")
        elif rsi_val > 70: signals.append("BEAR")
    if "BULLISH" in str(macd.get("signal", "")): signals.append("BULL")
    elif "BEARISH" in str(macd.get("signal", "")): signals.append("BEAR")
    if "BULLISH" in str(ma.get("signal", "")): signals.append("BULL")
    elif "BEARISH" in str(ma.get("signal", "")): signals.append("BEAR")
    bull = signals.count("BULL")
    bear = signals.count("BEAR")
    if bull > bear:
        sig_text, sig_color, sig_bg = "▲  BUY", "#1a7f37", SIGNAL_BG_BUY
    elif bear > bull:
        sig_text, sig_color, sig_bg = "▼  SELL", "#cf222e", SIGNAL_BG_SELL
    else:
        sig_text, sig_color, sig_bg = "◆  HOLD", "#57606a", SIGNAL_BG_HOLD

    # ── HEADER BAR ───────────────────────────────────────────
    header_data = [[
        Paragraph("<font color='#58a6ff'><b>ALPHA</b></font><font color='#ffffff'>AGENT</font>", ParagraphStyle("lg", fontSize=17, textColor=WHITE,
                  fontName="Helvetica-Bold")),
        Paragraph(
            f"<font color='#8b949e'>Equity Research Report</font><br/>"
            f"<font color='#8b949e'>{datetime.now().strftime('%d %B %Y  |  %I:%M %p')}</font>",
            ParagraphStyle("hd", fontSize=8, textColor=WHITE, fontName="Helvetica",
                           alignment=TA_RIGHT, leading=13)
        )
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.5, W*0.5])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), HEADER_BG),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (0,0), 14),
        ("RIGHTPADDING", (-1,0), (-1,0), 14),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10))

    # ── COMPANY + SIGNAL ─────────────────────────────────────
    sig_cell = Table(
        [[Paragraph(f'<font color="{sig_color}"><b>{sig_text}</b></font>',
                    ParagraphStyle("sc", fontSize=11, textColor=colors.HexColor(sig_color),
                                   fontName="Helvetica-Bold", alignment=TA_CENTER))]],
        colWidths=[36*mm]
    )
    sig_cell.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), sig_bg),
        ("BOX", (0,0), (-1,-1), 0.8, colors.HexColor(sig_color)),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))

    top_row = Table(
        [[Paragraph(company, s_company), sig_cell]],
        colWidths=[W - 44*mm, 44*mm]
    )
    top_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(top_row)
    story.append(Paragraph(
        f"{ticker.upper()}  &nbsp;·&nbsp;  {currency}  &nbsp;·&nbsp;  {sector}  &nbsp;·&nbsp;  Period: {period}",
        s_meta
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY))

    # ── KEY METRICS ──────────────────────────────────────────
    section_rule("Key Metrics")

    change_col = "#1a7f37" if isinstance(change, float) and change >= 0 else "#cf222e"

    def kpi(label, value, sub="", sub_color="#57606a"):
        return [
            Paragraph(label, ParagraphStyle("kl", fontSize=7, textColor=MID_GRAY,
                      fontName="Helvetica-Bold", spaceAfter=3)),
            Paragraph(str(value), ParagraphStyle("kv", fontSize=13, textColor=BLACK,
                      fontName="Helvetica-Bold", spaceAfter=2)),
            Paragraph(str(sub), ParagraphStyle("ks", fontSize=7.5,
                      textColor=colors.HexColor(sub_color), fontName="Helvetica")),
        ]

    col_w = W / 5
    kpi_data = [[
        kpi("CURRENT PRICE", price_str, change_str, change_col),
        kpi("52-WEEK HIGH", fmt(high52, curr_sym)),
        kpi("52-WEEK LOW", fmt(low52, curr_sym)),
        kpi("RSI (14)", rsi_str,
            "Overbought" if isinstance(rsi_val, float) and rsi_val > 70
            else "Oversold" if isinstance(rsi_val, float) and rsi_val < 30 else "Neutral",
            "#cf222e" if isinstance(rsi_val, float) and rsi_val > 70
            else "#1a7f37" if isinstance(rsi_val, float) and rsi_val < 30 else "#57606a"),
        kpi("ANOMALIES", str(anomaly_count),
            "Detected" if anomaly_count > 0 else "Clean",
            "#bc4c00" if anomaly_count > 0 else "#1a7f37"),
    ]]
    kpi_tbl = Table(kpi_data, colWidths=[col_w]*5)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), WHITE),
        ("BOX", (0,0), (0,-1), 0.8, BORDER_GRAY),
        ("BOX", (1,0), (1,-1), 0.8, BORDER_GRAY),
        ("BOX", (2,0), (2,-1), 0.8, BORDER_GRAY),
        ("BOX", (3,0), (3,-1), 0.8, BORDER_GRAY),
        ("BOX", (4,0), (4,-1), 0.8, BORDER_GRAY),
        ("LINEABOVE", (0,0), (0,-1), 3, ACCENT_BLUE),
        ("LINEABOVE", (1,0), (1,-1), 3, ACCENT_BLUE),
        ("LINEABOVE", (2,0), (2,-1), 3, ACCENT_BLUE),
        ("LINEABOVE", (3,0), (3,-1), 3, ACCENT_BLUE),
        ("LINEABOVE", (4,0), (4,-1), 3, ACCENT_BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LINEAFTER", (0,0), (3,-1), 0.5, BORDER_GRAY),
    ]))
    story.append(kpi_tbl)

    # ── TECHNICAL INDICATORS ─────────────────────────────────
    section_rule("Technical Indicators")

    def signal_badge(sig):
        if sig == "BULLISH":
            return Paragraph(colored("● BULLISH", "#1a7f37"),
                             ParagraphStyle("sb", fontSize=8, textColor=ACCENT_GREEN,
                                           fontName="Helvetica-Bold", alignment=TA_RIGHT))
        elif sig == "BEARISH":
            return Paragraph(colored("● BEARISH", "#cf222e"),
                             ParagraphStyle("sb", fontSize=8, textColor=ACCENT_RED,
                                           fontName="Helvetica-Bold", alignment=TA_RIGHT))
        elif sig:
            return Paragraph(sig, ParagraphStyle("sb", fontSize=8, textColor=MID_GRAY,
                                                fontName="Helvetica", alignment=TA_RIGHT))
        return Paragraph("—", ParagraphStyle("sb", fontSize=8, textColor=BORDER_GRAY,
                                            fontName="Helvetica", alignment=TA_RIGHT))

    hdr = [
        Paragraph("INDICATOR", s_tbl_hdr),
        Paragraph("VALUE", ParagraphStyle("th2", fontSize=7, textColor=MID_GRAY,
                  fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        Paragraph("SIGNAL", ParagraphStyle("th3", fontSize=7, textColor=MID_GRAY,
                  fontName="Helvetica-Bold", alignment=TA_RIGHT)),
    ]

    def ind_row(label, value, sig=None):
        return [
            Paragraph(label, s_tbl_lbl),
            Paragraph(str(value), s_tbl_val),
            signal_badge(sig),
        ]

    ind_data = [
        hdr,
        ind_row("Moving Average 20", fmt(ma.get("MA_20", "N/A")), ma.get("signal")),
        ind_row("Moving Average 50", fmt(ma.get("MA_50", "N/A"))),
        ind_row("MACD Line", fmt(macd.get("macd", "N/A")), macd.get("signal")),
        ind_row("MACD Signal Line", fmt(macd.get("signal_line", "N/A"))),
        ind_row("MACD Histogram", fmt(macd.get("histogram", "N/A"))),
        ind_row("Bollinger Upper Band", fmt(bb.get("upper", "N/A"))),
        ind_row("Bollinger Middle Band", fmt(bb.get("middle", "N/A"))),
        ind_row("Bollinger Lower Band", fmt(bb.get("lower", "N/A"))),
        ind_row("RSI (14)", rsi_str,
                "OVERBOUGHT" if isinstance(rsi_val, float) and rsi_val > 70
                else "OVERSOLD" if isinstance(rsi_val, float) and rsi_val < 30 else "NEUTRAL"),
    ]

    col_widths = [W*0.52, W*0.28, W*0.20]
    ind_tbl = Table(ind_data, colWidths=col_widths, repeatRows=1)
    ind_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0,0), (-1,0), TABLE_HEADER_BG),
        ("LINEBELOW", (0,0), (-1,0), 1, BORDER_GRAY),
        ("TOPPADDING", (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 7),
        # Data rows
        ("LINEBELOW", (0,1), (-1,-1), 0.5, BORDER_GRAY),
        ("TOPPADDING", (0,1), (-1,-1), 7),
        ("BOTTOMPADDING", (0,1), (-1,-1), 7),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        # All
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GRAY),
    ]))
    story.append(ind_tbl)

    # ── NEWS HEADLINES ────────────────────────────────────────
    if headlines:
        section_rule("Latest Market News")
        for i, h in enumerate(headlines[:5], 1):
            story.append(Table(
                [[
                    Paragraph(str(i), ParagraphStyle("ni", fontSize=8, textColor=ACCENT_BLUE,
                              fontName="Helvetica-Bold", alignment=TA_CENTER)),
                    Paragraph(h, s_news)
                ]],
                colWidths=[8*mm, W - 8*mm]
            ))
            story.append(Spacer(1, 2))

    # ── ANOMALIES ─────────────────────────────────────────────
    if anomaly_list:
        section_rule(f"Anomalies Detected  ({anomaly_count})")
        anom_data = [
            [Paragraph(h, ParagraphStyle("ah", fontSize=7, textColor=MID_GRAY,
                       fontName="Helvetica-Bold"))
             for h in ["DATE", "TYPE", "Z-SCORE", "SEVERITY"]]
        ]
        for a in anomaly_list[:6]:
            sev = a.get("severity", "")
            sev_col = "#cf222e" if "HIGH" in str(sev) else "#bc4c00"
            anom_data.append([
                Paragraph(str(a.get("date", "N/A")), s_tbl_lbl),
                Paragraph(str(a.get("type", "N/A")), s_tbl_lbl),
                Paragraph(str(a.get("z_score", "N/A")), s_tbl_val),
                Paragraph(colored(str(sev), sev_col),
                          ParagraphStyle("sv", fontSize=9, textColor=colors.HexColor(sev_col),
                                        fontName="Helvetica-Bold", alignment=TA_RIGHT)),
            ])
        anom_tbl = Table(anom_data, colWidths=[W*0.25, W*0.30, W*0.22, W*0.23])
        anom_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), TABLE_HEADER_BG),
            ("LINEBELOW", (0,0), (-1,0), 1, BORDER_GRAY),
            ("LINEBELOW", (0,1), (-1,-1), 0.5, BORDER_GRAY),
            ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("BOX", (0,0), (-1,-1), 0.5, BORDER_GRAY),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ]))
        story.append(anom_tbl)

    # ── AI RECOMMENDATION ─────────────────────────────────────
    section_rule("AlphaAgent Recommendation")

    ma20 = ma.get("MA_20", 0)
    ma50 = ma.get("MA_50", 0)
    trend = "above" if isinstance(ma20, float) and isinstance(ma50, float) and ma20 > ma50 else "below"
    momentum = "confirming bullish momentum." if ma.get("signal") == "BULLISH" else "signalling bearish pressure."

    rsi_comment = (
        "RSI at overbought territory — a pullback may be likely in the near term."
        if isinstance(rsi_val, float) and rsi_val > 70
        else "RSI in oversold territory — a recovery could be forming."
        if isinstance(rsi_val, float) and rsi_val < 30
        else f"RSI at {rsi_str} sits in neutral zone with balanced momentum."
    )

    rec_text = (
        f"Signal: {colored(sig_text, sig_color)}  &nbsp;|&nbsp;  "
        f"RSI: <b>{rsi_str}</b>  &nbsp;|&nbsp;  "
        f"Anomalies: {colored(str(anomaly_count) + ' detected', '#bc4c00' if anomaly_count > 0 else '#1a7f37')}"
        f"<br/><br/>"
        f"Based on technical analysis, <b>{company}</b> is showing a "
        f"{colored('<b>' + sig_text + '</b>', sig_color)} signal. "
        f"{rsi_comment} "
        f"MA20 is {trend} MA50, {momentum}"
    )

    rec_inner = Table(
        [
            [Paragraph("◆  ALPHAAGENT  ·  AUTONOMOUS ANALYSIS", s_ai_title)],
            [Paragraph(rec_text, s_ai_body)],
        ],
        colWidths=[W - 4*mm]
    )
    rec_inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), AI_BG),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("LINEAFTER", (0,0), (0,-1), 3, ACCENT_BLUE),  # left accent stripe via right border of col -1... using box:
    ]))

    # Wrap in outer table to add left blue stripe
    rec_outer = Table([[rec_inner]], colWidths=[W])
    rec_outer.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LINEBEFORE", (0,0), (0,-1), 4, ACCENT_BLUE),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#c8e1ff")),
    ]))
    story.append(KeepTogether(rec_outer))

    # ── FOOTER ────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"AlphaAgent Equity Research  &nbsp;·&nbsp;  Generated {datetime.now().strftime('%d %b %Y')}  "
        f"&nbsp;·&nbsp;  This report is for informational purposes only and does not constitute financial advice.",
        s_footer
    ))

    doc.build(story)
    print(f"[REPORT] PDF saved to: {output_path}")
    return output_path


# --- Test ---
if __name__ == "__main__":
    from tools.fetch_stock_data import fetch_stock_data
    from tools.technical_indicators import calculate_indicators
    from tools.anomaly_detection import detect_anomalies
    from tools.news_sentiment import get_stock_news

    ticker = "TCS.NS"
    print(f"Generating report for {ticker}...")
    stock = fetch_stock_data(ticker)
    indicators = calculate_indicators(ticker)
    anomalies = detect_anomalies(ticker)
    news = get_stock_news(ticker, stock.get("company_name", ticker))
    path = generate_report(ticker, stock, indicators, anomalies, news)
    print(f"Report generated: {path}")
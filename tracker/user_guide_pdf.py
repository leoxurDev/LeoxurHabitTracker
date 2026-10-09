import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def build_user_guide_pdf():
    """Generate executive-level PDF User & Deployment Guide by Leoxur Inc."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom Apple/Executive Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1D1D1F'),
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0071E3'),
        alignment=TA_LEFT,
        spaceAfter=12,
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#86868B'),
        alignment=TA_RIGHT,
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1D1D1F'),
        spaceBefore=14,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0071E3'),
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#333336'),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#424245'),
        leftIndent=12,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1D1D1F'),
        backColor=colors.HexColor('#F5F5F7'),
        borderColor=colors.HexColor('#D2D2D7'),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )

    elements = []

    # 1. Header Banner
    header_table = Table([
        [
            Paragraph("<b>HABIT TRACKER OS</b>", title_style),
            Paragraph("<b>Version 2.4.0 Production</b><br/>Engineered by <b>Leoxur Inc.</b>", meta_style)
        ],
        [
            Paragraph("Official User Manual, Architecture & Post-Deployment Setup Guide", subtitle_style),
            Paragraph("Build Date: 2026.10<br/>Status: Verified Stable", meta_style)
        ]
    ], colWidths=[4.2 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0071E3'), spaceBefore=2, spaceAfter=12))

    # 2. Executive Overview
    elements.append(Paragraph("1. Executive Overview & System Architecture", h1_style))
    elements.append(Paragraph(
        "<b>Habit Tracker OS</b> by <b>Leoxur Inc.</b> is an executive-tier, 24-hour life canvas application engineered with Apple Cupertino ergonomics and powered by Google Gemini Cloud AI. Designed for high-output leadership and personal mastery, it models time at second-level fidelity without double-counting.",
        body_style
    ))

    # Architecture Highlights Table
    arch_data = [
        [Paragraph("<b>Core Feature</b>", h2_style), Paragraph("<b>Implementation & Behavioral Logic</b>", h2_style)],
        [
            Paragraph("<b>24-Hour Matrix</b>", body_style),
            Paragraph("24 chronological slots (00:00 to 23:00) with squircle glass cards in Grid View and vertical chronological stream in List View.", body_style)
        ],
        [
            Paragraph("<b>Proportional Color Fill</b>", body_style),
            Paragraph("Exact geometric fill: 1h = 100% card glow, 30m = 50% half fill with a vertical glowing divider accent, 15m = 25%, micro-seconds sliced proportionally. Segmented multi-activity gradients per category.", body_style)
        ],
        [
            Paragraph("<b>Multi-Hour Spanning</b>", body_style),
            Paragraph("Sessions exceeding 1 hour automatically cascade across subsequent hour blocks with 'Spanned • Start-End' badges. Stored as a single master record to maintain mathematical accuracy in Apple Activity Rings.", body_style)
        ],
        [
            Paragraph("<b>Persistent Live Stopwatch</b>", body_style),
            Paragraph("Real-time top bar & floating focus stopwatch that persists elapsed time across browser tabs and reloads via localStorage.", body_style)
        ],
        [
            Paragraph("<b>Habit Intelligence (Gemini AI)</b>", body_style),
            Paragraph("Autonomous cloud AI (Google Gemini 3.5 Flash Lite) with full application knowledge capable of logging activities, clearing slots, and controlling views from chat.", body_style)
        ]
    ]
    t_arch = Table(arch_data, colWidths=[2.2 * inch, 5.2 * inch])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1D1D1F')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t_arch)
    elements.append(Spacer(1, 10))

    # 3. Post-Deployment Step-by-Step Configuration Guide
    elements.append(Paragraph("2. Post-Deployment Configuration Steps (By Leoxur Inc.)", h1_style))
    elements.append(Paragraph("Follow these 4 simple steps immediately after deploying Habit Tracker to your server:", body_style))

    elements.append(Paragraph("<b>Step 1: Database Initialization & Migrations</b>", h2_style))
    elements.append(Paragraph("Run database migrations to ensure all profile, localization, and scheduler tables are active:", body_style))
    elements.append(Paragraph("./venv/bin/python3 manage.py migrate", code_style))

    elements.append(Paragraph("<b>Step 2: Google Gemini AI Cloud Key Setup</b>", h2_style))
    elements.append(Paragraph(
        "1. Open <b>Google AI Studio</b> (<font color='#0071E3'>aistudio.google.com</font>) and create a free Gemini API key.<br/>"
        "2. In Habit Tracker, go to <b>Settings → Habit Intelligence & Gemini AI</b>.<br/>"
        "3. Paste your API key and click <b>Test Connection ⚡</b>. The system validates the key in ~0.8s and activates <b>Gemini 3.5 Flash Lite</b>.<br/>"
        "4. Click <b>Save AI Configuration</b>. The green status badge will confirm connection.",
        bullet_style
    ))

    elements.append(Paragraph("<b>Step 3: Automated SMTP Email Delivery Setup</b>", h2_style))
    elements.append(Paragraph(
        "1. In <b>Settings → SMTP Email Configuration</b>, choose your preset (Gmail, iCloud, or Outlook).<br/>"
        "2. For Gmail: Use your Google App Password (generated at myaccount.google.com/apppasswords).<br/>"
        "3. Enter host (smtp.gmail.com), port (587), and check <b>Use TLS</b>.<br/>"
        "4. Click <b>Test SMTP Connection</b> to send a verification email to your inbox.",
        bullet_style
    ))

    elements.append(Paragraph("<b>Step 4: Global Language & Regional Timezone</b>", h2_style))
    elements.append(Paragraph(
        "1. Select your preferred language from over 40 global world languages in <b>Settings → Profile & Targets</b>.<br/>"
        "2. Habit Intelligence automatically adapts to communicate in your chosen language.<br/>"
        "3. Timezone can be adjusted in <font color='#0071E3'>habit_project/settings.py</font> (<font color='#1D1D1F'>TIME_ZONE = 'Asia/Kolkata'</font> or your local timezone).",
        bullet_style
    ))
    elements.append(Spacer(1, 10))

    # 4. Bulk CSV Spreadsheet Schema
    elements.append(Paragraph("3. Bulk CSV Spreadsheet Upload Schema", h1_style))
    elements.append(Paragraph("You can bulk log activities across any date using our built-in CSV template. The 7 columns are:", body_style))

    csv_data = [
        [Paragraph("<b>Column Header</b>", h2_style), Paragraph("<b>Format / Options</b>", h2_style), Paragraph("<b>Example Value</b>", h2_style)],
        [Paragraph("Date", body_style), Paragraph("YYYY-MM-DD", body_style), Paragraph("2026-10-10", body_style)],
        [Paragraph("Hour", body_style), Paragraph("Integer (0 - 23)", body_style), Paragraph("9 (for 9:00 AM)", body_style)],
        [Paragraph("Activity Title", body_style), Paragraph("Text (up to 150 chars)", body_style), Paragraph("Executive Strategy Review", body_style)],
        [Paragraph("Category", body_style), Paragraph("Matches category name", body_style), Paragraph("Deep Work & Career", body_style)],
        [Paragraph("Duration", body_style), Paragraph("Numeric float or integer", body_style), Paragraph("2.5", body_style)],
        [Paragraph("Unit", body_style), Paragraph("hours / minutes / seconds", body_style), Paragraph("hours", body_style)],
        [Paragraph("Energy Level", body_style), Paragraph("Integer (1 to 5)", body_style), Paragraph("5", body_style)],
    ]
    t_csv = Table(csv_data, colWidths=[1.8 * inch, 2.8 * inch, 2.8 * inch])
    t_csv.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F7')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t_csv)
    elements.append(Spacer(1, 10))

    # 5. Natural Language Command Directory
    elements.append(Paragraph("4. Habit Intelligence Autonomous Command Quick-Reference", h1_style))
    cmd_data = [
        [Paragraph("<b>Goal / Intent</b>", h2_style), Paragraph("<b>Sample Natural Language Command</b>", h2_style)],
        [Paragraph("Log Multi-Hour Activity", body_style), Paragraph("<i>'Log 3 hours of Deep Work at 10 AM'</i>", body_style)],
        [Paragraph("Log Sub-Hour Activity", body_style), Paragraph("<i>'Add workout for 45 minutes at 7:00'</i>", body_style)],
        [Paragraph("Clear Specific Activity", body_style), Paragraph("<i>'Remove the log at 8am 1 Hour deep work'</i>", body_style)],
        [Paragraph("Wipe / Reset Hour Slot", body_style), Paragraph("<i>'Clear hour 14'</i> or <i>'Delete activity at 2 PM'</i>", body_style)],
        [Paragraph("Stopwatch Control", body_style), Paragraph("<i>'Start stopwatch'</i>, <i>'Pause timer'</i>, or <i>'Reset stopwatch'</i>", body_style)],
        [Paragraph("View & Theme Switch", body_style), Paragraph("<i>'Switch to grid view'</i>, <i>'Turn on dark mode'</i>", body_style)],
        [Paragraph("Set Hourly Reminders", body_style), Paragraph("<i>'Remind me at 8:30 PM to review daily goals'</i>", body_style)],
        [Paragraph("Language Switch", body_style), Paragraph("<i>'Change language to Spanish'</i> or <i>'Set language to Hindi'</i>", body_style)],
    ]
    t_cmd = Table(cmd_data, colWidths=[2.5 * inch, 4.9 * inch])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F7')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t_cmd)
    elements.append(Spacer(1, 14))

    # Footer Notice
    footer_text = Paragraph(
        "<b>Habit Tracker OS v2.4.0</b> • Engineered by <b>Leoxur Inc.</b> • Confidential & Proprietary Document<br/>"
        "For enterprise support or deployment inquiries, visit repository: <b>github.com/leoxurDev/LeoxurHabitTracker</b>",
        ParagraphStyle(
            'Footer_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#86868B'),
            alignment=TA_CENTER
        )
    )
    elements.append(footer_text)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

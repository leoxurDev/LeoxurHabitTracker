import csv
import io
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from django.utils import timezone
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum, Q

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import HourlyLog, Category, SMTPSettings


# --- 1. Template CSV Generator & Parser ---

TEMPLATE_INSTRUCTIONS = """# ==============================================================================
# HABIT TRACKER - 24-HOUR BULK ACTIVITY IMPORT TEMPLATE
# ==============================================================================
# HOW TO FILL THIS SPREADSHEET:
# 1. Date: format YYYY-MM-DD (e.g. 2026-10-08). Defaults to today if left blank.
# 2. Hour: 0 to 23 representing the 24-hour slots (e.g. 9 = 9:00 AM, 14 = 2:00 PM).
# 3. Category: Match any category (Deep Work & Career, Health & Workout, Learning & Reading,
#              Mindfulness & Meditation, Sleep & Recovery, Social & Family, Leisure & Entertainment,
#              Chores & Errands, Nutrition & Meals) or type a new custom category.
# 4. Activity Title: Short summary of what you accomplished in this hour.
# 5. Duration Value: Numeric quantity (e.g. 1.0, 45, 90).
# 6. Unit: 'hours', 'minutes', or 'seconds'.
# 7. Energy Level: Integer between 1 and 5 (1 = lowest, 5 = peak focus/energy).
# 8. Notes: Optional reflections, obstacles, or insights.
# ==============================================================================
"""

def generate_activity_template_csv():
    """Generate CSV template with instructions and sample rows."""
    output = io.StringIO()
    output.write(TEMPLATE_INSTRUCTIONS)
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'Date', 'Hour', 'Category', 'Activity Title', 'Duration Value', 'Unit', 'Energy Level', 'Notes'
    ])

    today_str = timezone.localdate().strftime('%Y-%m-%d')
    # Sample rows
    writer.writerow([today_str, 7, 'Mindfulness & Meditation', 'Morning breathwork & hydration', 20, 'minutes', 5, 'Great start to the morning'])
    writer.writerow([today_str, 8, 'Health & Workout', 'Zone 2 running & core stretches', 45, 'minutes', 5, 'Outdoor session'])
    writer.writerow([today_str, 9, 'Nutrition & Meals', 'Healthy breakfast & espresso', 30, 'minutes', 4, 'High protein'])
    writer.writerow([today_str, 10, 'Deep Work & Career', 'Core system architecture & planning', 1.0, 'hours', 5, 'Undisturbed deep work'])
    writer.writerow([today_str, 11, 'Deep Work & Career', 'Feature implementation & tests', 1.0, 'hours', 5, 'High output flow'])
    writer.writerow([today_str, 14, 'Learning & Reading', 'Read 25 pages of Atomic Habits', 35, 'minutes', 4, 'Actionable notes taken'])
    writer.writerow([today_str, 22, 'Sleep & Recovery', 'Night wind-down & restorative sleep', 1.0, 'hours', 5, 'No screens 1hr prior'])

    return output.getvalue()


def process_bulk_upload_csv(user, file_obj):
    """
    Parse uploaded CSV file, validate rows, and bulk update/create HourlyLog entries.
    Returns: dict(success=True/False, imported_count=int, errors=[str])
    """
    imported_count = 0
    errors = []

    try:
        content = file_obj.read()
        if isinstance(content, bytes):
            # Decode UTF-8 with BOM or standard
            content = content.decode('utf-8-sig', errors='replace')
        
        lines = content.splitlines()
        csv_lines = [line for line in lines if not line.strip().startswith('#')]
        
        reader = csv.DictReader(csv_lines)
        if not reader.fieldnames:
            return {'success': False, 'imported_count': 0, 'errors': ['Spreadsheet contains no header columns.']}

        # Normalize field names
        field_map = {}
        for fn in reader.fieldnames:
            clean = fn.strip().lower()
            if 'date' in clean: field_map['date'] = fn
            elif 'hour' in clean: field_map['hour'] = fn
            elif 'cat' in clean: field_map['category'] = fn
            elif 'title' in clean or 'activity' in clean: field_map['title'] = fn
            elif 'duration' in clean or 'value' in clean: field_map['duration'] = fn
            elif 'unit' in clean: field_map['unit'] = fn
            elif 'energy' in clean: field_map['energy'] = fn
            elif 'note' in clean: field_map['notes'] = fn

        row_num = 0
        for row in reader:
            row_num += 1
            try:
                # 1. Date
                date_val = row.get(field_map.get('date', 'Date'), '').strip()
                if date_val:
                    try:
                        log_date = datetime.datetime.strptime(date_val, '%Y-%m-%d').date()
                    except ValueError:
                        log_date = timezone.localdate()
                else:
                    log_date = timezone.localdate()

                # 2. Hour
                hour_raw = row.get(field_map.get('hour', 'Hour'), '0').strip()
                try:
                    hour = int(float(hour_raw))
                    if hour < 0 or hour > 23:
                        errors.append(f"Row {row_num}: Hour must be 0-23 (got '{hour_raw}'). Skipped.")
                        continue
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid hour '{hour_raw}'. Skipped.")
                    continue

                # 3. Category
                cat_name = row.get(field_map.get('category', 'Category'), '').strip()
                category = None
                if cat_name:
                    category = Category.objects.filter(
                        Q(user=None) | Q(user=user),
                        name__iexact=cat_name
                    ).first()
                    if not category:
                        # Auto-create custom category for user
                        category = Category.objects.create(
                            user=user,
                            name=cat_name,
                            icon='🎯',
                            color='#0071E3',
                            is_productive=True
                        )

                # 4. Title
                title = row.get(field_map.get('title', 'Activity Title'), '').strip()
                if not title:
                    title = category.name if category else f"Hour {hour:02d}:00 Activity"

                # 5. Unit & Duration
                unit_type = row.get(field_map.get('unit', 'Unit'), 'hours').strip().lower()
                if unit_type not in ['hours', 'minutes', 'seconds']:
                    unit_type = 'hours'

                dur_raw = row.get(field_map.get('duration', 'Duration Value'), '1.0').strip()
                try:
                    dur_val = float(dur_raw)
                except ValueError:
                    dur_val = 1.0

                if unit_type == 'seconds':
                    duration_seconds = max(1, int(dur_val))
                elif unit_type == 'minutes':
                    duration_seconds = max(1, int(dur_val * 60))
                else:
                    duration_seconds = max(1, int(dur_val * 3600))

                # 6. Energy
                energy_raw = row.get(field_map.get('energy', 'Energy Level'), '4').strip()
                try:
                    energy = max(1, min(5, int(float(energy_raw))))
                except ValueError:
                    energy = 4

                # 7. Notes
                notes = row.get(field_map.get('notes', 'Notes'), '').strip()

                HourlyLog.objects.update_or_create(
                    user=user,
                    date=log_date,
                    hour=hour,
                    defaults={
                        'category': category,
                        'title': title,
                        'duration_seconds': duration_seconds,
                        'unit_type': unit_type,
                        'energy_level': energy,
                        'notes': notes,
                        'completed': True
                    }
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: Failed to import ({str(e)})")

        return {
            'success': True,
            'imported_count': imported_count,
            'errors': errors
        }
    except Exception as e:
        return {'success': False, 'imported_count': 0, 'errors': [f"Could not parse file: {str(e)}"]}


# --- 2. Analytics CSV Export ---

def generate_logs_csv(user, start_date, end_date):
    """Generate CSV containing all user logs within date range."""
    logs = HourlyLog.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('category').order_by('date', 'hour')

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Date', 'Hour (24h)', 'Hour (AM/PM)', 'Category', 'Activity Title',
        'Duration Display', 'Duration Seconds', 'Unit', 'Energy Level (1-5)', 'Notes'
    ])

    for log in logs:
        writer.writerow([
            log.date.strftime('%Y-%m-%d'),
            f"{log.hour:02d}:00",
            log.hour_formatted,
            log.category.name if log.category else 'General',
            log.title,
            log.duration_display,
            log.duration_seconds,
            log.unit_type,
            log.energy_level,
            log.notes
        ])

    return output.getvalue()


# --- 3. Apple-Standard PDF Report Generator (ReportLab) ---

def generate_analytics_pdf(user, start_date, end_date):
    """
    Build a PDF report with Apple typography, summary metrics,
    category distribution, and activity records.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Apple Palette Styles
    title_style = ParagraphStyle(
        'AppleTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1D1D1F'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'AppleSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#86868B'),
        spaceAfter=16
    )
    section_style = ParagraphStyle(
        'AppleSection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1D1D1F'),
        spaceBefore=14,
        spaceAfter=8
    )
    normal_style = ParagraphStyle(
        'AppleNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1D1D1F')
    )
    bold_style = ParagraphStyle(
        'AppleBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1D1D1F')
    )
    subtle_style = ParagraphStyle(
        'AppleSubtle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#6E6E73')
    )

    story = []

    # Title & Header
    story.append(Paragraph("Habit — Performance Report", title_style))
    range_str = f"{start_date.strftime('%B %d, %Y')} – {end_date.strftime('%B %d, %Y')}"
    user_name = user.first_name or user.username
    story.append(Paragraph(f"Prepared for <b>{user_name}</b> ({user.email or user.username}) • Range: {range_str}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E5EA'), spaceAfter=16))

    # Calculate Data
    logs = HourlyLog.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('category').order_by('date', 'hour')

    total_seconds = sum(l.duration_seconds for l in logs)
    total_hours = round(total_seconds / 3600.0, 1)
    
    num_days = max(1, (end_date - start_date).days + 1)
    daily_avg_hours = round(total_hours / num_days, 1)
    target = getattr(user.profile, 'daily_target_hours', 8.0) or 8.0
    completion_rate = min(100, int((daily_avg_hours / target) * 100)) if target > 0 else 0

    # 1. Executive Summary Table
    story.append(Paragraph("Executive Summary", section_style))
    summary_data = [
        [
            Paragraph("<b>Total Active Time</b>", normal_style),
            Paragraph("<b>Daily Average</b>", normal_style),
            Paragraph("<b>Daily Target</b>", normal_style),
            Paragraph("<b>Goal Rate</b>", normal_style),
            Paragraph("<b>Active Days</b>", normal_style),
        ],
        [
            Paragraph(f"<font size=13 color='#0071E3'><b>{total_hours}h</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#34C759'><b>{daily_avg_hours}h / day</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#1D1D1F'><b>{target}h</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#5856D6'><b>{completion_rate}%</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#FF9500'><b>{logs.values('date').distinct().count()} / {num_days}</b></font>", normal_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[105, 105, 100, 100, 105])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E5E5EA')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # 2. Category Distribution
    story.append(Paragraph("Category Distribution", section_style))
    category_counts = {}
    for l in logs:
        cname = l.category.name if l.category else 'General'
        category_counts[cname] = category_counts.get(cname, 0) + (l.duration_seconds / 3600.0)

    cat_rows = [
        [Paragraph("<b>Category</b>", bold_style), Paragraph("<b>Total Hours</b>", bold_style), Paragraph("<b>Share of Total</b>", bold_style)]
    ]
    for cname, chours in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        share_pct = round((chours / max(0.1, total_hours)) * 100, 1)
        cat_rows.append([
            Paragraph(cname, normal_style),
            Paragraph(f"{round(chours, 1)}h", normal_style),
            Paragraph(f"{share_pct}%", normal_style)
        ])

    if len(cat_rows) == 1:
        cat_rows.append([Paragraph("No activities recorded", subtle_style), Paragraph("0h", subtle_style), Paragraph("0%", subtle_style)])

    cat_table = Table(cat_rows, colWidths=[240, 135, 140])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F7')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 18))

    # 3. Activity Logs Listing (Latest up to 40 entries)
    story.append(Paragraph(f"Activity Records ({min(40, logs.count())} of {logs.count()} entries)", section_style))
    log_rows = [
        [
            Paragraph("<b>Date</b>", bold_style),
            Paragraph("<b>Hour</b>", bold_style),
            Paragraph("<b>Category</b>", bold_style),
            Paragraph("<b>Activity Title</b>", bold_style),
            Paragraph("<b>Duration</b>", bold_style),
        ]
    ]

    for log in logs[:40]:
        log_rows.append([
            Paragraph(log.date.strftime('%b %d'), subtle_style),
            Paragraph(log.hour_formatted, subtle_style),
            Paragraph(log.category.name if log.category else 'General', subtle_style),
            Paragraph(log.title[:35], normal_style),
            Paragraph(log.duration_display, bold_style),
        ])

    if len(log_rows) == 1:
        log_rows.append([Paragraph("No logs recorded", subtle_style), Paragraph("-", subtle_style), Paragraph("-", subtle_style), Paragraph("-", subtle_style), Paragraph("-", subtle_style)])

    log_table = Table(log_rows, colWidths=[70, 75, 120, 190, 60])
    log_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F7')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA')),
    ]))
    story.append(log_table)

    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated automatically on {timezone.localtime().strftime('%Y-%m-%d %I:%M %p')} • Habit 24-Hour System", subtle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- 4. SMTP Email Delivery ---

def send_analytics_email_report(user, recipient_email, start_date, end_date):
    """
    Send email report to recipient using user's configured SMTP settings
    (or Django system email backend).
    Attaches both CSV spreadsheet and PDF graphical report.
    """
    smtp_settings = getattr(user, 'smtp_settings', None)

    range_str = f"{start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}"
    subject = f"Habit Performance Report ({range_str})"

    # Generate documents
    csv_data = generate_logs_csv(user, start_date, end_date)
    pdf_data = generate_analytics_pdf(user, start_date, end_date)

    logs = HourlyLog.objects.filter(user=user, date__gte=start_date, date__lte=end_date)
    total_sec = sum(l.duration_seconds for l in logs)
    total_hours = round(total_sec / 3600.0, 1)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; background-color: #F5F5F7; color: #1D1D1F; margin: 0; padding: 24px; }}
        .card {{ background: #FFFFFF; border-radius: 16px; padding: 28px; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #E5E5EA; }}
        .header {{ border-bottom: 1px solid #E5E5EA; padding-bottom: 16px; margin-bottom: 20px; }}
        .title {{ font-size: 22px; font-weight: 700; color: #1D1D1F; margin: 0; }}
        .subtitle {{ font-size: 13px; color: #86868B; margin-top: 4px; }}
        .stats-grid {{ display: flex; gap: 12px; margin: 20px 0; }}
        .stat-box {{ flex: 1; background: #F5F5F7; padding: 12px 16px; border-radius: 10px; text-align: center; }}
        .stat-val {{ font-size: 20px; font-weight: 700; color: #0071E3; }}
        .stat-lbl {{ font-size: 11px; text-transform: uppercase; color: #86868B; margin-top: 4px; }}
        .footer {{ margin-top: 24px; font-size: 12px; color: #86868B; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1 class="title">Habit — Activity & Trend Report</h1>
          <div class="subtitle">{range_str} • Prepared for {user.first_name or user.username}</div>
        </div>
        <p style="font-size: 14.5px; line-height: 1.5; color: #3A3A3C;">
          Here is your comprehensive habit tracking intelligence report. Over this period, you logged <strong>{total_hours} total active hours</strong> across <strong>{logs.count()} hour slots</strong>.
        </p>
        <div style="background: #F9F9FA; padding: 16px; border-radius: 12px; border: 1px solid #E5E5EA; margin: 20px 0;">
          <div style="font-size: 13.5px; font-weight: 600; margin-bottom: 8px;">Attached in this email:</div>
          <div style="font-size: 13px; color: #3A3A3C; line-height: 1.6;">
            📄 <strong>habit_report_{start_date}_{end_date}.pdf</strong> — High-resolution graphical report with executive summaries and distribution tables.<br>
            📊 <strong>habit_activities_{start_date}_{end_date}.csv</strong> — Clean spreadsheet containing your granular hourly logs.
          </div>
        </div>
        <div class="footer">
          Habit • 24-Hour Time Canvas
        </div>
      </div>
    </body>
    </html>
    """

    sender_email = (smtp_settings.sender_email if smtp_settings and smtp_settings.sender_email else None) or "noreply@habit.local"

    # If user provided custom active SMTP settings, send directly via smtplib
    if smtp_settings and smtp_settings.is_active and smtp_settings.host and smtp_settings.username:
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = smtp_settings.sender_email or smtp_settings.username
        msg['To'] = recipient_email

        # HTML body
        msg_body = MIMEMultipart('alternative')
        msg_body.attach(MIMEText(html_content, 'html'))
        msg.attach(msg_body)

        # Attach CSV
        csv_attachment = MIMEApplication(csv_data.encode('utf-8'), Name=f"habit_activities_{start_date}_{end_date}.csv")
        csv_attachment['Content-Disposition'] = f'attachment; filename="habit_activities_{start_date}_{end_date}.csv"'
        msg.attach(csv_attachment)

        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_data, Name=f"habit_report_{start_date}_{end_date}.pdf")
        pdf_attachment['Content-Disposition'] = f'attachment; filename="habit_report_{start_date}_{end_date}.pdf"'
        msg.attach(pdf_attachment)

        # Connect
        if smtp_settings.use_ssl:
            server = smtplib.SMTP_SSL(smtp_settings.host, smtp_settings.port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_settings.host, smtp_settings.port, timeout=12)
            if smtp_settings.use_tls:
                server.starttls()

        server.login(smtp_settings.username, smtp_settings.password)
        server.send_message(msg)
        server.quit()
        return {'success': True, 'method': 'user_smtp'}

    else:
        # Fallback to Django EmailMessage (prints to console or uses default settings)
        email = EmailMultiAlternatives(
            subject=subject,
            body=f"Habit Activity Report for {range_str}. Attached is your CSV spreadsheet and PDF report.",
            from_email=sender_email,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.attach(f"habit_activities_{start_date}_{end_date}.csv", csv_data, 'text/csv')
        email.attach(f"habit_report_{start_date}_{end_date}.pdf", pdf_data, 'application/pdf')
        email.send(fail_silently=False)
        return {'success': True, 'method': 'system_mail'}


def test_smtp_configuration(host, port, username, password, use_tls, use_ssl, sender_email, recipient_email):
    """Test SMTP connection credentials by delivering a verification test message."""
    msg = MIMEText("Hello! This is a verification test email from your Habit Tracker system. Your SMTP settings are correctly configured.", "plain", "utf-8")
    msg['Subject'] = "Habit Tracker — SMTP Verification Test"
    msg['From'] = sender_email or username
    msg['To'] = recipient_email

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=10)
    else:
        server = smtplib.SMTP(host, port, timeout=10)
        if use_tls:
            server.starttls()

    if username and password:
        server.login(username, password)

    server.send_message(msg)
    server.quit()
    return True

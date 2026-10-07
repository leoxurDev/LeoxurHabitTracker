import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count, Q

from .models import UserProfile, Category, HourlyLog, Reminder, ChatMessage, SMTPSettings, GOAL_CHOICES
from .quotes import get_quote_for_goal, MOTIVATIONAL_QUOTES
from .assistant import HabitAIAssistant
from .utils import ensure_default_categories, calculate_streak


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        primary_goal = request.POST.get('primary_goal', 'focus')
        target_hours = float(request.POST.get('daily_target_hours', 8.0) or 8.0)

        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'tracker/register.html', {'goal_choices': GOAL_CHOICES})

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'tracker/register.html', {'goal_choices': GOAL_CHOICES})

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please pick another.')
            return render(request, 'tracker/register.html', {'goal_choices': GOAL_CHOICES})

        user = User.objects.create_user(username=username, email=email, password=password)
        profile = user.profile
        profile.primary_goal = primary_goal
        profile.daily_target_hours = target_hours
        profile.save()

        ensure_default_categories()

        # Create a welcome reminder
        Reminder.objects.create(
            user=user,
            title="Log today's final habits & review",
            time=datetime.time(21, 0),
            is_active=True
        )

        login(request, user)
        messages.success(request, f'Welcome to your iOS Habit Tracker, {username}!')
        return redirect('dashboard')

    return render(request, 'tracker/register.html', {'goal_choices': GOAL_CHOICES})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Check if demo login button was clicked
        if 'demo_login' in request.POST:
            demo_user, created = User.objects.get_or_create(username='demo_apple_user')
            if created:
                demo_user.set_password('demo1234')
                demo_user.first_name = 'Alex'
                demo_user.save()
                demo_user.profile.primary_goal = 'focus'
                demo_user.profile.daily_target_hours = 8.0
                demo_user.profile.save()
                ensure_default_categories()
                _seed_demo_logs(demo_user)
            login(request, demo_user)
            messages.success(request, 'Welcome to the Apple-inspired demo experience!')
            return redirect('dashboard')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'tracker/login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been safely signed out.')
    return redirect('login')


def _seed_demo_logs(user):
    """Seed sample hours for the demo user today so it looks rich right away."""
    today = timezone.localdate()
    ensure_default_categories()

    work_cat = Category.objects.filter(name__icontains='Deep Work').first()
    fitness_cat = Category.objects.filter(name__icontains='Health').first()
    learn_cat = Category.objects.filter(name__icontains='Learning').first()
    mind_cat = Category.objects.filter(name__icontains='Mindfulness').first()
    sleep_cat = Category.objects.filter(name__icontains='Sleep').first()
    meals_cat = Category.objects.filter(name__icontains='Nutrition').first()

    samples = [
        (0, sleep_cat, "Deep restorative sleep", 3600, 'hours', 5),
        (1, sleep_cat, "Restorative sleep", 3600, 'hours', 5),
        (2, sleep_cat, "Restorative sleep", 3600, 'hours', 5),
        (3, sleep_cat, "Restorative sleep", 3600, 'hours', 5),
        (4, sleep_cat, "Restorative sleep", 3600, 'hours', 5),
        (5, sleep_cat, "Restorative sleep", 3600, 'hours', 5),
        (6, sleep_cat, "Waking up & natural light exposure", 3600, 'hours', 4),
        (7, mind_cat, "Morning meditation & hydration", 1200, 'minutes', 5),
        (8, fitness_cat, "Zone 2 morning run & stretches", 2700, 'minutes', 5),
        (9, meals_cat, "High-protein breakfast & coffee", 1800, 'minutes', 4),
        (10, work_cat, "Deep Work: Architecture & clean design", 3600, 'hours', 5),
        (11, work_cat, "Deep Work: Core system coding", 3600, 'hours', 5),
        (14, learn_cat, "Reading Atomic Habits & tech docs", 2400, 'minutes', 4),
    ]

    for hour, cat, title, sec, unit, energy in samples:
        HourlyLog.objects.update_or_create(
            user=user,
            date=today,
            hour=hour,
            defaults={
                'category': cat,
                'title': title,
                'duration_seconds': sec,
                'unit_type': unit,
                'energy_level': energy,
                'completed': True,
            }
        )


@login_required
def dashboard_view(request):
    ensure_default_categories()
    user = request.user
    profile = user.profile

    # Update streak
    profile.streak_count = max(1, calculate_streak(user))
    profile.save(update_fields=['streak_count'])

    # Date handling
    date_str = request.GET.get('date')
    if date_str:
        try:
            current_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.localdate()
    else:
        current_date = timezone.localdate()

    today = timezone.localdate()
    prev_date = current_date - datetime.timedelta(days=1)
    next_date = current_date + datetime.timedelta(days=1)

    # Categories available to user (defaults + user created)
    categories = Category.objects.filter(Q(user=None) | Q(user=user))

    # Retrieve 24 hourly logs for the selected date
    logs = HourlyLog.objects.filter(user=user, date=current_date).select_related('category')
    logs_by_hour = {log.hour: log for log in logs}

    # Build 24-hour slots structure
    timeline_hours = []
    current_system_hour = timezone.localtime().hour if current_date == today else -1

    total_logged_seconds = 0
    productive_seconds = 0
    deep_work_seconds = 0
    health_seconds = 0
    mindfulness_seconds = 0

    for h in range(24):
        log = logs_by_hour.get(h)
        period = "AM" if h < 12 else "PM"
        display_h = 12 if h % 12 == 0 else h % 12
        hour_label = f"{display_h:02d}:00 {period}"
        hour_24 = f"{h:02d}:00"

        if log:
            total_logged_seconds += log.duration_seconds
            if log.category:
                if log.category.is_productive:
                    productive_seconds += log.duration_seconds
                c_name = log.category.name.lower()
                if 'work' in c_name or 'career' in c_name or 'code' in c_name:
                    deep_work_seconds += log.duration_seconds
                elif 'health' in c_name or 'workout' in c_name or 'fitness' in c_name:
                    health_seconds += log.duration_seconds
                elif 'mind' in c_name or 'meditat' in c_name or 'sleep' in c_name or 'learning' in c_name:
                    mindfulness_seconds += log.duration_seconds

        timeline_hours.append({
            'hour': h,
            'label': hour_label,
            'label_24': hour_24,
            'is_current': (h == current_system_hour),
            'log': log,
        })

    # Duration aggregations
    total_hours = round(total_logged_seconds / 3600.0, 1)
    target_hours = profile.daily_target_hours or 8.0
    progress_pct = min(100, int((total_hours / target_hours) * 100)) if target_hours > 0 else 0

    # Apple Activity Rings percentage calculations (0 to 100)
    # Ring 1 (Red / Coral): Overall Daily Activity Target
    ring_move_pct = min(100, int((total_hours / target_hours) * 100)) if target_hours > 0 else 0

    # Ring 2 (Green): Health & Vitality (Target: 1.5h = 5400s)
    ring_health_pct = min(100, int((health_seconds / 5400.0) * 100))

    # Ring 3 (Blue / Cyan): Deep Focus & Mastery (Target: 4.0h = 14400s)
    ring_focus_pct = min(100, int((deep_work_seconds / 14400.0) * 100))

    # Motivational quote
    quote_data = get_quote_for_goal(profile.primary_goal)

    # Active Reminders
    reminders = Reminder.objects.filter(user=user, is_active=True)

    # Chat history (last 10 messages)
    chat_history = ChatMessage.objects.filter(user=user).order_by('-timestamp')[:10]
    chat_history = reversed(list(chat_history))

    context = {
        'profile': profile,
        'current_date': current_date,
        'today': today,
        'is_today': (current_date == today),
        'prev_date': prev_date,
        'next_date': next_date,
        'timeline_hours': timeline_hours,
        'categories': categories,
        'total_hours': total_hours,
        'target_hours': target_hours,
        'progress_pct': progress_pct,
        'ring_move_pct': ring_move_pct,
        'ring_health_pct': ring_health_pct,
        'ring_focus_pct': ring_focus_pct,
        'deep_work_hours': round(deep_work_seconds / 3600.0, 1),
        'health_hours': round(health_seconds / 3600.0, 1),
        'mindfulness_hours': round(mindfulness_seconds / 3600.0, 1),
        'quote': quote_data,
        'reminders': reminders,
        'chat_history': chat_history,
        'goal_choices': GOAL_CHOICES,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
@require_POST
def api_log_hour(request):
    """
    Ajax endpoint to add or update an hourly activity.
    Supports units in hours, minutes, or seconds!
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    date_str = data.get('date')
    hour = int(data.get('hour', 0))
    title = data.get('title', '').strip()
    category_id = data.get('category_id')
    unit_type = data.get('unit_type', 'hours')
    duration_val = float(data.get('duration_value', 1.0) or 1.0)
    notes = data.get('notes', '').strip()
    energy_level = int(data.get('energy_level', 4) or 4)

    if not date_str:
        log_date = timezone.localdate()
    else:
        try:
            log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            log_date = timezone.localdate()

    # Calculate exact duration in seconds
    if unit_type == 'seconds':
        duration_seconds = max(1, int(duration_val))
    elif unit_type == 'minutes':
        duration_seconds = max(1, int(duration_val * 60))
    else: # hours
        duration_seconds = max(1, int(duration_val * 3600))

    category = None
    if category_id:
        category = Category.objects.filter(id=category_id).first()

    # If title is empty and user provided category, use category name
    if not title:
        title = category.name if category else f"Hour {hour:02d}:00 Activity"

    log, created = HourlyLog.objects.update_or_create(
        user=request.user,
        date=log_date,
        hour=hour,
        defaults={
            'title': title,
            'category': category,
            'duration_seconds': duration_seconds,
            'unit_type': unit_type,
            'notes': notes,
            'energy_level': energy_level,
            'completed': True
        }
    )

    return JsonResponse({
        'status': 'success',
        'created': created,
        'log': {
            'id': log.id,
            'hour': log.hour,
            'title': log.title,
            'category_name': category.name if category else '',
            'category_icon': category.icon if category else '💼',
            'category_color': category.color if category else '#007AFF',
            'duration_display': log.duration_display,
            'duration_seconds': log.duration_seconds,
            'unit_type': log.unit_type,
            'notes': log.notes,
            'energy_level': log.energy_level,
        }
    })


@login_required
@require_POST
def api_delete_hour(request):
    """Delete an hourly log."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    date_str = data.get('date')
    hour = int(data.get('hour', 0))

    try:
        log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        log_date = timezone.localdate()

    HourlyLog.objects.filter(user=request.user, date=log_date, hour=hour).delete()
    return JsonResponse({'status': 'success', 'hour': hour})


@login_required
def api_get_quote(request):
    """Return a fresh motivational quote tailored to user's goal."""
    goal = request.user.profile.primary_goal
    quote = get_quote_for_goal(goal)
    return JsonResponse({'status': 'success', 'quote': quote})


@login_required
@require_POST
def api_chat(request):
    """
    AI Assistant chat endpoint.
    Handles conversation, natural language commands, status requests and reminder scheduling.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    user_message = data.get('message', '').strip()
    if not user_message:
        return JsonResponse({'status': 'error', 'message': 'Message cannot be empty.'}, status=400)

    # Save user message to DB
    ChatMessage.objects.create(
        user=request.user,
        sender='user',
        message=user_message
    )

    # Process via AI Assistant
    assistant = HabitAIAssistant(request.user)
    response_data = assistant.process_message(user_message)

    # Save assistant message to DB
    ChatMessage.objects.create(
        user=request.user,
        sender='assistant',
        message=response_data['reply'],
        action_type=response_data.get('action_type')
    )

    return JsonResponse({
        'status': 'success',
        'reply': response_data['reply'],
        'action_type': response_data.get('action_type'),
        'payload': response_data.get('payload', {}),
        'timestamp': timezone.localtime().strftime('%I:%M %p')
    })


@login_required
def api_reminders(request):
    """List or create reminders."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        title = data.get('title', '').strip() or "Log hourly activity"
        time_str = data.get('time', '').strip()
        try:
            reminder_time = datetime.datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            reminder_time = timezone.localtime().time()

        reminder = Reminder.objects.create(
            user=request.user,
            title=title,
            time=reminder_time,
            is_active=True
        )
        return JsonResponse({
            'status': 'success',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'time': reminder.time.strftime('%H:%M'),
                'time_display': reminder.time.strftime('%I:%M %p'),
                'is_active': reminder.is_active
            }
        })

    # GET
    reminders = Reminder.objects.filter(user=request.user)
    reminders_data = [{
        'id': r.id,
        'title': r.title,
        'time': r.time.strftime('%H:%M'),
        'time_display': r.time.strftime('%I:%M %p'),
        'is_active': r.is_active
    } for r in reminders]
    return JsonResponse({'status': 'success', 'reminders': reminders_data})


@login_required
@require_POST
def api_toggle_reminder(request, reminder_id):
    """Toggle reminder active state."""
    reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
    reminder.is_active = not reminder.is_active
    reminder.save(update_fields=['is_active'])
    return JsonResponse({'status': 'success', 'is_active': reminder.is_active})


@login_required
@require_POST
def api_delete_reminder(request, reminder_id):
    """Delete a reminder."""
    reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
    reminder.delete()
    return JsonResponse({'status': 'success'})


@login_required
def api_check_due_reminders(request):
    """
    Checks if any active reminder is due right now (within current 2-minute window).
    Used by the frontend to pop an iOS audio/visual alert.
    """
    now = timezone.localtime()
    current_time = now.time()
    # Check within current hour and minute
    due = Reminder.objects.filter(
        user=request.user,
        is_active=True,
        time__hour=current_time.hour,
        time__minute=current_time.minute
    )
    results = [{
        'id': r.id,
        'title': r.title,
        'time_display': r.time.strftime('%I:%M %p')
    } for r in due]
    return JsonResponse({'status': 'success', 'due_reminders': results})


def download_template_view(request):
    """Download the spreadsheet template with instructions and sample rows."""
    from .reports import generate_activity_template_csv
    csv_content = generate_activity_template_csv()
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="habit_activity_template.csv"'
    return response


@login_required
@require_POST
def bulk_upload_view(request):
    """Process uploaded CSV spreadsheet to bulk create or update hourly logs."""
    from .reports import process_bulk_upload_csv
    if 'file' not in request.FILES:
        messages.error(request, 'Please select a spreadsheet file (.csv) to upload.')
        return redirect('dashboard')

    file_obj = request.FILES['file']
    result = process_bulk_upload_csv(request.user, file_obj)

    if result['success']:
        msg = f"Successfully imported {result['imported_count']} activities from spreadsheet!"
        if result['errors']:
            msg += f" ({len(result['errors'])} warnings/skipped rows)"
        messages.success(request, msg)
    else:
        messages.error(request, f"Spreadsheet upload failed: {', '.join(result['errors'][:2])}")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(result)
    return redirect('dashboard')


@login_required
def analytics_view(request):
    """
    Visual breakdown of user's habits, categories, rhythm heat map,
    and custom date ranges up to 90 days.
    """
    user = request.user
    today = timezone.localdate()

    range_param = request.GET.get('range', '7')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Determine date range (max 90 days)
    if range_param == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            # Limit to 90 days
            if (end_date - start_date).days > 90:
                end_date = start_date + datetime.timedelta(days=90)
        except ValueError:
            start_date = today - datetime.timedelta(days=6)
            end_date = today
    else:
        try:
            days_count = int(range_param)
            days_count = max(1, min(90, days_count))
        except ValueError:
            days_count = 7
        start_date = today - datetime.timedelta(days=days_count - 1)
        end_date = today

    total_days = max(1, (end_date - start_date).days + 1)

    # Logs for the selected date range
    range_logs = HourlyLog.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('category').order_by('date', 'hour')

    # Daily Stats
    daily_stats = []
    days_met_target = 0
    target_hours = user.profile.daily_target_hours or 8.0

    for i in range(total_days):
        d = start_date + datetime.timedelta(days=i)
        day_logs = [l for l in range_logs if l.date == d]
        total_sec = sum(l.duration_seconds for l in day_logs)
        hrs = round(total_sec / 3600.0, 1)
        if hrs >= target_hours:
            days_met_target += 1
        daily_stats.append({
            'date': d,
            'label': d.strftime('%a'),
            'date_formatted': d.strftime('%b %d'),
            'hours': hrs,
            'slots': len(day_logs),
            'is_today': (d == today)
        })

    # Category Breakdown across range
    category_totals = {}
    hourly_rhythm = [0] * 24  # Counts for hour 0-23
    for l in range_logs:
        cname = l.category.name if l.category else 'General'
        color = l.category.color if l.category else '#0071E3'
        icon = l.category.icon if l.category else '💼'
        if cname not in category_totals:
            category_totals[cname] = {'name': cname, 'seconds': 0, 'color': color, 'icon': icon}
        category_totals[cname]['seconds'] += l.duration_seconds

        if 0 <= l.hour <= 23:
            hourly_rhythm[l.hour] += round(l.duration_seconds / 3600.0, 1)

    category_list = []
    total_range_seconds = sum(c['seconds'] for c in category_totals.values()) or 1
    total_range_hours = round(total_range_seconds / 3600.0, 1)

    for k, v in sorted(category_totals.items(), key=lambda x: x[1]['seconds'], reverse=True):
        hrs = round(v['seconds'] / 3600.0, 1)
        pct = round((v['seconds'] / total_range_seconds) * 100, 1)
        category_list.append({
            'name': v['name'],
            'hours': hrs,
            'percentage': pct,
            'color': v['color'],
            'icon': v['icon'],
        })

    daily_avg_hours = round(total_range_hours / total_days, 1)
    target_completion_pct = min(100, int((daily_avg_hours / target_hours) * 100)) if target_hours > 0 else 0

    # Hourly Rhythm objects for chart
    rhythm_stats = []
    max_rhythm = max(hourly_rhythm) or 1
    for h in range(24):
        period = "AM" if h < 12 else "PM"
        disp_h = 12 if h % 12 == 0 else h % 12
        rhythm_stats.append({
            'hour': h,
            'label': f"{disp_h}{period}",
            'hours_spent': round(hourly_rhythm[h], 1),
            'height_pct': min(100, int((hourly_rhythm[h] / max_rhythm) * 100)) if max_rhythm > 0 else 0
        })

    smtp_settings, _ = SMTPSettings.objects.get_or_create(user=user)

    context = {
        'daily_stats': daily_stats,
        'category_list': category_list,
        'rhythm_stats': rhythm_stats,
        'total_range_hours': total_range_hours,
        'daily_avg_hours': daily_avg_hours,
        'days_met_target': days_met_target,
        'total_days': total_days,
        'target_completion_pct': target_completion_pct,
        'streak_count': user.profile.streak_count,
        'target_hours': target_hours,
        'profile': user.profile,
        'start_date': start_date,
        'end_date': end_date,
        'range_param': str(range_param),
        'smtp_configured': bool(smtp_settings.is_active and smtp_settings.host),
    }
    return render(request, 'tracker/analytics.html', context)


@login_required
def export_analytics_csv_view(request):
    """Download CSV export of logs for selected date range."""
    from .reports import generate_logs_csv
    user = request.user
    today = timezone.localdate()

    range_param = request.GET.get('range', '7')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - datetime.timedelta(days=6)
            end_date = today
    else:
        try:
            days = min(90, max(1, int(range_param)))
        except ValueError:
            days = 7
        start_date = today - datetime.timedelta(days=days - 1)
        end_date = today

    csv_data = generate_logs_csv(user, start_date, end_date)
    response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="habit_logs_{start_date}_{end_date}.csv"'
    return response


@login_required
def export_analytics_pdf_view(request):
    """Download PDF report with summary and charts for selected date range."""
    from .reports import generate_analytics_pdf
    user = request.user
    today = timezone.localdate()

    range_param = request.GET.get('range', '7')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - datetime.timedelta(days=6)
            end_date = today
    else:
        try:
            days = min(90, max(1, int(range_param)))
        except ValueError:
            days = 7
        start_date = today - datetime.timedelta(days=days - 1)
        end_date = today

    pdf_data = generate_analytics_pdf(user, start_date, end_date)
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="habit_report_{start_date}_{end_date}.pdf"'
    return response


@login_required
@require_POST
def share_email_report_view(request):
    """Email report to user with CSV spreadsheet and PDF graphical report attached."""
    from .reports import send_analytics_email_report
    user = request.user
    today = timezone.localdate()

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    recipient_email = data.get('recipient_email', '').strip() or user.email
    if not recipient_email:
        return JsonResponse({'status': 'error', 'message': 'Please provide recipient email address.'}, status=400)

    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    range_param = data.get('range', '7')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - datetime.timedelta(days=6)
            end_date = today
    else:
        try:
            days = min(90, max(1, int(range_param)))
        except ValueError:
            days = 7
        start_date = today - datetime.timedelta(days=days - 1)
        end_date = today

    try:
        res = send_analytics_email_report(user, recipient_email, start_date, end_date)
        return JsonResponse({
            'status': 'success',
            'message': f"Report successfully dispatched to {recipient_email} with CSV and PDF attached!",
            'method': res['method']
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f"Failed to deliver email: {str(e)}"
        }, status=500)


@login_required
@require_POST
def api_test_smtp(request):
    """Test SMTP connection and credentials."""
    from .reports import test_smtp_configuration
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    host = data.get('host', '').strip()
    port = int(data.get('port', 587) or 587)
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    use_tls = bool(data.get('use_tls', True))
    use_ssl = bool(data.get('use_ssl', False))
    sender_email = data.get('sender_email', '').strip() or username
    recipient_email = data.get('recipient_email', '').strip() or request.user.email or username

    if not host or not recipient_email:
        return JsonResponse({'status': 'error', 'message': 'Host and recipient email are required.'}, status=400)

    try:
        test_smtp_configuration(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            use_ssl=use_ssl,
            sender_email=sender_email,
            recipient_email=recipient_email
        )
        return JsonResponse({'status': 'success', 'message': f'SMTP verified! Test message sent to {recipient_email}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'SMTP Connection Failed: {str(e)}'}, status=400)


@login_required
def settings_view(request):
    """User profile, SMTP email host configuration, and habit preferences."""
    profile = request.user.profile
    smtp_settings, _ = SMTPSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', 'profile')

        if action == 'smtp':
            # Save SMTP configuration
            smtp_settings.host = request.POST.get('smtp_host', 'smtp.gmail.com').strip()
            try:
                smtp_settings.port = int(request.POST.get('smtp_port', 587))
            except ValueError:
                smtp_settings.port = 587
            smtp_settings.username = request.POST.get('smtp_username', '').strip()
            pwd = request.POST.get('smtp_password', '')
            if pwd:
                smtp_settings.password = pwd
            smtp_settings.sender_email = request.POST.get('smtp_sender_email', '').strip()
            smtp_settings.use_tls = 'smtp_use_tls' in request.POST
            smtp_settings.use_ssl = 'smtp_use_ssl' in request.POST
            smtp_settings.is_active = 'smtp_is_active' in request.POST
            smtp_settings.save()
            messages.success(request, 'SMTP Email Configuration saved successfully!')
            return redirect('settings')

        else:
            # Save profile preferences
            profile.primary_goal = request.POST.get('primary_goal', profile.primary_goal)
            try:
                profile.daily_target_hours = float(request.POST.get('daily_target_hours', profile.daily_target_hours))
            except ValueError:
                pass
            profile.bio_motto = request.POST.get('bio_motto', profile.bio_motto).strip()
            profile.theme = request.POST.get('theme', profile.theme)
            profile.avatar_color = request.POST.get('avatar_color', profile.avatar_color)
            profile.notifications_enabled = 'notifications_enabled' in request.POST
            profile.save()

            first_name = request.POST.get('first_name', '').strip()
            email = request.POST.get('email', '').strip()
            if first_name:
                request.user.first_name = first_name
            if email:
                request.user.email = email
            request.user.save()

            messages.success(request, 'Preferences have been updated!')
            return redirect('settings')

    categories = Category.objects.filter(Q(user=None) | Q(user=request.user))
    context = {
        'profile': profile,
        'smtp_settings': smtp_settings,
        'goal_choices': GOAL_CHOICES,
        'categories': categories,
    }
    return render(request, 'tracker/settings.html', context)


@login_required
@require_POST
def api_add_custom_category(request):
    """Allow user to create their own custom category with icon and color."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    name = data.get('name', '').strip()
    icon = data.get('icon', '🎯').strip()
    color = data.get('color', '#0071E3').strip()
    is_productive = data.get('is_productive', True)

    if not name:
        return JsonResponse({'status': 'error', 'message': 'Category name required'}, status=400)

    cat = Category.objects.create(
        user=request.user,
        name=name,
        icon=icon,
        color=color,
        is_productive=is_productive
    )
    return JsonResponse({
        'status': 'success',
        'category': {
            'id': cat.id,
            'name': cat.name,
            'icon': cat.icon,
            'color': cat.color,
        }
    })

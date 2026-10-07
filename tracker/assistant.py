import re
import datetime
from django.utils import timezone
from .models import HourlyLog, Reminder, Category, UserProfile
from .quotes import get_quote_for_goal


class HabitAIAssistant:
    """
    Intelligent Assistant Engine modeled after iOS Siri / Apple Intelligence.
    Provides context-aware help, day analysis, reminder creation, and habit coaching.
    """

    def __init__(self, user):
        self.user = user
        self.profile = getattr(user, 'profile', None)

    def process_message(self, user_text):
        """
        Analyze user query and return a structured response dictionary:
        {
            'reply': str,
            'action_type': str,
            'payload': dict (optional extra data, e.g. newly created reminder)
        }
        """
        text = user_text.strip().lower()

        # 1. Check for reminder creation commands
        # Examples: "remind me at 20:00 to review my day", "set reminder at 9:30 am", "remind me at 10 pm"
        reminder_match = re.search(r'(?:remind\s+me|set\s+reminder|add\s+reminder)(?:\s+at|\s+for)?\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+to\s+(.+))?', text)
        if reminder_match:
            time_str = reminder_match.group(1).strip()
            task_title = reminder_match.group(2) or "Log habits and hourly activities"
            reminder_obj = self._create_reminder_from_text(time_str, task_title)
            if reminder_obj:
                return {
                    'reply': f"I've scheduled a reminder for you at **{reminder_obj.time.strftime('%I:%M %p')}**: *\"{reminder_obj.title}\"*. You'll receive an in-app alert and chime at that time!",
                    'action_type': 'set_reminder',
                    'payload': {
                        'id': reminder_obj.id,
                        'title': reminder_obj.title,
                        'time': reminder_obj.time.strftime('%H:%M'),
                        'time_display': reminder_obj.time.strftime('%I:%M %p')
                    }
                }

        # 2. Status / Progress / Daily breakdown requests
        if any(k in text for k in ['status', 'how am i doing', 'progress', 'summary', 'today', 'analysis', 'stats', 'score']):
            return self._generate_status_report()

        # 3. How to use / Tutorial / Help
        if any(k in text for k in ['how to use', 'help', 'guide', 'tutorial', 'instructions', 'walkthrough', 'feature']):
            return self._generate_help_guide()

        # 4. Motivation / Quote / Boost
        if any(k in text for k in ['motivat', 'quote', 'inspire', 'lazy', 'tired', 'boost', 'energy', 'focus tip']):
            goal = self.profile.primary_goal if self.profile else 'focus'
            quote_data = get_quote_for_goal(goal)
            return {
                'reply': f"✨ **Daily Inspiration for {self.profile.get_goal_display_text() if self.profile else 'You'}:**\n\n> \"{quote_data['quote']}\"\n> — *{quote_data['author']}* ({quote_data['tag']})\n\nRemember: even logging 15 minutes of conscious action triggers dopamine and builds compound momentum today!",
                'action_type': 'motivation',
                'payload': quote_data
            }

        # 5. Question about units (hours, minutes, seconds)
        if any(k in text for k in ['second', 'minute', 'hour', 'duration', 'unit', 'stopwatch', 'timer']):
            return {
                'reply': "⏱️ **Tracking with Precision:**\n\n"
                         "• **Hours**: Ideal for deep work, full lecture sessions, or sleep blocks.\n"
                         "• **Minutes**: Great for quick workouts (e.g. 45m), meditation (15m), or pomodoros.\n"
                         "• **Seconds**: Perfect for micro-habits (e.g. 90s cold shower, 120s plank) or live stopwatch tracking.\n\n"
                         "You can use the **Quick Add modal** or tap any hour cell to set precise units. The built-in **Live Stopwatch** in the top bar logs exact seconds automatically!",
                'action_type': 'guide',
                'payload': {}
            }

        # 6. Questions about categories
        if any(k in text for k in ['category', 'categories', 'color', 'icon']):
            return {
                'reply': "🎨 **Activity Categories:**\n\n"
                         "Your hours are color-coded to visualize your day in Apple iOS style:\n"
                         "• 💼 **Deep Work** (Blue)\n"
                         "• 🏃‍♂️ **Health & Workout** (Green)\n"
                         "• 📚 **Learning & Reading** (Purple)\n"
                         "• 🧘‍♀️ **Mindfulness** (Indigo)\n"
                         "• 🌙 **Sleep & Recovery** (Teal)\n"
                         "• 👥 **Social & Family** (Orange)\n"
                         "• 🎮 **Leisure** (Rose)\n"
                         "• 🧺 **Chores** (Gray)\n\n"
                         "You can also create custom categories under Settings!",
                'action_type': 'guide',
                'payload': {}
            }

        # 7. Default intelligent response with context & options
        today = timezone.localdate()
        logged_count = HourlyLog.objects.filter(user=self.user, date=today).count()
        greeting_name = self.user.first_name or self.user.username

        return {
            'reply': f"Hello {greeting_name}! I'm your **Habit & Time Assistant**.\n\n"
                     f"Today you have logged **{logged_count} of 24 hours**.\n\n"
                     f"Here are a few things I can assist you with:\n"
                     f"• Ask **\"Show my status\"** for today's hourly summary & productivity score.\n"
                     f"• Say **\"Remind me at 9:00 PM to log my day\"** to create an audio/visual reminder.\n"
                     f"• Ask **\"How do I use this app?\"** for the quick iOS walkthrough.\n"
                     f"• Ask **\"Give me motivation\"** for a tailored quote based on your goal (*{self.profile.get_goal_display_text() if self.profile else 'Focus'}*).\n"
                     f"• Ask **\"How to track in seconds/minutes\"** to master precision tracking.",
            'action_type': 'general',
            'payload': {}
        }

    def _generate_status_report(self):
        today = timezone.localdate()
        logs = HourlyLog.objects.filter(user=self.user, date=today)
        total_seconds = sum(log.duration_seconds for log in logs)
        total_hours = round(total_seconds / 3600.0, 1)

        target = self.profile.daily_target_hours if self.profile else 8.0
        pct = min(100, int((total_hours / target) * 100)) if target > 0 else 0

        # Category breakdown
        cat_counts = {}
        for l in logs:
            cname = l.category.name if l.category else 'General'
            cat_counts[cname] = cat_counts.get(cname, 0) + (l.duration_seconds / 3600.0)

        cat_summary = ", ".join([f"{k}: {round(v, 1)}h" for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]]) or "No categories logged yet"

        current_hour = timezone.localtime().hour
        period_name = "morning" if current_hour < 12 else "afternoon" if current_hour < 18 else "evening"

        reply = (
            f"📊 **Your Daily Status Report ({today.strftime('%A, %b %d')}):**\n\n"
            f"• **Logged Hours**: {logs.count()} slots filled ({total_hours}h total active duration)\n"
            f"• **Daily Target Progress**: {total_hours}h / {target}h (**{pct}% complete**)\n"
            f"• **Top Activities**: {cat_summary}\n"
            f"• **Current Streak**: 🔥 {self.profile.streak_count if self.profile else 1} Days\n\n"
            f"💡 **Tip for this {period_name}**: "
            + (f"Great momentum! Keep logging your consecutive hours." if pct >= 50 else f"You have {round(target - total_hours, 1)}h remaining toward your target. Add an entry for hour {current_hour:02d}:00!")
        )

        return {
            'reply': reply,
            'action_type': 'status_check',
            'payload': {
                'total_hours': total_hours,
                'target_hours': target,
                'percentage': pct,
                'slots_logged': logs.count()
            }
        }

    def _generate_help_guide(self):
        return {
            'reply': "📱 **Welcome to Habit Tracker - Apple iOS Edition!**\n\n"
                     "Here is how to get the most out of your 24-hour day:\n\n"
                     "1️⃣ **24-Hour Timeline Grid**:\n"
                     "Scroll down the timeline representing all 24 hours (00:00 to 23:00). Tap any cell to log your activity for that exact hour.\n\n"
                     "2️⃣ **Flexible Units (Hours, Minutes, Seconds)**:\n"
                     "Choose your unit when logging! You can log 45 minutes of workout, 1 hour of deep work, or 90 seconds of breathing exercises.\n\n"
                     "3️⃣ **Live Stopwatch Widget**:\n"
                     "Tap **Start Timer** at the top right to time an active session. When you hit **Save**, it automatically logs the recorded seconds to the current hour slot!\n\n"
                     "4️⃣ **Interactive Apple Activity Rings**:\n"
                     "Watch your Deep Work, Health, and Balance rings close as you fill your 24 hours.\n\n"
                     "5️⃣ **Reminders & Alerts**:\n"
                     "Enable notifications to get subtle iOS-style chimes prompting you to log your hours throughout the day.\n\n"
                     "6️⃣ **AI Assistant (Me!)**:\n"
                     "Chat with me anytime to see your status, schedule reminders, or get an instant motivational boost!",
            'action_type': 'guide',
            'payload': {}
        }

    def _create_reminder_from_text(self, time_str, title):
        """Parse natural time strings like '9 pm', '21:00', '09:30 AM'"""
        parsed_time = None
        time_str = time_str.strip().upper()

        # Try various formats
        formats = ['%I:%M %p', '%I %p', '%I:%M%p', '%I%p', '%H:%M', '%H']
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                parsed_time = dt.time()
                break
            except ValueError:
                continue

        if not parsed_time:
            # Fallback regex parsing
            m = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?', time_str)
            if m:
                h = int(m.group(1))
                minute = int(m.group(2)) if m.group(2) else 0
                meridiem = m.group(3)
                if meridiem == 'PM' and h < 12:
                    h += 12
                elif meridiem == 'AM' and h == 12:
                    h = 0
                if 0 <= h <= 23 and 0 <= minute <= 59:
                    parsed_time = datetime.time(h, minute)

        if not parsed_time:
            parsed_time = datetime.time(20, 0)  # Default 8 PM

        clean_title = title.strip().capitalize() if title else "Update daily habits"
        reminder = Reminder.objects.create(
            user=self.user,
            title=clean_title,
            time=parsed_time,
            is_active=True
        )
        return reminder

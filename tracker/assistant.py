import os
import re
import math
import json
import urllib.request
import urllib.error
import datetime
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from .models import HourlyLog, Reminder, Category, UserProfile, SMTPSettings
from .quotes import get_quote_for_goal


class HabitIntelligence:
    """
    Habit Intelligence — The Autonomous Time & Habit Orchestrator.
    Powered by Google Gemini AI (when API key is provided) and an ultra-robust
    local deterministic semantic brain that executes every action natively.
    """

    def __init__(self, user):
        self.user = user
        self.profile = getattr(user, 'profile', None)

    def get_gemini_api_key(self):
        """Retrieve Gemini API key from environment, settings, or user profile."""
        key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        if not key and self.profile:
            key = getattr(self.profile, 'gemini_api_key', '')
        return (key or '').strip()

    def process_message(self, user_text):
        """
        Analyze user query and return a structured response dictionary:
        {
            'reply': str,
            'action_type': str,
            'payload': dict
        }
        """
        text = user_text.strip().lower()

        # 0. Check for Gemini API Key configuration via chat
        gemini_set_match = re.search(r'(?:set|save|update)\s+gemini\s+(?:api\s+)?key\s+(?:to\s+)?([A-Za-z0-9_-]{20,})', user_text, re.I)
        if gemini_set_match:
            new_key = gemini_set_match.group(1).strip()
            if self.profile:
                self.profile.gemini_api_key = new_key
                self.profile.save(update_fields=['gemini_api_key'])
                return {
                    'reply': "🤖 **Google Gemini API Key Configured!**\n\nHabit Intelligence is now powered directly by Google Gemini 1.5 Flash. You have full multimodal and natural reasoning enabled across your habit tracker.",
                    'action_type': 'general',
                    'payload': {'gemini_connected': True}
                }

        # 0.1 Try calling Google Gemini Cloud AI if API key is configured
        gemini_key = self.get_gemini_api_key()
        if gemini_key:
            try:
                gemini_result = self._call_gemini_api(user_text, gemini_key)
                if gemini_result and isinstance(gemini_result, dict) and gemini_result.get('reply'):
                    return gemini_result
            except Exception as e:
                # If Gemini API fails (network or quota), seamlessly fall back to local intelligence
                pass

        # 1. Action: View Mode Toggle (Grid vs List)
        if any(p in text for p in ['grid view', 'switch to grid', 'show grid', 'matrix view', 'open grid']):
            return {
                'reply': "🔲 **Switched to 24-Hour Grid View.**\n\nYou can now see your entire 24-hour day in squircle cards with proportional color filling across hours, minutes, and seconds.",
                'action_type': 'switch_view',
                'payload': {'view': 'grid'}
            }
        if any(p in text for p in ['list view', 'switch to list', 'show list', 'vertical view', 'open list']):
            return {
                'reply': "📋 **Switched to 24-Hour List View.**\n\nYour day is now displayed in an Apple chronological vertical timeline.",
                'action_type': 'switch_view',
                'payload': {'view': 'list'}
            }

        # 2. Action: Appearance Theme (Dark vs Light)
        if any(p in text for p in ['dark mode', 'dark theme', 'switch to dark', 'enable dark', 'turn on dark']):
            if self.profile:
                self.profile.theme = 'dark'
                self.profile.save(update_fields=['theme'])
            return {
                'reply': "🌙 **Dark Mode Activated.**\n\nThe interface is now in sleek, OLED-optimized Apple Dark Mode.",
                'action_type': 'change_theme',
                'payload': {'theme': 'dark'}
            }
        if any(p in text for p in ['light mode', 'light theme', 'switch to light', 'enable light', 'turn on light']):
            if self.profile:
                self.profile.theme = 'light'
                self.profile.save(update_fields=['theme'])
            return {
                'reply': "☀️ **Light Mode Activated.**\n\nThe interface is now in crisp, luminous Apple Light Mode.",
                'action_type': 'change_theme',
                'payload': {'theme': 'light'}
            }

        # 3. Action: Live Stopwatch / Timer Control
        if any(p in text for p in ['start stopwatch', 'start timer', 'start the timer', 'start the stopwatch']):
            return {
                'reply': "⏱️ **Stopwatch Started!**\n\nYour focus session is now timing in real-time in the top bar. When you finish, tap Log to record the exact seconds directly into this hour.",
                'action_type': 'control_timer',
                'payload': {'action': 'start'}
            }
        if any(p in text for p in ['pause stopwatch', 'pause timer', 'stop timer', 'stop stopwatch', 'pause the timer']):
            return {
                'reply': "⏸️ **Stopwatch Paused.**\n\nYour elapsed time is saved and persisted across browser tabs.",
                'action_type': 'control_timer',
                'payload': {'action': 'stop'}
            }
        if any(p in text for p in ['reset stopwatch', 'reset timer', 'clear stopwatch', 'reset the stopwatch']):
            return {
                'reply': "↺ **Stopwatch Reset.**\n\nThe timer has been cleared to 00:00:00.",
                'action_type': 'control_timer',
                'payload': {'action': 'reset'}
            }

        # 4. Action: Schedule Filtering
        if any(p in text for p in ['filter productive', 'show productive', 'only productive', 'filter work', 'filter deep work']):
            return {
                'reply': "⚡ **Filter Applied:** Showing only **Productive & Work** hours.",
                'action_type': 'filter_schedule',
                'payload': {'filter': 'productive'}
            }
        if any(p in text for p in ['filter rest', 'show rest', 'show sleep', 'only sleep', 'filter sleep', 'filter recovery']):
            return {
                'reply': "🌙 **Filter Applied:** Showing only **Rest & Recovery** hours.",
                'action_type': 'filter_schedule',
                'payload': {'filter': 'sleep'}
            }
        if any(p in text for p in ['show logged', 'filter logged', 'only logged', 'show active', 'filter active']):
            return {
                'reply': "📌 **Filter Applied:** Showing only **Logged** hours.",
                'action_type': 'filter_schedule',
                'payload': {'filter': 'logged'}
            }
        if any(p in text for p in ['show all', 'all hours', 'clear filter', 'reset filter', 'filter all']):
            return {
                'reply': "🌐 **Filter Reset:** Showing all **24 Hours**.",
                'action_type': 'filter_schedule',
                'payload': {'filter': 'all'}
            }

        # 5. Action: App Navigation
        if any(p in text for p in ['go to analytics', 'open analytics', 'view analytics', 'show trends', 'open trends']):
            return {
                'reply': "📈 Navigating to your **Analytics & Trends** dashboard...",
                'action_type': 'navigate',
                'payload': {'url': '/analytics/'}
            }
        if any(p in text for p in ['go to settings', 'open settings', 'view settings', 'manage categories']):
            return {
                'reply': "⚙️ Navigating to **Settings**...",
                'action_type': 'navigate',
                'payload': {'url': '/settings/'}
            }
        if any(p in text for p in ['go to today', 'go to dashboard', 'open dashboard', 'open today']):
            return {
                'reply': "📅 Navigating to **Today's Dashboard**...",
                'action_type': 'navigate',
                'payload': {'url': '/'}
            }

        # 6. Action: Daily Target / Goal Modification
        target_match = re.search(r'(?:set|change|update)\s+(?:daily\s+)?(?:target|goal)\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)?', text)
        if target_match:
            try:
                new_target = float(target_match.group(1))
                if new_target > 0 and self.profile:
                    self.profile.daily_target_hours = new_target
                    self.profile.save(update_fields=['daily_target_hours'])
                    return {
                        'reply': f"🎯 **Daily Target Updated!**\n\nYour target is now set to **{new_target} hours/day**. Your Apple Activity Rings have been updated to reflect this goal.",
                        'action_type': 'update_profile',
                        'payload': {'target_hours': new_target}
                    }
            except ValueError:
                pass

        primary_goal_match = re.search(r'(?:change|set)\s+primary\s+goal\s+to\s+(focus|fitness|mindfulness|learning|balance)', text)
        if primary_goal_match:
            new_goal = primary_goal_match.group(1)
            if self.profile:
                self.profile.primary_goal = new_goal
                self.profile.save(update_fields=['primary_goal'])
                return {
                    'reply': f"🌟 **Primary Goal Updated!**\n\nYour focus is now aligned with **{self.profile.get_goal_display_text()}**.",
                    'action_type': 'update_profile',
                    'payload': {'primary_goal': new_goal}
                }

        # 7. PRIORITY: Action: Clear / Delete / Remove Hourly Log
        # If user expresses ANY removal intent, NEVER allow it to fall through to log activity!
        del_keywords = ['remove', 'delete', 'clear', 'erase', 'cancel', 'wipe', 'drop', 'trash']
        is_delete_intent = any(re.search(rf'\b{w}\b', text) for w in del_keywords)
        if is_delete_intent:
            return self._execute_delete_command(user_text)

        # 8. Action: Natural Language Log Activity (ONLY if NOT a delete intent!)
        # Examples:
        # "log 2 hours of deep work at 10 am"
        # "add workout for 45 minutes at 7:00"
        # "log sleep for 8 hours at 00:00"
        # "track 30 minutes reading at 9 pm"
        # "add lunch at 12:00 for 1 hour"
        # "log 90 seconds plank at 18:00"
        if not is_delete_intent and re.search(r'\b(?:log|add|track|record|spent|did)\b', text) and ('remind' not in text and 'template' not in text):
            log_result = self._execute_log_command(user_text)
            if log_result:
                return log_result

        # 9. Action: Reminder Scheduling
        reminder_match = re.search(r'(?:remind\s+me|set\s+reminder|add\s+reminder)(?:\s+at|\s+for)?\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+to\s+(.+))?', text)
        if reminder_match:
            time_str = reminder_match.group(1).strip()
            task_title = reminder_match.group(2) or "Log habits and hourly activities"
            reminder_obj = self._create_reminder_from_text(time_str, task_title)
            if reminder_obj:
                return {
                    'reply': f"⏰ **Reminder Scheduled!**\n\nI'll alert you at **{reminder_obj.time.strftime('%I:%M %p')}** with: *\"{reminder_obj.title}\"*. You'll receive a native alert and synthesized Apple chime.",
                    'action_type': 'set_reminder',
                    'payload': {
                        'id': reminder_obj.id,
                        'title': reminder_obj.title,
                        'time': reminder_obj.time.strftime('%H:%M'),
                        'time_display': reminder_obj.time.strftime('%I:%M %p')
                    }
                }

        # 10. Query: List Reminders
        if any(p in text for p in ['list reminders', 'show reminders', 'my reminders', 'all reminders']):
            reminders = Reminder.objects.filter(user=self.user, is_active=True).order_by('time')
            if not reminders.exists():
                return {
                    'reply': "⏰ **Active Reminders:**\n\nYou currently have no active reminders scheduled. Say *\"Remind me at 9:00 PM to review my day\"* to create one!",
                    'action_type': 'general',
                    'payload': {}
                }
            lines = [f"• **{r.time.strftime('%I:%M %p')}**: {r.title}" for r in reminders]
            return {
                'reply': "⏰ **Your Scheduled Reminders:**\n\n" + "\n".join(lines),
                'action_type': 'general',
                'payload': {}
            }

        # 11. Action: Email Daily Report
        if any(p in text for p in ['email report', 'send report to my email', 'email my status', 'send daily report', 'send email report']):
            return self._handle_email_report_request()

        # 12. Knowledge: Proportional Color Fill
        if any(p in text for p in ['proportional', 'half color', 'color fill', 'color update', 'highlighted', 'fill percentage']):
            return {
                'reply': "🎨 **Proportional Color Filling Engine:**\n\n"
                         "Every 1-hour slot (3600 seconds) dynamically fills with that category's color based on exact time logged:\n\n"
                         "• **1 Full Hour (3600s)**: The **entire grid box is 100% highlighted** with rich Apple translucency.\n"
                         "• **30 Minutes (1800s)**: Exactly **50% of the box is colored** with a glowing divider accent.\n"
                         "• **15 Minutes (900s)**: Exactly **25% filled**.\n"
                         "• **Micro Seconds (e.g. 17s)**: Proportional colored slice with minimum indicator width.\n"
                         "• **Multiple Activities in an Hour**: Segmented gradient stops displaying each activity's proportional slice in its category color!",
                'action_type': 'guide',
                'payload': {}
            }

        # 13. Knowledge: Multi-Hour Spanning
        if any(p in text for p in ['span', 'more than 1 hour', 'multi hour', 'reflecting into another', 'ongoing activity']):
            return {
                'reply': "⏱️ **Multi-Hour Spanning System:**\n\n"
                         "When you log an activity longer than 1 hour (e.g. **Work for 8h starting at 09:00**):\n\n"
                         "1️⃣ **Automatic Reflection**: The activity automatically spans across all subsequent hours (10:00 to 16:00) with sleek **Spanned • 09:00–17:00** badges.\n"
                         "2️⃣ **No Double-Counting**: It is stored as a single master log record, keeping your total daily hours and Apple Activity Rings mathematically exact.\n"
                         "3️⃣ **Layering Multiple Activities**: You can still tap any spanned hour (like 12:00) to add a 2nd activity (like Lunch) without overwriting the ongoing session!",
                'action_type': 'guide',
                'payload': {}
            }

        # 14. Knowledge: Bulk CSV Spreadsheet Import
        if any(p in text for p in ['csv', 'excel', 'spreadsheet', 'template', 'bulk upload', 'bulk import']):
            return {
                'reply': "📊 **Bulk Spreadsheet Upload & CSV Template:**\n\n"
                         "You can log dozens of activities simultaneously across any dates and hours:\n\n"
                         "1. Tap the **Spreadsheet Upload** icon next to the date switcher on the dashboard.\n"
                         "2. Download the pre-formatted CSV template with built-in instructions.\n"
                         "3. Fill in columns: `Date (YYYY-MM-DD)`, `Hour (0-23)`, `Activity Title`, `Category`, `Duration`, `Unit (hours/minutes/seconds)`, and `Energy Level (1-5)`.\n"
                         "4. Upload the file to instantly update all your schedule boxes!",
                'action_type': 'guide',
                'payload': {}
            }

        # 15. Query: Daily Status & Progress Report
        if any(k in text for k in ['status', 'how am i doing', 'progress', 'summary', 'today', 'analysis', 'stats', 'score']):
            return self._generate_status_report()

        # 16. Query: Full Walkthrough & Help
        if any(k in text for k in ['how to use', 'help', 'guide', 'tutorial', 'instructions', 'walkthrough', 'feature', 'what can you do']):
            return self._generate_help_guide()

        # 17. Query: Motivation & Quotes
        if any(k in text for k in ['motivat', 'quote', 'inspire', 'lazy', 'tired', 'boost', 'energy', 'focus tip']):
            goal = self.profile.primary_goal if self.profile else 'focus'
            quote_data = get_quote_for_goal(goal)
            return {
                'reply': f"✨ **Motivation for {self.profile.get_goal_display_text() if self.profile else 'You'}:**\n\n> \"{quote_data['quote']}\"\n> — *{quote_data['author']}* ({quote_data['tag']})\n\nEvery logged hour compounds. Start by claiming this current hour!",
                'action_type': 'motivation',
                'payload': quote_data
            }

        # 18. Default Intelligent Response with Action Shortcuts
        return self._generate_default_response()

    def _execute_delete_command(self, raw_text):
        """Intelligently delete an activity or clear an hour slot."""
        text = raw_text.lower().strip()
        today = timezone.localdate()

        # Handle reminder deletion if 'remind' is present
        if 'remind' in text:
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text)
            if time_match:
                parsed_h = self._parse_hour_string(time_match.group(1))
                if parsed_h is not None:
                    rems = Reminder.objects.filter(user=self.user, time__hour=parsed_h)
                    c = rems.count()
                    rems.delete()
                    return {
                        'reply': f"🗑️ **Reminder Removed.** Cancelled {c} reminder(s) around {time_match.group(1)}.",
                        'action_type': 'set_reminder',
                        'payload': {}
                    }

        # 1. Extract hour
        hour = self._extract_hour(text)

        # 2. Extract title keywords
        cleaned = re.sub(r'\b(?:please|remove|delete|clear|erase|cancel|wipe|drop|trash|from|at|the|log|activity|entry|session|hour|slot)\b', ' ', text, flags=re.I)
        cleaned = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b', ' ', cleaned, flags=re.I)
        cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b', ' ', cleaned, flags=re.I)
        title_keywords = [w.strip() for w in cleaned.split() if len(w.strip()) >= 3]

        user_today_logs = HourlyLog.objects.filter(user=self.user, date=today)

        # Case 1: Specific hour identified
        if hour is not None:
            hour_logs = user_today_logs.filter(hour=hour)
            period = "AM" if hour < 12 else "PM"
            disp_h = 12 if hour % 12 == 0 else hour % 12
            time_str = f"{disp_h:02d}:00 {period}"

            if not hour_logs.exists():
                return {
                    'reply': f"ℹ️ **Hour {time_str} ({hour:02d}:00) is already clear.**\n\nThere are no active activities logged in this slot.",
                    'action_type': 'delete_activity',
                    'payload': {'hour': hour}
                }

            # If user provided title keywords (e.g. '1 hour deep work' -> keywords ['deep', 'work'])
            matched_logs = []
            if title_keywords:
                for l in hour_logs:
                    l_lower = l.title.lower()
                    if any(kw in l_lower for kw in title_keywords):
                        matched_logs.append(l)

            if matched_logs:
                del_titles = ", ".join([f'"{l.title}"' for l in matched_logs])
                HourlyLog.objects.filter(id__in=[l.id for l in matched_logs]).delete()
                return {
                    'reply': f"🗑️ **Removed {del_titles} from {time_str}.**\n\nThe schedule box has been updated.",
                    'action_type': 'delete_activity',
                    'payload': {'hour': hour}
                }
            else:
                # If no specific keyword matched or none given, clear all logs in this hour
                count, _ = hour_logs.delete()
                return {
                    'reply': f"🗑️ **Cleared Hour {time_str} ({hour:02d}:00).**\n\nRemoved {count} logged activity entry(ies). The box is now reset to Unscheduled.",
                    'action_type': 'delete_activity',
                    'payload': {'hour': hour}
                }

        # Case 2: No hour identified, but title keywords given (e.g. "remove deep work")
        if title_keywords:
            matched_logs = []
            for l in user_today_logs:
                l_lower = l.title.lower()
                if any(kw in l_lower for kw in title_keywords):
                    matched_logs.append(l)

            if matched_logs:
                del_titles = ", ".join([f'"{l.title}"' for l in matched_logs])
                del_hours = list(set([l.hour for l in matched_logs]))
                HourlyLog.objects.filter(id__in=[l.id for l in matched_logs]).delete()
                return {
                    'reply': f"🗑️ **Removed {del_titles}.**\n\nReset {len(del_hours)} hour slot(s) on your dashboard.",
                    'action_type': 'delete_activity',
                    'payload': {'hour': del_hours[0] if del_hours else 0}
                }

        # Case 3: Clear all logs today
        if 'all' in text and any(w in text for w in ['logs', 'activities', 'today']):
            count, _ = user_today_logs.delete()
            return {
                'reply': f"🗑️ **Cleared All Today's Logs.**\n\nRemoved {count} activities across all 24 hours.",
                'action_type': 'delete_activity',
                'payload': {'hour': 0}
            }

        # Case 4: Ambiguous
        return {
            'reply': "❓ **Which log would you like to remove?**\n\nYou can say:\n• *\"Remove the log at 8 AM\"*\n• *\"Delete Deep Work at 10:00\"*\n• *\"Clear hour 14\"*",
            'action_type': 'general',
            'payload': {}
        }

    def _call_gemini_api(self, user_text, api_key):
        """Invoke Google Gemini 1.5 Flash API with rich contextual prompt."""
        today = timezone.localdate()
        now_h = timezone.localtime().hour
        logs = HourlyLog.objects.filter(user=self.user, date=today).order_by('hour')
        log_summary = [f"Hour {l.hour:02d}:00: '{l.title}' ({l.duration_display}, {l.category.name if l.category else 'General'})" for l in logs]
        schedule_context = "\n".join(log_summary) if log_summary else "No activities logged today yet."

        categories = [c.name for c in Category.objects.filter(Q(user=None) | Q(user=self.user))]

        system_prompt = f"""You are Habit Intelligence, the autonomous AI companion for an Apple iOS-style executive Habit & Time Tracker application.
You possess COMPLETE and EXCLUSIVE knowledge about this application and its features:

=== COMPREHENSIVE APPLICATION ARCHITECTURE & FEATURES ===
1. 24-HOUR HOURLY MATRIX:
   - 24 chronological slots from 00:00 to 23:00.
   - Dual-view toggle: 24-Hour Grid View (squircle glass cards) and List View (vertical chronological timeline).
2. PROPORTIONAL COLOR FILLING ENGINE:
   - Dynamic highlight filling based on exact duration logged:
     • 1 full hour (3600s) = 100% complete box highlight with category translucent glow.
     • 30 minutes (1800s) = Exactly 50% half fill with a vertical glowing divider accent.
     • 15 minutes (900s) = Exactly 25% quarter fill.
     • Seconds (e.g. 17s) = Proportional micro-slice.
     • Multiple activities in one hour = Segmented proportional slices in each category's distinct color!
3. MULTI-HOUR SPANNING SYSTEM:
   - Activities longer than 1 hour (e.g. Work for 8 hours starting at 09:00) automatically reflect across all spanned hours (09:00 to 16:00).
   - Displayed with an Apple badge: "Spanned • 09:00–17:00".
   - Stored as a single master record to keep daily total hours and Apple Activity Rings mathematically exact without double-counting.
   - Users can still click into any spanned hour (e.g. 12:00) to add another activity (e.g. Lunch) simultaneously!
4. PERSISTENT LIVE STOPWATCH:
   - Live Apple-style focus timer in the top bar.
   - Persists elapsed seconds across browser reloads via localStorage.
   - Tap 'Log' to commit the exact elapsed time directly into the current hour.
5. BULK CSV SPREADSHEET IMPORT:
   - Download built-in CSV template next to dashboard date switcher.
   - Columns: Date (YYYY-MM-DD), Hour (0-23), Activity Title, Category, Duration, Unit (hours/minutes/seconds), Energy Level (1-5).
6. APPLE ACTIVITY RINGS & PROGRESS:
   - Daily Target Active Hours ring, Productive Habits ring, and Energy Score ring.
   - Categories include: Deep Work & Career, Health & Workout, Learning & Reading, Mindfulness & Meditation, Sleep & Recovery, Nutrition & Meals, Social & Family, Leisure & Entertainment, Chores & Errands.
7. AUTOMATED SMTP EMAIL REPORTS:
   - Sends daily habit & time summary to user's inbox via Gmail, iCloud, or custom SMTP.
8. APPEARANCE & THEMES:
   - Apple Dark Mode (OLED pitch black with vibrant accents) and Light Mode.

=== CURRENT USER STATE ===
Current Time: {timezone.localtime().strftime('%I:%M %p')}, Hour Slot: {now_h}
Today's Date: {today.strftime('%Y-%m-%d')}
User Profile: Goal={self.profile.primary_goal if self.profile else 'focus'}, Daily Target={self.profile.daily_target_hours if self.profile else 8.0}h
Categories available: {', '.join(categories)}

CURRENT LOGGED ACTIVITIES TODAY:
{schedule_context}

=== ACTION PROTOCOL (STRICT JSON RESPONSE) ===
You must ALWAYS respond with a valid JSON object matching this schema:
{{
  "thought": "Reasoning about user intent",
  "reply": "Concise, friendly Apple-style markdown response with emojis and clear details",
  "action_type": "log_activity | delete_activity | switch_view | change_theme | control_timer | filter_schedule | update_profile | set_reminder | navigate | general | guide",
  "payload": {{ ... }}
}}

ACTION INSTRUCTIONS:
- If user confirms API connection (e.g. 'added api', 'is api working', 'check gemini'):
  action_type = "general", reply = "🟢 **Google Gemini Cloud AI is Live & Working!**\n\nConnected to **Gemini 3.5 Flash**. I have full contextual access to your habit tracker and can execute logs, deletions, view switching, timers, and answer any questions about your day."
- If user wants to delete/remove/clear/erase an activity or hour:
  CRITICAL: NEVER log an activity! Set action_type = "delete_activity", payload: {{"hour": <0-23 or null>, "target_title": "<activity title or null>"}}
- If user wants to log/add/record an activity:
  action_type = "log_activity", payload: {{"hour": <0-23>, "title": "<clean title>", "duration_seconds": <int>, "unit_type": "hours|minutes|seconds", "category_name": "<matching category>"}}
- If user wants to switch between grid and list views:
  action_type = "switch_view", payload: {{"view": "grid" or "list"}}
- If user wants dark or light mode:
  action_type = "change_theme", payload: {{"theme": "dark" or "light"}}
- If user wants stopwatch/timer:
  action_type = "control_timer", payload: {{"action": "start" or "stop" or "reset"}}
- If user wants to filter:
  action_type = "filter_schedule", payload: {{"filter": "all" or "productive" or "sleep" or "logged"}}
- If user wants to update daily target or primary goal:
  action_type = "update_profile", payload: {{"target_hours": <float> or "primary_goal": "<str>"}}
- If user wants a reminder:
  action_type = "set_reminder", payload: {{"time": "HH:MM", "title": "<task>"}}
- If user asks questions about application features or guidance:
  action_type = "guide", payload: {{}}

Return ONLY valid JSON.
"""

        payload_data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}]
                }
            ],
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        # Try Google Gemini models in order of support
        candidate_models = ['gemini-3.5-flash-lite', 'gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-flash-latest']
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=9) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    text_content = result['candidates'][0]['content']['parts'][0]['text']
                    data = json.loads(text_content)
                    return self._apply_gemini_action(data)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Model deprecated or unavailable, try next candidate
                    continue
                raise
            except Exception:
                continue

        raise RuntimeError("No available Gemini model responded successfully.")

    def _apply_gemini_action(self, data):
        """Execute action returned from Gemini API."""
        action_type = data.get('action_type', 'general')
        payload = data.get('payload', {})
        reply = data.get('reply', '')
        today = timezone.localdate()

        if action_type == 'delete_activity':
            hour = payload.get('hour')
            target_title = payload.get('target_title')
            if hour is not None:
                qs = HourlyLog.objects.filter(user=self.user, date=today, hour=hour)
                if target_title:
                    qs = qs.filter(title__icontains=target_title)
                qs.delete()
            elif target_title:
                HourlyLog.objects.filter(user=self.user, date=today, title__icontains=target_title).delete()

        elif action_type == 'log_activity':
            hour = payload.get('hour', timezone.localtime().hour)
            title = payload.get('title', 'Activity')
            duration_seconds = payload.get('duration_seconds', 3600)
            unit_type = payload.get('unit_type', 'hours')
            category_name = payload.get('category_name', '')
            cat = None
            if category_name:
                cat = Category.objects.filter(Q(user=None) | Q(user=self.user)).filter(name__icontains=category_name).first()
            if not cat:
                cat = Category.objects.filter(Q(user=None) | Q(user=self.user)).first()

            log = HourlyLog.objects.create(
                user=self.user,
                date=today,
                hour=hour,
                title=title,
                category=cat,
                duration_seconds=duration_seconds,
                unit_type=unit_type,
                energy_level=4,
                completed=True
            )
            payload['id'] = log.id
            payload['category_color'] = cat.color if cat else '#0071E3'

        elif action_type == 'change_theme':
            if self.profile and 'theme' in payload:
                self.profile.theme = payload['theme']
                self.profile.save(update_fields=['theme'])

        elif action_type == 'update_profile':
            if self.profile:
                if 'target_hours' in payload:
                    try:
                        self.profile.daily_target_hours = float(payload['target_hours'])
                    except (ValueError, TypeError):
                        pass
                if 'primary_goal' in payload:
                    self.profile.primary_goal = payload['primary_goal']
                self.profile.save()

        elif action_type == 'set_reminder':
            time_str = payload.get('time', '20:00')
            task_title = payload.get('title', 'Habit Check-in')
            rem = self._create_reminder_from_text(time_str, task_title)
            if rem:
                payload['id'] = rem.id

        return {
            'reply': reply,
            'action_type': action_type,
            'payload': payload
        }

    def _execute_log_command(self, raw_text):
        """Parse natural language log commands and create the HourlyLog directly."""
        text = raw_text.lower()
        today = timezone.localdate()

        # Parse hour
        hour = self._extract_hour(text)
        if hour is None:
            hour = timezone.localtime().hour

        # Parse duration
        duration_seconds, unit_type, dur_display = self._extract_duration(text)

        # Match category and clean title
        category, title = self._extract_category_and_title(raw_text)

        log = HourlyLog.objects.create(
            user=self.user,
            date=today,
            hour=hour,
            title=title,
            category=category,
            duration_seconds=duration_seconds,
            unit_type=unit_type,
            energy_level=4,
            completed=True
        )

        span_h = max(1, math.ceil(duration_seconds / 3600.0))
        period = "AM" if hour < 12 else "PM"
        disp_h = 12 if hour % 12 == 0 else hour % 12
        time_formatted = f"{disp_h:02d}:00 {period}"

        span_note = f" (Spanning across {span_h} hour blocks)" if span_h > 1 else ""

        return {
            'reply': f"✅ **Activity Logged!**\n\n"
                     f"• **Title**: {log.title}\n"
                     f"• **Time**: {time_formatted} ({hour:02d}:00)\n"
                     f"• **Duration**: {dur_display}{span_note}\n"
                     f"• **Category**: {category.name if category else 'General'}\n\n"
                     f"Your schedule box has been updated with proportional color filling!",
            'action_type': 'log_activity',
            'payload': {
                'id': log.id,
                'hour': hour,
                'span_hours': span_h,
                'title': log.title,
                'category_color': category.color if category else '#0071E3'
            }
        }

    def _extract_hour(self, text):
        """Extract hour (0-23) from strings like 'at 10 am', 'at 14:00', 'at 9pm', 'slot 10'."""
        # 'at 10:30 am', 'at 10 am', 'hour 14', 'slot 9'
        m = re.search(r'(?:at|slot|hour)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', text)
        if m:
            h = int(m.group(1))
            meridiem = (m.group(3) or '').lower()
            if meridiem == 'pm' and h < 12:
                h += 12
            elif meridiem == 'am' and h == 12:
                h = 0
            if 0 <= h <= 23:
                return h

        # standalone 9pm, 10am, 14:00
        m2 = re.search(r'\b(\d{1,2})\s*(am|pm)\b', text)
        if m2:
            h = int(m2.group(1))
            if m2.group(2) == 'pm' and h < 12:
                h += 12
            elif m2.group(2) == 'am' and h == 12:
                h = 0
            if 0 <= h <= 23:
                return h

        return None

    def _extract_duration(self, text):
        """Extract duration in seconds, unit type, and display string."""
        # Check hours
        m_hr = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b', text)
        if m_hr:
            hrs = float(m_hr.group(1))
            sec = max(1, int(hrs * 3600))
            return sec, 'hours', f"{int(hrs) if hrs.is_integer() else hrs}h"

        # Check minutes
        m_min = re.search(r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)\b', text)
        if m_min:
            mins = float(m_min.group(1))
            sec = max(1, int(mins * 60))
            return sec, 'minutes', f"{int(mins) if mins.is_integer() else mins}m"

        # Check seconds
        m_sec = re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b', text)
        if m_sec:
            secs = int(float(m_sec.group(1)))
            return secs, 'seconds', f"{secs}s"

        # Natural words
        if 'half an hour' in text or 'half hour' in text or '30 mins' in text:
            return 1800, 'minutes', '30m'
        if 'quarter hour' in text or '15 mins' in text:
            return 900, 'minutes', '15m'

        # Default 1 hour
        return 3600, 'hours', '1h'

    def _extract_category_and_title(self, raw_text):
        """Match appropriate category and generate clean title."""
        text = raw_text.lower()
        user_cats = Category.objects.filter(Q(user=None) | Q(user=self.user))

        cat_keywords = [
            ('deep work', 'Deep Work & Career'),
            ('work', 'Deep Work & Career'),
            ('code', 'Deep Work & Career'),
            ('coding', 'Deep Work & Career'),
            ('study', 'Deep Work & Career'),
            ('workout', 'Health & Workout'),
            ('exercise', 'Health & Workout'),
            ('running', 'Health & Workout'),
            ('run', 'Health & Workout'),
            ('gym', 'Health & Workout'),
            ('fitness', 'Health & Workout'),
            ('walk', 'Health & Workout'),
            ('read', 'Learning & Reading'),
            ('book', 'Learning & Reading'),
            ('learn', 'Learning & Reading'),
            ('meditat', 'Mindfulness & Meditation'),
            ('breath', 'Mindfulness & Meditation'),
            ('mindful', 'Mindfulness & Meditation'),
            ('sleep', 'Sleep & Recovery'),
            ('nap', 'Sleep & Recovery'),
            ('lunch', 'Nutrition & Meals'),
            ('dinner', 'Nutrition & Meals'),
            ('breakfast', 'Nutrition & Meals'),
            ('meal', 'Nutrition & Meals'),
            ('food', 'Nutrition & Meals'),
            ('family', 'Social & Family'),
            ('friend', 'Social & Family'),
            ('movie', 'Leisure & Entertainment'),
            ('game', 'Leisure & Entertainment'),
            ('clean', 'Chores & Errands'),
            ('chore', 'Chores & Errands'),
        ]

        matched_cat = None
        for kw, cat_name in cat_keywords:
            if kw in text:
                matched_cat = user_cats.filter(name__icontains=cat_name.split()[0]).first()
                if matched_cat:
                    break

        if not matched_cat:
            matched_cat = user_cats.first()

        # Clean title from command syntax
        clean = re.sub(r'^(?:please\s+)?(?:log|add|track|record)\s+', '', raw_text, flags=re.I)
        # Strip trailing time/duration phrases
        clean = re.sub(r'\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?.*$', '', clean, flags=re.I)
        clean = re.sub(r'\s+for\s+\d+(?:\.\d+)?\s*(?:hours?|hrs?|minutes?|mins?|seconds?|secs?).*$', '', clean, flags=re.I)
        clean = re.sub(r'\s+(?:in|slot|hour)\s+\d{1,2}.*$', '', clean, flags=re.I)
        # Strip leading duration phrases like "2 hours of", "30 mins of", "an hour of"
        clean = re.sub(r'^\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\s*(?:of\s+)?', '', clean, flags=re.I)
        clean = re.sub(r'^(?:an?\s+)?(?:half\s+an?\s+hour|quarter\s+hour|hour)\s*(?:of\s+)?', '', clean, flags=re.I)
        clean = re.sub(r'^(?:a|an)\s+', '', clean, flags=re.I)
        clean = clean.strip()

        if not clean or clean.lower() in ['activity', 'entry', 'session', 'it']:
            clean = matched_cat.name if matched_cat else "Activity"

        return matched_cat, clean.title()

    def _parse_hour_string(self, hour_str):
        """Parse hour string like '10 am', '9pm', '14', '07:00' to integer 0..23."""
        hour_str = hour_str.strip().lower()
        m = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', hour_str)
        if m:
            h = int(m.group(1))
            meridiem = m.group(3)
            if meridiem == 'pm' and h < 12:
                h += 12
            elif meridiem == 'am' and h == 12:
                h = 0
            if 0 <= h <= 23:
                return h
        return None

    def _handle_email_report_request(self):
        """Handle request to email daily report."""
        smtp = SMTPSettings.objects.filter(user=self.user, is_active=True).first()
        if not smtp or not smtp.sender_email:
            return {
                'reply': "📧 **Email Reports Configuration:**\n\n"
                         "To enable autonomous report delivery to your inbox:\n"
                         "1. Go to **Settings** → **Email & SMTP Reports**.\n"
                         "2. Enter your Gmail or custom SMTP credentials.\n"
                         "3. Turn on Active Delivery.\n\n"
                         "Once configured, say *\"Send daily report to my email\"* and I will automatically dispatch your PDF analytics and CSV data!",
                'action_type': 'navigate',
                'payload': {'url': '/settings/'}
            }

        # Attempt to send
        try:
            from .reports import send_email_report
            recipient = self.user.email or smtp.sender_email
            today = timezone.localdate()
            res = send_email_report(self.user, recipient, today, today, report_type='both')
            if res.get('success'):
                return {
                    'reply': f"📬 **Report Dispatched!**\n\nYour comprehensive Habit Report (with Excel spreadsheet and PDF charts) has been successfully emailed to **{recipient}**.",
                    'action_type': 'general',
                    'payload': {}
                }
            else:
                return {
                    'reply': f"⚠️ Unable to send email: {res.get('error')}. Please verify your SMTP settings in Settings.",
                    'action_type': 'general',
                    'payload': {}
                }
        except Exception as e:
            return {
                'reply': f"⚠️ Error sending report: {str(e)}. Please check your SMTP configuration under Settings.",
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

        cat_counts = {}
        for l in logs:
            cname = l.category.name if l.category else 'General'
            cat_counts[cname] = cat_counts.get(cname, 0) + (l.duration_seconds / 3600.0)

        cat_summary = ", ".join([f"{k}: {round(v, 1)}h" for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]]) or "No categories logged yet"

        current_hour = timezone.localtime().hour
        period_name = "morning" if current_hour < 12 else "afternoon" if current_hour < 18 else "evening"

        reply = (
            f"📊 **Daily Status Report ({today.strftime('%A, %b %d')}):**\n\n"
            f"• **Total Active Time**: **{total_hours}h** / {target}h Target (**{pct}% complete**)\n"
            f"• **Logged Slots**: {logs.count()} entries recorded across your 24 hours\n"
            f"• **Top Categories**: {cat_summary}\n"
            f"• **Current Streak**: 🔥 **{self.profile.streak_count if self.profile else 1} Days**\n\n"
            f"💡 **Tip for this {period_name}**: "
            + (f"Incredible progress! Your Activity Rings are glowing." if pct >= 60 else f"You have {round(target - total_hours, 1)}h remaining toward your target. Say *\"Log 1 hour Work at {current_hour:02d}:00\"* to log now!")
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
            'reply': "🧠 **Habit Intelligence — Master Walkthrough:**\n\n"
                     "I can autonomously control every single feature in this app. Here is what you can ask me to do:\n\n"
                     "1️⃣ **Log Any Activity**:\n"
                     "• *\"Log 2 hours of Deep Work at 10 AM\"*\n"
                     "• *\"Add 45 minutes of workout at 7:00\"*\n"
                     "• *\"Log sleep for 8 hours at 00:00\"*\n"
                     "• *\"Add lunch at 12:00 for 1 hour\"*\n\n"
                     "2️⃣ **Clear or Delete Activities**:\n"
                     "• *\"Clear hour 14\"* or *\"Delete activity at 10 AM\"*\n\n"
                     "3️⃣ **Switch Views & Themes**:\n"
                     "• *\"Switch to Grid View\"* or *\"Switch to List View\"*\n"
                     "• *\"Switch to Dark Mode\"* or *\"Switch to Light Mode\"*\n\n"
                     "4️⃣ **Control Stopwatch & Reminders**:\n"
                     "• *\"Start stopwatch\"* / *\"Stop timer\"* / *\"Reset stopwatch\"*\n"
                     "• *\"Remind me at 9:00 PM to log my day\"*\n\n"
                     "5️⃣ **Analytics, Goals & Reports**:\n"
                     "• *\"Show my status\"*\n"
                     "• *\"Set daily target to 9 hours\"*\n"
                     "• *\"Send daily report to my email\"*\n"
                     "• *\"Go to Analytics\"* / *\"Go to Settings\"*",
            'action_type': 'guide',
            'payload': {}
        }

    def _generate_default_response(self):
        greeting_name = self.user.first_name or self.user.username
        today = timezone.localdate()
        logged_count = HourlyLog.objects.filter(user=self.user, date=today).count()

        return {
            'reply': f"Hello {greeting_name}! I am **Habit Intelligence**.\n\n"
                     f"Today you have **{logged_count} activities** logged.\n\n"
                     f"Here are a few commands I can execute for you right now:\n"
                     f"• *\"Log 2 hours of Deep Work at 10 AM\"*\n"
                     f"• *\"Switch to Grid View\"* or *\"Switch to List View\"*\n"
                     f"• *\"Turn on Dark Mode\"*\n"
                     f"• *\"Start stopwatch\"*\n"
                     f"• *\"Show my status\"*\n"
                     f"• *\"Remind me at 9 PM to log my day\"*",
            'action_type': 'general',
            'payload': {}
        }

    def _create_reminder_from_text(self, time_str, title):
        """Parse natural time strings like '9 pm', '21:00', '09:30 AM'"""
        parsed_time = None
        time_str = time_str.strip().upper()

        formats = ['%I:%M %p', '%I %p', '%I:%M%p', '%I%p', '%H:%M', '%H']
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                parsed_time = dt.time()
                break
            except ValueError:
                continue

        if not parsed_time:
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
            parsed_time = datetime.time(20, 0)

        clean_title = title.strip().capitalize() if title else "Update daily habits"
        reminder = Reminder.objects.create(
            user=self.user,
            title=clean_title,
            time=parsed_time,
            is_active=True
        )
        return reminder


# Backward compatibility alias
HabitAIAssistant = HabitIntelligence

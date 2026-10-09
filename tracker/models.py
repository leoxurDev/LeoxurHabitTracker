import math
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


GOAL_CHOICES = [
    ('focus', 'Deep Focus & Career Mastery'),
    ('fitness', 'Health & Physical Vitality'),
    ('mindfulness', 'Mindfulness & Mental Peace'),
    ('learning', 'Continuous Learning & Growth'),
    ('balance', 'Work-Life Harmony & Well-being'),
]

UNIT_CHOICES = [
    ('hours', 'Hours'),
    ('minutes', 'Minutes'),
    ('seconds', 'Seconds'),
]


GLOBAL_LANGUAGES = [
    ('en', 'English (US / UK)'),
    ('es', 'Español (Spanish)'),
    ('fr', 'Français (French)'),
    ('de', 'Deutsch (German)'),
    ('it', 'Italiano (Italian)'),
    ('pt', 'Português (Portuguese)'),
    ('ru', 'Русский (Russian)'),
    ('zh-hans', '简体中文 (Chinese Simplified)'),
    ('zh-hant', '繁體中文 (Chinese Traditional)'),
    ('ja', '日本語 (Japanese)'),
    ('ko', '한국어 (Korean)'),
    ('ar', 'العربية (Arabic)'),
    ('hi', 'हिन्दी (Hindi)'),
    ('ta', 'தமிழ் (Tamil)'),
    ('te', 'తెలుగు (Telugu)'),
    ('bn', 'বাংলা (Bengali)'),
    ('mr', 'मराठी (Marathi)'),
    ('ur', 'اردو (Urdu)'),
    ('gu', 'ગુજરાતી (Gujarati)'),
    ('kn', 'ಕನ್ನಡ (Kannada)'),
    ('ml', 'മലയാളം (Malayalam)'),
    ('pa', 'ਪੰਜਾਬੀ (Punjabi)'),
    ('tr', 'Türkçe (Turkish)'),
    ('vi', 'Tiếng Việt (Vietnamese)'),
    ('th', 'ไทย (Thai)'),
    ('id', 'Bahasa Indonesia (Indonesian)'),
    ('ms', 'Bahasa Melayu (Malay)'),
    ('nl', 'Nederlands (Dutch)'),
    ('pl', 'Polski (Polish)'),
    ('sv', 'Svenska (Swedish)'),
    ('el', 'Ελληνικά (Greek)'),
    ('he', 'עברית (Hebrew)'),
    ('uk', 'Українська (Ukrainian)'),
    ('cs', 'Čeština (Czech)'),
    ('ro', 'Română (Romanian)'),
    ('hu', 'Magyar (Hungarian)'),
    ('da', 'Dansk (Danish)'),
    ('fi', 'Suomi (Finnish)'),
    ('no', 'Norsk (Norwegian)'),
    ('fil', 'Filipino / Tagalog'),
    ('sw', 'Kiswahili (Swahili)'),
    ('fa', 'فارسی (Persian)'),
]

COMMON_TIMEZONES = [
    ('UTC', 'UTC (Universal Coordinated Time)'),
    ('Asia/Kolkata', 'Asia/Kolkata (India Standard Time - IST)'),
    ('America/New_York', 'America/New_York (US Eastern Time - EST/EDT)'),
    ('America/Chicago', 'America/Chicago (US Central Time - CST/CDT)'),
    ('America/Denver', 'America/Denver (US Mountain Time - MST/MDT)'),
    ('America/Los_Angeles', 'America/Los_Angeles (US Pacific Time - PST/PDT)'),
    ('America/Anchorage', 'America/Anchorage (Alaska - AKST/AKDT)'),
    ('Pacific/Honolulu', 'Pacific/Honolulu (Hawaii - HST)'),
    ('America/Toronto', 'America/Toronto (Canada Eastern)'),
    ('America/Vancouver', 'America/Vancouver (Canada Pacific)'),
    ('America/Sao_Paulo', 'America/Sao_Paulo (Brazil - BRT)'),
    ('America/Buenos_Aires', 'America/Buenos_Aires (Argentina - ART)'),
    ('America/Mexico_City', 'America/Mexico_City (Mexico City - CST)'),
    ('Europe/London', 'Europe/London (London - GMT / BST)'),
    ('Europe/Dublin', 'Europe/Dublin (Dublin - GMT / IST)'),
    ('Europe/Paris', 'Europe/Paris (Paris - CET / CEST)'),
    ('Europe/Berlin', 'Europe/Berlin (Berlin - CET / CEST)'),
    ('Europe/Rome', 'Europe/Rome (Rome - CET / CEST)'),
    ('Europe/Madrid', 'Europe/Madrid (Madrid - CET / CEST)'),
    ('Europe/Amsterdam', 'Europe/Amsterdam (Amsterdam - CET / CEST)'),
    ('Europe/Athens', 'Europe/Athens (Athens - EET / EEST)'),
    ('Europe/Istanbul', 'Europe/Istanbul (Istanbul - TRT)'),
    ('Europe/Moscow', 'Europe/Moscow (Moscow - MSK)'),
    ('Africa/Cairo', 'Africa/Cairo (Cairo - EET)'),
    ('Africa/Johannesburg', 'Africa/Johannesburg (Johannesburg - SAST)'),
    ('Africa/Lagos', 'Africa/Lagos (Lagos - WAT)'),
    ('Africa/Nairobi', 'Africa/Nairobi (Nairobi - EAT)'),
    ('Asia/Dubai', 'Asia/Dubai (Dubai / UAE - GST)'),
    ('Asia/Riyadh', 'Asia/Riyadh (Riyadh / Saudi Arabia - AST)'),
    ('Asia/Dhaka', 'Asia/Dhaka (Bangladesh - BST)'),
    ('Asia/Karachi', 'Asia/Karachi (Pakistan - PKT)'),
    ('Asia/Bangkok', 'Asia/Bangkok (Bangkok / Indochina - ICT)'),
    ('Asia/Singapore', 'Asia/Singapore (Singapore - SGT)'),
    ('Asia/Hong_Kong', 'Asia/Hong_Kong (Hong Kong - HKT)'),
    ('Asia/Shanghai', 'Asia/Shanghai (China Standard Time - CST)'),
    ('Asia/Tokyo', 'Asia/Tokyo (Japan Standard Time - JST)'),
    ('Asia/Seoul', 'Asia/Seoul (Korea Standard Time - KST)'),
    ('Australia/Sydney', 'Australia/Sydney (Sydney - AEST / AEDT)'),
    ('Australia/Melbourne', 'Australia/Melbourne (Melbourne - AEST / AEDT)'),
    ('Australia/Perth', 'Australia/Perth (Perth - AWST)'),
    ('Pacific/Auckland', 'Pacific/Auckland (New Zealand - NZST / NZDT)'),
]

AI_PROVIDER_CHOICES = [
    ('gemini', 'Google Gemini (Free Tier Available)'),
    ('groq', 'Groq Cloud (100% Free Ultra-Fast Tier)'),
    ('openai', 'OpenAI (GPT-4o / GPT-4o-mini / GPT-3.5)'),
    ('anthropic', 'Anthropic Claude (Claude 3.5 Sonnet / Haiku)'),
    ('openrouter', 'OpenRouter (Multi-Model Gateway w/ Free Models)'),
    ('custom', 'Custom / Local Endpoint (Ollama, vLLM, LM Studio)'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    primary_goal = models.CharField(max_length=50, choices=GOAL_CHOICES, default='focus')
    daily_target_hours = models.FloatField(default=8.0)
    preferred_reminder_time = models.TimeField(null=True, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    streak_count = models.IntegerField(default=1)
    last_active_date = models.DateField(null=True, blank=True)
    bio_motto = models.CharField(max_length=255, blank=True, default="Making every single hour intentional.")
    theme = models.CharField(max_length=20, default='system', choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'Auto/System')])
    avatar_color = models.CharField(max_length=20, default='#007AFF')
    gemini_api_key = models.CharField(max_length=255, blank=True, default='')
    language = models.CharField(max_length=20, default='en', choices=GLOBAL_LANGUAGES)
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    ai_provider = models.CharField(max_length=30, default='gemini', choices=AI_PROVIDER_CHOICES)
    ai_api_key = models.CharField(max_length=255, blank=True, default='')
    ai_model = models.CharField(max_length=100, blank=True, default='')
    ai_custom_endpoint = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_goal_display_text(self):
        return dict(GOAL_CHOICES).get(self.primary_goal, 'Productivity & Growth')

    def get_language_display_text(self):
        return dict(GLOBAL_LANGUAGES).get(self.language, 'English (US / UK)')

    def get_timezone_display_text(self):
        return dict(COMMON_TIMEZONES).get(self.timezone, self.timezone)

    def get_active_ai_key(self):
        """Return ai_api_key or fallback to gemini_api_key"""
        return (self.ai_api_key.strip() or self.gemini_api_key.strip())

    def get_effective_ai_model(self):
        """Return user-configured model or provider default"""
        if self.ai_model and self.ai_model.strip():
            return self.ai_model.strip()
        defaults = {
            'gemini': 'gemini-1.5-flash',
            'groq': 'llama-3.3-70b-versatile',
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'openrouter': 'meta-llama/llama-3.2-3b-instruct:free',
            'custom': 'llama3.2',
        }
        return defaults.get(self.ai_provider, 'gemini-1.5-flash')


class Category(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='custom_categories')
    name = models.CharField(max_length=60)
    icon = models.CharField(max_length=10, default='💼') # Emoji icon
    color = models.CharField(max_length=20, default='#007AFF') # iOS Hex color
    is_productive = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class HourlyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hourly_logs')
    date = models.DateField(default=timezone.now)
    hour = models.IntegerField(default=0)  # 0 to 23 representing 24 hours
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    title = models.CharField(max_length=150)
    notes = models.TextField(blank=True)
    duration_seconds = models.IntegerField(default=3600)  # Stored in exact seconds
    unit_type = models.CharField(max_length=10, default='hours', choices=UNIT_CHOICES)
    energy_level = models.IntegerField(default=4)  # 1 to 5
    completed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'hour', 'created_at']

    def __str__(self):
        return f"{self.user.username} - {self.date} @ {self.hour:02d}:00 - {self.title}"

    @property
    def span_hours(self):
        """Number of hour blocks this activity covers (minimum 1)"""
        return max(1, math.ceil(self.duration_seconds / 3600.0))

    @property
    def hour_formatted(self):
        """Format 0-23 into 12-hour AM/PM string, e.g. '09:00 AM'"""
        h = self.hour
        period = "AM" if h < 12 else "PM"
        display_h = 12 if h % 12 == 0 else h % 12
        return f"{display_h:02d}:00 {period}"

    @property
    def duration_display(self):
        """Human-readable duration based on unit_type or optimal format"""
        sec = self.duration_seconds
        if sec < 60:
            return f"{sec}s"
        elif sec < 3600:
            mins = round(sec / 60, 1)
            return f"{int(mins) if mins.is_integer() else mins}m"
        else:
            hrs = round(sec / 3600, 1)
            return f"{int(hrs) if hrs.is_integer() else hrs}h"

    @property
    def duration_hours(self):
        return round(self.duration_seconds / 3600.0, 2)

    @property
    def duration_minutes(self):
        return round(self.duration_seconds / 60.0, 1)


class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=120)
    time = models.TimeField()
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"{self.user.username} - {self.title} at {self.time.strftime('%I:%M %p')}"


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    message = models.TextField()
    action_type = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.sender}] {self.user.username}: {self.message[:30]}"


class SMTPSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='smtp_settings')
    host = models.CharField(max_length=150, default='smtp.gmail.com')
    port = models.IntegerField(default=587)
    username = models.CharField(max_length=150, blank=True)
    password = models.CharField(max_length=200, blank=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    sender_email = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s SMTP ({self.host})"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        SMTPSettings.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        if hasattr(instance, 'smtp_settings'):
            instance.smtp_settings.save()

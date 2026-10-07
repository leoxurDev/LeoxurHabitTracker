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

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_goal_display_text(self):
        return dict(GOAL_CHOICES).get(self.primary_goal, 'Productivity & Growth')


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
        ordering = ['date', 'hour']
        unique_together = ('user', 'date', 'hour')

    def __str__(self):
        return f"{self.user.username} - {self.date} @ {self.hour:02d}:00 - {self.title}"

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

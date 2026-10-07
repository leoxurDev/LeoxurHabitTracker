from django.contrib import admin
from .models import UserProfile, Category, HourlyLog, Reminder, ChatMessage, SMTPSettings

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'primary_goal', 'daily_target_hours', 'streak_count', 'notifications_enabled')
    search_fields = ('user__username', 'user__email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'is_productive', 'is_default', 'user')
    list_filter = ('is_productive', 'is_default')
    search_fields = ('name',)

@admin.register(HourlyLog)
class HourlyLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'hour', 'title', 'category', 'duration_display', 'completed')
    list_filter = ('date', 'category', 'completed')
    search_fields = ('user__username', 'title', 'notes')

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'time', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'title')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender', 'message', 'action_type', 'timestamp')
    list_filter = ('sender', 'timestamp')

@admin.register(SMTPSettings)
class SMTPSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'host', 'port', 'sender_email', 'use_tls', 'is_active', 'updated_at')
    list_filter = ('is_active', 'use_tls', 'use_ssl')
    search_fields = ('user__username', 'sender_email', 'host')

from django.urls import path
from . import views

urlpatterns = [
    # Core pages
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('settings/', views.settings_view, name='settings'),

    # Ajax APIs for seamless iOS-feel interactions
    path('api/log-hour/', views.api_log_hour, name='api_log_hour'),
    path('api/delete-hour/', views.api_delete_hour, name='api_delete_hour'),
    path('api/quote/', views.api_get_quote, name='api_get_quote'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/reminders/', views.api_reminders, name='api_reminders'),
    path('api/reminders/<int:reminder_id>/toggle/', views.api_toggle_reminder, name='api_toggle_reminder'),
    path('api/reminders/<int:reminder_id>/delete/', views.api_delete_reminder, name='api_delete_reminder'),
    path('api/reminders/check/', views.api_check_due_reminders, name='api_check_due_reminders'),
    path('api/category/add/', views.api_add_custom_category, name='api_add_custom_category'),

    # Template & Bulk Upload
    path('template/download/', views.download_template_view, name='download_template'),
    path('bulk-upload/', views.bulk_upload_view, name='bulk_upload'),

    # Analytics Exports & Email Sharing
    path('analytics/export/csv/', views.export_analytics_csv_view, name='export_analytics_csv'),
    path('analytics/export/pdf/', views.export_analytics_pdf_view, name='export_analytics_pdf'),
    path('analytics/share-email/', views.share_email_report_view, name='share_email_report'),

    # SMTP Testing API
    path('api/smtp/test/', views.api_test_smtp, name='api_test_smtp'),

    # Gemini & Multi-Provider AI Testing API
    path('api/gemini/test/', views.api_test_gemini, name='api_test_gemini'),
    path('api/ai/test-connection/', views.api_test_ai_connection, name='api_test_ai_connection'),

    # User Guide Download (Leoxur Inc.)
    path('help/user-guide/download/', views.download_user_guide_pdf, name='download_user_guide_pdf'),
]

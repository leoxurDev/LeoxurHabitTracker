from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import json
import datetime

from .models import Category, HourlyLog, Reminder, SMTPSettings, UserProfile


class HabitTrackerComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test_pilot',
            email='pilot@leoxur.com',
            password='TestPassword123!'
        )
        self.profile = self.user.profile
        self.profile.timezone = 'Asia/Kolkata'
        self.profile.language = 'en'
        self.profile.save()

        self.category = Category.objects.create(
            user=self.user,
            name='Deep Engineering',
            icon='💻',
            color='#0071E3',
            is_productive=True
        )

    def test_login_and_logout(self):
        """Test login and logout flow."""
        login_res = self.client.post(reverse('login'), {
            'username': 'test_pilot',
            'password': 'TestPassword123!'
        })
        self.assertEqual(login_res.status_code, 302)

        logout_res = self.client.get(reverse('logout'))
        self.assertEqual(logout_res.status_code, 302)

    def test_dashboard_renders(self):
        """Test dashboard renders properly with 24 hours timeline."""
        self.client.login(username='test_pilot', password='TestPassword123!')
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Habit')
        self.assertContains(res, 'Deep Engineering')

    def test_analytics_renders(self):
        """Test analytics page loads without template errors."""
        self.client.login(username='test_pilot', password='TestPassword123!')
        res = self.client.get(reverse('analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Analytics')

    def test_settings_renders_and_updates(self):
        """Test settings view, language update, and timezone update."""
        self.client.login(username='test_pilot', password='TestPassword123!')
        res = self.client.get(reverse('settings'))
        self.assertEqual(res.status_code, 200)

        # Update profile settings
        post_res = self.client.post(reverse('settings'), {
            'action': 'profile',
            'first_name': 'Pilot',
            'email': 'pilot@leoxur.com',
            'primary_goal': 'focus',
            'daily_target_hours': '9.0',
            'bio_motto': 'Intentional Every Hour',
            'theme': 'dark',
            'avatar_color': '#0071E3',
            'language': 'ta',
            'timezone': 'Asia/Kolkata',
            'notifications_enabled': 'on',
        })
        self.assertEqual(post_res.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.language, 'ta')
        self.assertEqual(self.profile.daily_target_hours, 9.0)

    def test_ai_mode_switch_and_key_clear(self):
        """Test switching AI modes and clearing API key completely."""
        self.client.login(username='test_pilot', password='TestPassword123!')

        # Set a key in Cloud AI mode
        res1 = self.client.post(reverse('settings'), {
            'action': 'ai',
            'ai_mode': 'cloud',
            'ai_provider': 'groq',
            'ai_api_key': 'gsk_testdummykey1234567890abcdef',
            'ai_model': 'llama-3.3-70b-versatile',
        })
        self.assertEqual(res1.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ai_mode, 'cloud')
        self.assertEqual(self.profile.ai_api_key, 'gsk_testdummykey1234567890abcdef')

        # Clear the key in Cloud AI mode: both ai_api_key and gemini_api_key MUST be wiped
        res2 = self.client.post(reverse('settings'), {
            'action': 'ai',
            'ai_mode': 'cloud',
            'ai_provider': 'groq',
            'ai_api_key': '',
            'ai_model': 'llama-3.3-70b-versatile',
        })
        self.assertEqual(res2.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ai_api_key, '')
        self.assertEqual(self.profile.gemini_api_key, '')
        self.assertEqual(self.profile.get_saved_ai_key(), '')
        self.assertEqual(self.profile.get_active_ai_key(), '')

        # Switch to Non-AI Local mode
        res3 = self.client.post(reverse('settings'), {
            'action': 'ai',
            'ai_mode': 'local',
            'ai_provider': 'gemini',
            'ai_api_key': '',
        })
        self.assertEqual(res3.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ai_mode, 'local')
        status = self.profile.get_ai_status_display()
        self.assertEqual(status['mode'], 'local')
        self.assertFalse(status['is_online'])

    def test_api_log_and_delete_hour(self):
        """Test logging an hour and deleting it via AJAX."""
        self.client.login(username='test_pilot', password='TestPassword123!')
        today_str = timezone.localdate().strftime('%Y-%m-%d')

        log_res = self.client.post(reverse('api_log_hour'), json.dumps({
            'date': today_str,
            'hour': 14,
            'title': 'High Scale Architecture',
            'category_id': self.category.id,
            'duration_value': 1.5,
            'unit_type': 'hours',
            'energy_level': 5,
            'notes': 'Production verification test'
        }), content_type='application/json')
        self.assertEqual(log_res.status_code, 200)
        data = json.loads(log_res.content)
        self.assertEqual(data['status'], 'success')
        log_id = data['log']['id']
        self.assertEqual(data['log']['duration_seconds'], 5400)

        # Delete hour
        del_res = self.client.post(reverse('api_delete_hour'), json.dumps({
            'log_id': log_id
        }), content_type='application/json')
        self.assertEqual(del_res.status_code, 200)
        del_data = json.loads(del_res.content)
        self.assertEqual(del_data['status'], 'success')

    def test_api_chat_local_engine(self):
        """Test Habit Intelligence chatbot processing under local engine mode."""
        self.client.login(username='test_pilot', password='TestPassword123!')

        # Send greeting / status query
        chat_res = self.client.post(reverse('api_chat'), json.dumps({
            'message': 'status'
        }), content_type='application/json')
        self.assertEqual(chat_res.status_code, 200)
        data = json.loads(chat_res.content)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('reply' in data)

        # Switch to non-ai mode via chat
        chat_mode = self.client.post(reverse('api_chat'), json.dumps({
            'message': 'switch to non-ai mode'
        }), content_type='application/json')
        self.assertEqual(chat_mode.status_code, 200)
        mode_data = json.loads(chat_mode.content)
        self.assertEqual(mode_data['status'], 'success')
        self.assertIn('Non-AI Local Mode', mode_data['reply'])

    def test_reminders_crud(self):
        """Test reminder creation, list, toggle, and deletion."""
        self.client.login(username='test_pilot', password='TestPassword123!')

        # Create
        c_res = self.client.post(reverse('api_reminders'), json.dumps({
            'title': 'Hydration Check',
            'time': '15:30'
        }), content_type='application/json')
        self.assertEqual(c_res.status_code, 200)
        r_data = json.loads(c_res.content)
        self.assertEqual(r_data['status'], 'success')
        rem_id = r_data['reminder']['id']

        # List
        l_res = self.client.get(reverse('api_reminders'))
        self.assertEqual(l_res.status_code, 200)
        l_data = json.loads(l_res.content)
        self.assertTrue(any(r['id'] == rem_id for r in l_data['reminders']))

        # Toggle
        t_res = self.client.post(reverse('api_toggle_reminder', kwargs={'reminder_id': rem_id}))
        self.assertEqual(t_res.status_code, 200)

        # Delete
        d_res = self.client.post(reverse('api_delete_reminder', kwargs={'reminder_id': rem_id}))
        self.assertEqual(d_res.status_code, 200)

    def test_pdf_downloads(self):
        """Verify ReportLab PDF generation for analytics and executive guide."""
        self.client.login(username='test_pilot', password='TestPassword123!')

        # User Guide PDF
        guide_res = self.client.get(reverse('download_user_guide_pdf'))
        self.assertEqual(guide_res.status_code, 200)
        self.assertEqual(guide_res['Content-Type'], 'application/pdf')
        self.assertTrue(len(guide_res.content) > 1000)

        # Analytics PDF
        analytics_pdf_res = self.client.get(reverse('export_analytics_pdf'))
        self.assertEqual(analytics_pdf_res.status_code, 200)
        self.assertEqual(analytics_pdf_res['Content-Type'], 'application/pdf')
        self.assertTrue(len(analytics_pdf_res.content) > 1000)

    def test_csv_exports(self):
        """Verify CSV export and CSV template downloads."""
        self.client.login(username='test_pilot', password='TestPassword123!')

        # CSV Export
        csv_res = self.client.get(reverse('export_analytics_csv'))
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res['Content-Type'])

        # CSV Template
        tpl_res = self.client.get(reverse('download_template'))
        self.assertEqual(tpl_res.status_code, 200)
        self.assertIn('text/csv', tpl_res['Content-Type'])

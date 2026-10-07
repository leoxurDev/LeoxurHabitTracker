from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.utils import ensure_default_categories
from tracker.views import _seed_demo_logs
from tracker.models import Reminder
import datetime

class Command(BaseCommand):
    help = 'Seeds initial default categories and demo user'

    def handle(self, *args, **options):
        ensure_default_categories()
        self.stdout.write(self.style.SUCCESS('Default categories ensured.'))

        demo_user, created = User.objects.get_or_create(username='demo_apple_user')
        if created:
            demo_user.set_password('demo1234')
            demo_user.first_name = 'Alex'
            demo_user.save()
            demo_user.profile.primary_goal = 'focus'
            demo_user.profile.daily_target_hours = 8.0
            demo_user.profile.save()

            Reminder.objects.create(
                user=demo_user,
                title="Log today's final habits & review",
                time=datetime.time(21, 0),
                is_active=True
            )

        _seed_demo_logs(demo_user)
        self.stdout.write(self.style.SUCCESS(f'Demo user {demo_user.username} ready with sample 24h data.'))

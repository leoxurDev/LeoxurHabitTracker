import datetime
from django.utils import timezone
from .models import Category, HourlyLog

DEFAULT_CATEGORIES = [
    {
        'name': 'Deep Work & Career',
        'icon': '💼',
        'color': '#007AFF',
        'is_productive': True,
        'description': 'High-focus work, coding, projects, business execution'
    },
    {
        'name': 'Health & Workout',
        'icon': '🏃‍♂️',
        'color': '#34C759',
        'is_productive': True,
        'description': 'Gym, running, sports, stretching, walking'
    },
    {
        'name': 'Learning & Reading',
        'icon': '📚',
        'color': '#AF52DE',
        'is_productive': True,
        'description': 'Reading books, skill mastery, courses, research'
    },
    {
        'name': 'Mindfulness & Meditation',
        'icon': '🧘‍♀️',
        'color': '#5856D6',
        'is_productive': True,
        'description': 'Meditation, breathwork, journaling, quiet reflection'
    },
    {
        'name': 'Sleep & Recovery',
        'icon': '🌙',
        'color': '#5AC8FA',
        'is_productive': True,
        'description': 'Night sleep, power naps, physical recovery'
    },
    {
        'name': 'Social & Family',
        'icon': '👥',
        'color': '#FF9500',
        'is_productive': True,
        'description': 'Quality time with loved ones, friends, meaningful calls'
    },
    {
        'name': 'Leisure & Entertainment',
        'icon': '🎮',
        'color': '#FF2D55',
        'is_productive': False,
        'description': 'Movies, gaming, social media browsing, relaxation'
    },
    {
        'name': 'Chores & Errands',
        'icon': '🧺',
        'color': '#8E8E93',
        'is_productive': True,
        'description': 'Cleaning, meal prep, groceries, home maintenance'
    },
    {
        'name': 'Nutrition & Meals',
        'icon': '🥗',
        'color': '#30D158',
        'is_productive': True,
        'description': 'Mindful eating, cooking, hydration tracking'
    },
]


def ensure_default_categories():
    """Ensure system-wide default categories exist."""
    for cat_data in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=cat_data['name'],
            user=None,
            defaults={
                'icon': cat_data['icon'],
                'color': cat_data['color'],
                'is_productive': cat_data['is_productive'],
                'description': cat_data['description'],
                'is_default': True,
            }
        )


def calculate_streak(user):
    """Calculate consecutive active days for the user."""
    today = timezone.localdate()
    # Check distinct dates user has logged activities
    logged_dates = set(
        HourlyLog.objects.filter(user=user)
        .values_list('date', flat=True)
        .distinct()
    )

    if not logged_dates:
        return 0

    streak = 0
    current_check = today

    # If nothing logged today yet, check if yesterday was logged to preserve streak
    if current_check not in logged_dates:
        yesterday = current_check - datetime.timedelta(days=1)
        if yesterday in logged_dates:
            current_check = yesterday
        else:
            return 0

    while current_check in logged_dates:
        streak += 1
        current_check -= datetime.timedelta(days=1)

    return streak

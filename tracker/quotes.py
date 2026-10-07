import random

MOTIVATIONAL_QUOTES = {
    'focus': [
        {
            "quote": "Focus is a muscle. The more you protect this single hour from distraction, the stronger you become.",
            "author": "Cal Newport",
            "tag": "Deep Work"
        },
        {
            "quote": "You do not rise to the level of your goals. You fall to the level of your systems.",
            "author": "James Clear",
            "tag": "Atomic Habits"
        },
        {
            "quote": "Deciding what not to do is as important as deciding what to do.",
            "author": "Steve Jobs",
            "tag": "Clarity & Execution"
        },
        {
            "quote": "Concentrate all your thoughts upon the work at hand. The sun's rays do not burn until brought to a focus.",
            "author": "Alexander Graham Bell",
            "tag": "Intensity"
        },
        {
            "quote": "Small disciplines repeated with consistency every day lead to great achievements gained slowly over time.",
            "author": "John C. Maxwell",
            "tag": "Consistency"
        },
    ],
    'fitness': [
        {
            "quote": "Take care of your body. It's the only place you have to live.",
            "author": "Jim Rohn",
            "tag": "Vitality"
        },
        {
            "quote": "Energy flows where attention goes. Fuel this hour with intention and vitality.",
            "author": "Robin Sharma",
            "tag": "Body & Mind"
        },
        {
            "quote": "The body achieves what the mind believes.",
            "author": "Napoleon Hill",
            "tag": "Endurance"
        },
        {
            "quote": "A 30-minute workout is only 2% of your entire day. No excuses.",
            "author": "Fitness Proverb",
            "tag": "Every Minute Counts"
        },
        {
            "quote": "Action inspires momentum. Move first, motivation will quickly follow.",
            "author": "Habit Principle",
            "tag": "Daily Movement"
        },
    ],
    'mindfulness': [
        {
            "quote": "You have power over your mind - not outside events. Realize this, and you will find strength.",
            "author": "Marcus Aurelius",
            "tag": "Stoic Presence"
        },
        {
            "quote": "The present moment is the only moment available to us, and it is the door to all moments.",
            "author": "Thich Nhat Hanh",
            "tag": "Mindful Living"
        },
        {
            "quote": "Quiet the mind, and the soul will speak.",
            "author": "Ma Jaya Sati Bhagavati",
            "tag": "Inner Calm"
        },
        {
            "quote": "Slow down and enjoy life. It's not only the scenery you miss by going too fast — you also miss where you are going.",
            "author": "Eddie Cantor",
            "tag": "Pacing & Peace"
        },
        {
            "quote": "Breath is the bridge which connects life to consciousness.",
            "author": "Thich Nhat Hanh",
            "tag": "Clarity"
        },
    ],
    'learning': [
        {
            "quote": "Live as if you were to die tomorrow. Learn as if you were to live forever.",
            "author": "Mahatma Gandhi",
            "tag": "Continuous Growth"
        },
        {
            "quote": "An investment in knowledge pays the best interest.",
            "author": "Benjamin Franklin",
            "tag": "Intellect"
        },
        {
            "quote": "The capacity to learn is a gift; the ability to learn is a skill; the willingness to learn is a choice.",
            "author": "Brian Herbert",
            "tag": "Wisdom"
        },
        {
            "quote": "Compound knowledge just like compound interest. 15 minutes a day doubles your perspective in a year.",
            "author": "Warren Buffett",
            "tag": "Compounding"
        },
    ],
    'balance': [
        {
            "quote": "Balance is not something you find, it's something you create.",
            "author": "Jana Kingsford",
            "tag": "Harmony"
        },
        {
            "quote": "Never get so busy making a living that you forget to make a life.",
            "author": "Dolly Parton",
            "tag": "Life Design"
        },
        {
            "quote": "Almost everything will work again if you unplug it for a few minutes, including you.",
            "author": "Anne Lamott",
            "tag": "Rest & Recharge"
        },
        {
            "quote": "Productivity isn't about doing more things; it's about doing the right things with joyful presence.",
            "author": "Essentialism Principle",
            "tag": "Intentional Living"
        },
    ]
}


def get_quote_for_goal(goal_key='focus'):
    """Return a curated quote based on user goal, with fallback."""
    quotes = MOTIVATIONAL_QUOTES.get(goal_key, MOTIVATIONAL_QUOTES['focus'])
    return random.choice(quotes)


def get_all_quotes():
    """Return all quotes organized by goal category."""
    return MOTIVATIONAL_QUOTES

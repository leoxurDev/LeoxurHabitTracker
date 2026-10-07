# Habit — 24-Hour Time Canvas

A minimalist, precision habit and hourly life tracking system built with **Python Django** and Apple Human Interface Guidelines aesthetic (Helvetica Neue typography, translucent materials, and fluid micro-animations).

---

## What's New

### 1. Schedule View: Grid View & List View Toggle
- **List View**: A refined vertical 24-hour ruler showing hour slots (`00:00` to `23:00`), category icon, activity title, notes, and duration badge.
- **Grid View**: An Apple calendar-style 24-block matrix (responsive columns) allowing you to inspect your full day at a glance.
- One-click segmented toggle button `[ ≡ List | ☵ Grid ]` with persistent preference.

### 2. Bulk Activity Import & Template Download
- **Download Template (`.csv`)**: One-click download of a pre-formatted spreadsheet containing detailed instructions on columns (`Date`, `Hour`, `Category`, `Activity Title`, `Duration Value`, `Unit`, `Energy Level`, `Notes`) and pre-filled examples.
- **Bulk Upload**: Upload your completed spreadsheet to populate or update multiple hours across any date in seconds.

### 3. SMTP Mail Server Configuration
- Configure your own email delivery in **Settings**:
  - Support for **Gmail** (`smtp.gmail.com:587`), **iCloud Mail** (`smtp.mail.me.com:587`), **Outlook**, or custom SMTP servers.
  - Options for TLS / SSL, custom sender address, and app-specific passwords.
  - Built-in **"Test Connection"** button to verify SMTP credentials and deliver a verification email immediately.

### 4. Advanced Analytics & Custom Date Ranges (Up to 90 Days)
- Select ranges: **7 Days**, **14 Days**, **30 Days**, **90 Days**, or **Custom Date Range** (between 1 and 90 days).
- **Multiple Visual Charts**:
  1. **Daily Activity Hours Trend**: Bar chart measuring logged volume against your daily target.
  2. **24-Hour Circadian Rhythm Heat-Map**: Shows which hours (from `0` to `23`) you dedicate the most time to.
  3. **Category Distribution**: Breakdown of life areas with percentage shares and total hours.
  4. **Goal Consistency & Metrics**: Total active hours, daily average, target completion rate, and active streak.

### 5. Multi-Format Export & Email Sharing
- **Direct PDF Export**: High-resolution graphical report formatted with executive summaries, metrics, category distribution, and activity records.
- **Direct CSV Export**: Clean spreadsheet export of all hourly activities within the chosen date range.
- **Email Report**: Dispatch an email to the user (or custom recipient) with both the **CSV spreadsheet** and **PDF report** attached!

---

## Quickstart

### 1. Environment & Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Apply migrations
python manage.py migrate

# Seed default categories & demo user
python manage.py seed_data
```

### 2. Run Locally
```bash
python manage.py runserver 0.0.0.0:8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

### Credentials
- **Username**: `demo_apple_user`
- **Password**: `demo1234`
*(Or create a new account via the Register page)*

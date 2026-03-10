# GA4 Analytics Report Generator

Pulls data from Google Analytics 4 via the Data API and generates a styled, bilingual (EN/ES) HTML report with period-over-period comparisons.

## What It Generates

A single-page HTML report with 6 sections:

1. **Overview cards** with period-over-period change indicators (sessions, users, pageviews, avg duration)
2. **Top pages** table (path, views, users)
3. **Traffic sources** table (source, sessions, bounce rate)
4. **Geography** table (country, sessions, users)
5. **Devices** breakdown (desktop, mobile, tablet with session counts and avg duration)
6. **New vs returning** visitors

The report uses a dark theme with sage green accents and Inter typography. All labels are bilingual EN/ES.

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google Analytics Data API**
4. Go to **Credentials** and create an **OAuth 2.0 Client ID** (Desktop application)
5. Download the JSON file and save it as `credentials.json` in this directory

### 2. GA4 Property ID

1. In Google Analytics, go to **Admin > Property Settings**
2. Copy your Property ID (numeric, e.g. `123456789`)
3. Update `PROPERTY_ID` in `analytics_report.py`

### 3. Install Dependencies

```bash
pip install google-analytics-data google-auth-oauthlib
```

### 4. First Run (OAuth)

```bash
python3 analytics_report.py
```

On first run, a browser window will open for OAuth consent. After authorizing, a token is cached at `~/.ga4_token.pickle` for future runs.

## Usage

```bash
# Last 7 days (default)
python3 analytics_report.py

# Last 30 days
python3 analytics_report.py --days 30

# Last 14 days
python3 analytics_report.py --days 14
```

Output: `./output/analytics-YYYY-MM-DD.html`

## Customization

Edit the brand color constants at the top of `analytics_report.py`:

```python
COLOR_BG = "#0b0b0b"        # Page background
COLOR_SURFACE = "#141414"    # Card/container background
COLOR_ACCENT = "#8a9a7b"     # Section headers, accent color
COLOR_TEXT = "#e8e8e8"        # Primary text
COLOR_MUTED = "#9ca3af"      # Secondary text
COLOR_BORDER = "#222222"     # Dividers
```

## File Structure

```
ga4-analytics-report/
  analytics_report.py    # Main report generator
  ga4_auth.py            # OAuth token management
  credentials.json       # Your Google Cloud OAuth credentials (not included)
  output/                # Generated reports land here
```

## Requirements

- Python 3.8+
- google-analytics-data
- google-auth-oauthlib

## License

MIT

# GA4 Analytics Report

GA4 analytics report generator. Pulls data via API, outputs styled HTML digests.

**[View sample output](https://sbc1-code.github.io/ga4-analytics-report/)**

## What it does

Connects to a Google Analytics 4 property, pulls key metrics for a configurable time window, and generates a single-page HTML report you can open in any browser or email to stakeholders.

The report includes:

- **Overview cards** with period-over-period change indicators (sessions, users, pageviews, avg duration)
- **Top pages** table (path, views, users)
- **Traffic sources** table (source, sessions, bounce rate)
- **Geography** table (country, sessions, users)
- **Devices** breakdown (desktop, mobile, tablet)
- **New vs returning** visitors

Dark theme with customizable brand colors. All styling is inline HTML so the report renders in any email client or browser.

## Setup

### 1. Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable the **Google Analytics Data API**
4. Create an **OAuth 2.0 Client ID** (Desktop application) under Credentials
5. Download the JSON and save as `credentials.json` in this directory

### 2. GA4 Property ID

1. In Google Analytics, go to **Admin > Property Settings**
2. Copy your numeric Property ID
3. Set `PROPERTY_ID` in `analytics_report.py`

### 3. Install dependencies

```bash
pip install google-analytics-data google-auth-oauthlib
```

## Usage

```bash
# Last 7 days (default)
python3 analytics_report.py

# Last 30 days
python3 analytics_report.py --days 30

# Last 14 days
python3 analytics_report.py --days 14
```

First run opens a browser for OAuth consent. Token is cached at `~/.ga4_token.pickle` for future runs.

## What you get

A styled HTML file at `./output/analytics-YYYY-MM-DD.html`. Open it in a browser, print to PDF, or send as an email attachment.

Brand colors are configurable at the top of `analytics_report.py`:

```python
COLOR_BG = "#0b0b0b"
COLOR_SURFACE = "#141414"
COLOR_ACCENT = "#8a9a7b"
COLOR_TEXT = "#e8e8e8"
COLOR_MUTED = "#9ca3af"
COLOR_BORDER = "#222222"
```

## File structure

```
ga4-analytics-report/
  analytics_report.py    # Main report generator
  ga4_auth.py            # OAuth token management
  index.html             # Sample output (GitHub Pages demo)
  credentials.json       # Your OAuth credentials (not included)
  output/                # Generated reports
```

## License

MIT

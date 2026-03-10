#!/usr/bin/env python3
"""
GA4 Analytics Report Generator
Pulls data from a GA4 property and generates a styled HTML report
with period-over-period comparisons.

Usage:
    python3 analytics_report.py              # Last 7 days (default)
    python3 analytics_report.py --days 30    # Last 30 days
    python3 analytics_report.py --days 14    # Last 14 days
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    OrderBy,
)

from ga4_auth import get_credentials

# === CONFIGURATION ===
# Replace with your GA4 property ID (found in Admin > Property Settings)
PROPERTY_ID = "XXXXXXXXX"
OUTPUT_DIR = Path(__file__).parent / "output"

# === BRAND COLORS (customize these) ===
COLOR_BG = "#0b0b0b"
COLOR_SURFACE = "#141414"
COLOR_ACCENT = "#8a9a7b"
COLOR_TEXT = "#e8e8e8"
COLOR_MUTED = "#9ca3af"
COLOR_BORDER = "#222222"


def make_client():
    creds = get_credentials()
    return BetaAnalyticsDataClient(credentials=creds)


def run_report(client, dimensions, metrics, date_ranges, order_bys=None, limit=10):
    """Run a GA4 report and return rows as list of dicts."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=date_ranges,
        order_bys=order_bys or [],
        limit=limit,
    )
    response = client.run_report(request)
    rows = []
    for row in response.rows:
        r = {}
        for i, dim in enumerate(dimensions):
            r[dim] = row.dimension_values[i].value
        for i, met in enumerate(metrics):
            r[met] = row.metric_values[i].value
        rows.append(r)
    return rows


def pull_all_data(client, days):
    """Pull all 6 report types. Returns dict of results."""
    today = date.today()
    start_current = today - timedelta(days=days)
    start_previous = start_current - timedelta(days=days)
    end_previous = start_current - timedelta(days=1)

    current_range = DateRange(
        start_date=start_current.isoformat(), end_date=today.isoformat()
    )
    previous_range = DateRange(
        start_date=start_previous.isoformat(), end_date=end_previous.isoformat()
    )
    both_ranges = [current_range, previous_range]

    data = {}

    # 1. Overview (current vs previous)
    data["overview"] = run_report(
        client,
        dimensions=[],
        metrics=["sessions", "activeUsers", "screenPageViews", "averageSessionDuration"],
        date_ranges=both_ranges,
        limit=2,
    )

    # 2. Top pages
    data["pages"] = run_report(
        client,
        dimensions=["pagePath"],
        metrics=["screenPageViews", "activeUsers"],
        date_ranges=[current_range],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                desc=True,
            )
        ],
        limit=10,
    )

    # 3. Traffic sources
    data["sources"] = run_report(
        client,
        dimensions=["sessionSource"],
        metrics=["sessions", "bounceRate"],
        date_ranges=[current_range],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                desc=True,
            )
        ],
        limit=10,
    )

    # 4. Geography
    data["geo"] = run_report(
        client,
        dimensions=["country"],
        metrics=["sessions", "activeUsers"],
        date_ranges=[current_range],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                desc=True,
            )
        ],
        limit=10,
    )

    # 5. Devices
    data["devices"] = run_report(
        client,
        dimensions=["deviceCategory"],
        metrics=["sessions", "averageSessionDuration"],
        date_ranges=[current_range],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                desc=True,
            )
        ],
        limit=5,
    )

    # 6. New vs returning
    data["new_returning"] = run_report(
        client,
        dimensions=["newVsReturning"],
        metrics=["sessions", "activeUsers"],
        date_ranges=[current_range],
        limit=5,
    )

    return data


def fmt_num(val):
    """Format a numeric string nicely."""
    try:
        f = float(val)
        if f == int(f):
            return f"{int(f):,}"
        return f"{f:,.1f}"
    except (ValueError, TypeError):
        return val


def fmt_duration(seconds_str):
    """Format seconds as Xm Ys."""
    try:
        s = float(seconds_str)
        m, sec = divmod(int(s), 60)
        return f"{m}m {sec}s"
    except (ValueError, TypeError):
        return seconds_str


def fmt_pct(val):
    """Format as percentage."""
    try:
        return f"{float(val) * 100:.1f}%"
    except (ValueError, TypeError):
        return val


def calc_change(current, previous):
    """Calculate % change and return (value, direction)."""
    try:
        c, p = float(current), float(previous)
        if p == 0:
            return ("N/A", "neutral")
        change = ((c - p) / p) * 100
        direction = "up" if change > 0 else "down" if change < 0 else "neutral"
        return (f"{abs(change):.1f}%", direction)
    except (ValueError, TypeError):
        return ("N/A", "neutral")


def generate_html(data, days):
    """Generate styled HTML report with dark theme."""
    today = date.today()
    start = today - timedelta(days=days)

    # Extract overview metrics
    current = data["overview"][0] if data["overview"] else {}
    previous = data["overview"][1] if len(data["overview"]) > 1 else {}

    metrics_cards = []
    metric_defs = [
        ("Sesiones / Sessions", "sessions", fmt_num),
        ("Usuarios / Users", "activeUsers", fmt_num),
        ("Vistas / Pageviews", "screenPageViews", fmt_num),
        ("Duracion Prom. / Avg. Duration", "averageSessionDuration", fmt_duration),
    ]

    for label, key, formatter in metric_defs:
        cur_val = current.get(key, "0")
        prev_val = previous.get(key, "0")
        change_val, direction = calc_change(cur_val, prev_val)
        metrics_cards.append({
            "label": label,
            "value": formatter(cur_val),
            "change": change_val,
            "direction": direction,
        })

    # Build pages table rows
    pages_rows = ""
    for row in data.get("pages", []):
        path = row.get("pagePath", "/")
        if len(path) > 45:
            path = path[:42] + "..."
        pages_rows += f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};font-family:'Inter',sans-serif;">{path}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};text-align:right;font-weight:600;font-family:'Inter',sans-serif;">{fmt_num(row.get('screenPageViews','0'))}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_MUTED};text-align:right;font-family:'Inter',sans-serif;">{fmt_num(row.get('activeUsers','0'))}</td>
            </tr>"""

    # Build sources table rows
    sources_rows = ""
    for row in data.get("sources", []):
        source = row.get("sessionSource", "(direct)")
        bounce = fmt_pct(row.get("bounceRate", "0"))
        sources_rows += f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};font-family:'Inter',sans-serif;">{source}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};text-align:right;font-weight:600;font-family:'Inter',sans-serif;">{fmt_num(row.get('sessions','0'))}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_MUTED};text-align:right;font-family:'Inter',sans-serif;">{bounce}</td>
            </tr>"""

    # Build geo table rows
    geo_rows = ""
    for row in data.get("geo", []):
        geo_rows += f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};font-family:'Inter',sans-serif;">{row.get('country','Unknown')}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_TEXT};text-align:right;font-weight:600;font-family:'Inter',sans-serif;">{fmt_num(row.get('sessions','0'))}</td>
                <td style="padding:10px 12px;border-bottom:1px solid {COLOR_BORDER};font-size:13px;color:{COLOR_MUTED};text-align:right;font-family:'Inter',sans-serif;">{fmt_num(row.get('activeUsers','0'))}</td>
            </tr>"""

    # Build devices section
    devices_html = ""
    for row in data.get("devices", []):
        cat = row.get("deviceCategory", "unknown").capitalize()
        sessions = fmt_num(row.get("sessions", "0"))
        dur = fmt_duration(row.get("averageSessionDuration", "0"))
        devices_html += f"""
            <div style="display:inline-block;width:30%;text-align:center;padding:16px 8px;vertical-align:top;">
                <div style="font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:6px;font-family:'Inter',sans-serif;">{cat}</div>
                <div style="font-size:24px;font-weight:700;color:{COLOR_TEXT};font-family:'Inter',sans-serif;">{sessions}</div>
                <div style="font-size:12px;color:{COLOR_MUTED};margin-top:2px;font-family:'Inter',sans-serif;">avg {dur}</div>
            </div>"""

    # Build new vs returning
    new_ret_html = ""
    for row in data.get("new_returning", []):
        segment = row.get("newVsReturning", "unknown")
        label = "Nuevos / New Visitors" if segment == "new" else "Recurrentes / Returning" if segment == "returning" else segment.capitalize()
        new_ret_html += f"""
            <div style="display:inline-block;width:45%;text-align:center;padding:16px 8px;vertical-align:top;">
                <div style="font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:6px;font-family:'Inter',sans-serif;">{label}</div>
                <div style="font-size:28px;font-weight:700;color:{COLOR_TEXT};font-family:'Inter',sans-serif;">{fmt_num(row.get('sessions','0'))}</div>
                <div style="font-size:12px;color:{COLOR_MUTED};margin-top:2px;font-family:'Inter',sans-serif;">{fmt_num(row.get('activeUsers','0'))} usuarios / users</div>
            </div>"""

    # Metric cards HTML
    cards_html = ""
    for card in metrics_cards:
        arrow = ""
        color = COLOR_MUTED
        if card["direction"] == "up":
            arrow = "&#9650;"
            color = "#16a34a"
        elif card["direction"] == "down":
            arrow = "&#9660;"
            color = "#dc2626"

        cards_html += f"""
            <div style="display:inline-block;width:23%;text-align:center;padding:20px 8px;vertical-align:top;">
                <div style="font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:8px;font-family:'Inter',sans-serif;">{card['label']}</div>
                <div style="font-size:28px;font-weight:700;color:{COLOR_TEXT};line-height:1.1;font-family:'Inter',sans-serif;">{card['value']}</div>
                <div style="font-size:12px;color:{color};margin-top:6px;font-family:'Inter',sans-serif;">{arrow} {card['change']} vs anterior</div>
            </div>"""

    # Determine period label (use month name for 28-31 day reports)
    if 27 <= days <= 31:
        period_label = f"{start.strftime('%B')} {start.year}"
    else:
        period_label = f"{days}-Day Report"

    html = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Report | Reporte de Analitica</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        @media print {{
            body {{ background: #fff !important; }}
            .brief {{ box-shadow: none !important; margin: 0 !important; }}
        }}
    </style>
</head>
<body style="margin:0;padding:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:{COLOR_BG};color:{COLOR_TEXT};line-height:1.6;-webkit-font-smoothing:antialiased;">

<div class="brief" style="max-width:680px;margin:40px auto;background:{COLOR_SURFACE};border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.3),0 8px 24px rgba(0,0,0,0.2);">

    <!-- HEADER -->
    <div style="background:{COLOR_SURFACE};padding:32px 40px 28px;position:relative;border-bottom:1px solid {COLOR_BORDER};">
        <div style="position:absolute;bottom:0;left:40px;right:40px;height:3px;background:{COLOR_ACCENT};"></div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <div style="font-size:15px;font-weight:700;letter-spacing:3px;color:{COLOR_TEXT};text-transform:uppercase;font-family:'Inter',sans-serif;">YOUR BRAND</div>
            <div style="font-size:12px;font-weight:500;color:{COLOR_MUTED};letter-spacing:1px;font-family:'Inter',sans-serif;">{today.strftime('%B %d, %Y').upper()}</div>
        </div>
        <div style="font-size:22px;font-weight:300;color:{COLOR_TEXT};letter-spacing:-0.2px;font-family:'Inter',sans-serif;">
            <strong>Reporte de Analitica / Analytics Report</strong> | {period_label}
        </div>
        <div style="font-size:13px;color:{COLOR_MUTED};margin-top:8px;font-family:'Inter',sans-serif;">
            {start.strftime('%b %d')} | {today.strftime('%b %d, %Y')} &nbsp;|&nbsp; example.com
        </div>
    </div>

    <!-- OVERVIEW CARDS -->
    <div style="padding:32px 40px 24px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">RESUMEN / OVERVIEW</div>
        <div style="text-align:center;">
            {cards_html}
        </div>
    </div>

    <!-- DIVIDER -->
    <div style="margin:0 40px;height:1px;background:{COLOR_BORDER};"></div>

    <!-- TOP PAGES -->
    <div style="padding:28px 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">PAGINAS PRINCIPALES / TOP PAGES</div>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:left;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Pagina / Page</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Vistas / Views</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Usuarios / Users</th>
                </tr>
            </thead>
            <tbody>
                {pages_rows}
            </tbody>
        </table>
    </div>

    <!-- DIVIDER -->
    <div style="margin:0 40px;height:1px;background:{COLOR_BORDER};"></div>

    <!-- TRAFFIC SOURCES -->
    <div style="padding:28px 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">FUENTES DE TRAFICO / TRAFFIC SOURCES</div>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:left;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Fuente / Source</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Sesiones / Sessions</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Rebote / Bounce</th>
                </tr>
            </thead>
            <tbody>
                {sources_rows}
            </tbody>
        </table>
    </div>

    <!-- DIVIDER -->
    <div style="margin:0 40px;height:1px;background:{COLOR_BORDER};"></div>

    <!-- GEOGRAPHY -->
    <div style="padding:28px 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">GEOGRAFIA / GEOGRAPHY</div>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:left;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Pais / Country</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Sesiones / Sessions</th>
                    <th style="padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{COLOR_MUTED};text-align:right;border-bottom:2px solid {COLOR_BORDER};font-family:'Inter',sans-serif;">Usuarios / Users</th>
                </tr>
            </thead>
            <tbody>
                {geo_rows}
            </tbody>
        </table>
    </div>

    <!-- DIVIDER -->
    <div style="margin:0 40px;height:1px;background:{COLOR_BORDER};"></div>

    <!-- DEVICES -->
    <div style="padding:28px 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">DISPOSITIVOS / DEVICES</div>
        <div style="text-align:center;">
            {devices_html}
        </div>
    </div>

    <!-- DIVIDER -->
    <div style="margin:0 40px;height:1px;background:{COLOR_BORDER};"></div>

    <!-- NEW VS RETURNING -->
    <div style="padding:28px 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{COLOR_ACCENT};margin-bottom:16px;font-family:'Inter',sans-serif;">NUEVOS VS RECURRENTES / NEW VS RETURNING</div>
        <div style="text-align:center;">
            {new_ret_html}
        </div>
    </div>

    <!-- FOOTER -->
    <div style="background:{COLOR_SURFACE};padding:24px 40px;text-align:center;border-top:1px solid {COLOR_BORDER};">
        <div style="font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:{COLOR_MUTED};font-family:'Inter',sans-serif;">
            Analytics Report | Reporte de Analitica
        </div>
        <div style="font-size:11px;color:{COLOR_MUTED};margin-top:6px;font-family:'Inter',sans-serif;">
            Data: Google Analytics 4 &nbsp;|&nbsp; Property: example.com
        </div>
    </div>

</div>

</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="GA4 Analytics Report Generator")
    parser.add_argument("--days", type=int, default=7, help="Number of days to report on (default: 7)")
    args = parser.parse_args()

    print(f"Pulling {args.days}-day GA4 data...")
    client = make_client()
    data = pull_all_data(client, args.days)

    # Quick summary to stdout
    if data["overview"]:
        cur = data["overview"][0]
        print(f"  Sessions: {fmt_num(cur.get('sessions','0'))}")
        print(f"  Users: {fmt_num(cur.get('activeUsers','0'))}")
        print(f"  Pageviews: {fmt_num(cur.get('screenPageViews','0'))}")
        print(f"  Avg Duration: {fmt_duration(cur.get('averageSessionDuration','0'))}")

    html = generate_html(data, args.days)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"analytics-{date.today().isoformat()}.html"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w") as f:
        f.write(html)

    print(f"\nReport saved: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    main()

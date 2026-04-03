"""
Chicago Fleet Wraps Reddit Bot — Karma Dashboard Generator v1.0
Generates a self-contained HTML dashboard showing:
- Karma growth over time
- Best-performing comments
- Subreddit performance breakdown
- Competitor mention tracking
- Reply engagement stats
- Timing analysis

The dashboard is a single HTML file with embedded Chart.js
that can be opened in any browser or hosted anywhere.
"""
import json
import os
from datetime import datetime
from config import DATA_DIR, LOG_DIR, REDDIT_USERNAME

DASHBOARD_FILE = os.path.join(LOG_DIR, "dashboard.html")


def generate_dashboard():
    """Generate the full HTML dashboard from all bot data files."""
    print(f"  [DASHBOARD] Generating dashboard...", flush=True)

    # Load all data sources
    perf_log = _load_json(os.path.join(DATA_DIR, "performance_log.json"), [])
    perf_summary = _load_json(os.path.join(DATA_DIR, "performance_summary.json"), {})
    sub_profiles = _load_json(os.path.join(DATA_DIR, "sub_profiles.json"), {})
    competitor_log = _load_json(os.path.join(DATA_DIR, "competitor_mentions.json"), [])
    comment_history = _load_json(os.path.join(DATA_DIR, "comment_history.json"), [])
    replies_sent = _load_json(os.path.join(DATA_DIR, "replies_sent.json"), {})
    daily_log = _load_json(os.path.join(LOG_DIR, "daily_activity.json"), {})

    # Build dashboard data
    karma_trend = _build_karma_trend(perf_log)
    sub_breakdown = _build_sub_breakdown(perf_summary, sub_profiles)
    top_comments = _build_top_comments(perf_log)
    worst_comments = _build_worst_comments(perf_log)
    competitor_data = _build_competitor_data(competitor_log)
    activity_stats = _build_activity_stats(comment_history, daily_log, replies_sent)
    length_analysis = _build_length_analysis(perf_summary)

    # Generate HTML
    html = _render_html(
        karma_trend=karma_trend,
        sub_breakdown=sub_breakdown,
        top_comments=top_comments,
        worst_comments=worst_comments,
        competitor_data=competitor_data,
        activity_stats=activity_stats,
        length_analysis=length_analysis,
        perf_summary=perf_summary,
    )

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(DASHBOARD_FILE, "w") as f:
        f.write(html)

    print(f"  [DASHBOARD] Dashboard saved to {DASHBOARD_FILE}", flush=True)
    return DASHBOARD_FILE


def _load_json(path: str, default):
    """Safely load a JSON file."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _build_karma_trend(perf_log: list) -> dict:
    """Build daily karma trend data for the chart."""
    daily = {}
    for entry in perf_log:
        date_str = entry.get("tracked_at", "")[:10]
        if date_str:
            if date_str not in daily:
                daily[date_str] = {"total_score": 0, "count": 0}
            daily[date_str]["total_score"] += entry.get("score", 0)
            daily[date_str]["count"] += 1

    dates = sorted(daily.keys())
    cumulative = 0
    labels = []
    values = []
    daily_values = []
    for d in dates:
        cumulative += daily[d]["total_score"]
        labels.append(d)
        values.append(cumulative)
        daily_values.append(daily[d]["total_score"])

    return {"labels": labels, "cumulative": values, "daily": daily_values}


def _build_sub_breakdown(perf_summary: dict, sub_profiles: dict) -> list:
    """Build subreddit performance breakdown."""
    by_sub = perf_summary.get("by_subreddit", {})
    rows = []
    for sub, data in by_sub.items():
        profile = sub_profiles.get(sub.lower(), {})
        tones = profile.get("tone_counts", {})
        dominant_tone = max(tones, key=tones.get) if tones and sum(tones.values()) > 0 else "unknown"

        rows.append({
            "subreddit": sub,
            "avg_score": data.get("avg_score", 0),
            "count": data.get("count", 0),
            "best_score": data.get("best_score", 0),
            "best_comment": data.get("best_comment", "")[:80],
            "dominant_tone": dominant_tone,
            "avg_winning_length": profile.get("avg_winning_length", 0),
        })

    rows.sort(key=lambda x: x["avg_score"], reverse=True)
    return rows


def _build_top_comments(perf_log: list) -> list:
    """Get the top 10 best-performing comments."""
    sorted_log = sorted(perf_log, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_log[:10]


def _build_worst_comments(perf_log: list) -> list:
    """Get the bottom 5 worst-performing comments."""
    sorted_log = sorted(perf_log, key=lambda x: x.get("score", 0))
    return sorted_log[:5]


def _build_competitor_data(competitor_log: list) -> dict:
    """Build competitor mention analytics."""
    by_comp = {}
    by_context = {}
    responded = 0

    for entry in competitor_log:
        comp = entry.get("competitor", "unknown")
        ctx = entry.get("context", "unknown")
        by_comp[comp] = by_comp.get(comp, 0) + 1
        by_context[ctx] = by_context.get(ctx, 0) + 1
        if entry.get("responded"):
            responded += 1

    return {
        "total": len(competitor_log),
        "by_competitor": by_comp,
        "by_context": by_context,
        "response_rate": round(responded / len(competitor_log) * 100, 1) if competitor_log else 0,
        "recent": competitor_log[-5:],
    }


def _build_activity_stats(comment_history: list, daily_log: dict, replies_sent: dict) -> dict:
    """Build overall activity statistics."""
    total_comments = len(comment_history)
    promo_count = sum(1 for c in comment_history if c.get("is_promo"))
    non_promo = total_comments - promo_count

    # Comments per day
    days = set()
    for c in comment_history:
        d = c.get("date", "")
        if d:
            days.add(d)

    avg_per_day = round(total_comments / len(days), 1) if days else 0

    return {
        "total_comments": total_comments,
        "promo_comments": promo_count,
        "non_promo_comments": non_promo,
        "promo_ratio": round(promo_count / total_comments * 100, 1) if total_comments else 0,
        "active_days": len(days),
        "avg_per_day": avg_per_day,
        "replies_sent_today": replies_sent.get("count", 0),
        "today_total": daily_log.get("total_comments", 0),
        "today_promo": daily_log.get("promo_comments", 0),
    }


def _build_length_analysis(perf_summary: dict) -> dict:
    """Build comment length vs performance analysis."""
    return perf_summary.get("by_length", {})


def _render_html(**data) -> str:
    """Render the full HTML dashboard."""
    karma_trend = data.get("karma_trend", {})
    sub_breakdown = data.get("sub_breakdown", [])
    top_comments = data.get("top_comments", [])
    worst_comments = data.get("worst_comments", [])
    competitor_data = data.get("competitor_data", {})
    activity_stats = data.get("activity_stats", {})
    length_analysis = data.get("length_analysis", {})
    perf_summary = data.get("perf_summary", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build sub breakdown rows
    sub_rows_html = ""
    for row in sub_breakdown:
        sub_rows_html += f"""
        <tr>
            <td><strong>r/{row['subreddit']}</strong></td>
            <td>{row['avg_score']}</td>
            <td>{row['count']}</td>
            <td>{row['best_score']}</td>
            <td>{row['dominant_tone']}</td>
            <td>{row['avg_winning_length']:.0f}w</td>
            <td class="comment-preview">{_escape(row['best_comment'])}</td>
        </tr>"""

    # Build top comments rows
    top_rows_html = ""
    for c in top_comments:
        top_rows_html += f"""
        <tr class="good">
            <td><strong>{c.get('score', 0)}</strong></td>
            <td>r/{c.get('subreddit', '')}</td>
            <td>{c.get('word_count', 0)}w</td>
            <td class="comment-preview">{_escape(c.get('body_preview', '')[:120])}</td>
        </tr>"""

    # Build worst comments rows
    worst_rows_html = ""
    for c in worst_comments:
        worst_rows_html += f"""
        <tr class="bad">
            <td><strong>{c.get('score', 0)}</strong></td>
            <td>r/{c.get('subreddit', '')}</td>
            <td>{c.get('word_count', 0)}w</td>
            <td class="comment-preview">{_escape(c.get('body_preview', '')[:120])}</td>
        </tr>"""

    # Build competitor rows
    comp_rows_html = ""
    for comp, count in competitor_data.get("by_competitor", {}).items():
        comp_rows_html += f"<tr><td>{_escape(comp)}</td><td>{count}</td></tr>"

    # Length analysis
    length_html = ""
    for bucket in ["short", "medium", "long"]:
        d = length_analysis.get(bucket, {})
        if d.get("count", 0) > 0:
            label = {"short": "Short (<20w)", "medium": "Medium (20-50w)", "long": "Long (50+w)"}.get(bucket, bucket)
            length_html += f"<tr><td>{label}</td><td>{d.get('avg_score', 0)}</td><td>{d.get('count', 0)}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CFW Reddit Bot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }}
.header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; }}
.header h1 {{ font-size: 28px; color: #ff6b35; margin-bottom: 5px; }}
.header p {{ color: #888; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }}
.card {{ background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333; }}
.card h2 {{ font-size: 16px; color: #ff6b35; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }}
.stat-number {{ font-size: 36px; font-weight: bold; color: #fff; }}
.stat-label {{ font-size: 13px; color: #888; margin-top: 5px; }}
.stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #222; }}
.chart-container {{ background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333; margin-bottom: 30px; }}
.chart-container h2 {{ font-size: 16px; color: #ff6b35; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 10px 8px; background: #222; color: #ff6b35; font-weight: 600; }}
td {{ padding: 8px; border-bottom: 1px solid #222; }}
tr:hover {{ background: #1f1f1f; }}
tr.good td:first-child {{ color: #4caf50; }}
tr.bad td:first-child {{ color: #f44336; }}
.comment-preview {{ max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #aaa; font-size: 12px; }}
.section {{ margin-bottom: 30px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
.badge-green {{ background: #1b5e20; color: #4caf50; }}
.badge-red {{ background: #b71c1c33; color: #f44336; }}
.badge-orange {{ background: #e65100; color: #ff9800; }}
canvas {{ max-height: 300px; }}
</style>
</head>
<body>

<div class="header">
    <h1>CFW Reddit Bot Dashboard</h1>
    <p>u/{REDDIT_USERNAME} | Last updated: {now}</p>
</div>

<!-- Quick Stats -->
<div class="grid">
    <div class="card">
        <h2>Total Comments</h2>
        <div class="stat-number">{activity_stats.get('total_comments', 0)}</div>
        <div class="stat-label">{activity_stats.get('avg_per_day', 0)} avg/day over {activity_stats.get('active_days', 0)} days</div>
    </div>
    <div class="card">
        <h2>Avg Score</h2>
        <div class="stat-number">{perf_summary.get('overall_avg_score', 0)}</div>
        <div class="stat-label">across {perf_summary.get('total_tracked', 0)} tracked comments</div>
    </div>
    <div class="card">
        <h2>Promo Ratio</h2>
        <div class="stat-number">{activity_stats.get('promo_ratio', 0)}%</div>
        <div class="stat-label">{activity_stats.get('promo_comments', 0)} promo / {activity_stats.get('non_promo_comments', 0)} organic</div>
    </div>
    <div class="card">
        <h2>Competitor Mentions</h2>
        <div class="stat-number">{competitor_data.get('total', 0)}</div>
        <div class="stat-label">{competitor_data.get('response_rate', 0)}% response rate</div>
    </div>
</div>

<!-- Karma Trend Chart -->
<div class="chart-container">
    <h2>Karma Growth Over Time</h2>
    <canvas id="karmaChart"></canvas>
</div>

<!-- Two-column: Sub Performance + Length Analysis -->
<div class="grid">
    <div class="card" style="grid-column: span 2;">
        <h2>Subreddit Performance</h2>
        <table>
            <thead><tr><th>Subreddit</th><th>Avg Score</th><th>Comments</th><th>Best</th><th>Tone</th><th>Win Length</th><th>Best Comment</th></tr></thead>
            <tbody>{sub_rows_html if sub_rows_html else '<tr><td colspan="7" style="text-align:center;color:#666;">No data yet — bot needs more runs to build profiles</td></tr>'}</tbody>
        </table>
    </div>
</div>

<!-- Comment Length Analysis -->
<div class="grid">
    <div class="card">
        <h2>Length vs Performance</h2>
        <table>
            <thead><tr><th>Length</th><th>Avg Score</th><th>Count</th></tr></thead>
            <tbody>{length_html if length_html else '<tr><td colspan="3" style="text-align:center;color:#666;">Not enough data yet</td></tr>'}</tbody>
        </table>
    </div>
    <div class="card">
        <h2>Competitor Mentions</h2>
        <table>
            <thead><tr><th>Competitor</th><th>Mentions</th></tr></thead>
            <tbody>{comp_rows_html if comp_rows_html else '<tr><td colspan="2" style="text-align:center;color:#666;">No competitor mentions tracked yet</td></tr>'}</tbody>
        </table>
    </div>
</div>

<!-- Top Performing Comments -->
<div class="chart-container">
    <h2>Top Performing Comments</h2>
    <table>
        <thead><tr><th>Score</th><th>Subreddit</th><th>Length</th><th>Comment</th></tr></thead>
        <tbody>{top_rows_html if top_rows_html else '<tr><td colspan="4" style="text-align:center;color:#666;">No scored comments yet — run upvote-check mode</td></tr>'}</tbody>
    </table>
</div>

<!-- Worst Performing Comments -->
<div class="chart-container">
    <h2>Worst Performing Comments (Learn From These)</h2>
    <table>
        <thead><tr><th>Score</th><th>Subreddit</th><th>Length</th><th>Comment</th></tr></thead>
        <tbody>{worst_rows_html if worst_rows_html else '<tr><td colspan="4" style="text-align:center;color:#666;">No data yet</td></tr>'}</tbody>
    </table>
</div>

<!-- Today's Activity -->
<div class="card">
    <h2>Today's Activity</h2>
    <div class="stat-row"><span>Comments posted</span><span>{activity_stats.get('today_total', 0)}</span></div>
    <div class="stat-row"><span>Promo comments</span><span>{activity_stats.get('today_promo', 0)}</span></div>
    <div class="stat-row"><span>Replies sent</span><span>{activity_stats.get('replies_sent_today', 0)}</span></div>
</div>

<script>
// Karma Growth Chart
const karmaCtx = document.getElementById('karmaChart').getContext('2d');
const karmaLabels = {json.dumps(karma_trend.get('labels', []))};
const karmaCumulative = {json.dumps(karma_trend.get('cumulative', []))};
const karmaDaily = {json.dumps(karma_trend.get('daily', []))};

if (karmaLabels.length > 0) {{
    new Chart(karmaCtx, {{
        type: 'line',
        data: {{
            labels: karmaLabels,
            datasets: [
                {{
                    label: 'Cumulative Karma',
                    data: karmaCumulative,
                    borderColor: '#ff6b35',
                    backgroundColor: 'rgba(255, 107, 53, 0.1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y',
                }},
                {{
                    label: 'Daily Karma',
                    data: karmaDaily,
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.3)',
                    type: 'bar',
                    yAxisID: 'y1',
                }}
            ]
        }},
        options: {{
            responsive: true,
            scales: {{
                y: {{ position: 'left', grid: {{ color: '#222' }}, ticks: {{ color: '#888' }} }},
                y1: {{ position: 'right', grid: {{ display: false }}, ticks: {{ color: '#888' }} }},
                x: {{ grid: {{ color: '#222' }}, ticks: {{ color: '#888' }} }}
            }},
            plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }}
        }}
    }});
}} else {{
    karmaCtx.font = '16px sans-serif';
    karmaCtx.fillStyle = '#666';
    karmaCtx.textAlign = 'center';
    karmaCtx.fillText('No karma data yet — run upvote-check mode to start tracking', karmaCtx.canvas.width / 2, 100);
}}
</script>

</body>
</html>"""

    return html


def _escape(text: str) -> str:
    """HTML-escape a string."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

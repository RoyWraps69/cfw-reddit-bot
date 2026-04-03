"""
Chicago Fleet Wraps — Unified Multi-Platform Dashboard v1.0
ONE DASHBOARD FOR ALL PLATFORMS

Generates a self-contained HTML dashboard showing:
- Overall engagement across all platforms
- Per-platform performance breakdown
- Cross-platform intelligence insights
- Damage control log
- Trending topics and content performance
- Best/worst performing content
- Karma/follower growth trends
- Active campaigns and their ROI
"""
import os
import json
from datetime import datetime
from config import DATA_DIR, LOG_DIR

DASHBOARD_OUTPUT = os.path.join(LOG_DIR, "unified_dashboard.html")


def generate_unified_dashboard() -> str:
    """Generate the unified multi-platform dashboard HTML."""
    os.makedirs(LOG_DIR, exist_ok=True)

    # Gather data from all sources
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reddit": _get_reddit_data(),
        "facebook": _get_platform_data("facebook"),
        "instagram": _get_platform_data("instagram"),
        "tiktok": _get_platform_data("tiktok"),
        "cross_intel": _get_cross_intel_data(),
        "damage": _get_damage_data(),
        "master_log": _get_master_log(),
        "trends": _get_trend_data(),
    }

    html = _render_html(data)

    with open(DASHBOARD_OUTPUT, "w") as f:
        f.write(html)

    print(f"  [DASHBOARD] Unified dashboard generated: {DASHBOARD_OUTPUT}", flush=True)
    return DASHBOARD_OUTPUT


def _load_json(filepath: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _get_reddit_data() -> dict:
    perf_summary = _load_json(os.path.join(DATA_DIR, "performance_summary.json"))
    perf_log = _load_json(os.path.join(DATA_DIR, "performance_log.json"), [])
    sub_profiles = _load_json(os.path.join(DATA_DIR, "sub_profiles.json"))
    competitor_data = _load_json(os.path.join(DATA_DIR, "competitor_mentions.json"), [])
    comment_history = _load_json(os.path.join(DATA_DIR, "comment_history.json"), [])
    replies_sent = _load_json(os.path.join(DATA_DIR, "replies_sent.json"), [])

    return {
        "total_comments": len(comment_history),
        "avg_score": perf_summary.get("overall_avg_score", 0),
        "total_tracked": perf_summary.get("total_tracked", 0),
        "best_comments": perf_summary.get("best_comments", [])[:5],
        "worst_comments": perf_summary.get("worst_comments", [])[:5],
        "by_subreddit": perf_summary.get("by_subreddit", {}),
        "by_length": perf_summary.get("by_length", {}),
        "sub_profiles_count": len(sub_profiles),
        "competitor_mentions": len(competitor_data),
        "replies_sent": len(replies_sent) if isinstance(replies_sent, list) else 0,
        "recent_scores": [e.get("score", 0) for e in perf_log[-20:]],
    }


def _get_platform_data(platform: str) -> dict:
    engagement = _load_json(os.path.join(DATA_DIR, f"{platform}_engagement.json"), [])
    posts = _load_json(os.path.join(DATA_DIR, f"{platform}_posts.json"), [])

    total_likes = sum(e.get("likes", 0) for e in engagement)
    total_comments = sum(e.get("comments", 0) for e in engagement)
    total_shares = sum(e.get("shares", 0) for e in engagement)

    return {
        "total_posts": len(posts),
        "total_engagement_records": len(engagement),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "recent_posts": posts[-5:] if isinstance(posts, list) else [],
    }


def _get_cross_intel_data() -> dict:
    return _load_json(os.path.join(DATA_DIR, "cross_platform_intel.json"))


def _get_damage_data() -> dict:
    damage_log = _load_json(os.path.join(DATA_DIR, "damage_control_log.json"), [])
    monitored = _load_json(os.path.join(DATA_DIR, "monitored_posts.json"), [])

    return {
        "total_deleted": len(damage_log),
        "currently_monitoring": sum(1 for p in monitored if p.get("status") == "active"),
        "recent_incidents": damage_log[-5:],
    }


def _get_master_log() -> list:
    return _load_json(os.path.join(LOG_DIR, "master_log.json"), [])[-10:]


def _get_trend_data() -> dict:
    return _load_json(os.path.join(DATA_DIR, "trend_cache.json"))


def _render_html(data: dict) -> str:
    reddit = data["reddit"]
    facebook = data["facebook"]
    instagram = data["instagram"]
    tiktok = data["tiktok"]
    cross = data["cross_intel"]
    damage = data["damage"]
    master_log = data["master_log"]

    # Build score trend data for chart
    reddit_scores = reddit.get("recent_scores", [])
    score_labels = list(range(1, len(reddit_scores) + 1))

    # Platform comparison data
    platform_posts = [reddit.get("total_comments", 0), facebook.get("total_posts", 0),
                      instagram.get("total_posts", 0), tiktok.get("total_posts", 0)]
    platform_engagement = [reddit.get("avg_score", 0) * reddit.get("total_tracked", 1),
                           facebook.get("total_likes", 0),
                           instagram.get("total_likes", 0),
                           tiktok.get("total_likes", 0)]

    # Cross-platform insights
    insights = cross.get("cross_insights", [])[:8]
    amplifications = cross.get("active_amplifications", [])[:5]
    suppressions = cross.get("active_suppressions", [])[:5]

    # Best Reddit comments
    best_comments_html = ""
    for c in reddit.get("best_comments", []):
        best_comments_html += f"""
        <div class="comment-card good">
            <div class="comment-score">+{c.get('score', 0)}</div>
            <div class="comment-body">
                <div class="comment-sub">r/{c.get('sub', '?')}</div>
                <div class="comment-text">{_escape(c.get('preview', '')[:120])}</div>
                <div class="comment-meta">{c.get('word_count', 0)} words</div>
            </div>
        </div>"""

    worst_comments_html = ""
    for c in reddit.get("worst_comments", []):
        worst_comments_html += f"""
        <div class="comment-card bad">
            <div class="comment-score">{c.get('score', 0)}</div>
            <div class="comment-body">
                <div class="comment-sub">r/{c.get('sub', '?')}</div>
                <div class="comment-text">{_escape(c.get('preview', '')[:120])}</div>
                <div class="comment-meta">{c.get('word_count', 0)} words</div>
            </div>
        </div>"""

    # Subreddit breakdown table
    sub_rows = ""
    for sub, stats in sorted(reddit.get("by_subreddit", {}).items(),
                             key=lambda x: x[1].get("avg_score", 0), reverse=True):
        sub_rows += f"""
        <tr>
            <td>r/{sub}</td>
            <td>{stats.get('avg_score', 0)}</td>
            <td>{stats.get('count', 0)}</td>
            <td>{stats.get('best_score', 0)}</td>
        </tr>"""

    # Cross-platform insights HTML
    insights_html = ""
    for ins in insights:
        ins_type = ins.get("type", "")
        if ins_type == "topic_divergence":
            insights_html += f"""
            <div class="insight-card divergence">
                <strong>{ins.get('topic', '')}</strong>: 
                {ins.get('winner', {}).get('platform', '').upper()} ({ins.get('winner', {}).get('avg_score', 0):.1f}) 
                vs {ins.get('loser', {}).get('platform', '').upper()} ({ins.get('loser', {}).get('avg_score', 0):.1f})
                — {ins.get('ratio', 0):.1f}x difference
            </div>"""
        elif ins_type == "universal_winner":
            insights_html += f"""
            <div class="insight-card winner">
                <strong>{ins.get('topic', '')}</strong>: Universal winner across all platforms
            </div>"""

    # Damage control HTML
    damage_html = ""
    for inc in damage.get("recent_incidents", []):
        damage_html += f"""
        <div class="damage-card">
            <span class="damage-platform">{inc.get('platform', '').upper()}</span>
            <span class="damage-topic">{_escape(inc.get('topic', '')[:60])}</span>
            <span class="damage-neg">{inc.get('negative_count', 0)} negative</span>
            <span class="damage-time">{inc.get('timestamp', '')[:16]}</span>
        </div>"""

    # Cycle log HTML
    cycle_html = ""
    for cycle in reversed(master_log[-5:]):
        ts = cycle.get("timestamp", "")[:16]
        topic = cycle.get("content_decision", {}).get("topic", "none")
        trends_count = cycle.get("trends", {}).get("topics_found", 0)
        dmg = cycle.get("damage_control", {})
        cycle_html += f"""
        <div class="cycle-card">
            <span class="cycle-time">{ts}</span>
            <span>Topic: {_escape(topic[:40])}</span>
            <span>Trends: {trends_count}</span>
            <span>Damage: {dmg.get('deleted', 0)} deleted</span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="10">
<title>CFW Social Media Command Center</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); padding: 30px; text-align: center; border-bottom: 3px solid #e94560; }}
.header h1 {{ font-size: 28px; color: #fff; margin-bottom: 5px; }}
.header p {{ color: #aaa; font-size: 14px; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

/* Quick Stats */
.stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
.stat-card {{ background: #1a1a2e; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #2a2a4a; }}
.stat-card.reddit {{ border-left: 4px solid #ff4500; }}
.stat-card.facebook {{ border-left: 4px solid #1877f2; }}
.stat-card.instagram {{ border-left: 4px solid #e1306c; }}
.stat-card.tiktok {{ border-left: 4px solid #00f2ea; }}
.stat-value {{ font-size: 32px; font-weight: bold; color: #fff; }}
.stat-label {{ font-size: 12px; color: #888; margin-top: 5px; text-transform: uppercase; }}
.stat-sub {{ font-size: 11px; color: #666; margin-top: 3px; }}

/* Section headers */
.section {{ margin: 30px 0; }}
.section h2 {{ font-size: 20px; color: #e94560; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #2a2a4a; }}

/* Charts */
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
.chart-box {{ background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }}
.chart-box h3 {{ font-size: 14px; color: #aaa; margin-bottom: 10px; }}

/* Comments */
.comment-card {{ display: flex; gap: 12px; padding: 12px; margin: 8px 0; background: #1a1a2e; border-radius: 8px; border: 1px solid #2a2a4a; }}
.comment-card.good {{ border-left: 3px solid #4caf50; }}
.comment-card.bad {{ border-left: 3px solid #f44336; }}
.comment-score {{ font-size: 20px; font-weight: bold; min-width: 40px; text-align: center; }}
.comment-card.good .comment-score {{ color: #4caf50; }}
.comment-card.bad .comment-score {{ color: #f44336; }}
.comment-sub {{ font-size: 11px; color: #e94560; }}
.comment-text {{ font-size: 13px; color: #ccc; margin: 4px 0; }}
.comment-meta {{ font-size: 11px; color: #666; }}

/* Table */
table {{ width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }}
th {{ background: #16213e; color: #e94560; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; }}
td {{ padding: 10px; border-bottom: 1px solid #2a2a4a; font-size: 13px; }}
tr:hover {{ background: #16213e; }}

/* Insights */
.insight-card {{ padding: 10px; margin: 6px 0; border-radius: 6px; font-size: 13px; }}
.insight-card.divergence {{ background: #1a1a2e; border-left: 3px solid #ff9800; }}
.insight-card.winner {{ background: #1a1a2e; border-left: 3px solid #4caf50; }}

/* Damage */
.damage-card {{ display: flex; gap: 15px; padding: 8px 12px; margin: 4px 0; background: #2a1a1a; border-radius: 6px; font-size: 12px; align-items: center; }}
.damage-platform {{ background: #f44336; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
.damage-neg {{ color: #f44336; font-weight: bold; }}
.damage-time {{ color: #666; margin-left: auto; }}

/* Cycle log */
.cycle-card {{ display: flex; gap: 20px; padding: 8px 12px; margin: 4px 0; background: #1a1a2e; border-radius: 6px; font-size: 12px; }}
.cycle-time {{ color: #e94560; font-weight: bold; }}

/* Two column */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}

@media (max-width: 768px) {{
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-grid, .two-col {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>CFW SOCIAL MEDIA COMMAND CENTER</h1>
    <p>Reddit | Facebook | Instagram | TikTok — Last updated: {data['generated_at']}</p>
</div>

<div class="container">

<!-- Quick Stats -->
<div class="stats-grid">
    <div class="stat-card reddit">
        <div class="stat-value">{reddit.get('total_comments', 0)}</div>
        <div class="stat-label">Reddit Comments</div>
        <div class="stat-sub">Avg score: {reddit.get('avg_score', 0)} | {reddit.get('total_tracked', 0)} tracked</div>
    </div>
    <div class="stat-card facebook">
        <div class="stat-value">{facebook.get('total_posts', 0)}</div>
        <div class="stat-label">Facebook Posts</div>
        <div class="stat-sub">{facebook.get('total_likes', 0)} likes | {facebook.get('total_comments', 0)} comments</div>
    </div>
    <div class="stat-card instagram">
        <div class="stat-value">{instagram.get('total_posts', 0)}</div>
        <div class="stat-label">Instagram Posts</div>
        <div class="stat-sub">{instagram.get('total_likes', 0)} likes | {instagram.get('total_comments', 0)} comments</div>
    </div>
    <div class="stat-card tiktok">
        <div class="stat-value">{tiktok.get('total_posts', 0)}</div>
        <div class="stat-label">TikTok Posts</div>
        <div class="stat-sub">{tiktok.get('total_likes', 0)} likes | {tiktok.get('total_shares', 0)} shares</div>
    </div>
</div>

<!-- System Health -->
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value">{reddit.get('sub_profiles_count', 0)}</div>
        <div class="stat-label">Sub Profiles Built</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{reddit.get('competitor_mentions', 0)}</div>
        <div class="stat-label">Competitor Mentions</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{damage.get('total_deleted', 0)}</div>
        <div class="stat-label">Posts Deleted (Damage Ctrl)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{len(cross.get('cross_insights', []))}</div>
        <div class="stat-label">Cross-Platform Insights</div>
    </div>
</div>

<!-- Charts -->
<div class="chart-grid">
    <div class="chart-box">
        <h3>Reddit Comment Scores (Recent)</h3>
        <canvas id="scoreChart" height="200"></canvas>
    </div>
    <div class="chart-box">
        <h3>Platform Activity Comparison</h3>
        <canvas id="platformChart" height="200"></canvas>
    </div>
</div>

<!-- Cross-Platform Intelligence -->
<div class="section">
    <h2>Cross-Platform Intelligence</h2>
    {insights_html if insights_html else '<p style="color:#666;">No cross-platform insights yet. Data will appear after multiple cycles.</p>'}
</div>

<!-- Best & Worst Comments -->
<div class="two-col">
    <div class="section">
        <h2>Top Performing Comments</h2>
        {best_comments_html if best_comments_html else '<p style="color:#666;">No tracked comments yet.</p>'}
    </div>
    <div class="section">
        <h2>Worst Performing Comments</h2>
        {worst_comments_html if worst_comments_html else '<p style="color:#666;">No tracked comments yet.</p>'}
    </div>
</div>

<!-- Subreddit Performance -->
<div class="section">
    <h2>Subreddit Performance</h2>
    <table>
        <tr><th>Subreddit</th><th>Avg Score</th><th>Comments</th><th>Best Score</th></tr>
        {sub_rows if sub_rows else '<tr><td colspan="4" style="color:#666;">No subreddit data yet.</td></tr>'}
    </table>
</div>

<!-- Damage Control -->
<div class="section">
    <h2>Damage Control Log</h2>
    <p style="color:#888; font-size:13px; margin-bottom:10px;">
        Monitoring: {damage.get('currently_monitoring', 0)} posts | 
        Total deleted: {damage.get('total_deleted', 0)}
    </p>
    {damage_html if damage_html else '<p style="color:#666;">No damage incidents. All posts performing well.</p>'}
</div>

<!-- Recent Cycles -->
<div class="section">
    <h2>Recent Orchestrator Cycles</h2>
    {cycle_html if cycle_html else '<p style="color:#666;">No cycle data yet.</p>'}
</div>

</div>

<script>
// Reddit Score Trend
new Chart(document.getElementById('scoreChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(score_labels)},
        datasets: [{{
            label: 'Comment Score',
            data: {json.dumps(reddit_scores)},
            borderColor: '#ff4500',
            backgroundColor: 'rgba(255,69,0,0.1)',
            fill: true,
            tension: 0.3,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }},
            y: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }}
        }}
    }}
}});

// Platform Comparison
new Chart(document.getElementById('platformChart'), {{
    type: 'bar',
    data: {{
        labels: ['Reddit', 'Facebook', 'Instagram', 'TikTok'],
        datasets: [
            {{
                label: 'Posts/Comments',
                data: {json.dumps(platform_posts)},
                backgroundColor: ['#ff4500', '#1877f2', '#e1306c', '#00f2ea'],
            }},
            {{
                label: 'Total Engagement',
                data: {json.dumps(platform_engagement)},
                backgroundColor: ['#ff6b35', '#4299e1', '#f56565', '#38b2ac'],
            }}
        ]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
        scales: {{
            x: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }},
            y: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }}
        }}
    }}
}});
</script>

</body>
</html>"""


def _escape(text: str) -> str:
    """Escape HTML characters."""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


if __name__ == "__main__":
    path = generate_unified_dashboard()
    print(f"Dashboard: {path}")

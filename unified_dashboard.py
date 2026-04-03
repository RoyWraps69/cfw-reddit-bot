"""
Chicago Fleet Wraps — Unified Multi-Platform Dashboard v2.0
ONE DASHBOARD FOR ALL PLATFORMS + CONTENT QUEUE + LEARNING ENGINE

Generates a self-contained HTML dashboard showing:
- Content Queue: all queued posts with image previews
- Posting Schedule: FB 4/day, IG 12/day timeline
- Learning Engine: engagement insights, top patterns
- Overall engagement across all platforms
- Per-platform performance breakdown
- Cross-platform intelligence insights
- Damage control log
- Weekly audit results
- Best/worst performing content
- Karma/follower growth trends
"""
import os
import json
from datetime import datetime
from config import DATA_DIR, LOG_DIR

DASHBOARD_OUTPUT = os.path.join(LOG_DIR, "unified_dashboard.html")
QUEUE_DIR = os.path.join(DATA_DIR, "content_queue")


def generate_unified_dashboard() -> str:
    """Generate the unified multi-platform dashboard HTML."""
    os.makedirs(LOG_DIR, exist_ok=True)

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
        "queue": _get_queue_data(),
        "schedule": _get_schedule_data(),
        "learning": _get_learning_data(),
        "audit": _get_audit_data(),
        "posted": _get_posted_data(),
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


def _get_queue_data() -> list:
    return _load_json(os.path.join(QUEUE_DIR, "queue.json"), [])


def _get_schedule_data() -> dict:
    return _load_json(os.path.join(QUEUE_DIR, "schedule.json"))


def _get_learning_data() -> dict:
    return _load_json(os.path.join(QUEUE_DIR, "learning.json"))


def _get_audit_data() -> list:
    return _load_json(os.path.join(QUEUE_DIR, "audit_log.json"), [])


def _get_posted_data() -> list:
    return _load_json(os.path.join(QUEUE_DIR, "posted.json"), [])


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _render_html(data: dict) -> str:
    reddit = data["reddit"]
    facebook = data["facebook"]
    instagram = data["instagram"]
    tiktok = data["tiktok"]
    cross = data["cross_intel"]
    damage = data["damage"]
    master_log = data["master_log"]
    queue = data["queue"]
    schedule = data["schedule"]
    learning = data["learning"]
    audit_log = data["audit"]
    posted = data["posted"]

    # Build score trend data for chart
    reddit_scores = reddit.get("recent_scores", [])
    score_labels = list(range(1, len(reddit_scores) + 1))

    platform_posts = [reddit.get("total_comments", 0), facebook.get("total_posts", 0),
                      instagram.get("total_posts", 0), tiktok.get("total_posts", 0)]
    platform_engagement = [reddit.get("avg_score", 0) * reddit.get("total_tracked", 1),
                           facebook.get("total_likes", 0),
                           instagram.get("total_likes", 0),
                           tiktok.get("total_likes", 0)]

    # Cross-platform insights
    insights = cross.get("cross_insights", [])[:8]
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

    # Best Reddit comments
    best_comments_html = ""
    for c in reddit.get("best_comments", []):
        link = c.get('url', c.get('permalink', ''))
        link_html = f'<a href="{link}" target="_blank" class="link-green">View ↗</a>' if link else ''
        best_comments_html += f"""
        <div class="comment-card good">
            <div class="comment-score">+{c.get('score', 0)}</div>
            <div class="comment-body">
                <div class="comment-sub">r/{c.get('sub', '?')} {link_html}</div>
                <div class="comment-text">{_escape(c.get('preview', '')[:120])}</div>
                <div class="comment-meta">{c.get('word_count', 0)} words</div>
            </div>
        </div>"""

    worst_comments_html = ""
    for c in reddit.get("worst_comments", []):
        link = c.get('url', c.get('permalink', ''))
        link_html = f'<a href="{link}" target="_blank" class="link-red">View ↗</a>' if link else ''
        worst_comments_html += f"""
        <div class="comment-card bad">
            <div class="comment-score">{c.get('score', 0)}</div>
            <div class="comment-body">
                <div class="comment-sub">r/{c.get('sub', '?')} {link_html}</div>
                <div class="comment-text">{_escape(c.get('preview', '')[:120])}</div>
                <div class="comment-meta">{c.get('word_count', 0)} words</div>
            </div>
        </div>"""

    # Subreddit breakdown
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

    # Damage control
    damage_html = ""
    for inc in damage.get("recent_incidents", []):
        damage_html += f"""
        <div class="damage-card">
            <span class="damage-platform">{inc.get('platform', '').upper()}</span>
            <span class="damage-topic">{_escape(inc.get('topic', '')[:60])}</span>
            <span class="damage-neg">{inc.get('negative_count', 0)} negative</span>
            <span class="damage-time">{inc.get('timestamp', '')[:16]}</span>
        </div>"""

    # Cycle log
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

    # ═══════════════════════════════════════════════════════════
    # CONTENT QUEUE SECTION
    # ═══════════════════════════════════════════════════════════
    queue_total = len(queue)
    queue_fb = len([q for q in queue if q.get("platform_target") in ("both", "facebook")])
    queue_ig = len([q for q in queue if q.get("platform_target") in ("both", "instagram")])
    days_of_content_fb = round(queue_fb / 4, 1) if queue_fb else 0
    days_of_content_ig = round(queue_ig / 12, 1) if queue_ig else 0

    queue_cards_html = ""
    for i, post in enumerate(queue):
        topic = post.get("decision", {}).get("topic", "Untitled")
        target = post.get("platform_target", "both")
        image_url = post.get("image_url", "")
        fb_cap = post.get("captions", {}).get("facebook", "")
        ig_cap = post.get("captions", {}).get("instagram", "")
        preview_cap = fb_cap[:150] if fb_cap else ig_cap[:150]

        target_badge = ""
        if target == "both":
            target_badge = '<span class="badge badge-fb">FB</span><span class="badge badge-ig">IG</span>'
        elif target == "facebook":
            target_badge = '<span class="badge badge-fb">FB</span>'
        elif target == "instagram":
            target_badge = '<span class="badge badge-ig">IG</span>'

        img_html = f'<img src="{image_url}" alt="{_escape(topic)}" class="queue-img" loading="lazy">' if image_url else '<div class="queue-img-placeholder">No Image</div>'

        queue_cards_html += f"""
        <div class="queue-card">
            {img_html}
            <div class="queue-card-body">
                <div class="queue-card-header">
                    <span class="queue-num">#{i+1}</span>
                    {target_badge}
                </div>
                <div class="queue-card-topic">{_escape(topic)}</div>
                <div class="queue-card-preview">{_escape(preview_cap)}...</div>
            </div>
        </div>"""

    # Quick Post queue picker items
    qp_queue_items = ""
    for i, post in enumerate(queue):
        topic = post.get("decision", {}).get("topic", "Untitled")
        image_url = post.get("image_url", "")
        qp_img = f'<img src="{image_url}" alt="{_escape(topic)}" loading="lazy">' if image_url else '<div style="height:100px;background:#2a2a4a;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#666;font-size:11px;">No Image</div>'
        qp_queue_items += f'<div class="qp-queue-item" id="qp-item-{i}" onclick="selectQueueItem({i})">{qp_img}<div class="title">#{i+1}: {_escape(topic[:40])}</div></div>'
    if not queue:
        qp_queue_items = '<p style="color:#666;">Queue is empty. Click Refill Queue below to generate new content.</p>'

    # ═══════════════════════════════════════════════════════════
    # POSTING SCHEDULE SECTION
    # ═══════════════════════════════════════════════════════════
    fb_schedule = schedule.get("facebook", {})
    ig_schedule = schedule.get("instagram", {})
    fb_slots = fb_schedule.get("slots", [])
    ig_slots = ig_schedule.get("slots", [])
    schedule_opt_count = schedule.get("optimization_count", 0)

    # Build timeline data for chart
    fb_slot_hours = [s.get("hour", 0) for s in fb_slots]
    ig_slot_hours = [s.get("hour", 0) for s in ig_slots]

    # Schedule table rows
    fb_schedule_rows = ""
    for s in sorted(fb_slots, key=lambda x: x.get("hour", 0)):
        h = s.get("hour", 0)
        m = s.get("minute", 0)
        label = s.get("label", "")
        ampm = "AM" if h < 12 else "PM"
        h12 = h if h <= 12 else h - 12
        if h12 == 0:
            h12 = 12
        fb_schedule_rows += f'<tr><td>{h12}:{m:02d} {ampm}</td><td>{label}</td><td class="slot-fb">Facebook</td></tr>'

    ig_schedule_rows = ""
    for s in sorted(ig_slots, key=lambda x: x.get("hour", 0)):
        h = s.get("hour", 0)
        m = s.get("minute", 0)
        label = s.get("label", "")
        ampm = "AM" if h < 12 else "PM"
        h12 = h if h <= 12 else h - 12
        if h12 == 0:
            h12 = 12
        ig_schedule_rows += f'<tr><td>{h12}:{m:02d} {ampm}</td><td>{label}</td><td class="slot-ig">Instagram</td></tr>'

    # ═══════════════════════════════════════════════════════════
    # LEARNING ENGINE SECTION
    # ═══════════════════════════════════════════════════════════
    learn_total = learning.get("total_posts_analyzed", 0)
    learn_avg = learning.get("avg_score", 0)
    learn_best = learning.get("best_score", 0)
    learn_trend = learning.get("trend_direction", "N/A")
    learn_insights = learning.get("insights_summary", "")
    learn_top_topics = learning.get("top_performing_topics", [])
    learn_avoid = learning.get("underperforming_topics", [])
    learn_hooks = learning.get("top_hooks", [])
    learn_questions = learning.get("best_engagement_questions", [])

    top_topics_html = ""
    for t in learn_top_topics[:8]:
        top_topics_html += f'<span class="tag tag-green">{_escape(t)}</span>'

    avoid_topics_html = ""
    for t in learn_avoid[:8]:
        avoid_topics_html += f'<span class="tag tag-red">{_escape(t)}</span>'

    hooks_html = ""
    for h in learn_hooks[:5]:
        hooks_html += f'<div class="hook-item">{_escape(h)}</div>'

    questions_html = ""
    for q in learn_questions[:5]:
        questions_html += f'<div class="question-item">{_escape(q)}</div>'

    # ═══════════════════════════════════════════════════════════
    # WEEKLY AUDIT SECTION
    # ═══════════════════════════════════════════════════════════
    latest_audit = audit_log[-1] if audit_log else {}
    audit_date = latest_audit.get("date", "No audits yet")[:10]
    audit_fb = latest_audit.get("facebook", {})
    audit_ig = latest_audit.get("instagram", {})
    audit_recs = latest_audit.get("recommendations", [])

    audit_recs_html = ""
    for rec in audit_recs:
        if rec.strip():
            audit_recs_html += f'<div class="rec-item">{_escape(rec.strip())}</div>'

    # Build audit history rows
    audit_history_rows = ""
    if audit_log:
        for a in reversed(audit_log[-10:]):
            a_date = a.get('date', '')[:10]
            a_fb_posts = a.get('facebook', {}).get('posts_this_week', 0)
            a_fb_score = a.get('facebook', {}).get('avg_score', 0)
            a_ig_posts = a.get('instagram', {}).get('posts_this_week', 0)
            a_ig_score = a.get('instagram', {}).get('avg_score', 0)
            audit_history_rows += f'<tr><td>{a_date}</td><td>{a_fb_posts}</td><td>{a_fb_score}</td><td>{a_ig_posts}</td><td>{a_ig_score}</td></tr>'
    else:
        audit_history_rows = '<tr><td colspan="5" style="color:#666;">No audit history yet.</td></tr>'

    # ═══════════════════════════════════════════════════════════
    # POSTED HISTORY (engagement scores over time)
    # ═══════════════════════════════════════════════════════════
    posted_scores = [p.get("score", 0) for p in posted[-30:]]
    posted_labels = list(range(1, len(posted_scores) + 1))
    posted_total = len(posted)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CFW Social Media Command Center v2.0</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; }}

/* Header */
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); padding: 30px; text-align: center; border-bottom: 3px solid #e94560; position: relative; }}
.header h1 {{ font-size: 28px; color: #fff; margin-bottom: 5px; letter-spacing: 2px; }}
.header p {{ color: #aaa; font-size: 14px; }}
.header .version {{ position: absolute; top: 10px; right: 20px; background: #e94560; color: #fff; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }}

.container {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}

/* Nav Tabs */
.nav-tabs {{ display: flex; gap: 4px; margin: 20px 0; background: #1a1a2e; border-radius: 12px; padding: 4px; overflow-x: auto; }}
.nav-tab {{ padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; color: #888; transition: all 0.2s; white-space: nowrap; border: none; background: none; }}
.nav-tab:hover {{ color: #fff; background: #2a2a4a; }}
.nav-tab.active {{ color: #fff; background: #e94560; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

/* Quick Stats */
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
.stat-card {{ background: #1a1a2e; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #2a2a4a; transition: transform 0.2s; }}
.stat-card:hover {{ transform: translateY(-2px); }}
.stat-card.reddit {{ border-left: 4px solid #ff4500; }}
.stat-card.facebook {{ border-left: 4px solid #1877f2; }}
.stat-card.instagram {{ border-left: 4px solid #e1306c; }}
.stat-card.tiktok {{ border-left: 4px solid #00f2ea; }}
.stat-card.queue {{ border-left: 4px solid #ffd700; }}
.stat-card.learning {{ border-left: 4px solid #9b59b6; }}
.stat-value {{ font-size: 32px; font-weight: bold; color: #fff; }}
.stat-label {{ font-size: 12px; color: #888; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }}
.stat-sub {{ font-size: 11px; color: #666; margin-top: 3px; }}

/* Section headers */
.section {{ margin: 30px 0; }}
.section h2 {{ font-size: 20px; color: #e94560; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #2a2a4a; }}

/* Charts */
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
.chart-box {{ background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }}
.chart-box h3 {{ font-size: 14px; color: #aaa; margin-bottom: 10px; }}

/* Queue Cards */
.queue-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin: 20px 0; }}
.queue-card {{ background: #1a1a2e; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a4a; transition: transform 0.2s, box-shadow 0.2s; }}
.queue-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 25px rgba(233,69,96,0.15); }}
.queue-img {{ width: 100%; height: 180px; object-fit: cover; display: block; }}
.queue-img-placeholder {{ width: 100%; height: 180px; background: #2a2a4a; display: flex; align-items: center; justify-content: center; color: #666; font-size: 14px; }}
.queue-card-body {{ padding: 14px; }}
.queue-card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
.queue-num {{ background: #e94560; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }}
.queue-card-topic {{ font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 6px; line-height: 1.3; }}
.queue-card-preview {{ font-size: 12px; color: #888; line-height: 1.4; }}

/* Badges */
.badge {{ padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; color: #fff; }}
.badge-fb {{ background: #1877f2; }}
.badge-ig {{ background: #e1306c; }}
.badge-both {{ background: #9b59b6; }}

/* Schedule */
.schedule-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.schedule-panel {{ background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }}
.schedule-panel h3 {{ font-size: 16px; margin-bottom: 12px; }}
.schedule-panel.fb h3 {{ color: #1877f2; }}
.schedule-panel.ig h3 {{ color: #e1306c; }}

/* Timeline */
.timeline {{ position: relative; padding: 10px 0; }}
.timeline-bar {{ position: relative; height: 40px; background: #16213e; border-radius: 20px; margin: 10px 0; overflow: hidden; }}
.timeline-dot {{ position: absolute; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; border-radius: 50%; z-index: 2; }}
.timeline-dot.fb {{ background: #1877f2; box-shadow: 0 0 8px rgba(24,119,242,0.5); }}
.timeline-dot.ig {{ background: #e1306c; box-shadow: 0 0 8px rgba(225,48,108,0.5); }}
.timeline-labels {{ display: flex; justify-content: space-between; font-size: 10px; color: #666; padding: 0 5px; }}

/* Table */
table {{ width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }}
th {{ background: #16213e; color: #e94560; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; }}
td {{ padding: 10px; border-bottom: 1px solid #2a2a4a; font-size: 13px; }}
tr:hover {{ background: #16213e; }}
.slot-fb {{ color: #1877f2; font-weight: bold; }}
.slot-ig {{ color: #e1306c; font-weight: bold; }}

/* Learning Tags */
.tags-container {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
.tag {{ padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; }}
.tag-green {{ background: rgba(76,175,80,0.15); color: #4caf50; border: 1px solid rgba(76,175,80,0.3); }}
.tag-red {{ background: rgba(244,67,54,0.15); color: #f44336; border: 1px solid rgba(244,67,54,0.3); }}
.tag-blue {{ background: rgba(33,150,243,0.15); color: #2196f3; border: 1px solid rgba(33,150,243,0.3); }}

/* Hooks & Questions */
.hook-item, .question-item {{ padding: 10px 14px; margin: 6px 0; background: #16213e; border-radius: 8px; font-size: 13px; line-height: 1.4; }}
.hook-item {{ border-left: 3px solid #ffd700; color: #ddd; }}
.question-item {{ border-left: 3px solid #e1306c; color: #ddd; }}

/* Quick Post */
.quickpost-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.quickpost-panel {{ background: #1a1a2e; border-radius: 12px; padding: 24px; border: 1px solid #2a2a4a; }}
.quickpost-panel h3 {{ color: #4caf50; margin-bottom: 16px; font-size: 18px; }}
.quickpost-panel.custom h3 {{ color: #ffd700; }}
.qp-textarea {{ width: 100%; min-height: 120px; background: #0a0a0f; border: 1px solid #2a2a4a; border-radius: 8px; color: #e0e0e0; padding: 12px; font-size: 14px; font-family: inherit; resize: vertical; }}
.qp-textarea:focus {{ outline: none; border-color: #4caf50; }}
.qp-input {{ width: 100%; background: #0a0a0f; border: 1px solid #2a2a4a; border-radius: 8px; color: #e0e0e0; padding: 10px 12px; font-size: 14px; font-family: inherit; margin-bottom: 10px; }}
.qp-input:focus {{ outline: none; border-color: #ffd700; }}
.qp-btn {{ padding: 12px 24px; border-radius: 8px; border: none; font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.2s; text-transform: uppercase; letter-spacing: 1px; }}
.qp-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
.qp-btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
.qp-btn-fb {{ background: #1877f2; color: #fff; }}
.qp-btn-ig {{ background: #e1306c; color: #fff; }}
.qp-btn-both {{ background: linear-gradient(135deg, #1877f2, #e1306c); color: #fff; }}
.qp-btn-queue {{ background: #4caf50; color: #fff; }}
.qp-btn-custom {{ background: #ffd700; color: #000; }}
.qp-btn-refill {{ background: #9b59b6; color: #fff; }}
.qp-select {{ width: 100%; background: #0a0a0f; border: 1px solid #2a2a4a; border-radius: 8px; color: #e0e0e0; padding: 10px 12px; font-size: 14px; margin-bottom: 10px; }}
.qp-status {{ margin-top: 12px; padding: 10px; border-radius: 8px; font-size: 13px; display: none; }}
.qp-status.success {{ display: block; background: rgba(76,175,80,0.15); color: #4caf50; border: 1px solid rgba(76,175,80,0.3); }}
.qp-status.error {{ display: block; background: rgba(244,67,54,0.15); color: #f44336; border: 1px solid rgba(244,67,54,0.3); }}
.qp-status.loading {{ display: block; background: rgba(255,152,0,0.15); color: #ff9800; border: 1px solid rgba(255,152,0,0.3); }}
.qp-queue-pick {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin: 12px 0; max-height: 400px; overflow-y: auto; }}
.qp-queue-item {{ background: #16213e; border-radius: 8px; padding: 10px; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; }}
.qp-queue-item:hover {{ border-color: #4caf50; }}
.qp-queue-item.selected {{ border-color: #4caf50; background: rgba(76,175,80,0.1); }}
.qp-queue-item img {{ width: 100%; height: 100px; object-fit: cover; border-radius: 6px; margin-bottom: 6px; }}
.qp-queue-item .title {{ font-size: 12px; color: #fff; font-weight: 600; }}
.qp-actions {{ display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }}

/* Insights box */
.insights-box {{ background: linear-gradient(135deg, #1a1a2e, #16213e); border: 1px solid #9b59b6; border-radius: 12px; padding: 20px; margin: 15px 0; }}
.insights-box h3 {{ color: #9b59b6; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
.insights-box p {{ color: #ccc; font-size: 14px; line-height: 1.6; }}

/* Audit */
.rec-item {{ padding: 10px 14px; margin: 6px 0; background: #1a1a2e; border-radius: 8px; font-size: 13px; border-left: 3px solid #2196f3; color: #ccc; line-height: 1.4; }}

/* Trend indicator */
.trend {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
.trend-up {{ background: rgba(76,175,80,0.2); color: #4caf50; }}
.trend-learning {{ background: rgba(255,152,0,0.2); color: #ff9800; }}

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

/* Links */
.link-green {{ color: #4caf50; text-decoration: none; font-size: 11px; }}
.link-red {{ color: #f44336; text-decoration: none; font-size: 11px; }}

/* Two column */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}

/* Responsive */
@media (max-width: 900px) {{
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-grid, .two-col, .schedule-grid {{ grid-template-columns: 1fr; }}
    .queue-grid {{ grid-template-columns: 1fr; }}
    .nav-tabs {{ flex-wrap: wrap; }}
}}
</style>
</head>
<body>

<div class="header">
    <span class="version">v2.0</span>
    <h1>CFW SOCIAL MEDIA COMMAND CENTER</h1>
    <p>Content Queue + Learning Engine + Multi-Platform Analytics — Last updated: {data['generated_at']}</p>
</div>

<div class="container">

<!-- Navigation Tabs -->
<div class="nav-tabs">
    <button class="nav-tab active" onclick="showTab('overview')">Overview</button>
    <button class="nav-tab" onclick="showTab('queue')">Content Queue ({queue_total})</button>
    <button class="nav-tab" onclick="showTab('schedule')">Schedule</button>
    <button class="nav-tab" onclick="showTab('learning')">Learning Engine</button>
    <button class="nav-tab" onclick="showTab('reddit')">Reddit</button>
    <button class="nav-tab" onclick="showTab('social')">FB / IG / TT</button>
    <button class="nav-tab" onclick="showTab('intel')">Intelligence</button>
    <button class="nav-tab" onclick="showTab('audit')">Weekly Audit</button>
    <button class="nav-tab" onclick="showTab('quickpost')" style="background:#4caf50;color:#fff;">⚡ Quick Post</button>
</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: OVERVIEW -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-overview" class="tab-content active">

<div class="stats-grid">
    <div class="stat-card queue">
        <div class="stat-value">{queue_total}</div>
        <div class="stat-label">Posts in Queue</div>
        <div class="stat-sub">FB: {days_of_content_fb} days | IG: {days_of_content_ig} days of content</div>
    </div>
    <div class="stat-card learning">
        <div class="stat-value">{learn_total}</div>
        <div class="stat-label">Posts Analyzed</div>
        <div class="stat-sub">Avg score: {learn_avg} | <span class="trend {'trend-up' if learn_trend == 'improving' else 'trend-learning'}">{learn_trend}</span></div>
    </div>
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
        <div class="stat-value">{schedule_opt_count}</div>
        <div class="stat-label">Schedule Optimizations</div>
    </div>
</div>

<!-- Charts -->
<div class="chart-grid">
    <div class="chart-box">
        <h3>Engagement Score Trend (Posted Content)</h3>
        <canvas id="engagementChart" height="200"></canvas>
    </div>
    <div class="chart-box">
        <h3>Platform Activity Comparison</h3>
        <canvas id="platformChart" height="200"></canvas>
    </div>
</div>

<!-- 24-Hour Posting Timeline -->
<div class="section">
    <h2>24-Hour Posting Timeline</h2>
    <div class="chart-box">
        <h3>Facebook (4/day) + Instagram (12/day) — Posting Slots</h3>
        <canvas id="timelineChart" height="120"></canvas>
    </div>
</div>

{f'''<div class="insights-box">
    <h3>AI Learning Insights</h3>
    <p>{_escape(learn_insights)}</p>
</div>''' if learn_insights else ''}

<!-- Recent Activity Feed -->
<div class="section">
    <h2>Recent Activity Feed</h2>
    {_build_activity_feed(data)}
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: CONTENT QUEUE -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-queue" class="tab-content">

<div class="stats-grid">
    <div class="stat-card queue">
        <div class="stat-value">{queue_total}</div>
        <div class="stat-label">Total in Queue</div>
    </div>
    <div class="stat-card facebook">
        <div class="stat-value">{queue_fb}</div>
        <div class="stat-label">FB-Eligible</div>
        <div class="stat-sub">{days_of_content_fb} days at 4/day</div>
    </div>
    <div class="stat-card instagram">
        <div class="stat-value">{queue_ig}</div>
        <div class="stat-label">IG-Eligible</div>
        <div class="stat-sub">{days_of_content_ig} days at 12/day</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{posted_total}</div>
        <div class="stat-label">Total Posted</div>
    </div>
</div>

<div class="section">
    <h2>Queued Posts — Ready to Fire</h2>
    <div class="queue-grid">
        {queue_cards_html if queue_cards_html else '<p style="color:#666;">Queue is empty. Trigger a refill to generate new content.</p>'}
    </div>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: SCHEDULE -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-schedule" class="tab-content">

<div class="stats-grid">
    <div class="stat-card facebook">
        <div class="stat-value">{len(fb_slots)}</div>
        <div class="stat-label">FB Slots / Day</div>
    </div>
    <div class="stat-card instagram">
        <div class="stat-value">{len(ig_slots)}</div>
        <div class="stat-label">IG Slots / Day</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{schedule_opt_count}</div>
        <div class="stat-label">Optimizations Run</div>
    </div>
    <div class="stat-card learning">
        <div class="stat-value">{len(fb_slots) + len(ig_slots)}</div>
        <div class="stat-label">Total Daily Posts</div>
    </div>
</div>

<div class="section">
    <h2>Daily Posting Schedule (CDT)</h2>
    <div class="schedule-grid">
        <div class="schedule-panel fb">
            <h3>Facebook — {len(fb_slots)} Posts/Day</h3>
            <table>
                <tr><th>Time</th><th>Slot</th><th>Platform</th></tr>
                {fb_schedule_rows if fb_schedule_rows else '<tr><td colspan="3" style="color:#666;">No schedule configured</td></tr>'}
            </table>
        </div>
        <div class="schedule-panel ig">
            <h3>Instagram — {len(ig_slots)} Posts/Day</h3>
            <table>
                <tr><th>Time</th><th>Slot</th><th>Platform</th></tr>
                {ig_schedule_rows if ig_schedule_rows else '<tr><td colspan="3" style="color:#666;">No schedule configured</td></tr>'}
            </table>
        </div>
    </div>
</div>

<div class="section">
    <h2>24-Hour Timeline Visualization</h2>
    <div class="chart-box">
        <canvas id="scheduleDetailChart" height="150"></canvas>
    </div>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: LEARNING ENGINE -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-learning" class="tab-content">

<div class="stats-grid">
    <div class="stat-card learning">
        <div class="stat-value">{learn_total}</div>
        <div class="stat-label">Posts Analyzed</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{learn_avg}</div>
        <div class="stat-label">Avg Engagement Score</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{learn_best}</div>
        <div class="stat-label">Best Score</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><span class="trend {'trend-up' if learn_trend == 'improving' else 'trend-learning'}">{learn_trend}</span></div>
        <div class="stat-label">Trend Direction</div>
    </div>
</div>

{f'''<div class="insights-box">
    <h3>AI-Generated Performance Insights</h3>
    <p>{_escape(learn_insights)}</p>
</div>''' if learn_insights else '<div class="insights-box"><h3>AI-Generated Performance Insights</h3><p style="color:#666;">Not enough data yet. Insights will appear after 5+ posts are analyzed.</p></div>'}

<div class="two-col">
    <div class="section">
        <h2>Top Performing Topics</h2>
        <div class="tags-container">
            {top_topics_html if top_topics_html else '<span style="color:#666;">No data yet</span>'}
        </div>
    </div>
    <div class="section">
        <h2>Topics to Avoid</h2>
        <div class="tags-container">
            {avoid_topics_html if avoid_topics_html else '<span style="color:#666;">No data yet</span>'}
        </div>
    </div>
</div>

<div class="section">
    <h2>Hooks That Worked</h2>
    {hooks_html if hooks_html else '<p style="color:#666;">No hook data yet. Will populate after engagement analysis.</p>'}
</div>

<div class="section">
    <h2>Best Engagement Questions</h2>
    {questions_html if questions_html else '<p style="color:#666;">No question performance data yet.</p>'}
</div>

<div class="section">
    <h2>Engagement Score Over Time</h2>
    <div class="chart-box">
        <canvas id="learningTrendChart" height="200"></canvas>
    </div>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: REDDIT -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-reddit" class="tab-content">

<div class="chart-grid">
    <div class="chart-box">
        <h3>Reddit Comment Scores (Recent)</h3>
        <canvas id="redditScoreChart" height="200"></canvas>
    </div>
    <div class="chart-box">
        <h3>Score Distribution</h3>
        <canvas id="redditDistChart" height="200"></canvas>
    </div>
</div>

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

<div class="section">
    <h2>Subreddit Performance</h2>
    <table>
        <tr><th>Subreddit</th><th>Avg Score</th><th>Comments</th><th>Best Score</th></tr>
        {sub_rows if sub_rows else '<tr><td colspan="4" style="color:#666;">No subreddit data yet.</td></tr>'}
    </table>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: SOCIAL (FB/IG/TT) -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-social" class="tab-content">

<div class="stats-grid">
    <div class="stat-card facebook">
        <div class="stat-value">{facebook.get('total_posts', 0)}</div>
        <div class="stat-label">Facebook Posts</div>
        <div class="stat-sub">{facebook.get('total_likes', 0)} likes | {facebook.get('total_comments', 0)} comments | {facebook.get('total_shares', 0)} shares</div>
    </div>
    <div class="stat-card instagram">
        <div class="stat-value">{instagram.get('total_posts', 0)}</div>
        <div class="stat-label">Instagram Posts</div>
        <div class="stat-sub">{instagram.get('total_likes', 0)} likes | {instagram.get('total_comments', 0)} comments | {instagram.get('total_shares', 0)} shares</div>
    </div>
    <div class="stat-card tiktok">
        <div class="stat-value">{tiktok.get('total_posts', 0)}</div>
        <div class="stat-label">TikTok Posts</div>
        <div class="stat-sub">{tiktok.get('total_likes', 0)} likes | {tiktok.get('total_shares', 0)} shares</div>
    </div>
</div>

<!-- Cross-Platform Intelligence -->
<div class="section">
    <h2>Cross-Platform Intelligence</h2>
    {insights_html if insights_html else '<p style="color:#666;">No cross-platform insights yet.</p>'}
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

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: INTELLIGENCE -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-intel" class="tab-content">

<div class="section">
    <h2>Content Strategy Overview</h2>
    <div class="two-col">
        <div class="insights-box">
            <h3>Facebook Strategy</h3>
            <p><strong>Cadence:</strong> 4 posts/day<br>
            <strong>Focus:</strong> Business owner pain points, ROI, fleet branding<br>
            <strong>Tone:</strong> Professional, educational, data-driven<br>
            <strong>CTA:</strong> Every post ends with an engagement question<br>
            <strong>Geo:</strong> 4711 N Lamon Ave, Chicago IL 60630</p>
        </div>
        <div class="insights-box">
            <h3>Instagram Strategy</h3>
            <p><strong>Cadence:</strong> 12 posts/day<br>
            <strong>Focus:</strong> Wrap tips, behind-the-scenes, insider knowledge<br>
            <strong>Tone:</strong> Casual expert, visual-first<br>
            <strong>CTA:</strong> Free wrap knowledge giveaways, build audience<br>
            <strong>Geo:</strong> 4711 N Lamon Ave, Chicago IL 60630</p>
        </div>
    </div>
</div>

<div class="section">
    <h2>Cross-Platform Intelligence</h2>
    {insights_html if insights_html else '<p style="color:#666;">No cross-platform insights yet. Data will appear after multiple cycles.</p>'}
</div>

<div class="section">
    <h2>Competitive Landscape</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{reddit.get('competitor_mentions', 0)}</div>
            <div class="stat-label">Competitor Mentions Tracked</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{reddit.get('sub_profiles_count', 0)}</div>
            <div class="stat-label">Subreddit Profiles</div>
        </div>
    </div>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: WEEKLY AUDIT -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-audit" class="tab-content">

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value">{len(audit_log)}</div>
        <div class="stat-label">Audits Completed</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{audit_date}</div>
        <div class="stat-label">Last Audit Date</div>
    </div>
    <div class="stat-card facebook">
        <div class="stat-value">{audit_fb.get('posts_this_week', 0)}/{audit_fb.get('target_posts', 28)}</div>
        <div class="stat-label">FB Posts (Last Week)</div>
        <div class="stat-sub">Avg score: {audit_fb.get('avg_score', 0)}</div>
    </div>
    <div class="stat-card instagram">
        <div class="stat-value">{audit_ig.get('posts_this_week', 0)}/{audit_ig.get('target_posts', 84)}</div>
        <div class="stat-label">IG Posts (Last Week)</div>
        <div class="stat-sub">Avg score: {audit_ig.get('avg_score', 0)}</div>
    </div>
</div>

<div class="section">
    <h2>AI Recommendations</h2>
    {audit_recs_html if audit_recs_html else '<p style="color:#666;">No audit recommendations yet. First audit will run after 7 days of posting.</p>'}
</div>

<div class="section">
    <h2>Audit History</h2>
    <table>
        <tr><th>Date</th><th>FB Posts</th><th>FB Avg Score</th><th>IG Posts</th><th>IG Avg Score</th></tr>
        {audit_history_rows}
    </table>
</div>

</div>

<!-- ═══════════════════════════════════════════════ -->
<!-- TAB: QUICK POST -->
<!-- ═══════════════════════════════════════════════ -->
<div id="tab-quickpost" class="tab-content">

<div class="quickpost-grid">

    <!-- LEFT: Post from Queue -->
    <div class="quickpost-panel">
        <h3>⚡ Post from Queue</h3>
        <p style="color:#888;font-size:13px;margin-bottom:12px;">Select a queued post and fire it to Facebook, Instagram, or both.</p>
        
        <div class="qp-queue-pick" id="qpQueuePick">
            {qp_queue_items}
        </div>
        
        <div class="qp-actions">
            <button class="qp-btn qp-btn-fb" onclick="triggerQueuePost('facebook')" id="qpBtnFb">Post to Facebook</button>
            <button class="qp-btn qp-btn-ig" onclick="triggerQueuePost('instagram')" id="qpBtnIg">Post to Instagram</button>
            <button class="qp-btn qp-btn-both" onclick="triggerQueuePost('both')" id="qpBtnBoth">Post to Both</button>
        </div>
        <div id="qpQueueStatus" class="qp-status"></div>
    </div>

    <!-- RIGHT: Custom Post -->
    <div class="quickpost-panel custom">
        <h3>✏️ Write a Custom Post</h3>
        <p style="color:#888;font-size:13px;margin-bottom:12px;">Write your own caption and post it manually to any platform.</p>
        
        <input type="text" class="qp-input" id="qpImageUrl" placeholder="Image URL (paste a link to any image — optional)">
        <textarea class="qp-textarea" id="qpCaption" placeholder="Write your caption here...

Tip: End with a question to boost engagement!

#ChicagoFleetWraps #VehicleWrap #FleetBranding"></textarea>
        
        <div style="margin-top:10px;">
            <label style="color:#888;font-size:12px;">Post to:</label>
            <select class="qp-select" id="qpPlatform">
                <option value="both">Both (Facebook + Instagram)</option>
                <option value="facebook">Facebook Only</option>
                <option value="instagram">Instagram Only</option>
            </select>
        </div>
        
        <div class="qp-actions">
            <button class="qp-btn qp-btn-custom" onclick="triggerCustomPost()">Publish Custom Post</button>
        </div>
        <div id="qpCustomStatus" class="qp-status"></div>
    </div>

</div>

<div style="margin-top:20px;">
    <div class="quickpost-panel" style="border-color:#9b59b6;">
        <h3 style="color:#9b59b6;">🔧 Quick Actions</h3>
        <div class="qp-actions">
            <button class="qp-btn qp-btn-refill" onclick="triggerMode('refill')">🔄 Refill Queue</button>
            <button class="qp-btn qp-btn-queue" onclick="triggerMode('learn')">🧠 Run Learning</button>
            <button class="qp-btn" style="background:#e94560;color:#fff;" onclick="triggerMode('dashboard')">📊 Refresh Dashboard</button>
            <button class="qp-btn" style="background:#ff9800;color:#fff;" onclick="triggerMode('social')">📱 Run Social Cycle</button>
            <button class="qp-btn" style="background:#00f2ea;color:#000;" onclick="triggerMode('full')">🚀 Full Engine Run</button>
        </div>
        <div id="qpActionStatus" class="qp-status"></div>
    </div>
</div>

</div>

</div><!-- /container -->

<script>
// GitHub API config for Quick Post
const GH_TOKEN = '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';
const GH_REPO = 'RoyWraps69/cfw-reddit-bot';
const GH_WORKFLOW = 'bot.yml';

let selectedQueueIdx = -1;

function selectQueueItem(idx) {{
    document.querySelectorAll('.qp-queue-item').forEach(el => el.classList.remove('selected'));
    document.getElementById('qp-item-' + idx).classList.add('selected');
    selectedQueueIdx = idx;
}}

async function triggerWorkflow(mode, extraRef) {{
    const url = `https://api.github.com/repos/${{GH_REPO}}/actions/workflows/${{GH_WORKFLOW}}/dispatches`;
    const body = {{
        ref: 'master',
        inputs: {{ mode: mode }}
    }};
    const resp = await fetch(url, {{
        method: 'POST',
        headers: {{
            'Authorization': `token ${{GH_TOKEN}}`,
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }},
        body: JSON.stringify(body)
    }});
    return resp;
}}

async function triggerQueuePost(platform) {{
    const statusEl = document.getElementById('qpQueueStatus');
    if (selectedQueueIdx < 0) {{
        statusEl.className = 'qp-status error';
        statusEl.textContent = 'Please select a post from the queue first.';
        return;
    }}
    statusEl.className = 'qp-status loading';
    statusEl.textContent = `Triggering post #${{selectedQueueIdx + 1}} to ${{platform}}... Please wait.`;
    try {{
        const resp = await triggerWorkflow('post');
        if (resp.status === 204) {{
            statusEl.className = 'qp-status success';
            statusEl.textContent = `Post triggered successfully! The next queued post will be published to ${{platform}}. Check GitHub Actions for status.`;
        }} else {{
            const data = await resp.json();
            statusEl.className = 'qp-status error';
            statusEl.textContent = `Error: ${{data.message || resp.statusText}}`;
        }}
    }} catch (e) {{
        statusEl.className = 'qp-status error';
        statusEl.textContent = `Network error: ${{e.message}}`;
    }}
}}

async function triggerCustomPost() {{
    const caption = document.getElementById('qpCaption').value.trim();
    const imageUrl = document.getElementById('qpImageUrl').value.trim();
    const platform = document.getElementById('qpPlatform').value;
    const statusEl = document.getElementById('qpCustomStatus');
    
    if (!caption) {{
        statusEl.className = 'qp-status error';
        statusEl.textContent = 'Please write a caption first.';
        return;
    }}
    
    statusEl.className = 'qp-status loading';
    statusEl.textContent = 'Triggering custom post...';
    
    try {{
        // Save the custom post data to a gist, then trigger the workflow
        const gistResp = await fetch('https://api.github.com/gists', {{
            method: 'POST',
            headers: {{
                'Authorization': `token ${{GH_TOKEN}}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{
                description: 'CFW Quick Post Data',
                public: false,
                files: {{
                    'quick_post.json': {{
                        content: JSON.stringify({{
                            caption: caption,
                            image_url: imageUrl,
                            platform: platform,
                            timestamp: new Date().toISOString()
                        }}, null, 2)
                    }}
                }}
            }})
        }});
        
        if (gistResp.ok) {{
            // Now trigger the post workflow
            const resp = await triggerWorkflow('post');
            if (resp.status === 204) {{
                statusEl.className = 'qp-status success';
                statusEl.textContent = `Custom post triggered! Caption will be published to ${{platform}}. Check GitHub Actions for status.`;
                document.getElementById('qpCaption').value = '';
                document.getElementById('qpImageUrl').value = '';
            }} else {{
                const data = await resp.json();
                statusEl.className = 'qp-status error';
                statusEl.textContent = `Workflow error: ${{data.message || resp.statusText}}`;
            }}
        }} else {{
            statusEl.className = 'qp-status error';
            statusEl.textContent = 'Failed to save post data.';
        }}
    }} catch (e) {{
        statusEl.className = 'qp-status error';
        statusEl.textContent = `Network error: ${{e.message}}`;
    }}
}}

async function triggerMode(mode) {{
    const statusEl = document.getElementById('qpActionStatus');
    statusEl.className = 'qp-status loading';
    statusEl.textContent = `Triggering ${{mode}} mode...`;
    try {{
        const resp = await triggerWorkflow(mode);
        if (resp.status === 204) {{
            statusEl.className = 'qp-status success';
            statusEl.textContent = `${{mode.toUpperCase()}} mode triggered successfully! Check GitHub Actions for progress.`;
        }} else {{
            const data = await resp.json();
            statusEl.className = 'qp-status error';
            statusEl.textContent = `Error: ${{data.message || resp.statusText}}`;
        }}
    }} catch (e) {{
        statusEl.className = 'qp-status error';
        statusEl.textContent = `Network error: ${{e.message}}`;
    }}
}}
// Tab navigation
function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
    // Re-render charts for the active tab
    setTimeout(() => {{ window.dispatchEvent(new Event('resize')); }}, 50);
}}

// Color palette
const colors = {{
    red: '#e94560', blue: '#1877f2', pink: '#e1306c', cyan: '#00f2ea',
    green: '#4caf50', orange: '#ff9800', purple: '#9b59b6', gold: '#ffd700'
}};

const chartDefaults = {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
    scales: {{
        x: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }},
        y: {{ grid: {{ color: '#2a2a4a' }}, ticks: {{ color: '#666' }} }}
    }}
}};

// Engagement Score Trend
new Chart(document.getElementById('engagementChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(posted_labels)},
        datasets: [{{
            label: 'Engagement Score',
            data: {json.dumps(posted_scores)},
            borderColor: colors.purple,
            backgroundColor: 'rgba(155,89,182,0.1)',
            fill: true, tension: 0.3, pointRadius: 3,
        }}]
    }},
    options: chartDefaults
}});

// Platform Comparison
new Chart(document.getElementById('platformChart'), {{
    type: 'bar',
    data: {{
        labels: ['Reddit', 'Facebook', 'Instagram', 'TikTok'],
        datasets: [
            {{ label: 'Posts', data: {json.dumps(platform_posts)}, backgroundColor: [colors.red, colors.blue, colors.pink, colors.cyan] }},
            {{ label: 'Engagement', data: {json.dumps(platform_engagement)}, backgroundColor: ['#ff6b35', '#4299e1', '#f56565', '#38b2ac'] }}
        ]
    }},
    options: chartDefaults
}});

// 24-Hour Timeline (Overview)
new Chart(document.getElementById('timelineChart'), {{
    type: 'scatter',
    data: {{
        datasets: [
            {{
                label: 'Facebook',
                data: {json.dumps([{"x": h, "y": 2} for h in fb_slot_hours])},
                backgroundColor: colors.blue,
                pointRadius: 12, pointHoverRadius: 15,
            }},
            {{
                label: 'Instagram',
                data: {json.dumps([{"x": h, "y": 1} for h in ig_slot_hours])},
                backgroundColor: colors.pink,
                pointRadius: 8, pointHoverRadius: 11,
            }}
        ]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
        scales: {{
            x: {{
                min: 0, max: 24,
                grid: {{ color: '#2a2a4a' }},
                ticks: {{
                    color: '#888',
                    callback: function(v) {{
                        if (v === 0) return '12AM';
                        if (v < 12) return v + 'AM';
                        if (v === 12) return '12PM';
                        return (v-12) + 'PM';
                    }},
                    stepSize: 2
                }},
                title: {{ display: true, text: 'Hour (CDT)', color: '#666' }}
            }},
            y: {{
                min: 0, max: 3,
                grid: {{ color: '#2a2a4a' }},
                ticks: {{
                    color: '#888',
                    callback: function(v) {{
                        if (v === 1) return 'Instagram';
                        if (v === 2) return 'Facebook';
                        return '';
                    }}
                }}
            }}
        }}
    }}
}});

// Schedule Detail Chart
if (document.getElementById('scheduleDetailChart')) {{
    new Chart(document.getElementById('scheduleDetailChart'), {{
        type: 'scatter',
        data: {{
            datasets: [
                {{
                    label: 'Facebook ({len(fb_slots)} slots)',
                    data: {json.dumps([{"x": s.get("hour", 0) + s.get("minute", 0)/60, "y": 2} for s in fb_slots])},
                    backgroundColor: colors.blue,
                    pointRadius: 14, pointHoverRadius: 18,
                    pointStyle: 'rectRounded',
                }},
                {{
                    label: 'Instagram ({len(ig_slots)} slots)',
                    data: {json.dumps([{"x": s.get("hour", 0) + s.get("minute", 0)/60, "y": 1} for s in ig_slots])},
                    backgroundColor: colors.pink,
                    pointRadius: 10, pointHoverRadius: 14,
                    pointStyle: 'circle',
                }}
            ]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
            scales: {{
                x: {{
                    min: 0, max: 24,
                    grid: {{ color: '#2a2a4a' }},
                    ticks: {{
                        color: '#888',
                        callback: function(v) {{
                            if (v === 0) return '12AM';
                            if (v < 12) return v + 'AM';
                            if (v === 12) return '12PM';
                            return (v-12) + 'PM';
                        }},
                        stepSize: 1
                    }},
                    title: {{ display: true, text: 'Hour of Day (CDT)', color: '#666' }}
                }},
                y: {{
                    min: 0, max: 3,
                    grid: {{ color: '#2a2a4a' }},
                    ticks: {{
                        color: '#888',
                        callback: function(v) {{
                            if (v === 1) return 'Instagram';
                            if (v === 2) return 'Facebook';
                            return '';
                        }}
                    }}
                }}
            }}
        }}
    }});
}}

// Reddit Score Chart
if (document.getElementById('redditScoreChart')) {{
    new Chart(document.getElementById('redditScoreChart'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(score_labels)},
            datasets: [{{
                label: 'Comment Score',
                data: {json.dumps(reddit_scores)},
                borderColor: '#ff4500',
                backgroundColor: 'rgba(255,69,0,0.1)',
                fill: true, tension: 0.3,
            }}]
        }},
        options: chartDefaults
    }});
}}

// Reddit Distribution
if (document.getElementById('redditDistChart')) {{
    const scores = {json.dumps(reddit_scores)};
    const bins = [0, 0, 0, 0, 0]; // <0, 0-1, 2-5, 6-10, 10+
    scores.forEach(s => {{
        if (s < 0) bins[0]++;
        else if (s <= 1) bins[1]++;
        else if (s <= 5) bins[2]++;
        else if (s <= 10) bins[3]++;
        else bins[4]++;
    }});
    new Chart(document.getElementById('redditDistChart'), {{
        type: 'doughnut',
        data: {{
            labels: ['Negative', '0-1', '2-5', '6-10', '10+'],
            datasets: [{{ data: bins, backgroundColor: ['#f44336', '#ff9800', '#ffd700', '#4caf50', '#2196f3'] }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }} }}
    }});
}}

// Learning Trend Chart
if (document.getElementById('learningTrendChart')) {{
    new Chart(document.getElementById('learningTrendChart'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(posted_labels)},
            datasets: [{{
                label: 'Engagement Score',
                data: {json.dumps(posted_scores)},
                borderColor: colors.purple,
                backgroundColor: 'rgba(155,89,182,0.15)',
                fill: true, tension: 0.4, pointRadius: 4,
                pointBackgroundColor: colors.purple,
            }}]
        }},
        options: {{
            ...chartDefaults,
            plugins: {{
                ...chartDefaults.plugins,
                annotation: {{
                    annotations: {{
                        avgLine: {{
                            type: 'line',
                            yMin: {learn_avg},
                            yMax: {learn_avg},
                            borderColor: colors.orange,
                            borderWidth: 2,
                            borderDash: [6, 6],
                            label: {{ content: 'Avg: {learn_avg}', enabled: true, position: 'end' }}
                        }}
                    }}
                }}
            }}
        }}
    }});
}}
</script>

</body>
</html>"""


def _build_activity_feed(data: dict) -> str:
    """Build a unified activity feed showing all recent posts/comments."""
    activities = []

    comment_history = _load_json(os.path.join(DATA_DIR, "comment_history.json"), [])
    for c in comment_history[-15:]:
        url = c.get("url", c.get("permalink", ""))
        if not url and c.get("thread_id"):
            url = f"https://www.reddit.com/comments/{c['thread_id']}"
        activities.append({
            "platform": "reddit", "type": "comment",
            "text": c.get("comment", c.get("text", ""))[:100],
            "sub": c.get("subreddit", c.get("sub", "")),
            "url": url, "time": c.get("posted_at", c.get("timestamp", "")),
            "score": c.get("score", "-"),
        })

    replies = _load_json(os.path.join(DATA_DIR, "replies_sent.json"), [])
    for r in replies[-10:]:
        activities.append({
            "platform": "reddit", "type": "reply",
            "text": r.get("reply", "")[:100], "sub": r.get("subreddit", ""),
            "url": r.get("url", ""), "time": r.get("replied_at", ""), "score": "-",
        })

    fb_posts = _load_json(os.path.join(DATA_DIR, "fb_post_history.json"), [])
    for p in fb_posts[-10:]:
        activities.append({
            "platform": "facebook", "type": "post",
            "text": p.get("caption", "")[:100], "sub": "Page",
            "url": p.get("url", ""), "time": p.get("posted_at", ""),
            "score": p.get("likes", "-"),
        })

    ig_posts = _load_json(os.path.join(DATA_DIR, "ig_post_history.json"), [])
    for p in ig_posts[-10:]:
        activities.append({
            "platform": "instagram", "type": "post",
            "text": p.get("caption", "")[:100], "sub": "Feed",
            "url": p.get("url", ""), "time": p.get("posted_at", ""),
            "score": p.get("likes", "-"),
        })

    tt_posts = _load_json(os.path.join(DATA_DIR, "tt_post_history.json"), [])
    for p in tt_posts[-10:]:
        activities.append({
            "platform": "tiktok", "type": "post",
            "text": p.get("caption", "")[:100], "sub": "Feed",
            "url": p.get("url", ""), "time": p.get("posted_at", ""),
            "score": p.get("likes", "-"),
        })

    activities.sort(key=lambda x: x.get("time", ""), reverse=True)
    activities = activities[:25]

    if not activities:
        return '<p style="color:#666;">No activity recorded yet.</p>'

    platform_colors = {
        "reddit": "#ff4500", "facebook": "#1877f2",
        "instagram": "#e1306c", "tiktok": "#00f2ea",
    }
    type_icons = {"post": "NEW POST", "comment": "COMMENT", "reply": "REPLY"}

    html = '<div style="max-height:500px;overflow-y:auto;">'
    for a in activities:
        color = platform_colors.get(a["platform"], "#888")
        icon = type_icons.get(a["type"], "")
        url = a.get("url", "")
        link = f'<a href="{url}" target="_blank" style="color:{color};text-decoration:none;margin-left:8px;">View ↗</a>' if url else ''
        time_str = a.get("time", "")[:16]
        score_str = f' | Score: {a["score"]}' if a.get("score") and a["score"] != "-" else ''

        html += f"""
        <div style="display:flex;gap:10px;padding:8px 12px;margin:4px 0;background:#1a1a2e;border-radius:6px;border-left:3px solid {color};align-items:center;font-size:12px;">
            <span style="background:{color};color:#fff;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:bold;min-width:60px;text-align:center;">{a['platform'].upper()}</span>
            <span style="color:#888;min-width:70px;">{icon}</span>
            <span style="color:#ccc;flex:1;">{_escape(a['text'])}</span>
            <span style="color:#888;font-size:11px;">{a.get('sub', '')}{score_str}</span>
            <span style="color:#666;font-size:10px;">{time_str}</span>
            {link}
        </div>"""
    html += '</div>'
    return html


if __name__ == "__main__":
    path = generate_unified_dashboard()
    print(f"Dashboard: {path}")

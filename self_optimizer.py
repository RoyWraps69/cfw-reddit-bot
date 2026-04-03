"""
Chicago Fleet Wraps — Self-Optimizer v1.0

This module makes the bot smarter every single day.

The core loop:
1. OBSERVE: What did I do yesterday? What performed?
2. QUESTION: Ask 5 progressively better questions about performance
3. LEARN: Draw conclusions from the answers
4. ADAPT: Update keyword weights, persona weights, content strategy
5. PLAN: Set today's focus based on what was learned

The "ask better questions" principle:
- Day 1 questions are shallow: "Did my comments get upvotes?"
- Week 2 questions are deeper: "Which subreddits have the highest upvote-to-DM conversion?"
- Month 2 questions are strategic: "Is there a correlation between comment length and DM requests?"

The bot generates ITS OWN questions and then answers them from its own data.
This is the engine of continuous self-improvement.
"""

import os
import json
import random
from datetime import datetime, date, timedelta
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

OPTIMIZER_LOG_FILE = os.path.join(DATA_DIR, "optimizer_log.json")
STRATEGY_FILE = os.path.join(DATA_DIR, "current_strategy.json")
QUESTION_ARCHIVE_FILE = os.path.join(DATA_DIR, "question_archive.json")

client = OpenAI()

# ─────────────────────────────────────────────────────────────────────
# QUESTION EVOLUTION ENGINE
# The bot generates questions that get progressively smarter
# ─────────────────────────────────────────────────────────────────────

QUESTION_DEPTH_LEVELS = {
    1: "Surface observation — what happened?",
    2: "Pattern recognition — what happens consistently?",
    3: "Causation — WHY does that happen?",
    4: "Prediction — what WILL happen if I change X?",
    5: "Strategic — how does this fit into the larger goal?",
}

SEED_QUESTIONS = [
    # Depth 1 — Surface
    "Which subreddits got the most upvotes today?",
    "Which comments got replies?",
    "Did any comments get removed or downvoted?",
    "How many comments were posted today vs the daily limit?",

    # Depth 2 — Patterns
    "Which persona (voice style) consistently gets more upvotes?",
    "Is there a correlation between comment length and upvotes?",
    "Which thread types (question/showcase/rant) get the best response?",
    "Are morning or evening posts performing better?",

    # Depth 3 — Causation
    "Why do competitor threads get more replies than general wrap questions?",
    "Why do comments in r/chicago get fewer upvotes than r/smallbusiness?",
    "What specific language in my comments is triggering DMs?",
    "What's different about the comments that got removed?",

    # Depth 4 — Prediction
    "If I shift 30% more comments to fleet/business subs, will DM volume increase?",
    "If I use the fleet_manager persona more in commercial subs, will conversion go up?",
    "Would posting 2 educational content pieces per week increase organic reach?",
    "Would targeting the 1-3 hour thread age window improve upvote velocity?",

    # Depth 5 — Strategic
    "Is Reddit driving real phone calls or is the phone ringing for other reasons?",
    "Which platform (Reddit/TikTok/Instagram) has the shortest path from content to booked job?",
    "What would it take to dominate the first page of results when someone Googles 'car wrap chicago'?",
    "Am I building a brand or just gaming a platform? What's the difference in long-term outcome?",
]


def generate_daily_questions(performance_data: dict, days_active: int = 1) -> list:
    """Generate 5 progressively better questions based on performance data and experience level.

    The longer the bot has been running, the deeper the questions get.
    """
    # Determine question depth based on experience
    if days_active <= 7:
        allowed_depths = [1, 2]
    elif days_active <= 30:
        allowed_depths = [1, 2, 3]
    elif days_active <= 90:
        allowed_depths = [2, 3, 4]
    else:
        allowed_depths = [3, 4, 5]

    # Build performance context for AI
    perf_summary = _summarize_performance(performance_data)

    prompt = f"""You are the self-improvement engine for a Reddit/social media bot promoting Chicago Fleet Wraps.
The bot has been running for {days_active} days.

YESTERDAY'S PERFORMANCE SUMMARY:
{perf_summary}

QUESTION DEPTH LEVELS:
{json.dumps(QUESTION_DEPTH_LEVELS, indent=2)}

Your job: Generate 5 questions the bot should ask itself TODAY to get smarter.
Focus on depth levels: {allowed_depths}

Rules:
- Questions should be specific to the data, not generic
- Each question should be answerable from the bot's own logs and data
- Questions should lead to actionable changes (not just curiosity)
- At least 1 question should challenge an assumption the bot is currently making
- At least 1 question should be about WHAT ISN'T WORKING, not just what is

Return ONLY valid JSON:
{{
    "questions": [
        {{"depth": 1, "question": "...", "why_this_matters": "...", "data_source": "which log/file answers this"}},
        ...
    ],
    "top_hypothesis": "The single most important thing to test today based on the data",
    "blind_spot": "The assumption we might be making that we should question"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        result["generated_date"] = str(date.today())
        result["days_active"] = days_active
        _archive_questions(result)
        return result
    except Exception:
        return {
            "questions": [{"depth": 1, "question": q, "why_this_matters": "baseline tracking", "data_source": "daily_activity.json"}
                         for q in random.sample(SEED_QUESTIONS[:4], 5)],
            "top_hypothesis": "Comments in commercial subreddits convert better than car enthusiast subs",
            "blind_spot": "We might be optimizing for upvotes instead of DMs",
            "generated_date": str(date.today()),
        }


def answer_questions(questions_result: dict) -> dict:
    """Auto-answer the daily questions from available log data.

    Reads all available data files and generates answers.
    """
    answers = {}

    # Load all available data
    all_data = _load_all_performance_data()

    for q in questions_result.get("questions", []):
        question = q["question"]
        data_source = q.get("data_source", "")

        # Try to answer from data
        answer = _find_answer_in_data(question, all_data)
        answers[question] = {
            "answer": answer,
            "depth": q.get("depth", 1),
            "confidence": "high" if answer != "insufficient data" else "low",
        }

    return {
        "date": str(date.today()),
        "questions_answered": answers,
        "top_hypothesis": questions_result.get("top_hypothesis", ""),
        "blind_spot": questions_result.get("blind_spot", ""),
    }


def _find_answer_in_data(question: str, all_data: dict) -> str:
    """Try to answer a question from available log data."""
    # This is a simplified version — in production, this would do
    # actual statistical analysis of the log files

    comment_history = all_data.get("comment_history", [])
    persona_stats = all_data.get("persona_stats", {})
    content_log = all_data.get("content_log", [])

    if not comment_history and not persona_stats:
        return "insufficient data — need more operational history"

    # Let AI answer from the data
    data_snapshot = {
        "comments_last_7_days": comment_history[-50:] if comment_history else [],
        "persona_stats": persona_stats,
        "content_performance": content_log[-20:] if content_log else [],
    }

    prompt = f"""You have access to this bot performance data. Answer this question:

QUESTION: {question}

DATA:
{json.dumps(data_snapshot, indent=2)[:3000]}

Give a 1-3 sentence specific answer. If the data doesn't support a definitive answer, say what the data DOES show and what's still unclear.
Be direct. No fluff."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "unable to analyze — API error"


# ─────────────────────────────────────────────────────────────────────
# STRATEGY ADAPTATION
# ─────────────────────────────────────────────────────────────────────

def generate_strategy_update(answered_questions: dict, current_strategy: dict) -> dict:
    """Generate updated strategy based on answered questions.

    This is the actual learning step — what should we DO differently tomorrow?
    """
    prompt = f"""You are the strategy brain for a bot promoting Chicago Fleet Wraps on Reddit/social media.

CURRENT STRATEGY:
{json.dumps(current_strategy, indent=2)}

TODAY'S LEARNING (questions + answers):
{json.dumps(answered_questions, indent=2)[:2000]}

Based on what was learned today, generate SPECIFIC strategy updates.
Be concrete. Don't say "focus more on X" — say "increase X from 2 to 4 comments per day" or "switch persona Y to subreddit Z."

Return ONLY valid JSON:
{{
    "strategy_changes": [
        {{"change": "specific change", "reason": "based on which data", "confidence": "high/medium/low"}}
    ],
    "subreddit_weight_changes": {{"r/subreddit": "+20%" or "-10%" or "remove" or "add"}},
    "persona_weight_changes": {{"persona_key": "+increase" or "-decrease"}},
    "keyword_additions": ["new keywords to target"],
    "keyword_removals": ["keywords that aren't converting"],
    "content_focus_tomorrow": "which content archetype to prioritize tomorrow",
    "one_thing_to_test": "the single most important thing to A/B test this week"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    try:
        updates = json.loads(response.choices[0].message.content)
        updates["updated_date"] = str(date.today())

        # Merge with current strategy
        new_strategy = current_strategy.copy()
        new_strategy["last_updated"] = str(date.today())
        new_strategy["recent_changes"] = updates.get("strategy_changes", [])
        new_strategy["current_test"] = updates.get("one_thing_to_test", "")
        new_strategy["content_focus"] = updates.get("content_focus_tomorrow", "before_after")

        _save_strategy(new_strategy)
        return updates
    except Exception as e:
        return {"error": str(e), "strategy_changes": []}


# ─────────────────────────────────────────────────────────────────────
# DAILY OPTIMIZATION CYCLE
# ─────────────────────────────────────────────────────────────────────

def run_daily_optimization() -> dict:
    """Run the full daily optimization cycle.

    Called once per day (recommend: 6 AM).
    Returns a summary of what was learned and what's changing.
    """
    print("[OPTIMIZER] Starting daily optimization cycle...", flush=True)

    # 1. Calculate days active
    days_active = _get_days_active()
    print(f"[OPTIMIZER] Days active: {days_active}", flush=True)

    # 2. Load yesterday's performance
    performance_data = _load_all_performance_data()

    # 3. Generate today's questions
    print("[OPTIMIZER] Generating daily questions...", flush=True)
    questions = generate_daily_questions(performance_data, days_active)
    print(f"[OPTIMIZER] Generated {len(questions.get('questions', []))} questions", flush=True)

    # 4. Answer the questions
    print("[OPTIMIZER] Answering questions from data...", flush=True)
    answers = answer_questions(questions)

    # 5. Load current strategy
    current_strategy = _load_strategy()

    # 6. Generate strategy updates
    print("[OPTIMIZER] Generating strategy updates...", flush=True)
    updates = generate_strategy_update(answers, current_strategy)

    # 7. Log everything
    log_entry = {
        "date": str(date.today()),
        "days_active": days_active,
        "questions": questions,
        "answers": answers,
        "strategy_updates": updates,
    }
    _log_optimizer_entry(log_entry)

    # 8. Build report
    report_lines = [
        "=" * 60,
        "DAILY OPTIMIZATION REPORT",
        f"Date: {date.today()} | Day #{days_active}",
        "=" * 60,
        "",
        f"TOP HYPOTHESIS: {questions.get('top_hypothesis', 'n/a')}",
        f"BLIND SPOT IDENTIFIED: {questions.get('blind_spot', 'n/a')}",
        "",
        "STRATEGY CHANGES:",
    ]
    for change in updates.get("strategy_changes", []):
        report_lines.append(f"  [{change.get('confidence', '?').upper()}] {change.get('change', '')}")
        report_lines.append(f"         Reason: {change.get('reason', '')}")

    report_lines.append("")
    report_lines.append(f"A/B TEST THIS WEEK: {updates.get('one_thing_to_test', 'none')}")
    report_lines.append(f"CONTENT FOCUS TOMORROW: {updates.get('content_focus_tomorrow', 'before_after')}")

    report = "\n".join(report_lines)
    print(report, flush=True)

    return {
        "report": report,
        "questions": questions,
        "answers": answers,
        "updates": updates,
        "days_active": days_active,
    }


# ─────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def _summarize_performance(performance_data: dict) -> str:
    """Create a concise text summary of performance data."""
    lines = []
    comment_history = performance_data.get("comment_history", [])
    persona_stats = performance_data.get("persona_stats", {})

    if comment_history:
        recent = comment_history[-20:]
        total_upvotes = sum(c.get("upvotes", 0) for c in recent)
        total_comments = len(recent)
        subs = list(set(c.get("subreddit", "") for c in recent))
        lines.append(f"Comments last 20 entries: {total_comments}, Total upvotes: {total_upvotes}")
        lines.append(f"Subreddits: {', '.join(subs[:8])}")
    else:
        lines.append("No comment history available yet")

    if persona_stats:
        top_persona = max(persona_stats.items(), key=lambda x: x[1].get("avg_upvotes", 0), default=("none", {}))
        lines.append(f"Top persona: {top_persona[0]} ({top_persona[1].get('avg_upvotes', 0)} avg upvotes)")

    return "\n".join(lines) if lines else "No performance data available"


def _load_all_performance_data() -> dict:
    """Load all available performance data from all log files."""
    data = {}

    files = {
        "comment_history": os.path.join(DATA_DIR, "comment_history.json"),
        "persona_stats": os.path.join(DATA_DIR, "persona_stats.json"),
        "content_log": os.path.join(DATA_DIR, "content_log.json"),
        "daily_activity": os.path.join(LOG_DIR, "daily_activity.json"),
        "upvote_data": os.path.join(DATA_DIR, "upvote_data.json"),
    }

    for key, path in files.items():
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data[key] = json.load(f)
            except Exception:
                data[key] = []

    return data


def _get_days_active() -> int:
    """Calculate how many days the bot has been running."""
    start_file = os.path.join(DATA_DIR, "start_date.json")
    if os.path.exists(start_file):
        try:
            with open(start_file) as f:
                start = json.load(f).get("start_date", str(date.today()))
            start_dt = datetime.strptime(start, "%Y-%m-%d").date()
            return (date.today() - start_dt).days + 1
        except Exception:
            pass

    # First run — record start date
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(start_file, "w") as f:
        json.dump({"start_date": str(date.today())}, f)
    return 1


def _load_strategy() -> dict:
    """Load the current strategy from disk."""
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    # Default initial strategy
    return {
        "created": str(date.today()),
        "last_updated": str(date.today()),
        "primary_goal": "Dominate Chicago fleet wrap search and social presence",
        "current_phase": "warming",  # warming → normal → growth → domination
        "top_target_subs": ["chicago", "smallbusiness", "foodtrucks", "Rivian"],
        "top_persona": "roy_craftsman",
        "content_focus": "before_after",
        "current_test": "None yet",
        "recent_changes": [],
    }


def _save_strategy(strategy: dict):
    """Save updated strategy to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STRATEGY_FILE, "w") as f:
        json.dump(strategy, f, indent=2)


def _archive_questions(questions_result: dict):
    """Archive questions for longitudinal analysis."""
    os.makedirs(DATA_DIR, exist_ok=True)
    archive = []
    if os.path.exists(QUESTION_ARCHIVE_FILE):
        try:
            with open(QUESTION_ARCHIVE_FILE) as f:
                archive = json.load(f)
        except Exception:
            pass
    archive.append(questions_result)
    archive = archive[-365:]  # Keep 1 year
    with open(QUESTION_ARCHIVE_FILE, "w") as f:
        json.dump(archive, f, indent=2)


def _log_optimizer_entry(entry: dict):
    """Log the optimizer run for historical analysis."""
    os.makedirs(DATA_DIR, exist_ok=True)
    log = []
    if os.path.exists(OPTIMIZER_LOG_FILE):
        try:
            with open(OPTIMIZER_LOG_FILE) as f:
                log = json.load(f)
        except Exception:
            pass
    log.append(entry)
    log = log[-365:]
    with open(OPTIMIZER_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

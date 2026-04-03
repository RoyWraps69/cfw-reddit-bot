"""
Chicago Fleet Wraps Reddit Bot — Competitor Monitor v1.0
Detects when someone mentions a competitor wrap shop and responds with
a helpful answer that naturally positions CFW as the better option.

Strategy:
- NEVER trash-talk competitors (looks desperate)
- Instead, answer the question helpfully and mention CFW as an alternative
- Focus on CFW's differentiators: transparency, online calculator, fast response
- Only engage when someone is actively looking for options
- If someone is praising a competitor, don't jump in (looks petty)
"""
import json
import os
import time
from datetime import datetime
from config import COMPETITORS, DATA_DIR, ALL_TARGET_SUBS, TIER1_LOCAL, INDUSTRY_SUBS

COMPETITOR_LOG_FILE = os.path.join(DATA_DIR, "competitor_mentions.json")

# Expanded competitor list with variations
COMPETITOR_VARIATIONS = {}
for comp in COMPETITORS:
    # Generate common variations
    variations = [comp.lower()]
    # Add without common suffixes
    for suffix in [" wraps", " wrap", " chicago", " graphics"]:
        if comp.lower().endswith(suffix):
            variations.append(comp.lower().replace(suffix, "").strip())
    COMPETITOR_VARIATIONS[comp] = variations


def scan_for_competitor_mentions(threads: list) -> list:
    """Scan a list of threads for competitor mentions.

    Returns threads that mention competitors, enriched with competitor info.
    """
    competitor_threads = []

    for thread in threads:
        title = thread.get("title", "").lower()
        body = thread.get("body", "").lower()
        text = title + " " + body

        for comp_name, variations in COMPETITOR_VARIATIONS.items():
            for var in variations:
                if var in text:
                    thread["competitor_mentioned"] = comp_name
                    thread["competitor_context"] = _classify_competitor_context(text, comp_name)
                    competitor_threads.append(thread)
                    break
            else:
                continue
            break

    return competitor_threads


def _classify_competitor_context(text: str, competitor: str) -> str:
    """Classify how the competitor is being mentioned.

    Returns:
    - "seeking_alternative" — they're looking for options (BEST opportunity)
    - "asking_about" — asking about the competitor specifically
    - "praising" — saying good things about competitor (DON'T engage)
    - "complaining" — unhappy with competitor (GOOD opportunity)
    - "comparing" — comparing shops (GOOD opportunity)
    - "neutral_mention" — just mentioned in passing
    """
    # Check for seeking alternatives
    seeking_words = ["alternative", "instead of", "other than", "besides",
                     "anyone else", "other shops", "other options", "recommend",
                     "looking for", "suggestions", "who else"]
    if any(w in text for w in seeking_words):
        return "seeking_alternative"

    # Check for complaints
    complaint_words = ["terrible", "awful", "worst", "scam", "ripped off",
                       "overcharged", "bad experience", "never again", "avoid",
                       "disappointed", "poor quality", "ruined", "messed up",
                       "wouldn't recommend", "don't go"]
    if any(w in text for w in complaint_words):
        return "complaining"

    # Check for comparison
    compare_words = ["vs", "versus", "compared to", "better than", "or",
                     "which is better", "thoughts on", "between"]
    if any(w in text for w in compare_words):
        return "comparing"

    # Check for praise
    praise_words = ["love", "amazing", "best", "incredible", "highly recommend",
                    "great job", "excellent", "perfect", "outstanding", "10/10"]
    if any(w in text for w in praise_words):
        return "praising"

    # Check for asking about
    asking_words = ["anyone used", "has anyone", "experience with",
                    "what do you think", "heard of", "know about"]
    if any(w in text for w in asking_words):
        return "asking_about"

    return "neutral_mention"


def should_respond_to_competitor(thread: dict) -> bool:
    """Determine if we should respond to a competitor mention.

    Rules:
    - YES: seeking_alternative, complaining, comparing, asking_about
    - NO: praising, neutral_mention
    - EXTRA YES: if it's in a Chicago-area or industry sub
    """
    context = thread.get("competitor_context", "neutral_mention")

    # Never jump in when someone is praising a competitor
    if context == "praising":
        return False

    # Skip neutral mentions
    if context == "neutral_mention":
        return False

    # All other contexts are good opportunities
    return True


def get_competitor_response_strategy(thread: dict) -> dict:
    """Get the response strategy for a competitor mention thread.

    Returns guidance for the AI responder on how to handle this.
    """
    context = thread.get("competitor_context", "neutral_mention")
    competitor = thread.get("competitor_mentioned", "unknown")
    subreddit = thread.get("subreddit", "")

    strategies = {
        "seeking_alternative": {
            "approach": "helpful_recommendation",
            "tone": "casual, helpful",
            "mention_cfw": True,
            "guidance": f"They're looking for alternatives to {competitor}. Answer their question first with general advice about what to look for in a wrap shop (transparency, portfolio, reviews). Then casually mention CFW as an option you've had good experience with. Don't trash {competitor}.",
        },
        "complaining": {
            "approach": "empathetic_alternative",
            "tone": "empathetic, not opportunistic",
            "mention_cfw": True,
            "guidance": f"They had a bad experience with {competitor}. Validate their frustration first — 'that sucks, sorry to hear that.' Then offer general advice on what to look for next time (ask to see their portfolio, get everything in writing, check reviews). Mention CFW as a shop that does things differently (online calculator, transparent pricing). Don't pile on {competitor}.",
        },
        "comparing": {
            "approach": "objective_comparison",
            "tone": "knowledgeable, balanced",
            "mention_cfw": True,
            "guidance": f"They're comparing wrap shops. Share what you know about what differentiates good shops from bad ones. Mention CFW's differentiators naturally (online price calculator, 600+ Rivians wrapped, 10+ years). Be balanced — acknowledge that different shops have different strengths.",
        },
        "asking_about": {
            "approach": "informed_opinion",
            "tone": "casual, informed",
            "mention_cfw": True,
            "guidance": f"They're asking about {competitor}. If you genuinely know something about them, share it (but nothing negative unless it's factual). Then mention CFW as another option worth checking out. Focus on CFW's unique selling points.",
        },
    }

    return strategies.get(context, {
        "approach": "skip",
        "tone": "none",
        "mention_cfw": False,
        "guidance": "Skip this one.",
    })


def log_competitor_mention(thread: dict, responded: bool):
    """Log a competitor mention for tracking."""
    os.makedirs(DATA_DIR, exist_ok=True)

    log = []
    if os.path.exists(COMPETITOR_LOG_FILE):
        try:
            with open(COMPETITOR_LOG_FILE, "r") as f:
                log = json.load(f)
        except Exception:
            log = []

    log.append({
        "date": datetime.now().isoformat(),
        "competitor": thread.get("competitor_mentioned", ""),
        "context": thread.get("competitor_context", ""),
        "subreddit": thread.get("subreddit", ""),
        "title": thread.get("title", "")[:100],
        "responded": responded,
        "url": thread.get("url", ""),
    })

    # Keep last 200 entries
    log = log[-200:]
    with open(COMPETITOR_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def get_competitor_dashboard_data() -> dict:
    """Get competitor mention data for the dashboard."""
    if not os.path.exists(COMPETITOR_LOG_FILE):
        return {"total_mentions": 0, "by_competitor": {}, "by_context": {}, "response_rate": 0}

    try:
        with open(COMPETITOR_LOG_FILE, "r") as f:
            log = json.load(f)
    except Exception:
        return {"total_mentions": 0, "by_competitor": {}, "by_context": {}, "response_rate": 0}

    by_competitor = {}
    by_context = {}
    responded_count = 0

    for entry in log:
        comp = entry.get("competitor", "unknown")
        ctx = entry.get("context", "unknown")

        by_competitor[comp] = by_competitor.get(comp, 0) + 1
        by_context[ctx] = by_context.get(ctx, 0) + 1
        if entry.get("responded"):
            responded_count += 1

    return {
        "total_mentions": len(log),
        "by_competitor": by_competitor,
        "by_context": by_context,
        "response_rate": round(responded_count / len(log) * 100, 1) if log else 0,
        "recent": log[-5:] if log else [],
    }

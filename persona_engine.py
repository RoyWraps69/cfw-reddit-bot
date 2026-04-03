"""
Chicago Fleet Wraps — Persona Engine v1.0
DYNAMIC PERSONALITY SYSTEM THAT EVOLVES WITH ENGAGEMENT

Instead of a hardcoded "Chicago voice," this module maintains a living
persona profile that adapts per platform based on what resonates.

The persona has measurable traits on a 0-10 scale:
  - humor:        0 = dead serious, 10 = comedy account
  - technical:    0 = pure vibes, 10 = deep technical detail
  - directness:   0 = subtle/soft, 10 = blunt/no-BS
  - warmth:       0 = cool/detached, 10 = warm/community-focused
  - controversy:  0 = totally safe, 10 = hot takes
  - storytelling: 0 = just facts, 10 = narrative-driven

Each platform has its own trait profile that evolves independently.
The engine also maintains a "voice bank" of phrases, hooks, and
response patterns that have proven effective.
"""

import os
import json
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL

PERSONA_DIR = os.path.join(DATA_DIR, "persona")
PROFILE_FILE = os.path.join(PERSONA_DIR, "profile.json")
VOICE_BANK_FILE = os.path.join(PERSONA_DIR, "voice_bank.json")
EVOLUTION_LOG = os.path.join(PERSONA_DIR, "evolution_log.json")

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

# The baseline persona — Roy from Chicago Fleet Wraps
BASELINE_PERSONA = {
    "name": "Roy",
    "business": "Chicago Fleet Wraps",
    "location": "Portage Park, Chicago, IL",
    "background": (
        "Roy runs Chicago Fleet Wraps out of Portage Park. He's been in the wrap "
        "game for years and knows his stuff. He's direct, doesn't sugarcoat, and "
        "genuinely loves transforming vehicles. He's not a marketing guy — he's a "
        "wrap guy who happens to post on social media."
    ),
    "core_values": [
        "Quality work speaks for itself",
        "Treat every vehicle like it's your own",
        "Chicago pride — this city is in our DNA",
        "No shortcuts, no BS",
        "Community over competition",
    ],
}

DEFAULT_TRAITS = {
    "humor": 4.0,
    "technical": 5.0,
    "directness": 7.0,
    "warmth": 5.0,
    "controversy": 2.0,
    "storytelling": 4.0,
}


def _ensure_dirs():
    os.makedirs(PERSONA_DIR, exist_ok=True)


def _load_profile() -> dict:
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _initialize_profile()


def _save_profile(profile: dict):
    _ensure_dirs()
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)


def _initialize_profile() -> dict:
    """Create the initial persona profile with default traits per platform."""
    profile = {
        "baseline": BASELINE_PERSONA,
        "platforms": {
            "facebook": {
                "traits": dict(DEFAULT_TRAITS),
                "effective_phrases": [],
                "avoid_phrases": [],
                "best_hooks": [],
                "posts_analyzed": 0,
            },
            "instagram": {
                "traits": dict(DEFAULT_TRAITS),
                "effective_phrases": [],
                "avoid_phrases": [],
                "best_hooks": [],
                "posts_analyzed": 0,
            },
            "tiktok": {
                "traits": {**DEFAULT_TRAITS, "humor": 6.0, "directness": 8.0, "controversy": 3.0},
                "effective_phrases": [],
                "avoid_phrases": [],
                "best_hooks": [],
                "posts_analyzed": 0,
            },
            "reddit": {
                "traits": {**DEFAULT_TRAITS, "technical": 7.0, "warmth": 6.0, "controversy": 1.0},
                "effective_phrases": [],
                "avoid_phrases": [],
                "best_hooks": [],
                "posts_analyzed": 0,
            },
        },
        "created_at": datetime.now().isoformat(),
        "last_evolved": None,
    }
    _ensure_dirs()
    _save_profile(profile)
    return profile


def _load_voice_bank() -> dict:
    if os.path.exists(VOICE_BANK_FILE):
        try:
            with open(VOICE_BANK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"winning_hooks": [], "winning_closers": [], "winning_responses": []}


def _save_voice_bank(bank: dict):
    _ensure_dirs()
    with open(VOICE_BANK_FILE, "w") as f:
        json.dump(bank, f, indent=2)


def _load_evolution_log() -> list:
    if os.path.exists(EVOLUTION_LOG):
        try:
            with open(EVOLUTION_LOG, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_evolution_log(log: list):
    _ensure_dirs()
    log = log[-200:]
    with open(EVOLUTION_LOG, "w") as f:
        json.dump(log, f, indent=2)


# ═══════════════════════════════════════════════════════════════
# PERSONA RETRIEVAL — Get the current persona for a platform
# ═══════════════════════════════════════════════════════════════

def get_persona(platform: str) -> dict:
    """Get the current persona profile for a specific platform.

    Returns a dict with baseline info, platform-specific traits,
    and a formatted system prompt for the AI.
    """
    profile = _load_profile()
    platform_data = profile["platforms"].get(platform, profile["platforms"]["facebook"])
    traits = platform_data["traits"]

    # Build the system prompt dynamically from traits
    trait_descriptions = []
    if traits["humor"] >= 6:
        trait_descriptions.append("Use humor freely — puns, jokes, self-deprecating wit.")
    elif traits["humor"] <= 3:
        trait_descriptions.append("Keep it serious and professional. No jokes.")

    if traits["technical"] >= 6:
        trait_descriptions.append("Drop technical details — vinyl brands, mil thickness, application techniques.")
    elif traits["technical"] <= 3:
        trait_descriptions.append("Keep it simple and visual. No jargon.")

    if traits["directness"] >= 7:
        trait_descriptions.append("Be blunt and direct. No fluff. Say it like it is.")
    elif traits["directness"] <= 3:
        trait_descriptions.append("Be gentle and suggestive. Soft-sell only.")

    if traits["warmth"] >= 6:
        trait_descriptions.append("Be warm and community-focused. Mention customers, neighbors, Chicago pride.")
    elif traits["warmth"] <= 3:
        trait_descriptions.append("Keep it cool and professional. Business-focused.")

    if traits["controversy"] >= 4:
        trait_descriptions.append("Don't be afraid to share hot takes or challenge common opinions about wraps.")
    else:
        trait_descriptions.append("Stay safe and non-controversial. Universally positive content only.")

    if traits["storytelling"] >= 6:
        trait_descriptions.append("Tell stories. Every wrap has a story — the customer, the process, the reveal.")
    elif traits["storytelling"] <= 3:
        trait_descriptions.append("Keep it factual and visual. Show, don't tell.")

    system_prompt = f"""You are {BASELINE_PERSONA['name']} from {BASELINE_PERSONA['business']} in {BASELINE_PERSONA['location']}.

{BASELINE_PERSONA['background']}

YOUR VOICE ON {platform.upper()}:
{chr(10).join(f'- {d}' for d in trait_descriptions)}

EFFECTIVE PHRASES (use these or similar):
{chr(10).join(f'- "{p}"' for p in platform_data.get('effective_phrases', [])[:5]) or '- (Still learning what works here)'}

AVOID THESE (they flopped):
{chr(10).join(f'- "{p}"' for p in platform_data.get('avoid_phrases', [])[:5]) or '- (Nothing to avoid yet)'}

HOOKS THAT WORKED:
{chr(10).join(f'- "{h}"' for h in platform_data.get('best_hooks', [])[:5]) or '- (Still testing hooks)'}

RULES:
- Never sound like a marketing agency or corporate brand
- Never use "we are proud to announce" or similar corporate speak
- You ARE Roy. Talk like Roy. A real person running a real shop.
- If you mention CFW, do it naturally — like you'd mention your own business in conversation
"""

    return {
        "system_prompt": system_prompt,
        "traits": traits,
        "baseline": BASELINE_PERSONA,
        "platform": platform,
        "effective_phrases": platform_data.get("effective_phrases", []),
        "best_hooks": platform_data.get("best_hooks", []),
    }


# ═══════════════════════════════════════════════════════════════
# PERSONA EVOLUTION — Learn from engagement data
# ═══════════════════════════════════════════════════════════════

def evolve_persona(platform: str, top_posts: list, bottom_posts: list):
    """Evolve the persona traits for a platform based on performance data.

    This is called by the learning engine after analyzing engagement.

    Args:
        platform: The platform to evolve (facebook, instagram, tiktok, reddit).
        top_posts: List of dicts with caption, hook, engagement_score for top performers.
        bottom_posts: List of dicts with caption, hook, engagement_score for bottom performers.
    """
    if not top_posts and not bottom_posts:
        return

    profile = _load_profile()
    platform_data = profile["platforms"].get(platform)
    if not platform_data:
        return

    old_traits = dict(platform_data["traits"])

    # Use AI to analyze what trait adjustments are needed
    try:
        top_summary = "\n".join([
            f"  Score {p.get('score', 0)}: \"{p.get('caption', '')[:150]}\""
            for p in top_posts[:5]
        ])
        bottom_summary = "\n".join([
            f"  Score {p.get('score', 0)}: \"{p.get('caption', '')[:150]}\""
            for p in bottom_posts[:5]
        ])

        prompt = f"""Analyze these social media posts for {BASELINE_PERSONA['business']} on {platform}.

TOP PERFORMERS (high engagement):
{top_summary}

BOTTOM PERFORMERS (low engagement):
{bottom_summary}

Current persona traits (0-10 scale):
{json.dumps(platform_data['traits'], indent=2)}

Based on what's working vs what's not, suggest trait adjustments.
Also extract any specific phrases or hooks from top performers that should be reused.

Return ONLY valid JSON:
{{
    "trait_adjustments": {{
        "humor": 0,
        "technical": 0,
        "directness": 0,
        "warmth": 0,
        "controversy": 0,
        "storytelling": 0
    }},
    "effective_phrases": ["phrases from top posts to reuse"],
    "avoid_phrases": ["phrases from bottom posts to avoid"],
    "best_hooks": ["opening hooks from top posts"],
    "reasoning": "Brief explanation of why these adjustments"
}}

RULES:
- Adjustments should be -2 to +2 (small incremental changes)
- Traits must stay within 0-10 range
- Be specific about phrases — extract actual text from the posts
- Focus on what ACTUALLY drove engagement, not generic advice"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        analysis = json.loads(result.strip())

        # Apply trait adjustments
        adjustments = analysis.get("trait_adjustments", {})
        for trait, delta in adjustments.items():
            if trait in platform_data["traits"]:
                new_val = platform_data["traits"][trait] + delta
                platform_data["traits"][trait] = max(0.0, min(10.0, new_val))

        # Update effective phrases (keep last 20)
        new_phrases = analysis.get("effective_phrases", [])
        platform_data["effective_phrases"] = (
            new_phrases + platform_data.get("effective_phrases", [])
        )[:20]

        # Update avoid phrases (keep last 20)
        new_avoid = analysis.get("avoid_phrases", [])
        platform_data["avoid_phrases"] = (
            new_avoid + platform_data.get("avoid_phrases", [])
        )[:20]

        # Update best hooks (keep last 10)
        new_hooks = analysis.get("best_hooks", [])
        platform_data["best_hooks"] = (
            new_hooks + platform_data.get("best_hooks", [])
        )[:10]

        platform_data["posts_analyzed"] = (
            platform_data.get("posts_analyzed", 0) + len(top_posts) + len(bottom_posts)
        )

        profile["last_evolved"] = datetime.now().isoformat()
        _save_profile(profile)

        # Log the evolution
        log = _load_evolution_log()
        log.append({
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "old_traits": old_traits,
            "new_traits": dict(platform_data["traits"]),
            "adjustments": adjustments,
            "reasoning": analysis.get("reasoning", ""),
            "new_phrases_added": len(new_phrases),
            "new_hooks_added": len(new_hooks),
        })
        _save_evolution_log(log)

        print(f"  [PERSONA] Evolved {platform} persona: {adjustments}", flush=True)

    except Exception as e:
        print(f"  [PERSONA] Evolution error for {platform}: {e}", flush=True)


# ═══════════════════════════════════════════════════════════════
# RESPONSE GENERATION — Generate replies in persona
# ═══════════════════════════════════════════════════════════════

def generate_reply(platform: str, context: str, reply_type: str = "comment") -> str:
    """Generate a reply to a comment or post, in the current persona voice.

    Args:
        platform: The platform (reddit, facebook, instagram, tiktok).
        context: The text being replied to.
        reply_type: "comment" for replying to a comment, "engage" for proactive engagement.

    Returns:
        The generated reply text.
    """
    persona = get_persona(platform)

    if reply_type == "engage":
        user_prompt = f"""Someone posted this on {platform}:
\"{context[:500]}\"

Write a genuine, engaging reply as Roy. You're NOT selling — you're participating
in the community. Be helpful, interesting, or funny. Only mention CFW if it's
genuinely relevant (like if they're asking about wraps in Chicago).

Keep it under 100 words. Sound like a real person, not a brand."""
    else:
        user_prompt = f"""Someone replied to your post on {platform}:
\"{context[:500]}\"

Write a natural reply as Roy. Be genuine. If they're asking a question, answer it.
If they're complimenting, be gracious. If they're critical, be professional but real.

Keep it under 80 words. Sound like a real person."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": persona["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        print(f"  [PERSONA] Reply generation error: {e}", flush=True)
        return ""


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def get_persona_dashboard() -> dict:
    """Get persona data for the unified dashboard."""
    profile = _load_profile()
    log = _load_evolution_log()

    platform_summaries = {}
    for platform, data in profile.get("platforms", {}).items():
        platform_summaries[platform] = {
            "traits": data["traits"],
            "posts_analyzed": data.get("posts_analyzed", 0),
            "effective_phrases_count": len(data.get("effective_phrases", [])),
            "best_hooks_count": len(data.get("best_hooks", [])),
        }

    return {
        "baseline": BASELINE_PERSONA["name"],
        "platforms": platform_summaries,
        "total_evolutions": len(log),
        "last_evolved": profile.get("last_evolved"),
        "recent_evolutions": log[-5:],
    }


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "reset":
        _initialize_profile()
        print("Persona reset to defaults.")
    elif cmd == "show":
        platform = sys.argv[2] if len(sys.argv) > 2 else "instagram"
        persona = get_persona(platform)
        print(f"\n{'='*60}")
        print(f"PERSONA FOR {platform.upper()}")
        print(f"{'='*60}")
        print(persona["system_prompt"])
        print(f"\nTraits: {json.dumps(persona['traits'], indent=2)}")
    elif cmd == "status":
        dashboard = get_persona_dashboard()
        print(json.dumps(dashboard, indent=2))
    else:
        print("Usage: python persona_engine.py [reset|show <platform>|status]")

"""
Chicago Fleet Wraps — Optimization Engine v1.0
MULTI-ARMED BANDIT (Thompson Sampling) FOR CONTENT OPTIMIZATION

This module replaces the basic averaging in content_queue.py with a
statistically rigorous approach to learning what works.

It tracks "arms" (content components) across multiple dimensions:
  - Visual style: matte, satin, gloss, chrome, color-shift, etc.
  - Subject type: truck, sedan, SUV, van, fleet, exotic, etc.
  - Lighting: golden hour, studio, neon, dramatic, natural, etc.
  - Background: Chicago skyline, urban street, showroom, highway, etc.
  - Hook style: question, bold claim, statistic, story, controversy, etc.
  - CTA style: none, soft, direct
  - Tone: casual, professional, humorous, technical, inspirational
  - Caption length: short (<50 words), medium (50-100), long (100+)

Each arm has a Beta distribution (alpha, beta) updated by engagement
outcomes. Thompson Sampling selects the next arm to pull by sampling
from each arm's distribution and picking the highest sample.

The 30-day schedule controls the exploration-exploitation tradeoff
via an epsilon parameter that decays over time.
"""

import os
import json
import random
import math
from datetime import datetime, timedelta
from config import DATA_DIR

OPT_DIR = os.path.join(DATA_DIR, "optimization")
ARMS_FILE = os.path.join(OPT_DIR, "arms.json")
HISTORY_FILE = os.path.join(OPT_DIR, "decision_history.json")
SCHEDULE_FILE = os.path.join(OPT_DIR, "schedule.json")

# ═══════════════════════════════════════════════════════════════
# ARM DEFINITIONS — The dimensions the agent optimizes over
# ═══════════════════════════════════════════════════════════════

ARM_DIMENSIONS = {
    "visual_style": [
        "matte_black", "matte_white", "satin_finish", "gloss_finish",
        "chrome_wrap", "color_shift", "carbon_fiber", "camo_pattern",
        "racing_stripes", "full_color_change", "partial_wrap", "commercial_branding",
    ],
    "subject_type": [
        "pickup_truck", "sedan", "suv", "van", "box_truck",
        "sports_car", "exotic_car", "motorcycle", "boat",
        "fleet_vehicles", "food_truck", "trailer",
    ],
    "lighting": [
        "golden_hour", "studio_lighting", "neon_night", "dramatic_shadows",
        "natural_daylight", "overcast_moody", "sunset_backlit", "garage_spotlight",
    ],
    "background": [
        "chicago_skyline", "urban_street", "showroom_floor", "highway_motion",
        "parking_garage", "lakefront", "industrial_area", "residential_driveway",
    ],
    "hook_style": [
        "question", "bold_claim", "statistic", "before_after",
        "story", "controversy", "tip", "challenge",
    ],
    "cta_style": ["none", "soft", "direct"],
    "tone": [
        "casual", "professional", "humorous", "technical",
        "inspirational", "edgy", "friendly",
    ],
    "caption_length": ["short", "medium", "long"],
}


def _ensure_dirs():
    os.makedirs(OPT_DIR, exist_ok=True)


def _load_arms() -> dict:
    """Load arm statistics. Each arm has alpha (successes) and beta (failures)."""
    if os.path.exists(ARMS_FILE):
        try:
            with open(ARMS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _initialize_arms()


def _save_arms(arms: dict):
    _ensure_dirs()
    with open(ARMS_FILE, "w") as f:
        json.dump(arms, f, indent=2)


def _initialize_arms() -> dict:
    """Create initial arm statistics with uniform priors (alpha=1, beta=1)."""
    arms = {}
    for dimension, options in ARM_DIMENSIONS.items():
        arms[dimension] = {}
        for option in options:
            arms[dimension][option] = {
                "alpha": 1.0,   # Prior successes (Beta distribution)
                "beta": 1.0,    # Prior failures (Beta distribution)
                "pulls": 0,     # Total times this arm was selected
                "total_reward": 0.0,  # Cumulative engagement score
                "avg_reward": 0.0,
                "last_pulled": None,
            }
    _ensure_dirs()
    with open(ARMS_FILE, "w") as f:
        json.dump(arms, f, indent=2)
    return arms


def _load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(history: list):
    _ensure_dirs()
    history = history[-1000:]  # Keep last 1000 decisions
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ═══════════════════════════════════════════════════════════════
# 30-DAY SCHEDULE — Controls exploration vs exploitation
# ═══════════════════════════════════════════════════════════════

def get_current_phase() -> dict:
    """Determine the current phase of the 30-day optimization plan.

    Returns a dict with phase info and the current epsilon value
    (probability of exploring a random arm vs exploiting the best).
    """
    _ensure_dirs()

    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r") as f:
                schedule = json.load(f)
        except Exception:
            schedule = {}
    else:
        schedule = {}

    # Initialize start date if not set
    if "start_date" not in schedule:
        schedule["start_date"] = datetime.now().isoformat()
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(schedule, f, indent=2)

    start = datetime.fromisoformat(schedule["start_date"])
    elapsed_days = (datetime.now() - start).days

    if elapsed_days <= 7:
        return {
            "phase": "exploration",
            "week": 1,
            "day": elapsed_days,
            "epsilon": 0.8,
            "description": "Week 1: Broad exploration — gathering diverse data.",
        }
    elif elapsed_days <= 14:
        return {
            "phase": "pattern_recognition",
            "week": 2,
            "day": elapsed_days,
            "epsilon": 0.5,
            "description": "Week 2: Pattern recognition — identifying early winners.",
        }
    elif elapsed_days <= 21:
        return {
            "phase": "exploitation",
            "week": 3,
            "day": elapsed_days,
            "epsilon": 0.2,
            "description": "Week 3: Exploitation — doubling down on what works.",
        }
    else:
        return {
            "phase": "home_run",
            "week": 4,
            "day": elapsed_days,
            "epsilon": 0.05,
            "description": "Week 4: Home run phase — maximum engagement.",
        }


# ═══════════════════════════════════════════════════════════════
# THOMPSON SAMPLING — Select the best arm per dimension
# ═══════════════════════════════════════════════════════════════

def _thompson_sample(alpha: float, beta_param: float) -> float:
    """Draw a sample from Beta(alpha, beta) distribution."""
    try:
        return random.betavariate(max(alpha, 0.01), max(beta_param, 0.01))
    except Exception:
        return random.random()


def select_arms() -> dict:
    """Select one arm per dimension using Thompson Sampling.

    Respects the current phase's epsilon for exploration-exploitation balance.
    Returns a dict like: {"visual_style": "matte_black", "subject_type": "truck", ...}
    """
    arms = _load_arms()
    phase = get_current_phase()
    epsilon = phase["epsilon"]
    selection = {}

    for dimension, options in arms.items():
        if random.random() < epsilon:
            # EXPLORE: pick a random arm
            selection[dimension] = random.choice(list(options.keys()))
        else:
            # EXPLOIT: Thompson Sampling — sample from each arm's Beta
            # distribution and pick the one with the highest sample
            best_arm = None
            best_sample = -1.0
            for arm_name, stats in options.items():
                sample = _thompson_sample(stats["alpha"], stats["beta"])
                if sample > best_sample:
                    best_sample = sample
                    best_arm = arm_name
            selection[dimension] = best_arm

    # Log the decision
    history = _load_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "phase": phase["phase"],
        "epsilon": epsilon,
        "selection": selection,
        "outcome": None,  # Filled in later by record_outcome
    })
    _save_history(history)

    return selection


def record_outcome(selection: dict, engagement_score: float, threshold: float = 5.0):
    """Record the engagement outcome for a set of selected arms.

    Updates the Beta distribution for each arm based on whether the
    post's engagement score exceeded the threshold (success) or not (failure).

    Args:
        selection: The dict returned by select_arms().
        engagement_score: The post's unified engagement score.
        threshold: Score above which the post is considered a "success."
    """
    arms = _load_arms()
    success = engagement_score >= threshold

    for dimension, chosen_arm in selection.items():
        if dimension in arms and chosen_arm in arms[dimension]:
            stats = arms[dimension][chosen_arm]
            stats["pulls"] += 1
            stats["total_reward"] += engagement_score
            stats["avg_reward"] = stats["total_reward"] / stats["pulls"]
            stats["last_pulled"] = datetime.now().isoformat()

            if success:
                stats["alpha"] += 1.0
            else:
                stats["beta"] += 1.0

    _save_arms(arms)

    # Update the most recent history entry with the outcome
    history = _load_history()
    for entry in reversed(history):
        if entry.get("selection") == selection and entry.get("outcome") is None:
            entry["outcome"] = {
                "engagement_score": engagement_score,
                "success": success,
                "threshold": threshold,
            }
            break
    _save_history(history)


# ═══════════════════════════════════════════════════════════════
# PROMPT BUILDER — Turn arm selections into generation prompts
# ═══════════════════════════════════════════════════════════════

def build_image_prompt(selection: dict, topic: str = "") -> str:
    """Convert arm selections into a detailed AI image generation prompt.

    This is the bridge between the MAB engine and the media generator.
    """
    style_map = {
        "matte_black": "matte black vinyl wrap",
        "matte_white": "matte white vinyl wrap",
        "satin_finish": "satin finish vinyl wrap in deep metallic blue",
        "gloss_finish": "high-gloss candy red vinyl wrap",
        "chrome_wrap": "mirror chrome vinyl wrap",
        "color_shift": "color-shifting chameleon vinyl wrap (purple to green)",
        "carbon_fiber": "carbon fiber textured vinyl wrap",
        "camo_pattern": "urban camouflage vinyl wrap",
        "racing_stripes": "dual racing stripe vinyl wrap in contrasting colors",
        "full_color_change": "full color-change vinyl wrap in electric blue",
        "partial_wrap": "partial vinyl wrap with exposed original paint accents",
        "commercial_branding": "commercial fleet branding vinyl wrap with company logo",
    }

    subject_map = {
        "pickup_truck": "Ford F-150 pickup truck",
        "sedan": "BMW 3 Series sedan",
        "suv": "Chevrolet Tahoe SUV",
        "van": "Mercedes Sprinter van",
        "box_truck": "commercial box truck",
        "sports_car": "Chevrolet Corvette C8",
        "exotic_car": "Lamborghini Huracan",
        "motorcycle": "Harley-Davidson motorcycle",
        "boat": "speedboat",
        "fleet_vehicles": "fleet of matching delivery vans",
        "food_truck": "food truck with custom wrap",
        "trailer": "enclosed trailer",
    }

    lighting_map = {
        "golden_hour": "golden hour sunlight, warm tones, long shadows",
        "studio_lighting": "professional studio lighting, clean and bright",
        "neon_night": "neon-lit night scene, vibrant reflections on the wrap",
        "dramatic_shadows": "dramatic chiaroscuro lighting, deep shadows",
        "natural_daylight": "natural midday sunlight, clear sky",
        "overcast_moody": "overcast sky, moody atmosphere, soft diffused light",
        "sunset_backlit": "backlit by a vivid sunset, silhouette edges glowing",
        "garage_spotlight": "single spotlight in a dark garage, cinematic",
    }

    bg_map = {
        "chicago_skyline": "with the Chicago skyline and Willis Tower in the background",
        "urban_street": "parked on a gritty Chicago side street",
        "showroom_floor": "on a polished showroom floor with reflections",
        "highway_motion": "on a highway with motion blur in the background",
        "parking_garage": "in a concrete parking garage, industrial feel",
        "lakefront": "along Chicago's lakefront with Lake Michigan visible",
        "industrial_area": "in a Chicago industrial district with brick buildings",
        "residential_driveway": "in a suburban driveway, relatable setting",
    }

    style = style_map.get(selection.get("visual_style", ""), "premium vinyl wrap")
    subject = subject_map.get(selection.get("subject_type", ""), "vehicle")
    lighting = lighting_map.get(selection.get("lighting", ""), "professional lighting")
    background = bg_map.get(selection.get("background", ""), "Chicago backdrop")

    prompt = (
        f"Photorealistic image of a {subject} with a {style}, "
        f"{background}, {lighting}. "
        f"Professional automotive photography, 4K resolution, sharp focus, "
        f"cinematic composition. Do NOT include any text, logos, watermarks, or words."
    )

    return prompt


def build_caption_guidance(selection: dict) -> dict:
    """Convert arm selections into caption generation guidance.

    Returns a dict of instructions for the AI caption generator.
    """
    hook_map = {
        "question": "Start with a compelling question that makes the reader stop scrolling.",
        "bold_claim": "Open with a bold, attention-grabbing claim or statement.",
        "statistic": "Lead with a surprising statistic or number about vehicle wraps.",
        "before_after": "Frame this as a before/after transformation story.",
        "story": "Tell a short, relatable story about this vehicle or its owner.",
        "controversy": "Open with a mildly controversial or debate-sparking take.",
        "tip": "Lead with a practical tip or insider knowledge about wraps.",
        "challenge": "Issue a challenge or dare to the audience.",
    }

    tone_map = {
        "casual": "Write like you're texting a friend — relaxed, real, maybe a little slang.",
        "professional": "Write with authority and expertise — confident but approachable.",
        "humorous": "Be funny and witty — make them laugh, then make them think.",
        "technical": "Share technical details that show deep expertise — geek out a little.",
        "inspirational": "Inspire them — paint a picture of what their vehicle could look like.",
        "edgy": "Be bold and a little provocative — don't play it safe.",
        "friendly": "Be warm and welcoming — like a neighbor who happens to wrap cars.",
    }

    length_map = {
        "short": "Keep it under 50 words. Punchy and direct.",
        "medium": "Aim for 50-100 words. Enough to tell a story but not a novel.",
        "long": "Go for 100+ words. Deep dive, educational, or storytelling.",
    }

    return {
        "hook_instruction": hook_map.get(selection.get("hook_style", ""), ""),
        "tone_instruction": tone_map.get(selection.get("tone", ""), ""),
        "length_instruction": length_map.get(selection.get("caption_length", ""), ""),
        "cta_style": selection.get("cta_style", "none"),
    }


# ═══════════════════════════════════════════════════════════════
# ANALYTICS — What's winning, what's losing
# ═══════════════════════════════════════════════════════════════

def get_top_arms(n: int = 3) -> dict:
    """Get the top-performing arms per dimension.

    Returns a dict like: {"visual_style": [("matte_black", 12.5), ...], ...}
    """
    arms = _load_arms()
    top = {}

    for dimension, options in arms.items():
        ranked = sorted(
            [(name, stats["avg_reward"]) for name, stats in options.items() if stats["pulls"] > 0],
            key=lambda x: x[1],
            reverse=True,
        )
        top[dimension] = ranked[:n]

    return top


def get_bottom_arms(n: int = 3) -> dict:
    """Get the worst-performing arms per dimension."""
    arms = _load_arms()
    bottom = {}

    for dimension, options in arms.items():
        ranked = sorted(
            [(name, stats["avg_reward"]) for name, stats in options.items() if stats["pulls"] > 0],
            key=lambda x: x[1],
        )
        bottom[dimension] = ranked[:n]

    return bottom


def get_optimization_dashboard() -> dict:
    """Get a summary for the unified dashboard."""
    arms = _load_arms()
    phase = get_current_phase()
    history = _load_history()

    total_decisions = len(history)
    outcomes = [h for h in history if h.get("outcome")]
    successes = sum(1 for h in outcomes if h["outcome"].get("success"))
    success_rate = (successes / len(outcomes) * 100) if outcomes else 0

    return {
        "phase": phase,
        "total_decisions": total_decisions,
        "total_outcomes": len(outcomes),
        "success_rate": round(success_rate, 1),
        "top_arms": get_top_arms(3),
        "bottom_arms": get_bottom_arms(3),
    }


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def reset_optimization():
    """Reset all optimization data (for testing or fresh start)."""
    _ensure_dirs()
    _initialize_arms()
    _save_history([])
    if os.path.exists(SCHEDULE_FILE):
        os.remove(SCHEDULE_FILE)
    print("[OPT] Optimization engine reset.", flush=True)


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "reset":
        reset_optimization()
    elif cmd == "select":
        selection = select_arms()
        print(json.dumps(selection, indent=2))
        print(f"\nImage prompt: {build_image_prompt(selection)}")
        print(f"\nCaption guidance: {json.dumps(build_caption_guidance(selection), indent=2)}")
    elif cmd == "status":
        dashboard = get_optimization_dashboard()
        print(json.dumps(dashboard, indent=2))
    elif cmd == "top":
        top = get_top_arms(5)
        for dim, ranked in top.items():
            print(f"\n{dim}:")
            for name, score in ranked:
                print(f"  {name}: {score:.1f}")
    else:
        print("Usage: python optimization_engine.py [reset|select|status|top]")

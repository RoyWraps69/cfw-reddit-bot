"""
Chicago Fleet Wraps — Cross-Platform Intelligence v1.0
UNIFIED LEARNING ACROSS ALL CHANNELS

This module connects Reddit, Facebook, Instagram, and TikTok performance data
into ONE intelligence layer. Each platform's wins and losses inform the others.

Examples:
- "EV wraps" topic gets 10x engagement on TikTok → push it harder on Instagram too
- "Fleet branding" flops on TikTok but crushes on Facebook → stop TikTok fleet posts, double down on FB
- Short punchy comments win on Reddit → try shorter captions on Instagram
- A specific vehicle (Cybertruck) trends on one platform → immediately post about it everywhere

The brain uses this to make smarter decisions per platform while learning from ALL data.
"""
import os
import json
from datetime import datetime, timedelta
from config import DATA_DIR

CROSS_INTEL_FILE = os.path.join(DATA_DIR, "cross_platform_intel.json")
CROSS_HISTORY_FILE = os.path.join(DATA_DIR, "cross_platform_history.json")


class CrossPlatformIntel:
    """Unified intelligence layer across all social platforms."""

    def __init__(self):
        self.intel = self._load_intel()
        self.history = self._load_history()

    def _load_intel(self) -> dict:
        if os.path.exists(CROSS_INTEL_FILE):
            try:
                with open(CROSS_INTEL_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "topic_performance": {},
            "audience_performance": {},
            "content_type_performance": {},
            "platform_strengths": {},
            "cross_insights": [],
            "active_amplifications": [],
            "active_suppressions": [],
            "last_analysis": None,
        }

    def _load_history(self) -> list:
        if os.path.exists(CROSS_HISTORY_FILE):
            try:
                with open(CROSS_HISTORY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CROSS_INTEL_FILE, "w") as f:
            json.dump(self.intel, f, indent=2)
        with open(CROSS_HISTORY_FILE, "w") as f:
            json.dump(self.history[-500:], f, indent=2)

    # ─────────────────────────────────────────
    # INGEST: Feed performance data from any platform
    # ─────────────────────────────────────────

    def ingest_performance(self, platform: str, post_data: dict):
        """Ingest a single post's performance data from any platform.
        
        post_data should include:
        - topic: str
        - audience: str
        - content_type: str (image, video, text, carousel)
        - campaign: str
        - engagement_score: float (normalized score)
        - likes: int
        - comments: int
        - shares: int
        - views: int (optional)
        """
        topic = post_data.get("topic", "unknown").lower().strip()
        audience = post_data.get("audience", "unknown").lower().strip()
        content_type = post_data.get("content_type", "unknown").lower().strip()
        score = post_data.get("engagement_score", 0)

        # Track topic performance per platform
        if topic not in self.intel["topic_performance"]:
            self.intel["topic_performance"][topic] = {}
        if platform not in self.intel["topic_performance"][topic]:
            self.intel["topic_performance"][topic][platform] = {
                "scores": [], "count": 0, "avg": 0, "trend": "stable"
            }
        tp = self.intel["topic_performance"][topic][platform]
        tp["scores"].append(score)
        tp["scores"] = tp["scores"][-20:]  # Keep last 20
        tp["count"] += 1
        tp["avg"] = round(sum(tp["scores"]) / len(tp["scores"]), 2)

        # Track audience performance per platform
        if audience not in self.intel["audience_performance"]:
            self.intel["audience_performance"][audience] = {}
        if platform not in self.intel["audience_performance"][audience]:
            self.intel["audience_performance"][audience][platform] = {
                "scores": [], "count": 0, "avg": 0
            }
        ap = self.intel["audience_performance"][audience][platform]
        ap["scores"].append(score)
        ap["scores"] = ap["scores"][-20:]
        ap["count"] += 1
        ap["avg"] = round(sum(ap["scores"]) / len(ap["scores"]), 2)

        # Track content type performance per platform
        if content_type not in self.intel["content_type_performance"]:
            self.intel["content_type_performance"][content_type] = {}
        if platform not in self.intel["content_type_performance"][content_type]:
            self.intel["content_type_performance"][content_type][platform] = {
                "scores": [], "count": 0, "avg": 0
            }
        cp = self.intel["content_type_performance"][content_type][platform]
        cp["scores"].append(score)
        cp["scores"] = cp["scores"][-20:]
        cp["count"] += 1
        cp["avg"] = round(sum(cp["scores"]) / len(cp["scores"]), 2)

        # Record to history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "topic": topic,
            "audience": audience,
            "content_type": content_type,
            "score": score,
            "campaign": post_data.get("campaign", ""),
        })

        self._save()

    # ─────────────────────────────────────────
    # ANALYZE: Cross-platform pattern detection
    # ─────────────────────────────────────────

    def run_cross_analysis(self):
        """Run the full cross-platform analysis.
        
        This is the core intelligence function. It:
        1. Compares topic performance ACROSS platforms
        2. Identifies what's working on one platform but not others
        3. Creates amplification signals (push winners to other platforms)
        4. Creates suppression signals (stop losers on specific platforms)
        5. Identifies platform-specific strengths
        """
        print(f"\n  [CROSS-INTEL] Running cross-platform analysis...", flush=True)

        insights = []
        amplifications = []
        suppressions = []

        # ── TOPIC CROSS-ANALYSIS ──
        for topic, platforms in self.intel.get("topic_performance", {}).items():
            if len(platforms) < 2:
                continue  # Need data from at least 2 platforms

            # Find the best and worst performing platform for this topic
            platform_avgs = {p: d["avg"] for p, d in platforms.items() if d["count"] >= 2}
            if len(platform_avgs) < 2:
                continue

            best_platform = max(platform_avgs, key=platform_avgs.get)
            worst_platform = min(platform_avgs, key=platform_avgs.get)
            best_score = platform_avgs[best_platform]
            worst_score = platform_avgs[worst_platform]

            # Significant difference? (best is 2x+ better than worst)
            if best_score > 0 and worst_score >= 0:
                ratio = best_score / max(worst_score, 0.1)

                if ratio >= 2.0:
                    # Topic crushes on one platform, flops on another
                    insight = {
                        "type": "topic_divergence",
                        "topic": topic,
                        "winner": {"platform": best_platform, "avg_score": best_score},
                        "loser": {"platform": worst_platform, "avg_score": worst_score},
                        "ratio": round(ratio, 1),
                        "action": f"AMPLIFY '{topic}' on {best_platform}, REDUCE on {worst_platform}",
                    }
                    insights.append(insight)

                    # Create amplification for platforms that haven't tried this topic yet
                    all_platforms = {"reddit", "facebook", "instagram", "tiktok"}
                    untried = all_platforms - set(platforms.keys())
                    for p in untried:
                        amplifications.append({
                            "topic": topic,
                            "target_platform": p,
                            "reason": f"Performing {ratio:.1f}x better on {best_platform}",
                            "source_platform": best_platform,
                            "confidence": min(ratio / 3, 1.0),
                        })

                    # Suppress on worst platform if really bad
                    if worst_score < 1.0 and ratio > 3.0:
                        suppressions.append({
                            "topic": topic,
                            "platform": worst_platform,
                            "reason": f"Only {worst_score:.1f} avg vs {best_score:.1f} on {best_platform}",
                        })

                elif ratio <= 0.5:
                    # Topic works everywhere — universal winner
                    insight = {
                        "type": "universal_winner",
                        "topic": topic,
                        "platforms": platform_avgs,
                        "action": f"PUSH '{topic}' across ALL platforms",
                    }
                    insights.append(insight)
                    for p in {"reddit", "facebook", "instagram", "tiktok"} - set(platforms.keys()):
                        amplifications.append({
                            "topic": topic,
                            "target_platform": p,
                            "reason": "Universal winner across tested platforms",
                            "source_platform": "all",
                            "confidence": 0.8,
                        })

        # ── AUDIENCE CROSS-ANALYSIS ──
        for audience, platforms in self.intel.get("audience_performance", {}).items():
            platform_avgs = {p: d["avg"] for p, d in platforms.items() if d["count"] >= 2}
            if len(platform_avgs) < 2:
                continue

            best_p = max(platform_avgs, key=platform_avgs.get)
            worst_p = min(platform_avgs, key=platform_avgs.get)

            if platform_avgs[best_p] > platform_avgs[worst_p] * 2:
                insights.append({
                    "type": "audience_platform_fit",
                    "audience": audience,
                    "best_platform": best_p,
                    "worst_platform": worst_p,
                    "action": f"Target '{audience}' primarily on {best_p}",
                })

        # ── CONTENT TYPE CROSS-ANALYSIS ──
        for ctype, platforms in self.intel.get("content_type_performance", {}).items():
            platform_avgs = {p: d["avg"] for p, d in platforms.items() if d["count"] >= 2}
            if platform_avgs:
                best_p = max(platform_avgs, key=platform_avgs.get)
                insights.append({
                    "type": "content_type_strength",
                    "content_type": ctype,
                    "best_platform": best_p,
                    "score": platform_avgs[best_p],
                })

        # ── PLATFORM STRENGTHS ──
        platform_strengths = {}
        for topic, platforms in self.intel.get("topic_performance", {}).items():
            for p, data in platforms.items():
                if data["count"] < 2:
                    continue
                if p not in platform_strengths:
                    platform_strengths[p] = {"winning_topics": [], "losing_topics": []}
                if data["avg"] > 5:
                    platform_strengths[p]["winning_topics"].append(
                        {"topic": topic, "avg": data["avg"]}
                    )
                elif data["avg"] < 1:
                    platform_strengths[p]["losing_topics"].append(
                        {"topic": topic, "avg": data["avg"]}
                    )

        # Sort by performance
        for p in platform_strengths:
            platform_strengths[p]["winning_topics"].sort(
                key=lambda x: x["avg"], reverse=True
            )
            platform_strengths[p]["winning_topics"] = platform_strengths[p]["winning_topics"][:10]
            platform_strengths[p]["losing_topics"].sort(key=lambda x: x["avg"])
            platform_strengths[p]["losing_topics"] = platform_strengths[p]["losing_topics"][:5]

        # Update intel
        self.intel["platform_strengths"] = platform_strengths
        self.intel["cross_insights"] = insights[-50:]
        self.intel["active_amplifications"] = amplifications[-30:]
        self.intel["active_suppressions"] = suppressions[-20:]
        self.intel["last_analysis"] = datetime.now().isoformat()

        self._save()

        print(f"  [CROSS-INTEL] Analysis complete:", flush=True)
        print(f"    Insights: {len(insights)}", flush=True)
        print(f"    Amplifications: {len(amplifications)}", flush=True)
        print(f"    Suppressions: {len(suppressions)}", flush=True)

        return {
            "insights": insights,
            "amplifications": amplifications,
            "suppressions": suppressions,
            "platform_strengths": platform_strengths,
        }

    # ─────────────────────────────────────────
    # QUERY: Get recommendations for a specific platform
    # ─────────────────────────────────────────

    def get_platform_recommendations(self, platform: str) -> dict:
        """Get cross-platform-informed recommendations for a specific platform.
        
        Returns what to amplify, what to suppress, and what to try based on
        other platforms' performance data.
        """
        amplify = [a for a in self.intel.get("active_amplifications", [])
                   if a.get("target_platform") == platform]
        suppress = [s for s in self.intel.get("active_suppressions", [])
                    if s.get("platform") == platform]

        # Get this platform's strengths
        strengths = self.intel.get("platform_strengths", {}).get(platform, {})

        # Find topics that work on OTHER platforms but haven't been tried here
        untried_winners = []
        for topic, platforms in self.intel.get("topic_performance", {}).items():
            if platform in platforms:
                continue  # Already tried on this platform
            # Check if it's winning elsewhere
            other_avgs = [d["avg"] for p, d in platforms.items() if d["count"] >= 2]
            if other_avgs and max(other_avgs) > 5:
                best_other = max(platforms.items(), key=lambda x: x[1]["avg"])
                untried_winners.append({
                    "topic": topic,
                    "proven_on": best_other[0],
                    "avg_score": best_other[1]["avg"],
                })

        untried_winners.sort(key=lambda x: x["avg_score"], reverse=True)

        return {
            "amplify_topics": amplify[:5],
            "suppress_topics": suppress[:3],
            "platform_winning_topics": strengths.get("winning_topics", [])[:5],
            "platform_losing_topics": strengths.get("losing_topics", [])[:3],
            "untried_winners": untried_winners[:5],
        }

    def get_strategy_override(self, platform: str, proposed_topic: str) -> dict:
        """Check if a proposed topic should be overridden based on cross-platform data.
        
        Returns:
        - {"action": "proceed"} — go ahead
        - {"action": "amplify", "reason": "..."} — definitely post this
        - {"action": "suppress", "reason": "...", "alternative": "..."} — don't post, try this instead
        - {"action": "adapt", "reason": "...", "suggestion": "..."} — post but adjust
        """
        topic_lower = proposed_topic.lower().strip()

        # Check suppressions
        for s in self.intel.get("active_suppressions", []):
            if s.get("platform") == platform and s.get("topic", "").lower() == topic_lower:
                # Find a better alternative
                recs = self.get_platform_recommendations(platform)
                alternative = ""
                if recs.get("untried_winners"):
                    alternative = recs["untried_winners"][0]["topic"]
                elif recs.get("amplify_topics"):
                    alternative = recs["amplify_topics"][0]["topic"]

                return {
                    "action": "suppress",
                    "reason": s.get("reason", "Poor cross-platform performance"),
                    "alternative": alternative,
                }

        # Check amplifications
        for a in self.intel.get("active_amplifications", []):
            if a.get("target_platform") == platform and a.get("topic", "").lower() == topic_lower:
                return {
                    "action": "amplify",
                    "reason": a.get("reason", "Cross-platform winner"),
                }

        # Check if this topic has mixed results across platforms
        topic_data = self.intel.get("topic_performance", {}).get(topic_lower, {})
        if platform in topic_data:
            platform_avg = topic_data[platform].get("avg", 0)
            other_avgs = [d["avg"] for p, d in topic_data.items()
                         if p != platform and d["count"] >= 2]
            if other_avgs:
                other_avg = sum(other_avgs) / len(other_avgs)
                if platform_avg < other_avg * 0.5:
                    return {
                        "action": "adapt",
                        "reason": f"This topic scores {platform_avg:.1f} here vs {other_avg:.1f} avg elsewhere",
                        "suggestion": "Try a different angle or format for this platform",
                    }

        return {"action": "proceed"}

    # ─────────────────────────────────────────
    # DASHBOARD DATA
    # ─────────────────────────────────────────

    def get_dashboard_data(self) -> dict:
        """Get cross-platform intelligence data for the unified dashboard."""
        return {
            "last_analysis": self.intel.get("last_analysis"),
            "insights_count": len(self.intel.get("cross_insights", [])),
            "active_amplifications": self.intel.get("active_amplifications", [])[:10],
            "active_suppressions": self.intel.get("active_suppressions", [])[:10],
            "cross_insights": self.intel.get("cross_insights", [])[:10],
            "platform_strengths": self.intel.get("platform_strengths", {}),
            "topic_count": len(self.intel.get("topic_performance", {})),
        }


def get_cross_intel() -> CrossPlatformIntel:
    """Get a CrossPlatformIntel instance."""
    return CrossPlatformIntel()

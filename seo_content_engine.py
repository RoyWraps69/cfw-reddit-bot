"""
Chicago Fleet Wraps — SEO Content Engine v1.0

Generates keyword-targeted blog posts for chicagofleetwraps.com.
The domain has 10 years of history — this is untapped SEO authority.

Target keywords by search intent:
  INFORMATIONAL: "how much does a car wrap cost", "how long do wraps last"
  NAVIGATIONAL: "chicago fleet wraps", "car wrap shop chicago"
  COMMERCIAL: "best wrap shop chicago", "fleet wrap company chicago"
  TRANSACTIONAL: "get a car wrap quote chicago", "car wrap near me chicago"

Each post:
  - Targets a specific keyword
  - 800-1200 words (Google sweet spot for local service pages)
  - Includes local signals (neighborhood names, Chicago-specific context)
  - Has proper H1/H2/H3 structure
  - Includes FAQ section (triggers Google featured snippets)
  - Natural internal linking to the price calculator

WordPress integration: posts directly via the WP REST API
"""

import os
import json
import random
from datetime import datetime, date
from openai import OpenAI

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEO_LOG = os.path.join(DATA_DIR, "seo_content_log.json")

WORDPRESS_URL = os.environ.get("WORDPRESS_URL", "https://chicagofleetwraps.com")
WORDPRESS_USERNAME = os.environ.get("WORDPRESS_USERNAME", "")
WORDPRESS_APP_PASSWORD = os.environ.get("WORDPRESS_APP_PASSWORD", "")  # WP Application Password

client = OpenAI()

# ─────────────────────────────────────────────────────────────────────
# KEYWORD STRATEGY
# ─────────────────────────────────────────────────────────────────────

SEO_KEYWORD_TARGETS = [
    # High-intent local
    {"keyword": "car wrap shop chicago", "monthly_volume": "high", "intent": "commercial", "priority": 1},
    {"keyword": "fleet wrap chicago", "monthly_volume": "high", "intent": "commercial", "priority": 1},
    {"keyword": "vehicle wrap chicago il", "monthly_volume": "high", "intent": "commercial", "priority": 1},
    {"keyword": "vinyl wrap chicago", "monthly_volume": "medium", "intent": "commercial", "priority": 1},

    # Informational (top of funnel)
    {"keyword": "how much does a car wrap cost", "monthly_volume": "very_high", "intent": "informational", "priority": 2},
    {"keyword": "how long does a vehicle wrap last", "monthly_volume": "high", "intent": "informational", "priority": 2},
    {"keyword": "car wrap vs paint job cost comparison", "monthly_volume": "medium", "intent": "informational", "priority": 2},
    {"keyword": "how to care for a car wrap", "monthly_volume": "medium", "intent": "informational", "priority": 2},
    {"keyword": "what is ppf coating", "monthly_volume": "medium", "intent": "informational", "priority": 2},
    {"keyword": "3m vs avery vinyl wrap", "monthly_volume": "medium", "intent": "informational", "priority": 2},

    # Vehicle-specific (high conversion)
    {"keyword": "rivian wrap chicago", "monthly_volume": "low", "intent": "commercial", "priority": 1},
    {"keyword": "cargo van wrap cost", "monthly_volume": "medium", "intent": "commercial", "priority": 1},
    {"keyword": "food truck wrap chicago", "monthly_volume": "low", "intent": "commercial", "priority": 1},
    {"keyword": "box truck wrap chicago", "monthly_volume": "low", "intent": "commercial", "priority": 1},
    {"keyword": "sprinter van wrap cost", "monthly_volume": "medium", "intent": "commercial", "priority": 2},

    # Business/fleet
    {"keyword": "fleet vehicle wraps for small business", "monthly_volume": "medium", "intent": "commercial", "priority": 2},
    {"keyword": "vehicle wrap tax deduction section 179", "monthly_volume": "medium", "intent": "informational", "priority": 2},
    {"keyword": "commercial fleet graphics chicago", "monthly_volume": "medium", "intent": "commercial", "priority": 1},

    # Seasonal
    {"keyword": "car wrap color change chicago", "monthly_volume": "medium", "intent": "commercial", "priority": 2},
    {"keyword": "ppf paint protection film chicago", "monthly_volume": "medium", "intent": "commercial", "priority": 2},
    {"keyword": "chrome delete wrap chicago", "monthly_volume": "low", "intent": "commercial", "priority": 3},
]


def get_next_keyword_target() -> dict:
    """Get the highest-priority keyword that hasn't been written about recently."""
    seo_log = _load_seo_log()
    published_keywords = {entry["keyword"] for entry in seo_log}

    # Filter out already-published keywords
    available = [k for k in SEO_KEYWORD_TARGETS if k["keyword"] not in published_keywords]

    if not available:
        # All keywords done — start over from priority 1
        available = [k for k in SEO_KEYWORD_TARGETS if k["priority"] == 1]

    # Sort by priority then volume
    volume_order = {"very_high": 4, "high": 3, "medium": 2, "low": 1}
    available.sort(key=lambda x: (x["priority"], -volume_order.get(x.get("monthly_volume", "low"), 1)))

    return available[0] if available else SEO_KEYWORD_TARGETS[0]


# ─────────────────────────────────────────────────────────────────────
# CONTENT GENERATION
# ─────────────────────────────────────────────────────────────────────

CFW_SEO_CONTEXT = """
Chicago Fleet Wraps | 4711 N. Lamon Ave, Portage Park, Chicago IL 60630
Owner: Roy | Since 2014 | 10+ years experience | 600+ Rivians wrapped
Services: Fleet wraps, color change, PPF, vinyl lettering, EV wraps, signage
Materials: 3M 2080, Avery Dennison SW900, XPEL PPF
Pricing: Cargo van starts $3,750 | Color change $3,500-4,500 | Fleet discount up to 15%
Turnaround: 3-5 business days
Phone: (312) 597-1286 | Website: chicagofleetwraps.com
Price calculator: chicagofleetwraps.com/calculator
"""

def generate_seo_blog_post(keyword: str = None, keyword_data: dict = None) -> dict:
    """Generate a full SEO-optimized blog post targeting a specific keyword."""

    if not keyword_data:
        keyword_data = get_next_keyword_target()
    if not keyword:
        keyword = keyword_data["keyword"]

    intent = keyword_data.get("intent", "informational")

    intent_instructions = {
        "informational": "Answer the question completely and authoritatively. Be the best resource on this topic. Don't sell — educate. The mention of CFW should be natural and minimal.",
        "commercial": "Help the reader make a decision. Include CFW naturally as an example or recommendation. Include pricing, process, and what sets quality shops apart.",
        "transactional": "This person is ready to buy. Make it easy for them to take action. Include CFW's contact info, pricing, and calculator link prominently.",
    }

    prompt = f"""Write a complete, SEO-optimized blog post for Chicago Fleet Wraps targeting the keyword: "{keyword}"

BUSINESS CONTEXT:
{CFW_SEO_CONTEXT}

CONTENT INTENT: {intent_instructions.get(intent, intent_instructions['informational'])}

STRUCTURE REQUIREMENTS:
1. H1: Include the target keyword naturally
2. Introduction (100-150 words): Hook + what the reader will learn
3. 3-5 H2 sections with relevant H3 subsections
4. FAQ section (4-6 Q&A pairs that target "People Also Ask" queries)
5. Conclusion with CTA

WRITING RULES:
- 900-1200 words total
- Include Chicago-specific context (neighborhoods, winters, traffic density, etc.)
- Include specific prices, timelines, and material names — specificity builds trust
- Natural keyword density: target keyword appears 3-5 times, variations throughout
- Write for a real person who's considering a wrap, not for an algorithm
- Include at least 2 internal links using this format: [anchor text](chicagofleetwraps.com/path)
  - Always link to: chicagofleetwraps.com/calculator for the price calculator
  - Link to: chicagofleetwraps.com for the homepage when appropriate
- Include 1-2 "Did you know?" facts that are genuinely surprising

Return ONLY valid JSON:
{{
    "title": "SEO title (55-60 chars, includes keyword)",
    "meta_description": "Meta description (150-160 chars, includes keyword, compelling)",
    "slug": "url-slug-for-post",
    "content_html": "Full HTML blog post content",
    "target_keyword": "{keyword}",
    "secondary_keywords": ["list", "of", "3-5", "related", "keywords"],
    "word_count": 0,
    "faq_questions": ["list", "of", "4-6", "FAQ", "questions"],
    "internal_links": ["list", "of", "internal", "links", "used"]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )

    try:
        post = json.loads(response.choices[0].message.content)
        post["generated_at"] = str(datetime.now())
        post["keyword_data"] = keyword_data
        return post
    except Exception as e:
        return {"error": str(e), "keyword": keyword}


def publish_to_wordpress(post: dict) -> dict:
    """Publish a blog post to WordPress via REST API."""
    if not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return {
            "status": "no_credentials",
            "note": "Set WORDPRESS_USERNAME and WORDPRESS_APP_PASSWORD (WP Application Password)",
            "post_preview": post.get("title", ""),
        }

    api_url = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"

    wp_payload = {
        "title": post.get("title", ""),
        "content": post.get("content_html", ""),
        "status": "draft",  # Draft first — Roy reviews before publishing
        "slug": post.get("slug", ""),
        "excerpt": post.get("meta_description", ""),
        "meta": {
            "_yoast_wpseo_focuskw": post.get("target_keyword", ""),
            "_yoast_wpseo_metadesc": post.get("meta_description", ""),
        },
    }

    try:
        response = requests.post(
            api_url,
            json=wp_payload,
            auth=(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD),
            timeout=30,
        )
        if response.status_code in (200, 201):
            wp_post = response.json()
            post_id = wp_post.get("id")
            _log_seo_post(post, post_id, status="draft")
            return {"status": "draft_created", "post_id": post_id,
                    "edit_url": f"{WORDPRESS_URL}/wp-admin/post.php?post={post_id}&action=edit"}
        else:
            return {"status": "error", "code": response.status_code, "body": response.text[:300]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_seo_content_cycle(posts_to_generate: int = 1) -> list:
    """Generate and publish SEO blog posts."""
    results = []
    for _ in range(posts_to_generate):
        keyword_data = get_next_keyword_target()
        print(f"[SEO] Generating post for: {keyword_data['keyword']}", flush=True)

        post = generate_seo_blog_post(keyword_data=keyword_data)
        if "error" not in post:
            wp_result = publish_to_wordpress(post)
            results.append({"keyword": keyword_data["keyword"], "post": post, "wordpress": wp_result})
            print(f"[SEO] WordPress result: {wp_result.get('status')}", flush=True)
        else:
            results.append({"keyword": keyword_data["keyword"], "error": post["error"]})

    return results


def _log_seo_post(post: dict, post_id: int = None, status: str = "draft"):
    """Log published SEO content."""
    os.makedirs(DATA_DIR, exist_ok=True)
    log = _load_seo_log()
    log.append({
        "date": str(date.today()),
        "keyword": post.get("target_keyword", ""),
        "title": post.get("title", ""),
        "slug": post.get("slug", ""),
        "word_count": post.get("word_count", 0),
        "post_id": post_id,
        "status": status,
    })
    with open(SEO_LOG, "w") as f:
        json.dump(log, f, indent=2)


def _load_seo_log() -> list:
    if os.path.exists(SEO_LOG):
        try:
            with open(SEO_LOG) as f:
                return json.load(f)
        except Exception:
            pass
    return []

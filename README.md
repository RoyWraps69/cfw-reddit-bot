# Chicago Fleet Wraps — Autonomous Marketing System v6.0

Full-stack autonomous marketing system for Chicago Fleet Wraps.
Reddit bot + 5-agent content orchestrator + CRM + Google Business Profile + Review automation + SEO + Email nurture.

---

## Quick Start (5 minutes)

```bash
# 1. Clone the repo
git clone https://github.com/RoyWraps69/cfw-reddit-bot
cd cfw-reddit-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the setup script — migrates your existing .env and shows what's missing
python setup_env.py

# 4. Fill in missing keys in .env

# 5. Test one cycle
python master_runner.py once

# 6. Start continuous operation
python master_runner.py run
```

---

## System Architecture

```
master_runner.py          ← Single entry point for everything
│
├── bot.py                ← Reddit bot (comments, DMs, replies)
├── orchestrator.py       ← 5-agent content system
│   ├── agents/strategy_agent.py   ← CMO — decides what to create
│   ├── agents/creative_agent.py   ← Director — generates content
│   ├── agents/quality_agent.py    ← Editor — reviews before publishing
│   ├── agents/monitor_agent.py    ← Analyst — publishes + tracks
│   └── agents/community_agent.py  ← Manager — engagement + lead detection
│
├── lead_alert.py         ← SMS/Slack alerts when hot lead detected
├── lead_crm.py           ← Lead pipeline tracking
├── calculator_webhook.py ← Flask server receiving calculator form submissions
├── google_business_profile.py  ← GBP posts + review responses
├── review_generator.py   ← Post-job review request automation
├── seo_content_engine.py ← Blog post generation for chicagofleetwraps.com
├── email_nurture.py      ← 5-email nurture sequences
├── intelligence_bridge.py ← Shared data layer connecting all systems
│
├── persona_engine_v2.py  ← 10 evolved personas with psychology
├── sales_psychology.py   ← Cialdini principles + objection scripts + AIDA
├── content_creator.py    ← Video script generation (Runway/HeyGen/ElevenLabs)
├── self_optimizer.py     ← Daily self-improvement questions + strategy updates
└── ai_responder.py       ← AI response generation (updated v6.0)
```

---

## Commands

```bash
python master_runner.py run      # 24/7 autonomous operation
python master_runner.py once     # Single cycle (test)
python master_runner.py status   # System status report
python master_runner.py leads    # CRM pipeline report
python master_runner.py brief    # Send morning brief SMS to Roy
python master_runner.py health   # Health check all systems

python bot.py auto               # Reddit bot only
python orchestrator.py full      # Content agents only
python calculator_webhook.py     # Start webhook server (port 5001)
python setup_env.py              # Re-run environment setup
```

---

## Daily Schedule (auto)

| Time | Activity |
|------|----------|
| 6:00 AM | Self-optimizer runs — generates today's questions, updates strategy |
| 6:30 AM | Morning brief SMS sent to Roy |
| 7:00 AM | Intelligence bridge sync |
| 7:00 AM–11:00 PM | Reddit posting cycles every 45-90 min |
| Peak hours | 5-agent orchestrator + lead processing + GBP reviews |
| Monday | Weekly GBP post published |
| Wednesday | SEO blog post drafted to WordPress |
| Friday | Weekly CRM + persona report |

---

## New API Keys Needed (Priority Order)

### Week 1 — Revenue Impact

1. **Twilio** (twilio.com) — Roy gets texted on every hot lead
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `ROY_PHONE_NUMBER`

2. **Google Business Profile** (developers.google.com/my-business) — weekly GBP posts + review responses
   - `GBP_ACCESS_TOKEN`, `GBP_ACCOUNT_ID`, `GBP_LOCATION_ID`, `GOOGLE_REVIEW_LINK`

3. **SendGrid** (sendgrid.com — 100 emails/day free) — email nurture sequences
   - `SENDGRID_API_KEY`

4. **Calculator webhook** — add `WEBHOOK_SECRET` to .env, then point your website form to:
   - `https://your-railway-app.railway.app/webhook/calculator`

### Week 2 — Content Creation

5. **ElevenLabs** (elevenlabs.io) — clone Roy's voice for TikTok/Reels voiceovers
   - `ELEVENLABS_API_KEY`, `ELEVENLABS_ROY_VOICE_ID`
   - Clone voice: ElevenLabs → Voice Cloning → Add Voice → upload 5+ min of Roy speaking

6. **RunwayML** (runwayml.com) — AI video generation
   - `RUNWAY_API_KEY`

7. **HeyGen** (heygen.com) — AI spokesperson videos
   - `HEYGEN_API_KEY`

### Week 3 — Distribution

8. **Facebook** — `FACEBOOK_PAGE_TOKEN`, `FACEBOOK_PAGE_ID`
9. **WordPress** — `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD`
10. **YouTube** — `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`

---

## Deployment on Railway

```bash
# Push to GitHub
git add .
git commit -m "v6.0 complete system"
git push

# Railway auto-deploys from GitHub
# Add all .env variables in Railway dashboard → Variables
# Railway → New Project → Deploy from GitHub repo
```

The `railway.toml` and `Procfile` are already configured.

---

## What This System Does

Every day, automatically:
- Posts 6-8 targeted Reddit comments
- Generates 2-4 platform-specific video scripts
- Publishes Facebook posts and queues TikTok/Reels/Shorts
- Responds to Google reviews
- Sends review requests to recent customers
- Follows up with warm leads via DM and email
- Texts Roy when a hot lead appears
- Posts weekly to Google Business Profile
- Drafts SEO blog posts for chicagofleetwraps.com
- Runs a self-improvement cycle to get smarter every day

No manual intervention required.

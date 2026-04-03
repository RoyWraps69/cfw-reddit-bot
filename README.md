# Chicago Fleet Wraps — Autonomous Marketing System v6.0

**Website hosting:** Netlify
**Bot & automation:** GitHub Actions (free, runs on schedule)
**Alerts & webhooks:** Netlify Functions

---

## Architecture

```
chicagofleetwraps.com (Netlify)
├── netlify/functions/calculator.js   ← SMS Roy when calculator is used
├── netlify/functions/reddit-lead.js  ← SMS Roy when Reddit lead detected
└── netlify/functions/health.js       ← Health check

GitHub Actions (free, scheduled)
├── bot-cycle.yml       → Reddit bot every 45 min, 7 AM–11 PM CT
├── daily-optimizer.yml → Self-optimizer + morning brief at 6 AM
├── content-cycle.yml   → Content creation Tue/Thu/Sat
└── leads-reviews.yml   → Email nurture + review requests 3x/day
```

---

## Setup

### Netlify environment variables (Site → Environment variables)
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, ROY_PHONE_NUMBER,
SLACK_WEBHOOK_URL, SENDGRID_API_KEY, GBP_ACCESS_TOKEN, GBP_ACCOUNT_ID,
GBP_LOCATION_ID, GOOGLE_REVIEW_LINK

Point calculator form to: https://chicagofleetwraps.com/webhook/calculator

### GitHub Actions secrets (Settings → Secrets → Actions)
OPENAI_API_KEY, REDDIT_USERNAME, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
REDDIT_PASSWORD, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER,
ROY_PHONE_NUMBER, FACEBOOK_PAGE_TOKEN, FACEBOOK_PAGE_ID, WORDPRESS_URL,
WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD, SENDGRID_API_KEY,
GBP_ACCESS_TOKEN, GBP_ACCOUNT_ID, GBP_LOCATION_ID, GOOGLE_REVIEW_LINK,
YELP_REVIEW_LINK, RUNWAY_API_KEY, HEYGEN_API_KEY, ELEVENLABS_API_KEY,
ELEVENLABS_ROY_VOICE_ID

---

## What runs when

| Time | Workflow | Action |
|------|----------|--------|
| Every 45 min, 7 AM–11 PM CT | bot-cycle | Reddit comments + replies + DMs |
| 6 AM daily | daily-optimizer | Self-optimizer + morning brief SMS to Roy |
| Tue/Thu/Sat 9 AM | content-cycle | Video scripts + GBP post + SEO blog |
| 9 AM, 1 PM, 6 PM | leads-reviews | Email nurture + review request SMS |
| Friday | leads-reviews | Weekly CRM + persona report |

Manually trigger any workflow: GitHub → Actions tab → Run workflow

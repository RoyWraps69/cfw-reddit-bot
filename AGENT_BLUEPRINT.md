# Chicago Fleet Wraps: 30-Day Self-Improving AI Agent Blueprint

This document outlines the architectural transformation of the `cfw-reddit-bot` repository from a scheduled automation script into a true, self-improving **Multi-Agent System**. The goal is to build an autonomous system that generates high-quality AI media, learns from real-world engagement, develops a distinct personality, and optimizes its own performance over a 30-day period to achieve maximum positive interactions.

## 1. The Multi-Agent Framework

The core of the new system is a message-based architecture. Instead of one monolithic script trying to do everything, five specialized AI agents communicate through a central `MessageBus`. This allows for complex workflows, such as the Quality Agent rejecting the Creative Agent's work and forcing a revision.

### The Five Agents

| Agent | Role | Responsibilities |
| :--- | :--- | :--- |
| **Strategy Agent** | Chief Marketing Officer | Analyzes trends, consults the optimization engine, and decides WHAT to post, WHERE, and WHEN. Issues content requests to the Creative Agent. |
| **Creative Agent** | Creative Director | Generates all content (images, videos, captions, hooks). Uses the persona engine to ensure the voice sounds like Roy. Sends drafts to the Quality Agent. |
| **Quality Agent** | Quality Editor | The gatekeeper. Reviews all drafts against strict brand standards. Approves good content or rejects bad content with specific feedback for revision. |
| **Monitor Agent** | Performance Analyst | Publishes approved content. Tracks engagement velocity, runs attribution analysis, and feeds learnings back to Strategy. Issues kill signals for failing posts. |
| **Community Agent** | Community Manager | Runs in parallel to handle all inbound and outbound engagement. Responds to comments, builds relationships with key accounts, and surfs trends. |

### The Communication Loop

The content pipeline operates as a continuous feedback loop:

1. **Strategy** sends a `CONTENT_REQUEST` to **Creative**.
2. **Creative** generates the content and sends a `CONTENT_DRAFT` to **Quality**.
3. **Quality** reviews the draft. If it fails, it sends a `REVISION_REQUEST` back to **Creative**. If it passes, it sends `CONTENT_APPROVED` to **Monitor**.
4. **Monitor** publishes the content, tracks its performance, and sends a `PERFORMANCE_REPORT` and `LEARNING_UPDATE` back to **Strategy**.
5. **Community** receives `RESPOND_REQUEST` messages from **Monitor** when comments need replies.

## 2. The Learning Engines

The agents rely on three core engines to continuously improve over the 30-day optimization period.

### Optimization Engine (Multi-Armed Bandit)
This engine breaks content down into "arms" (components like visual style, hook style, tone, and CTA). It uses an epsilon-greedy algorithm to balance exploring new combinations with exploiting proven winners [1]. As the Monitor Agent feeds engagement data back, the engine learns which combinations drive the highest interaction.

### Persona Engine
This engine ensures the AI sounds like Roy, the owner of CFW. It maintains platform-specific personas (e.g., casual on TikTok, helpful on Reddit) and dynamically adjusts the system prompts based on what resonates with the audience.

### Engagement Tracker
This module ingests real-time data across all platforms. It tracks not just total likes, but engagement velocity (how fast interactions occur). It runs attribution analysis to determine *why* a post succeeded or failed, providing actionable insights to the Strategy Agent.

## 3. The 30-Day Optimization Plan

The system is designed to evolve from a baseline state to a highly optimized engagement machine over 30 days.

| Phase | Timeline | Goal | Action | MAB State | Success Metric |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Week 1: Exploration & Baseline** | Days 1-7 | Gather diverse data. | Generate a wide variety of content (different vehicle types, wrap colors, caption lengths, and tones). | High exploration rate (epsilon = 0.8). | Establish baseline engagement rates for each platform. |
| **Week 2: Pattern Recognition** | Days 8-14 | Identify early winners. | The Deep Feedback Loop attributes success to specific prompt components and persona traits. The agent drops the lowest-performing content types. | Moderate exploration (epsilon = 0.5). | 20% increase in average engagement score compared to Week 1. |
| **Week 3: Exploitation & Refinement** | Days 15-21 | Double down on what works. | The Visual Prompt Optimizer heavily favors winning combinations. The Persona Engine locks into the most effective voice per platform. | Low exploration (epsilon = 0.2). | Consistent high-performing posts; significant reduction in low-engagement posts. |
| **Week 4: The "Home Run" Phase** | Days 22-30 | Maximum engagement and viral potential. | The agent is highly specialized, generating content only using statistically proven prompts and hooks. It actively surfs real-time trends and engages with high-value accounts. | Pure exploitation (epsilon = 0.05). | Achieving consistently high engagement rates across all platforms. |

## 4. Deployment and Execution

The system is deployed via GitHub Actions, running a full cycle every hour.

- **Full Cycle:** The orchestrator runs the agents in sequence (Strategy → Creative → Quality → Monitor), followed by the Community Agent.
- **Pre-generation:** During off-peak hours, the Creative Agent pre-generates content into a "barrel" (queue) to ensure a steady supply of approved content.
- **Damage Control:** The Monitor Agent constantly checks for negative reactions. If a post is failing, it issues a kill signal, and the post is immediately deleted and replaced.

This multi-agent architecture transforms the CFW bot from a simple automation script into a self-improving, autonomous marketing team.

## References
[1] Braze. "Multi Armed Bandit Marketing Optimization." https://www.braze.com/resources/articles/multi-armed-bandit
[2] Amplitude. "What is a Multi-Armed Bandit? Full Explanation." https://amplitude.com/explore/experiment/multi-armed-bandit

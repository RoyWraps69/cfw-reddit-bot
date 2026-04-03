"""
Chicago Fleet Wraps — Multi-Agent System
=========================================
Five specialized AI agents that collaborate through a shared message bus:

  STRATEGY AGENT  (The CMO)      — Decides WHAT, WHERE, and WHEN to post
  CREATIVE AGENT  (The Artist)   — Generates images, videos, captions, hooks
  QUALITY AGENT   (The Editor)   — Reviews everything BEFORE it goes live
  MONITOR AGENT   (The Analyst)  — Watches engagement, attributes outcomes
  COMMUNITY AGENT (The Networker)— Responds to comments, builds relationships

Communication flow:
  Strategy → Creative → Quality → [publish] → Monitor → Strategy (loop)
  Community runs in parallel, responding to inbound engagement.
"""

from agents.base import BaseAgent, AgentMessage, MessageBus, AgentRegistry

__all__ = [
    "BaseAgent",
    "AgentMessage",
    "MessageBus",
    "AgentRegistry",
]

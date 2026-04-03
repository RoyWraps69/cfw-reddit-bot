"""
Chicago Fleet Wraps — Agent Base Infrastructure
=================================================
Provides:
  - AgentMessage:  Typed messages agents send to each other
  - MessageBus:    Central hub that routes messages between agents
  - BaseAgent:     Abstract base class every agent inherits from
  - AgentRegistry: Singleton that tracks all live agent instances
"""

import os
import json
import uuid
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# MESSAGE TYPES — What agents say to each other
# ═══════════════════════════════════════════════════════════════

class MessageType(str, Enum):
    """Every message between agents has a type so the receiver knows
    how to handle it without parsing free-text."""

    # Strategy → Creative
    CONTENT_REQUEST     = "content_request"      # "Make this content"
    TREND_ALERT         = "trend_alert"           # "This is trending, act now"

    # Creative → Quality
    CONTENT_DRAFT       = "content_draft"         # "Here's what I made, review it"

    # Quality → Creative  (rejection loop)
    REVISION_REQUEST    = "revision_request"      # "Fix this and try again"

    # Quality → Bus (approved for publishing)
    CONTENT_APPROVED    = "content_approved"       # "This is good, publish it"

    # Monitor → Strategy
    PERFORMANCE_REPORT  = "performance_report"    # "Here's how things are going"
    KILL_SIGNAL         = "kill_signal"            # "Delete this post NOW"
    LEARNING_UPDATE     = "learning_update"        # "I learned something new"

    # Monitor → Community
    RESPOND_REQUEST     = "respond_request"        # "Someone commented, reply"

    # Community → Monitor
    INTERACTION_REPORT  = "interaction_report"     # "I engaged with someone"

    # Any → Any
    STATUS_REQUEST      = "status_request"         # "What's your status?"
    STATUS_RESPONSE     = "status_response"        # "Here's my status"
    HEARTBEAT           = "heartbeat"              # "I'm alive"
    ERROR               = "error"                  # "Something went wrong"


# ═══════════════════════════════════════════════════════════════
# AGENT MESSAGE — The envelope agents pass around
# ═══════════════════════════════════════════════════════════════

class AgentMessage:
    """A structured message passed between agents via the MessageBus."""

    def __init__(
        self,
        msg_type: MessageType,
        sender: str,
        recipient: str,
        payload: dict,
        priority: int = 5,
        in_reply_to: str = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.type = msg_type
        self.sender = sender
        self.recipient = recipient
        self.payload = payload
        self.priority = priority          # 1 = urgent, 10 = low priority
        self.in_reply_to = in_reply_to    # ID of message this replies to
        self.timestamp = datetime.now().isoformat()
        self.delivered = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "priority": self.priority,
            "in_reply_to": self.in_reply_to,
            "timestamp": self.timestamp,
            "delivered": self.delivered,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        msg = cls(
            msg_type=data.get("type", "status_request"),
            sender=data.get("sender", "unknown"),
            recipient=data.get("recipient", "unknown"),
            payload=data.get("payload", {}),
            priority=data.get("priority", 5),
            in_reply_to=data.get("in_reply_to"),
        )
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        msg.delivered = data.get("delivered", False)
        return msg

    def __repr__(self):
        return (
            f"<Msg {self.id} [{self.type}] {self.sender}→{self.recipient} "
            f"p={self.priority}>"
        )


# ═══════════════════════════════════════════════════════════════
# MESSAGE BUS — Routes messages between agents
# ═══════════════════════════════════════════════════════════════

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_BUS_DIR = os.path.join(_DATA_DIR, "message_bus")
_BUS_LOG = os.path.join(_BUS_DIR, "bus_log.json")

log = logging.getLogger("message_bus")


class MessageBus:
    """Central message routing hub.

    Messages are persisted to disk so they survive process restarts
    (important for GitHub Actions where each run is a fresh process).
    Each agent has its own inbox file.
    """

    def __init__(self):
        os.makedirs(_BUS_DIR, exist_ok=True)

    # ── Sending ──────────────────────────────────────────────

    def send(self, message: AgentMessage):
        """Send a message to the recipient's inbox."""
        inbox = self._inbox_path(message.recipient)
        messages = self._load(inbox)
        messages.append(message.to_dict())
        self._save(inbox, messages)
        self._log_message(message, "sent")
        log.info(f"BUS: {message}")

    def broadcast(self, message: AgentMessage, exclude_sender: bool = True):
        """Send a message to ALL agents."""
        registry = AgentRegistry()
        for name in registry.list_agents():
            if exclude_sender and name == message.sender:
                continue
            msg_copy = AgentMessage(
                msg_type=message.type,
                sender=message.sender,
                recipient=name,
                payload=message.payload,
                priority=message.priority,
            )
            self.send(msg_copy)

    # ── Receiving ────────────────────────────────────────────

    def receive(self, agent_name: str, msg_type: str = None) -> list:
        """Pull all pending messages for an agent.

        Optionally filter by message type.
        Returns list of AgentMessage objects, sorted by priority (urgent first).
        """
        inbox = self._inbox_path(agent_name)
        raw = self._load(inbox)

        # Filter undelivered
        pending = [m for m in raw if not m.get("delivered")]

        if msg_type:
            pending = [m for m in pending if m.get("type") == msg_type]

        # Mark as delivered
        for m in raw:
            if not m.get("delivered"):
                if msg_type is None or m.get("type") == msg_type:
                    m["delivered"] = True

        self._save(inbox, raw)

        # Convert to AgentMessage objects, sorted by priority
        messages = [AgentMessage.from_dict(m) for m in pending]
        messages.sort(key=lambda m: m.priority)
        return messages

    def peek(self, agent_name: str) -> int:
        """Check how many unread messages an agent has (without consuming them)."""
        inbox = self._inbox_path(agent_name)
        raw = self._load(inbox)
        return sum(1 for m in raw if not m.get("delivered"))

    # ── Cleanup ──────────────────────────────────────────────

    def clear_inbox(self, agent_name: str):
        """Clear all messages for an agent."""
        inbox = self._inbox_path(agent_name)
        self._save(inbox, [])

    def purge_old(self, max_age_hours: int = 24):
        """Remove delivered messages older than max_age_hours."""
        cutoff = datetime.now()
        for fname in os.listdir(_BUS_DIR):
            if not fname.endswith("_inbox.json"):
                continue
            path = os.path.join(_BUS_DIR, fname)
            messages = self._load(path)
            kept = []
            for m in messages:
                try:
                    ts = datetime.fromisoformat(m.get("timestamp", ""))
                    age_h = (cutoff - ts).total_seconds() / 3600
                    if not m.get("delivered") or age_h < max_age_hours:
                        kept.append(m)
                except Exception:
                    kept.append(m)
            self._save(path, kept)

    # ── Internal ─────────────────────────────────────────────

    def _inbox_path(self, agent_name: str) -> str:
        return os.path.join(_BUS_DIR, f"{agent_name}_inbox.json")

    def _load(self, path: str) -> list:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self, path: str, data: list):
        # Keep inboxes from growing unbounded
        data = data[-200:]
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _log_message(self, message: AgentMessage, action: str):
        bus_log = self._load(_BUS_LOG)
        bus_log.append({
            "action": action,
            "message_id": message.id,
            "type": message.type.value if isinstance(message.type, MessageType) else message.type,
            "sender": message.sender,
            "recipient": message.recipient,
            "priority": message.priority,
            "timestamp": message.timestamp,
        })
        self._save(_BUS_LOG, bus_log[-500:])


# ═══════════════════════════════════════════════════════════════
# AGENT REGISTRY — Tracks all live agents
# ═══════════════════════════════════════════════════════════════

_REGISTRY_FILE = os.path.join(_BUS_DIR, "registry.json")


class AgentRegistry:
    """Singleton registry of all agents in the system.

    Persisted to disk so agents can discover each other across
    separate process invocations (GitHub Actions runs).
    """

    def register(self, name: str, role: str, status: str = "active"):
        reg = self._load()
        reg[name] = {
            "role": role,
            "status": status,
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
        }
        self._save(reg)

    def heartbeat(self, name: str):
        reg = self._load()
        if name in reg:
            reg[name]["last_heartbeat"] = datetime.now().isoformat()
            reg[name]["status"] = "active"
            self._save(reg)

    def list_agents(self) -> list:
        return list(self._load().keys())

    def get_agent(self, name: str) -> Optional[dict]:
        return self._load().get(name)

    def get_all(self) -> dict:
        return self._load()

    def _load(self) -> dict:
        os.makedirs(_BUS_DIR, exist_ok=True)
        if os.path.exists(_REGISTRY_FILE):
            try:
                with open(_REGISTRY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, data: dict):
        os.makedirs(_BUS_DIR, exist_ok=True)
        with open(_REGISTRY_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# BASE AGENT — Abstract class every agent inherits
# ═══════════════════════════════════════════════════════════════

class BaseAgent:
    """Abstract base class for all CFW agents.

    Every agent has:
      - A name and role
      - Access to the MessageBus
      - A run() method that processes its inbox and does its job
      - A think() method where the agent uses AI to reason about its task
    """

    NAME: str = "base"
    ROLE: str = "Base Agent"

    def __init__(self):
        self.bus = MessageBus()
        self.registry = AgentRegistry()
        self.logger = logging.getLogger(f"agent.{self.NAME}")

        # Register on creation
        self.registry.register(self.NAME, self.ROLE)

    def send(self, recipient: str, msg_type: MessageType, payload: dict,
             priority: int = 5, in_reply_to: str = None):
        """Send a message to another agent."""
        msg = AgentMessage(
            msg_type=msg_type,
            sender=self.NAME,
            recipient=recipient,
            payload=payload,
            priority=priority,
            in_reply_to=in_reply_to,
        )
        self.bus.send(msg)

    def receive(self, msg_type: str = None) -> list:
        """Pull pending messages from this agent's inbox."""
        return self.bus.receive(self.NAME, msg_type)

    def broadcast(self, msg_type: MessageType, payload: dict, priority: int = 5):
        """Broadcast a message to all other agents."""
        msg = AgentMessage(
            msg_type=msg_type,
            sender=self.NAME,
            recipient="all",
            payload=payload,
            priority=priority,
        )
        self.bus.broadcast(msg)

    def heartbeat(self):
        """Signal that this agent is alive."""
        self.registry.heartbeat(self.NAME)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] [{self.NAME.upper()}] {msg}", flush=True)
        self.logger.info(msg)

    # ── Abstract methods (override in subclasses) ────────────

    def run(self) -> dict:
        """Execute this agent's main cycle.

        Returns a dict summarizing what happened.
        Must be implemented by every subclass.
        """
        raise NotImplementedError(f"{self.NAME} must implement run()")

    def think(self, context: str) -> str:
        """Use AI to reason about a decision.

        Override in subclasses for agent-specific reasoning.
        Default implementation calls the OpenAI API.
        """
        try:
            from openai import OpenAI
            from config import OPENAI_MODEL

            base_url = os.environ.get("OPENAI_BASE_URL", None)
            client = OpenAI(base_url=base_url) if base_url else OpenAI()

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": context},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.log(f"Think error: {e}")
            return ""

    def _system_prompt(self) -> str:
        """System prompt for this agent's AI reasoning.

        Override in subclasses for specialized behavior.
        """
        return (
            f"You are the {self.ROLE} for Chicago Fleet Wraps, a vehicle wrap "
            f"shop in Chicago. Your job is to help maximize social media engagement. "
            f"Be concise, data-driven, and actionable."
        )

    def status(self) -> dict:
        """Return this agent's current status."""
        return {
            "name": self.NAME,
            "role": self.ROLE,
            "pending_messages": self.bus.peek(self.NAME),
        }

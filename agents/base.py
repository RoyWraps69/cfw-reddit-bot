"""
Chicago Fleet Wraps — Agent Base Infrastructure v2.0

MessageBus: Inter-agent communication layer
AgentRegistry: Agent registration and heartbeat tracking
BaseAgent: Abstract class all agents inherit from

Message types:
  CONTENT_REQUEST     — Strategy → Creative
  CONTENT_DRAFT       — Creative → Quality
  REVISION_REQUEST    — Quality → Creative
  CONTENT_APPROVED    — Quality → Monitor
  CONTENT_REJECTED    — Quality → Creative (with feedback)
  PERFORMANCE_REPORT  — Monitor → Strategy
  LEARNING_UPDATE     — Monitor → Strategy
  RESPOND_REQUEST     — Monitor → Community
  COMPETITOR_ALERT    — Any → All
  HOT_LEAD_DETECTED   — Community → LeadAlert
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUS_FILE = os.path.join(DATA_DIR, "message_bus.json")
REGISTRY_FILE = os.path.join(DATA_DIR, "agent_registry.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────
# MESSAGE BUS
# ─────────────────────────────────────────────────────────────────────

class MessageBus:
    """File-based message bus for inter-agent communication."""

    def send(self, to: str, message_type: str, payload: dict,
             from_agent: str = "system", priority: int = 5) -> str:
        """Send a message to an agent's inbox."""
        messages = self._load()

        msg_id = str(uuid.uuid4())[:8].upper()
        message = {
            "id": msg_id,
            "to": to,
            "from": from_agent,
            "type": message_type,
            "payload": payload,
            "priority": priority,
            "status": "pending",
            "sent_at": str(datetime.now()),
            "delivered_at": None,
        }

        messages.append(message)
        self._save(messages)
        return msg_id

    def receive(self, agent_name: str, limit: int = 10) -> list:
        """Get pending messages for an agent, sorted by priority."""
        messages = self._load()
        inbox = [m for m in messages if m["to"] == agent_name and m["status"] == "pending"]
        inbox.sort(key=lambda x: x.get("priority", 5), reverse=True)

        # Mark as delivered
        inbox_ids = {m["id"] for m in inbox[:limit]}
        for m in messages:
            if m["id"] in inbox_ids:
                m["status"] = "delivered"
                m["delivered_at"] = str(datetime.now())

        self._save(messages)
        return inbox[:limit]

    def peek(self, agent_name: str) -> int:
        """Count pending messages for an agent without consuming them."""
        messages = self._load()
        return sum(1 for m in messages if m["to"] == agent_name and m["status"] == "pending")

    def broadcast(self, message_type: str, payload: dict, from_agent: str = "system",
                  exclude: list = None):
        """Send a message to all registered agents."""
        registry = AgentRegistry()
        agents = registry.get_all()
        exclude = exclude or []

        for agent_name in agents:
            if agent_name not in exclude:
                self.send(to=agent_name, message_type=message_type,
                          payload=payload, from_agent=from_agent)

    def purge_old(self, max_age_hours: int = 48):
        """Remove old delivered messages."""
        messages = self._load()
        cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        messages = [m for m in messages
                    if m.get("status") == "pending" or m.get("sent_at", "") > cutoff]
        self._save(messages)

    def _load(self) -> list:
        if os.path.exists(BUS_FILE):
            try:
                with open(BUS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self, messages: list):
        # Keep only last 1000 messages
        messages = messages[-1000:]
        with open(BUS_FILE, "w") as f:
            json.dump(messages, f, indent=2)


# ─────────────────────────────────────────────────────────────────────
# AGENT REGISTRY
# ─────────────────────────────────────────────────────────────────────

class AgentRegistry:
    """Tracks registered agents and their status."""

    def register(self, name: str, role: str, capabilities: list = None):
        """Register an agent."""
        registry = self._load()
        registry[name] = {
            "name": name,
            "role": role,
            "capabilities": capabilities or [],
            "status": "active",
            "registered_at": str(datetime.now()),
            "last_heartbeat": str(datetime.now()),
            "cycles_completed": 0,
        }
        self._save(registry)

    def heartbeat(self, name: str, status: str = "active", last_action: str = ""):
        """Update an agent's heartbeat."""
        registry = self._load()
        if name in registry:
            registry[name]["last_heartbeat"] = str(datetime.now())
            registry[name]["status"] = status
            if last_action:
                registry[name]["last_action"] = last_action
            registry[name]["cycles_completed"] = registry[name].get("cycles_completed", 0) + 1
        self._save(registry)

    def get_all(self) -> dict:
        return self._load()

    def get(self, name: str) -> dict:
        return self._load().get(name, {})

    def _load(self) -> dict:
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, registry: dict):
        with open(REGISTRY_FILE, "w") as f:
            json.dump(registry, f, indent=2)


# ─────────────────────────────────────────────────────────────────────
# BASE AGENT
# ─────────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """Abstract base class all agents inherit from."""

    def __init__(self, name: str, role: str, capabilities: list = None):
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.bus = MessageBus()
        self.registry = AgentRegistry()
        self.registry.register(name, role, capabilities)
        self.log_prefix = f"[{name.upper()}]"

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {self.log_prefix} {msg}", flush=True)

    def get_messages(self, limit: int = 10) -> list:
        """Get messages from the bus."""
        return self.bus.receive(self.name, limit=limit)

    def send(self, to: str, message_type: str, payload: dict, priority: int = 5) -> str:
        """Send a message to another agent."""
        return self.bus.send(to=to, message_type=message_type,
                              payload=payload, from_agent=self.name, priority=priority)

    def heartbeat(self, status: str = "active", action: str = ""):
        """Update registry with current status."""
        self.registry.heartbeat(self.name, status=status, last_action=action)

    @abstractmethod
    def run(self) -> dict:
        """Execute the agent's main cycle. Must be implemented by subclasses."""
        pass

    def _save_state(self, state: dict):
        """Save agent-specific state to disk."""
        state_file = os.path.join(DATA_DIR, f"agent_{self.name}_state.json")
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> dict:
        """Load agent-specific state from disk."""
        state_file = os.path.join(DATA_DIR, f"agent_{self.name}_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

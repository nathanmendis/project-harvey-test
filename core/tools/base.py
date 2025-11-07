# core/actions/base.py
from dataclasses import dataclass

@dataclass
class ActionResult:
    """Represents the result of a chatbot backend action."""
    ok: bool
    message: str




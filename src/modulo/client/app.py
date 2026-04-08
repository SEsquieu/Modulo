from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_connected: bool = False
    hosting_enabled: bool = False


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Connect OpenClaw",
        "Enable hosting to earn",
    ]


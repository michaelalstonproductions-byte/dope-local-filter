#!/usr/bin/env python3
"""User-facing explanations for DOPE v0.5 decisions."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def _profile_name(profile: Mapping[str, Any] | None) -> str:
    if not isinstance(profile, Mapping):
        return "default"
    return str(profile.get("profile_name") or "default")


def _goals(profile: Mapping[str, Any] | None) -> str:
    if not isinstance(profile, Mapping):
        return "learning, calm, and useful action"
    raw = profile.get("primary_goals")
    if not isinstance(raw, list) or not raw:
        return "learning, calm, and useful action"
    goals = [str(item).replace("_", " ") for item in raw[:3]]
    return ", ".join(goals)


def explain_decision(content: Mapping[str, Any] | None, decision: Mapping[str, Any], profile: Mapping[str, Any] | None) -> str:
    category = str(decision.get("category", "NEUTRAL"))
    action = str(decision.get("action", "ALLOW"))
    reason = str(decision.get("reason", "local heuristic signal"))
    labels = {str(label) for label in decision.get("labels", []) if str(label)}
    profile_name = _profile_name(profile)
    goals = _goals(profile)

    if "CONSTRUCTIVE_NEWS" in labels or "HARD_NEWS" in labels or "CIVIC_AWARENESS" in labels:
        return (
            f"Profile '{profile_name}' kept this available because it looks like useful news or civic information, "
            f"not an outrage loop. Action: {action}. Reason: {reason}."
        )
    if category == "UPLIFT":
        return f"Profile '{profile_name}' allowed this because it supports {goals}. Reason: {reason}."
    if action == "ALLOW":
        return f"Profile '{profile_name}' allowed this because no strong harmful attention pattern was detected."
    return (
        f"This was {action.lower()} because it matches {category.lower()} framing. "
        f"Your profile prioritizes {goals}, so DOPE suggested a constructive alternative."
    )


def explain_replacement(decision: Mapping[str, Any], profile: Mapping[str, Any] | None) -> str:
    replacement = str(decision.get("positive_replacement", "") or "")
    if not replacement:
        return "No replacement was needed."
    return f"The replacement is meant to support {_goals(profile)} without shaming or forcing positivity."


def explain_session_summary(memory: Mapping[str, Any], profile: Mapping[str, Any] | None) -> str:
    seen = int(memory.get("items_seen", 0)) if isinstance(memory, Mapping) else 0
    risk = str(memory.get("dominant_risk", "") or "none") if isinstance(memory, Mapping) else "none"
    return f"This local session reviewed {seen} item(s). Dominant risk: {risk}. Profile focus: {_goals(profile)}."


__all__ = ["explain_decision", "explain_replacement", "explain_session_summary"]

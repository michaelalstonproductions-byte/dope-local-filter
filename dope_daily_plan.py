#!/usr/bin/env python3
"""Simple local daily plan builder for DOPE v0.5."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from dope_recommender import DOPE_VERSION


def _profile_name(profile: Mapping[str, Any] | None) -> str:
    return str(profile.get("profile_name", "default")) if isinstance(profile, Mapping) else "default"


def _entries(content_library: Mapping[str, Any], target: str, count: int = 1) -> List[Dict[str, Any]]:
    raw = content_library.get(target) if isinstance(content_library, Mapping) else []
    if not isinstance(raw, list):
        return []
    rows: List[Dict[str, Any]] = []
    for entry in raw[:count]:
        if isinstance(entry, Mapping):
            rows.append(
                {
                    "target": target,
                    "title": str(entry.get("title", target.replace("_", " ").title())),
                    "prompt": str(entry.get("prompt", "Choose one constructive action.")),
                    "why": str(entry.get("why", "This supports healthy attention.")),
                    "time_cost": str(entry.get("time_cost", "5_min")),
                    "mode": str(entry.get("mode", "reflect")),
                    "source": "local_content_library",
                }
            )
    return rows


def build_emergency_reset(profile: Mapping[str, Any], content_library: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return _entries(content_library, "emergency_reset", count=3)


def build_daily_plan(
    profile: Mapping[str, Any],
    content_library: Mapping[str, Any],
    session_memory: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    morning = _entries(content_library, "gratitude", 1) + _entries(content_library, "discipline", 1)
    midday = _entries(content_library, "working", 1) + _entries(content_library, "fitness", 1)
    evening = _entries(content_library, "family", 1) + _entries(content_library, "positive_history", 1)
    counts = session_memory.get("category_counts", {}) if isinstance(session_memory, Mapping) else {}
    doom = int(counts.get("DOOMSCROLL", 0)) if isinstance(counts, Mapping) and str(counts.get("DOOMSCROLL", 0)).isdigit() else 0
    rage = int(counts.get("RAGEBAIT", 0)) if isinstance(counts, Mapping) and str(counts.get("RAGEBAIT", 0)).isdigit() else 0
    shame = int(counts.get("SHAME", 0)) if isinstance(counts, Mapping) and str(counts.get("SHAME", 0)).isdigit() else 0
    emergency_reset = build_emergency_reset(profile, content_library)
    plan = {
        "dope_version": DOPE_VERSION,
        "profile_used": _profile_name(profile),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_first": True,
        "morning": morning[:3],
        "midday": midday[:3],
        "evening": evening[:3],
        "emergency_reset": emergency_reset,
        "recommended_limits": {
            "doomscroll_replacements": min(5, max(1, doom or 5)),
            "ragebait_replacements": min(5, max(1, rage or 5)),
            "shame_replacements": min(5, max(1, shame or 5)),
        },
    }
    if not emergency_reset:
        plan["warnings"] = ["missing_local_content_library_emergency_reset"]
    return plan


def save_daily_plan(plan: Dict[str, Any], path: str | pathlib.Path) -> None:
    plan_path = pathlib.Path(path)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with plan_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, sort_keys=True)
        f.write("\n")


__all__ = ["build_daily_plan", "build_emergency_reset", "save_daily_plan"]

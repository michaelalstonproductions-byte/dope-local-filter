#!/usr/bin/env python3
"""Local-only session memory for DOPE v0.4."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict


DOPE_VERSION = "0.4"
HARMFUL_CATEGORIES = {"TOXIC", "RAGEBAIT", "DOOMSCROLL", "SHAME", "VIOLENCE", "SEXUALIZED", "SCAM"}


def _new_memory() -> Dict[str, Any]:
    return {
        "dope_version": DOPE_VERSION,
        "session_started_at": datetime.now(timezone.utc).isoformat(),
        "items_seen": 0,
        "category_counts": {},
        "action_counts": {},
        "replacement_counts": {},
        "dominant_risk": "",
        "positive_targets_served": {},
        "last_replacements": [],
        "local_first": True,
    }


def load_session_memory(path: str | pathlib.Path) -> Dict[str, Any]:
    memory_path = pathlib.Path(path)
    try:
        with memory_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _new_memory()
    if not isinstance(payload, dict):
        return _new_memory()
    memory = _new_memory()
    memory.update(payload)
    memory["dope_version"] = DOPE_VERSION
    memory["local_first"] = True
    for key in ("category_counts", "action_counts", "replacement_counts", "positive_targets_served"):
        if not isinstance(memory.get(key), dict):
            memory[key] = {}
        else:
            memory[key] = _sanitize_counter(memory[key])
    if not isinstance(memory.get("last_replacements"), list):
        memory["last_replacements"] = []
    memory["items_seen"] = _safe_int(memory.get("items_seen"), 0)
    return memory


def save_session_memory(memory: Dict[str, Any], path: str | pathlib.Path) -> None:
    memory_path = pathlib.Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with memory_path.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, sort_keys=True)
        f.write("\n")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _sanitize_counter(counter: Dict[str, Any]) -> Dict[str, int]:
    return {str(key): _safe_int(value, 0) for key, value in counter.items() if str(key)}


def _increment(counter: Dict[str, Any], key: str) -> None:
    if not key:
        return
    counter[key] = _safe_int(counter.get(key), 0) + 1


def _dominant_risk(category_counts: Dict[str, Any]) -> str:
    candidates = {k: _safe_int(v, 0) for k, v in category_counts.items() if k in HARMFUL_CATEGORIES}
    if not candidates:
        return ""
    return max(sorted(candidates), key=lambda key: candidates[key])


def update_session_memory(memory: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    updated = _new_memory()
    updated.update(memory if isinstance(memory, dict) else {})
    decision = result.get("decision") if isinstance(result, dict) else {}
    decision = decision if isinstance(decision, dict) else {}
    category = str(decision.get("category", "NEUTRAL"))
    action = str(decision.get("action", "ALLOW"))
    source = str(result.get("replacement_source", "") or "")
    replacement = str(decision.get("positive_replacement", "") or "")

    for key in ("category_counts", "action_counts", "replacement_counts", "positive_targets_served"):
        if not isinstance(updated.get(key), dict):
            updated[key] = {}
        updated[key] = _sanitize_counter(updated[key])

    updated["items_seen"] = _safe_int(updated.get("items_seen"), 0) + 1
    _increment(updated["category_counts"], category)
    _increment(updated["action_counts"], action)
    if source:
        _increment(updated["replacement_counts"], source)
        _increment(updated["positive_targets_served"], source)
    if replacement:
        last = list(updated.get("last_replacements", []))
        last.append(replacement)
        updated["last_replacements"] = last[-10:]
    updated["dominant_risk"] = _dominant_risk(updated["category_counts"])
    updated["dope_version"] = DOPE_VERSION
    updated["local_first"] = True
    return updated


def summarize_session(memory: Dict[str, Any]) -> Dict[str, Any]:
    category_counts = memory.get("category_counts") if isinstance(memory, dict) else {}
    action_counts = memory.get("action_counts") if isinstance(memory, dict) else {}
    category_counts = category_counts if isinstance(category_counts, dict) else {}
    action_counts = action_counts if isinstance(action_counts, dict) else {}
    category_counts = _sanitize_counter(category_counts)
    action_counts = _sanitize_counter(action_counts)
    top_category = max(sorted(category_counts), key=lambda key: category_counts[key]) if category_counts else ""
    top_action = max(sorted(action_counts), key=lambda key: action_counts[key]) if action_counts else ""
    return {
        "dope_version": DOPE_VERSION,
        "items_seen": _safe_int(memory.get("items_seen"), 0) if isinstance(memory, dict) else 0,
        "dominant_risk": str(memory.get("dominant_risk", "")) if isinstance(memory, dict) else "",
        "top_category": top_category,
        "top_action": top_action,
        "positive_targets_served": dict(memory.get("positive_targets_served", {})) if isinstance(memory, dict) else {},
        "local_first": True,
    }


__all__ = ["load_session_memory", "save_session_memory", "summarize_session", "update_session_memory"]

#!/usr/bin/env python3
"""
DOPE v0.5 - Positive replacement engine.

This module intentionally does not rank by engagement. Replacements are chosen
from healthy domains and lightly rotated by category to avoid a single loop.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict, List

from dope_classifier import normalize_controls


HEALTHY_REPLACEMENTS = {
    "learning": [
        "Read one page of a useful book or save a lesson for later.",
        "Spend five minutes learning one concrete skill step.",
    ],
    "creating": [
        "Open a draft and make one small creative improvement.",
        "Capture one idea, sketch, hook, or outline you can build on.",
    ],
    "working": [
        "Pick the next visible task and work on it for ten focused minutes.",
        "Close one loop: send the message, file the note, or finish the small task.",
    ],
    "fitness": [
        "Take a short walk, stretch, or do one low-friction movement set.",
        "Drink water and move for three minutes before returning to media.",
    ],
    "calm": [
        "Take six slow breaths and let the nervous system settle.",
        "Look away from the screen and relax your shoulders for one minute.",
    ],
    "family": [
        "Send a kind check-in to someone close to you.",
        "Make a small plan that improves home or family life today.",
    ],
    "spirituality": [
        "Pause for prayer, gratitude, or a short grounding reflection.",
        "Read or recall one line that points you toward patience and hope.",
    ],
    "business_progress": [
        "Do one action that moves a real offer, client, invoice, or launch forward.",
        "Write the next business decision in one clear sentence.",
    ],
    "emotional_regulation": [
        "Name the feeling, lower the intensity, and choose the next useful action.",
        "Journal one sentence: what happened, what I feel, what I will do next.",
    ],
    "positive_history": [
        "Read one short story of resilience and write one lesson you can use today.",
        "Look up one builder, inventor, or reformer and note the habit that made them durable.",
    ],
    "constructive_news": [
        "Read one constructive update, then write the one practical action it suggests.",
        "Switch from crisis scanning to one verified resource with a clear next step.",
    ],
    "civic_awareness": [
        "Save one factual civic update and identify the practical local action, if any.",
        "Check the source, separate facts from framing, and move on after the useful part.",
    ],
    "gratitude": [
        "Name three concrete things that are still working today.",
        "Send one specific thank-you or appreciation message.",
    ],
    "discipline": [
        "Choose the next right action and do it for ten focused minutes.",
        "Make the smallest disciplined move available right now.",
    ],
}

CATEGORY_DOMAIN_MAP = {
    "RAGEBAIT": ["calm", "emotional_regulation", "learning"],
    "DOOMSCROLL": ["constructive_news", "calm", "civic_awareness"],
    "SHAME": ["emotional_regulation", "fitness", "family"],
    "TOXIC": ["calm", "working", "creating"],
    "VIOLENCE": ["calm", "family", "spirituality"],
    "SEXUALIZED": ["fitness", "working", "spirituality"],
    "SCAM": ["business_progress", "learning", "working"],
    "NEUTRAL": ["learning", "creating", "working"],
    "UPLIFT": ["creating", "working", "family"],
}

PROJECT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_CONTENT_LIBRARY_PATH = PROJECT_DIR / "dope_content_library.json"


def _allowed_domains(user_controls: Dict[str, Any] | None) -> List[str]:
    controls = normalize_controls(user_controls)
    domains = list(HEALTHY_REPLACEMENTS.keys())
    if not controls.get("allow_spirituality", True):
        domains.remove("spirituality")
    if not controls.get("allow_business", True):
        domains.remove("business_progress")
    targets = controls.get("positive_reinforcement_targets")
    if isinstance(targets, list) and targets:
        target_set = {str(target) for target in targets}
        domains = [domain for domain in domains if domain in target_set]
    if not controls.get("allow_fitness", True):
        if "fitness" in domains:
            domains.remove("fitness")
    return domains


def positive_replacement(category: str, text: str = "", user_controls: Dict[str, Any] | None = None) -> str:
    allowed = set(_allowed_domains(user_controls))
    preferred = [d for d in CATEGORY_DOMAIN_MAP.get(category, ["learning"]) if d in allowed]
    domains = preferred or sorted(allowed) or ["learning"]
    key = f"{category}:{text}".encode("utf-8", errors="replace")
    digest = hashlib.sha256(key).hexdigest()
    domain = domains[int(digest[:4], 16) % len(domains)]
    choices = HEALTHY_REPLACEMENTS[domain]
    return choices[int(digest[4:8], 16) % len(choices)]


def load_content_library(path: str | pathlib.Path | None = None) -> Dict[str, Any]:
    library_path = pathlib.Path(path) if path else DEFAULT_CONTENT_LIBRARY_PATH
    try:
        with library_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def replacement_source_for_decision(decision: Dict[str, Any]) -> str:
    labels = {str(label) for label in decision.get("labels", [])}
    category = str(decision.get("category", "NEUTRAL"))
    if "POSITIVE_HISTORY" in labels:
        return "positive_history"
    if "CONSTRUCTIVE_NEWS" in labels:
        return "constructive_news"
    if "CIVIC_AWARENESS" in labels or "HARD_NEWS" in labels:
        return "civic_awareness"
    if category == "DOOMSCROLL":
        return "constructive_news"
    if category in {"RAGEBAIT", "TOXIC", "VIOLENCE"}:
        return "calm"
    if category == "SHAME":
        return "emotional_regulation"
    if category == "SCAM":
        return "business_progress"
    if category == "SEXUALIZED":
        return "discipline"
    if category == "UPLIFT":
        return "gratitude"
    return ""


def library_replacement(source: str, text: str = "", path: str | pathlib.Path | None = None) -> str:
    if not source:
        return ""
    library = load_content_library(path)
    entries = library.get(source)
    if not isinstance(entries, list) or not entries:
        return ""
    key = f"{source}:{text}".encode("utf-8", errors="replace")
    digest = hashlib.sha256(key).hexdigest()
    entry = entries[int(digest[:4], 16) % len(entries)]
    if isinstance(entry, dict):
        title = str(entry.get("title", "")).strip()
        prompt = str(entry.get("prompt", "")).strip()
        if title and prompt:
            return f"{title}: {prompt}"
        return title or prompt
    return str(entry)


def attach_replacement(decision: Dict[str, Any], content: Dict[str, Any], user_controls: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result = dict(decision)
    source = replacement_source_for_decision(result)
    if result.get("action") in {"SOFT_WARN", "BLUR", "BLOCK", "REPLACE"}:
        text = str(content.get("text", ""))
        result["positive_replacement"] = library_replacement(source, text) or positive_replacement(
            str(result.get("category", "NEUTRAL")), text, user_controls
        )
    else:
        result["positive_replacement"] = ""
    return result


__all__ = ["attach_replacement", "library_replacement", "positive_replacement", "replacement_source_for_decision"]

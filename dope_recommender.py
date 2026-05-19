#!/usr/bin/env python3
"""Local positive content recommendation engine for DOPE v0.5."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping


DOPE_VERSION = "0.5"
RECOMMENDABLE_TARGETS = {
    "learning",
    "creating",
    "working",
    "fitness",
    "calm",
    "family",
    "spirituality",
    "business_progress",
    "emotional_regulation",
    "positive_history",
    "constructive_news",
    "civic_awareness",
    "gratitude",
    "discipline",
}

CATEGORY_TARGETS = {
    "DOOMSCROLL": ["calm", "constructive_news", "civic_awareness", "discipline"],
    "RAGEBAIT": ["emotional_regulation", "learning", "civic_awareness", "calm"],
    "SHAME": ["calm", "fitness", "gratitude", "discipline"],
    "SCAM": ["business_progress", "discipline", "learning"],
    "VIOLENCE": ["calm", "family", "spirituality"],
    "SEXUALIZED": ["discipline", "fitness", "working"],
    "TOXIC": ["calm", "emotional_regulation", "creating"],
    "UPLIFT": ["gratitude", "creating", "positive_history"],
    "NEUTRAL": ["learning", "working", "constructive_news"],
}

PROFILE_GOAL_TARGETS = {
    "learn": "learning",
    "learning": "learning",
    "create": "creating",
    "creating": "creating",
    "work": "working",
    "working": "working",
    "fitness": "fitness",
    "calm": "calm",
    "family": "family",
    "spirituality": "spirituality",
    "business_progress": "business_progress",
    "emotional_regulation": "emotional_regulation",
}

TIME_COSTS = {"under_2_min", "5_min", "15_min", "30_min"}
MODES = {"read", "watch", "create", "move", "reflect", "connect", "work"}


def _profile_name(profile: Mapping[str, Any] | None) -> str:
    return str(profile.get("profile_name", "default")) if isinstance(profile, Mapping) else "default"


def _profile_targets(profile: Mapping[str, Any] | None) -> List[str]:
    if not isinstance(profile, Mapping):
        return ["learning", "calm", "discipline"]
    raw = profile.get("primary_goals")
    if not isinstance(raw, list):
        return ["learning", "calm", "discipline"]
    targets = []
    for goal in raw:
        target = PROFILE_GOAL_TARGETS.get(str(goal))
        if target and target not in targets:
            targets.append(target)
    return targets or ["learning", "calm", "discipline"]


def _category_counts(results: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in results:
        decision = row.get("decision") if isinstance(row, Mapping) else {}
        decision = decision if isinstance(decision, Mapping) else {}
        category = str(decision.get("category", "NEUTRAL"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def _blocked_or_replaced_count(results: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    for row in results:
        decision = row.get("decision") if isinstance(row, Mapping) else {}
        action = str(decision.get("action", "ALLOW")) if isinstance(decision, Mapping) else "ALLOW"
        if action != "ALLOW":
            count += 1
    return count


def _memory_counts(session_memory: Mapping[str, Any] | None) -> Dict[str, int]:
    if not isinstance(session_memory, Mapping):
        return {}
    raw = session_memory.get("category_counts")
    if not isinstance(raw, Mapping):
        return {}
    counts: Dict[str, int] = {}
    for key, value in raw.items():
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 0
        counts[str(key)] = max(0, parsed)
    return counts


def _dominant_risk(counts: Mapping[str, int]) -> str:
    risk_order = ["SCAM", "VIOLENCE", "SEXUALIZED", "SHAME", "RAGEBAIT", "DOOMSCROLL", "TOXIC"]
    active = [category for category in risk_order if counts.get(category, 0) > 0]
    if not active:
        return ""
    return max(active, key=lambda category: (counts.get(category, 0), -risk_order.index(category)))


def _entry_to_candidate(target: str, entry: Any, recommended_after: List[str], index: int = 0) -> Dict[str, Any]:
    if isinstance(entry, Mapping):
        title = str(entry.get("title", target.replace("_", " ").title()))
        prompt = str(entry.get("prompt", "Choose one constructive local action."))
        why = str(entry.get("why", "This supports a healthier attention loop."))
        time_cost = str(entry.get("time_cost", "5_min"))
        mode = str(entry.get("mode", "reflect"))
    else:
        title = target.replace("_", " ").title()
        prompt = str(entry)
        why = "This supports a healthier attention loop."
        time_cost = "5_min"
        mode = "reflect"
    return {
        "rank": 0,
        "target": target,
        "title": title,
        "prompt": prompt,
        "why": why,
        "recommended_after": recommended_after,
        "time_cost": time_cost if time_cost in TIME_COSTS else "5_min",
        "mode": mode if mode in MODES else "reflect",
        "source": "local_content_library",
        "_library_index": index,
    }


def recommendation_for_category(category: str, profile: Mapping[str, Any], content_library: Mapping[str, Any]) -> List[Dict[str, Any]]:
    targets = CATEGORY_TARGETS.get(str(category), ["learning", "calm", "discipline"])
    candidates: List[Dict[str, Any]] = []
    for target in targets:
        entries = content_library.get(target) if isinstance(content_library, Mapping) else []
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries[:2]):
            candidates.append(_entry_to_candidate(target, entry, [str(category)], index=index))
    return candidates


def _candidate_pool(results: List[Mapping[str, Any]], profile: Mapping[str, Any], content_library: Mapping[str, Any], session_memory: Mapping[str, Any] | None) -> List[Dict[str, Any]]:
    result_counts = _category_counts(results)
    memory_counts = _memory_counts(session_memory)
    combined = dict(result_counts)
    for category, count in memory_counts.items():
        combined[category] = combined.get(category, 0) + count

    ordered_categories = sorted(combined, key=lambda category: (-combined[category], category))
    candidates: List[Dict[str, Any]] = []
    for category in ordered_categories:
        candidates.extend(recommendation_for_category(category, profile, content_library))

    for target in _profile_targets(profile):
        entries = content_library.get(target) if isinstance(content_library, Mapping) else []
        if isinstance(entries, list):
            for index, entry in enumerate(entries[:1]):
                candidates.append(_entry_to_candidate(target, entry, ["PROFILE_GOAL"], index=index))

    for target in ("positive_history", "constructive_news", "gratitude", "discipline"):
        entries = content_library.get(target) if isinstance(content_library, Mapping) else []
        if isinstance(entries, list):
            for index, entry in enumerate(entries[:1]):
                candidates.append(_entry_to_candidate(target, entry, ["HEALTHY_BASELINE"], index=index))
    return candidates


def rank_recommendations(candidates: List[Dict[str, Any]], profile: Mapping[str, Any], session_memory: Mapping[str, Any] | None = None) -> List[Dict[str, Any]]:
    memory_counts = _memory_counts(session_memory)
    dominant = _dominant_risk(memory_counts)
    preferred_targets = set(_profile_targets(profile))
    risk_targets = set(CATEGORY_TARGETS.get(dominant, []))
    risk_weight = {"SCAM": 70, "VIOLENCE": 60, "SEXUALIZED": 55, "SHAME": 50, "RAGEBAIT": 45, "DOOMSCROLL": 45, "TOXIC": 35}

    def score(candidate: Mapping[str, Any]) -> tuple[int, int, str, int]:
        target = str(candidate.get("target", ""))
        base = 0
        recommended_after = [str(item) for item in candidate.get("recommended_after", [])]
        base += max((risk_weight.get(category, 0) for category in recommended_after), default=0)
        for category in recommended_after:
            ordered_targets = CATEGORY_TARGETS.get(category, [])
            if target in ordered_targets:
                base += max(0, 12 - ordered_targets.index(target))
        if target in risk_targets:
            base += 40
        if target in preferred_targets:
            base += 20
        if "HEALTHY_BASELINE" in recommended_after:
            base += 5
        if str(candidate.get("time_cost")) in {"under_2_min", "5_min"}:
            base += 3
        source_ok = 1 if candidate.get("source") == "local_content_library" else 0
        return (base, source_ok, target, -int(candidate.get("_library_index", 0)))

    seen = set()
    unique: List[Dict[str, Any]] = []
    for candidate in sorted(candidates, key=score, reverse=True):
        key = (candidate.get("target"), candidate.get("title"), candidate.get("prompt"))
        if key in seen:
            continue
        seen.add(key)
        clean = {k: v for k, v in candidate.items() if not k.startswith("_")}
        unique.append(clean)
    for index, candidate in enumerate(unique, start=1):
        candidate["rank"] = index
    return unique


def summarize_avoidance(results: List[Mapping[str, Any]], session_memory: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    result_counts = _category_counts(results)
    memory_counts = _memory_counts(session_memory)
    combined = dict(result_counts)
    for category, count in memory_counts.items():
        combined[category] = combined.get(category, 0) + count
    dominant = _dominant_risk(combined)
    blocked_count = _blocked_or_replaced_count(results)
    if dominant:
        reason = f"Local decisions show repeated {dominant.lower()} signals; recommendations emphasize healthier substitutes."
    else:
        reason = "No dominant harmful loop detected; recommendations emphasize profile goals and constructive variety."
    return {
        "dominant_risk": dominant,
        "blocked_or_replaced_count": blocked_count,
        "reason": reason,
    }


def build_recommendations(
    results: List[Mapping[str, Any]],
    profile: Mapping[str, Any],
    content_library: Mapping[str, Any],
    session_memory: Mapping[str, Any] | None = None,
    limit: int = 10,
) -> Dict[str, Any]:
    candidates = _candidate_pool(results, profile, content_library, session_memory)
    ranked = rank_recommendations(candidates, profile, session_memory=session_memory)[: max(1, int(limit))]
    return {
        "dope_version": DOPE_VERSION,
        "profile_used": _profile_name(profile),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_first": True,
        "recommendations": ranked,
        "avoidance_summary": summarize_avoidance(results, session_memory=session_memory),
    }


__all__ = [
    "build_recommendations",
    "rank_recommendations",
    "recommendation_for_category",
    "summarize_avoidance",
]

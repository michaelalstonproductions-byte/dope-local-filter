#!/usr/bin/env python3
"""
DOPE v0.5 - Local-first positive reinforcement classifier.

DOPE = Dopamine-Oriented Positive Environment.

This module is intentionally transparent and standard-library only.
It does not call networks, APIs, telemetry systems, or ranking services.

classify_content() returns raw classifier output. DopePolicyEngine.decide_content()
enriches replacement text and writes audit records.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping, Tuple


DOPE_VERSION = "0.5"

CATEGORIES = {
    "UPLIFT",
    "NEUTRAL",
    "TOXIC",
    "RAGEBAIT",
    "DOOMSCROLL",
    "SHAME",
    "VIOLENCE",
    "SEXUALIZED",
    "SCAM",
}

SECONDARY_LABELS = {
    "CONSTRUCTIVE_NEWS",
    "HARD_NEWS",
    "POSITIVE_HISTORY",
    "CIVIC_AWARENESS",
}

ALL_LABELS = CATEGORIES | SECONDARY_LABELS

ACTIONS = {
    "ALLOW",
    "SOFT_WARN",
    "BLUR",
    "BLOCK",
    "REPLACE",
}

DEFAULT_CONTROLS: Dict[str, Any] = {
    "strictness": "medium",
    "allow_spirituality": True,
    "allow_business": True,
    "allow_fitness": True,
    "block_sexualized": True,
    "block_scam": True,
    "block_violence": True,
    "replace_doomscroll": True,
    "confidence_thresholds": {
        "soft_warn": 0.35,
        "blur": 0.55,
        "block": 0.7,
        "replace": 0.5,
    },
    "positive_reinforcement_targets": [
        "learning",
        "creating",
        "working",
        "fitness",
        "calm",
        "family",
        "spirituality",
        "business_progress",
        "emotional_regulation",
    ],
}

TRUE_STRINGS = {"1", "true", "t", "yes", "y", "on", "enabled", "enable"}
FALSE_STRINGS = {"0", "false", "f", "no", "n", "off", "disabled", "disable"}

DEFAULT_CONFIDENCE_THRESHOLDS = DEFAULT_CONTROLS["confidence_thresholds"]
DEFAULT_TARGETS = DEFAULT_CONTROLS["positive_reinforcement_targets"]


def parse_bool(value: Any, default: bool = False) -> bool:
    """Safely parse booleans from CLI/config values."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in TRUE_STRINGS:
            return True
        if v in FALSE_STRINGS:
            return False
        return default
    return default


def _clamp_float(value: Any, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_controls(controls: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Merge user controls with defaults and safely parse booleans."""
    raw = dict(DEFAULT_CONTROLS)
    raw["confidence_thresholds"] = dict(DEFAULT_CONFIDENCE_THRESHOLDS)
    raw["positive_reinforcement_targets"] = list(DEFAULT_TARGETS)
    if controls:
        incoming = dict(controls)
        if isinstance(incoming.get("confidence_thresholds"), Mapping):
            thresholds = dict(raw["confidence_thresholds"])
            thresholds.update(dict(incoming.pop("confidence_thresholds")))
            incoming["confidence_thresholds"] = thresholds
        if not isinstance(incoming.get("positive_reinforcement_targets"), list):
            incoming.pop("positive_reinforcement_targets", None)
        raw.update(incoming)

    strictness = str(raw.get("strictness", "medium")).strip().lower()
    if strictness not in {"low", "medium", "high"}:
        strictness = "medium"

    thresholds_raw = raw.get("confidence_thresholds")
    thresholds_raw = thresholds_raw if isinstance(thresholds_raw, Mapping) else {}
    thresholds = {
        "soft_warn": _clamp_float(thresholds_raw.get("soft_warn"), 0.35),
        "blur": _clamp_float(thresholds_raw.get("blur"), 0.55),
        "block": _clamp_float(thresholds_raw.get("block"), 0.7),
        "replace": _clamp_float(thresholds_raw.get("replace"), 0.5),
    }

    targets = raw.get("positive_reinforcement_targets")
    if not isinstance(targets, list):
        targets = list(DEFAULT_TARGETS)
    targets = [str(item) for item in targets if str(item).strip()]

    return {
        "strictness": strictness,
        "allow_spirituality": parse_bool(raw.get("allow_spirituality"), True),
        "allow_business": parse_bool(raw.get("allow_business"), True),
        "allow_fitness": parse_bool(raw.get("allow_fitness"), True),
        "block_sexualized": parse_bool(raw.get("block_sexualized"), True),
        "block_scam": parse_bool(raw.get("block_scam"), True),
        "block_violence": parse_bool(raw.get("block_violence"), True),
        "replace_doomscroll": parse_bool(raw.get("replace_doomscroll"), True),
        "confidence_thresholds": thresholds,
        "positive_reinforcement_targets": targets,
    }


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"\s+", " ", text.strip().lower())


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalize_text(text)))


def contains_phrase(text: str, phrases: Iterable[str]) -> bool:
    t = normalize_text(text)
    return any(normalize_text(p) in t for p in phrases)


UPLIFT_PHRASES = {
    "learn something",
    "study with me",
    "build with me",
    "workout",
    "finished my workout",
    "family dinner",
    "call your mom",
    "gratitude",
    "prayer",
    "faith",
    "meditation",
    "deep work",
    "business progress",
    "small win",
    "emotional regulation",
    "calm breathing",
    "meal prep",
    "healthy routine",
    "journal",
    "create something",
    "ship the project",
    "clean your room",
    "focus session",
    "walk outside",
    "stretch",
    "read a book",
    "save money",
    "build a business",
    "positive habit",
}

UPLIFT_TOKENS = {
    "learn",
    "study",
    "create",
    "build",
    "work",
    "fitness",
    "run",
    "walk",
    "lift",
    "calm",
    "family",
    "faith",
    "prayer",
    "god",
    "gratitude",
    "journal",
    "focus",
    "business",
    "progress",
    "healing",
    "breathe",
    "meditate",
    "discipline",
    "cook",
    "clean",
    "practice",
    "skill",
    "read",
    "health",
    "sleep",
}

POSITIVE_HISTORY_PHRASES = {
    "lesson from history",
    "civil rights",
    "positive history",
    "story of resilience",
    "rebuilt after",
    "overcame hardship",
}
POSITIVE_HISTORY_TOKENS = {
    "history",
    "biography",
    "resilience",
    "inventor",
    "freedom",
    "rebuilding",
    "recovery",
    "ancestor",
    "stoicism",
    "wisdom",
}

HARD_NEWS_PHRASES = {
    "public safety",
    "court ruling",
    "economic report",
    "emergency update",
    "local officials",
    "city council",
}
HARD_NEWS_TOKENS = {
    "news",
    "election",
    "court",
    "policy",
    "budget",
    "storm",
    "earthquake",
    "war",
    "investigation",
    "safety",
    "officials",
}

CONSTRUCTIVE_NEWS_PHRASES = {
    "how to help",
    "recovery plan",
    "community response",
    "constructive update",
    "safety guidance",
    "what residents can do",
    "rebuilding effort",
}
CONSTRUCTIVE_NEWS_TOKENS = {
    "recovery",
    "rebuilding",
    "guidance",
    "solutions",
    "resources",
    "preparedness",
    "constructive",
}

CIVIC_AWARENESS_PHRASES = {
    "city council",
    "public meeting",
    "local election",
    "court ruling",
    "community safety",
    "voter guide",
}
CIVIC_AWARENESS_TOKENS = {
    "civic",
    "voter",
    "election",
    "policy",
    "council",
    "court",
    "community",
    "local",
}

TOXIC_PHRASES = {
    "everyone should mock",
    "publicly humiliate",
    "they are trash",
    "absolute clown",
    "human garbage",
    "worthless loser",
}
TOXIC_TOKENS = {"idiot", "moron", "stupid", "trash", "pathetic", "clown", "garbage", "hate", "humiliate", "mock", "loser"}

RAGEBAIT_PHRASES = {
    "you won't believe",
    "this will make you furious",
    "everyone is lying",
    "they don't want you to know",
    "destroyed in seconds",
    "watch them get exposed",
    "must be stopped",
    "this is why everyone hates",
    "share before they delete",
}
RAGEBAIT_TOKENS = {"exposed", "destroyed", "furious", "outrage", "cancel", "triggered", "meltdown", "rage"}

DOOMSCROLL_PHRASES = {
    "everything is collapsing",
    "the world is ending",
    "we are doomed",
    "crisis after crisis",
    "can't look away",
    "another disaster",
    "nothing matters anymore",
    "it only gets worse",
    "society is finished",
}
DOOMSCROLL_TOKENS = {"doomed", "collapse", "collapsing", "hopeless", "disaster", "crisis", "catastrophe", "apocalypse"}

SHAME_PHRASES = {
    "you are lazy",
    "you are worthless",
    "no one loves you",
    "only losers",
    "you will never be enough",
    "your body is disgusting",
    "you are broke because you are weak",
    "no excuses loser",
}
SHAME_TOKENS = {"worthless", "ugly", "fat", "lazy", "weak", "unlovable", "disgusting", "failure", "failed", "broke"}

VIOLENCE_PHRASES = {
    "fight footage",
    "graphic fight",
    "shooting video",
    "watch the assault",
    "street fight",
    "gore compilation",
    "blood everywhere",
}
VIOLENCE_TOKENS = {"kill", "killing", "murder", "shooting", "gun", "guns", "stab", "stabbing", "assault", "blood", "gore", "weapon", "weapons", "violence", "fight"}

SEXUALIZED_PHRASES = {"onlyfans", "explicit content", "nsfw", "thirst trap", "nude leak", "hot body challenge", "sexual content"}
SEXUALIZED_TOKENS = {"nude", "nudes", "explicit", "sexual", "porn", "nsfw", "thirst", "onlyfans"}

SCAM_PHRASES = {
    "guaranteed profit",
    "send money now",
    "wire me money",
    "cashapp me",
    "click this link to claim",
    "login to claim prize",
    "crypto giveaway",
    "double your money",
    "get rich quick",
    "limited time investment",
}
SCAM_TOKENS = {"scam", "giveaway", "wire", "cashapp", "prize", "crypto", "bitcoin", "investment", "guaranteed", "profit", "claim"}

CATEGORY_RULES: Dict[str, Tuple[set[str], set[str], str]] = {
    "UPLIFT": (UPLIFT_PHRASES, UPLIFT_TOKENS, "healthy reinforcement signal"),
    "TOXIC": (TOXIC_PHRASES, TOXIC_TOKENS, "toxic or hostile language"),
    "RAGEBAIT": (RAGEBAIT_PHRASES, RAGEBAIT_TOKENS, "outrage/ragebait framing"),
    "DOOMSCROLL": (DOOMSCROLL_PHRASES, DOOMSCROLL_TOKENS, "doomscroll pattern"),
    "SHAME": (SHAME_PHRASES, SHAME_TOKENS, "shame-based content"),
    "VIOLENCE": (VIOLENCE_PHRASES, VIOLENCE_TOKENS, "violent or graphic content"),
    "SEXUALIZED": (SEXUALIZED_PHRASES, SEXUALIZED_TOKENS, "sexualized content"),
    "SCAM": (SCAM_PHRASES, SCAM_TOKENS, "possible scam or manipulation"),
}

SECONDARY_RULES: Dict[str, Tuple[set[str], set[str], str]] = {
    "POSITIVE_HISTORY": (POSITIVE_HISTORY_PHRASES, POSITIVE_HISTORY_TOKENS, "positive history or resilience signal"),
    "HARD_NEWS": (HARD_NEWS_PHRASES, HARD_NEWS_TOKENS, "useful hard news or civic awareness"),
    "CONSTRUCTIVE_NEWS": (CONSTRUCTIVE_NEWS_PHRASES, CONSTRUCTIVE_NEWS_TOKENS, "constructive news framing"),
    "CIVIC_AWARENESS": (CIVIC_AWARENESS_PHRASES, CIVIC_AWARENESS_TOKENS, "civic awareness signal"),
}

HARMFUL_PRIORITY = ["SCAM", "VIOLENCE", "SEXUALIZED", "SHAME", "RAGEBAIT", "DOOMSCROLL", "TOXIC"]
RISK_WEIGHT = {"SCAM": 100, "VIOLENCE": 95, "SEXUALIZED": 85, "SHAME": 80, "RAGEBAIT": 70, "DOOMSCROLL": 65, "TOXIC": 60, "UPLIFT": 10}


def _matches(text: str, phrases: Iterable[str], tokens: Iterable[str]) -> tuple[list[str], list[str]]:
    t = normalize_text(text)
    toks = tokenize(t)
    phrase_matches = sorted({p for p in phrases if normalize_text(p) in t})
    token_matches = sorted({tok for tok in tokens if tok in toks})
    return phrase_matches, token_matches


def _positive_allowed(text: str, controls: Dict[str, Any]) -> bool:
    t = normalize_text(text)
    if not controls["allow_spirituality"] and contains_phrase(t, {"prayer", "faith", "god", "spirituality", "church", "scripture"}):
        return False
    if not controls["allow_business"] and contains_phrase(t, {"business", "startup", "sales", "profit", "entrepreneur"}):
        return False
    if not controls["allow_fitness"] and contains_phrase(t, {"workout", "fitness", "gym", "run", "lift weights", "meal prep"}):
        return False
    return True


def _category_scores(text: str, controls: Dict[str, Any]) -> tuple[Dict[str, int], Dict[str, Dict[str, list[str]]]]:
    scores = {category: 0 for category in CATEGORIES}
    evidence_by_category: Dict[str, Dict[str, list[str]]] = {}
    for category, (phrases, tokens, _reason) in {**CATEGORY_RULES, **SECONDARY_RULES}.items():
        phrase_matches, token_matches = _matches(text, phrases, tokens)
        if category == "UPLIFT" and not _positive_allowed(text, controls):
            phrase_matches = []
            token_matches = []
        score = len(phrase_matches) * 2 + len(token_matches)
        scores[category] = score
        evidence_by_category[category] = {
            "matched_phrases": phrase_matches,
            "matched_tokens": token_matches,
        }
    return scores, evidence_by_category


def _choose_category(scores: Dict[str, int]) -> str:
    harmful = [category for category in HARMFUL_PRIORITY if scores.get(category, 0) > 0]
    if harmful:
        return max(harmful, key=lambda category: (RISK_WEIGHT[category], scores[category]))
    if scores.get("UPLIFT", 0) > 0:
        return "UPLIFT"
    if scores.get("POSITIVE_HISTORY", 0) > 0:
        return "UPLIFT"
    return "NEUTRAL"


def _confidence(category: str, scores: Dict[str, int]) -> float:
    secondary_max = max((scores.get(label, 0) for label in SECONDARY_LABELS), default=0)
    if category == "NEUTRAL" and secondary_max <= 0:
        return 0.0
    primary = scores.get(category, 0)
    if category == "NEUTRAL":
        primary = secondary_max
    if category == "UPLIFT" and primary <= 0:
        primary = scores.get("POSITIVE_HISTORY", 0)
    if primary <= 0:
        return 0.0
    total = sum(max(0, value) for value in scores.values()) or primary
    density = min(1.0, primary / 4.0)
    dominance = primary / total
    return round(max(0.05, min(1.0, (density * 0.75) + (dominance * 0.25))), 3)


def _score_for_category(category: str, confidence: float) -> int:
    base = {
        "UPLIFT": 92,
        "NEUTRAL": 60,
        "TOXIC": 35,
        "RAGEBAIT": 25,
        "DOOMSCROLL": 28,
        "SHAME": 18,
        "VIOLENCE": 5,
        "SEXUALIZED": 30,
        "SCAM": 0,
    }.get(category, 50)
    if category in {"UPLIFT", "NEUTRAL"}:
        return base
    return max(0, min(100, int(round(base + ((1.0 - confidence) * 10)))))


def _action_for_category(category: str, controls: Dict[str, Any], confidence: float) -> str:
    strictness = controls["strictness"]
    thresholds = controls["confidence_thresholds"]

    if category in {"UPLIFT", "NEUTRAL"}:
        return "ALLOW"

    if category == "SCAM":
        if controls["block_scam"] and confidence >= thresholds["block"]:
            return "BLOCK"
        return "SOFT_WARN"

    if category == "VIOLENCE":
        if controls["block_violence"] and confidence >= thresholds["block"]:
            return "BLOCK"
        return "BLUR" if confidence >= thresholds["blur"] else "SOFT_WARN"

    if category == "SEXUALIZED":
        if controls["block_sexualized"] and confidence >= thresholds["block"]:
            return "BLOCK"
        return "BLUR" if confidence >= thresholds["blur"] else "SOFT_WARN"

    if category == "DOOMSCROLL":
        if controls["replace_doomscroll"] and confidence >= thresholds["replace"]:
            return "REPLACE"
        return "BLUR" if strictness == "high" and confidence >= thresholds["blur"] else "SOFT_WARN"

    if category in {"RAGEBAIT", "SHAME"}:
        if strictness == "low" and confidence < thresholds["replace"]:
            return "SOFT_WARN"
        return "REPLACE"

    if category == "TOXIC":
        if strictness == "high" and confidence >= thresholds["blur"]:
            return "BLUR"
        if strictness in {"medium", "high"} and confidence >= thresholds["replace"]:
            return "REPLACE"
        return "SOFT_WARN"

    return "SOFT_WARN"


def _news_action(labels: Iterable[str], controls: Dict[str, Any]) -> str | None:
    label_set = set(labels)
    if "CONSTRUCTIVE_NEWS" in label_set:
        return "ALLOW"
    if "HARD_NEWS" in label_set or "CIVIC_AWARENESS" in label_set:
        return "SOFT_WARN" if controls["strictness"] == "high" else "ALLOW"
    return None


def required_output(
    score: int,
    category: str,
    action: str,
    reason: str,
    positive_replacement: str = "",
    confidence: float = 0.0,
    labels: Iterable[str] | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    category = category if category in CATEGORIES else "NEUTRAL"
    action = action if action in ACTIONS else "SOFT_WARN"
    score = max(0, min(100, int(score)))
    label_list = [label for label in (labels or [category]) if label in ALL_LABELS]
    if category not in label_list:
        label_list.insert(0, category)
    evidence_obj = dict(evidence or {})
    evidence_obj.setdefault("matched_phrases", [])
    evidence_obj.setdefault("matched_tokens", [])
    evidence_obj.setdefault("category_scores", {cat: 0 for cat in sorted(ALL_LABELS)})

    return {
        "score": score,
        "confidence": _clamp_float(confidence, 0.0),
        "category": category,
        "labels": label_list,
        "action": action,
        "reason": str(reason or ""),
        "evidence": evidence_obj,
        "positive_replacement": str(positive_replacement or ""),
    }


def classify_content(content: Mapping[str, Any] | Any, controls: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Classify one content item with transparent local heuristics."""
    normalized_controls = normalize_controls(controls)
    if not isinstance(content, Mapping):
        return required_output(
            score=50,
            category="NEUTRAL",
            action="SOFT_WARN",
            reason=f"malformed_content_input:{type(content).__name__}",
            positive_replacement="",
            confidence=0.0,
            labels=["NEUTRAL"],
        )

    text = str(content.get("text", "") or "")
    if not normalize_text(text):
        return required_output(
            score=60,
            category="NEUTRAL",
            action="ALLOW",
            reason="empty_or_missing_text",
            confidence=0.0,
            labels=["NEUTRAL"],
        )

    scores, evidence_by_category = _category_scores(text, normalized_controls)
    category = _choose_category(scores)
    confidence = _confidence(category, scores)
    score = _score_for_category(category, confidence)

    labels = [cat for cat in HARMFUL_PRIORITY if scores.get(cat, 0) > 0]
    if scores.get("UPLIFT", 0) > 0:
        labels.append("UPLIFT")
    for label in ("POSITIVE_HISTORY", "CONSTRUCTIVE_NEWS", "HARD_NEWS", "CIVIC_AWARENESS"):
        if scores.get(label, 0) > 0:
            labels.append(label)
    if not labels:
        labels = ["NEUTRAL"]

    action = _action_for_category(category, normalized_controls, confidence)
    if category in {"NEUTRAL", "UPLIFT"}:
        action = _news_action(labels, normalized_controls) or action

    matched_phrases: list[str] = []
    matched_tokens: list[str] = []
    for label in labels:
        matched_phrases.extend(evidence_by_category.get(label, {}).get("matched_phrases", []))
        matched_tokens.extend(evidence_by_category.get(label, {}).get("matched_tokens", []))

    reason = CATEGORY_RULES.get(category, (set(), set(), "no strong positive or harmful pattern detected"))[2]
    if category == "NEUTRAL":
        reason = "no strong positive or harmful pattern detected"
    if category in {"NEUTRAL", "UPLIFT"}:
        if "CONSTRUCTIVE_NEWS" in labels:
            reason = "constructive news framing with useful next steps"
        elif "HARD_NEWS" in labels or "CIVIC_AWARENESS" in labels:
            reason = "useful hard news or civic awareness without ragebait framing"
        elif "POSITIVE_HISTORY" in labels:
            reason = "positive history or resilience signal"

    return required_output(
        score=score,
        confidence=confidence,
        category=category,
        labels=labels,
        action=action,
        reason=reason,
        evidence={
            "matched_phrases": sorted(set(matched_phrases)),
            "matched_tokens": sorted(set(matched_tokens)),
            "category_scores": {cat: scores.get(cat, 0) for cat in sorted(ALL_LABELS)},
        },
        positive_replacement="",
    )


if __name__ == "__main__":
    import json

    demo = {
        "text": "Take a walk, breathe, journal one small win, and build your project for 25 minutes.",
        "source": "social_post",
        "media_type": "text",
        "metadata": {},
    }
    print(json.dumps(classify_content(demo), indent=2, sort_keys=True))

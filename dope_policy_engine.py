#!/usr/bin/env python3
"""
DOPE v0.3 - Feed decision engine with local audit log.

classify_content() returns raw classifier output. DopePolicyEngine.decide_content()
returns policy output enriched with replacement text and audit status.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping

from dope_classifier import DEFAULT_CONTROLS, DOPE_VERSION, normalize_controls, parse_bool, required_output
from dope_classifier import classify_content
from dope_explain import explain_decision, explain_replacement
from dope_reinforcement_engine import attach_replacement, replacement_source_for_decision
from dope_session_memory import load_session_memory, save_session_memory, summarize_session, update_session_memory


PROJECT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_AUDIT_LOG_PATH = PROJECT_DIR / "audit" / "dope_audit.jsonl"
DEFAULT_PROFILE_PATH = PROJECT_DIR / "dope_profile.json"


class DopeConfigError(Exception):
    """Raised when a local controls config cannot be loaded clearly."""


def load_feed(path: pathlib.Path) -> List[Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise ValueError("Feed must be a JSON list or an object with an 'items' list.")


def load_controls_config(path: pathlib.Path | None) -> Dict[str, Any]:
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise DopeConfigError(f"Could not load config: {path}: malformed JSON") from exc
    except OSError as exc:
        raise DopeConfigError(f"Could not load config: {path}: {exc.strerror or exc}") from exc
    if not isinstance(payload, dict):
        raise DopeConfigError(f"Could not load config: {path}: config JSON must be an object")
    return payload


def default_profile() -> Dict[str, Any]:
    return {
        "dope_version": DOPE_VERSION,
        "profile_name": "default",
        "primary_goals": [
            "learn",
            "create",
            "fitness",
            "calm",
            "family",
            "spirituality",
            "business_progress",
            "emotional_regulation",
        ],
        "sensitive_areas": ["doomscrolling", "ragebait", "shame", "scams"],
        "content_preferences": {
            "allow_hard_news": True,
            "prefer_constructive_news": True,
            "prefer_positive_history": True,
            "prefer_learning": True,
            "prefer_faith_spirituality": True,
            "prefer_business": True,
            "prefer_fitness": True,
            "prefer_family": True,
        },
        "replacement_style": "firm_but_kind",
        "daily_reinforcement_limit": 25,
        "audit_level": "full",
    }


def load_profile(path: pathlib.Path | None) -> Dict[str, Any]:
    if path is None:
        return default_profile()
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise DopeConfigError(f"Could not load profile: {path}: malformed JSON") from exc
    except OSError as exc:
        raise DopeConfigError(f"Could not load profile: {path}: {exc.strerror or exc}") from exc
    if not isinstance(payload, dict):
        raise DopeConfigError(f"Could not load profile: {path}: profile JSON must be an object")
    profile = default_profile()
    profile.update(payload)
    if not isinstance(profile.get("content_preferences"), dict):
        profile["content_preferences"] = default_profile()["content_preferences"]
    if not isinstance(profile.get("primary_goals"), list):
        profile["primary_goals"] = default_profile()["primary_goals"]
    if not isinstance(profile.get("sensitive_areas"), list):
        profile["sensitive_areas"] = default_profile()["sensitive_areas"]
    profile["dope_version"] = DOPE_VERSION
    return profile


def normalize_feed_item(item: Any, index: int | None = None) -> tuple[Dict[str, Any], str | None]:
    fallback_id = f"item_{index}" if index is not None else "item_unknown"
    if not isinstance(item, Mapping):
        return (
            {
                "id": fallback_id,
                "text": "",
                "source": "malformed_feed_item",
                "media_type": "text",
                "metadata": {
                    "validation_error": "feed_item_not_object",
                    "raw_type": type(item).__name__,
                    "raw_value": repr(item)[:200],
                },
            },
            f"feed_item_not_object:{type(item).__name__}",
        )

    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return (
        {
            "id": str(item.get("id", fallback_id)),
            "text": str(item.get("text", "")),
            "source": str(item.get("source", "social_post")),
            "media_type": str(item.get("media_type", "text")),
            "metadata": metadata,
        },
        None,
    )


class DopePolicyEngine:
    """
    Reusable local-first policy engine.

    decide_content() returns a single policy result and appends one JSONL audit
    record. evaluate_feed() preserves item order and logs every feed item.
    """

    def __init__(
        self,
        controls: Mapping[str, Any] | None = None,
        audit_path: str | pathlib.Path | None = None,
        profile: Mapping[str, Any] | None = None,
        session_memory_path: str | pathlib.Path | None = None,
    ) -> None:
        self.controls = normalize_controls(controls)
        self.audit_path = pathlib.Path(audit_path) if audit_path else DEFAULT_AUDIT_LOG_PATH
        self.profile = dict(profile) if isinstance(profile, Mapping) else default_profile()
        self.session_memory_path = pathlib.Path(session_memory_path) if session_memory_path else None
        self.session_memory = load_session_memory(self.session_memory_path) if self.session_memory_path else None

    def _write_audit(self, result: Dict[str, Any], validation_error: str | None = None) -> str:
        profile_snapshot = {
            "profile_name": self.profile.get("profile_name", "default"),
            "primary_goals": self.profile.get("primary_goals", []),
            "sensitive_areas": self.profile.get("sensitive_areas", []),
            "audit_level": self.profile.get("audit_level", "full"),
        }
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "index": result.get("index"),
            "content": result.get("content"),
            "decision": result.get("decision"),
            "controls": self.controls,
            "profile": profile_snapshot,
            "profile_used": result.get("profile_used"),
            "explanation": result.get("explanation"),
            "replacement_source": result.get("replacement_source"),
            "session_summary": result.get("session_summary"),
            "validation_error": validation_error,
            "local_first": True,
            "dark_patterns": {
                "infinite_scroll_optimization": False,
                "outrage_optimization": False,
                "harmful_exposure_increase": False,
            },
            "dope_version": DOPE_VERSION,
        }
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        return "written"

    def decide_content(self, content: Any, index: int | None = None) -> Dict[str, Any]:
        normalized_content, validation_error = normalize_feed_item(content, index)
        if validation_error:
            raw_decision = required_output(
                score=50,
                category="NEUTRAL",
                action="SOFT_WARN",
                reason=validation_error,
                positive_replacement="",
                confidence=0.0,
                labels=["NEUTRAL"],
            )
        else:
            raw_decision = classify_content(normalized_content, self.controls)

        decision = attach_replacement(raw_decision, normalized_content, self.controls)
        replacement_source = replacement_source_for_decision(decision)
        explanation = explain_decision(normalized_content, decision, self.profile)
        replacement_explanation = explain_replacement(decision, self.profile)
        result = {
            "index": index,
            "content": normalized_content,
            "decision": decision,
            "profile_used": str(self.profile.get("profile_name", "default")),
            "explanation": explanation,
            "replacement_explanation": replacement_explanation,
            "replacement_source": replacement_source,
            "audit_status": "failed",
            "audit_path": str(self.audit_path),
        }
        if self.session_memory is not None and self.session_memory_path is not None:
            self.session_memory = update_session_memory(self.session_memory, result)
            session_summary = summarize_session(self.session_memory)
            result["session_summary"] = session_summary
            save_session_memory(self.session_memory, self.session_memory_path)

        try:
            result["audit_status"] = self._write_audit(result, validation_error=validation_error)
        except OSError:
            result["audit_status"] = "failed"

        return result

    def evaluate_feed(self, feed: Iterable[Any]) -> List[Dict[str, Any]]:
        return [self.decide_content(item, index=index) for index, item in enumerate(feed)]


def build_controls(args: argparse.Namespace) -> Dict[str, Any]:
    controls = dict(DEFAULT_CONTROLS)
    controls.update(load_controls_config(pathlib.Path(args.config)) if args.config else {})

    cli_values = {
        "strictness": args.strictness,
        "allow_spirituality": args.allow_spirituality,
        "allow_business": args.allow_business,
        "allow_fitness": args.allow_fitness,
        "block_sexualized": args.block_sexualized,
        "block_scam": args.block_scam,
        "block_violence": args.block_violence,
        "replace_doomscroll": args.replace_doomscroll,
    }
    for key, value in cli_values.items():
        if value is not None:
            controls[key] = value

    return normalize_controls(controls)


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    allowed = [r for r in results if r["decision"]["action"] == "ALLOW"]
    blocked_or_replaced = [r for r in results if r["decision"]["action"] != "ALLOW"]
    replacements = [
        r["decision"]["positive_replacement"]
        for r in blocked_or_replaced
        if r["decision"].get("positive_replacement")
    ]
    audit_path = results[0]["audit_path"] if results else str(DEFAULT_AUDIT_LOG_PATH)
    session_summary = None
    for row in reversed(results):
        if row.get("session_summary"):
            session_summary = row["session_summary"]
            break
    return {
        "allowed": allowed,
        "blocked_or_replaced": blocked_or_replaced,
        "positive_replacements": replacements,
        "audit_log_path": audit_path,
        "session_summary": session_summary,
    }


def print_report(report: Dict[str, Any]) -> None:
    print("=== ALLOWED CONTENT ===")
    for row in report["allowed"]:
        content = row["content"]
        decision = row["decision"]
        print(f"- {content['id']}: {decision['category']} score={decision['score']} :: {content['text']}")

    print("\n=== BLOCKED / REPLACED CONTENT ===")
    for row in report["blocked_or_replaced"]:
        content = row["content"]
        decision = row["decision"]
        print(
            f"- {content['id']}: {decision['action']} {decision['category']} "
            f"score={decision['score']} audit={row['audit_status']} :: {decision['reason']}"
        )

    print("\n=== POSITIVE REPLACEMENTS ===")
    if report["positive_replacements"]:
        for replacement in report["positive_replacements"]:
            print(f"- {replacement}")
    else:
        print("- None")

    if report.get("session_summary"):
        print("\n=== SESSION SUMMARY ===")
        print(json.dumps(report["session_summary"], indent=2, sort_keys=True))

    print(f"\nAudit log path: {report['audit_log_path']}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DOPE v0.3 local-first content policy engine")
    parser.add_argument("feed_path", help="Path to a JSON feed file")
    parser.add_argument("--config", help="Optional local JSON controls config")
    parser.add_argument("--profile", help="Optional local JSON reinforcement profile")
    parser.add_argument("--audit-path", help="Optional JSONL audit log path")
    parser.add_argument("--session-memory", help="Optional local JSON session memory path")
    parser.add_argument("--strictness", choices=["low", "medium", "high"])
    parser.add_argument("--allow-spirituality", type=parse_bool)
    parser.add_argument("--allow-business", type=parse_bool)
    parser.add_argument("--allow-fitness", type=parse_bool)
    parser.add_argument("--block-sexualized", type=parse_bool)
    parser.add_argument("--block-scam", type=parse_bool)
    parser.add_argument("--block-violence", type=parse_bool)
    parser.add_argument("--replace-doomscroll", type=parse_bool)
    parser.add_argument("--json", action="store_true", help="Print machine-readable policy results")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        controls = build_controls(args)
        profile = load_profile(pathlib.Path(args.profile)) if args.profile else load_profile(DEFAULT_PROFILE_PATH)
    except DopeConfigError as exc:
        print(f"[DOPE CONFIG ERROR] {exc}", file=sys.stderr)
        return 2
    items = load_feed(pathlib.Path(args.feed_path))
    engine = DopePolicyEngine(
        controls=controls,
        audit_path=args.audit_path,
        profile=profile,
        session_memory_path=args.session_memory,
    )
    results = engine.evaluate_feed(items)
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        print_report(summarize_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

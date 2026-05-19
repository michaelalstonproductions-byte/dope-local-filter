#!/usr/bin/env python3
"""Local bundle helpers for DOPE v0.5 mobile integrations."""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Mapping

from dope_classifier import DEFAULT_CONTROLS, DOPE_VERSION, normalize_controls
from dope_reinforcement_engine import load_content_library
from dope_session_memory import load_session_memory


PROJECT_DIR = pathlib.Path(__file__).resolve().parent


class DopeBundleError(Exception):
    """Raised when a local DOPE bundle cannot be loaded or saved cleanly."""


def _default_profile() -> Dict[str, Any]:
    profile_path = PROJECT_DIR / "dope_profile.json"
    try:
        with profile_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        payload = {}
    profile = payload if isinstance(payload, dict) else {}
    profile.setdefault("profile_name", "default")
    profile.setdefault("primary_goals", ["learn", "create", "fitness", "calm", "family"])
    profile.setdefault("sensitive_areas", ["doomscrolling", "ragebait", "shame", "scams"])
    profile.setdefault("content_preferences", {"allow_hard_news": True})
    profile.setdefault("replacement_style", "firm_but_kind")
    profile.setdefault("daily_reinforcement_limit", 25)
    profile.setdefault("audit_level", "full")
    profile["dope_version"] = DOPE_VERSION
    return profile


def default_bundle() -> Dict[str, Any]:
    return {
        "dope_version": DOPE_VERSION,
        "controls": normalize_controls(DEFAULT_CONTROLS),
        "profile": _default_profile(),
        "content_library": load_content_library(PROJECT_DIR / "dope_content_library.json"),
        "session_memory": load_session_memory(PROJECT_DIR / ".runtime" / "default_session_memory.json"),
        "local_first": True,
    }


def validate_bundle(bundle: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(bundle, Mapping):
        return False, ["bundle_not_object"]
    if bundle.get("local_first") is not True:
        errors.append("local_first_must_be_true")
    if not isinstance(bundle.get("controls"), Mapping):
        errors.append("controls_missing_or_invalid")
    if not isinstance(bundle.get("profile"), Mapping):
        errors.append("profile_missing_or_invalid")
    if not isinstance(bundle.get("content_library"), Mapping):
        errors.append("content_library_missing_or_invalid")
    if not isinstance(bundle.get("session_memory"), Mapping):
        errors.append("session_memory_missing_or_invalid")
    return not errors, errors


def load_bundle(path: str | pathlib.Path) -> Dict[str, Any]:
    bundle_path = pathlib.Path(path)
    try:
        with bundle_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise DopeBundleError(f"Could not load bundle: {bundle_path}: malformed JSON") from exc
    except OSError as exc:
        raise DopeBundleError(f"Could not load bundle: {bundle_path}: {exc.strerror or exc}") from exc
    if not isinstance(payload, dict):
        raise DopeBundleError(f"Could not load bundle: {bundle_path}: bundle JSON must be an object")
    base = default_bundle()
    base.update(payload)
    base["dope_version"] = DOPE_VERSION
    base["local_first"] = True
    if not isinstance(base.get("controls"), Mapping):
        base["controls"] = default_bundle()["controls"]
    if not isinstance(base.get("profile"), Mapping):
        base["profile"] = default_bundle()["profile"]
    if not isinstance(base.get("content_library"), Mapping):
        base["content_library"] = default_bundle()["content_library"]
    if not isinstance(base.get("session_memory"), Mapping):
        base["session_memory"] = default_bundle()["session_memory"]
    valid, errors = validate_bundle(base)
    if not valid:
        raise DopeBundleError(f"Could not load bundle: {bundle_path}: {';'.join(errors)}")
    return base


def save_bundle(bundle: Mapping[str, Any], path: str | pathlib.Path) -> None:
    valid, errors = validate_bundle(bundle)
    if not valid:
        raise ValueError(";".join(errors))
    bundle_path = pathlib.Path(path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with bundle_path.open("w", encoding="utf-8") as f:
        json.dump(dict(bundle), f, indent=2, sort_keys=True)
        f.write("\n")


__all__ = ["DopeBundleError", "default_bundle", "load_bundle", "save_bundle", "validate_bundle"]

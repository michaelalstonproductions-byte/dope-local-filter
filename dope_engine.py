#!/usr/bin/env python3
"""Stable reusable DOPE v0.5 local engine API."""

from __future__ import annotations

import pathlib
from typing import Any, Dict, Iterable, Mapping

from dope_bundle import default_bundle, load_bundle, save_bundle
from dope_classifier import DOPE_VERSION
from dope_daily_plan import build_daily_plan
from dope_policy_engine import DopePolicyEngine, default_profile
from dope_recommender import build_recommendations
from dope_reinforcement_engine import load_content_library
from dope_session_memory import summarize_session, update_session_memory


def evaluate_content(content: Any, controls: Mapping[str, Any] | None = None, profile: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    engine = DopePolicyEngine(controls=controls, profile=profile or default_profile())
    return engine.decide_content(content, index=0)


def evaluate_feed(
    feed: Iterable[Any],
    controls: Mapping[str, Any] | None = None,
    profile: Mapping[str, Any] | None = None,
    session_memory: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    memory = dict(session_memory) if isinstance(session_memory, Mapping) else None
    engine = DopePolicyEngine(controls=controls, profile=profile or default_profile())
    results = []
    for index, item in enumerate(feed):
        result = engine.decide_content(item, index=index)
        if memory is not None:
            memory = update_session_memory(memory, result)
            result["session_summary"] = summarize_session(memory)
        results.append(result)
    return {
        "results": results,
        "session_memory": memory,
        "session_summary": summarize_session(memory or {}),
        "audit_written": all(row.get("audit_status") == "written" for row in results),
    }


def recommend_from_results(
    results: list[Mapping[str, Any]],
    profile: Mapping[str, Any] | None = None,
    session_memory: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return build_recommendations(
        results,
        profile or default_profile(),
        load_content_library(),
        session_memory=session_memory,
    )


def build_daily_plan_for_profile(
    profile: Mapping[str, Any] | None = None,
    session_memory: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return build_daily_plan(profile or default_profile(), load_content_library(), session_memory=session_memory)


def run_dope_bundle(feed: Iterable[Any], bundle_path: str | pathlib.Path | None = None) -> Dict[str, Any]:
    if bundle_path:
        path = pathlib.Path(bundle_path)
        if path.exists():
            bundle = load_bundle(path)
        else:
            bundle = default_bundle()
            save_bundle(bundle, path)
    else:
        bundle = default_bundle()

    evaluated = evaluate_feed(
        feed,
        controls=bundle.get("controls"),
        profile=bundle.get("profile"),
        session_memory=bundle.get("session_memory"),
    )
    session_memory = evaluated.get("session_memory") or bundle.get("session_memory") or {}
    bundle["session_memory"] = session_memory
    if bundle_path:
        save_bundle(bundle, bundle_path)

    recommendations = build_recommendations(
        evaluated["results"],
        bundle.get("profile") or default_profile(),
        bundle.get("content_library") or load_content_library(),
        session_memory=session_memory,
    )
    daily_plan = build_daily_plan(
        bundle.get("profile") or default_profile(),
        bundle.get("content_library") or load_content_library(),
        session_memory=session_memory,
    )
    return {
        "dope_version": DOPE_VERSION,
        "local_first": True,
        "content_results": evaluated["results"],
        "recommendations": recommendations,
        "daily_plan": daily_plan,
        "session_summary": summarize_session(session_memory),
        "audit_written": bool(evaluated["audit_written"]),
    }


__all__ = [
    "evaluate_content",
    "evaluate_feed",
    "recommend_from_results",
    "build_daily_plan_for_profile",
    "run_dope_bundle",
]

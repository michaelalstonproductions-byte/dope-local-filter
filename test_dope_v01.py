#!/usr/bin/env python3
"""Standard-library tests for DOPE v0.4."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from dope_classifier import ACTIONS, CATEGORIES, classify_content, normalize_controls, parse_bool
from dope_daily_plan import build_daily_plan
from dope_policy_engine import DopePolicyEngine, load_controls_config, load_feed, load_profile
from dope_recommender import build_recommendations
from dope_reinforcement_engine import load_content_library
from dope_session_memory import load_session_memory, update_session_memory


PROJECT_DIR = pathlib.Path(__file__).resolve().parent
SAMPLE_FEED = PROJECT_DIR / "sample_feed.json"
CONTROLS_FILE = PROJECT_DIR / "dope_controls.json"
PROFILE_FILE = PROJECT_DIR / "dope_profile.json"
CONTENT_LIBRARY_FILE = PROJECT_DIR / "dope_content_library.json"
NETWORK_IMPORT_TERMS = ("requests", "urllib", "http.client", "socket")


class DopeV04Tests(unittest.TestCase):
    def test_recommender_and_daily_plan_import(self) -> None:
        self.assertTrue(callable(build_recommendations))
        self.assertTrue(callable(build_daily_plan))

    def test_parse_bool_false_strings(self) -> None:
        self.assertIs(parse_bool("false"), False)
        self.assertIs(parse_bool("0"), False)
        self.assertIs(parse_bool("no"), False)

    def test_parse_bool_true_string(self) -> None:
        self.assertIs(parse_bool("true"), True)

    def test_normalize_controls_handles_string_booleans(self) -> None:
        controls = normalize_controls(
            {
                "allow_spirituality": "false",
                "allow_business": "0",
                "allow_fitness": "no",
                "block_sexualized": "true",
                "block_scam": "1",
                "block_violence": "yes",
                "replace_doomscroll": "off",
                "confidence_thresholds": {"block": "0.9"},
            }
        )
        self.assertEqual(controls["strictness"], "medium")
        self.assertIs(controls["allow_spirituality"], False)
        self.assertIs(controls["allow_business"], False)
        self.assertIs(controls["allow_fitness"], False)
        self.assertIs(controls["block_sexualized"], True)
        self.assertIs(controls["block_scam"], True)
        self.assertIs(controls["block_violence"], True)
        self.assertIs(controls["replace_doomscroll"], False)
        self.assertEqual(controls["confidence_thresholds"]["block"], 0.9)

    def test_classifier_always_returns_required_schema_keys(self) -> None:
        decision = classify_content({"text": "Study one lesson and take a walk."})
        self.assertEqual(
            set(decision.keys()),
            {"score", "confidence", "category", "labels", "action", "reason", "evidence", "positive_replacement"},
        )
        self.assertIsInstance(decision["score"], int)
        self.assertIn(decision["category"], CATEGORIES)
        self.assertIn(decision["action"], ACTIONS)
        self.assertIsInstance(decision["labels"], list)
        self.assertIsInstance(decision["reason"], str)
        self.assertEqual(decision["positive_replacement"], "")

    def test_confidence_field_exists_and_is_0_to_1(self) -> None:
        decision = classify_content({"text": "Guaranteed profit crypto giveaway double your money."})
        self.assertGreaterEqual(decision["confidence"], 0.0)
        self.assertLessEqual(decision["confidence"], 1.0)

    def test_labels_field_can_contain_multiple_categories(self) -> None:
        decision = classify_content({"text": "Learn a calm skill, then claim this guaranteed profit crypto giveaway."})
        self.assertIn("SCAM", decision["labels"])
        self.assertIn("UPLIFT", decision["labels"])

    def test_evidence_contains_expected_fields(self) -> None:
        decision = classify_content({"text": "Everything is collapsing and we are doomed."})
        evidence = decision["evidence"]
        self.assertIn("matched_phrases", evidence)
        self.assertIn("matched_tokens", evidence)
        self.assertIn("category_scores", evidence)
        self.assertIsInstance(evidence["matched_phrases"], list)
        self.assertIsInstance(evidence["matched_tokens"], list)
        self.assertIsInstance(evidence["category_scores"], dict)

    def test_harmful_category_beats_uplift_when_both_match(self) -> None:
        decision = classify_content({"text": "Learn a business skill, then send money now for guaranteed profit."})
        self.assertEqual(decision["category"], "SCAM")
        self.assertIn("UPLIFT", decision["labels"])

    def test_scam_and_violence_can_block(self) -> None:
        scam = classify_content({"text": "Guaranteed profit crypto giveaway, double your money and claim the prize."})
        violence = classify_content({"text": "Graphic fight footage with blood everywhere after the street fight."})
        self.assertEqual(scam["category"], "SCAM")
        self.assertEqual(scam["action"], "BLOCK")
        self.assertEqual(violence["category"], "VIOLENCE")
        self.assertEqual(violence["action"], "BLOCK")

    def test_all_categories_are_reachable(self) -> None:
        cases = {
            "UPLIFT": "Learn a skill, take a walk, and journal a small win.",
            "NEUTRAL": "The meeting starts at six and has three agenda items.",
            "TOXIC": "That person is an idiot and a moron.",
            "RAGEBAIT": "You won't believe this outrage meltdown.",
            "DOOMSCROLL": "Everything is collapsing and we are doomed.",
            "SHAME": "You are worthless and you will never be enough.",
            "VIOLENCE": "Graphic fight footage with blood everywhere.",
            "SEXUALIZED": "NSFW explicit sexual content.",
            "SCAM": "Guaranteed profit from this crypto giveaway.",
        }
        reached = {classify_content({"text": text})["category"] for text in cases.values()}
        self.assertEqual(reached, set(cases.keys()))

    def test_all_actions_are_reachable(self) -> None:
        cases = [
            ("ALLOW", {"text": "The meeting starts at six."}, {}),
            ("SOFT_WARN", {"text": "That person is an idiot."}, {"strictness": "low"}),
            ("BLUR", {"text": "Graphic fight with blood everywhere."}, {"block_violence": "false"}),
            ("BLOCK", {"text": "Guaranteed profit crypto giveaway double your money claim prize."}, {}),
            ("REPLACE", {"text": "Everything is collapsing and we are doomed."}, {}),
        ]
        reached = {classify_content(content, controls)["action"] for _, content, controls in cases}
        self.assertEqual(reached, {expected for expected, _, _ in cases})

    def test_profile_json_loads(self) -> None:
        profile = load_profile(PROFILE_FILE)
        self.assertEqual(profile["dope_version"], "0.4")
        self.assertEqual(profile["profile_name"], "default")
        self.assertIn("business_progress", profile["primary_goals"])

    def test_content_library_json_loads(self) -> None:
        library = load_content_library(CONTENT_LIBRARY_FILE)
        self.assertIn("positive_history", library)
        self.assertIn("constructive_news", library)
        for target in (
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
            "emergency_reset",
        ):
            self.assertGreaterEqual(len(library[target]), 5)

    def test_hard_news_is_not_automatically_blocked(self) -> None:
        decision = classify_content(
            {"text": "Local officials issued a public safety update after the storm with shelter resources."}
        )
        self.assertIn("HARD_NEWS", decision["labels"])
        self.assertIn(decision["action"], {"ALLOW", "SOFT_WARN"})
        self.assertNotIn(decision["action"], {"BLOCK", "REPLACE"})

    def test_ragebait_news_is_replaced(self) -> None:
        decision = classify_content({"text": "You won't believe this election outrage meltdown. Share before they delete."})
        self.assertEqual(decision["category"], "RAGEBAIT")
        self.assertEqual(decision["action"], "REPLACE")

    def test_doomscroll_is_replaced(self) -> None:
        decision = classify_content({"text": "Everything is collapsing and crisis after crisis proves we are doomed."})
        self.assertEqual(decision["category"], "DOOMSCROLL")
        self.assertEqual(decision["action"], "REPLACE")

    def test_positive_history_is_allowed(self) -> None:
        decision = classify_content({"text": "A biography about an inventor shows resilience and a lesson from history."})
        self.assertIn("POSITIVE_HISTORY", decision["labels"])
        self.assertIn(decision["category"], {"UPLIFT", "NEUTRAL"})
        self.assertEqual(decision["action"], "ALLOW")

    def test_config_json_loads(self) -> None:
        controls = load_controls_config(CONTROLS_FILE)
        normalized = normalize_controls(controls)
        self.assertEqual(normalized["strictness"], "medium")
        self.assertIn("business_progress", normalized["positive_reinforcement_targets"])

    def test_malformed_config_json_exits_2_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_config = pathlib.Path(tmp) / "bad_config.json"
            bad_config.write_text("{bad json", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "dope_policy_engine.py"), str(SAMPLE_FEED), "--config", str(bad_config)],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("[DOPE CONFIG ERROR]", result.stderr)
            self.assertIn("malformed JSON", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_non_object_config_json_exits_2_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            list_config = pathlib.Path(tmp) / "list_config.json"
            list_config.write_text("[1,2,3]", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--config",
                    str(list_config),
                    "--json",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("[DOPE CONFIG ERROR]", result.stderr)
            self.assertIn("must be an object", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_profile_cli_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--profile",
                    str(PROFILE_FILE),
                    "--audit-path",
                    str(audit_path),
                    "--json",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["profile_used"], "default")
            self.assertIn("explanation", payload[0])

    def test_session_memory_cli_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_path = pathlib.Path(tmp) / "memory.json"
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--session-memory",
                    str(memory_path),
                    "--audit-path",
                    str(audit_path),
                    "--json",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertEqual(memory["items_seen"], len(load_feed(SAMPLE_FEED)))
            payload = json.loads(result.stdout)
            self.assertIn("session_summary", payload[-1])

    def test_malformed_feed_items_do_not_crash_and_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            results = engine.evaluate_feed(["bad item", 123, None])
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r["audit_status"] == "written" for r in results))
            self.assertTrue(all(r["decision"]["action"] == "SOFT_WARN" for r in results))
            self.assertEqual(len(audit_path.read_text(encoding="utf-8").splitlines()), 3)

    def test_policy_output_includes_explanation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path, profile=load_profile(PROFILE_FILE))
            result = engine.decide_content({"text": "I finished my workout and studied."}, index=0)
            self.assertIn("explanation", result)
            self.assertIn("profile_used", result)
            self.assertIn("replacement_source", result)
            self.assertNotIn("validation_error", result)

    def test_audit_keeps_validation_error_for_malformed_feed_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            result = engine.decide_content("bad item", index=7)
            self.assertNotIn("validation_error", result)
            record = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["validation_error"], "feed_item_not_object:str")
            self.assertIn("explanation", record)

    def test_audit_includes_dope_version_04(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            engine.decide_content({"text": "The meeting starts at six."}, index=0)
            record = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["dope_version"], "0.4")
            self.assertTrue(record["local_first"])
            self.assertFalse(record["dark_patterns"]["outrage_optimization"])
            self.assertEqual(record["profile_used"], "default")

    def test_session_memory_increments_category_and_action_counts(self) -> None:
        memory = load_session_memory("/tmp/does_not_need_to_exist_dope_memory.json")
        result = {
            "decision": {"category": "DOOMSCROLL", "action": "REPLACE", "positive_replacement": "Take six breaths."},
            "replacement_source": "calm",
        }
        updated = update_session_memory(memory, result)
        self.assertEqual(updated["items_seen"], 1)
        self.assertEqual(updated["category_counts"]["DOOMSCROLL"], 1)
        self.assertEqual(updated["action_counts"]["REPLACE"], 1)
        self.assertEqual(updated["replacement_counts"]["calm"], 1)

    def test_malformed_session_memory_values_do_not_crash(self) -> None:
        memory = {
            "items_seen": "bad",
            "category_counts": {"DOOMSCROLL": "bad"},
            "action_counts": {"REPLACE": "bad"},
            "replacement_counts": {"calm": "bad"},
            "positive_targets_served": {"calm": "bad"},
        }
        result = {
            "decision": {"category": "DOOMSCROLL", "action": "REPLACE", "positive_replacement": "Take six breaths."},
            "replacement_source": "calm",
        }
        updated = update_session_memory(memory, result)
        self.assertEqual(updated["items_seen"], 1)
        self.assertEqual(updated["category_counts"]["DOOMSCROLL"], 1)

    def test_build_recommendations_output_contract(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = load_content_library(CONTENT_LIBRARY_FILE)
        results = [
            {"decision": {"category": "DOOMSCROLL", "action": "REPLACE"}},
            {"decision": {"category": "RAGEBAIT", "action": "REPLACE"}},
        ]
        output = build_recommendations(results, profile, library, limit=5)
        self.assertEqual(output["dope_version"], "0.4")
        self.assertTrue(output["local_first"])
        self.assertEqual(output["profile_used"], "default")
        self.assertEqual(len(output["recommendations"]), 5)
        self.assertTrue(all(row["source"] == "local_content_library" for row in output["recommendations"]))

    def test_repeated_doomscroll_memory_changes_recommendation_mix(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = load_content_library(CONTENT_LIBRARY_FILE)
        output = build_recommendations([], profile, library, {"category_counts": {"DOOMSCROLL": 4}}, limit=3)
        targets = {row["target"] for row in output["recommendations"]}
        self.assertTrue({"calm", "constructive_news"} & targets)

    def test_repeated_ragebait_memory_changes_recommendation_mix(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = load_content_library(CONTENT_LIBRARY_FILE)
        output = build_recommendations([], profile, library, {"category_counts": {"RAGEBAIT": 4}}, limit=3)
        targets = {row["target"] for row in output["recommendations"]}
        self.assertTrue({"emotional_regulation", "civic_awareness", "learning"} & targets)

    def test_positive_history_uplift_recommends_reflective_action_in_top_five(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = load_content_library(CONTENT_LIBRARY_FILE)
        content = {"text": "A biography about an inventor shows resilience and a lesson from history."}
        decision = classify_content(content)
        self.assertEqual(decision["category"], "UPLIFT")
        self.assertIn("POSITIVE_HISTORY", decision["labels"])
        output = build_recommendations(
            [{"decision": decision}],
            profile,
            library,
            session_memory=None,
            limit=5,
        )
        top_five = output["recommendations"][:5]
        targets = {row["target"] for row in top_five}
        modes = {row["mode"] for row in top_five}
        prompts = " ".join(row["prompt"].lower() for row in top_five)
        self.assertTrue(
            {"positive_history", "gratitude"} & targets
            or {"reflect", "create", "read"} & modes
            or "real-world" in prompts
            or "action" in prompts
        )

    def test_daily_plan_has_required_sections(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = load_content_library(CONTENT_LIBRARY_FILE)
        plan = build_daily_plan(profile, library)
        self.assertEqual(plan["dope_version"], "0.4")
        self.assertTrue(plan["local_first"])
        for key in ("morning", "midday", "evening", "emergency_reset"):
            self.assertIn(key, plan)
            self.assertIsInstance(plan[key], list)

    def test_daily_plan_missing_emergency_reset_uses_warning_not_fallback_text(self) -> None:
        profile = load_profile(PROFILE_FILE)
        library = dict(load_content_library(CONTENT_LIBRARY_FILE))
        library.pop("emergency_reset", None)
        plan = build_daily_plan(profile, library)
        self.assertEqual(plan["emergency_reset"], [])
        self.assertEqual(plan["warnings"], ["missing_local_content_library_emergency_reset"])

    def test_json_cli_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "cli_audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--audit-path",
                    str(audit_path),
                    "--json",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIsInstance(payload, list)
            self.assertIn("decision", payload[0])
            self.assertIn("explanation", payload[0])
            self.assertTrue(audit_path.exists())

    def test_json_cli_with_valid_config_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "cli_audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--config",
                    str(CONTROLS_FILE),
                    "--audit-path",
                    str(audit_path),
                    "--json",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), list)
            self.assertTrue(audit_path.exists())

    def test_recommend_cli_works(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_DIR / "dope_policy_engine.py"),
                str(SAMPLE_FEED),
                "--recommend",
                "--profile",
                str(PROFILE_FILE),
            ],
            cwd=str(PROJECT_DIR),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("=== DOPE RECOMMENDATIONS ===", result.stdout)

    def test_daily_plan_cli_works(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_DIR / "dope_policy_engine.py"),
                str(SAMPLE_FEED),
                "--daily-plan",
                "--profile",
                str(PROFILE_FILE),
            ],
            cwd=str(PROJECT_DIR),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("=== DOPE DAILY PLAN ===", result.stdout)

    def test_json_recommend_cli_works(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_DIR / "dope_policy_engine.py"),
                str(SAMPLE_FEED),
                "--json",
                "--recommend",
                "--profile",
                str(PROFILE_FILE),
            ],
            cwd=str(PROJECT_DIR),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["dope_version"], "0.4")
        self.assertTrue(payload["local_first"])
        self.assertIn("recommendations", payload)

    def test_cli_smoke_test_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "cli_audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--config",
                    str(CONTROLS_FILE),
                    "--audit-path",
                    str(audit_path),
                    "--allow-spirituality",
                    "false",
                ],
                cwd=str(PROJECT_DIR),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("=== ALLOWED CONTENT ===", result.stdout)
            self.assertIn("Audit log path:", result.stdout)
            self.assertTrue(audit_path.exists())

    def test_audit_line_count_equals_feed_item_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            feed = load_feed(SAMPLE_FEED)
            engine = DopePolicyEngine(audit_path=audit_path)
            results = engine.evaluate_feed(feed)
            lines = audit_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(results), len(feed))
            self.assertEqual(len(lines), len(feed))
            for line in lines:
                record = json.loads(line)
                self.assertIn("decision", record)
                self.assertEqual(record["dope_version"], "0.4")

    def test_no_network_related_imports_are_introduced(self) -> None:
        for path in PROJECT_DIR.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for term in NETWORK_IMPORT_TERMS:
                self.assertNotIn(f"import {term}", text)
                self.assertNotIn(f"from {term}", text)


if __name__ == "__main__":
    unittest.main()

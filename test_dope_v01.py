#!/usr/bin/env python3
"""Standard-library tests for DOPE v0.2."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from dope_classifier import ACTIONS, CATEGORIES, classify_content, normalize_controls, parse_bool
from dope_policy_engine import DopePolicyEngine, load_feed, load_controls_config


PROJECT_DIR = pathlib.Path(__file__).resolve().parent
SAMPLE_FEED = PROJECT_DIR / "sample_feed.json"
CONTROLS_FILE = PROJECT_DIR / "dope_controls.json"
NETWORK_IMPORT_TERMS = ("requests", "urllib", "http.client", "socket")


class DopeV02Tests(unittest.TestCase):
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
            {
                "score",
                "confidence",
                "category",
                "labels",
                "action",
                "reason",
                "evidence",
                "positive_replacement",
            },
        )
        self.assertIsInstance(decision["score"], int)
        self.assertIn(decision["category"], CATEGORIES)
        self.assertIn(decision["action"], ACTIONS)
        self.assertIsInstance(decision["reason"], str)
        self.assertEqual(decision["positive_replacement"], "")

    def test_confidence_field_exists_and_is_0_to_1(self) -> None:
        decision = classify_content({"text": "Guaranteed profit crypto giveaway double your money."})
        self.assertIn("confidence", decision)
        self.assertGreaterEqual(decision["confidence"], 0.0)
        self.assertLessEqual(decision["confidence"], 1.0)

    def test_labels_field_can_contain_multiple_categories(self) -> None:
        decision = classify_content({"text": "Learn a calm skill, then claim this guaranteed profit crypto giveaway."})
        self.assertIn("labels", decision)
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
                [
                    sys.executable,
                    str(PROJECT_DIR / "dope_policy_engine.py"),
                    str(SAMPLE_FEED),
                    "--config",
                    str(bad_config),
                ],
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

    def test_malformed_feed_items_do_not_crash_and_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            results = engine.evaluate_feed(["bad item", 123, None])
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r["audit_status"] == "written" for r in results))
            self.assertTrue(all(r["decision"]["action"] == "SOFT_WARN" for r in results))
            self.assertEqual(len(audit_path.read_text(encoding="utf-8").splitlines()), 3)

    def test_decide_content_policy_output_top_level_keys_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            result = engine.decide_content({"text": "I finished my workout and studied."}, index=0)
            self.assertEqual(
                set(result.keys()),
                {"index", "content", "decision", "audit_status", "audit_path"},
            )
            self.assertNotIn("validation_error", result)

    def test_audit_keeps_validation_error_for_malformed_feed_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            result = engine.decide_content("bad item", index=7)
            self.assertNotIn("validation_error", result)
            record = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["validation_error"], "feed_item_not_object:str")

    def test_audit_includes_dope_version_02(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = pathlib.Path(tmp) / "audit.jsonl"
            engine = DopePolicyEngine(audit_path=audit_path)
            engine.decide_content({"text": "The meeting starts at six."}, index=0)
            record = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["dope_version"], "0.2")
            self.assertTrue(record["local_first"])
            self.assertFalse(record["dark_patterns"]["outrage_optimization"])

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
                self.assertEqual(record["dope_version"], "0.2")

    def test_no_network_related_imports_are_introduced(self) -> None:
        for path in PROJECT_DIR.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for term in NETWORK_IMPORT_TERMS:
                self.assertNotIn(f"import {term}", text)
                self.assertNotIn(f"from {term}", text)


if __name__ == "__main__":
    unittest.main()

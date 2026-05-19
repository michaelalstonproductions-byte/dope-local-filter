# DOPE v0.2

DOPE means **Dopamine-Oriented Positive Environment**.

This is a local-first prototype for scoring social/media content and steering users away from dark-pattern loops while reinforcing healthier behaviors.

## Safety Rules

DOPE v0.2 does **not**:

- optimize for infinite scrolling
- optimize for outrage
- increase exposure to harmful content
- call external APIs
- call network services
- run telemetry
- upload analytics
- use addictive ranking loops

DOPE v0.2 does:

- classify locally with transparent phrase/token heuristics
- evaluate harmful categories before uplift
- log every feed item decision locally
- expose user controls through CLI flags and `dope_controls.json`
- preserve matched evidence terms and multi-label category signals
- prefer learning, creating, working, fitness, calm, family, spirituality, business progress, and emotional regulation

## Categories And Actions

Categories:

`UPLIFT`, `NEUTRAL`, `TOXIC`, `RAGEBAIT`, `DOOMSCROLL`, `SHAME`, `VIOLENCE`, `SEXUALIZED`, `SCAM`

Actions:

`ALLOW`, `SOFT_WARN`, `BLUR`, `BLOCK`, `REPLACE`

## Output Contracts

`classify_content()` in `dope_classifier.py` returns raw classifier output. v0.2 keeps the v0.1 fields and adds `confidence`, `labels`, and `evidence`:

```json
{
  "score": 0,
  "confidence": 0.0,
  "category": "NEUTRAL",
  "labels": ["NEUTRAL"],
  "action": "ALLOW",
  "reason": "...",
  "evidence": {
    "matched_phrases": [],
    "matched_tokens": [],
    "category_scores": {}
  },
  "positive_replacement": ""
}
```

`DopePolicyEngine.decide_content()` in `dope_policy_engine.py` returns policy output enriched with replacement text and audit status:

```json
{
  "index": 0,
  "content": {},
  "decision": {},
  "audit_status": "written",
  "audit_path": "/Volumes/Logic/DOPE_V01/audit/dope_audit.jsonl"
}
```

Audit records are JSONL and include local-first safety metadata:

```json
{
  "ts": "...",
  "index": 0,
  "content": {},
  "decision": {},
  "controls": {},
  "validation_error": null,
  "local_first": true,
  "dark_patterns": {
    "infinite_scroll_optimization": false,
    "outrage_optimization": false,
    "harmful_exposure_increase": false
  },
  "dope_version": "0.2"
}
```

## CLI

```bash
cd "/Volumes/Logic/DOPE_V01"
python3 dope_policy_engine.py sample_feed.json
python3 dope_policy_engine.py sample_feed.json --config dope_controls.json
python3 dope_policy_engine.py sample_feed.json --audit-path /tmp/dope_audit.jsonl
python3 dope_policy_engine.py sample_feed.json --json
```

Malformed, unreadable, or non-object config JSON exits cleanly with code `2`
and a `[DOPE CONFIG ERROR]` message on stderr. It does not print a Python
traceback.

Optional local controls:

```bash
python3 dope_policy_engine.py sample_feed.json \
  --config dope_controls.json \
  --audit-path /tmp/dope_audit.jsonl \
  --strictness high \
  --allow-spirituality true \
  --allow-business true \
  --allow-fitness true \
  --block-sexualized true \
  --block-scam true \
  --block-violence true \
  --replace-doomscroll true
```

Default controls live in `dope_controls.json`:

```json
{
  "strictness": "medium",
  "allow_spirituality": true,
  "allow_business": true,
  "allow_fitness": true,
  "block_sexualized": true,
  "block_scam": true,
  "block_violence": true,
  "replace_doomscroll": true,
  "confidence_thresholds": {
    "soft_warn": 0.35,
    "blur": 0.55,
    "block": 0.7,
    "replace": 0.5
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
    "emotional_regulation"
  ]
}
```

Audit log default:

```text
/Volumes/Logic/DOPE_V01/audit/dope_audit.jsonl
```

## Files

```text
/Volumes/Logic/DOPE_V01/dope_classifier.py
/Volumes/Logic/DOPE_V01/dope_policy_engine.py
/Volumes/Logic/DOPE_V01/dope_reinforcement_engine.py
/Volumes/Logic/DOPE_V01/dope_schema.json
/Volumes/Logic/DOPE_V01/dope_controls.json
/Volumes/Logic/DOPE_V01/sample_feed.json
/Volumes/Logic/DOPE_V01/test_dope_v01.py
/Volumes/Logic/DOPE_V01/README.md
```

## Limitations

- v0.2 uses transparent keyword and phrase heuristics only.
- Image and video understanding is limited to supplied captions/text.
- Slang, coded language, sarcasm, misspellings, and mixed-language content can bypass simple heuristics.
- Confidence is heuristic confidence, not a statistical model probability.
- This is not a personalized recommender and intentionally avoids engagement optimization.
- `__pycache__` files are generated Python bytecode and can be ignored during simple grep-based safety scans.

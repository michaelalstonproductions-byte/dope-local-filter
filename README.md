# DOPE v0.3

DOPE means **Dopamine-Oriented Positive Environment**.

DOPE v0.3 is a local-first, opt-in personal reinforcement prototype. It is not a censorship engine, propaganda engine, forced positivity engine, or live platform integration. It uses transparent phrase/token heuristics to reduce harmful attention loops while preserving useful hard news and civic awareness.

## Safety Rules

DOPE v0.3 does **not**:

- optimize for infinite scrolling
- optimize for outrage
- increase exposure to harmful content
- call external APIs
- call network services
- run telemetry
- upload analytics
- use addictive ranking loops
- block all negative news

DOPE v0.3 does:

- classify locally with transparent phrase/token heuristics
- evaluate harmful categories before uplift
- allow useful hard news when it is not ragebait or doomscroll framing
- support a local personal reinforcement profile
- log every feed item decision locally
- explain decisions in plain language
- optionally track local session patterns in a JSON file

Image and video handling is text/caption-only in v0.3. Confidence is heuristic confidence, not a model probability.

## Categories, Labels, And Actions

Primary categories remain compatible with v0.2:

`UPLIFT`, `NEUTRAL`, `TOXIC`, `RAGEBAIT`, `DOOMSCROLL`, `SHAME`, `VIOLENCE`, `SEXUALIZED`, `SCAM`

Secondary labels can add context without changing the primary category contract:

`CONSTRUCTIVE_NEWS`, `HARD_NEWS`, `POSITIVE_HISTORY`, `CIVIC_AWARENESS`

Actions:

`ALLOW`, `SOFT_WARN`, `BLUR`, `BLOCK`, `REPLACE`

## Output Contracts

`classify_content()` in `dope_classifier.py` returns raw classifier output:

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

`DopePolicyEngine.decide_content()` in `dope_policy_engine.py` returns policy output enriched with replacement text, profile context, explanations, optional session summary, and audit status:

```json
{
  "index": 0,
  "content": {},
  "decision": {},
  "profile_used": "default",
  "explanation": "...",
  "replacement_explanation": "...",
  "replacement_source": "calm",
  "session_summary": {},
  "audit_status": "written",
  "audit_path": "/Volumes/Logic/DOPE_V01/audit/dope_audit.jsonl"
}
```

`session_summary` is present when `--session-memory` is used.

Audit records are JSONL and include local-first safety metadata, profile context, explanation, session summary, and validation errors:

```json
{
  "ts": "...",
  "index": 0,
  "content": {},
  "decision": {},
  "controls": {},
  "profile": {},
  "profile_used": "default",
  "explanation": "...",
  "replacement_source": "calm",
  "session_summary": {},
  "validation_error": null,
  "local_first": true,
  "dark_patterns": {
    "infinite_scroll_optimization": false,
    "outrage_optimization": false,
    "harmful_exposure_increase": false
  },
  "dope_version": "0.3"
}
```

## CLI

```bash
cd "/Volumes/Logic/DOPE_V01"
python3 dope_policy_engine.py sample_feed.json
python3 dope_policy_engine.py sample_feed.json --config dope_controls.json
python3 dope_policy_engine.py sample_feed.json --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --config dope_controls.json --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --audit-path /tmp/dope_audit.jsonl
python3 dope_policy_engine.py sample_feed.json --json --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --session-memory /tmp/dope_session_memory.json
```

Malformed, unreadable, or non-object controls/profile JSON exits cleanly with code `2` and a `[DOPE CONFIG ERROR]` message on stderr. It does not print a Python traceback.

## Local Profile

`dope_profile.json` controls personal reinforcement preferences:

- primary goals such as learning, creating, fitness, calm, family, spirituality, business progress, and emotional regulation
- sensitive areas such as doomscrolling, ragebait, shame, and scams
- preferences for hard news, constructive news, positive history, learning, faith/spirituality, business, fitness, and family
- replacement tone and audit level

The profile is local JSON only. It is not uploaded or used to call any external service.

## Local Content Library

`dope_content_library.json` contains local replacement suggestions for:

`learning`, `creating`, `working`, `fitness`, `calm`, `family`, `spirituality`, `business_progress`, `emotional_regulation`, `positive_history`, `constructive_news`, `civic_awareness`, `gratitude`, and `discipline`.

## Session Memory

`dope_session_memory.py` can track local session patterns when `--session-memory` is provided:

```json
{
  "dope_version": "0.3",
  "session_started_at": "...",
  "items_seen": 0,
  "category_counts": {},
  "action_counts": {},
  "replacement_counts": {},
  "dominant_risk": "",
  "positive_targets_served": {},
  "last_replacements": [],
  "local_first": true
}
```

Session memory is a local JSON file. No external storage is used.

## Files

```text
/Volumes/Logic/DOPE_V01/dope_classifier.py
/Volumes/Logic/DOPE_V01/dope_policy_engine.py
/Volumes/Logic/DOPE_V01/dope_reinforcement_engine.py
/Volumes/Logic/DOPE_V01/dope_session_memory.py
/Volumes/Logic/DOPE_V01/dope_explain.py
/Volumes/Logic/DOPE_V01/dope_schema.json
/Volumes/Logic/DOPE_V01/dope_controls.json
/Volumes/Logic/DOPE_V01/dope_profile.json
/Volumes/Logic/DOPE_V01/dope_content_library.json
/Volumes/Logic/DOPE_V01/sample_feed.json
/Volumes/Logic/DOPE_V01/test_dope_v01.py
/Volumes/Logic/DOPE_V01/README.md
```

## Limitations

- v0.3 uses transparent keyword and phrase heuristics only.
- Image and video understanding is limited to supplied captions/text.
- Slang, coded language, sarcasm, misspellings, and mixed-language content can bypass simple heuristics.
- Confidence is heuristic confidence, not a statistical model probability.
- Session memory is local and simple; it is not a learned model.
- DOPE intentionally avoids engagement optimization and live social platform APIs.
- `__pycache__` files are generated Python bytecode and can be ignored during simple grep-based safety scans.

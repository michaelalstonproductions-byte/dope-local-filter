# DOPE v0.5

DOPE means **Dopamine-Oriented Positive Environment**.

DOPE v0.5 is a local-first, opt-in personal reinforcement and positive content recommendation prototype prepared for mobile integration. It is not censorship, propaganda, forced positivity, medical treatment, or a live platform integration. It uses transparent local heuristics and a local content library to help users replace harmful attention loops with healthy, interesting, constructive alternatives.

## V0.5 Mobile-Ready Additions

- Stable engine API in `dope_engine.py`
- Local bundle helpers in `dope_bundle.py`
- Mobile JSON contract in `dope_mobile_contract.json`
- Mode presets in `dope_modes.json`
- Demo mobile feed in `demo_mobile_feed.json`
- iOS, browser-extension, and local-first safety guides in `docs/`
- CLI support for `--bundle`, `--mode`, and `--mobile-json`

## Safety Rules

DOPE v0.5 does **not**:

- optimize for infinite scrolling
- optimize for outrage
- increase exposure to harmful content
- call external APIs
- call network services
- run telemetry
- upload analytics
- use addictive ranking loops
- block all negative news
- claim medical treatment or forced brain rewiring

DOPE v0.5 does:

- classify locally with transparent phrase/token heuristics
- evaluate harmful categories before uplift
- allow useful hard news when it is not ragebait or doomscroll framing
- recommend from `dope_content_library.json` only
- prioritize user goals and session health over novelty or engagement
- support a local personal reinforcement profile
- log every feed item decision locally
- optionally track local session patterns in a JSON file

Image and video handling is text/caption-only. Confidence is heuristic confidence, not a model probability.

## Categories, Labels, And Actions

Primary categories remain compatible with v0.2/v0.3:

`UPLIFT`, `NEUTRAL`, `TOXIC`, `RAGEBAIT`, `DOOMSCROLL`, `SHAME`, `VIOLENCE`, `SEXUALIZED`, `SCAM`

Secondary labels add context without changing the primary category contract:

`CONSTRUCTIVE_NEWS`, `HARD_NEWS`, `POSITIVE_HISTORY`, `CIVIC_AWARENESS`

Actions:

`ALLOW`, `SOFT_WARN`, `BLUR`, `BLOCK`, `REPLACE`

## CLI

```bash
cd "/Volumes/Logic/DOPE_V01"
python3 dope_policy_engine.py sample_feed.json
python3 dope_policy_engine.py sample_feed.json --config dope_controls.json
python3 dope_policy_engine.py sample_feed.json --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --session-memory /tmp/dope_session_memory.json
python3 dope_policy_engine.py sample_feed.json --recommend --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --recommend --session-memory /tmp/dope_session_memory.json
python3 dope_policy_engine.py sample_feed.json --daily-plan --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --json --recommend --profile dope_profile.json
python3 dope_policy_engine.py sample_feed.json --json --daily-plan --profile dope_profile.json
python3 dope_policy_engine.py demo_mobile_feed.json --mobile-json
python3 dope_policy_engine.py demo_mobile_feed.json --bundle /tmp/dope_bundle.json
python3 dope_policy_engine.py demo_mobile_feed.json --mode parent_guardian
python3 dope_policy_engine.py demo_mobile_feed.json --mode creator_focus --json
```

Malformed, unreadable, or non-object controls/profile JSON exits cleanly with code `2` and a `[DOPE CONFIG ERROR]` message on stderr. It does not print a Python traceback.

## Classifier Output

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

## Policy Output

`DopePolicyEngine.decide_content()` returns policy output enriched with replacement text, profile context, explanations, optional session summary, and audit status:

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

## Recommendation Mode

`--recommend` evaluates the feed locally, then builds recommendations from `dope_content_library.json` only:

```json
{
  "dope_version": "0.5",
  "profile_used": "default",
  "generated_at": "...",
  "local_first": true,
  "recommendations": [
    {
      "rank": 1,
      "target": "constructive_news",
      "title": "...",
      "prompt": "...",
      "why": "...",
      "recommended_after": ["DOOMSCROLL"],
      "time_cost": "5_min",
      "mode": "read",
      "source": "local_content_library"
    }
  ],
  "avoidance_summary": {
    "dominant_risk": "DOOMSCROLL",
    "blocked_or_replaced_count": 0,
    "reason": "..."
  }
}
```

## Mobile JSON Mode

`--mobile-json` emits one mobile-ready object:

```json
{
  "dope_version": "0.5",
  "local_first": true,
  "results": [],
  "recommendations": {},
  "daily_plan": {},
  "session_summary": {}
}
```

## Local Bundle Format

`dope_bundle.py` reads and writes local bundles:

```json
{
  "dope_version": "0.5",
  "controls": {},
  "profile": {},
  "content_library": {},
  "session_memory": {},
  "local_first": true
}
```

Bundles are for local mobile/browser-extension integration. They are not uploaded by DOPE.

Malformed bundle JSON fails cleanly with exit code `2` and a stderr message beginning
with `[DOPE BUNDLE ERROR]`. A traceback is not expected for malformed JSON,
unreadable bundle files, or bundle JSON that is not an object.

## Mode Presets

`dope_modes.json` includes:

`default`, `parent_guardian`, `creator_focus`, `student_learning`, `business_builder`, `fitness_recovery`, `faith_family`

Ranking is not engagement ranking. It gives priority to:

- profile goals
- repeated local session risks
- short, non-overwhelming actions
- constructive replacements after harmful categories

Examples:

- repeated `DOOMSCROLL` -> calm, constructive news, civic awareness, and practical action
- repeated `RAGEBAIT` -> emotional regulation, learning, and civic awareness
- repeated `SHAME` -> calm, fitness, gratitude, and one tiny action
- `SCAM` -> verification habits and business discipline, not finance hype
- `UPLIFT` or `POSITIVE_HISTORY` -> reinforce and suggest real-world follow-through

## Daily Plan Mode

`--daily-plan` creates a simple local plan:

```json
{
  "dope_version": "0.5",
  "profile_used": "default",
  "generated_at": "...",
  "local_first": true,
  "morning": [],
  "midday": [],
  "evening": [],
  "emergency_reset": [],
  "recommended_limits": {
    "doomscroll_replacements": 5,
    "ragebait_replacements": 5,
    "shame_replacements": 5
  }
}
```

The plan is intentionally small and local. It is not medical advice.

## Local Profile

`dope_profile.json` controls personal reinforcement preferences:

- primary goals such as learning, creating, fitness, calm, family, spirituality, business progress, and emotional regulation
- sensitive areas such as doomscrolling, ragebait, shame, and scams
- preferences for hard news, constructive news, positive history, learning, faith/spirituality, business, fitness, and family
- replacement tone and audit level

The profile is local JSON only. It is not uploaded or used to call any external service.

## Local Content Library

`dope_content_library.json` contains local replacement suggestions for:

`learning`, `creating`, `working`, `fitness`, `calm`, `family`, `spirituality`, `business_progress`, `emotional_regulation`, `positive_history`, `constructive_news`, `civic_awareness`, `gratitude`, `discipline`, and `emergency_reset`.

No external links are required.

## Session Memory

`dope_session_memory.py` can track local session patterns when `--session-memory` is provided:

```json
{
  "dope_version": "0.5",
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

Session memory is a local JSON file. No external storage is used. Malformed memory values are sanitized back into safe counters.

## Audit Records

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
  "dope_version": "0.5"
}
```

## Files

```text
/Volumes/Logic/DOPE_V01/dope_classifier.py
/Volumes/Logic/DOPE_V01/dope_policy_engine.py
/Volumes/Logic/DOPE_V01/dope_reinforcement_engine.py
/Volumes/Logic/DOPE_V01/dope_session_memory.py
/Volumes/Logic/DOPE_V01/dope_explain.py
/Volumes/Logic/DOPE_V01/dope_recommender.py
/Volumes/Logic/DOPE_V01/dope_daily_plan.py
/Volumes/Logic/DOPE_V01/dope_engine.py
/Volumes/Logic/DOPE_V01/dope_bundle.py
/Volumes/Logic/DOPE_V01/dope_schema.json
/Volumes/Logic/DOPE_V01/dope_recommendation_schema.json
/Volumes/Logic/DOPE_V01/dope_mobile_contract.json
/Volumes/Logic/DOPE_V01/dope_controls.json
/Volumes/Logic/DOPE_V01/dope_profile.json
/Volumes/Logic/DOPE_V01/dope_modes.json
/Volumes/Logic/DOPE_V01/dope_content_library.json
/Volumes/Logic/DOPE_V01/sample_feed.json
/Volumes/Logic/DOPE_V01/demo_mobile_feed.json
/Volumes/Logic/DOPE_V01/test_dope_v01.py
/Volumes/Logic/DOPE_V01/README.md
```

## Limitations

- v0.5 uses transparent keyword and phrase heuristics only.
- Recommendations are local suggestions, not predictions of what will make content engaging.
- Image and video understanding is limited to supplied captions/text.
- Slang, coded language, sarcasm, misspellings, and mixed-language content can bypass simple heuristics.
- Confidence is heuristic confidence, not a statistical model probability.
- Session memory is local and simple; it is not a learned model.
- DOPE intentionally avoids engagement optimization and live social platform APIs.

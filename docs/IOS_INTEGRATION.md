# DOPE v0.5 iOS Integration Guide

DOPE v0.5 is designed as a local engine that an iOS app can call through a bundled Python runtime, a native port, or a thin local process during development. The mobile contract is JSON-first so the same data shape can be used from Swift.

## Local-Only Flow

1. Store a DOPE bundle on device.
2. Send content text or captions to the local engine.
3. Read decisions, recommendations, daily plan, and session summary from the JSON response.
4. Show explanations and user controls in the app UI.
5. Never upload profile, controls, session memory, or feed text unless the user explicitly exports it.

## Swift Shape

Use `dope_mobile_contract.json` as the source contract. The mobile response includes:

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

## Recommended UI Principles

- Make DOPE opt-in.
- Let users inspect and edit profile/mode settings.
- Show why content was warned, blurred, replaced, or allowed.
- Do not hide all negative news.
- Do not rank for engagement, outrage, or time-on-screen.
- Keep audit logs local unless the user exports them.

## Suggested Swift Calls

During development, call:

```bash
python3 dope_policy_engine.py demo_mobile_feed.json --mobile-json
```

For production, port the transparent rules or call a local embedded runtime. Do not add live social APIs, telemetry, OAuth, or analytics upload by default.

# DOPE v0.5 Browser Extension Integration Guide

DOPE can be used by a browser extension as a local healthy-attention layer. The extension should pass visible text/captions to a local engine and receive decisions plus recommended replacements.

## Local-First Extension Pattern

1. Content script extracts visible post text or video captions.
2. Extension sends text to a local-only DOPE engine or bundled rules module.
3. DOPE returns a decision, explanation, replacement source, recommendations, and daily plan.
4. Extension applies user-selected UI behavior: allow, warn, blur, block, or replace.
5. Audit logs remain on the user device.

## Do Not Add By Default

- remote moderation APIs
- social posting APIs
- telemetry
- OAuth
- analytics upload
- engagement ranking
- automatic censorship of all negative news

## User Controls

Expose mode presets from `dope_modes.json`:

- default
- parent_guardian
- creator_focus
- student_learning
- business_builder
- fitness_recovery
- faith_family

Users should be able to turn DOPE off, inspect matched evidence terms, and edit local profile preferences.

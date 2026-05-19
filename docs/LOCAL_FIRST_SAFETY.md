# DOPE v0.5 Local-First Safety Notes

DOPE is an opt-in healthy attention layer. It is not censorship, propaganda, forced positivity, or medical treatment.

## Safety Guarantees

- No network calls.
- No external APIs.
- No telemetry.
- No analytics upload.
- No OAuth or social auth.
- No social posting APIs.
- No infinite-scroll optimization.
- No outrage optimization.
- No harmful exposure-increasing ranking.
- No addictive novelty ranking.

## Hard News Policy

DOPE should not block useful negative news by default. Factual hard news and civic information can be allowed or softly warned when it is constructive and not ragebait or doomscroll framing.

## Data Handling

Local data includes:

- controls
- profile
- content library
- session memory
- audit logs

This data should remain on device unless the user explicitly exports it.

## Mobile Bundle

`dope_bundle.py` provides a local bundle shape:

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

The bundle is a local file format for iOS, browser-extension, or companion-app integration.

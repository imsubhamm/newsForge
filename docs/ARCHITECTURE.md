# Architecture notes

See the root README for the current MVP architecture.

The important rule: **AI reasons, Remotion/FFmpeg render.**

```
script + voice + footage
        ↓
transcription / alignment / footage analysis   (AI + media tools)
        ↓
timeline.json                                  (strict schema)
        ↓
Remotion template + FFmpeg                     (deterministic 1080×1920 MP4)
```

No social publishing in v1.

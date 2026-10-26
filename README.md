# ClipCanary for AI coding assistants

One skill that teaches your coding assistant the [ClipCanary](https://clipcanary.com)
video transcoding API: building jobs (MP4, HLS, DASH, WebM, GIF, audio, thumbnails),
uploading files of any size, delivering to your storage or ours, webhooks and errors.
It ships two tested helpers per language — an uploader that handles files over 5 GiB and
a webhook signature check — for Python (standard library) and Node 18+ (no packages).

## Install

| assistant | how |
|---|---|
| Claude Code | `claude plugin marketplace add ClipCanary/clipcanary-ai`, then `claude plugin install clipcanary@clipcanary` |
| Codex | `codex plugin marketplace add ClipCanary/clipcanary-ai` |
| GitHub Copilot CLI | `copilot plugin install ClipCanary/clipcanary-ai` |
| Gemini CLI | `gemini extensions install https://github.com/ClipCanary/clipcanary-ai` |
| Cursor | add `https://github.com/ClipCanary/clipcanary-ai` as a plugin |
| anything else that reads Agent Skills | copy `skills/clipcanary/` into its skills folder |

Then ask your assistant something like *"transcode uploaded videos to HLS with
ClipCanary and notify my backend when they're done"*.

You need an API key from the ClipCanary dashboard; the skill reads it from
`CLIPCANARY_API_KEY` and never asks you to paste it into code.

## What's inside

```
skills/clipcanary/
  SKILL.md                     the guide your assistant reads first
  references/                  jobs, delivery, uploads, webhooks, errors
  scripts/                     clipcanary_upload.py, clipcanary_webhook.py,
                               clipcanary-upload.mjs, clipcanary-webhook.mjs
```

The full API reference for assistants: https://clipcanary.com/llms-full.txt.

This repository is generated from ClipCanary's own repository, where every example job is
validated against the API's schema and every helper is tested against its behaviour.
Issues and suggestions are welcome; pull requests are copied over by hand.

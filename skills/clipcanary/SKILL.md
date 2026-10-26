---
name: clipcanary
description: Integrate the ClipCanary video transcoding API into an application — submit transcoding jobs (MP4, HLS, DASH, WebM, GIF, audio, thumbnails), upload source files, deliver outputs to the user's storage or ClipCanary hosting, poll or verify webhooks, and handle errors. Use when the user wants to transcode, encode, package or stream video with ClipCanary, or mentions api.clipcanary.com.
license: MIT
metadata:
  vendor: ClipCanary
  docs: https://clipcanary.com/llms.txt
---

# ClipCanary video transcoding API

ClipCanary turns one source video into every rendition an app needs, on GPUs, through one
REST call. Use this skill to write integration code, not to guess: every shape below is
the API's own, and the full reference is one fetch away.

## Before writing code

1. **The API base URL** is `https://api.clipcanary.com`. Read it from configuration
   (e.g. `CLIPCANARY_API_BASE`) rather than hard-coding it.
2. **The key** is a secret `sk_…` from the dashboard's API keys page. Read it from the
   environment (`CLIPCANARY_API_KEY`); never put it in client-side code or a repository.
   Every request carries `Authorization: Bearer <key>`.
3. **For any field not covered here, fetch the reference** rather than inventing one:
   `https://clipcanary.com/docs-api.md` (the whole API reference as Markdown) or
   `https://clipcanary.com/llms-full.txt` (reference and tutorials). The API rejects
   unknown fields with a `400` naming them.
4. **Send a real User-Agent.** Python's bare `urllib` default is blocked at the edge with a
   plain-text `403` (`error code: 1010`); `requests`, `httpx`, `fetch` and `curl` are fine.

## The life of a job

1. `POST /v1/jobs?validate=1` — **a dry run. Do this first** while building a request: it
   runs every check the real submit does and answers `200` with `valid`, `warnings` and a
   `billable` block (what the job will bill), creating and charging nothing.
2. `POST /v1/jobs` with an `Idempotency-Key` header — answers `202` and the job (`id`,
   `state: "queued"`). A retry with the same key returns the same job instead of running
   (and billing) it twice.
3. Follow it: `GET /v1/jobs/{id}` until `state` is `completed`, `failed` or `cancelled`
   (every 5–10 s with backoff), **or** pass `webhook_url` and receive the finished job —
   see `references/webhooks.md`. `progress_percent` is 0–100.
4. Read `outputs.files` on the finished job: each file's name and size, and for hosted
   outputs a `download` path (or a `play` link for playable HLS).

`DELETE /v1/jobs/{id}` cancels; `POST /v1/jobs/{id}/resubmit` runs it again as a new job.

## A minimal job

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/source.mp4"},
    "outputs": [
      {"type": "mp4",
       "rendition": {"name": "720p", "height": 720},
       "destination": {"hosted": true}}
    ]
  }
}
```

- `input` is where the source is: `signed_url` (any HTTP(S) URL a server can GET, public or
  signed) or `upload_id` for a file uploaded to ClipCanary (`references/uploads.md`).
- `outputs` is a list; one job can make many renditions and formats at once.
- Every output needs a `destination` — see `references/delivery.md`. `{"hosted": true}`
  needs no storage of your own: ClipCanary keeps the files 24 hours behind download links.
- A job-level `destination` applies to every output that names none.

## Choosing outputs

| the app needs | output |
|---|---|
| one file that plays everywhere | `mp4` with an `h264` rendition |
| adaptive streaming for web and mobile | `hls` with a `ladder` (`default_1080p`, `default_720p`, `default_4k`) |
| DASH players | `dash` with a `ladder` |
| smaller files, modern browsers | `mp4` with `hevc` or `av1`; `webm` with `vp9` |
| a preview loop | `gif` (≤ 30 s, ≤ 1920 px wide) |
| a podcast or soundtrack | `audio` with `format` `mp3`, `m4a`, `opus`, `flac` or `wav` |
| the same streams in another container, no re-encode | `repack` to `mp4`, `mov`, `mkv`, `webm` or `ts` |
| facts about the source (duration, codecs) | `metadata` |
| scrub previews | job-level `thumbnails` with a `sprite` |

Worked jobs for each are in `references/jobs.md`.

## Rules that save a failed request

- **Validate first** (`?validate=1`) and show the user the `billable` block before
  submitting anything that costs money.
- **Use an `Idempotency-Key`** on every submit, derived from the app's own id for the work.
- **A bare `signed_put_url` holds one file.** HLS, DASH and thumbnails write many files:
  use `hosted`, a storage `connector`, a `post_policy`, or `signed_put_url` with
  `"tar": true`.
- **Webhooks are signed.** Verify every delivery before trusting it, with the helper in
  `scripts/` (`references/webhooks.md`). Deliveries can repeat; de-duplicate on `job_id`.
- **A `429` carries `Retry-After`.** The account runs 4 jobs at once by default; queue on
  the app side and retry after that many seconds.
- **Failed jobs are never billed**, and an output the source cannot support (audio from a
  silent file) is listed in `skipped`, not billed.
- **Every 4xx body is `{"detail": "<one sentence>"}`** naming the field. Show it; don't
  retry a 4xx unchanged. See `references/errors.md`.

## Files in this skill

- `references/jobs.md` — worked job payloads for each output type.
- `references/delivery.md` — destinations: hosted, playable HLS, connectors, your own URLs.
- `references/uploads.md` — sending a local file, including files over 5 GiB.
- `references/webhooks.md` — receiving and verifying the finished job.
- `references/errors.md` — every status code and what to do.
- `scripts/clipcanary_upload.py`, `scripts/clipcanary-upload.mjs` — upload a local file of
  any size and get the `input` to use. Python standard library / Node 18+ only.
- `scripts/clipcanary_webhook.py`, `scripts/clipcanary-webhook.mjs` — verify a delivery.

Copy a helper into the user's project rather than rewriting it: both are tested against
the API's own behaviour.

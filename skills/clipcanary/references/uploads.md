# Sending a local file: uploads

When the source is not already at a URL a server can GET, upload it to ClipCanary and
name it in the job. The upload is kept 24 hours, free.

**Use the helper** rather than writing this by hand — it handles both shapes below,
sends parts concurrently with retries, and finishes the upload:

- Python (standard library only): `scripts/clipcanary_upload.py`
  `source = upload_file("talk.mov", api_key)` → `{"upload_id": "up_…"}`
- Node 18+ (no packages): `scripts/clipcanary-upload.mjs`
  `const source = await uploadFile("talk.mov", apiKey)`

Then: `job["input"] = source`.

## What the helper does

1. `POST /v1/uploads` with `{"filename", "content_type", "size_bytes"}`. `size_bytes` is
   required and exact: it is signed into the upload as its `Content-Length`.
2. The answer is one of two shapes:
   - **`put_url`** (files up to 5 GiB less 5 MiB): one `PUT` of the whole file to `put_url`
     with the answer's `headers`, **verbatim** — they are part of the signature.
   - **`put_url: null` and `parts`** (bigger files): each part has `part_number`,
     `offset`, `size_bytes`, `put_url` and `headers`. `PUT` exactly `size_bytes` bytes from `offset`
     to each part's URL with its headers, in any order, several at once. Then
     `POST /v1/uploads/{upload_id}/complete` (the ticket's `complete_path`); a `409` names parts still missing — resend
     those and call it again. Calling it twice is safe.
3. The answer's `source` (`{"upload_id": "up_…"}`) goes in the job as `input` — or as an
   `overlay` or `subtitles` `source`.

## Limits and refusals

- One upload holds up to the deployment's ceiling (the ticket's `max_bytes`); over it, the
  ticket is a `413` before any bytes move.
- An account may mint 200 uploads or 100 GiB per rolling day; over either, `429` with
  `Retry-After`.
- The PUT must start within an hour of the ticket (`put_url_expires_at`); a job naming an
  upload whose bytes never arrived, or that has expired, is a `400` saying which.
- `GET /v1/uploads/{upload_id}` says whether the bytes arrived (`received`).

For a file that already lives in the app's own bucket, skip all of this: sign a GET URL
for it and send `{"input": {"signed_url": "…"}}`.

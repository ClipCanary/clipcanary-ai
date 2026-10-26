# Where the outputs go: `destination`

Every output needs one, or the job sets one at job level for all of them. Exactly one of
these shapes per destination.

| shape | when | many files (HLS, DASH, thumbnails)? |
|---|---|---|
| `{"hosted": true}` | the app has no storage, or wants a link to hand on | yes — one `.tar` per tree |
| `{"hosted": true, "playable": true}` | HLS that plays from one link, no storage needed | yes — loose files and a `play` link |
| `{"connector": "name", "path": "folder/{job}/"}` | the app's own S3, GCS or Azure bucket, saved once in the dashboard | yes — one `.tar` per tree |
| `{"signed_put_url": "https://…"}` | the app signs a PUT URL on its own bucket per file | **no** — one file only |
| `{"signed_put_url": "https://…", "tar": true}` | the same, for a tree | yes — one `.tar` |
| `{"post_policy": {"url": "…", "fields": {…}}, "prefix": "jobs/42/"}` | a GCS/S3 signed POST policy covering a prefix | yes — loose files |

## Hosted (no storage of your own)

```json
{"destination": {"hosted": true}}
```

- Kept **24 hours** from the job's finish (`hosted_until` on the job), then deleted.
- The finished job lists each file with a `download` path:
  `GET /v1/jobs/{id}/outputs/{name}` answers a `302` to a 15-minute signed URL. It needs
  the API key, so call it from the app's backend and copy the file to permanent storage
  if the app keeps it longer than a day.
- Up to 100 GiB a file. An account may make 200 GiB of hosted output per rolling day; over
  that, submits answer `429` with `Retry-After`.

## Playable HLS

```json
{"type": "hls", "ladder": "default_1080p", "destination": {"hosted": true, "playable": true}}
```

- HLS outputs only (DASH, MP4 and thumbnails are refused with `playable`).
- The job shows one entry: the master playlist, `file_count`, the total size, and `play`:
  `/v1/play/{job}/{token}/hls/master.m3u8`. Prefix the API base URL and give it to a
  player: Safari and iOS natively, hls.js or Video.js elsewhere. No key needed; anyone with
  the link can watch until `hosted_until`. Segments stream straight from storage.

## Storage connectors (the app's own bucket, by name)

The account saves a bucket once (dashboard → Connectors: S3, Google Cloud Storage or
Azure); a job then names it. ClipCanary signs a write per output at dispatch, so the job
holds no credential.

```json
{"destination": {"connector": "prod-s3", "path": "renditions/{job}/"}}
```

`path` is a folder inside the bucket; `{job}` becomes the job id. A connector the account
has not saved is a `400`.

## The app's own signed URLs

```json
{"destination": {"signed_put_url": "https://bucket.s3.amazonaws.com/out/720p.mp4?X-Amz-Signature=…"}}
```

- **Sign each URL for the exact `Content-Type` of that output** (`video/mp4`, `video/webm`,
  `application/x-tar` for `tar: true`) or the storage refuses the upload with a bare `403`.
- Give the URL enough life for the queue and the encode: hours, not minutes.
- A job-level `signed_put_url` is refused when more than one output would write to it.

Full detail, including POST policies: `https://clipcanary.com/docs-api.md`, section
"destination".

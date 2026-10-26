# Errors and what to do

Every 4xx from the API is JSON: `{"detail": "<one sentence>"}`, naming the field where
there is one. Show `detail` to the developer; do not retry a 4xx unchanged.

| status | means | do |
|---|---|---|
| 400 | the request is unusable: a missing, unknown or out-of-range field, a destination that cannot hold the output, an upload that never arrived, a connector the account has not saved | fix what `detail` names; check the field against `https://clipcanary.com/docs-api.md` |
| 401 | no key, or an unknown, revoked or expired one | check `Authorization: Bearer sk_…`; make a new key if it expired |
| 402 | the account cannot fund the job: out of credit, or free-credit jobs carrying their own `overlay` | top up in the dashboard; reads still work while suspended |
| 403, plain text `error code: 1010` | the edge's bot protection, not the API | send a real User-Agent (Python's bare `urllib` is the known trigger) |
| 404 | no such job, template or upload for this account | check the id; accounts cannot see each other's |
| 409 | an `Idempotency-Key` reused with a different body; an upload completed with parts missing (`detail` names them) | use a new key; send the missing parts and complete again |
| 410 | a hosted file or play link after `hosted_until` | the files were deleted after 24 hours; run the job again |
| 413 | an upload larger than one upload may hold | send a `signed_url` to the file in the app's own storage |
| 429 | the account's concurrent-job limit (4 by default) or a daily ceiling | wait `Retry-After` seconds, then retry |
| 503 | a feature this deployment has not enabled (uploads, hosted, playable), or its storage did not answer | use another destination or input shape, or retry |
| 5xx | ClipCanary's side | retry with backoff; jobs already accepted are not lost |

## A job that fails after it was accepted

The submit checks the whole payload, so most mistakes are a `400` and no job. What only
the machine can find — the source is missing or not a video, the app's storage refuses
the upload — ends the job `failed` with `error` in plain words. **Failed jobs are never
billed.** Machine-side problems are retried automatically (the job returns to `queued`
with `error` explaining the previous attempt) before a job is marked `failed`.

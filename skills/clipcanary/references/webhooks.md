# Finding out a job finished: webhooks or polling

## Webhooks

Pass `webhook_url` beside the job:

```json
{"job": {"input": {"signed_url": "https://example.com/in.mp4"},
         "outputs": [{"type": "mp4", "rendition": {"name": "720p", "height": 720},
                      "destination": {"hosted": true}}]},
 "webhook_url": "https://app.example.com/hooks/clipcanary"}
```

When the job reaches `completed`, `failed` or `cancelled`, ClipCanary POSTs the job object
(the same shape `GET /v1/jobs/{id}` answers, with `job_id` beside `id`) as JSON, with two
headers:

```
X-Fleet-Timestamp: 1756200046
X-Fleet-Signature: v1=9a1c…
```

**Verify every delivery before acting on it.** The signature is HMAC-SHA256, keyed with
the account's webhook secret (`whsec_…`, on the dashboard's API keys page), over
`<timestamp>.<raw body>`, hex, prefixed `v1=`. Use the **raw** request body exactly as
received — not re-serialised JSON — compare in constant time, and reject deliveries more
than 5 minutes old.

Use the helper instead of writing this:

- Python: `scripts/clipcanary_webhook.py` —
  `verify_delivery(raw_body, headers, secret)` → `True`/`False`
- Node: `scripts/clipcanary-webhook.mjs` —
  `verifyDelivery(rawBody, headers, secret)` → `true`/`false`

Framework notes: read the raw bytes before any JSON middleware parses them
(Express: `express.raw({type: "application/json"})` on that route; Flask:
`request.get_data()`; FastAPI: `await request.body()`; Django: `request.body`).

**Delivery is at least once.** Answer `2xx` within 10 seconds and do the work afterwards
(queue it). A failed delivery is retried up to 8 attempts, 30 seconds apart and doubling,
up to an hour apart. De-duplicate on `job_id`. `GET /v1/jobs/{id}` shows the delivery
state under `webhook` (`delivered`, `tries`).

## Polling

`GET /v1/jobs/{id}` every 5–10 seconds while `state` is `queued` or `running`, backing off
for long jobs. `progress_percent` is 0–100. Stop at `completed`, `failed` or `cancelled`.
A job may go back to `queued` with `error` set if a machine was lost — ClipCanary retries it
itself, up to three attempts; keep polling.

`GET /v1/jobs` lists the account's jobs, newest first, paged by time.

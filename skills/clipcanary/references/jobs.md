# Worked jobs

Each block is a complete `POST /v1/jobs` body. Send it to `?validate=1` first to check it
and see what it bills. Field ranges and every option: `https://clipcanary.com/docs-api.md`
(section "Request reference").

## An MP4 ladder into the app's own storage

Three renditions, each written to a signed PUT URL the app minted on its own bucket.
`height` alone keeps the source's aspect ratio.

```json
{
  "job": {
    "input": {"signed_url": "https://storage.example.com/uploads/talk.mov?sig=abc"},
    "outputs": [
      {"type": "mp4", "rendition": {"name": "1080p", "height": 1080},
       "destination": {"signed_put_url": "https://storage.example.com/out/1080p.mp4?sig=abc"}},
      {"type": "mp4", "rendition": {"name": "720p", "height": 720},
       "destination": {"signed_put_url": "https://storage.example.com/out/720p.mp4?sig=abc"}},
      {"type": "mp4", "rendition": {"name": "480p", "height": 480},
       "destination": {"signed_put_url": "https://storage.example.com/out/480p.mp4?sig=abc"}}
    ]
  },
  "webhook_url": "https://app.example.com/hooks/clipcanary"
}
```

## Adaptive streaming: HLS from a ladder, hosted and playable

A named ladder (`default_1080p`, `default_720p`, `default_4k`) is fitted to the source, so
a 720p source never gets an upscaled 1080p rung. `playable` gives one link a player opens.

```json
{
  "job": {
    "input": {"upload_id": "up_Qx3k9v2mP8sLwT1a"},
    "outputs": [
      {"type": "hls", "ladder": "default_1080p",
       "destination": {"hosted": true, "playable": true}}
    ]
  }
}
```

## HLS and DASH with HEVC as well as H.264

`codecs` expands the ladder once per codec. HLS and DASH write many files, so the
destination must hold a tree: here the app's own bucket through a saved storage connector.

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/film.mp4"},
    "destination": {"connector": "prod-s3", "path": "videos/{job}/"},
    "outputs": [
      {"type": "hls", "ladder": "default_1080p", "codecs": ["h264", "hevc"]},
      {"type": "dash", "ladder": "default_1080p", "codecs": ["h264", "hevc"]}
    ]
  }
}
```

## Explicit renditions with quality control

`quality` (1–100) is the usual knob; `bitrate`, `maxrate` and `bufsize` pin the rate
instead. `fps` caps the frame rate.

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/game.mp4"},
    "outputs": [
      {"type": "mp4",
       "rendition": {"name": "1080p60", "height": 1080, "codec": "h264", "fps": 60,
                     "maxrate": "8M", "bufsize": "16M"},
       "destination": {"hosted": true}},
      {"type": "mp4",
       "rendition": {"name": "1080p-av1", "height": 1080, "codec": "av1", "quality": 70},
       "destination": {"hosted": true}}
    ]
  }
}
```

## WebM, a GIF preview and an MP3

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/clip.mp4"},
    "destination": {"hosted": true},
    "outputs": [
      {"type": "webm", "rendition": {"name": "720p", "height": 720, "codec": "vp9"}},
      {"type": "gif", "start_s": 3, "duration_s": 4, "width": 480, "fps": 12},
      {"type": "audio", "format": "mp3", "bitrate": "192k", "loudnorm": true}
    ]
  }
}
```

## Repack without re-encoding, and the source's metadata

`repack` copies the streams into another container: no re-encode, no quality loss, and
billed on its own line. `metadata` with no destination answers inline on the job as `metadata`.

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/master.mkv"},
    "outputs": [
      {"type": "repack", "container": "mp4", "destination": {"hosted": true}},
      {"type": "metadata"}
    ]
  }
}
```

## Watermark, burned-in subtitles, trim and scrub thumbnails

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/lecture.mp4"},
    "trim": {"start": 12.5, "duration": 600},
    "overlay": {"source": {"signed_url": "https://example.com/logo.png"},
                "position": "top-right", "scale": 0.12, "opacity": 0.8},
    "subtitles": {"source": {"signed_url": "https://example.com/lecture.en.srt"}},
    "thumbnails": {"interval": 5, "width": 160, "sprite": {"columns": 10, "rows": 10},
                   "destination": {"hosted": true}},
    "outputs": [
      {"type": "mp4", "rendition": {"name": "720p", "height": 720},
       "destination": {"hosted": true}}
    ]
  }
}
```

## Encrypted HLS (AES-128)

ClipCanary encrypts with the app's key; players fetch the key from the app's own
`key_url`. AES-128 needs `segment_type: "mpegts"`.

```json
{
  "job": {
    "input": {"signed_url": "https://example.com/paid.mp4"},
    "outputs": [
      {"type": "hls", "ladder": "default_720p", "segment_type": "mpegts",
       "encryption": {"scheme": "aes-128", "key_hex": "000102030405060708090a0b0c0d0e0f",
                      "key_url": "https://app.example.com/keys/paid-42"},
       "destination": {"hosted": true}}
    ]
  }
}
```

## Reading the result

On `completed`, `outputs.files` lists what was written. A hosted file has a `download`
path on the API (`GET /v1/jobs/{id}/outputs/{name}`, a `302` to a fresh signed URL, needs
the key); a playable HLS output is one entry with a `play` path (no key needed) and
`file_count`. Both are relative: prefix the API base URL. Hosted files are deleted at
`hosted_until`, 24 hours after the job finished.

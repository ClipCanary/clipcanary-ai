// Upload a local file to ClipCanary and get the `input` for a job. Node 18+, no packages.
//
//   import {uploadFile} from "./clipcanary-upload.mjs";
//   job.input = await uploadFile("talk.mov", process.env.CLIPCANARY_API_KEY);
//
// Handles both answers `POST /v1/uploads` can give: one PUT for a file up to 5 GiB less
// 5 MiB, or parts (sent four at a time, each retried) and the call that joins them.
// Try it: `CLIPCANARY_API_KEY=sk_… node clipcanary-upload.mjs talk.mov`.

import {openAsBlob} from "node:fs";
import {stat} from "node:fs/promises";
import {basename, extname} from "node:path";

const API_BASE = (process.env.CLIPCANARY_API_BASE ?? "https://api.clipcanary.com").replace(/\/$/, "");
const USER_AGENT = "clipcanary-upload/1.0 (node)";
const PARTS_AT_ONCE = 4;
const ATTEMPTS = 4;
const TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska",
  ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
  ".png": "image/png", ".jpg": "image/jpeg", ".srt": "application/x-subrip", ".vtt": "text/vtt"};

export class UploadError extends Error {}

async function send(method, url, headers, body) {
  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    let answer;
    try {
      answer = await fetch(url, {method, headers: {"User-Agent": USER_AGENT, ...headers}, body,
                                 duplex: body ? "half" : undefined});
    } catch (error) {
      if (attempt === ATTEMPTS) throw new UploadError(`${method} ${url.split("?")[0]} failed: ${error.message}`);
      await new Promise((done) => setTimeout(done, Math.min(30, 2 ** attempt) * 1000));
      continue;
    }
    if (answer.ok) return answer;
    const text = await answer.text();
    if (answer.status < 500 || attempt === ATTEMPTS) {
      let detail = text;
      try { detail = JSON.parse(text).detail ?? text; } catch { /* not JSON */ }
      throw new UploadError(`${method} ${url.split("?")[0]} answered ${answer.status}: ${detail}`);
    }
    await new Promise((done) => setTimeout(done, Math.min(30, 2 ** attempt) * 1000));
  }
  throw new Error("unreachable");
}

async function api(method, path, apiKey, payload) {
  const headers = {"Authorization": `Bearer ${apiKey}`};
  if (payload !== undefined) headers["Content-Type"] = "application/json";
  const answer = await send(method, `${API_BASE}${path}`, headers,
                            payload === undefined ? undefined : JSON.stringify(payload));
  return answer.json();
}

/** Upload `path` and return the job input for it: `{upload_id: "up_…"}`. */
export async function uploadFile(path, apiKey, contentType) {
  const size = (await stat(path)).size;
  const kind = contentType ?? TYPES[extname(path).toLowerCase()] ?? "application/octet-stream";
  const ticket = await api("POST", "/v1/uploads", apiKey,
                           {filename: basename(path), content_type: kind, size_bytes: size});
  const file = await openAsBlob(path);
  if (ticket.put_url) {
    await send("PUT", ticket.put_url, ticket.headers, file);
    return ticket.source;
  }
  const queue = [...ticket.parts];
  const worker = async () => {
    for (let part = queue.shift(); part; part = queue.shift()) {
      const piece = file.slice(part.offset, part.offset + part.size_bytes);
      await send("PUT", part.put_url, part.headers, piece);
    }
  };
  await Promise.all(Array.from({length: PARTS_AT_ONCE}, worker));
  await api("POST", ticket.complete_path ?? `/v1/uploads/${ticket.upload_id}/complete`, apiKey);
  return ticket.source;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  if (process.argv.length !== 3 || !process.env.CLIPCANARY_API_KEY) {
    console.error("usage: CLIPCANARY_API_KEY=sk_… node clipcanary-upload.mjs <file>");
    process.exit(2);
  }
  console.log(JSON.stringify(await uploadFile(process.argv[2], process.env.CLIPCANARY_API_KEY)));
}

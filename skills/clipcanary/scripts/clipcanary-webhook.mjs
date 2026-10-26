// Verify a ClipCanary webhook delivery. Node 18+, no packages.
//
//   import {verifyDelivery} from "./clipcanary-webhook.mjs";
//   app.post("/hooks/clipcanary", express.raw({type: "application/json"}), (req, res) => {
//     if (!verifyDelivery(req.body, req.headers, process.env.CLIPCANARY_WEBHOOK_SECRET)) {
//       return res.sendStatus(400);
//     }
//     res.sendStatus(200);  // acknowledge fast; queue the work
//   });
//
// `rawBody` must be the exact bytes received (a Buffer or string), never re-serialised
// JSON. `headers` may be a Node headers object or a Fetch `Headers`. The secret is the
// account's `whsec_…` from the dashboard's API keys page.

import {createHmac, timingSafeEqual} from "node:crypto";

export const TOLERANCE_S = 300;

function header(headers, name) {
  if (typeof headers?.get === "function") return headers.get(name) ?? "";
  for (const [key, value] of Object.entries(headers ?? {})) {
    if (key.toLowerCase() === name.toLowerCase()) return Array.isArray(value) ? value[0] : value;
  }
  return "";
}

/** True when the delivery is signed with `secret` and less than `toleranceS` old. */
export function verifyDelivery(rawBody, headers, secret, toleranceS = TOLERANCE_S, now = Date.now() / 1000) {
  const timestamp = header(headers, "X-Fleet-Timestamp");
  const signature = header(headers, "X-Fleet-Signature");
  if (!/^\d+$/.test(timestamp)) return false;
  if (Math.abs(now - Number(timestamp)) > toleranceS) return false;
  const body = typeof rawBody === "string" ? Buffer.from(rawBody) : Buffer.from(rawBody);
  const mac = createHmac("sha256", secret).update(`${timestamp}.`).update(body).digest("hex");
  const expected = Buffer.from(`v1=${mac}`);
  const given = Buffer.from(String(signature));
  return expected.length === given.length && timingSafeEqual(expected, given);
}

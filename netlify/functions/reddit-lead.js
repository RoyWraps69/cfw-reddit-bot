// netlify/functions/reddit-lead.js
// Called by the GitHub Actions bot when a hot Reddit lead is detected

const https = require("https");

async function sendSMS(to, body) {
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken  = process.env.TWILIO_AUTH_TOKEN;
  const from       = process.env.TWILIO_FROM_NUMBER;
  if (!accountSid || !to) return { status: "skipped" };

  return new Promise((resolve) => {
    const formData = `To=${encodeURIComponent(to)}&From=${encodeURIComponent(from)}&Body=${encodeURIComponent(body.slice(0, 1600))}`;
    const req = https.request({
      hostname: "api.twilio.com",
      path: `/2010-04-01/Accounts/${accountSid}/Messages.json`,
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": Buffer.byteLength(formData),
        Authorization: "Basic " + Buffer.from(`${accountSid}:${authToken}`).toString("base64"),
      },
    }, (res) => resolve({ status: res.statusCode === 201 ? "sent" : "error" }));
    req.on("error", (e) => resolve({ status: "error", error: e.message }));
    req.write(formData); req.end();
  });
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "Method not allowed" };

  let data = {};
  try { data = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "Bad JSON" }; }

  const level    = data.intent_level || "warm";
  const emoji    = level === "hot" ? "🔥" : "🟡";
  const platform = data.platform || "reddit";
  const username = data.username || "unknown";
  const message  = data.message_text || "";
  const vehicle  = data.vehicle_type || "";

  const smsLines = [
    `${emoji} ${level.toUpperCase()} LEAD — ${platform}`,
    `From: u/${username}`,
    vehicle ? `Vehicle: ${vehicle}` : null,
    `"${message.slice(0, 150)}"`,
    `Score: ${data.lead_score || "?"}/10`,
  ].filter(Boolean);

  await sendSMS(process.env.ROY_PHONE_NUMBER, smsLines.join("\n"));

  return { statusCode: 200, body: JSON.stringify({ status: "alerted" }) };
};

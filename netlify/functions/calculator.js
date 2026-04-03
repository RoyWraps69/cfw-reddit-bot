// netlify/functions/calculator.js
// Receives price calculator form submissions from chicagofleetwraps.com
// Fires SMS to Roy via Twilio + Slack alert + logs the lead
// Deploy: this runs automatically on Netlify when form is submitted

const https = require("https");

// ── Price ranges (mirrors your website calculator) ─────────────────
const PRICE_RANGES = {
  cargo_van:     { full: "$3,750 - $4,500", partial: "$1,800 - $2,400", lettering: "$450 - $900" },
  box_truck:     { full: "$4,500 - $6,500", partial: "$2,200 - $3,000", lettering: "$600 - $1,200" },
  pickup_truck:  { full: "$3,200 - $4,200", partial: "$1,500 - $2,200", lettering: "$400 - $800" },
  car:           { full: "$3,200 - $4,800", partial: "$1,400 - $2,000", color_change: "$3,500 - $4,500" },
  suv:           { full: "$3,500 - $5,000", partial: "$1,600 - $2,200", color_change: "$3,700 - $4,800" },
  sprinter_van:  { full: "$4,200 - $5,500", partial: "$2,000 - $2,800", lettering: "$500 - $1,000" },
  trailer:       { full: "$2,500 - $4,500", partial: "$1,200 - $2,000", lettering: "$400 - $900" },
  rivian:        { full: "$4,200 - $5,500", color_change: "$4,000 - $5,200", ppf: "$3,000 - $6,000" },
  tesla:         { full: "$3,800 - $5,000", color_change: "$3,800 - $4,800", ppf: "$2,800 - $5,500" },
};

function getPriceEstimate(vehicleType, wrapType) {
  const key = vehicleType.toLowerCase().replace(/\s+/g, "_").replace(/-/g, "_");
  for (const [k, prices] of Object.entries(PRICE_RANGES)) {
    if (key.includes(k) || k.includes(key)) {
      return prices[wrapType] || prices.full || "Contact for quote";
    }
  }
  return "Contact for custom quote";
}

// ── Twilio SMS ─────────────────────────────────────────────────────
async function sendSMS(to, body) {
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken  = process.env.TWILIO_AUTH_TOKEN;
  const from       = process.env.TWILIO_FROM_NUMBER;

  if (!accountSid || !authToken || !to) return { status: "skipped" };

  const data = JSON.stringify({
    To: to, From: from, Body: body.slice(0, 1600),
  });

  return new Promise((resolve) => {
    const req = https.request({
      hostname: "api.twilio.com",
      path: `/2010-04-01/Accounts/${accountSid}/Messages.json`,
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": Buffer.byteLength(data),
        Authorization: "Basic " + Buffer.from(`${accountSid}:${authToken}`).toString("base64"),
      },
    }, (res) => {
      resolve({ status: res.statusCode === 201 ? "sent" : "error", code: res.statusCode });
    });
    req.on("error", (e) => resolve({ status: "error", error: e.message }));
    // Encode as form data
    const formData = `To=${encodeURIComponent(to)}&From=${encodeURIComponent(from)}&Body=${encodeURIComponent(body.slice(0, 1600))}`;
    req.end(formData);
  });
}

// ── Slack ──────────────────────────────────────────────────────────
async function sendSlack(webhookUrl, payload) {
  if (!webhookUrl) return { status: "skipped" };
  const data = JSON.stringify(payload);
  return new Promise((resolve) => {
    const url = new URL(webhookUrl);
    const req = https.request({
      hostname: url.hostname, path: url.pathname + url.search,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
    }, (res) => resolve({ status: res.statusCode === 200 ? "sent" : "error" }));
    req.on("error", (e) => resolve({ status: "error", error: e.message }));
    req.write(data); req.end();
  });
}

// ── SendGrid email to Roy ──────────────────────────────────────────
async function notifyRoyEmail(lead) {
  const apiKey = process.env.SENDGRID_API_KEY;
  const royEmail = process.env.ROY_EMAIL || "roy@chicagofleetwraps.com";
  if (!apiKey) return { status: "skipped" };

  const subject = `🔥 Hot Lead — ${lead.vehicleType} (${lead.priceEstimate})`;
  const body = `New calculator lead:\n\nVehicle: ${lead.vehicleType}\nWrap type: ${lead.wrapType}\nEstimate: ${lead.priceEstimate}\n\nName: ${lead.name || "Not provided"}\nPhone: ${lead.phone || "Not provided"}\nEmail: ${lead.email || "Not provided"}\nNotes: ${lead.notes || "None"}\n\nSubmitted: ${new Date().toLocaleString("en-US", { timeZone: "America/Chicago" })} CT`;

  const data = JSON.stringify({
    personalizations: [{ to: [{ email: royEmail }] }],
    from: { email: "noreply@chicagofleetwraps.com", name: "CFW Lead Alert" },
    subject,
    content: [{ type: "text/plain", value: body }],
  });

  return new Promise((resolve) => {
    const req = https.request({
      hostname: "api.sendgrid.com", path: "/v3/mail/send", method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        "Content-Length": Buffer.byteLength(data),
      },
    }, (res) => resolve({ status: res.statusCode === 202 ? "sent" : "error", code: res.statusCode }));
    req.on("error", (e) => resolve({ status: "error", error: e.message }));
    req.write(data); req.end();
  });
}

// ── Main handler ───────────────────────────────────────────────────
exports.handler = async (event) => {
  // Allow CORS for form submissions from your website
  const headers = {
    "Access-Control-Allow-Origin": "https://chicagofleetwraps.com",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers, body: "" };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers, body: JSON.stringify({ error: "Method not allowed" }) };
  }

  let data = {};
  try {
    if (event.headers["content-type"]?.includes("application/json")) {
      data = JSON.parse(event.body || "{}");
    } else {
      // Parse URL-encoded form data
      const params = new URLSearchParams(event.body || "");
      for (const [k, v] of params) data[k] = v;
    }
  } catch (e) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: "Invalid body" }) };
  }

  const vehicleType    = data.vehicle_type || data.vehicle || "Unknown Vehicle";
  const wrapType       = data.wrap_type || "full";
  const name           = data.name || "";
  const email          = data.email || "";
  const phone          = data.phone || "";
  const notes          = data.notes || data.message || "";
  const priceEstimate  = data.estimated_price || getPriceEstimate(vehicleType, wrapType);
  const royPhone       = process.env.ROY_PHONE_NUMBER;
  const slackUrl       = process.env.SLACK_WEBHOOK_URL;

  const lead = { vehicleType, wrapType, name, email, phone, notes, priceEstimate };

  // ── Build SMS ──────────────────────────────────────────────────
  const smsLines = [
    "🔥 HOT LEAD — Calculator",
    `Vehicle: ${vehicleType} (${wrapType})`,
    `Est: ${priceEstimate}`,
  ];
  if (name)  smsLines.push(`Name: ${name}`);
  if (phone) smsLines.push(`Phone: ${phone}`);
  if (email) smsLines.push(`Email: ${email}`);
  if (notes) smsLines.push(`Notes: ${notes.slice(0, 100)}`);
  smsLines.push("Call NOW — this lead is hot.");
  const smsBody = smsLines.join("\n");

  // ── Build Slack ────────────────────────────────────────────────
  const slackPayload = {
    text: "🔥 *HOT LEAD — Price Calculator Used*",
    attachments: [{
      color: "#FF0000",
      fields: [
        { title: "Vehicle",   value: `${vehicleType} (${wrapType})`, short: true },
        { title: "Estimate",  value: priceEstimate,                  short: true },
        { title: "Name",      value: name  || "Not provided",        short: true },
        { title: "Phone",     value: phone || "Not provided",        short: true },
        { title: "Email",     value: email || "Not provided",        short: false },
        { title: "Notes",     value: notes || "None",                short: false },
      ],
      footer: "CFW Calculator Webhook",
      ts: Math.floor(Date.now() / 1000),
    }],
  };

  // ── Fire all alerts in parallel ────────────────────────────────
  const [smsResult, slackResult, emailResult] = await Promise.all([
    sendSMS(royPhone, smsBody),
    sendSlack(slackUrl, slackPayload),
    notifyRoyEmail(lead),
  ]);

  console.log("Calculator lead:", { vehicleType, priceEstimate, sms: smsResult.status, slack: slackResult.status });

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      status: "received",
      message: "Thank you! Roy will be in touch within 2 hours.",
      estimate: priceEstimate,
    }),
  };
};

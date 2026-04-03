// netlify/functions/health.js
exports.handler = async () => ({
  statusCode: 200,
  body: JSON.stringify({ status: "ok", service: "CFW Netlify Functions", time: new Date().toISOString() }),
});

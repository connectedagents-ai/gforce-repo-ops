/**
 * G Force Gripper Control Skill for OpenClaw
 * -------------------------------------------
 * Controls the physical OpenClaw gripper via the Raspberry Pi FastAPI bridge.
 * All commands are safety-validated before sending to hardware.
 */

const https = require("http");

const PI_HOST = process.env.PI_HOST || "localhost";
const PI_PORT = parseInt(process.env.PI_GRIPPER_PORT || "8080");
const MAX_FORCE = parseInt(process.env.PI_MAX_FORCE || "80");
const API_KEY = process.env.PI_GRIPPER_API_KEY || null;

async function piRequest(path, method = "GET", body = null) {
  return new Promise((resolve, reject) => {
    const bodyStr = body ? JSON.stringify(body) : null;
    const options = {
      hostname: PI_HOST,
      port: PI_PORT,
      path,
      method,
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "GForce-OpenClaw/1.0",
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
        ...(bodyStr ? { "Content-Length": Buffer.byteLength(bodyStr) } : {}),
      },
    };

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data });
        }
      });
    });

    req.on("error", (err) => {
      reject(new Error(`Cannot reach Pi at ${PI_HOST}:${PI_PORT} — ${err.message}`));
    });
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error("Gripper request timed out (10s)"));
    });

    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

async function run(action, params, context) {
  try {
    switch (action) {
      case "open":
        return await openGripper();
      case "close":
        return await closeGripper(params.force);
      case "set_force":
        return await setForce(params.force);
      case "move":
        return await moveGripper(params.position);
      case "status":
        return await getStatus();
      default:
        return (
          `Unknown gripper action: ${action}.\n` +
          `Available: open, close, set_force, move, status`
        );
    }
  } catch (err) {
    return `❌ Gripper error: ${err.message}\n\nMake sure the Raspberry Pi is online at ${PI_HOST}:${PI_PORT}`;
  }
}

async function openGripper() {
  const { status, data } = await piRequest("/open", "POST");
  if (status !== 200) return `❌ Error ${status}: ${JSON.stringify(data)}`;
  return `✅ Gripper opened fully. Position: ${data.position}%, State: ${data.state}`;
}

async function closeGripper(force) {
  const safeForce = Math.min(force || 50, MAX_FORCE);
  if (force && force > MAX_FORCE) {
    console.warn(`Force ${force}% > max ${MAX_FORCE}%, clamping to ${MAX_FORCE}%`);
  }
  const { status, data } = await piRequest("/close", "POST", { force: safeForce });
  if (status !== 200) return `❌ Error ${status}: ${JSON.stringify(data)}`;
  return `✅ Gripper closed at ${safeForce}% force. State: ${data.state}`;
}

async function setForce(force) {
  if (!force || force < 1 || force > 100) {
    return "❌ Force must be between 1 and 100";
  }
  const safeForce = Math.min(force, MAX_FORCE);
  const { status, data } = await piRequest(`/set_force/${safeForce}`, "POST");
  if (status !== 200) return `❌ Error ${status}: ${JSON.stringify(data)}`;
  return `✅ Force limit set to ${safeForce}%${force > MAX_FORCE ? ` (clamped from ${force}%)` : ""}`;
}

async function moveGripper(position) {
  if (position === undefined || position < 0 || position > 100) {
    return "❌ Position must be between 0 (closed) and 100 (fully open)";
  }
  const { status, data } = await piRequest(`/move/${position}`, "POST");
  if (status !== 200) return `❌ Error ${status}: ${JSON.stringify(data)}`;
  return `✅ Gripper at ${position}%. State: ${data.state}`;
}

async function getStatus() {
  const { status, data } = await piRequest("/status", "GET");
  if (status !== 200) return `❌ Error ${status}: ${JSON.stringify(data)}`;
  return [
    `🦾 Gripper Status:`,
    `  State:    ${data.state || "unknown"}`,
    `  Position: ${data.position ?? "?"}%`,
    `  Force:    ${data.force ?? "?"}%`,
    `  Temp:     ${data.temperature_c ?? "N/A"}°C`,
    `  Pi Host:  ${PI_HOST}:${PI_PORT}`,
  ].join("\n");
}

module.exports = { run };

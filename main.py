import asyncio
import json
import os
import random
import httpx
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ABUSEIPDB_KEY = os.getenv("ABUSEIPDB_KEY", "")

# Connected clients
clients: list[WebSocket] = []
# Country → lat/lng lookup
COUNTRY_COORDS = {
    "CN": (35.86, 104.19, "China"),
    "RU": (55.75, 37.61, "Russia"),
    "US": (38.90, -77.03, "USA"),
    "DE": (51.16, 10.45, "Germany"),
    "BR": (-14.23, -51.92, "Brazil"),
    "IN": (20.59, 78.96, "India"),
    "NL": (52.13, 5.29, "Netherlands"),
    "UA": (48.37, 31.16, "Ukraine"),
    "KR": (35.90, 127.76, "South Korea"),
    "IR": (32.42, 53.68, "Iran"),
    "FR": (46.22, 2.21, "France"),
    "VN": (14.05, 108.27, "Vietnam"),
    "BD": (23.68, 90.35, "Bangladesh"),
    "JP": (36.20, 138.25, "Japan"),
    "GB": (55.37, -3.43, "UK"),
    "TR": (38.96, 35.24, "Turkey"),
    "PK": (30.37, 69.34, "Pakistan"),
    "ID": (-0.78, 113.92, "Indonesia"),
    "TH": (15.87, 100.99, "Thailand"),
    "HK": (22.39, 114.10, "Hong Kong"),
}

TARGETS = [
    {"lat": 37.77, "lng": -122.4, "name": "US-West"},
    {"lat": 40.71, "lng": -74.0,  "name": "US-East"},
    {"lat": 51.5,  "lng": -0.12,  "name": "EU-London"},
    {"lat": 52.5,  "lng": 13.4,   "name": "EU-Frankfurt"},
    {"lat": 35.68, "lng": 139.69, "name": "AP-Tokyo"},
    {"lat": 1.35,  "lng": 103.81, "name": "AP-Singapore"},
]

CATEGORY_MAP = {
    3:  "Web Spam",
    4:  "Email Spam",
    5:  "Phishing",
    6:  "Fraud",
    7:  "DDoS",
    9:  "Open Proxy",
    10: "Web Scraper",
    11: "Exploit Attempt",
    14: "Port Scan",
    15: "Hacking",
    18: "Brute Force",
    19: "Bad Bot",
    20: "Exploit Attempt",
    21: "SQL Injection",
    22: "SSH Bruteforce",
}


def score_to_severity(score: int) -> str:
    if score >= 75:
        return "high"
    elif score >= 35:
        return "med"
    return "low"


def parse_abuseipdb_report(report: dict) -> dict | None:
    """Convert a raw AbuseIPDB report into our event format."""
    data = report.get("data", {})
    country_code = data.get("countryCode", "")
    coords = COUNTRY_COORDS.get(country_code)
    if not coords:
        return None

    lat, lng, country_name = coords
    lat += (random.random() - 0.5) * 6
    lng += (random.random() - 0.5) * 6

    target = random.choice(TARGETS)
    score = data.get("abuseConfidenceScore", 0)
    cats = data.get("categories", [])
    category = CATEGORY_MAP.get(cats[0], "Suspicious Activity") if cats else "Suspicious Activity"

    return {
        "ip": data.get("ipAddress", "0.0.0.0"),
        "srcCountry": country_name,
        "srcLat": lat,
        "srcLng": lng,
        "dstLat": target["lat"] + (random.random() - 0.5) * 1.5,
        "dstLng": target["lng"] + (random.random() - 0.5) * 1.5,
        "target": target["name"],
        "severity": score_to_severity(score),
        "category": category,
        "score": score,
        "ts": datetime.utcnow().isoformat(),
    }


async def broadcast(event: dict):
    """Send event to all connected WebSocket clients."""
    dead = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


async def fetch_abuseipdb():
    """
    Pull the AbuseIPDB blacklist endpoint.
    Free tier: 1000 requests/day — we poll every ~30s so ~2880/day,
    use the 'limit' param to stay within rate limits.
    """
    if not ABUSEIPDB_KEY:
        return []

    url = "https://api.abuseipdb.com/api/v2/blacklist"
    headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}
    params = {"confidenceMinimum": 75, "limit": 20}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            print(f"[AbuseIPDB error] {e}")
    return []


async def simulate_event():
    """Fallback demo event when no API key is set."""
    countries = list(COUNTRY_COORDS.values())
    lat, lng, country = random.choice(countries)
    target = random.choice(TARGETS)
    score = random.randint(10, 100)
    categories = list(CATEGORY_MAP.values())
    return {
        "ip": f"{random.randint(10,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        "srcCountry": country,
        "srcLat": lat + (random.random() - 0.5) * 6,
        "srcLng": lng + (random.random() - 0.5) * 6,
        "dstLat": target["lat"] + (random.random() - 0.5) * 1.5,
        "dstLng": target["lng"] + (random.random() - 0.5) * 1.5,
        "target": target["name"],
        "severity": score_to_severity(score),
        "category": random.choice(categories),
        "score": score,
        "ts": datetime.utcnow().isoformat(),
    }


async def threat_feed_loop():
    """Main loop: fetch threats and stream to clients."""
    seen_ips = set()
    poll_interval = 30  # seconds between AbuseIPDB polls

    while True:
        if ABUSEIPDB_KEY:
            print("[*] Fetching from AbuseIPDB...")
            reports = await fetch_abuseipdb()
            new_events = 0
            for report in reports:
                ip = report.get("ipAddress", "")
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)
                # Keep seen_ips from growing forever
                if len(seen_ips) > 5000:
                    seen_ips.clear()

                event = parse_abuseipdb_report({"data": report})
                if event and clients:
                    await broadcast(event)
                    new_events += 1
                    await asyncio.sleep(random.uniform(0.3, 1.2))  # stagger

            print(f"[*] Sent {new_events} new events to {len(clients)} client(s)")
            await asyncio.sleep(poll_interval)

        else:
            # Demo mode: simulate events
            if clients:
                event = await simulate_event()
                await broadcast(event)
            await asyncio.sleep(random.uniform(0.5, 1.8))


@app.on_event("startup")
async def startup():
    if not ABUSEIPDB_KEY:
        print("[!] No ABUSEIPDB_KEY found — running in simulation mode")
        print("[!] Get a free key at https://www.abuseipdb.com/register")
        print("[!] Add it to .env as: ABUSEIPDB_KEY=your_key_here")
    else:
        print(f"[+] AbuseIPDB key found — using live threat data")
    asyncio.create_task(threat_feed_loop())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print(f"[+] Client connected. Total: {len(clients)}")
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        clients.remove(websocket)
        print(f"[-] Client disconnected. Total: {len(clients)}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "clients": len(clients),
        "live_mode": bool(ABUSEIPDB_KEY),
    }

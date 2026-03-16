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

# Comprehensive Country → lat/lng lookup (180+ countries)
COUNTRY_COORDS = {
    "AF": (33.93, 67.70, "Afghanistan"),
    "AL": (41.15, 20.17, "Albania"),
    "DZ": (28.03, 1.65, "Algeria"),
    "AD": (42.54, 1.60, "Andorra"),
    "AO": (-11.20, 17.87, "Angola"),
    "AG": (17.06, -61.80, "Antigua"),
    "AR": (-38.42, -63.61, "Argentina"),
    "AM": (40.07, 45.04, "Armenia"),
    "AU": (-25.27, 133.77, "Australia"),
    "AT": (47.52, 14.55, "Austria"),
    "AZ": (40.14, 47.57, "Azerbaijan"),
    "BS": (25.03, -77.39, "Bahamas"),
    "BH": (26.00, 50.55, "Bahrain"),
    "BD": (23.68, 90.35, "Bangladesh"),
    "BB": (13.19, -59.54, "Barbados"),
    "BY": (53.71, 27.95, "Belarus"),
    "BE": (50.50, 4.47, "Belgium"),
    "BZ": (17.19, -88.49, "Belize"),
    "BJ": (9.31, 2.32, "Benin"),
    "BT": (27.51, 90.43, "Bhutan"),
    "BO": (-16.29, -63.59, "Bolivia"),
    "BA": (43.92, 17.67, "Bosnia"),
    "BW": (-22.33, 24.68, "Botswana"),
    "BR": (-14.23, -51.92, "Brazil"),
    "BN": (4.53, 114.73, "Brunei"),
    "BG": (42.73, 25.48, "Bulgaria"),
    "BF": (12.36, -1.53, "Burkina Faso"),
    "BI": (-3.37, 29.92, "Burundi"),
    "CV": (16.00, -24.01, "Cape Verde"),
    "KH": (12.56, 104.99, "Cambodia"),
    "CM": (3.85, 11.50, "Cameroon"),
    "CA": (56.13, -106.34, "Canada"),
    "CF": (6.61, 20.93, "Central African Rep."),
    "TD": (15.45, 18.73, "Chad"),
    "CL": (-35.67, -71.54, "Chile"),
    "CN": (35.86, 104.19, "China"),
    "CO": (4.57, -74.29, "Colombia"),
    "KM": (-11.87, 43.87, "Comoros"),
    "CG": (-0.22, 15.82, "Congo"),
    "CD": (-4.03, 21.75, "DR Congo"),
    "CR": (9.74, -83.75, "Costa Rica"),
    "HR": (45.10, 15.20, "Croatia"),
    "CU": (21.52, -77.78, "Cuba"),
    "CY": (35.13, 33.43, "Cyprus"),
    "CZ": (49.82, 15.47, "Czech Republic"),
    "DK": (56.26, 9.50, "Denmark"),
    "DJ": (11.83, 42.59, "Djibouti"),
    "DO": (18.74, -70.16, "Dominican Rep."),
    "EC": (-1.83, -78.18, "Ecuador"),
    "EG": (26.82, 30.80, "Egypt"),
    "SV": (13.79, -88.90, "El Salvador"),
    "GQ": (1.65, 10.27, "Equatorial Guinea"),
    "ER": (15.18, 39.78, "Eritrea"),
    "EE": (58.60, 25.01, "Estonia"),
    "SZ": (-26.52, 31.47, "Eswatini"),
    "ET": (9.14, 40.49, "Ethiopia"),
    "FJ": (-16.58, 179.41, "Fiji"),
    "FI": (61.92, 25.74, "Finland"),
    "FR": (46.22, 2.21, "France"),
    "GA": (-0.80, 11.61, "Gabon"),
    "GM": (13.44, -15.31, "Gambia"),
    "GE": (42.32, 43.36, "Georgia"),
    "DE": (51.16, 10.45, "Germany"),
    "GH": (7.95, -1.02, "Ghana"),
    "GR": (39.07, 21.82, "Greece"),
    "GT": (15.78, -90.23, "Guatemala"),
    "GN": (9.95, -11.24, "Guinea"),
    "GW": (11.80, -15.18, "Guinea-Bissau"),
    "GY": (4.86, -58.93, "Guyana"),
    "HT": (18.97, -72.29, "Haiti"),
    "HN": (15.20, -86.24, "Honduras"),
    "HK": (22.39, 114.10, "Hong Kong"),
    "HU": (47.16, 19.50, "Hungary"),
    "IS": (64.96, -19.02, "Iceland"),
    "IN": (20.59, 78.96, "India"),
    "ID": (-0.78, 113.92, "Indonesia"),
    "IR": (32.42, 53.68, "Iran"),
    "IQ": (33.22, 43.68, "Iraq"),
    "IE": (53.41, -8.24, "Ireland"),
    "IL": (31.05, 34.85, "Israel"),
    "IT": (41.87, 12.56, "Italy"),
    "JM": (18.11, -77.30, "Jamaica"),
    "JP": (36.20, 138.25, "Japan"),
    "JO": (30.59, 36.24, "Jordan"),
    "KZ": (48.02, 66.92, "Kazakhstan"),
    "KE": (-0.02, 37.91, "Kenya"),
    "KP": (40.34, 127.51, "North Korea"),
    "KR": (35.90, 127.76, "South Korea"),
    "KW": (29.31, 47.48, "Kuwait"),
    "KG": (41.20, 74.76, "Kyrgyzstan"),
    "LA": (19.85, 102.49, "Laos"),
    "LV": (56.88, 24.60, "Latvia"),
    "LB": (33.85, 35.86, "Lebanon"),
    "LS": (-29.61, 28.23, "Lesotho"),
    "LR": (6.43, -9.43, "Liberia"),
    "LY": (26.33, 17.22, "Libya"),
    "LI": (47.14, 9.55, "Liechtenstein"),
    "LT": (55.17, 23.88, "Lithuania"),
    "LU": (49.81, 6.13, "Luxembourg"),
    "MO": (22.19, 113.54, "Macao"),
    "MG": (-18.77, 46.87, "Madagascar"),
    "MW": (-13.25, 34.30, "Malawi"),
    "MY": (4.21, 101.97, "Malaysia"),
    "MV": (3.20, 73.22, "Maldives"),
    "ML": (17.57, -3.99, "Mali"),
    "MT": (35.94, 14.37, "Malta"),
    "MR": (21.00, -10.94, "Mauritania"),
    "MU": (-20.35, 57.55, "Mauritius"),
    "MX": (23.63, -102.55, "Mexico"),
    "MD": (47.41, 28.37, "Moldova"),
    "MC": (43.73, 7.40, "Monaco"),
    "MN": (46.86, 103.84, "Mongolia"),
    "ME": (42.71, 19.37, "Montenegro"),
    "MA": (31.79, -7.09, "Morocco"),
    "MZ": (-18.67, 35.53, "Mozambique"),
    "MM": (21.91, 95.96, "Myanmar"),
    "NA": (-22.96, 18.49, "Namibia"),
    "NP": (28.39, 84.12, "Nepal"),
    "NL": (52.13, 5.29, "Netherlands"),
    "NZ": (-40.90, 174.88, "New Zealand"),
    "NI": (12.86, -85.21, "Nicaragua"),
    "NE": (17.61, 8.08, "Niger"),
    "NG": (9.08, 8.67, "Nigeria"),
    "MK": (41.61, 21.74, "North Macedonia"),
    "NO": (60.47, 8.47, "Norway"),
    "OM": (21.51, 55.92, "Oman"),
    "PK": (30.37, 69.34, "Pakistan"),
    "PA": (8.54, -80.78, "Panama"),
    "PG": (-6.31, 143.95, "Papua New Guinea"),
    "PY": (-23.44, -58.44, "Paraguay"),
    "PE": (-9.19, -75.02, "Peru"),
    "PH": (12.88, 121.77, "Philippines"),
    "PL": (51.92, 19.14, "Poland"),
    "PT": (39.40, -8.22, "Portugal"),
    "QA": (25.35, 51.18, "Qatar"),
    "RO": (45.94, 24.97, "Romania"),
    "RU": (55.75, 37.61, "Russia"),
    "RW": (-1.94, 29.87, "Rwanda"),
    "SA": (23.88, 45.08, "Saudi Arabia"),
    "SN": (14.50, -14.45, "Senegal"),
    "RS": (44.02, 21.01, "Serbia"),
    "SL": (8.46, -11.78, "Sierra Leone"),
    "SG": (1.35, 103.82, "Singapore"),
    "SK": (48.67, 19.70, "Slovakia"),
    "SI": (46.15, 14.99, "Slovenia"),
    "SO": (5.15, 46.20, "Somalia"),
    "ZA": (-30.56, 22.94, "South Africa"),
    "SS": (4.86, 31.57, "South Sudan"),
    "ES": (40.46, -3.75, "Spain"),
    "LK": (7.87, 80.77, "Sri Lanka"),
    "SD": (12.86, 30.22, "Sudan"),
    "SR": (3.92, -56.03, "Suriname"),
    "SE": (60.13, 18.64, "Sweden"),
    "CH": (46.82, 8.23, "Switzerland"),
    "SY": (34.80, 38.99, "Syria"),
    "TW": (23.70, 120.96, "Taiwan"),
    "TJ": (38.86, 71.28, "Tajikistan"),
    "TZ": (-6.37, 34.89, "Tanzania"),
    "TH": (15.87, 100.99, "Thailand"),
    "TL": (-8.87, 125.73, "Timor-Leste"),
    "TG": (8.62, 0.82, "Togo"),
    "TT": (10.69, -61.22, "Trinidad & Tobago"),
    "TN": (33.89, 9.54, "Tunisia"),
    "TR": (38.96, 35.24, "Turkey"),
    "TM": (38.97, 59.56, "Turkmenistan"),
    "UG": (1.37, 32.29, "Uganda"),
    "UA": (48.37, 31.16, "Ukraine"),
    "AE": (23.42, 53.85, "UAE"),
    "GB": (55.37, -3.43, "UK"),
    "US": (38.90, -77.03, "USA"),
    "UY": (-32.52, -55.77, "Uruguay"),
    "UZ": (41.38, 64.59, "Uzbekistan"),
    "VE": (6.42, -66.59, "Venezuela"),
    "VN": (14.05, 108.27, "Vietnam"),
    "YE": (15.55, 48.52, "Yemen"),
    "ZM": (-13.13, 27.85, "Zambia"),
    "ZW": (-19.01, 29.15, "Zimbabwe"),
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
    data = report.get("data", {})
    country_code = data.get("countryCode", "")
    coords = COUNTRY_COORDS.get(country_code)

    if coords:
        lat, lng, country_name = coords
        lat += (random.random() - 0.5) * 6
        lng += (random.random() - 0.5) * 6
    else:
        lat = random.uniform(-55, 70)
        lng = random.uniform(-150, 150)
        country_name = country_code if country_code else "Unknown"
        print(f"[!] Unknown country code: '{country_code}' — using fallback coords")

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
    dead = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


async def fetch_abuseipdb():
    if not ABUSEIPDB_KEY:
        return []

    url = "https://api.abuseipdb.com/api/v2/blacklist"
    headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}
    params = {"confidenceMinimum": 75, "limit": 50}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                reports = data.get("data", [])
                if reports:
                    country_codes = [r.get("countryCode", "??") for r in reports[:10]]
                    print(f"[DEBUG] Sample country codes: {country_codes}")
                return reports
            else:
                print(f"[AbuseIPDB] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[AbuseIPDB error] {e}")
    return []


async def simulate_event():
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
    seen_ips = set()
    poll_interval = 30

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
                if len(seen_ips) > 5000:
                    seen_ips.clear()

                event = parse_abuseipdb_report({"data": report})
                if event and clients:
                    await broadcast(event)
                    new_events += 1
                    await asyncio.sleep(random.uniform(0.3, 1.2))

            print(f"[*] Sent {new_events} new events to {len(clients)} client(s)")
            await asyncio.sleep(poll_interval)

        else:
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
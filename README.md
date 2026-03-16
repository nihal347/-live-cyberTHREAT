# live cyberTHREAT — Live Global Cyberattack Map

Real-time cyberattack visualization. Browser dashboard + Python WebSocket backend.

## Quick Start (Demo Mode — no API key needed)

1. Open `index.html` directly in your browser. It runs in demo mode with simulated attacks out of the box.

## Full Setup (Live Data)

### 1. Install dependencies
```bash
pip install fastapi uvicorn httpx python-dotenv websockets
```

### 2. Get a free AbuseIPDB API key
Sign up at https://www.abuseipdb.com/register (free tier = 1000 req/day)

### 3. Create a .env file
```
ABUSEIPDB_KEY=your_key_here
```

### 4. Run the backend
```bash
uvicorn main:app --reload
```

### 5. Open the dashboard
Open `index.html` in your browser. Change `DEMO_MODE = true` to `DEMO_MODE = false` at the top of the script in `index.html`.

## What it shows
- Animated attack arcs from source country → target data center
- Live threat feed with IP, category, severity, and confidence score
- Top attacker countries leaderboard
- Stats: total threats, unique IPs, countries, rate per minute

## Upgrading
- Add Shodan API for more data sources
- Add sound alerts for high-severity events
- Deploy backend to a VPS and keep it running 24/7
- Add a time-series chart of attack volume

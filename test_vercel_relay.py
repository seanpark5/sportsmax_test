import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SYDNEY_TZ = ZoneInfo("Australia/Sydney")
RELAY_URL = os.environ.get(
    "SPORTSMAX_PROXY_URL",
    "https://www.courtscouter.com/api/internal/sportsmax",
).strip()
SECRET = os.environ.get("SPORTSMAX_PROXY_SECRET", "").strip()

def main():
    today = datetime.now(SYDNEY_TZ).date().isoformat()

    print("=== SportsMax Vercel relay test ===", flush=True)
    print(f"date={today}", flush=True)
    print(f"relay={RELAY_URL}", flush=True)

    if not SECRET:
        raise RuntimeError("SPORTSMAX_PROXY_SECRET is missing")

    response = requests.get(
        RELAY_URL,
        params={"date": today},
        headers={
            "Authorization": f"Bearer {SECRET}",
            "Accept": "application/json",
        },
        timeout=45,
    )

    print(f"HTTP {response.status_code}", flush=True)
    print("BODY:", response.text[:2500], flush=True)

    if response.status_code != 200:
        raise RuntimeError(f"Relay HTTP {response.status_code}")

    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Relay returned ok=false: {payload}")

    sessions = payload.get("sessions") or {}
    groups = sessions.get("ResourceGroups") or []
    resources = sessions.get("Resources") or []

    pricing_count = 0
    for resource in resources:
        for day in resource.get("Days", []) or []:
            for item in day.get("Sessions", []) or []:
                if str(item.get("Name") or "").lower() == "pricing":
                    pricing_count += 1

    print(f"ResourceGroups={len(groups)}", flush=True)
    print(f"Resources={len(resources)}", flush=True)
    print(f"PricingSessions={pricing_count}", flush=True)
    print("✅ VERCEL RELAY TEST SUCCEEDED", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"❌ VERCEL RELAY TEST FAILED: {type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

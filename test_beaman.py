import time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

BASE = "https://clubspark.au"
BOOKING_URL = f"{BASE}/sportsmax/Booking/BookByDate"
SETTINGS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetSettings"
SESSIONS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetVenueSessions"

BEAMAN_ID = "fb825473-257b-4951-91d9-f3ce04657284"
SYDNEY_TZ = ZoneInfo("Australia/Sydney")

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": BOOKING_URL,
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}

def do_get(session, url, params):
    response = session.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    print(f"HTTP {response.status_code} {response.url}", flush=True)
    print("BODY:", response.text[:1200], flush=True)
    return response

def main():
    today = datetime.now(SYDNEY_TZ).date().isoformat()
    print("=== Beaman Park standalone Render test ===", flush=True)
    print(f"date={today}", flush=True)

    s = requests.Session()
    stamp = int(time.time() * 1000)

    print("\n1) GetSettings", flush=True)
    r = do_get(s, SETTINGS_URL, {"_": stamp})
    if r.status_code != 200:
        raise RuntimeError(f"GetSettings HTTP {r.status_code}")

    settings = r.json()
    print(f"VenueID={settings.get('VenueID')}", flush=True)
    print(f"IsAuthenticated={settings.get('IsAuthenticated')}", flush=True)
    print(f"MustAuthenticate={settings.get('MustAuthenticate')}", flush=True)

    print("\n2) Beaman-only GetVenueSessions", flush=True)
    r = do_get(
        s,
        SESSIONS_URL,
        {
            "resourceID": BEAMAN_ID,
            "startDate": today,
            "endDate": today,
            "roleId": "",
            "_": stamp + 1,
        },
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"Beaman GetVenueSessions HTTP {r.status_code}"
        )

    payload = r.json()
    groups = payload.get("ResourceGroups") or []
    resources = payload.get("Resources") or []

    print(f"ResourceGroups={len(groups)}", flush=True)
    print(f"Resources={len(resources)}", flush=True)

    pricing = 0
    for resource in resources:
        for day in resource.get("Days", []) or []:
            for item in day.get("Sessions", []) or []:
                if str(item.get("Name") or "").lower() == "pricing":
                    pricing += 1

    print(f"PricingSessions={pricing}", flush=True)
    print("✅ BEAMAN TEST SUCCEEDED", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"❌ BEAMAN TEST FAILED: {type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

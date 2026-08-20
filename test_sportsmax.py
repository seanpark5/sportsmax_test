import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

BASE = "https://clubspark.au"
BOOKING_URL = f"{BASE}/sportsmax/Booking/BookByDate"
SETTINGS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetSettings"
SESSIONS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetVenueSessions"

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

TIMEOUT = 30


def get_json(session, url, params):
    response = session.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    print(
        f"HTTP {response.status_code} "
        f"{response.url}",
        flush=True,
    )

    text = response.text

    if response.status_code != 200:
        print(
            "BODY:",
            text[:1000],
            flush=True,
        )
        raise RuntimeError(
            f"HTTP {response.status_code}"
        )

    try:
        return response.json()
    except Exception:
        print(
            "NON-JSON BODY:",
            text[:1000],
            flush=True,
        )
        raise


def main():
    today = datetime.now(
        SYDNEY_TZ
    ).date().isoformat()

    print(
        "=== SportsMax standalone Render test ===",
        flush=True,
    )
    print(f"date={today}", flush=True)
    print(f"booking_page={BOOKING_URL}", flush=True)

    session = requests.Session()

    stamp = int(time.time() * 1000)

    print("\n1) GetSettings", flush=True)

    settings = get_json(
        session,
        SETTINGS_URL,
        {
            "_": stamp,
        },
    )

    print(
        f"VenueID={settings.get('VenueID')}",
        flush=True,
    )
    print(
        f"MustAuthenticate={settings.get('MustAuthenticate')}",
        flush=True,
    )

    print("\n2) GetVenueSessions", flush=True)

    payload = get_json(
        session,
        SESSIONS_URL,
        {
            "resourceID": "",
            "startDate": today,
            "endDate": today,
            "roleId": "",
            "_": stamp + 1,
        },
    )

    groups = payload.get("ResourceGroups", []) or []
    resources = payload.get("Resources", []) or []

    print(
        f"ResourceGroups={len(groups)}",
        flush=True,
    )
    print(
        f"Resources={len(resources)}",
        flush=True,
    )

    group_names = [
        g.get("Name")
        for g in groups
        if g.get("Name")
    ]

    print(
        f"Groups={group_names}",
        flush=True,
    )

    pricing_count = 0

    for resource in resources:
        for day in resource.get("Days", []) or []:
            for session_obj in day.get("Sessions", []) or []:
                if (
                    str(
                        session_obj.get("Name") or ""
                    ).lower()
                    == "pricing"
                ):
                    pricing_count += 1

    print(
        f"PricingSessions={pricing_count}",
        flush=True,
    )

    print(
        "\n✅ SPORTSMAX TEST SUCCEEDED",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"\n❌ SPORTSMAX TEST FAILED: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE = "https://clubspark.au"
BOOKING_URL = f"{BASE}/sportsmax/Booking/BookByDate"
SETTINGS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetSettings"
SESSIONS_URL = f"{BASE}/v0/VenueBooking/sportsmax/GetVenueSessions"

BEAMAN_GROUP_ID = "fb825473-257b-4951-91d9-f3ce04657284"
SYDNEY = ZoneInfo("Australia/Sydney")

EMAIL = os.environ.get("SPORTSMAX_EMAIL", "").strip()
PASSWORD = os.environ.get("SPORTSMAX_PASSWORD", "").strip()


def fmt_minutes(value):
    try:
        total = int(value)
    except Exception:
        return str(value)
    h, m = divmod(total, 60)
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


async def api_get(page, url, params):
    result = await page.evaluate(
        """async ({url, params}) => {
            const u = new URL(url);
            Object.entries(params).forEach(([k,v]) => u.searchParams.set(k, String(v)));
            const r = await fetch(u.toString(), {
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "*/*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            });
            return {status:r.status, text:await r.text()};
        }""",
        {"url": url, "params": params},
    )
    if result["status"] != 200:
        raise RuntimeError(f"{url} HTTP {result['status']}: {result['text'][:500]}")
    return json.loads(result["text"])


async def login(page):
    if not EMAIL or not PASSWORD:
        raise RuntimeError("SPORTSMAX_EMAIL / SPORTSMAX_PASSWORD missing")

    await page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1000)

    if "auth.clubspark.net" in page.url.lower():
        email = page.locator('input[name="EmailAddress"]').first
        password = page.locator('input[name="Password"]').first
        await email.wait_for(state="visible", timeout=30000)
        await password.wait_for(state="visible", timeout=30000)
        await email.fill(EMAIL)
        await password.fill(PASSWORD)

        submit = page.locator('button[type="submit"], input[type="submit"]').first
        if await submit.count():
            await submit.click()
        else:
            await password.press("Enter")

        try:
            await page.wait_for_url(
                lambda u: "clubspark.au" in u.lower() and "auth.clubspark.net" not in u.lower(),
                timeout=60000,
            )
        except Exception:
            await page.wait_for_timeout(5000)

    if "clubspark.au" not in page.url.lower():
        raise RuntimeError(f"Login did not return to clubspark.au: {page.url}")

    if "/sportsmax/" not in page.url.lower():
        await page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1000)


def inspect_beaman(payload, date_str):
    resources = payload.get("Resources") or []
    beaman = [r for r in resources if r.get("ResourceGroupID") == BEAMAN_GROUP_ID]

    print(f"\n=== {date_str} ===", flush=True)
    print(f"Beaman courts={len(beaman)}", flush=True)

    found = 0

    for r in beaman:
        court = r.get("Name") or r.get("ID")
        days = r.get("Days") or []

        court_sessions = []
        for d in days:
            for s in d.get("Sessions") or []:
                court_sessions.append((d, s))

        if not court_sessions:
            continue

        print(f"\n{court}", flush=True)

        for day, s in court_sessions:
            found += 1
            name = s.get("Name")
            start = s.get("StartTime")
            end = s.get("EndTime")
            cost = s.get("Cost")
            interval = s.get("Interval")

            parts = [
                f"name={name!r}",
                f"time={fmt_minutes(start)}-{fmt_minutes(end)}",
            ]
            if cost is not None:
                parts.append(f"cost={cost}")
            if interval is not None:
                parts.append(f"interval={interval}")

            print("  " + " | ".join(parts), flush=True)

            # Print keys for first few sessions so we can map the real schema.
            if found <= 5:
                print(f"    keys={sorted(s.keys())}", flush=True)

    if found == 0:
        print("No Beaman session objects returned.", flush=True)
    else:
        print(f"\nSession objects found for {date_str}: {found}", flush=True)

    return found


async def main():
    start = datetime.now(SYDNEY).date()
    print("=== Authenticated Beaman 11-day availability test ===", flush=True)
    print(f"start={start.isoformat()}", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = await browser.new_context(
            locale="en-AU",
            timezone_id="Australia/Sydney",
        )
        page = await context.new_page()

        try:
            await login(page)

            stamp = int(time.time() * 1000)
            settings = await api_get(page, SETTINGS_URL, {"_": stamp})
            print(
                f"IsAuthenticated={settings.get('IsAuthenticated')} "
                f"MustAuthenticate={settings.get('MustAuthenticate')}",
                flush=True,
            )

            if settings.get("IsAuthenticated") is not True:
                raise RuntimeError("Authentication failed")

            total = 0

            for offset in range(11):
                d = start + timedelta(days=offset)
                ds = d.isoformat()

                payload = await api_get(
                    page,
                    SESSIONS_URL,
                    {
                        "resourceID": BEAMAN_GROUP_ID,
                        "startDate": ds,
                        "endDate": ds,
                        "roleId": "",
                        "_": stamp + offset + 1,
                    },
                )

                total += inspect_beaman(payload, ds)
                await page.wait_for_timeout(250)

            print(f"\nTOTAL BEAMAN SESSION OBJECTS ACROSS 11 DAYS: {total}", flush=True)

            if total > 0:
                print("✅ BEAMAN COURT DATA IS BEING SCRAPED", flush=True)
            else:
                print(
                    "⚠️ API authenticated successfully but returned zero "
                    "Beaman session objects across all 11 days.",
                    flush=True,
                )

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

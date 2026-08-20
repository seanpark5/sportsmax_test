import asyncio
import json
import os
import time
from datetime import datetime
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


def fmt_minutes(total):
    total = int(total)
    h, m = divmod(total, 60)
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def hourly_price(item):
    cost = item.get("Cost")
    if cost is None:
        cost = item.get("CostFrom")
    interval = item.get("Interval")
    try:
        cost = float(cost)
        interval = float(interval)
    except (TypeError, ValueError):
        return None
    if interval <= 0:
        return None
    return round(cost * 60.0 / interval, 2)


async def fetch_json(page, url, params):
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

    print(f"HTTP {result['status']} {url}", flush=True)
    if result["status"] != 200:
        print("BODY:", result["text"][:1200], flush=True)
        raise RuntimeError(f"HTTP {result['status']}")

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
                lambda url: "clubspark.au" in url.lower()
                and "auth.clubspark.net" not in url.lower(),
                timeout=60000,
            )
        except Exception:
            await page.wait_for_timeout(5000)

    if "clubspark.au" not in page.url.lower():
        raise RuntimeError(f"Login did not return to clubspark.au: {page.url}")

    if "/sportsmax/" not in page.url.lower():
        await page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1200)


async def main():
    today = datetime.now(SYDNEY).date().isoformat()

    print("=== Authenticated Beaman availability test ===", flush=True)
    print(f"date={today}", flush=True)

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

            settings = await fetch_json(page, SETTINGS_URL, {"_": stamp})
            print(
                f"IsAuthenticated={settings.get('IsAuthenticated')} "
                f"MustAuthenticate={settings.get('MustAuthenticate')}",
                flush=True,
            )

            if settings.get("IsAuthenticated") is not True:
                raise RuntimeError("Not authenticated after login")

            payload = await fetch_json(
                page,
                SESSIONS_URL,
                {
                    "resourceID": BEAMAN_GROUP_ID,
                    "startDate": today,
                    "endDate": today,
                    "roleId": "",
                    "_": stamp + 1,
                },
            )

            resources = payload.get("Resources") or []
            beaman_resources = [
                r for r in resources
                if r.get("ResourceGroupID") == BEAMAN_GROUP_ID
            ]

            print(
                f"\nBeaman resources found: {len(beaman_resources)}",
                flush=True,
            )

            total_available = 0

            for resource in beaman_resources:
                court = resource.get("Name") or resource.get("ID")
                print(f"\n{court}", flush=True)

                court_count = 0

                for day in resource.get("Days", []) or []:
                    date_value = day.get("Date") or today

                    sessions = day.get("Sessions", []) or []

                    for item in sessions:
                        name = str(item.get("Name") or "")

                        # ClubSpark marks bookable/public availability as Pricing rows.
                        if name.lower() != "pricing":
                            continue

                        try:
                            start = int(item["StartTime"])
                            end = int(item["EndTime"])
                        except (KeyError, TypeError, ValueError):
                            continue

                        price = hourly_price(item)
                        price_text = (
                            f"${price:.2f}/hr"
                            if price is not None
                            else "price unavailable"
                        )

                        print(
                            f"  {date_value[:10]}  "
                            f"{fmt_minutes(start)}–{fmt_minutes(end)}  "
                            f"{price_text}",
                            flush=True,
                        )

                        court_count += 1
                        total_available += 1

                if court_count == 0:
                    print("  No Pricing availability rows found.", flush=True)

            print(
                f"\nTotal Beaman Pricing rows: {total_available}",
                flush=True,
            )

            # Diagnostic fallback: if there are no Pricing rows, print the
            # session names actually returned so we can adapt the parser.
            if total_available == 0:
                names = {}
                for resource in beaman_resources:
                    for day in resource.get("Days", []) or []:
                        for item in day.get("Sessions", []) or []:
                            n = str(item.get("Name") or "<blank>")
                            names[n] = names.get(n, 0) + 1

                print("\nReturned Beaman session names:", flush=True)
                if names:
                    for name, count in sorted(names.items()):
                        print(f"  {name}: {count}", flush=True)
                else:
                    print("  No session objects were returned for Beaman today.", flush=True)

            print("\n✅ BEAMAN AVAILABILITY RESPONSE PARSED", flush=True)

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(
            f"❌ BEAMAN AVAILABILITY TEST FAILED: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

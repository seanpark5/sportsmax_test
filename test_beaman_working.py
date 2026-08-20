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


def fmt_minutes(total):
    total = int(total)
    h, m = divmod(total, 60)
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def hourly_price(session):
    cost = session.get("Cost")
    interval = session.get("Interval")
    try:
        cost = float(cost)
        interval = float(interval)
    except (TypeError, ValueError):
        return None
    if interval <= 0:
        return None
    return cost * 60 / interval


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
            return {status:r.status, text:await r.text(), finalUrl:u.toString()};
        }""",
        {"url": url, "params": params},
    )
    print(f"HTTP {result['status']} {result['finalUrl']}", flush=True)
    if result["status"] != 200:
        print(result["text"][:1200], flush=True)
        raise RuntimeError(f"HTTP {result['status']}")
    return json.loads(result["text"])


async def login(page):
    if not EMAIL or not PASSWORD:
        raise RuntimeError("SPORTSMAX_EMAIL / SPORTSMAX_PASSWORD missing")

    await page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(800)

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
                lambda u: "clubspark.au" in u.lower()
                and "auth.clubspark.net" not in u.lower(),
                timeout=60000,
            )
        except Exception:
            await page.wait_for_timeout(5000)

    if "clubspark.au" not in page.url.lower():
        raise RuntimeError(f"Login failed: {page.url}")


def print_beaman(payload, requested_date):
    resources = payload.get("Resources") or []
    courts = [
        r for r in resources
        if r.get("ResourceGroupID") == BEAMAN_GROUP_ID
    ]

    print(f"\n=== {requested_date} ===", flush=True)
    print(f"Beaman courts found: {len(courts)}", flush=True)

    pricing_count = 0

    for court in courts:
        court_name = court.get("Name") or court.get("ID")
        rows = []

        for day in court.get("Days") or []:
            date_str = str(day.get("Date") or requested_date)[:10]
            for session in day.get("Sessions") or []:
                if str(session.get("Name") or "").lower() != "pricing":
                    continue

                start = session.get("StartTime")
                end = session.get("EndTime")
                if start is None or end is None:
                    continue

                hp = hourly_price(session)
                rows.append(
                    (
                        date_str,
                        fmt_minutes(start),
                        fmt_minutes(end),
                        hp,
                        session.get("Cost"),
                        session.get("Interval"),
                    )
                )

        print(f"\n{court_name}", flush=True)
        if not rows:
            print("  No available Pricing windows.", flush=True)
            continue

        for date_str, start, end, hp, cost, interval in rows:
            if hp is not None:
                price = f"${hp:.2f}/hr"
            else:
                price = f"cost={cost}, interval={interval}"

            print(
                f"  {date_str}  {start}–{end}  {price}",
                flush=True,
            )
            pricing_count += 1

    print(
        f"\nPricing windows for {requested_date}: {pricing_count}",
        flush=True,
    )
    return pricing_count


async def main():
    start = datetime.now(SYDNEY).date()

    print("=== WORKING authenticated Beaman scrape ===", flush=True)
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
                raise RuntimeError("Not authenticated")

            total = 0

            # First 3 days are enough to visually prove live scraping.
            for offset in range(3):
                date = start + timedelta(days=offset)
                ds = date.isoformat()

                # IMPORTANT:
                # The real SportsMax browser request sends resourceID BLANK.
                # Filter Beaman after receiving the full payload.
                payload = await api_get(
                    page,
                    SESSIONS_URL,
                    {
                        "resourceID": "",
                        "startDate": ds,
                        "endDate": ds,
                        "roleId": "",
                        "_": stamp + offset + 1,
                    },
                )

                total += print_beaman(payload, ds)

            print(
                f"\nTOTAL BEAMAN AVAILABLE WINDOWS: {total}",
                flush=True,
            )

            if total > 0:
                print("✅ BEAMAN COURT AVAILABILITY SCRAPED SUCCESSFULLY", flush=True)
            else:
                print(
                    "⚠️ Authenticated request worked but no Pricing windows "
                    "were returned in these 3 days.",
                    flush=True,
                )

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

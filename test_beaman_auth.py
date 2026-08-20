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

BEAMAN_ID = "fb825473-257b-4951-91d9-f3ce04657284"
SYDNEY_TZ = ZoneInfo("Australia/Sydney")

EMAIL = os.environ.get("SPORTSMAX_EMAIL", "").strip()
PASSWORD = os.environ.get("SPORTSMAX_PASSWORD", "").strip()


async def print_page(page, label):
    print(f"\n--- {label} ---", flush=True)
    print(f"url={page.url}", flush=True)
    try:
        print(f"title={await page.title()}", flush=True)
    except Exception:
        pass


async def fetch_json_same_origin(page, url, params):
    result = await page.evaluate(
        """
        async ({url, params}) => {
            const u = new URL(url);
            for (const [k, v] of Object.entries(params)) {
                u.searchParams.set(k, String(v));
            }

            const r = await fetch(u.toString(), {
                method: "GET",
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "*/*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            });

            return {
                status: r.status,
                text: await r.text()
            };
        }
        """,
        {"url": url, "params": params},
    )

    print(f"HTTP {result['status']} {url}", flush=True)
    print(f"BODY: {result['text'][:1200]}", flush=True)

    if result["status"] != 200:
        raise RuntimeError(f"HTTP {result['status']}")

    return json.loads(result["text"])


async def login(page):
    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "SPORTSMAX_EMAIL and SPORTSMAX_PASSWORD must be set in Render"
        )

    print("Opening SportsMax booking page...", flush=True)

    await page.goto(
        BOOKING_URL,
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    await page.wait_for_timeout(1000)
    await print_page(page, "after SportsMax navigation")

    # If ClubSpark redirects us to its auth host, log in there first.
    if "auth.clubspark.net" in page.url.lower():
        print("ClubSpark login required. Logging in...", flush=True)

        email = page.locator('input[name="EmailAddress"]').first
        password = page.locator('input[name="Password"]').first

        await email.wait_for(state="visible", timeout=30_000)
        await password.wait_for(state="visible", timeout=30_000)

        await email.fill(EMAIL)
        await password.fill(PASSWORD)

        remember = page.locator('input[name="RememberMe"]').first
        try:
            if await remember.count():
                checked = await remember.is_checked()
                if not checked:
                    await remember.check()
        except Exception:
            pass

        submit = page.locator(
            'button[type="submit"], input[type="submit"]'
        ).first

        if await submit.count():
            await submit.click()
        else:
            await password.press("Enter")

        # ClubSpark uses a federation redirect chain after successful login.
        try:
            await page.wait_for_url(
                lambda url: "clubspark.au" in url.lower()
                and "auth.clubspark.net" not in url.lower(),
                timeout=60_000,
            )
        except Exception:
            # Give the redirect chain a little extra time before deciding.
            await page.wait_for_timeout(5000)

        await print_page(page, "after login / federation redirect")

    # Ensure we are actually back on the SportsMax origin before making
    # same-origin API calls.
    if "clubspark.au" not in page.url.lower() or "auth.clubspark.net" in page.url.lower():
        raise RuntimeError(
            f"Login did not return to clubspark.au. Current URL: {page.url}"
        )

    # If federation returned to another ClubSpark path, explicitly reopen booking.
    if "/sportsmax/" not in page.url.lower():
        await page.goto(
            BOOKING_URL,
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        await page.wait_for_timeout(1200)
        await print_page(page, "SportsMax booking page after login")


async def main():
    today = datetime.now(SYDNEY_TZ).date().isoformat()

    print("=== Authenticated Beaman Park Render test v2 ===", flush=True)
    print(f"date={today}", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context = await browser.new_context(
            locale="en-AU",
            timezone_id="Australia/Sydney",
        )

        page = await context.new_page()

        try:
            await login(page)

            stamp = int(time.time() * 1000)

            print("\n1) Authenticated GetSettings", flush=True)

            settings = await fetch_json_same_origin(
                page,
                SETTINGS_URL,
                {"_": stamp},
            )

            print(
                f"IsAuthenticated={settings.get('IsAuthenticated')}",
                flush=True,
            )
            print(
                f"MustAuthenticate={settings.get('MustAuthenticate')}",
                flush=True,
            )

            if settings.get("IsAuthenticated") is not True:
                raise RuntimeError(
                    "Login completed but GetSettings still reports "
                    "IsAuthenticated=False"
                )

            print("\n2) Beaman-only GetVenueSessions", flush=True)

            payload = await fetch_json_same_origin(
                page,
                SESSIONS_URL,
                {
                    "resourceID": BEAMAN_ID,
                    "startDate": today,
                    "endDate": today,
                    "roleId": "",
                    "_": stamp + 1,
                },
            )

            resources = payload.get("Resources") or []
            pricing = 0

            for resource in resources:
                for day in resource.get("Days", []) or []:
                    for item in day.get("Sessions", []) or []:
                        if str(item.get("Name") or "").lower() == "pricing":
                            pricing += 1

            print(f"Resources={len(resources)}", flush=True)
            print(f"PricingSessions={pricing}", flush=True)

            print(
                "✅ AUTHENTICATED BEAMAN TEST SUCCEEDED",
                flush=True,
            )

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(
            f"❌ AUTHENTICATED BEAMAN TEST FAILED: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

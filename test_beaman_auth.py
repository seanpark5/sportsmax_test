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


async def dump_state(page, label):
    print(f"\n--- {label} ---", flush=True)
    print(f"url={page.url}", flush=True)
    try:
        print(f"title={await page.title()}", flush=True)
    except Exception:
        pass


async def login_if_needed(page):
    await page.goto(
        BOOKING_URL,
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    await page.wait_for_timeout(1500)
    await dump_state(page, "after initial SportsMax navigation")

    # The exact login host/form can change, so use robust field discovery.
    # First, detect whether we're already authenticated by testing GetSettings.
    settings = await page.evaluate(
        """
        async (url) => {
            const r = await fetch(url + "?_=" + Date.now(), {
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
            return {status: r.status, text: await r.text()};
        }
        """,
        SETTINGS_URL,
    )

    if settings["status"] == 200:
        try:
            payload = json.loads(settings["text"])
        except Exception:
            payload = {}
        print(
            f"Initial GetSettings: IsAuthenticated={payload.get('IsAuthenticated')} "
            f"MustAuthenticate={payload.get('MustAuthenticate')}",
            flush=True,
        )
        if payload.get("IsAuthenticated") is True:
            return

    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "SPORTSMAX_EMAIL and SPORTSMAX_PASSWORD must be set in Render"
        )

    # Try common email/username selectors.
    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[name="Email"]',
        'input[name="username"]',
        'input[name="Username"]',
        'input[autocomplete="username"]',
    ]

    password_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input[name="Password"]',
        'input[autocomplete="current-password"]',
    ]

    email_locator = None
    for sel in email_selectors:
        loc = page.locator(sel).first
        try:
            if await loc.count() and await loc.is_visible():
                email_locator = loc
                break
        except Exception:
            pass

    if email_locator is None:
        # Sometimes the page first shows a sign-in button.
        for text in ["Sign in", "Log in", "Login"]:
            btn = page.get_by_text(text, exact=False).first
            try:
                if await btn.count() and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        for sel in email_selectors:
            loc = page.locator(sel).first
            try:
                if await loc.count() and await loc.is_visible():
                    email_locator = loc
                    break
            except Exception:
                pass

    if email_locator is None:
        raise RuntimeError(
            f"Could not find SportsMax/ClubSpark email field. Current URL: {page.url}"
        )

    await email_locator.fill(EMAIL)

    # Some auth flows need "Next" before password appears.
    password_locator = None
    for sel in password_selectors:
        loc = page.locator(sel).first
        try:
            if await loc.count() and await loc.is_visible():
                password_locator = loc
                break
        except Exception:
            pass

    if password_locator is None:
        for text in ["Next", "Continue"]:
            btn = page.get_by_role("button", name=text, exact=False).first
            try:
                if await btn.count() and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        for sel in password_selectors:
            loc = page.locator(sel).first
            try:
                if await loc.count() and await loc.is_visible():
                    password_locator = loc
                    break
            except Exception:
                pass

    if password_locator is None:
        raise RuntimeError(
            f"Could not find SportsMax/ClubSpark password field. Current URL: {page.url}"
        )

    await password_locator.fill(PASSWORD)

    submitted = False
    for name in ["Sign in", "Log in", "Login", "Continue"]:
        btn = page.get_by_role("button", name=name, exact=False).first
        try:
            if await btn.count() and await btn.is_visible():
                await btn.click()
                submitted = True
                break
        except Exception:
            pass

    if not submitted:
        await password_locator.press("Enter")

    # Allow federation/redirect chain to complete.
    try:
        await page.wait_for_url(
            lambda url: "sportsmax" in url.lower(),
            timeout=60_000,
        )
    except Exception:
        pass

    await page.wait_for_timeout(2500)
    await dump_state(page, "after login attempt")


async def fetch_json(page, url, params):
    result = await page.evaluate(
        """
        async ({url, params}) => {
            const u = new URL(url, window.location.origin);
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


async def main():
    today = datetime.now(SYDNEY_TZ).date().isoformat()

    print("=== Authenticated Beaman Park Render test ===", flush=True)
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
            await login_if_needed(page)

            print("\n1) Authenticated GetSettings", flush=True)
            stamp = int(time.time() * 1000)
            settings = await fetch_json(
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
                    "Login did not produce IsAuthenticated=True"
                )

            print("\n2) Beaman-only GetVenueSessions", flush=True)
            payload = await fetch_json(
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
            print("✅ AUTHENTICATED BEAMAN TEST SUCCEEDED", flush=True)

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

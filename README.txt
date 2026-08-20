SPORTSMAX VERCEL RELAY TEST

Replace the old direct-Render SportsMax test with these files.

Render environment variables:
SPORTSMAX_PROXY_URL=https://www.courtscouter.com/api/internal/sportsmax
SPORTSMAX_PROXY_SECRET=<EXACT SAME VALUE AS VERCEL>

Vercel must also have SPORTSMAX_PROXY_SECRET set to the exact same value,
and Vercel must be redeployed after adding/changing it.

Interpretation:
401 -> secrets do not match.
502 with ClubSpark HTTP 500 -> Vercel is reachable, but ClubSpark rejects Vercel too.
200 -> relay works and can be used by the main CourtScouter scraper.

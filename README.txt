WORKING BEAMAN AUTHENTICATED SCRAPE TEST

Required Render environment variables:
SPORTSMAX_EMAIL
SPORTSMAX_PASSWORD

Critical fix:
GetVenueSessions must be requested with:
resourceID=

Do NOT send the Beaman ResourceGroupID as resourceID.

ClubSpark returns all SportsMax resources, then this test filters the
response to:
fb825473-257b-4951-91d9-f3ce04657284 (Beaman Park)

It prints Pricing windows for the next 3 days, court-by-court, with
hourly pricing calculated from Cost / Interval.

Example:
Beaman Park Court 1
  2026-08-20  7:00 am–4:00 pm  $23.00/hr

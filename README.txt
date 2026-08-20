AUTHENTICATED BEAMAN AVAILABILITY TEST

Required Render variables:
SPORTSMAX_EMAIL
SPORTSMAX_PASSWORD

This test logs in, calls GetVenueSessions for Beaman only, and prints
actual Beaman court availability rows.

If Pricing rows are returned, logs show:
Court name
date
start-end
hourly price

If Pricing rows are zero, it prints the actual returned Session names
so the production parser can be adjusted to the current ClubSpark payload.

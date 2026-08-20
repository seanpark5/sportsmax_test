BEAMAN PARK RENDER TEST

Purpose:
Test only Beaman Park for one date from a fresh Render service.

No environment variables needed.
No scheduler.
No database.
No Vercel relay.

Expected:
- GetSettings 200
- Beaman-specific GetVenueSessions using resourceID=fb825473-257b-4951-91d9-f3ce04657284

If Beaman-specific still returns 500, the problem is not caused by fetching all five SportsMax venues together.

SPORTSMAX STANDALONE RENDER TEST

FILES
-----
Dockerfile
requirements.txt
test_sportsmax.py


HOW TO DEPLOY ON RENDER
-----------------------

1. Unzip this folder locally.

2. Put these 3 files in a NEW GitHub repository:
   Dockerfile
   requirements.txt
   test_sportsmax.py

3. In Render:
   Dashboard
   -> New +
   -> Web Service

4. Connect the new GitHub repository.

5. Choose:
   Runtime: Docker

6. Use a cheap/free test instance if available.

7. Deploy.

8. Open Logs.

SUCCESS LOOKS LIKE:
-------------------
HTTP 200 ...GetSettings
VenueID=...
HTTP 200 ...GetVenueSessions
ResourceGroups=5
Resources=18
PricingSessions=...
✅ SPORTSMAX TEST SUCCEEDED

FAILURE LOOKS LIKE:
-------------------
HTTP 500 ...
BODY: {"Message":"An error has occurred."}
❌ SPORTSMAX TEST FAILED...

INTERPRETATION
--------------
If this fresh Render service succeeds:
- SportsMax is scrapeable from Render.
- The problem is specific to the main CourtScouter service or execution path.

If this fresh Render service fails with HTTP 500:
- ClubSpark is likely rejecting Render egress/network traffic generally.
- Stop debugging the main Render SportsMax scraper.
- Use the Vercel relay or another provider for SportsMax only.

AUTHENTICATED BEAMAN PARK RENDER TEST

Purpose:
Test whether SportsMax succeeds on Render after logging into ClubSpark.

FILES
-----
Dockerfile
requirements.txt
test_beaman_auth.py

RENDER ENVIRONMENT VARIABLES
----------------------------
SPORTSMAX_EMAIL=<your ClubSpark login email>
SPORTSMAX_PASSWORD=<your ClubSpark password>

Do NOT put the email/password in GitHub or the Python file.

DEPLOY
------
Use the existing sportsmax_test repo or a new test repo.
Replace its files with these files.
Commit to main.
Redeploy the Render test service.

SUCCESS
-------
Authenticated GetSettings:
IsAuthenticated=True
MustAuthenticate=False

Then:
Beaman-only GetVenueSessions -> HTTP 200

If login succeeds but GetVenueSessions still returns 500,
then authentication alone is not the missing factor.

If the script cannot find the login form, paste the log including
the "current URL" line and we can tailor the selectors to the exact
ClubSpark auth page.

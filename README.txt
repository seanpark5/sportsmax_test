AUTHENTICATED BEAMAN RENDER TEST V2

This version fixes the earlier cross-origin bug.

Required Render environment variables:
SPORTSMAX_EMAIL=<ClubSpark email>
SPORTSMAX_PASSWORD=<ClubSpark password>

It uses the exact login field names observed in the HAR:
EmailAddress
Password
RememberMe

Expected successful sequence:
1. Open SportsMax
2. Redirect to auth.clubspark.net
3. Fill EmailAddress + Password
4. Submit
5. Federation redirect back to clubspark.au
6. GetSettings -> IsAuthenticated=True
7. Beaman GetVenueSessions -> HTTP 200

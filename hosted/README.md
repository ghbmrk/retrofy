# Retrofy hosted Steam connection

Private, HTTPS, phone-accessible Steam account linking and visible-library snapshots. No Mac/localhost runtime dependency.

The Sites access boundary authenticates the visitor; all account/library storage is keyed by the server-injected stable `oai-authenticated-user-id`. Steam OpenID is an additional external account link, not a replacement for Sites authentication. Callbacks use `/steam/return`, preserving the platform's reserved auth routes.

Runtime configuration: `SESSION_SECRET` (required secret), R2 `BUCKET` binding (required), `STEAM_WEB_API_KEY` (optional server-managed secret). Without a server-managed Steam API key, the linked user supplies a key in an HTTPS password form for each sync. Keys are forwarded only to Valve and never persisted or logged. No arbitrary-URL fetching, user game upload/download, privacy-setting changes or ownership/compatibility certification occurs.

Library snapshots are private hosted records, available across devices after sign-in. An API-unavailable/private library is an error rather than an empty-success result. No background scheduler or cloud-save sync is implemented. Account switching and record deletion UI are not implemented.

Verification: run `node --test tests/*.mjs`, `bash scripts/build.sh`, then `node scripts/validate-artifact.mjs`. Automated provider-success fixtures are mocks. A real account link/library sync still requires the user's Valve login/API access. Production transport and access must be checked separately from unit tests.

Steam APIs: https://steamcommunity.com/dev and https://partner.steamgames.com/doc/webapi/IPlayerService#GetOwnedGames . Source is original MIT code; no Steam credentials, identities, library records or proprietary game files belong in this repository.

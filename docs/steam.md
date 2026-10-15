# Local Steam linking and visible-library sync

Run `python3 -m retrofy.cli steam-link --out local/steam-attempt-1` from the checkout. A loopback-only service prints a random URL and expires after 30 minutes. Open that URL in a browser on the same computer and choose **Sign in on Steam**. The sign-in page is Valve's `steamcommunity.com` OpenID endpoint; Retrofy never receives a Steam password or Steam Guard code.

Valve's [OpenID flow](https://steamcommunity.com/dev) identifies a SteamID. It does **not** grant access to private libraries or supply an API token. After verified sign-in, enter a [Steam Web API key obtained directly from Valve](https://steamcommunity.com/dev/apikey) in the local password field. Key registration, agreement acceptance and any credential creation are user actions. Keys are sent only to Valve's official HTTPS `GetOwnedGames` endpoint, never saved, and not placed in browser URLs or process arguments. The endpoint requires the key in its server-side GET request; do not add HTTP request logging. Python/TLS runtime memory is not a secure secret vault.

Steam's [GetOwnedGames documentation](https://partner.steamgames.com/doc/webapi/IPlayerService#GetOwnedGames) limits results to game details visible to the caller. A private/unavailable response is reported as unavailable, never a successful empty library. The app does not change privacy settings. If the API cannot see the library, the user must decide whether to change visibility; linking does not bypass that choice. Publisher ownership endpoints require publisher-specific access and are not a substitute for arbitrary library access.

## Local outputs and security scope

- `account.json`: SteamID and verification method only; no assertion, password or API key.
- `library.json`: returned app IDs, names and playtime, all marked `unassessed`; no compatibility or adaptation-rights inference. This is a snapshot, not ongoing background synchronization or Steam Cloud/save integration.
- Each file is created with mode 0600 and exclusive creation. Use a new output directory for each attempt. Outputs belong under ignored `local/`, never in Git or public issues. File parent directories must be trusted; hostile local processes are outside the protection boundary.
- The server binds only `127.0.0.1`, checks Host/Origin and form CSRF token, has a random callback path, validates signed identity fields and timestamp, verifies assertions directly with the fixed Valve HTTPS endpoint, and rejects replay after linking. It refuses redirects from API/verification endpoints. Response sizes and timeouts are bounded. HTTP access logging is disabled.
- No installation/filesystem scanning, purchases, downloads, game execution, license circumvention or Steam privacy changes occur. Steam is not required to be installed for account/library metadata linking.

A future hosted product should use its own securely managed API credentials rather than asking each user to register a key. That service, operational secret management and independent security audit are not implemented. The current implementation is a local research integration, not a production identity provider.

## Verification status

Automated tests cover assertion tampering, missing signature verification, expired nonce, wrong endpoint/callback, private versus empty library, duplicate/inconsistent metadata, invalid-key rejection, restrictive file creation, Host/Origin/CSRF checks, session expiry and callback replay. Provider responses in unit tests are mocks and are labeled as such. The live local page and redirect to Valve's official sign-in page were observed. **No authenticated library sync has yet been demonstrated.** A completed account link requires a real Valve assertion; a successful sync requires a real API response and saved local snapshot.

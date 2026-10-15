# Hosted Steam connection security model

Revision 2 minimizes sensitive data rather than promising absolute security.

## Structural boundaries

- Steam passwords and Guard codes are entered only on Valve's HTTPS OpenID site. Retrofy verifies assertions directly with the fixed Valve endpoint; redirects from upstream requests are refused.
- No personal API-key input exists. Form endpoints accept only a scoped, expiring CSRF token and reject extra fields. Library lookup uses an operator-managed runtime secret, never a user-supplied key.
- Library responses are rendered on demand with no server-side snapshot or download endpoint. HTML escapes upstream game names and sends no-store headers. No JavaScript runs in this application.
- The SteamID is carried in an AES-GCM authenticated encrypted cookie, scoped to the platform user and pinned HTTPS origin, with a one-hour expiry. Cookies are Secure, HttpOnly, SameSite=Lax and use the __Host- prefix.
- One pending challenge per platform user expires after ten minutes. An R2 conditional write consumes it before provider verification: concurrent replay cannot both succeed. Starting a new flow supersedes the previous one.
- CSRF tokens bind user, operation and expiry. POST operations also require the exact Origin. Login/callback/sync have bounded per-user rate counters using conditional writes.
- Unlink rotates revocation state, invalidating every copied link cookie, and deletes pending state and legacy account/library records. Pseudonymous rate counters and revocation state remain. Expired pending metadata is logically unusable but is not automatically physically deleted.
- Public deployment remains owner-private behind Sites authentication. The Worker trusts only the identity header supplied by that authenticated gateway. It must never be exposed through a route that permits clients to set that header directly.

The Referrer-Policy is `same-origin`: same-origin forms retain their Origin, while cross-origin navigations receive no referrer. `no-referrer` is unsuitable here because it can turn a legitimate form Origin into `null`; null origins remain rejected.

## Trust and limits

Security depends on Sites enforcing its access gate and stripping/replacing identity headers, TLS, Cloudflare R2 conditional-write semantics, secret protection, browser cookie protections, and Valve. The operator, hosting provider, compromised browser or compromised account can defeat relevant boundaries. Origin/CSRF protections do not cure gateway or host compromise. SteamIDs are encrypted client-side state, not anonymous data. Metadata still links activity to a hashed platform identifier. Infrastructure may retain request/access logs; application code does not log callbacks, API keys or game lists. HTTP no-store cannot prevent screenshots or all browser/OS retention.

The Steam service key grants service API access; OpenID proves identity but does not grant access to private library data. Missing service configuration disables sync explicitly. Never request a personal key as a workaround.

## Verification

Run `node --test tests/worker.mjs`. Sixteen tests cover identity/origin checks, script-free markup and CSP, signed/encrypted token rejection, CSRF scope, concurrent single-use consumption and rate limits, mocked OpenID success/rejection, replay, cross-user callback rejection, missing service configuration, escaped transient library rendering, revocation, and incomplete library rejection. The in-memory R2 model implements conditional writes; these tests do not validate provider infrastructure, actual Valve login, production R2 concurrency or a real private library fetch. Independent review and authenticated live testing remain valuable.

Primary protocol/storage references: https://steamcommunity.com/dev and https://developers.cloudflare.com/r2/api/workers/workers-api-reference/ .

The form-action policy permits only this origin and `https://steamcommunity.com`; browsers can apply this restriction to redirects after form submission, so Steam must be explicit. Server-side login redirects still use the fixed Valve OpenID endpoint.

## Local intake download

The private `/intake` and `/downloads/Retrofy-Intake-SteamOS.tar.gz` routes serve a fixed source package, with a SHA-256 digest. A digest delivered through the same site is a consistency check, not an independent signature. Downloading does not grant browser filesystem access. The downloaded Python tool runs locally only after user launch and confirmation, using existing Python 3 and KDialog or Zenity; no dependencies are installed. It has no network client, does not invoke game code, reads only bounded installation metadata and bounded archive prefixes, and writes fresh mode-0700 report folders with mode-0600 files. Account fields, absolute paths, raw archive bytes and unrecognized filenames are excluded from reports. Saves/userdata are not scanned. Final archive symlinks/devices and linked Data/Localization directories are refused/skipped; trusted local directory trees are assumed against concurrent hostile mutation. Partial hashes are not full-file integrity evidence. No report upload endpoint is provided.

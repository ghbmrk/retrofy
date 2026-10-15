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

Run `node --test tests/worker.mjs`. Seventeen tests cover identity/origin checks, script-free markup and CSP, signed/encrypted token rejection, CSRF scope, concurrent single-use consumption and rate limits, mocked OpenID success/rejection, replay, cross-user callback rejection, missing service configuration, escaped transient library rendering, revocation, and incomplete library rejection. The in-memory R2 model implements conditional writes; these tests do not validate provider infrastructure, actual Valve login, production R2 concurrency or a real private library fetch. Independent review and authenticated live testing remain valuable.

Primary protocol/storage references: https://steamcommunity.com/dev and https://developers.cloudflare.com/r2/api/workers/workers-api-reference/ .

The form-action policy permits only this origin and `https://steamcommunity.com`; browsers can apply this restriction to redirects after form submission, so Steam must be explicit. Server-side login redirects still use the fixed Valve OpenID endpoint.

## Hosted verification transport evidence

A private credential-free `/health/steam` probe sends a fixed invalid OpenID assertion; it never forwards request parameters, cookies, headers, or personal data. It is protected by the existing private Sites gateway, like `/health`. It compares manual and error redirect modes. On 2026-10-15, hosted manual POST returned HTTP 200 from Valve; error mode threw `Invalid redirect value, must be one of "follow" or "manual"`. Production verification therefore uses manual mode and explicitly rejects all non-2xx responses, including redirects. A regression test ensures redirected verification cannot issue a linked cookie. This proves transport reachability, not successful real-account authentication.

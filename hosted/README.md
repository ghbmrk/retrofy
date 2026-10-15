# Retrofy hosted Steam connection

Phone-accessible Steam identity connection hosted independently of the Mac. Production access remains owner-private through Sites authentication. Sign in to the owning ChatGPT account, then choose **Sign in on Steam**. Enter Steam credentials only on `steamcommunity.com`.

Revision 2 has no personal API-key entry, no stored library snapshots, no application JavaScript, one-hour encrypted account-link cookies, atomic single-use login challenges, per-user rate limits, CSRF protection and revocation. See [SECURITY.md](SECURITY.md) for exact assumptions and residual risks.

## Operator configuration

Use the Sites runtime secret manager for `SESSION_SECRET` (high entropy) and, to enable library lookup, `STEAM_WEB_API_KEY` (operator-managed). Configure `SITE_ORIGIN` as the exact HTTPS production origin. Do not commit secrets, request user keys, expose the Worker outside its identity-enforcing gateway, or change the private audience implicitly. R2 binding: `BUCKET`. Only pseudonymous pending state, rate counters and revocation state are stored. Unlink also deletes legacy saved account/library records.

Without an operator key, Steam login remains available and library sync is visibly disabled. OpenID does not bypass private Steam Game details. Imported titles remain unassessed; ownership is not adaptation permission.

## Reproduce

Use Node 24 or compatible WebCrypto runtime:

```
node --test tests/worker.mjs
bash scripts/build.sh
node scripts/validate-artifact.mjs
```

Build output is `dist/`. Publish through the Sites source workflow: commit/push the exact source, package that source's build output, then deploy the saved version privately. Keep local project configuration out of reusable examples. No proprietary game material belongs in source, logs or artifacts.

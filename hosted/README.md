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

## SteamOS local index reconnaissance v2

`/intake` offers a deterministic six-file, source-only tar.gz. The GUI launcher runs Python 3 and KDialog/Zenity, independently of Steam linking or an API key. No installer, sudo, network client, account output or saves/userdata scan. Only new private reports are written; the installation is unchanged.

The scanner reads 40-byte archive header probes and bounded non-solid v18 directory indexes. Index metadata is decompressed in memory; directory-referenced payloads are never read, extracted, decoded or executed. Reports contain only aggregate filename-based categories, physical counts/sizes, compression methods, safe archive labels and digests. Internal resource paths stay transient in memory. A signature/header probe of an unknown file can read its first 40 bytes. Raw bytes and internal paths are never reported.

The public layout reference is LSLib commit 6f5f6987d10d8485876b8368431c948e4dea4f83. An MIT notice is included for attribution; no LSLib binary is bundled. The bounded LZ4 decoder is independently tested against python-lz4 4.4.4, a temporary development-only dependency. Resource/format failures stay unresolved. Patches, dependencies, mods, permissions and behavioral semantics remain unassessed. Sizes are physical metadata totals, not an estimate of native ROM size.

Checks: `python3 tests/intake_test.py` (9 tests); `python3 tests/lspk_test.py` (12 tests; independent codec case skips if python-lz4 is absent); `node --test tests/worker.mjs` (18 hosted tests). Then `bash scripts/build.sh` and `node scripts/validate-artifact.mjs`. The package is deterministic. Version 1 ran on the user's machine; v2 still requires a local run.

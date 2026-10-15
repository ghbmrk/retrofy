# Steam connection

Open https://retrofy-steam.markizard.chatgpt.site on a phone or computer. Sign in with the owning ChatGPT account, then choose **Sign in on Steam**. Steam credentials stay on Valve. No Mac is required. The service remains owner-private.

Revision 2 accepts no personal API keys. Library lookup needs an operator-managed runtime secret that is not yet configured; login is available but sync is disabled. OpenID proves Steam identity, not permission to read private Game details. No real authenticated library retrieval has been demonstrated.

Library metadata is rendered only for the request, with no saved snapshot. The link is an authenticated encrypted one-hour browser cookie bound to the platform user and origin. Atomic one-use login challenges, operation-scoped CSRF checks, per-user rate limits, restrictive CSP and unlink revocation reduce the exposed surface. Pseudonymous rate/revocation metadata remains after unlink. See [the exact threat model](../hosted/SECURITY.md) for hosting trust, retention and residual risks.

The old local CLI/server entry points are disabled. Legacy Python components remain for research tests and are not deployed. Never deploy them or ask users to enter API keys. No installation scanning, game downloading, purchase, game execution or Steam privacy changes occur. Library membership does not prove adaptation rights or GBC compatibility.

Sixteen hosted tests use conditional-write storage models and mocked Valve responses. They establish application behavior under those models, not a security audit of Sites/Cloudflare/Valve or successful live authentication. Tests and reproducible build instructions are in `hosted/`.

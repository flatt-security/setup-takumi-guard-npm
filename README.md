<p align="center">
  <img src="branding.png" alt="Takumi Guard — a panda security guard scanning npm packages" width="300" />
</p>

<h1 align="center">Takumi Guard for npm</h1>

<p align="center">
  <strong>Stop malicious npm packages before they reach your CI.</strong><br />
  A GitHub Action that routes installs through a security proxy — no secrets, no config files, two lines of YAML.
</p>

<p align="center">
  <a href="https://github.com/flatt-security/setup-takumi-guard-npm/actions/workflows/test.yml"><img src="https://github.com/flatt-security/setup-takumi-guard-npm/actions/workflows/test.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/flatt-security/setup-takumi-guard-npm" alt="License" /></a>
</p>

---

> **Not using CI?** For local setup on your laptop, see the [email registration & token management appendix](#appendix-email-registration--token-management) below.

## Contents

- [What is Takumi Guard?](#what-is-takumi-guard)
- [Quickstart (3 steps)](#quickstart)
- [Verify it works](#verify-it-works)
- [Setup modes](#setup-modes)
- [Migrating existing projects (3 steps)](#migrating-existing-projects)
- [Inputs](#inputs)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Appendix: Email registration & token management](#appendix-email-registration--token-management)

---

## What is Takumi Guard?

Every `npm install` in your CI is a trust decision. Takumi Guard sits between your workflow and the npm registry, **blocking known-malicious packages before they execute**.

- **How it works** -- Routes installs through a security proxy (`npm.flatt.tech`) that checks packages against a threat database in real time.
- **What you change** -- One step in your workflow YAML. No config files, no secrets to manage.
- **What it supports** -- **npm**, **pnpm**, and **yarn**.

---

## Quickstart

**Goal:** Add Takumi Guard to any GitHub Actions workflow. No account required.

**Step 1.** Add the action to your workflow file (e.g. `.github/workflows/ci.yml`):

```yaml
steps:
  - uses: actions/checkout@v4

  - uses: flatt-security/setup-takumi-guard-npm@v1   # <-- add this line

  - run: npm install
  - run: npm test
```

**Step 2.** Push the change. Every `npm install` in this job now runs through the Takumi Guard proxy. Malicious packages are blocked automatically.

**Step 3.** *(Optional)* **Want audit logging and a dashboard?** Add a Bot ID for full visibility into package activity:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # Required for authentication
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: flatt-security/setup-takumi-guard-npm@v1
        with:
          bot-id: "YOUR_BOT_ID"

      - run: npm install
```

> **Where do I get a Bot ID?** Create one at [Shisho Cloud byGMO](https://cloud.shisho.dev) -- or skip this entirely. Blocking works without it. The Bot ID is a public reference key, not a secret.

---

## Verify it works

Confirm blocking is active by trying to install a known-blocked test package.

**From your terminal** (no account or setup needed):

```bash
npm install --registry https://npm.flatt.tech @panda-guard/test-malicious
```

**Or as a CI step** in your workflow:

```yaml
      - name: Verify Takumi Guard is active
        run: |
          npm install @panda-guard/test-malicious && exit 1 || echo "Blocked as expected"
```

> **Expected result:** The install fails with a block message. If it does, the guard is working.

---

## Setup modes

Pick the mode that fits your situation. Here is how they compare at a glance:

| Mode | Blocks malware | Audit logging | Account needed | Best for |
|---|:---:|:---:|:---:|---|
| **[Blocking only](#blocking-only)** | Yes | No | No | OSS projects, quick evaluation |
| **[Full protection](#full-protection)** | Yes | Yes | Yes | Production workloads |
| **[Auth-only](#auth-only-advanced)** | You manage | Yes | Yes | Monorepos, custom `.npmrc` |

---

### Blocking only

> **No account needed.** Add one line and you are protected.

Blocks known-malicious packages. No signup, no authentication.

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
```

Good for open-source projects or quick evaluation.

---

### Full protection

> **Recommended for production.** Blocks threats _and_ logs all package activity to your dashboard.

```yaml
permissions:
  id-token: write

steps:
  - uses: flatt-security/setup-takumi-guard-npm@v1
    with:
      bot-id: "YOUR_BOT_ID"
```

**Key details:**
- Auth is handled via **GitHub's built-in OIDC** -- no PATs or secrets to rotate.
- If authentication fails, **blocking remains active** but logging is degraded. The build continues with a warning.
- Get a Bot ID from [Shisho Cloud byGMO](https://cloud.shisho.dev).

---

### Auth-only (advanced)

> **For custom setups.** You manage the registry URL in your own `.npmrc`. The action only handles authentication.

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  with:
    bot-id: "YOUR_BOT_ID"
    set-registry: false
```

**Key details:**
- Useful for monorepos or projects that need full control over `.npmrc`.
- Requires `registry=https://npm.flatt.tech/` in your committed `.npmrc`.
- If authentication fails, **the action exits with an error** -- there is no fallback.

---

## Migrating existing projects

> **Why is this needed?** If your project already has a lockfile, it references `registry.npmjs.org`. You need a one-time regeneration so the lockfile points to the proxy registry instead. This works locally because the proxy serves package metadata without authentication.

**Step 1.** Set the registry to the Takumi Guard proxy:

```bash
npm config set registry "https://npm.flatt.tech/" --location=project
```

**Step 2.** Regenerate the lockfile for your package manager:

<details>
<summary><strong>pnpm</strong></summary>

```bash
rm pnpm-lock.yaml && pnpm install
```
</details>

<details>
<summary><strong>npm</strong></summary>

```bash
rm package-lock.json && npm install
```
</details>

<details>
<summary><strong>yarn</strong></summary>

```bash
yarn install
```
</details>

**Step 3.** Commit the updated `.npmrc` and lockfile:

```bash
git add .npmrc pnpm-lock.yaml   # or package-lock.json / yarn.lock
git commit -m "Route installs through Takumi Guard"
```

> **Done.** Your CI will now install packages through Takumi Guard on the next push.

---

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `bot-id` | No | -- | Bot ID from Shisho Cloud byGMO. Omit for blocking-only mode. |
| `set-registry` | No | `true` | Set the registry URL in `.npmrc`. Set to `false` if you manage it yourself. |
| `registry-url` | No | `https://npm.flatt.tech` | Registry endpoint. |
| `sts-url` | No | `https://sts.shisho.dev` | STS endpoint for token exchange. |
| `expires-in` | No | `1800` | Token lifetime in seconds (max 86400). |

---

## Outputs

| Output | Description |
|---|---|
| `token-expires-at` | ISO 8601 timestamp of token expiration. Only set when authenticated. |

---

## Troubleshooting

**Find your error message below**, then follow the fix.

| Error | Cause | Fix |
|---|---|---|
| `OIDC not available` | Missing permission on the job | Add `permissions: { id-token: write }` to your job |
| `invalid ID token` | Trust condition mismatch | Check the bot's trust settings in Shisho Cloud byGMO |
| `invalid request` | Malformed bot-id | Double-check the bot-id value from your console |
| `Authentication failed ... Falling back` | STS token exchange failed | Verify bot-id and trust settings. Blocking is still active. |
| Lockfile conflicts after setup | Lockfile still references `registry.npmjs.org` | Follow the [migration steps](#migrating-existing-projects) to regenerate it |

> **Still stuck?** Open an issue on this repository with your error output and workflow file (redact any IDs).

---

## Security

- **Short-lived tokens** -- 30 minutes by default, 24 hours max.
- **Auto-masked** -- Tokens are automatically masked in workflow logs.
- **Project-scoped** -- The action writes to project-level `.npmrc` only. Your global npm config is untouched.
- **Preserves scoped registries** -- Existing entries (e.g. `@myorg:registry=...`) are not overwritten.

---

## Appendix: Email registration & token management

> **Optional.** Register your email to receive breach notifications if a package you installed is later flagged as malicious. This works for local development -- CI workflows should use [Full protection](#full-protection) instead.

### Register

```bash
curl -X POST https://npm.flatt.tech/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

Check your inbox and click the verification link. You will receive a token like `tg_anon_xxx...`.

**Language preference:** Add `"language": "ja"` to receive emails in Japanese. Defaults to English (`"en"`) if omitted.

```bash
curl -X POST https://npm.flatt.tech/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "language": "ja"}'
```

### Configure npm

```bash
npm config set registry "https://npm.flatt.tech/"
npm config set //npm.flatt.tech/:_authToken "tg_anon_xxx..."
```

After this, `npm install` routes through Takumi Guard with your identity attached. If a package you downloaded is later found to be malicious, you will receive a breach notification email.

### Check token status

```bash
curl -H "Authorization: Bearer tg_anon_xxx..." \
  https://npm.flatt.tech/api/v1/tokens/status
```

### Rotate your key

If your key is compromised, regenerate it instantly:

```bash
curl -X POST -H "Authorization: Bearer tg_anon_xxx..." \
  https://npm.flatt.tech/api/v1/tokens/regenerate
```

Returns a new API key. The old one is invalidated immediately. Update your `.npmrc` with the new key.

Alternatively, call `POST /api/v1/tokens` again with the same email to receive a rotation link via email.

### Revoke a token

```bash
curl -X DELETE -H "Authorization: Bearer tg_anon_xxx..." \
  https://npm.flatt.tech/api/v1/tokens
```

Revoking a token stops future breach notifications and removes the email association. You can register again at any time.

> **For a complete walkthrough**, see the [Takumi Guard quickstart guide](https://shisho.dev/docs/t/guard/quickstart/npm#setup-anonymous).

---

<p align="center">
  Built by <a href="https://flatt.tech">GMO Flatt Security Inc.</a><br />
  <a href="LICENSE">MIT License</a>
</p>

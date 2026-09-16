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
- [Installs outside the repository root](#installs-outside-the-repository-root)
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
- **What it supports** -- **npm**, **pnpm**, **Yarn Classic (v1)**, and **Yarn Berry (v2+)**.

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
| **[Auth-only](#auth-only-advanced)** | You manage | Yes | Yes | Custom `.npmrc` |

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
- Useful for projects that need full control over `.npmrc`.
- Requires `registry=https://npm.flatt.tech/` in your committed `.npmrc`.
- If authentication fails, **the action exits with an error** -- there is no fallback.

---

## Installs outside the repository root

Works with every mode above. By default the action writes `${{ github.workspace }}/.npmrc`, which is the file npm, pnpm and Yarn Classic read when you install at the repository root. If your install reads a different file, use `npmrc-path`: writing the configuration anywhere else leaves the install on the public registry, and unless you use auth-only mode **nothing fails** -- the registry line and the token live in that one file, so both are ignored together and packages are fetched without passing through Takumi Guard.

`npmrc-path` takes a directory (the `.npmrc` is created inside it) or a file path. Relative paths resolve against the workspace.

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  with:
    bot-id: "YOUR_BOT_ID"
    npmrc-path: infrastructure   # the package.json you install lives here
```

**Which directory?** With workspaces, the workspace root. Without workspaces, the directory holding the `package.json` you install. The details differ per package manager (measured with npm 10.4.0, pnpm 11.5.0, Yarn 1.22.22 and Yarn 4.18.0):

| Package manager | No workspaces | Workspaces |
|---|---|---|
| npm | the directory holding `package.json`; a file at the repository root is **not** read from a subdirectory | the **workspace root**. npm ignores an `.npmrc` inside a workspace package even when the install runs in that package |
| pnpm | the directory holding `package.json` | the **workspace root**, which is where a workspace install runs from |
| Yarn Classic (v1) | the directory holding `package.json`; unlike npm it also reads a file at the repository root | the **workspace root**, for the same reason as pnpm |
| Yarn Berry (v2+) | not applicable -- Berry does not read `.npmrc` | not applicable |

Yarn Berry receives the registry and token through `YARN_NPM_REGISTRY_SERVER` and `YARN_NPM_AUTH_TOKEN` in `$GITHUB_ENV`, which apply to the whole job whatever directory the install runs in. `npmrc-path` has no effect on it.

### Keeping the file out of your working tree

Pass a path **outside** the workspace and the action also exports `NPM_CONFIG_USERCONFIG`, so npm, pnpm and Yarn Classic read it from any directory while your checkout stays untouched. Use this when a workflow commits its own changes -- a tracked `.npmrc` would otherwise be swept into an auto-generated commit -- or when the install happens inside a Docker build:

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  with:
    bot-id: "YOUR_BOT_ID"
    npmrc-path: ${{ runner.temp }}/takumi-guard/npmrc

- run: docker build --secret id=npmrc,src="$NPM_CONFIG_USERCONFIG" .
```

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

The secret is mounted for that one `RUN` and never becomes a layer, so the token stays out of the image and out of build args.

**Two things to know about this mode:**

- A committed `.npmrc` containing `registry=` **wins** over it, because project-level configuration takes precedence over user-level. If your repository commits its own registry line, point `npmrc-path` at that file instead.
- If `NPM_CONFIG_USERCONFIG` is already set -- `actions/setup-node` sets it whenever you give it `registry-url` -- the action stops with an error rather than discarding someone else's file. Pass that same path as `npmrc-path` and the settings are merged into it.

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
| `sts-url` | No | `https://sts.cloud.shisho.dev` | STS endpoint for token exchange. |
| `expires-in` | No | `1800` | Token lifetime in seconds (max 86400). |
| `audience` | No | `https://sts.cloud.shisho.dev` (the STS URL) | Audience for the OIDC token request. Override when your Bot trust condition expects a different value. |
| `npmrc-path` | No | `${{ github.workspace }}/.npmrc` | Directory or file path to write the `.npmrc` to. See [Installs outside the repository root](#installs-outside-the-repository-root). |

---

## Outputs

| Output | Description |
|---|---|
| `registry-url` | The npm registry URL. |
| `token` | The access token for the registry. Empty in anonymous mode. |
| `token-expires-at` | ISO 8601 timestamp of token expiration. Only set when authenticated. |
| `npmrc-path` | Absolute path of the `.npmrc` the action wrote. |

---

## Troubleshooting

**Find your error message below**, then follow the fix.

| Error | Cause | Fix |
|---|---|---|
| `OIDC not available` | Missing permission on the job | Add `permissions: { id-token: write }` to your job |
| `invalid ID token` | Trust condition mismatch | Check the bot's trust settings in Shisho Cloud byGMO. If your trust condition sets an audience, it must equal the value the action sends -- by default the STS URL (`https://sts.cloud.shisho.dev`); use the `audience` input to override. |
| `invalid request` | Malformed bot-id | Double-check the bot-id value from your console |
| `Authentication failed ... Falling back` | STS token exchange failed | Verify bot-id and trust settings. Blocking is still active. |
| Lockfile conflicts after setup | Lockfile still references `registry.npmjs.org` | Follow the [migration steps](#migrating-existing-projects) to regenerate it |

> **Still stuck?** Open an issue on this repository with your error output and workflow file (redact any IDs).

---

## Security

- **Short-lived tokens** -- 30 minutes by default, 24 hours max.
- **Auto-masked** -- Tokens are automatically masked in workflow logs.
- **Project-scoped** -- For npm/pnpm/Yarn v1, the action writes to project-level `.npmrc` only. Your global npm config is untouched. With `npmrc-path` pointing outside the workspace, it writes that file and exports `NPM_CONFIG_USERCONFIG`; the file is created with `600` permissions and your global config is still untouched.
- **Yarn Berry** -- For Yarn v2+, the registry URL and auth token are exported as environment variables (`YARN_NPM_REGISTRY_SERVER`, `YARN_NPM_AUTH_TOKEN`) via `$GITHUB_ENV`. These are job-scoped (visible to subsequent steps), but the token is short-lived and auto-masked in logs.
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

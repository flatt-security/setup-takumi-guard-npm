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
- [Where the configuration is written](#where-the-configuration-is-written)
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
- **What it supports** -- **npm**, **pnpm**, **Yarn Classic (v1)**, **Yarn Berry (v2+)**, and **bun**.

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
- Every client receives the token. npm, pnpm, bun and Yarn Berry send it with every request to the proxy; **Yarn Classic sends it only for scoped packages by default**, so its unscoped packages are checked but not attributed. Set `always-auth: true` to attribute those too (see [Yarn Classic](#yarn-classic)), and see [Yarn Berry](#yarn-berry) for the one case where Berry needs a setting of your own.
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

## Where the configuration is written

The action writes `$RUNNER_TEMP/.npmrc` and exports `NPM_CONFIG_USERCONFIG` and the registry through `$GITHUB_ENV`, so every later step in the job is covered whatever directory it runs in, and **nothing in your checkout is modified**.

```
$RUNNER_TEMP/
└── .npmrc              registry + token, mode 600

$GITHUB_ENV
├── NPM_CONFIG_USERCONFIG=$RUNNER_TEMP/.npmrc
├── NPM_CONFIG_REGISTRY=https://npm.flatt.tech/
└── pnpm_config_registry=https://npm.flatt.tech/

$GITHUB_WORKSPACE/      untouched
└── infrastructure/     npm ci here goes through Takumi Guard
```

**This is why an install in a subdirectory needs nothing from you.** npm, pnpm and Yarn Classic resolve project configuration from the directory holding `package.json`, so a file written at the repository root is ignored by an install that runs elsewhere -- and since the registry line and the token live in that one file, both are ignored together and the install silently leaves the proxy. A user-level file avoids the question entirely.

```yaml
defaults:
  run:
    working-directory: infrastructure

steps:
  - uses: flatt-security/setup-takumi-guard-npm@v1
  - run: npm ci        # goes through Takumi Guard
```

**`NPM_CONFIG_USERCONFIG` replaces `$HOME/.npmrc` rather than adding to it**, because npm reads exactly one user-level file. So the action does two things to avoid dropping settings you already rely on: if `$HOME/.npmrc` exists, its contents are copied into the new file first, and if another action already exported `NPM_CONFIG_USERCONFIG` -- `actions/setup-node` does when given `registry-url` -- the Guard settings are appended to that file instead, leaving the variable pointing where it already pointed.

Yarn Berry and bun do not read that file, so the action hands them the token through the variables they do read, which are job-scoped in the same way.

| Variable | What reads it | Set when |
|---|---|---|
| `NPM_CONFIG_USERCONFIG` | npm, pnpm, Yarn Classic | always |
| `NPM_CONFIG_REGISTRY` | npm, pnpm 10 and earlier, Yarn Classic, bun | unless `set-registry: false` |
| `pnpm_config_registry` | pnpm 11 and later | unless `set-registry: false` |
| `YARN_NPM_REGISTRY_SERVER` | Yarn Berry | unless `set-registry: false` |
| `YARN_NPM_AUTH_TOKEN` | Yarn Berry | when authenticated |
| `YARN_NPM_ALWAYS_AUTH` | Yarn Berry | when authenticated |
| `BUN_CONFIG_TOKEN` | bun | when authenticated |

### bun

bun does not read `NPM_CONFIG_USERCONFIG`, so it takes the registry from `NPM_CONFIG_REGISTRY` and the token from `BUN_CONFIG_TOKEN`. An install in any directory goes through Takumi Guard and is attributed to your bot. `BUN_CONFIG_TOKEN` is used rather than `NPM_CONFIG_TOKEN` because npm 11 prints `npm warn Unknown env config "token"` on every command while `NPM_CONFIG_TOKEN` is set, and ignores `BUN_CONFIG_TOKEN`.

`BUN_CONFIG_TOKEN` names no host, so a command that points bun at another registry (`bun add --registry <host>`, `bun publish --registry <host>`) sends it there. It also takes precedence over an `NPM_CONFIG_TOKEN` you set yourself. If a step talks to another registry, set `BUN_CONFIG_TOKEN` on that step to the token for that registry.

With `set-registry: false` bun sends it to the default registry you configured, which this mode requires to be `https://npm.flatt.tech`; installs stay attributed to your bot.

### Yarn Berry

Yarn Berry takes the registry from `YARN_NPM_REGISTRY_SERVER` and the token from `YARN_NPM_AUTH_TOKEN`. Berry sends that token only for scoped packages unless `npmAlwaysAuth` is set, so the action also exports `YARN_NPM_ALWAYS_AUTH=true`, and every package, scoped or not, is attributed to your bot.

One case needs a setting of your own:

- **Your `.yarnrc.yml` has an `npmRegistries` entry for `https://npm.flatt.tech`.** That entry's `npmAlwaysAuth`, which is `false` unless set, takes precedence over the variable. Add `npmAlwaysAuth: true` to the entry.

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  id: guard
  with:
    bot-id: "YOUR_BOT_ID"

- run: |
    yarn config set -H 'npmRegistries["https://npm.flatt.tech"].npmAuthToken' "$GUARD_TOKEN"
    yarn config set -H 'npmRegistries["https://npm.flatt.tech"].npmAlwaysAuth' true
    yarn install
  env:
    GUARD_TOKEN: ${{ steps.guard.outputs.token }}
```

`-H` writes `$HOME/.yarnrc.yml` rather than the project `.yarnrc.yml`, which Berry repositories normally commit, so the checkout stays clean. On a self-hosted runner that file outlives the job, so remove it if the runner is shared.

`YARN_NPM_AUTH_TOKEN` names no host either: Berry also sends it to a scoped registry in `npmScopes` that has no token of its own, and on `yarn npm publish` to a `publishConfig.registry` elsewhere. Give such a registry its own token in `npmScopes`, or set `YARN_NPM_AUTH_TOKEN` on the publish step.

A `yarn.lock` entry with `__archiveUrl` is fetched from that URL directly, not through Takumi Guard, so the package is neither checked nor attributed, and Berry sends the token to that host as well: for every such package while `npmAlwaysAuth` is in effect, and for scoped ones even without it. Yarn records `__archiveUrl` only when a registry returns tarball URLs on another host, which Takumi Guard did for Yarn until April 2026. Find such entries with `grep __archiveUrl yarn.lock`, remove the `::__archiveUrl=...` part from each `resolution` (up to the closing quote), and run `yarn install`. The locked version and the range in `package.json` stay the same, and the tarball is then fetched through Takumi Guard:

```sh
sed -i.bak -E 's/::__archiveUrl=[^"]*//' yarn.lock && rm yarn.lock.bak
yarn install
```

`yarn up <package>` also removes the entry, but it upgrades the package to its latest version and rewrites the range in `package.json`. A plain `yarn install` leaves the entry as it is.

### Yarn Classic

Yarn Classic reads the file this action writes, so it is configured like npm and pnpm, with one difference: it sends the token only for scoped packages. Unscoped dependencies are therefore checked but not attributed.

To attribute them as well, set `always-auth: true`, and the action adds a host-bound `always-auth` entry to the file next to the token:

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  with:
    bot-id: "YOUR_BOT_ID"
    always-auth: true
```

The entry names the host, so no other registry sees the credential, and it works with `set-registry: false` as well. It is off by default because npm 11 prints `npm warn Unknown user config "always-auth"` on every command while the entry exists (npm 10 does not), which is the trade-off.

### Auto-commit workflows

Because the checkout is untouched, `git status` stays clean and a workflow that generates commits cannot sweep the token into one.

### Dockerfile builds

`$RUNNER_TEMP` is not inside the build context, so hand the file to BuildKit as a secret. `$NPM_CONFIG_USERCONFIG` and the `npmrc-path` output both name it:

```yaml
- uses: flatt-security/setup-takumi-guard-npm@v1
  with:
    bot-id: "YOUR_BOT_ID"

- run: docker build --secret id=npmrc,src="$NPM_CONFIG_USERCONFIG" .
```

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

The secret is mounted for that one `RUN` and never becomes a layer, so the token stays out of the image and out of build args.

### Publishing from the same job

Takumi Guard is a read-only proxy and it becomes your default registry, so `npm publish` would target it and fail. Name the publish target explicitly:

```json
{ "publishConfig": { "registry": "https://registry.npmjs.org/" } }
```

or pass `npm publish --registry=https://registry.npmjs.org/`.

**bun is different.** `bun publish` ignores `publishConfig.registry` and targets the registry in the environment, so it reaches the proxy and fails. Pass `--registry=<host>` and set `BUN_CONFIG_TOKEN` on that step to your publish token; otherwise the Guard token is sent to that host.

### Migrating from a version that wrote into your checkout

Earlier versions appended the registry line and the token to `.npmrc` in the workspace root. Six habits are affected:

- **A Dockerfile that runs `COPY .npmrc`.** The file is no longer in the build context. If your repository does not commit an `.npmrc`, the `COPY` now fails; if it does commit one, the build silently uses the committed file: with `registry=https://npm.flatt.tech/` in it, the install inside the container still goes through the proxy but anonymously, not attributed to your bot; without that line, it leaves the proxy. Replace the `COPY` with a build secret, as shown above.
- **A step that reads `$GITHUB_WORKSPACE/.npmrc`** -- for example to copy it into a subdirectory, or to strip it before committing. Those steps fail with "No such file or directory", which is loud rather than silent. They are also no longer needed: the configuration now applies from every directory, and the checkout is never modified.
- **A later step that appends to `$HOME/.npmrc`** with `echo ... >> ~/.npmrc`. That file is no longer the one npm reads, so the addition has no effect. `npm config set` is fine: it writes to whichever file `NPM_CONFIG_USERCONFIG` names.
- **A token committed in your project `.npmrc`** (`//npm.flatt.tech/:_authToken=...`, for example an API key from local development). Earlier versions replaced that line in the checkout. The checkout is now untouched, and a project-level entry outranks the user-level file, so npm, pnpm and Yarn Classic send the committed token instead of your bot's. Remove the line from the repository; the bot token then applies.
- **Installs late in a long job.** Every install in the job now uses the token, including ones in subdirectories, which earlier versions did not reach at all, and unscoped packages with bun and Yarn Berry, which earlier versions fetched anonymously. An install that runs after the token expires (`expires-in`, 30 minutes by default) fails with a 401 instead of silently succeeding without attribution. Raise `expires-in` if installs happen late in the job.
- **A self-hosted runner where another step already pointed `NPM_CONFIG_USERCONFIG` at `$HOME/.npmrc`.** The action then writes the token into that file, which outlives the job. The token is short-lived, but remove it if your runner is shared.

### One case this does not cover

A committed `.npmrc` with a **scoped** entry such as `@corp:registry=https://other.example/` keeps that scope on its own registry, because a scoped entry is a different configuration key. A committed default `registry=` line **is** overridden, since the environment outranks every npmrc file.

To confirm what your install will use, run `npm config get registry` (or `pnpm config get registry`) from the directory the install runs in. In a workspace, run it at the workspace root: inside an npm workspace package the command reports `ENOWORKSPACES`. The check that always holds is that the install itself resolves through `npm.flatt.tech`.

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
| `set-registry` | No | `true` | Set the registry URL. Set to `false` if you manage the registry yourself. |
| `always-auth` | No | `false` | Also send the token for unscoped packages with Yarn Classic. npm 11 and later warn about the setting on every command. See [Yarn Classic](#yarn-classic). |
| `registry-url` | No | `https://npm.flatt.tech` | Registry endpoint. |
| `sts-url` | No | `https://sts.cloud.shisho.dev` | STS endpoint for token exchange. |
| `expires-in` | No | `1800` | Token lifetime in seconds (max 86400). |
| `audience` | No | `https://sts.cloud.shisho.dev` (the STS URL) | Audience for the OIDC token request. Override when your Bot trust condition expects a different value. |

---

## Outputs

| Output | Description |
|---|---|
| `registry-url` | The npm registry URL. |
| `token` | The access token for the registry. Empty in anonymous mode. |
| `token-expires-at` | ISO 8601 timestamp of token expiration. Only set when authenticated. |
| `npmrc-path` | Absolute path of the `.npmrc` the action wrote: the path in `NPM_CONFIG_USERCONFIG` if it was already set, otherwise `$RUNNER_TEMP/.npmrc`. |

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
- **Outside your checkout** -- For npm/pnpm/Yarn v1, the action writes `$RUNNER_TEMP/.npmrc` with mode `600` and points npm at it through `NPM_CONFIG_USERCONFIG`. Your repository is untouched and the runner discards `$RUNNER_TEMP` when the job ends. `$HOME/.npmrc` is not written either, but it stops being read for the rest of the job, because that variable replaces it -- so the action copies its contents into the new file first.
- **Host-bound credentials for npm, pnpm and Yarn Classic** -- The token is written as `//npm.flatt.tech/:_authToken=`, which names the host, so those clients send it to the proxy and nowhere else. The file stays at mode `600`.
- **Yarn Berry and bun** -- The token is exported as `YARN_NPM_AUTH_TOKEN` and `BUN_CONFIG_TOKEN` via `$GITHUB_ENV`. These are job-scoped (visible to subsequent steps), short-lived and auto-masked, but they name no host: a step that points either client at another registry sends the token there, and so does a `yarn.lock` entry with `__archiveUrl`, as described in [Yarn Berry](#yarn-berry) and [bun](#bun).
- **Preserves scoped registries** -- Existing entries (e.g. `@myorg:registry=...`) are not overwritten, including entries that came from `$HOME/.npmrc` or from the file another action owns. Only the default `registry=` line and this proxy's own `_authToken` line are rewritten.

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

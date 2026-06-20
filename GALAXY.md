# Galaxy Node deployment

This repository is not a native Node app. The Node entrypoint only downloads and
starts the Linux CLIProxyAPI Pro release binary so Galaxy Node-only deployments
can run it.

## Start command

```bash
npm start
```

## Recommended environment

For a small 0.3c / 384 MB container, keep the no-plugin binary and smaller usage
query defaults:

```text
CLIPROXY_NO_PLUGIN=1
USAGE_BATCH_SIZE=20
USAGE_POLL_INTERVAL_MS=1000
USAGE_QUERY_LIMIT=5000
```

The launcher already uses these values by default. Set `CLIPROXY_NO_PLUGIN=0`
only if you need dynamic plugin support.

## Git-backed config and auths

CLIProxyAPI Pro supports the official git storage mode. Configure a private
repository for config/auth persistence:

```text
GITSTORE_GIT_URL=https://github.com/OWNER/PRIVATE_CONFIG_REPO.git
GITSTORE_GIT_USERNAME=OWNER
GITSTORE_GIT_TOKEN=github_pat_xxx
GITSTORE_GIT_BRANCH=main
```

When `GITSTORE_GIT_URL` is set, this launcher does not generate a local
`config.yaml` or pass `-config`; the CLIProxyAPI Pro binary clones the git store
and uses:

```text
config/config.yaml
auths/
```

Use a private repository and a fine-grained GitHub token scoped only to that
repository. Give it contents read/write permission when you want management
changes and refreshed auth files to be pushed back.

## Optional release pinning

By default the launcher downloads the latest release from:

```text
ssfun/CLIProxyAPI-Pro
```

Pin a version when you want stable redeploys:

```text
CLIPROXY_VERSION=v7.2.22-pro
```

If a previous binary was cached and you want to replace it, set this once:

```text
CLIPROXY_FORCE_DOWNLOAD=1
```

## Data paths

The Docker image stores usage data in `/CLIProxyAPI/usage`. This Galaxy launcher
uses writable project-local paths instead:

```text
USAGE_DATA_DIR=./usage
USAGE_DB_PATH=./usage/usage.sqlite
ACCOUNT_INSPECTION_SCHEDULE_PATH=./usage/account-inspection-schedule.json
```

Override these if your Galaxy app has a dedicated persistent volume path.

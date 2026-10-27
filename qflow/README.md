# PHP2Shell QFlow: running container to source repo

This QFlow closes the loop from a running container back to the repo that built it.

1. Qualys Container Security finds PHP2Shell (CVE-2026-109618 and CVE-2026-109619) in a running container. The upstream PHP QID is 389102. The Ubuntu QID is 6877310 (USN-8948-1), which is the one the demo image trips.
2. QFlow maps the container's image to the GitHub repo that built it and sends that repo a `repository_dispatch` event.
3. In `nelssec/pipeline-demo`, the workflow `.github/workflows/php2shell-remediate.yml` takes over:
   1. It confirms the finding with QScanner.
   2. It bumps the PHP base image to the fixed release.
   3. It rebuilds and rescans with QScanner.
   4. It opens a PR.

```
 Schedule (every 4 hours)
   -> CS integration: GET /containers  filter "state:RUNNING and (vulnerabilities.qid:389102 or vulnerabilities.qid:6877310)"
   -> Custom JS: image -> owner/repo (OCI source label, else ghcr.io path), one item per image
   -> HTTP: POST https://api.github.com/repos/{repo}/dispatches  event_type=qualys-php2shell
        -> GitHub Actions "PHP2Shell remediation (Qualys QFlow)"
             confirm (qscanner image) -> bump php/Dockerfile -> rebuild + rescan -> PR qualys/php2shell
        -> merge -> "Build and push PHP image" -> redeploy -> Qualys rescans -> QFlow finds nothing
```

QFlow has no inbound webhook trigger and no GitHub node (QFLOW-10883), so the flow polls on a schedule and calls GitHub through an HTTP node.

## Files

| File | What it is |
|---|---|
| `qflow/php2shell-repo-dispatch.qflow.json` | The QFlow, in the same shape as the qflow-playbooks-hub templates (`definition` is a JSON string of `components`) |
| `qflow/build-dispatches.js` | Source of the Custom node |
| `qflow/build-qflow.py` | Regenerates the JSON from the JS: `python3 qflow/build-qflow.py` |
| `php/Dockerfile` | The vulnerable workload: Ubuntu 24.04 with `php8.3` `8.3.6-0ubuntu0.24.04.12` (fixed in `.13`) |
| `.github/workflows/build-php.yml` | Builds `ghcr.io/nelssec/pipeline-demo/php-app` with OCI provenance labels and pushes it |
| `.github/workflows/php2shell-remediate.yml` | Receives the dispatch: confirm, bump, verify, open the PR |
| `.github/scripts/bump-php-base.py` | Moves `ARG PHP_PKG_VERSION` to the fixed Ubuntu build. It also rewrites a `FROM php:x.y.z-*` tag to 8.5.12, 8.4.27, 8.3.36 or 8.2.35 |
| `.github/scripts/count-php2shell.sh` | Counts PHP2Shell QIDs and CVEs in a QScanner `Report.json` |

## Nodes

| # | Node | Type | Settings |
|---|---|---|---|
| 1 | Trigger | `trigger` | Schedule every 4 hours (Quartz `0 0 0/4 1/1 * ? *`, the editor's minimum). Manual runs work too |
| 2 | CS: running containers with PHP2Shell | `integration-resource`, provider `cs` (proxies `/csapi/v1.3`, QAS auth) | `GET /containers`, `filter=state:RUNNING and (vulnerabilities.qid:389102 or vulnerabilities.qid:6877310)`, `pageSize=50` |
| 3 | Map image to source repo | `custom` | Builds one item per image: `repo`, `qid`, `image` (pinned by digest), `revision`, `container_id`, `host`. Drops repos that aren't in `ALLOWED_REPOS` (default `nelssec/pipeline-demo`) |
| 4 | GitHub repository_dispatch | `http`, `urlResolution: external` | `POST https://api.github.com/repos/obj.repo/dispatches`, Bearer auth, the headers below, and the body below |

Headers on node 4:

- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: 2022-11-28`
- `User-Agent: qualys-qflow-php2shell`

Body on node 4:

```json
{
  "event_type": "qualys-php2shell",
  "client_payload": {
    "qid": "obj.qid", "image": "obj.image", "revision": "obj.revision",
    "container_id": "obj.container_id", "host": "obj.host",
    "detected_by": "Qualys Container Security via QFlow"
  }
}
```

The `obj.*` values are QFlow mappings. They resolve per item from node 3, so the HTTP node sends one request per image (at most 20 per run, the HTTP node's collection limit). GitHub answers `204 No Content`.

### How the repo is found

The Custom node tries two sources, in this order:

1. **The `org.opencontainers.image.source` label.** `build-php.yml` and `build-and-gate.yml` stamp it on every image as `https://github.com/nelssec/pipeline-demo`.
2. **The image path.** A `ghcr.io/<owner>/<repo>/...` image maps to `<owner>/<repo>`.

The `org.opencontainers.image.revision` label, when the CS response carries it, goes into the payload as the commit that built the running image.

## Setup

### GitHub (`nelssec/pipeline-demo`)

1. Create a fine-grained token scoped to `nelssec/pipeline-demo` only, with **Contents: Read and write**. `repository_dispatch` requires write access. Give it a short expiry.
2. Check that the repo already has the `QUALYS_ACCESS_TOKEN` secret (and `QUALYS_POD` if it isn't CA1). The workflows read the same ones `build-and-gate.yml` uses.
3. Optional: set the repo variable `PHP2SHELL_QIDS` (comma separated) to add more per-distro QIDs. The default is `389102,6877310`. The CVE IDs are always matched too.
4. Under Settings → Actions → General, enable "Allow GitHub Actions to create and approve pull requests". The PR step needs it.
5. Run **Build and push PHP image** once. Deploy `ghcr.io/nelssec/pipeline-demo/php-app:latest` where Qualys sees it:
   - ECS Fargate with the CS sensor, or Fargate Scan 2.0 on the connected AWS account.
   - Or any cluster or host with the CS sensor.

   Make the GHCR package public, or give the task repository credentials.

### QFlow

1. In QFlow, **Import** `qflow/php2shell-repo-dispatch.qflow.json`.
2. **Node 2:** select your Container Security connection. The export can't carry a tenant's `integrationId` or `connection`. Re-select the API (`GET /containers`) if the editor doesn't show it. QFLOW-10028 says the CS node's config can disappear after a page refresh, so save straight after editing and reopen the node to check.
3. **Node 4:** paste the GitHub token into Bearer auth. The export deliberately has no token.
4. Ask the tenant admin to add `api.github.com` to the HTTP node domain allowlist. The worker rejects other hosts with "Hostname is not whitelisted".
5. **Run once manually,** then **Deploy**. The schedule only fires on a deployed QFlow.

## Test it without waiting for Qualys

You can send the event QFlow would send, by hand:

```bash
gh api repos/nelssec/pipeline-demo/dispatches \
  -f event_type=qualys-php2shell \
  -F 'client_payload[qid]=6877310' \
  -F 'client_payload[image]=ghcr.io/nelssec/pipeline-demo/php-app:latest' \
  -F 'client_payload[detected_by]=manual test'
```

Or run **PHP2Shell remediation (Qualys QFlow)** from the Actions tab, which uses `workflow_dispatch`.

Expected result: a PR on branch `qualys/php2shell` that changes `PHP_PKG_VERSION` in `php/Dockerfile` from `8.3.6-0ubuntu0.24.04.12` to `.13`. The PR body shows the before and after QScanner counts. Running the workflow again updates the same PR instead of opening a new one.

How the workflow handles other cases:

| Case | Result |
|---|---|
| The reported image no longer has PHP2Shell | Stops with a "stale finding" notice |
| `main` is already fixed | Notice that the workload needs a redeploy; no PR |
| An image the repo doesn't build | Refused |
| PHP older than 8.2 | Fails; there's no fixed release for that branch |

## Why the workload uses Ubuntu packages

The official `php:` images compile PHP from source. Neither QScanner nor Container Security inventories that, so PHP2Shell is never reported for `php:8.3.35-fpm-bookworm`. Tested on 2026-10-27, QScanner found only a brotli QID there.

Ubuntu's `php8.3` packages are inventoried. On 2026-10-27, QScanner (CA1) gave these results:

| Package build | Result |
|---|---|
| `8.3.6-0ubuntu0.24.04.12` | QID 6877310, severity 5, both PHP2Shell CVEs |
| `8.3.6-0ubuntu0.24.04.13` | Nothing |

Alpine and Debian already ship fixed builds, and the Ubuntu pool no longer has `.12`. That's why the Dockerfile pulls the `.debs` from Launchpad.

The confirm, bump, rebuild and rescan loop was run locally on that date with the same scripts the workflow uses:

- Before the bump: `hits=1`.
- After the bump: `hits=0`.
- A second bump does nothing.

## Not verified yet

Hand these to ROC Studio, or check them in the QFlow editor, before the demo:

- **Export format.** The JSON follows the playbooks-hub template shape and the `workflow-model` node types (`trigger`, `integration-resource`, `custom`, `http`), checked against the editor source in `workflow-ui-service`. It loads in the ROC Studio editor. It hasn't been imported into a production QFlow yet.

Three shapes in this JSON matter, from what the editor and worker read:

- **Schedule value.** A `rate` value must be a Quartz cron string with no parentheses. A value like `rate(15 minutes)` crashes the editor's trigger summary with "APPLICATION CRASHED".
- **Integration node.** The API goes in `resource`, not `api`.
- **HTTP headers.** These are an object map, not a list.
- **CS containers response.** It hasn't been confirmed that `vulnerabilities.qid` is accepted on `/containers`. If it isn't, use `/images` with the same filter and add a Filter node for running images. The container fields (`imageSha`, `image`, `labels`, `host`) and whether labels come back at all are also unconfirmed. The Custom node handles several field names and falls back to the GHCR image path, so the repo mapping still works without labels.
- **QFLOW-10501.** The HTTP node can return 401 with a valid key; the fix is targeted for 1.26.0. If node 4 gets 401, test the same token with the `gh api` command above to rule out the token itself.
- **Deploy.** Nothing in this repo deploys `php-app` to ECS yet. After the PR merges, `build-php.yml` publishes the fixed image. Rolling the service onto it (new task definition plus `aws ecs update-service --force-new-deployment`) is a manual step or a follow-up job.

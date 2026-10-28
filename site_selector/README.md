# Avi Controller Site Selector Manager

Adds Avi (VMware NSX Advanced Load Balancer) controller clusters to each other's
**Controller Site Selector** (the controller switcher in the top-right of the UI),
and can rename or delete existing entries. Each cluster is added using its Controller Cluster IP (VIP).

## Features
- Add new sites to existing controllers (or build a full mesh of all sites)
- Skips entries that already exist (same name or same address), so it is safe to re-run
- Rename existing site entries
- Delete site entries by name, with a confirmation prompt
- `--dry-run` previews every change without making it
- Separate username/password per cluster when targeting `all`
- Adds and renames never remove anything; deletes happen only when you pass `--delete`, and ask for confirmation

## Requirements
```bash
pip install -r requirements.txt
```
Python 3 with network access to each controller on port 443.

## Configuration
Clusters and settings live in a JSON file, not in the script. Copy the example and edit it:
```bash
cp clusters.example.json clusters.json
```
By default the script reads `clusters.json` next to itself; use `--config FILE` for another file.
`clusters.json` is listed in `.gitignore` so real controller addresses are not committed.

```json
{
  "avi_version": "30.2.3",
  "tenant": "admin",
  "verify_tls": false,
  "clusters": [
    {"name": "SITE-1", "login": "192.0.2.11", "vip": null},
    {"name": "SITE-NEW-1", "login": "192.0.2.21", "new": true, "vip": "controller-new-1.example.com"}
  ]
}
```

| Setting | Meaning |
|---------|---------|
| `avi_version` | API version sent to the controllers; must match the controller version (default `30.2.3`) |
| `tenant` | Avi tenant (default `admin`) |
| `verify_tls` | Verify controller TLS certificates (default `false`) |
| `clusters` | List of clusters, described below |

| Cluster field | Meaning |
|---------------|---------|
| `name` | Site name shown in the other controllers' switchers (must be unique) |
| `login` | IP used to reach the cluster's API. For 3-node clusters use the cluster VIP |
| `vip` | `null` (or omitted) reads the Controller Cluster IP from `/api/cluster`. Set a value to use it as-is (needed for single-node clusters that have no cluster IP) |
| `new` | `true` marks a site being **added**. Flagged sites are added only to the unflagged (existing) clusters, and are never logged into when `vip` is hardcoded |

The script stops with a clear message if the file is missing, is not valid JSON, has no clusters,
or a cluster lacks `name`/`login` or repeats a name. A wrong `avi_version` makes the API return
`400 Invalid version`.

## Embedded-config variant
`avi_site_selector_embedded.py` is the same script with the cluster list and settings written
inside the file (edit the `CONFIG` section at the top) instead of read from `clusters.json`.
It has no `--config` option and needs no extra file. Everything else is identical, so the rest of
this README applies to both. Use `avi_site_selector_vip.py` if you want to keep real controller
addresses out of the script file.

## Usage
```bash
python3 avi_site_selector_vip.py [--target NAME [NAME ...]] [--dry-run]
                                 [--config FILE] [--rename OLD=NEW [...]] [--no-add] [--full-mesh]
                                 [--delete NAME [...]] [--yes]
```

| Option | Description |
|--------|-------------|
| `--config FILE` | JSON file with the cluster list and settings (default: `clusters.json` next to the script) |
| `--target NAME [...]` | Clusters to modify. Case-insensitive; quote names containing spaces |
| `--target all` | Every eligible cluster, with a separate login per cluster |
| *(no `--target`)* | Shows a numbered menu |
| `--dry-run` | Show planned changes only |
| `--rename OLD=NEW [...]` | Rename existing entries on the targets, before any adds |
| `--no-add` | Skip adding sites (use with `--rename` for a rename-only run) |
| `--delete NAME [...]` | Delete the entries with these **exact** names from the targets. A delete run never adds sites. Asks for confirmation first |
| `--yes` | Skip the delete confirmation prompt (for non-interactive use) |
| `--full-mesh` | Ignore the `new` flags: every cluster is a target and gets every other cluster |

With `new: True` clusters defined, only the unflagged clusters can be targets. Without any
`new` flag, every cluster is added to every target.

### Credentials
- **Single target:** one login from `AVI_USER` / `AVI_PASSWORD`, or a prompt.
- **`--target all`:** one login per cluster from `AVI_USER_<NAME>` / `AVI_PASSWORD_<NAME>`
  (name upper-cased, non-alphanumerics replaced by `_`, e.g. `AVI_USER_SITE_1`), or a prompt per cluster.
- Passwords are never stored in the file. Prompts do not echo input.

### Examples
```bash
# Use a different config file
python3 avi_site_selector_vip.py --config other-env.json --target all --dry-run

# Add the new sites to one existing cluster
python3 avi_site_selector_vip.py --target SITE-1 --dry-run
python3 avi_site_selector_vip.py --target SITE-1

# Add the new sites to every existing cluster (prompts per cluster)
python3 avi_site_selector_vip.py --target all --dry-run
python3 avi_site_selector_vip.py --target all

# Full mesh: every cluster lists every other cluster
python3 avi_site_selector_vip.py --target all --full-mesh --dry-run

# Rename an entry (and add the new sites)
python3 avi_site_selector_vip.py --target SITE-1 --rename "OLD-NAME=NEW-NAME" --dry-run

# Rename only
python3 avi_site_selector_vip.py --target all --rename "OLD-NAME=NEW-NAME" --no-add

# Delete an entry: preview first, then run (asks you to type 'yes')
python3 avi_site_selector_vip.py --target SITE-1 --delete SITE-NEW-1 --dry-run
python3 avi_site_selector_vip.py --target SITE-1 --delete SITE-NEW-1
```
Always run with `--dry-run` first, then repeat without it and check the controller switcher in the UI.

### Deleting entries
- `--delete` removes entries whose name matches **exactly**. A name that doesn't exist on a target is skipped with a message.
- Run `--dry-run` first: it prints `WOULD DELETE name -> address` and changes nothing.
- Without `--yes`, the script lists what it is about to delete on each target and asks you to type `yes`; anything else cancels that target.
- A delete run does **not** add sites, so an entry you delete can't be re-added in the same run.
- Deletes happen before renames. A failed delete makes the script exit with status 1.
- Deleting is permanent; to restore an entry, add it again.

## Example dry-run output
```
Target(s): ['SITE-1']  (dry run)

[SITE-1] login OK (192.0.2.11)
[SITE-1] cluster VIP: 192.0.2.11

[SITE-1] existing sites: none
[SITE-1] WOULD ADD SITE-NEW-1 -> controller-new-1.example.com
[SITE-1] WOULD ADD SITE-NEW-2 -> controller-new-2.example.com
```

## Notes and limitations
- A site is skipped if its name or address is already present. The address of an existing
  name is not updated.
- Renames and deletes affect only the controllers you target.
- The local controller shows its own identity (node IP or cluster name) in the switcher; this
  script cannot change that. Only the other sites listed come from these entries.
- TLS verification is off by default (`VERIFY_TLS = False`). Set it to `True` if the controllers
  have trusted certificates.

## Troubleshooting
| Error | Meaning |
|-------|---------|
| `401 Unauthorized` on login | Wrong username or password for that cluster |
| `400 Invalid version` | `AVI_VERSION` does not match the controller version |
| Login timeout | Network or firewall (port 443) |
| `no Controller Cluster IP` | No cluster IP is configured; configure one or set `vip` in `CLUSTERS` |
| `Unknown target(s)` | Name typo, or a `new` site was targeted while the flags are on |

#!/usr/bin/env python3
"""
Add Avi Controller clusters to each other's Controller Site Selector,
one entry per cluster, using each cluster's Controller Cluster IP (VIP).

Flow:
  1. Log in to each cluster and read its VIP from /api/cluster.
     Stops if any cluster has no VIP (unless you set "vip" in CLUSTERS below).
  2. On each cluster, POST /api/controllersite for every OTHER cluster,
     skipping entries that already exist (same name or same address).
  3. Shows the final site list on each cluster.

The cluster list and settings are embedded in this script (see CONFIG below);
edit CLUSTERS before running.

Usage:
  python3 avi_site_selector_embedded.py --target SITE-1 --dry-run   # SITE-1 only, preview
  python3 avi_site_selector_embedded.py --target SITE-1             # SITE-1 only
  python3 avi_site_selector_embedded.py --target all             # every cluster
  python3 avi_site_selector_embedded.py                          # prompts for target
  (set AVI_USER / AVI_PASSWORD env vars, or you'll be prompted)
  python3 avi_site_selector_embedded.py --target "SITE-1" --rename "OLD=NEW" --dry-run
  python3 avi_site_selector_embedded.py --target all --rename "OLD=NEW" --no-add   # rename only
  python3 avi_site_selector_embedded.py --target all --full-mesh --dry-run   # every cluster <-> every cluster
  python3 avi_site_selector_embedded.py --target "SITE-1" --delete SITE-NEW-1 --dry-run   # preview a delete
  python3 avi_site_selector_embedded.py --target "SITE-1" --delete SITE-NEW-1 [--yes]     # asks to confirm
  With --target all, you're prompted for a username/password PER cluster
  (or set AVI_USER_<NAME> / AVI_PASSWORD_<NAME>, e.g. AVI_USER_SITE_1).

Note: only the selected target(s) are modified. Other clusters are logged into
(read-only) only when their VIP has to be looked up.
"""

import argparse
import getpass
import json
import os
import sys

import requests
import urllib3

# ---------------------------------------------------------------------------
# CONFIG - edit this section (replace the placeholder clusters with your own)
# ---------------------------------------------------------------------------
AVI_VERSION = "30.2.3"   # must match the controller version
TENANT = "admin"
VERIFY_TLS = False

# "name"  = site name shown in the other controllers' switchers (must be unique).
# "login" = any node IP used to reach the cluster's API (for 3-node clusters, the cluster VIP).
# "vip"   = optional manual override; None reads it from /api/cluster.
#           Set it for single-node clusters, which have no Controller Cluster IP.
# "new"   = True marks sites being ADDED. If any cluster is flagged, only the
#           flagged ones are added, and only to the unflagged (existing) clusters.
#           A flagged cluster with a hardcoded "vip" is never logged into.
#           Use --full-mesh to ignore the flags (all clusters <-> all clusters).
CLUSTERS = [
    # Existing sites (these are the targets that get modified):
    {"name": "SITE-1", "login": "192.0.2.11", "vip": None},
    {"name": "SITE-2", "login": "192.0.2.12", "vip": None},
    # New sites being added to the existing ones above:
    {"name": "SITE-NEW-1", "login": "192.0.2.21", "new": True, "vip": "controller-new-1.example.com"},
    {"name": "SITE-NEW-2", "login": "192.0.2.22", "new": True, "vip": "controller-new-2.example.com"},
]
# ---------------------------------------------------------------------------


class Avi:
    def __init__(self, host, user, password):
        self.host = host
        self.base = f"https://{host}"
        self.s = requests.Session()
        self.s.verify = VERIFY_TLS
        r = self.s.post(f"{self.base}/login",
                        json={"username": user, "password": password}, timeout=30)
        r.raise_for_status()
        self.s.headers.update({
            "X-Avi-Version": AVI_VERSION,
            "X-Avi-Tenant": TENANT,
            "X-CSRFToken": self.s.cookies.get("csrftoken", ""),
            "Referer": self.base,
            "Content-Type": "application/json",
        })

    def vip(self):
        r = self.s.get(f"{self.base}/api/cluster", timeout=30)
        r.raise_for_status()
        return r.json().get("virtual_ip", {}).get("addr", "")

    def sites(self):
        r = self.s.get(f"{self.base}/api/controllersite", timeout=30)
        r.raise_for_status()
        return r.json().get("results", [])

    def add_site(self, name, address, port=443):
        r = self.s.post(f"{self.base}/api/controllersite",
                        json={"name": name, "address": address, "port": port},
                        timeout=30)
        return r.status_code, r.text

    def rename_site(self, site, new_name):
        body = dict(site, name=new_name)
        r = self.s.put(f"{self.base}/api/controllersite/{site['uuid']}",
                       json=body, timeout=30)
        return r.status_code, r.text

    def delete_site(self, site):
        r = self.s.delete(f"{self.base}/api/controllersite/{site['uuid']}", timeout=30)
        return r.status_code, r.text

    def logout(self):
        try:
            self.s.post(f"{self.base}/logout", timeout=10)
        except requests.RequestException:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", nargs="+", metavar="NAME",
                    help="where to add sites: 'all' or one or more cluster names")
    ap.add_argument("--full-mesh", action="store_true",
                    help="ignore the 'new' flags: every cluster (old and new) is a "
                         "target and gets every other cluster added")
    ap.add_argument("--dry-run", action="store_true",
                    help="show planned changes without making them")
    ap.add_argument("--rename", nargs="+", metavar="OLD=NEW", default=[],
                    help="rename existing site entries on the target(s), e.g. "
                         "--rename 'OLD-NAME=NEW-NAME' (done before any adds)")
    ap.add_argument("--no-add", action="store_true",
                    help="skip adding sites (use with --rename for a rename-only run)")
    ap.add_argument("--delete", nargs="+", metavar="NAME", default=[],
                    help="delete existing site entries with these exact names from the "
                         "target(s); a delete run does not add sites (preview with --dry-run)")
    ap.add_argument("--yes", action="store_true",
                    help="don't ask for confirmation before deleting")
    args = ap.parse_args()

    renames = []
    for item in args.rename:
        old, sep, new = item.partition("=")
        if not sep or not old.strip() or not new.strip():
            sys.exit(f"Bad --rename value {item!r}; use OLD=NEW.")
        renames.append((old.strip(), new.strip()))

    new_clusters = [] if args.full_mesh else [c for c in CLUSTERS if c.get("new")]
    # With "new" sites flagged, only existing (unflagged) clusters can be targets
    names_all = [c["name"] for c in CLUSTERS if not (new_clusters and c.get("new"))]

    # Resolve target(s): from --target, or interactive menu
    if not args.target:
        print("Add the new sites to:")
        options = names_all + ["all"]
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        choice = input(f"Select [1-{len(options)}]: ").strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(options):
            sys.exit("Invalid selection.")
        args.target = [options[int(choice) - 1]]

    per_cluster_creds = any(t.lower() == "all" for t in args.target)
    if per_cluster_creds:
        targets = names_all
    else:
        lookup = {n.lower(): n for n in names_all}
        bad = [t for t in args.target if t.lower() not in lookup]
        if bad:
            sys.exit(f"Unknown target(s) {bad}. Choose from {names_all} or 'all'.")
        targets = [lookup[t.lower()] for t in args.target]
    print(f"Target(s): {targets}{'  (dry run)' if args.dry_run else ''}\n")

    if not VERIFY_TLS:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Shared credentials for single-target runs. With --target all, each cluster
    # gets its own: AVI_USER_<NAME>/AVI_PASSWORD_<NAME> (name upper-cased, non-
    # alphanumerics as "_", e.g. AVI_USER_SITE_1) or a prompt per cluster.
    shared = {}

    def creds_for(c):
        if not per_cluster_creds:
            if not shared:
                shared["user"] = os.environ.get("AVI_USER") or input("Avi username: ")
                shared["password"] = (os.environ.get("AVI_PASSWORD")
                                      or getpass.getpass("Avi password: "))
            return shared["user"], shared["password"]
        key = "".join(ch if ch.isalnum() else "_" for ch in c["name"].upper())
        user = os.environ.get(f"AVI_USER_{key}") or input(f"[{c['name']}] Avi username: ")
        password = (os.environ.get(f"AVI_PASSWORD_{key}")
                    or getpass.getpass(f"[{c['name']}] Avi password: "))
        return user, password

    # Step 1: log in where needed and resolve VIPs
    sessions = {}
    for c in CLUSTERS:
        is_source = c in (new_clusters or CLUSTERS)
        if c["name"] not in targets and not (is_source and not c["vip"]):
            continue  # neither modified nor needing a VIP lookup: no login needed
        user, password = creds_for(c)
        try:
            sessions[c["name"]] = Avi(c["login"], user, password)
            print(f"[{c['name']}] login OK ({c['login']})")
        except requests.RequestException as e:
            print(f"[{c['name']}] login FAILED ({c['login']}): {e}", file=sys.stderr)
            sys.exit(1)
        if not c["vip"]:
            c["vip"] = sessions[c["name"]].vip()
        print(f"[{c['name']}] cluster VIP: {c['vip'] or 'NOT CONFIGURED'}")

    missing = [c["name"] for c in CLUSTERS
               if not c["vip"] and (c["name"] in sessions or c in (new_clusters or CLUSTERS))]
    if missing:
        print(f"\nStopping: no Controller Cluster IP for {missing}. Configure one under "
              "Administration > Controller > Nodes, or set 'vip' in CLUSTERS.",
              file=sys.stderr)
        sys.exit(1)

    # Step 2: on each selected target, add every other cluster
    failures = 0
    for c in CLUSTERS:
        if c["name"] not in targets:
            continue
        avi = sessions[c["name"]]
        existing = avi.sites()
        names = {s["name"] for s in existing}
        addrs = {s["address"] for s in existing}
        print(f"\n[{c['name']}] existing sites: "
              f"{[(s['name'], s['address']) for s in existing] or 'none'}")

        to_delete = []
        for name in args.delete:
            entry = next((s for s in existing if s["name"] == name), None)
            if not entry:
                print(f"[{c['name']}] delete skipped: no entry named {name!r}")
            elif args.dry_run:
                print(f"[{c['name']}] WOULD DELETE {name} -> {entry['address']}")
            else:
                to_delete.append(entry)
        if to_delete and not args.yes:
            print(f"[{c['name']}] about to DELETE: "
                  f"{[(s['name'], s['address']) for s in to_delete]}")
            if input(f"[{c['name']}] type 'yes' to delete: ").strip().lower() != "yes":
                print(f"[{c['name']}] delete cancelled")
                to_delete = []
        for entry in to_delete:
            code, body = avi.delete_site(entry)
            if code in (200, 204):
                print(f"[{c['name']}] deleted {entry['name']} -> {entry['address']} (HTTP {code})")
                names.discard(entry["name"])
                addrs.discard(entry["address"])
            else:
                failures += 1
                print(f"[{c['name']}] FAILED delete {entry['name']}: HTTP {code} {body}",
                      file=sys.stderr)

        for old, new in renames:
            entry = next((s for s in existing if s["name"] == old), None)
            if not entry:
                print(f"[{c['name']}] rename skipped: no entry named {old!r}")
                continue
            if new in names:
                print(f"[{c['name']}] rename skipped: {new!r} already exists")
                continue
            if args.dry_run:
                print(f"[{c['name']}] WOULD RENAME {old} -> {new} ({entry['address']})")
                continue
            code, body = avi.rename_site(entry, new)
            if code in (200, 201):
                print(f"[{c['name']}] renamed {old} -> {new} (HTTP {code})")
                names.discard(old)
                names.add(new)
            else:
                failures += 1
                print(f"[{c['name']}] FAILED rename {old}: HTTP {code} {body}",
                      file=sys.stderr)

        for other in ([] if (args.no_add or args.delete) else (new_clusters or CLUSTERS)):
            if other is c:
                continue
            if other["name"] in names or other["vip"] in addrs:
                print(f"[{c['name']}] skip {other['name']} -> {other['vip']} (already present)")
                continue
            if args.dry_run:
                print(f"[{c['name']}] WOULD ADD {other['name']} -> {other['vip']}")
                continue
            code, body = avi.add_site(other["name"], other["vip"])
            if code in (200, 201):
                print(f"[{c['name']}] added {other['name']} -> {other['vip']} (HTTP {code})")
            else:
                failures += 1
                print(f"[{c['name']}] FAILED {other['name']}: HTTP {code} {body}",
                      file=sys.stderr)

    # Step 3: show final state
    if not args.dry_run:
        print("\nFinal site lists:")
        for c in CLUSTERS:
            if c["name"] not in targets:
                continue
            print(f"[{c['name']}] " + json.dumps(
                [(s["name"], s["address"]) for s in sessions[c["name"]].sites()]))

    for avi in sessions.values():
        avi.logout()

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

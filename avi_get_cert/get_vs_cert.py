#!/usr/bin/env python3
"""
List Avi virtual services together with their assigned SSL certificates.

Read-only: logs in and issues GET requests only.

Usage:
  python get_vs_cert.py --controller CTRL                       # admin tenant
  python get_vs_cert.py --controller CTRL --cert-filter wildcard
  python get_vs_cert.py --controller CTRL --tenant prod dev     # several tenants
  python get_vs_cert.py --controller CTRL --all-tenants --show-profile
  (set AVI_USER / AVI_PASSWORD env vars, or you'll be prompted)
"""

import argparse
import getpass
import os
import sys

import requests
import urllib3
from tabulate import tabulate

TIMEOUT = 30
PAGE_SIZE = 200


def login(controller, username, password, verify):
    session = requests.Session()
    session.verify = verify
    try:
        response = session.post(f"https://{controller}/login",
                                json={"username": username, "password": password},
                                timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}", file=sys.stderr)
        return None
    print("Login successful.\n")
    return session


def logout(session, controller):
    try:
        session.post(f"https://{controller}/logout", timeout=10)
    except requests.exceptions.RequestException:
        pass


def detect_version(session, controller):
    """Return the controller's API version (e.g. '30.2.3'), or None."""
    try:
        response = session.get(f"https://{controller}/api/initial-data", timeout=TIMEOUT)
        response.raise_for_status()
        return response.json().get("version", {}).get("Version")
    except (requests.exceptions.RequestException, ValueError):
        return None


def get_all(session, url, headers, params=None):
    """GET every page of a list endpoint and return the combined results."""
    params = dict(params or {}, page_size=PAGE_SIZE)
    results = []
    page = 1
    while True:
        params["page"] = page
        response = session.get(url, headers=headers, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("next"):
            return results
        page += 1


def ref_name(ref):
    """Name part of an Avi reference. With include_name=true refs look like '<url>#<name>'."""
    if isinstance(ref, dict):
        ref = ref.get("ref")
    if not ref:
        return "Unknown"
    return ref.split("#")[-1] if "#" in ref else ref


def get_tenants(session, controller, headers):
    results = get_all(session, f"https://{controller}/api/tenant", headers,
                      {"fields": "name"})
    return sorted(t["name"] for t in results)


def get_vs_rows(session, controller, tenant, headers, cert_filter, show_profile):
    fields = "name,ssl_key_and_certificate_refs"
    if show_profile:
        fields += ",ssl_profile_ref"
    vs_list = get_all(session, f"https://{controller}/api/virtualservice",
                      dict(headers, **{"X-Avi-Tenant": tenant}),
                      {"include_name": "true", "fields": fields})

    rows = []
    for vs in vs_list:
        ssl_refs = vs.get("ssl_key_and_certificate_refs", [])
        if not ssl_refs:
            continue
        profile = ref_name(vs.get("ssl_profile_ref")) if vs.get("ssl_profile_ref") else ""
        for ssl in ssl_refs:
            cert_name = ref_name(ssl)
            if cert_filter and cert_filter.lower() not in cert_name.lower():
                continue
            rows.append([tenant, vs.get("name"), cert_name, profile])
    return sorted(rows, key=lambda r: (r[0], str(r[1]), r[2]))


def main():
    parser = argparse.ArgumentParser(
        description="Get Avi Virtual Services and assigned SSL certs (session auth, table output).")
    parser.add_argument("--controller", required=True, help="Avi controller IP or FQDN")
    parser.add_argument("--tenant", nargs="+", default=["admin"], metavar="TENANT",
                        help="Avi tenant(s) to query (default: admin)")
    parser.add_argument("--all-tenants", action="store_true",
                        help="query every tenant (overrides --tenant)")
    parser.add_argument("--cert-filter", help="Filter VSs by certificate name")
    parser.add_argument("--show-profile", action="store_true",
                        help="also show each VS's SSL profile")
    parser.add_argument("--api-version",
                        help="X-Avi-Version header (default: auto-detect from the controller)")
    parser.add_argument("--verify-tls", action="store_true",
                        help="verify the controller's TLS certificate")
    parser.add_argument("--ca-bundle", help="CA bundle file to verify against (implies --verify-tls)")
    args = parser.parse_args()

    verify = args.ca_bundle or args.verify_tls
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    username = os.environ.get("AVI_USER") or input("Enter Avi username: ")
    password = os.environ.get("AVI_PASSWORD") or getpass.getpass("Enter Avi password: ")

    session = login(args.controller, username, password, verify)
    if not session:
        print("Exiting due to login failure.", file=sys.stderr)
        return 1

    failed = False
    try:
        version = args.api_version or detect_version(session, args.controller)
        headers = {"Content-Type": "application/json"}
        if version:
            headers["X-Avi-Version"] = version

        tenants = args.tenant
        if args.all_tenants:
            try:
                tenants = get_tenants(session, args.controller, dict(headers, **{"X-Avi-Tenant": "admin"}))
            except requests.exceptions.RequestException as e:
                print(f"Error retrieving tenant list: {e}", file=sys.stderr)
                return 1

        rows = []
        for tenant in tenants:
            try:
                rows.extend(get_vs_rows(session, args.controller, tenant, headers,
                                        args.cert_filter, args.show_profile))
            except requests.exceptions.RequestException as e:
                failed = True
                print(f"Error retrieving VS list for tenant {tenant!r}: {e}", file=sys.stderr)

        if rows:
            columns = [(0, "Tenant"), (1, "Virtual Service"), (2, "SSL Certificate"), (3, "SSL Profile")]
            if len(tenants) < 2:
                columns.remove((0, "Tenant"))
            if not args.show_profile:
                columns.remove((3, "SSL Profile"))
            print(tabulate([[r[i] for i, _ in columns] for r in rows],
                           headers=[name for _, name in columns], tablefmt="grid"))
        elif not failed:
            print("No matching Virtual Services found.")
    finally:
        logout(session, args.controller)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

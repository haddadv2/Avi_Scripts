import os
import sys
import csv
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_token(controller, username, password):
    url = f"https://{controller}/login"
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, verify=False, timeout=30)
        r.raise_for_status()
    except Exception as e:
        sys.exit(f"[ERROR] Login failed on {controller}: {e}")
    return r.cookies.get("csrftoken"), r.cookies.get("sessionid")

def fetch_tenants(controller, token, sessionid):
    url = f"https://{controller}/api/tenant"
    headers = {
        "X-CSRFToken": token,
        "Referer": f"https://{controller}/",
    }
    cookies = {
        "csrftoken": token,
        "sessionid": sessionid,
    }
    r = requests.get(url, headers=headers, cookies=cookies, verify=False, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def fetch_virtual_services(controller, token, sessionid, tenant_uuid):
    url = f"https://{controller}/api/virtualservice?tenant_uuid={tenant_uuid}"
    headers = {
        "X-CSRFToken": token,
        "Referer": f"https://{controller}/",
    }
    cookies = {
        "csrftoken": token,
        "sessionid": sessionid,
    }
    r = requests.get(url, headers=headers, cookies=cookies, verify=False, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def fetch_gslb_services(controller, token, sessionid, tenant_uuid):
    url = f"https://{controller}/api/gslbservice?tenant_uuid={tenant_uuid}"
    headers = {
        "X-CSRFToken": token,
        "Referer": f"https://{controller}/",
    }
    cookies = {
        "csrftoken": token,
        "sessionid": sessionid,
    }
    r = requests.get(url, headers=headers, cookies=cookies, verify=False, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def delete_tenant(controller, token, sessionid, tenant_url):
    headers = {
        "X-CSRFToken": token,
        "Referer": f"https://{controller}/",
    }
    cookies = {
        "csrftoken": token,
        "sessionid": sessionid,
    }
    r = requests.delete(tenant_url, headers=headers, cookies=cookies, verify=False, timeout=30)
    if r.status_code not in [200, 204]:
        print(f"❌ Failed to delete tenant {tenant_url}: {r.status_code} - {r.text}")
    else:
        print(f"✅ Deleted tenant: {tenant_url}")

def show_tenants(controller, tenants, title):
    print(f"\n📋 {title} ({controller})")
    print("---------------------------------------------------")
    for t in tenants:
        print(f" - {t['name']} ({t['uuid']})")
    print(f"Total tenants: {len(tenants)}\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Delete empty tenants from multiple Avi controllers")
    parser.add_argument("--csv", help="CSV file with controller IPs")
    parser.add_argument("--controller", help="Run cleanup for specific controller only", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (no deletion)")
    args = parser.parse_args()

    username = os.getenv("AVI_USERNAME")
    password = os.getenv("AVI_PASSWORD")

    if not username or not password:
        sys.exit("❌ Missing environment variables AVI_USERNAME or AVI_PASSWORD")

    controllers = []
    if args.controller:
        controllers = [args.controller]
    elif args.csv:
        with open(args.csv) as f:
            reader = csv.reader(f)
            controllers = [row[0].strip() for row in reader if row]
    else:
        sys.exit("❌ Must specify either --csv or --controller")

    summary = []

    for controller in controllers:
        print(f"\n🔍 Starting Avi tenant cleanup on {controller} (Dry-Run={args.dry_run})")
        print("---------------------------------------------------")
        token, sessionid = get_token(controller, username, password)
        tenants_before = fetch_tenants(controller, token, sessionid)
        show_tenants(controller, tenants_before, "Existing tenants BEFORE cleanup")

        deleted_tenants = []
        for tenant in tenants_before:
            name = tenant["name"]
            uuid = tenant["uuid"]
            if name.lower() == "admin":
                continue  # Skip admin tenant

            vs_count = len(fetch_virtual_services(controller, token, sessionid, uuid))
            gslb_count = len(fetch_gslb_services(controller, token, sessionid, uuid))

            print(f"Tenant '{name}': VS={vs_count}, GSLB={gslb_count}")
            if vs_count == 0 and gslb_count == 0:
                if args.dry_run:
                    print(f"🟡 [DRY-RUN] Would delete tenant: {name}")
                    deleted_tenants.append(name + " (dry-run)")
                else:
                    delete_tenant(controller, token, sessionid, tenant["url"])
                    deleted_tenants.append(name)

        tenants_after = fetch_tenants(controller, token, sessionid)
        show_tenants(controller, tenants_after, "Existing tenants AFTER cleanup")

        deleted_count = len(deleted_tenants)
        summary.append({
            "controller": controller,
            "before": len(tenants_before),
            "after": len(tenants_after),
            "deleted": deleted_count,
        })

        if args.dry_run:
            print(f"✅ Dry-run completed on {controller}. No actual tenants deleted.")
        else:
            print(f"✅ Cleanup completed on {controller}. Deleted tenants: {deleted_tenants or 'None'}")

    # --- Summary Section ---
    print("\n\n📊 SUMMARY REPORT")
    print("===================================================")
    print(f"{'Controller':<20} {'Before':<10} {'After':<10} {'Deleted':<10}")
    print("---------------------------------------------------")
    for entry in summary:
        print(f"{entry['controller']:<20} {entry['before']:<10} {entry['after']:<10} {entry['deleted']:<10}")
    print("===================================================\n")
    print("🏁 All controller cleanups completed.\n")

if __name__ == "__main__":
    main()

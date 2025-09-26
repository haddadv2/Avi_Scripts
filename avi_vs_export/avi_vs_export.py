#!/usr/bin/env python3
import argparse
import requests
import pandas as pd
from urllib.parse import urlparse
import sys

def get_token(controller, version, username, password):
    url = f"https://{controller}/login"
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, verify=False, timeout=30)
        r.raise_for_status()
    except Exception as e:
        sys.exit(f"[ERROR] Login failed: {e}")
    return r.cookies.get("csrftoken"), r.cookies.get("sessionid")

def fetch_virtual_services(controller, version, token, sessionid, limit=None, cloud_filter=None):
    headers = {
        "X-CSRFToken": token,
        "Referer": f"https://{controller}/",
    }
    cookies = {
        "csrftoken": token,
        "sessionid": sessionid,
    }

    vs_list = []
    url = f"https://{controller}/api/virtualservice/?include_name&page_size=100"
    fetched = 0

    while url:
        r = requests.get(url, headers=headers, cookies=cookies, verify=False, timeout=60)
        r.raise_for_status()
        data = r.json()
        for vs in data.get("results", []):
            if limit and fetched >= limit:
                return vs_list
            cloud_name = vs.get("cloud_ref", "").split("#")[-1] if vs.get("cloud_ref") else ""
            if cloud_filter and cloud_filter.lower() not in cloud_name.lower():
                continue

            # VIP IPs
            vip_ips = []
            for vip in vs.get("vip_runtime", []):
                for intf in vip.get("se_list", []):
                    for v in intf.get("vip_intf_list", []):
                        vip_ips.append(v["vip_intf_ip"]["addr"])

            # SE names
            se_names = []
            for vip in vs.get("vip_runtime", []):
                for se in vip.get("se_list", []):
                    if "se_ref" in se:
                        se_names.append(se["se_ref"].split("#")[-1])

            vs_list.append({
                "VS Name": vs.get("name"),
                "VIP IP": ", ".join(set(vip_ips)) if vip_ips else "N/A",
                "Service Engines": ", ".join(set(se_names)) if se_names else "N/A",
                "Cloud": cloud_name or "N/A"
            })
            fetched += 1

        url = data.get("next")  # pagination link
        if url and not url.startswith("http"):
            url = f"https://{controller}{url}"

    return vs_list

def main():
    parser = argparse.ArgumentParser(description="Export Avi Virtual Services to Excel")
    parser.add_argument("-c", "--controller", required=True, help="Controller IP or FQDN (without https://)")
    parser.add_argument("-v", "--version", required=True, help="API version (e.g. 22.1.3)")
    parser.add_argument("-u", "--username", required=True, help="Username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument("-o", "--output", default="avi_virtual_services.xlsx", help="Output Excel filename")
    parser.add_argument("-n", "--number", type=int, help="Optional limit on number of Virtual Services")
    parser.add_argument("--cloud", help="Optional Cloud name filter")
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    print(f"[+] Logging in to {args.controller}...")
    token, sessionid = get_token(args.controller, args.version, args.username, args.password)

    print("[+] Fetching virtual services...")
    vs_list = fetch_virtual_services(args.controller, args.version, token, sessionid,
                                     limit=args.number, cloud_filter=args.cloud)

    if not vs_list:
        sys.exit("[!] No Virtual Services found with the given filters.")

    print(f"[+] Writing {len(vs_list)} entries to {args.output}")
    df = pd.DataFrame(vs_list)
    df.to_excel(args.output, index=False)

if __name__ == "__main__":
    main()


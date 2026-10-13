#!/usr/bin/env python3

import requests
import argparse
import urllib3
import getpass
from tabulate import tabulate

# Disable SSL warnings for self-signed certs (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def login(controller, username, password):
    url = f"https://{controller}/login"
    payload = {'username': username, 'password': password}

    session = requests.Session()
    try:
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        print("Login successful.\n")
        return session
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        return None

def get_vs_list(session, controller, tenant, cert_filter=None):
    url = f"https://{controller}/api/virtualservice?include_name=true&fields=ssl_key_and_certificate_refs&page_size=200&page=1"
    headers = {
        'Content-Type': 'application/json',
        'X-Avi-Tenant': tenant
    }

    try:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving VS list: {e}")
        return

    vs_list = response.json().get('results', [])

    table_data = []
    for vs in vs_list:
        vs_name = vs.get('name')
        ssl_refs = vs.get('ssl_key_and_certificate_refs', [])

        if not ssl_refs:
            continue

        for ssl in ssl_refs:
            # Handle both dict and string types in ssl_refs
            if isinstance(ssl, dict):
                cert_uri = ssl.get('ref')
            elif isinstance(ssl, str):
                cert_uri = ssl
            else:
                cert_uri = None

            if cert_uri:
                # Extract only the string after '#' if present
                cert_name = cert_uri.split('#')[-1] if '#' in cert_uri else cert_uri
            else:
                cert_name = "Unknown"

            if cert_filter:
                if cert_filter.lower() in cert_name.lower():
                    table_data.append([vs_name, cert_name])
            else:
                table_data.append([vs_name, cert_name])

    if table_data:
        print(tabulate(table_data, headers=["Virtual Service", "SSL Certificate"], tablefmt="grid"))
    else:
        print("No matching Virtual Services found.")

def main():
    parser = argparse.ArgumentParser(description="Get Avi Virtual Services and assigned SSL certs (session auth, table output).")
    parser.add_argument('--controller', required=True, help='Avi controller IP or FQDN')
    parser.add_argument('--tenant', default='admin', help='Avi tenant (default: admin)')
    parser.add_argument('--cert-filter', help='Filter VSs by certificate name')

    args = parser.parse_args()

    # Prompt for username and password securely
    username = input("Enter Avi username: ")
    password = getpass.getpass("Enter Avi password: ")

    # Login to obtain session
    session = login(args.controller, username, password)
    if not session:
        print("Exiting due to login failure.")
        return

    # Get VS list with SSL certs in table format
    get_vs_list(session, args.controller, args.tenant, args.cert_filter)

if __name__ == "__main__":
    main()

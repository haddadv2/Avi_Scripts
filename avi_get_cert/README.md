# Avi Virtual Service SSL Certificate Lister

Lists the **virtual services** on an Avi (VMware NSX Advanced Load Balancer) controller together
with the **SSL certificate(s)** assigned to each one, as a table. It can filter by certificate name,
which makes it handy for finding every VS that uses a certificate that is about to expire or be replaced.

The script is **read-only**: it only logs in and runs `GET` requests.

## Features
- Reads **all** virtual services (follows every page of results)
- One row per VS / certificate pair, so a VS with several certificates appears several times
- Optional case-insensitive filter on the certificate name
- One tenant, several tenants, or **all tenants** in a single run
- Optional SSL profile column
- Detects the controller's API version automatically (or set it yourself)
- Interactive or non-interactive credentials; logs out when finished

## Requirements
```bash
pip install -r requirements.txt
```
Python 3 and network access to the controller on port 443.

## Usage
```bash
python get_vs_cert.py --controller CONTROLLER [--tenant TENANT [TENANT ...] | --all-tenants]
                      [--cert-filter TEXT] [--show-profile] [--api-version VERSION]
                      [--verify-tls] [--ca-bundle FILE]
```

**Parameters:**
- `--controller` : Avi controller IP or FQDN (required)
- `--tenant` : One or more tenants to query (default: `admin`)
- `--all-tenants` : Query every tenant (overrides `--tenant`); the output gains a Tenant column
- `--cert-filter` : Only show rows whose certificate name contains this text (case-insensitive)
- `--show-profile` : Also show each virtual service's SSL profile
- `--api-version` : `X-Avi-Version` header to send (default: detected from the controller)
- `--verify-tls` : Verify the controller's TLS certificate (off by default, for self-signed certs)
- `--ca-bundle` : CA bundle file to verify against (implies `--verify-tls`)

### Credentials
The username and password are prompted when the script runs, so they never appear in the command
line or shell history. For non-interactive use, set `AVI_USER` and `AVI_PASSWORD` instead.

### Examples
```bash
# All VSs and their certificates in the admin tenant
python get_vs_cert.py --controller 10.10.10.10

# Only VSs using a certificate with "wildcard" in its name
python get_vs_cert.py --controller 10.10.10.10 --cert-filter wildcard

# Several tenants, with the SSL profile column
python get_vs_cert.py --controller avi.example.com --tenant prod dev --show-profile

# Every tenant on the controller
python get_vs_cert.py --controller avi.example.com --all-tenants --cert-filter 2024

# Verify the controller certificate against your CA
python get_vs_cert.py --controller avi.example.com --ca-bundle /path/to/ca.pem
```

## Output
```
+-------------------+-------------------+
| Virtual Service   | SSL Certificate   |
+===================+===================+
| vs-api-01         | app-cert          |
+-------------------+-------------------+
| vs-web-01         | wildcard-2026     |
+-------------------+-------------------+
```
Rows are sorted by tenant, then VS name. Virtual services with no certificate are not listed. If
nothing matches, the script prints `No matching Virtual Services found.`

The exit code is `0` on success and `1` if the login fails or any tenant could not be read. A
tenant that fails is reported on stderr and the other tenants are still shown.

## How it works
1. Logs in with `POST /login` and keeps the session.
2. Reads the controller version from `/api/initial-data` (unless `--api-version` is given) and
   sends it as `X-Avi-Version`.
3. For each tenant, calls `GET /api/virtualservice?include_name=true&fields=name,ssl_key_and_certificate_refs`
   with the `X-Avi-Tenant` header, following pages until there are no more. With `--all-tenants`
   the tenant list comes from `GET /api/tenant`.
4. For each VS, reads `ssl_key_and_certificate_refs`. With `include_name=true` each reference is
   `<url>#<name>`, and the part after `#` is shown as the certificate name.
5. Applies the optional filter, prints the table, then logs out.

## Limitations
- Only the virtual service's own server certificates (`ssl_key_and_certificate_refs`) are listed.
  CA / PKI profile certificates and certificates referenced elsewhere (pools, application
  profiles) are not included. `--show-profile` shows the SSL profile's **name** only.
- If a reference has no `#name` part, the full reference URL is shown instead of a name.
- TLS verification is off unless you pass `--verify-tls` or `--ca-bundle`.
- `--all-tenants` needs a user that is allowed to list tenants.

# Avi Virtual Service SSL Certificate Lister

Lists the **virtual services** on an Avi (VMware NSX Advanced Load Balancer) controller together
with the **SSL certificate(s)** assigned to each one, as a table. It can filter by certificate name,
which makes it handy for finding every VS that uses a certificate that is about to expire or be replaced.

The script is **read-only**: it only logs in and runs `GET` requests.

## Features
- Session (username/password) authentication, with the password prompted securely
- Shows one row per VS / certificate pair, so a VS with several certificates appears several times
- Optional case-insensitive filter on the certificate name
- Works per tenant (`--tenant`)

## Requirements
```bash
pip install -r requirements.txt
```
Python 3 and network access to the controller on port 443.

## Usage
```bash
python get_vs_cert.py --controller CONTROLLER [--tenant TENANT] [--cert-filter TEXT]
```

**Parameters:**
- `--controller` : Avi controller IP or FQDN (required)
- `--tenant` : Avi tenant (default: `admin`)
- `--cert-filter` : Only show rows whose certificate name contains this text (case-insensitive)

The username and password are prompted when the script runs, so they never appear in the command
line or shell history.

Examples:
```bash
# All VSs and their certificates in the admin tenant
python get_vs_cert.py --controller 10.10.10.10

# Only VSs using a certificate with "wildcard" in its name
python get_vs_cert.py --controller 10.10.10.10 --cert-filter wildcard

# A different tenant
python get_vs_cert.py --controller avi.example.com --tenant prod
```

## Output
```
+-------------------+-------------------+
| Virtual Service   | SSL Certificate   |
+===================+===================+
| vs-web-01         | wildcard-2026     |
+-------------------+-------------------+
| vs-api-01         | app-cert          |
+-------------------+-------------------+
```
Virtual services with no certificate are not listed. If nothing matches, the script prints
`No matching Virtual Services found.`

## How it works
1. Logs in with `POST /login` and keeps the session.
2. Calls `GET /api/virtualservice?include_name=true&fields=ssl_key_and_certificate_refs&page_size=200&page=1`
   with the `X-Avi-Tenant` header.
3. For each VS, reads `ssl_key_and_certificate_refs`. With `include_name=true` each reference is
   `<url>#<name>`, and the part after `#` is shown as the certificate name.
4. Applies the optional filter and prints the table.

## Limitations
- **Only the first 200 virtual services** are read (`page_size=200&page=1`). There is no paging,
  so larger tenants are truncated.
- **One tenant per run.** Use `--tenant` for each tenant you need.
- Only the virtual service's own certificates (`ssl_key_and_certificate_refs`) are checked, not
  SSL profiles or CA certificates.
- TLS verification is disabled (`verify=False`), and the script does not set an `X-Avi-Version`
  header, so the controller's default API version is used.
- If a reference has no `#name` part, the full reference URL is shown instead of a name.
- There is no username/password option for non-interactive use.

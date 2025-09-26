# Avi Virtual Services Exporter

This Python script connects to an Avi (VMware NSX Advanced Load Balancer) controller,
authenticates using username/password to obtain an API token, and exports virtual
service details to an Excel file.

## Features
- Authenticate using username/password and retrieve a session token
- List all virtual services (with optional limit and cloud filter)
- Export details (Virtual Service name, IP address, Service Engines, Cloud name) to an Excel file

## Requirements
Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python avi_vs_exporter.py -u USERNAME -p PASSWORD -c CONTROLLER_IP -v CONTROLLER_VERSION [-n LIMIT] [-C CLOUD_NAME] [-o OUTPUT_FILE]
```

**Parameters:**
- `-u`, `--username` : Avi controller username (required)
- `-p`, `--password` : Avi controller password (required)
- `-c`, `--controller` : Avi controller IP address (required)
- `-v`, `--version` : Avi API version (required)
- `-n`, `--number` : (Optional) Maximum number of virtual services to export
- `-C`, `--cloud` : (Optional) Filter by cloud name
- `-o`, `--output` : (Optional) Output Excel file name (default: avi_virtual_services.xlsx)

Example:
```bash
python avi_vs_exporter.py -u admin -p MyPass123 -c 10.10.10.10 -v 22.1.3 -n 50 -C Default-Cloud
```

## Output
The script generates an Excel file containing columns:
- Virtual Service Name
- IP Address
- Service Engines
- Cloud Name

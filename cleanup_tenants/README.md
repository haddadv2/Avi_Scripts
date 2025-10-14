# 🧹 Avi Load Balancer — Empty Tenant Cleanup Tool

This tool automates the process of identifying and deleting **empty tenants** (with **0 Virtual Services** and **0 GSLB Services**) from one or more **Avi Load Balancer (NSX Advanced Load Balancer)** controllers.

It supports:
- 🔄 **Dry-run mode** (safe simulation)
- 🗑️ **Actual cleanup**
- 🧭 Multiple controllers from a CSV file
- 🎯 Single controller targeting
- 📊 Summary report showing before/after tenant counts
- 🪶 Integration with **Ansible** for automated or scheduled cleanup jobs

---

## 📁 Repository Contents

```
cleanup_tenants/
├── cleanup_empty_tenants.py     # Main Python script
├── controllers.csv              # List of Avi Controller IPs
├── delete_empty_tenants.yml     # Ansible playbook to run the script
├── README.md                    # This documentation
└── env/                         # (optional) Python virtual environment folder
```

---

## ⚙️ Prerequisites

- Python **3.8+**
- Access to Avi Controller(s) with an account that can:
  - List tenants
  - Delete tenants (if not in dry-run mode)
- `requests` Python library  
- (Optional) **Ansible** for automation

---

## 🧰 Installation

### 1️⃣ Clone or copy the project

```bash
git clone https://github.com/<your-repo>/cleanup_tenants.git
cd cleanup_tenants
```

### 2️⃣ Create & activate a Python virtual environment

```bash
python3 -m venv env
source env/bin/activate
```

### 3️⃣ Install required libraries

```bash
pip install requests
```

---

## 🔐 Environment Variables

Before running the script or playbook, export your Avi credentials:

```bash
export AVI_USERNAME="admin"
export AVI_PASSWORD="MySecurePassword"
```

You can also store these in a `.env` file and load them automatically:

```bash
# .env
AVI_USERNAME=admin
AVI_PASSWORD=MySecurePassword
```

Load them with:
```bash
source .env
```

---

## 📋 Controller List (CSV)

`controllers.csv` should contain one controller IP per line, for example:

```
10.10.10.248
10.10.10.249
10.10.10.250
```

---

## 🚀 Running the Python Script

### 🧪 Dry-Run Mode (Safe Simulation)
```bash
python3 cleanup_empty_tenants.py --csv controllers.csv --dry-run
```

This lists tenants and shows which would be deleted **without actually deleting anything.**

### ⚡ Real Cleanup
```bash
python3 cleanup_empty_tenants.py --csv controllers.csv
```

### 🎯 Run Against a Single Controller
```bash
python3 cleanup_empty_tenants.py --controller 10.10.10.248 --dry-run
```

---

## 📊 Output Example

```
🔍 Starting Avi tenant cleanup on 10.10.10.248 (Dry-Run=True)
---------------------------------------------------
📋 Existing tenants BEFORE cleanup (10.10.10.248)
 - admin (tenant-1)
 - demo (tenant-2)
 - test (tenant-3)
Total tenants: 3

Tenant 'demo': VS=0, GSLB=0
🟡 [DRY-RUN] Would delete tenant: demo
Tenant 'test': VS=2, GSLB=0

📋 Existing tenants AFTER cleanup (10.10.10.248)
 - admin
 - demo
 - test
Total tenants: 3

📊 SUMMARY REPORT
===================================================
Controller           Before     After      Deleted
---------------------------------------------------
10.10.10.248       3          3          1
===================================================

🏁 All controller cleanups completed.
```

---

## 🤖 Running via Ansible Playbook

### Playbook: `delete_empty_tenants.yml`

```yaml
---
- name: Delete empty tenants from Avi Controllers
  hosts: localhost
  gather_facts: no

  vars:
    dry_run: true
    log_file: "{{ playbook_dir }}/delete_empty_tenants.log"

  tasks:
    - name: Run Python cleanup script and save output
      ansible.builtin.shell: >
        python3 cleanup_empty_tenants.py
        --csv controllers.csv
        {% if not dry_run|bool %} {% else %} --dry-run {% endif %}
        2>&1 | tee "{{ log_file }}"
      args:
        chdir: "{{ playbook_dir }}"
      environment:
        AVI_USERNAME: "{{ lookup('env','AVI_USERNAME') }}"
        AVI_PASSWORD: "{{ lookup('env','AVI_PASSWORD') }}"

    - name: Inform user where log is saved
      ansible.builtin.debug:
        msg: "Python script output is saved to {{ log_file }}"
```

### Run (Dry Run)
```bash
ansible-playbook delete_empty_tenants.yml
```

### Run (Actual Delete)
```bash
ansible-playbook delete_empty_tenants.yml -e "dry_run=false"
```

---

## 📁 Log File

The playbook saves all output to:
```
delete_empty_tenants.log
```

---

## 🧾 Summary Report (Auto CSV Export)

At the end of execution, the script generates a CSV file:
```
cleanup_summary.csv
```

Example content:

| Controller | Before | After | Deleted |
|-------------|--------|--------|----------|
| 10.10.10.248 | 3 | 2 | 1 |
| 10.10.10.249 | 5 | 4 | 1 |

---

## ⚠️ Notes & Safety

- Always run in **dry-run mode first** before enabling actual deletions.
- The `admin` tenant is **never deleted**.
- Make sure your Avi user account has sufficient privileges.
- The script disables SSL verification (`verify=False`) — for production, replace with proper CA validation.

---

## 🧠 Author Notes

- Written for automation of **Avi/NSX ALB tenant cleanup**.  
- Designed for flexibility, visibility, and safety (dry-run by default).  
- Works well for environments with multiple Avi controllers.

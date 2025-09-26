# Avi_Scripts

This repository is the **main hub** for my **VMware NSX Advanced Load Balancer (Avi)** Day-2 operation scripts.  
Each script is organized in its own subfolder with a dedicated README.

---

## 📑 Scripts Index

| Script Folder | Description | Link |
|---------------|-------------|------|
| **healthcheck** | Collects controller and SE health data and outputs a report | [README](healthcheck/README.md) |
| **cert_manager** | Automates certificate upload and renewal | [README](cert_manager/README.md) |
| **ipam_integration** | Example integration with IPAM/DNS APIs | [README](ipam_integration/README.md) |

---

## 🚀 Quick Start

Clone this repository:
```bash
git clone https://github.com/haddadv2/Avi_Acripts.git
cd Avi_Acripts
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Navigate into any script folder and follow its README:
```bash
cd healthcheck
python healthcheck.py
```

---

## 🤝 Contributions
When adding a new script:
1. Create a new subfolder  
2. Add your script(s) and a `README.md`  
3. Update this main README to include the new script.

## 📜 License
MIT License – see [LICENSE](LICENSE).

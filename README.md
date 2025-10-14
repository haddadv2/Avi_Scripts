# Avi_Scripts

This repository is the **main hub** for my **VMware NSX Advanced Load Balancer (Avi)** Day-2 operation scripts.  
Each script is organized in its own subfolder with a dedicated README.

---

## 📑 Scripts Index

| Script Folder | Description | Link |
|---------------|-------------|------|
| **avi_vs_export** | Export Avi Virtual Service configuration and details | [README](avi_vs_export/README.md) |
| **avi_get_cert** | Fetch and manage Avi certificates | [README](avi_get_cert/README.md) |
| **cleanup_tenants** | Cleanup unused Avi tenants | [README](cleanup_tenants/README.md) |

---

## 🚀 Quick Start

Clone this repository:
```bash
git clone https://github.com/haddadv2/Avi_Acripts.git
cd Avi_Acripts
```

### Example: Navigate and run a script

For **avi_vs_export**:
```bash
cd avi_vs_export
pip install -r requirements.txt
python avi_vs_export.py -u USERNAME -p PASSWORD -c CONTROLLER_IP -v CONTROLLER_VERSION [-n LIMIT] [-C CLOUD_NAME] [-o OUTPUT_FILE]
cd ..
```


---

## 📜 License
MIT License – see [LICENSE](LICENSE).

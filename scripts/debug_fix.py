import os

def fix_file(path, old, new):
    if not os.path.exists(path): return
    with open(path, 'r') as f:
        content = f.read()
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

# Fix dictionary syntax error in seed scripts
fix_file("/app/github_code_repository_1222/delta-9/seed_db.py", '"status": models.CRMStatus.NEW,', '"status": models.CRMStatus.NEW,')
fix_file("/app/github_code_repository_1222/delta-9/seed_db.py", 'status=models.CRMStatus.NEW,', '"status": models.CRMStatus.NEW,')
fix_file("/app/github_code_repository_1222/delta-9/seed_live_leads.py", 'status=models.CRMStatus.NEW,', 'status=models.CRMStatus.NEW,')

print("Fix applied. Verifying syntax...")
import subprocess
subprocess.run(["python3", "-m", "py_compile", "/app/github_code_repository_1222/delta-9/seed_db.py"])
subprocess.run(["python3", "-m", "py_compile", "/app/github_code_repository_1222/delta-9/seed_live_leads.py"])
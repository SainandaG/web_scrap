import subprocess
import os
import glob

# Find git executable
git_paths = glob.glob(r"C:\Program Files*\Git\cmd\git.exe") + glob.glob(r"C:\Program Files*\Git\bin\git.exe")
if not git_paths:
    print("Could not find git.exe")
    exit(1)

git_path = git_paths[0]
print(f"Found git at: {git_path}")

try:
    print("Adding files...")
    subprocess.run([git_path, "add", "."], check=True)
    
    print("Committing...")
    subprocess.run([git_path, "commit", "-m", "Use Android player client to bypass Vercel bot detection"], check=False)
    
    print("Pushing...")
    subprocess.run([git_path, "push", "origin", "main"], check=True)
    
    print("Successfully pushed to GitHub!")
except Exception as e:
    print(f"Error: {e}")

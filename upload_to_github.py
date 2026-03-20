import requests
import base64
import os

token = "sDazkqBGMrpEa9Wn6pjkUxbB"
username = "ashswin-git"
repo_name = "Universal-Downloader"

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 1. Create Repo
print("Creating repository...")
repo_payload = {
    "name": repo_name,
    "description": "Universal Downloader - Vercel Ready",
    "private": False
}
res = requests.post("https://api.github.com/user/repos", json=repo_payload, headers=headers)
if res.status_code == 201:
    print(f"Created repo: {repo_name}")
elif res.status_code == 422:
    print(f"Repo {repo_name} might already exist. Continuing...")
else:
    print(f"Error creating repo: {res.status_code} - {res.text}")

# 2. Upload files
files_to_upload = [
    "app.py",
    "requirements.txt",
    "vercel.json",
    "templates/index.html",
    "README.md",
    ".gitignore"
]

for file_path in files_to_upload:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} (not found)")
        continue
    
    with open(file_path, "rb") as f:
        content = f.read()
        
    encoded_content = base64.b64encode(content).decode("utf-8")
    
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    
    # Check if file exists to get SHA (needed for update)
    get_res = requests.get(url, headers=headers)
    sha = None
    if get_res.status_code == 200:
        sha = get_res.json().get("sha")
        
    payload = {
        "message": f"Add {file_path}",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    print(f"Uploading {file_path}...")
    put_res = requests.put(url, json=payload, headers=headers)
    if put_res.status_code in [201, 200]:
        print(f"Successfully uploaded {file_path}")
    else:
        print(f"Failed to upload {file_path}: {put_res.text}")
        
print(f"\nAll done! Your code is now at: https://github.com/{username}/{repo_name}")

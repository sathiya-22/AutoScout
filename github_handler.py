import os
import requests
import subprocess
import shutil

def create_github_repo(repo_name, github_token, description=""):
    """Creates a new public repository on GitHub if it doesn't already exist."""
    print(f"Ensuring GitHub repository {repo_name} exists...")
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "auto_init": True, # Ensure it has a README/main branch
        "private": False 
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"Created new repository: {repo_name}")
        return response.json()["clone_url"]
    elif response.status_code == 422 and "already exists" in response.text:
        print(f"Repository {repo_name} already exists.")
        user_resp = requests.get("https://api.github.com/user", headers=headers)
        if user_resp.status_code == 200:
            login = user_resp.json()["login"]
            return f"https://github.com/{login}/{repo_name}.git"
        else:
            raise Exception(f"Repo exists but failed to fetch user info: {user_resp.text}")
    else:
        raise Exception(f"Failed to create GitHub repo: {response.status_code} - {response.text}")

def push_to_github(batch_folder, repo_url, github_token):
    """Clones the single target repo, adds the daily batch folder, and pushes."""
    print(f"Pushing {batch_folder} to {repo_url}...")
    temp_dir = "temp_gh_repo"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    try:
        # 1. Use token in URL for authentication
        authenticated_url = repo_url.replace("https://", f"https://{github_token}@")
        
        # 2. Clone the repo
        subprocess.run(["git", "clone", authenticated_url, temp_dir], check=True)
        
        # 3. Copy the batch folder into the repo
        dest_path = os.path.join(temp_dir, batch_folder)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
            
        shutil.copytree(batch_folder, dest_path)
        
        # 4. Git Add, Commit, Push
        commands = [
            ["git", "config", "user.email", "scout-bot@example.com"],
            ["git", "config", "user.name", "Daily AI Scout Bot"],
            ["git", "add", "."],
            ["git", "commit", "-m", f"Add daily AI batch: {batch_folder} [skip ci]"],
            ["git", "push", "origin", "main"]
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Git command failed: {' '.join(cmd)}")
                print(f"Error: {result.stderr}")
                # Don't fail if there's nothing to commit
                if "nothing to commit" not in result.stderr:
                    raise Exception(f"Git error: {result.stderr}")
                    
        print(f"Successfully pushed {batch_folder} to {repo_url}")
    except Exception as e:
        print(f"Error during GitHub push: {e}")
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

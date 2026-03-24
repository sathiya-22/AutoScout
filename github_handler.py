import os
import requests
import subprocess

def create_github_repo(repo_name, github_token, description=""):
    """Creates a new public repository on GitHub."""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "auto_init": False,
        "private": False # Change to True if needed
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()["clone_url"]
    elif response.status_code == 422 and "already exists" in response.text:
        print(f"Repository {repo_name} already exists. Fetching existing URL...")
        user_resp = requests.get("https://api.github.com/user", headers=headers)
        if user_resp.status_code == 200:
            login = user_resp.json()["login"]
            return f"https://github.com/{login}/{repo_name}.git"
        else:
            raise Exception(f"Repo exists but failed to fetch user info: {user_resp.text}")
    else:
        raise Exception(f"Failed to create GitHub repo: {response.status_code} - {response.text}")

def push_to_github(folder_path, repo_url, github_token):
    """Initializes git and pushes the folder content to the remote repo."""
    try:
        # Use token in URL for authentication
        authenticated_url = repo_url.replace("https://", f"https://{github_token}@")
        
        commands = [
            ["git", "init"],
            ["git", "config", "user.email", "scout-bot@example.com"],
            ["git", "config", "user.name", "Daily AI Scout Bot"],
            ["git", "add", "."],
            ["git", "commit", "-m", "Initial commit from Daily AI Builder"],
            ["git", "branch", "-M", "main"],
            ["git", "remote", "add", "origin", authenticated_url],
            ["git", "push", "-u", "origin", "main"]
        ]
        
        # Check if there are any files to push
        files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
        if not files:
            print(f"Skipping push for {folder_path} - folder is empty.")
            return
            
        for cmd in commands:
            result = subprocess.run(cmd, cwd=folder_path, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Git command failed: {' '.join(cmd)}")
                print(f"Error: {result.stderr}")
                # Don't raise for remote add if it already exists, etc.
                if "remote origin already exists" not in result.stderr:
                   raise Exception(f"Git error: {result.stderr}")
                   
        print(f"Successfully pushed to {repo_url}")
    except Exception as e:
        print(f"Error pushing to GitHub: {e}")
        raise e

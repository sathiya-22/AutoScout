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

def push_project_to_own_repo(folder_name, github_token, description="", source_path=None):
    """Creates a brand-new repo named after the project and pushes the project
    folder's CONTENTS (not the folder itself) directly to the repo root.

    Args:
        folder_name:  Slug used as the GitHub repository name.
        github_token: Personal access token with repo scope.
        description:  Short description shown on GitHub.
        source_path:  Local directory to read files from. Defaults to folder_name.
    """
    source = source_path or folder_name
    print(f"\n--- [DEPLOY] Creating dedicated repo for: {folder_name} ---")
    repo_url = create_github_repo(folder_name, github_token, description=description)

    temp_dir = f"temp_repo_{folder_name}"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    try:
        authenticated_url = repo_url.replace("https://", f"https://{github_token}@")
        subprocess.run(["git", "clone", authenticated_url, temp_dir], check=True, capture_output=True)

        # Copy project files to repo root (not inside a subfolder)
        for item in os.listdir(source):
            src = os.path.join(source, item)
            dst = os.path.join(temp_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        commands = [
            ["git", "config", "user.email", "scout-bot@example.com"],
            ["git", "config", "user.name", "AutoScout Bot"],
            ["git", "add", "."],
            ["git", "commit", "-m", "feat: AutoScout generated project [skip ci]"],
            ["git", "push", "origin", "main"],
        ]

        for cmd in commands:
            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Git command failed: {' '.join(cmd)}\nError: {result.stderr}")
                if "nothing to commit" not in result.stderr:
                    raise Exception(f"Git error: {result.stderr}")

        # Derive the clean HTTPS URL for display (strip .git and token)
        clean_url = repo_url.replace(".git", "")
        print(f"✅ Pushed {folder_name} → {clean_url}")
        return clean_url

    except Exception as e:
        print(f"Error pushing {folder_name}: {e}")
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


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


def update_existing_repo(repo_name, github_token, file_name, new_code, commit_msg):
    """Clone an existing repo, update one file, and push the commit."""
    import os, shutil, subprocess

    print(f"\n--- [UPDATE] {repo_name} → {file_name} ---")
    temp_dir = f"temp_update_{repo_name}"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    # Derive repo URL from GitHub username
    username = _get_github_username(github_token)
    if not username:
        print(f"  Could not resolve GitHub username — skipping {repo_name}")
        return False

    repo_url = f"https://{github_token}@github.com/{username}/{repo_name}.git"

    try:
        subprocess.run(["git", "clone", repo_url, temp_dir],
                       check=True, capture_output=True)

        file_path = os.path.join(temp_dir, file_name)
        if not os.path.exists(file_path):
            print(f"  {file_name} not found in {repo_name} — skipping")
            return False

        with open(file_path, "w") as f:
            f.write(new_code)

        commands = [
            ["git", "config", "user.email", "scout-bot@example.com"],
            ["git", "config", "user.name", "AutoScout Bot"],
            ["git", "add", file_name],
            ["git", "commit", "-m", commit_msg],
            ["git", "push", "origin", "main"],
        ]
        for cmd in commands:
            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
            if result.returncode != 0:
                if "nothing to commit" in result.stderr:
                    print(f"  No changes detected in {file_name} — skipping commit")
                    return False
                raise Exception(f"Git error: {result.stderr}")

        print(f"  ✅ Updated {repo_name}/{file_name}: {commit_msg}")
        return True

    except Exception as e:
        print(f"  Update failed for {repo_name}: {e}")
        return False
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def _get_github_username(token):
    """Resolve the GitHub username for a given token."""
    import requests
    try:
        r = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"},
            timeout=10,
        )
        return r.json().get("login")
    except Exception:
        return None

import os
import json
import re
from slugify import slugify
from agents.architect import architect_project
from agents.engineer import engineer_file
from agents.qa_tester import generate_tests
from agents.marketer import generate_readme
from google import genai

def run_startup_team(idea, api_key):
    """Orchestrates the multi-agent team to build a technical prototype."""
    client = genai.Client(api_key=api_key)
    print(f"\n--- [AGENT: ARCHITECT] Designing {idea['problem_statement'][:50]}... ---")
    
    try:
        plan = architect_project(client, idea)
        folder_name = slugify(plan.get('folder_name', idea['search_keyword']))
        os.makedirs(folder_name, exist_ok=True)
        
        files_with_code = []
        # Support both 'file_list' and 'files' keys if architect varies
        file_list = plan.get('file_list', [])
        
        for file_name in file_list:
            if not file_name: continue
            print(f"--- [AGENT: ENGINEER] Implementing {file_name}... ---")
            try:
                code = engineer_file(client, idea, file_name, plan['architecture_notes'])
                files_with_code.append({"name": file_name, "code": code})
                
                with open(os.path.join(folder_name, file_name), "w") as f:
                    f.write(code)
            except Exception as e:
                print(f"Error implementing {file_name}: {e}")

        # Automatically add a requirements.txt if not generated
        if "requirements.txt" not in [f["name"] for f in files_with_code]:
            print("--- [SYSTEM] Generating requirements.txt... ---")
            req_prompt = f"List the python dependencies for this project: {idea['problem_statement']}. Return ONLY the list, one per line."
            req_resp = client.models.generate_content(model='gemini-1.5-flash', contents=req_prompt)
            with open(os.path.join(folder_name, "requirements.txt"), "w") as f:
                f.write(req_resp.text.strip())
                
        print("--- [AGENT: QA] Generating tests... ---")
        try:
            test_code = generate_tests(client, idea, files_with_code)
            with open(os.path.join(folder_name, "tests.py"), "w") as f:
                f.write(test_code)
        except Exception as e:
            print(f"QA phase failed: {e}")
            
        print("--- [AGENT: MARKETER] Writing README... ---")
        try:
            readme_content = generate_readme(client, idea, plan['architecture_notes'])
            with open(os.path.join(folder_name, "README.md"), "w") as f:
                f.write(readme_content)
        except Exception as e:
            print(f"Marketing phase failed: {e}")
            
        print(f"--- [STARTUP TEAM] Project {folder_name} completed! ---")
        return folder_name
    except Exception as e:
        print(f"Architect phase failed: {e}")
        return None

def build_all_projects(ideas, api_key):
    """Builds all ideas using the multi-agent team."""
    generated_folders = []
    for idea in ideas:
        folder = run_startup_team(idea, api_key)
        if folder:
            generated_folders.append(folder)
    return generated_folders

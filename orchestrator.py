import os
import json
from agents.architect import architect_project
from agents.engineer import engineer_file
from agents.qa_tester import generate_tests
from agents.marketer import generate_readme
from google import genai

def run_startup_team(idea, api_key):
    """Orchestrates the multi-agent team to build a project."""
    client = genai.Client(api_key=api_key)
    print(f"\n--- [AGENT: ARCHITECT] Designing {idea['problem_statement'][:50]}... ---")
    plan = architect_project(client, idea)
    
    folder_name = plan['folder_name']
    os.makedirs(folder_name, exist_ok=True)
    
    files_with_code = []
    for file_name in plan['file_list']:
        print(f"--- [AGENT: ENGINEER] Implementing {file_name}... ---")
        code = engineer_file(client, idea, file_name, plan['architecture_notes'])
        files_with_code.append({"name": file_name, "code": code})
        
        with open(os.path.join(folder_name, file_name), "w") as f:
            f.write(code)
            
    print("--- [AGENT: QA] Generating tests... ---")
    test_code = generate_tests(client, idea, files_with_code)
    with open(os.path.join(folder_name, "tests.py"), "w") as f:
        f.write(test_code)
        
    print("--- [AGENT: MARKETER] Writing README... ---")
    readme_content = generate_readme(client, idea, plan['architecture_notes'])
    with open(os.path.join(folder_name, "README.md"), "w") as f:
        f.write(readme_content)
        
    print(f"--- [STARTUP TEAM] Project {folder_name} completed! ---")
    return folder_name

def build_all_projects(ideas, api_key):
    """Builds all ideas using the multi-agent team."""
    generated_folders = []
    for idea in ideas:
        folder = run_startup_team(idea, api_key)
        generated_folders.append(folder)
    return generated_folders

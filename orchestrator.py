import os
import json
import re
from slugify import slugify
from agents.architect import architect_project
from agents.engineer import engineer_file
from agents.qa_tester import generate_tests
from agents.marketer import generate_readme
from agents.synthesizer import synthesize_ideas
from google import genai

SYNTHESIS_THRESHOLD = 6  # minimum connection_score to attempt unified build


def run_startup_team(idea, client):
    """Orchestrates the multi-agent team to build a technical prototype for one idea."""
    print(f"\n--- [AGENT: ARCHITECT] Designing {idea['problem_statement'][:60]}... ---")

    try:
        plan = architect_project(client, idea)
        folder_name = slugify(plan.get("folder_name", idea.get("search_keyword", "project")))
        os.makedirs(folder_name, exist_ok=True)

        files_with_code = []
        file_list = plan.get("file_list", [])

        for file_name in file_list:
            if not file_name:
                continue
            print(f"--- [AGENT: ENGINEER] Implementing {file_name}... ---")
            try:
                code = engineer_file(client, idea, file_name, plan["architecture_notes"])
                files_with_code.append({"name": file_name, "code": code})

                target_path = os.path.join(folder_name, file_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w") as f:
                    f.write(code)
            except Exception as e:
                print(f"Error implementing {file_name}: {e}")

        # Auto-generate requirements.txt if architect didn't include it
        if "requirements.txt" not in [f["name"] for f in files_with_code]:
            print("--- [SYSTEM] Generating requirements.txt... ---")
            req_prompt = (
                f"List the Python pip dependencies for this project: "
                f"{idea['problem_statement']}. Return ONLY package names, one per line."
            )
            req_resp = client.models.generate_content(model="gemini-2.5-flash", contents=req_prompt)
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
            readme_content = generate_readme(client, idea, plan["architecture_notes"])
            with open(os.path.join(folder_name, "README.md"), "w") as f:
                f.write(readme_content)
        except Exception as e:
            print(f"Marketer phase failed: {e}")

        print(f"--- [STARTUP TEAM] Project '{folder_name}' completed! ---")
        return folder_name

    except Exception as e:
        print(f"Architect phase failed: {e}")
        return None


def synthesize_and_build(ideas, api_key):
    """
    Main entry point for the build phase.

    1. Calls the Synthesizer agent to find the unifying thread across all 3 ideas.
    2. If connection_score >= SYNTHESIS_THRESHOLD → builds ONE unified project.
    3. If score is too low → falls back to building the single strongest idea.

    Returns a list containing one folder name (always one repo per run).
    """
    client = genai.Client(api_key=api_key)

    print("\n--- [AGENT: SYNTHESIZER] Finding unifying thread across ideas... ---")
    try:
        brief = synthesize_ideas(client, ideas)
        score = brief.get("connection_score", 0)
        print(f"--- [SYNTHESIZER] Connection score: {score}/10 — '{brief.get('project_title')}' ---")
    except Exception as e:
        print(f"Synthesizer failed: {e}. Falling back to strongest single idea.")
        brief = None
        score = 0

    if brief and score >= SYNTHESIS_THRESHOLD:
        print(f"--- [SYNTHESIZER] Score ≥ {SYNTHESIS_THRESHOLD}. Building unified project. ---")

        # Build a unified idea object compatible with all existing agents
        unified_idea = {
            "problem_statement": brief["unified_problem"],
            "solution_sketch": brief["solution_overview"],
            "why_it_matters": brief["why_unified"],
            "search_keyword": brief["project_name"],
            "title": brief["project_title"],
            "key_features": brief.get("key_features", []),
            "source_paper": "AutoScout Synthesis — 3 research ideas unified",
        }

        folder = run_startup_team(unified_idea, client)
        return [folder] if folder else []

    else:
        # Fallback: build just the strongest single idea
        fallback_index = (brief or {}).get("fallback_idea_index", 0)
        fallback_index = max(0, min(fallback_index, len(ideas) - 1))
        fallback_idea = ideas[fallback_index]
        print(
            f"--- [SYNTHESIZER] Score < {SYNTHESIS_THRESHOLD}. "
            f"Falling back to idea #{fallback_index + 1}: "
            f"{fallback_idea['problem_statement'][:60]}... ---"
        )

        folder = run_startup_team(fallback_idea, client)
        return [folder] if folder else []


def build_all_projects(ideas, api_key):
    """Legacy function kept for compatibility. Builds all ideas separately."""
    client = genai.Client(api_key=api_key)
    generated_folders = []
    for idea in ideas:
        folder = run_startup_team(idea, client)
        if folder:
            generated_folders.append(folder)
    return generated_folders

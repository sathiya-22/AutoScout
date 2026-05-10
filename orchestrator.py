import os
import subprocess
import sys
from slugify import slugify
from agents.architect import architect_project
from agents.engineer import engineer_file
from agents.critic import critique_and_revise
from agents.demo_writer import write_demo
from agents.qa_tester import generate_tests
from agents.marketer import generate_readme
from agents.synthesizer import synthesize_ideas
from utils import gemini_generate
from google import genai

SYNTHESIS_THRESHOLD = 6  # minimum connection_score to attempt unified build


# ─────────────────────────────────────────────
# Dependency Validation
# ─────────────────────────────────────────────

def _validate_and_fix_requirements(client, folder_name, idea):
    """pip-install dry-run the generated requirements.txt.
    If it fails, ask Gemini to fix it and try once more."""
    req_path = os.path.join(folder_name, "requirements.txt")
    if not os.path.exists(req_path):
        return

    print("--- [SYSTEM] Validating requirements.txt... ---")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_path,
         "--dry-run", "--quiet"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("--- [SYSTEM] Dependencies OK ✅ ---")
        return

    print("--- [SYSTEM] Dependency issues found — asking Gemini to fix... ---")
    with open(req_path) as f:
        current_reqs = f.read()

    fix_prompt = f"""
This requirements.txt has pip installation errors:

{current_reqs}

Error output:
{result.stderr[:600]}

Project goal: {idea['problem_statement']}

Return ONLY the corrected requirements.txt — one valid PyPI package name per line.
No comments, no version pins unless necessary, no markdown.
"""
    resp = gemini_generate(client, "gemini-1.5-flash", fix_prompt)
    fixed = resp.text.strip()
    if fixed.startswith("```"):
        fixed = "\n".join(fixed.split("\n")[1:])
    if fixed.endswith("```"):
        fixed = "\n".join(fixed.split("\n")[:-1])

    with open(req_path, "w") as f:
        f.write(fixed.strip())
    print("--- [SYSTEM] Requirements fixed ✅ ---")


# ─────────────────────────────────────────────
# Core build team
# ─────────────────────────────────────────────

def run_startup_team(idea, client):
    """Orchestrates the full multi-agent team to build one prototype:
    Architect → Engineer → Critic (per file) → Dependency Validator
    → Demo Writer → QA Tester → Marketer
    """
    print(f"\n--- [AGENT: ARCHITECT] Designing {idea['problem_statement'][:60]}... ---")

    try:
        plan = architect_project(client, idea)
        folder_name = slugify(plan.get("folder_name", idea.get("search_keyword", "project")))
        os.makedirs(folder_name, exist_ok=True)

        files_with_code = []
        for file_name in plan.get("file_list", []):
            if not file_name:
                continue

            print(f"--- [AGENT: ENGINEER] Implementing {file_name}... ---")
            try:
                code = engineer_file(client, idea, file_name, plan["architecture_notes"])

                # ── Self-critique loop ──────────────────────────────────
                code = critique_and_revise(
                    client, idea, file_name, code, plan["architecture_notes"]
                )
                # ────────────────────────────────────────────────────────

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
                f"{idea['problem_statement']}. "
                f"Return ONLY valid PyPI package names, one per line."
            )
            req_resp = gemini_generate(client, "gemini-1.5-flash", req_prompt)
            with open(os.path.join(folder_name, "requirements.txt"), "w") as f:
                f.write(req_resp.text.strip())

        # ── Dependency validation ───────────────────────────────────────
        _validate_and_fix_requirements(client, folder_name, idea)
        # ───────────────────────────────────────────────────────────────

        # ── Demo writer ────────────────────────────────────────────────
        print("--- [AGENT: DEMO WRITER] Writing demo.py... ---")
        try:
            demo_code = write_demo(client, idea, files_with_code)
            with open(os.path.join(folder_name, "demo.py"), "w") as f:
                f.write(demo_code)
        except Exception as e:
            print(f"Demo writer failed: {e}")
        # ───────────────────────────────────────────────────────────────

        print("--- [AGENT: QA] Generating tests... ---")
        try:
            test_code = generate_tests(client, idea, files_with_code)
            with open(os.path.join(folder_name, "tests.py"), "w") as f:
                f.write(test_code)
        except Exception as e:
            print(f"QA phase failed: {e}")

        print("--- [AGENT: MARKETER] Writing README... ---")
        readme_content = ""
        try:
            readme_content = generate_readme(client, idea, plan["architecture_notes"])
            with open(os.path.join(folder_name, "README.md"), "w") as f:
                f.write(readme_content)
        except Exception as e:
            print(f"Marketer phase failed: {e}")

        print(f"--- [STARTUP TEAM] Project '{folder_name}' completed! ---")
        return folder_name, readme_content

    except Exception as e:
        print(f"Architect phase failed: {e}")
        return None, ""


# ─────────────────────────────────────────────
# Synthesis entry point
# ─────────────────────────────────────────────

def synthesize_and_build(ideas, api_key):
    """
    Main Phase 3 entry point.

    1. Synthesizer finds the unifying thread and scores connection (1-10).
    2. Score >= SYNTHESIS_THRESHOLD → build ONE unified project.
    3. Score  < SYNTHESIS_THRESHOLD → build the single strongest idea.

    Returns: (folder_name, readme_content, brief) tuple.
             folder_name is None if build failed.
    """
    client = genai.Client(api_key=api_key)

    print("\n--- [AGENT: SYNTHESIZER] Finding unifying thread across ideas... ---")
    brief = None
    score = 0
    try:
        brief = synthesize_ideas(client, ideas)
        score = brief.get("connection_score", 0)
        print(
            f"--- [SYNTHESIZER] Connection score: {score}/10 "
            f"— '{brief.get('project_title')}' ---"
        )
    except Exception as e:
        print(f"Synthesizer failed: {e}. Falling back to strongest single idea.")

    fallback_used = False

    if brief and score >= SYNTHESIS_THRESHOLD:
        print(f"--- [SYNTHESIZER] Score ≥ {SYNTHESIS_THRESHOLD}. Building unified project. ---")
        unified_idea = {
            "problem_statement": brief["unified_problem"],
            "solution_sketch": brief["solution_overview"],
            "why_it_matters": brief["why_unified"],
            "search_keyword": brief["project_name"],
            "title": brief["project_title"],
            "key_features": brief.get("key_features", []),
            "source_paper": "AutoScout Synthesis — 3 research ideas unified",
        }
        folder, readme = run_startup_team(unified_idea, client)
    else:
        fallback_used = True
        idx = max(0, min((brief or {}).get("fallback_idea_index", 0), len(ideas) - 1))
        fallback_idea = ideas[idx]
        print(
            f"--- [SYNTHESIZER] Score < {SYNTHESIS_THRESHOLD}. "
            f"Falling back to idea #{idx + 1}: "
            f"{fallback_idea['problem_statement'][:60]}... ---"
        )
        # Use fallback idea as brief info for analytics
        brief = brief or {
            "project_name": fallback_idea.get("search_keyword", "project"),
            "project_title": fallback_idea.get("search_keyword", "project"),
            "connection_score": score,
        }
        folder, readme = run_startup_team(fallback_idea, client)

    return folder, readme, brief, fallback_used


# ─────────────────────────────────────────────
# Legacy (kept for compatibility)
# ─────────────────────────────────────────────

def build_all_projects(ideas, api_key):
    client = genai.Client(api_key=api_key)
    folders = []
    for idea in ideas:
        folder, _ = run_startup_team(idea, client)
        if folder:
            folders.append(folder)
    return folders

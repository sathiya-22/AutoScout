import os
import json
import datetime
import shutil
from dotenv import load_dotenv
from google import genai
from tavily import TavilyClient
import resend

from github_handler import push_project_to_own_repo
from researcher import scout_arxiv_gaps
from orchestrator import synthesize_and_build, build_all_projects
from memory import is_duplicate, add_to_memory
from analytics import record_run, get_summary
from utils import gemini_generate


# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY")
RESEND_API_KEY  = os.getenv("RESEND_API_KEY")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")

MODEL_NAME      = "gemini-2.0-flash"
SEEN_IDEAS_FILE = "seen_ideas.json"   # kept for legacy commits in GH Actions

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# ── Research ──────────────────────────────────────────────────────────────────

def research_node():
    """Searches for high-friction technical problems in the AI domain."""
    print("Running web research phase...")
    query = (
        "biggest unsolved technical challenges OR limitations in agent orchestration, "
        "RAG optimization, and LLM contextual drift. Open discussions on reddit or hacker news."
    )
    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=10,
            include_raw_content=True,
        )
        if not response:
            print("Tavily search returned empty response.")
            return ""
        context = ""
        for idx, result in enumerate(response.get("results", [])):
            title   = result.get("title") or "Untitled"
            content = result.get("content") or "No content available."
            raw     = (result.get("raw_content") or "")[:1000]
            context += f"Result {idx+1}:\nTitle: {title}\nContent: {content}\nRaw: {raw}\n\n"
        return context
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return ""


# ── Seen-ideas (legacy string list, kept for GH Actions commit step) ──────────

def load_seen_ideas():
    if os.path.exists(SEEN_IDEAS_FILE):
        with open(SEEN_IDEAS_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_seen_ideas(ideas):
    seen = load_seen_ideas()
    seen.extend(ideas)
    with open(SEEN_IDEAS_FILE, "w") as f:
        json.dump(list(set(seen)), f, indent=4)


# ── Validation ────────────────────────────────────────────────────────────────

def validation_node(raw_web_data, raw_arxiv_data):
    """Uses Gemini to batch-validate all problems and select the top 3.
    Deduplication is now semantic (via memory.py) instead of string-match."""
    print("Running batch validation phase...")

    raw_data = f"WEB RESEARCH:\n{raw_web_data}\n\nARXIV RESEARCH:\n{raw_arxiv_data}"
    try:
        extraction_prompt = f"""
        Extract 5 unique, high-friction AI technical problems from these results:
        {raw_data}
        Return JSON list of objects with: problem_statement, why_it_matters, solution_sketch, search_keyword.
        """
        response = gemini_generate(
            client, MODEL_NAME, extraction_prompt,
            config={"response_mime_type": "application/json"},
        )
        extracted_problems = json.loads(response.text.strip())

        candidate_data = []
        for idx, p in enumerate(extracted_problems):
            # ── Semantic duplicate check ─────────────────────────────
            if is_duplicate(client, p["problem_statement"]):
                print(f"  Skipping idea {idx+1} (semantic duplicate).")
                continue
            # ────────────────────────────────────────────────────────
            print(f"Checking competitors for idea candidate {idx+1}...")
            results = tavily_client.search(query=p["search_keyword"], search_depth="basic")
            comp_context = ""
            for r in results.get("results", []):
                comp_context += f"- {r.get('title')}: {r.get('content')[:200]}\n"
            candidate_data.append({"idea": p, "competitors": comp_context})

        if not candidate_data:
            return []

        validation_prompt = f"""
        Analyze these candidates and their competitors:
        {json.dumps(candidate_data, indent=2)}

        Pick the TOP 3 that are most unique and underserved technically.
        Return ONLY a JSON list of the 3 chosen idea objects.
        """
        val_response = gemini_generate(
            client, MODEL_NAME, validation_prompt,
            config={"response_mime_type": "application/json"},
        )
        selected_data = json.loads(val_response.text.strip())[:3]
        return [item.get("idea", item) for item in selected_data]

    except Exception as e:
        print(f"Error in batch validation: {e}")
        return []


# ── Email ─────────────────────────────────────────────────────────────────────

def format_html_email(ideas, repo_url=None, devto_url=None, analytics_summary=""):
    if not ideas:
        return "<p>No new unique ideas found today.</p>"

    html = '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; color: #333;">'
    html += '<h2 style="color: #2E86AB; text-align: center;">🚀 AutoScout Lab</h2>'
    html += f'<p style="text-align:center; color:#666;">Daily AI research synthesis — {datetime.date.today()}</p>'

    if repo_url:
        html += f'<p style="text-align:center;"><a href="{repo_url}" style="color:#2E86AB;">🔗 View Repository</a>'
        if devto_url:
            html += f' &nbsp;|&nbsp; <a href="{devto_url}" style="color:#2E86AB;">📝 Read on Dev.to</a>'
        html += "</p>"

    for idx, idea in enumerate(ideas):
        html += f"""
        <div style="background:#f9f9f9; padding:15px; margin-bottom:20px;
                    border-left:4px solid #F24236; border-radius:4px;">
            <h3 style="margin-top:0; color:#F24236;">
                Idea #{idx+1}: {idea.get('search_keyword', 'New Concept')}
            </h3>
            <p><strong>Problem:</strong> {idea['problem_statement']}</p>
            <p><strong>Impact:</strong> {idea['why_it_matters']}</p>
            <p><strong>Prototype Sketch:</strong> {idea['solution_sketch']}</p>
        </div>
        """

    if analytics_summary:
        html += (
            f'<p style="font-size:12px; color:#888; text-align:center;">'
            f'📊 {analytics_summary}</p>'
        )

    html += '<hr><p style="font-size:12px; text-align:center; color:#888;">Automated by AutoScout Autonomous R&D Lab</p>'
    html += "</div>"
    return html


def send_email(html_content, subject=None):
    subj = subject or f"AutoScout Lab Results — {datetime.date.today()}"
    print(f"\nDispatching email: {subj}")
    try:
        resend.Emails.send({
            "from": "Scout <onboarding@resend.dev>",
            "to": ["sendilnathsathiya@gmail.com"],
            "subject": subj,
            "html": html_content,
        })
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Starting AutoScout Lab at {datetime.datetime.now()}...")

    if not all([GEMINI_API_KEY, TAVILY_API_KEY, RESEND_API_KEY]):
        print("Error: Missing required API keys in environment.")
        return

    # PHASE 1: RESEARCH
    try:
        raw_web_research   = research_node()
        raw_arxiv_research = scout_arxiv_gaps(GEMINI_API_KEY)
        if not raw_web_research and not raw_arxiv_research:
            print("No research data found.")
            return
    except Exception as e:
        print(f"Research Phase failed: {e}")
        return

    # PHASE 2: VALIDATION (with semantic dedup)
    try:
        final_ideas = validation_node(raw_web_research, raw_arxiv_research)
        if not final_ideas:
            print("No valid, unique ideas discovered today.")
            return
    except Exception as e:
        print(f"Validation Phase failed: {e}")
        return

    # PHASE 3: SYNTHESIS + BUILD
    batch_name = f"ai_scout_batch_{datetime.date.today().strftime('%Y_%m_%d')}"
    os.makedirs(batch_name, exist_ok=True)

    folder = readme_content = brief = None
    fallback_used = False
    try:
        folder, readme_content, brief, fallback_used = synthesize_and_build(
            final_ideas, GEMINI_API_KEY
        )
        if folder:
            target_path = os.path.join(batch_name, folder)
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.move(folder, batch_name)
    except Exception as e:
        print(f"Build Phase failed: {e}")

    # PHASE 4: DEPLOYMENT — one dedicated repo
    repo_url = None
    if GITHUB_TOKEN and folder and brief:
        try:
            source_path = os.path.join(batch_name, folder)
            repo_url = push_project_to_own_repo(
                brief.get("project_name", folder),
                GITHUB_TOKEN,
                description=f"AutoScout: {brief.get('project_title', '')}",
                source_path=source_path,
            )
        except Exception as e:
            print(f"GitHub Deployment failed: {e}")

    # PHASE 5: ANALYTICS
    if brief:
        record_run(
            project_name=brief.get("project_name", folder or "unknown"),
            project_title=brief.get("project_title", ""),
            connection_score=brief.get("connection_score", 0),
            repo_url=repo_url,
            fallback_used=fallback_used,
        )

    # PHASE 6: NOTIFICATION EMAIL
    devto_url = None
    analytics_summary = get_summary()
    html_content = format_html_email(
        final_ideas,
        repo_url=repo_url,
        devto_url=devto_url,
        analytics_summary=analytics_summary,
    )
    if send_email(html_content):
        # Persist ideas to both semantic memory and legacy string list
        for idea in final_ideas:
            add_to_memory(
                client,
                idea["problem_statement"],
                project_name=brief.get("project_name", "") if brief else "",
                connection_score=brief.get("connection_score") if brief else None,
            )
        save_seen_ideas([idea["problem_statement"] for idea in final_ideas])
        print("AutoScout run completed successfully.")
        print(f"📊 {analytics_summary}")

    # Cleanup local batch folder
    if os.path.exists(batch_name):
        shutil.rmtree(batch_name)


if __name__ == "__main__":
    main()

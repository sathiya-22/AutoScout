import os
import json
import datetime
import requests
import shutil
from dotenv import load_dotenv
from google import genai
from tavily import TavilyClient
import resend
from github_handler import create_github_repo, push_to_github
from researcher import scout_arxiv_gaps
from orchestrator import build_all_projects

# Load environment variables
load_dotenv()

# Configure API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Constants
MODEL_NAME = "gemini-1.5-flash"
TARGET_REPO_NAME = "AutoScout-Lab"
SEEN_IDEAS_FILE = "seen_ideas.json"

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

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
            include_raw_content=True
        )
        
        if not response:
            print("Tavily search returned empty response.")
            return ""
            
        context = ""
        for idx, result in enumerate(response.get("results", [])):
            title = result.get('title') or "Untitled"
            content = result.get('content') or "No content available."
            raw = (result.get('raw_content') or "")[:1000]
            context += f"Result {idx+1}:\nTitle: {title}\nContent: {content}\nRaw Content: {raw}\n\n"
            
        return context
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return ""

def load_seen_ideas():
    if os.path.exists(SEEN_IDEAS_FILE):
        with open(SEEN_IDEAS_FILE, "r") as f:
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

def validation_node(raw_web_data, raw_arxiv_data):
    """Uses Gemini to batch-validate all problems and select the top 3."""
    print("Running batch validation phase...")
    seen_ideas = load_seen_ideas()
    
    raw_data = f"WEB RESEARCH:\n{raw_web_data}\n\nARXIV RESEARCH:\n{raw_arxiv_data}"
    try:
        extraction_prompt = f"""
        Extract 5 unique, high-friction AI technical problems from these results:
        {raw_data}
        Return JSON list of objects with: problem_statement, why_it_matters, solution_sketch, search_keyword.
        """
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=extraction_prompt,
            config={'response_mime_type': 'application/json'}
        )
        extracted_problems = json.loads(response.text.strip())
        
        candidate_data = []
        for idx, p in enumerate(extracted_problems):
            if p["problem_statement"] in seen_ideas: continue
            print(f"Checking competitors for idea candidate {idx+1}...")
            results = tavily_client.search(query=p["search_keyword"], search_depth="basic")
            comp_context = ""
            for r in results.get("results", []):
                comp_context += f"- {r.get('title')}: {r.get('content')[:200]}\n"
            candidate_data.append({"idea": p, "competitors": comp_context})

        if not candidate_data: return []
        
        full_candidate_text = json.dumps(candidate_data, indent=2)
        validation_prompt = f"""
        Analyze these candidates and their competitors:
        {full_candidate_text}
        
        Pick the TOP 3 that are most unique and underserved technically.
        Return ONLY a JSON list of the 3 chosen idea objects.
        """
        val_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=validation_prompt,
            config={'response_mime_type': 'application/json'}
        )
        selected_data = json.loads(val_response.text.strip())[:3]
        
        final_list = []
        for item in selected_data:
            final_list.append(item.get("idea", item))
        return final_list
        
    except Exception as e:
        print(f"Error in batch validation: {e}")
        return []

def format_html_email(ideas):
    """Formats the ideas into a beautiful HTML email."""
    if not ideas:
        return "<p>No new unique ideas found today.</p>"
        
    html = '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; color: #333;">'
    html += '<h2 style="color: #2E86AB; text-align: center;">🚀 AutoScout Lab</h2>'
    html += f'<p style="text-align: center; color: #666;">Daily AI research synthesis for {datetime.date.today()}</p>'
    
    for idx, idea in enumerate(ideas):
        html += f"""
        <div style="background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; border-left: 4px solid #F24236; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #F24236;">Idea #{idx + 1}: {idea.get('search_keyword', 'New Concept')}</h3>
            <p><strong>Problem:</strong> {idea['problem_statement']}</p>
            <p><strong>Impact:</strong> {idea['why_it_matters']}</p>
            <p><strong>Prototype Sketch:</strong> {idea['solution_sketch']}</p>
        </div>
        """
    html += '<hr><p style="font-size: 12px; text-align: center; color: #888;">Automated by AutoScout Autonomous R&D Lab</p>'
    html += '</div>'
    return html

def send_email(html_content, subject=None):
    """Sends email using Resend."""
    subj = subject or f"AutoScout Lab Results - {datetime.date.today()}"
    print(f"\nDispatching email: {subj}")
    try:
        resend.Emails.send({
            "from": "Scout <onboarding@resend.dev>",
            "to": ["sendilnathsathiya@gmail.com"],
            "subject": subj,
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    print(f"Starting AutoScout Lab at {datetime.datetime.now()}...")
    
    if not all([GEMINI_API_KEY, TAVILY_API_KEY, RESEND_API_KEY]):
        print("Error: Missing required API keys in environment.")
        return

    # PHASE 1: RESEARCH
    try:
        raw_web_research = research_node()
        raw_arxiv_research = scout_arxiv_gaps(GEMINI_API_KEY)
        
        if not raw_web_research and not raw_arxiv_research:
            print("No research data found.")
            return
    except Exception as e:
        print(f"Research Phase failed: {e}")
        return
        
    # PHASE 2: VALIDATION
    try:
        final_ideas = validation_node(raw_web_research, raw_arxiv_research)
        if not final_ideas:
            print("No valid, unique ideas discovered today.")
            return
    except Exception as e:
        print(f"Validation Phase failed: {e}")
        return
    
    # PHASE 3: BUILDING
    batch_name = f"ai_scout_batch_{datetime.date.today().strftime('%Y_%m_%d')}"
    os.makedirs(batch_name, exist_ok=True)
    
    try:
        print(f"\n--- [BUILD PHASE] Deploying Multi-Agent Team ---")
        folders = build_all_projects(final_ideas, GEMINI_API_KEY)
        
        for folder in folders:
            if not folder: continue
            target_path = os.path.join(batch_name, folder)
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.move(folder, batch_name)
    except Exception as e:
        print(f"Building Phase failed: {e}")

    # PHASE 4: DEPLOYMENT
    if GITHUB_TOKEN:
        try:
            print(f"\n--- [DEPLOY PHASE] Updating Lab Repository: {TARGET_REPO_NAME} ---")
            repo_url = create_github_repo(TARGET_REPO_NAME, GITHUB_TOKEN, 
                                        description="Master lab for AI prototypes generated by AutoScout")
            push_to_github(batch_name, repo_url, GITHUB_TOKEN)
        except Exception as e:
            print(f"GitHub Deployment failed: {e}")
    
    # PHASE 5: NOTIFICATION
    html_content = format_html_email(final_ideas)
    if send_email(html_content):
        save_seen_ideas([idea["problem_statement"] for idea in final_ideas])
        print("AutoScout run completed successfully.")
    
    # Cleanup batch folder locally after push
    if os.path.exists(batch_name):
        shutil.rmtree(batch_name)

if __name__ == "__main__":
    main()

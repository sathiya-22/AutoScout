import os
import json
import datetime
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from tavily import TavilyClient
import resend
from builder import generate_boilerplate
from github_handler import create_github_repo, push_to_github

# Load environment variables
load_dotenv()

# Configure API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

SEEN_IDEAS_FILE = "seen_ideas.json"

def research_node():
    """Searches for high-friction technical problems in the AI domain."""
    print("Running research phase...")
    query = (
        "biggest unsolved technical challenges OR limitations in agent orchestration, "
        "RAG optimization, and LLM contextual drift. Open discussions on reddit or hacker news."
    )
    try:
        # Perform an advanced search using Tavily
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=10,
            include_raw_content=True
        )
        
        if not response:
            print("Tavily search returned empty response.")
            return ""
            
        # Extract the meaningful content from the results
        context = ""
        for idx, result in enumerate(response.get("results", [])):
            title = result.get('title') or "Untitled"
            content = result.get('content') or "No content available."
            raw = (result.get('raw_content') or "")[:1000]
            context += f"Result {idx+1}:\nTitle: {title}\nContent: {content}\nRaw Content: {raw}\n\n"
            
        return context
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        import traceback
        traceback.print_exc()
        return ""

def competitor_check(problem_keyword):
    """Checks GitHub for similar existing solutions."""
    print(f"\nChecking GitHub for competitors regarding: {problem_keyword}")
    url = f"https://api.github.com/search/repositories?q={requests.utils.quote(problem_keyword)}&sort=stars&order=desc"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("total_count", 0) > 0:
                top_repo = data["items"][0]
                return f"Found competitor: {top_repo['full_name']} (Stars: {top_repo['stargazers_count']}) - {top_repo['description']}"
            else:
                return "No major competitors found on GitHub."
        else:
            return f"GitHub API Error: {response.status_code}"
    except Exception as e:
        return f"Error connecting to GitHub API: {str(e)}"

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

def validation_node(raw_data):
    """Uses Gemini 2.5 Flash to validate problems, checks competitors, and formats them."""
    print("Running validation phase...")
    seen_ideas = load_seen_ideas()
    
    # Step 1: Extract 5 potential problems
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        extraction_prompt = f"""
        You are a Senior AI Agent Architect. Based on the following search results about AI technical challenges,
        extract 5 highly specific, underserved, and high-friction technical problems.
        Focus on Agent Orchestration, Contextual Drift, or RAG optimization constraints.
        
        Search Results:
        {raw_data}
        
        Output valid JSON exactly in this format:
        [
            {{
                "problem_statement": "Concise 2-sentence description of the gap.",
                "why_it_matters": "Why this is a valid/urgent problem right now.",
                "solution_sketch": "A high-level technical approach using current AI tools.",
                "search_keyword": "2-3 words representing the core concept to search on GitHub"
            }}
        ]
        """
        response = model.generate_content(extraction_prompt)
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:-3]
        elif text_resp.startswith("```"):
            text_resp = text_resp[3:-3]
            
        extracted_problems = json.loads(text_resp)
        
        # Validate keys
        required_keys = ["problem_statement", "why_it_matters", "solution_sketch", "search_keyword"]
        valid_extracted = []
        for p in extracted_problems:
            if all(k in p for k in required_keys):
                valid_extracted.append(p)
        extracted_problems = valid_extracted
        
    except Exception as e:
        print(f"Error in Gemini extraction: {e}")
        return []
        
    valid_ideas = []
    
    # Step 2: Validate and check competitors
    for idea in extracted_problems:
        # Check against seen ideas (simple string match on the core problem)
        if idea["problem_statement"] in seen_ideas:
            print(f"Idea skipped (already seen): {idea['problem_statement'][:50]}...")
            continue
            
        # Check GitHub for competitors
        keyword = idea.get("search_keyword", idea["problem_statement"][:20])
        competitor_status = competitor_check(keyword)
        
        # If no major competitor or it's weakly tackled, we might keep it.
        validation_prompt = f"""
        You are evaluating a startup idea for uniqueness.
        Idea: {idea['problem_statement']}
        Competitor Check Result: {competitor_status}
        
        Is this idea still powerfully valid and relatively underserved given the competitor check?
        Answer 'YES' or 'NO'. If 'YES', explain briefly.
        """
        try:
            val_response = model.generate_content(validation_prompt)
            if "YES" in val_response.text.upper():
                print(f"Idea valid! Keep: {idea['problem_statement'][:50]}...")
                valid_ideas.append(idea)
            else:
                print(f"Idea discarded due to existing competition: {idea['problem_statement'][:50]}...")
        except Exception as e:
            print(f"Validation check failed: {e}")
            
        if len(valid_ideas) >= 3:
            break
            
    return valid_ideas[:3]

def format_html_email(ideas):
    """Formats the ideas into a beautiful HTML email."""
    if not ideas:
        return "<p>No new unique ideas found today.</p>"
        
    html = '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; color: #333;">'
    html += '<h2 style="color: #2E86AB; text-align: center;">🚀 Daily AI Idea Scout</h2>'
    html += '<p>Here are your 3 unique AI technical problems for today:</p>'
    
    for idx, idea in enumerate(ideas):
        html += f"""
        <div style="background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; border-left: 4px solid #F24236; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #F24236;">Idea #{idx + 1}</h3>
            <p><strong>The Problem:</strong> {idea['problem_statement']}</p>
            <p><strong>The "Why":</strong> {idea['why_it_matters']}</p>
            <p><strong>The Solution Sketch:</strong> {idea['solution_sketch']}</p>
        </div>
        """
    html += '<hr><p style="font-size: 12px; text-align: center; color: #888;">Automated by your Python AI Agent Scout</p>'
    html += '</div>'
    return html

def send_email(html_content):
    """Sends the formatted email using Resend."""
    print("\nDispatching email via Resend...")
    try:
        params = {
            "from": "Scout <onboarding@resend.dev>",
            "to": ["sendilnathsathiya@gmail.com"],
            "subject": f"Daily AI Idea Scout - {datetime.date.today()}",
            "html": html_content
        }
        email = resend.Emails.send(params)
        print("Email sent successfully! ID:", email.get('id', 'Unknown'))
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    print(f"Starting Daily AI Idea Scout at {datetime.datetime.now()}...")
    
    if not all([GEMINI_API_KEY, TAVILY_API_KEY, RESEND_API_KEY]):
        print("Error: Missing required API keys in environment variables.")
        print("Please ensure GEMINI_API_KEY, TAVILY_API_KEY, and RESEND_API_KEY are set.")
        return

    def send_failure_notification(part, error):
        msg = f"This part of the process has failed: {part}. Error: {error}"
        print(f"NOTIFYING FAILURE: {msg}")
        try:
            resend.Emails.send({
                "from": "Scout <onboarding@resend.dev>",
                "to": ["sendilnathsathiya@gmail.com"],
                "subject": f"Process Failed: {part}",
                "html": f"<p>{msg}</p>"
            })
        except Exception as e:
            print(f"Failed to send failure email: {e}")

    try:
        raw_research = research_node()
        if not raw_research:
            send_failure_notification("Research Phase", "No data found")
            return
    except Exception as e:
        send_failure_notification("Research Phase", str(e))
        return
        
    try:
        final_ideas = validation_node(raw_research)
        if not final_ideas:
            print("No valid, unique ideas discovered today.")
            return
    except Exception as e:
        send_failure_notification("Validation Phase", str(e))
        return
    
    # Create a batch directory for today's projects
    batch_name = f"ai_scout_batch_{datetime.date.today().strftime('%Y_%m_%d')}"
    os.makedirs(batch_name, exist_ok=True)
    
    # Process each idea
    for idea in final_ideas:
        try:
            print(f"\n--- Building Idea: {idea['problem_statement'][:50]}... ---")
            
            # 1. Generate Boilerplate
            folder = generate_boilerplate(idea, GEMINI_API_KEY)
            
            # 2. Move into batch folder
            import shutil
            target_path = os.path.join(batch_name, folder)
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.move(folder, batch_name)
                
        except Exception as e:
            send_failure_notification(f"Building Idea: {idea.get('problem_statement', 'Unknown')[:30]}", str(e))

    # Push the entire batch as one repository
    if GITHUB_TOKEN:
        try:
            print(f"\n--- Creating Batch Repository: {batch_name} ---")
            repo_url = create_github_repo(batch_name, GITHUB_TOKEN)
            push_to_github(batch_name, repo_url, GITHUB_TOKEN)
        except Exception as e:
            send_failure_notification("GitHub Deployment Phase", str(e))
    else:
        print(f"\nSkipping GitHub push for {batch_name} (GITHUB_TOKEN missing)")

    # Finally, send the daily summary email
    html_content = format_html_email(final_ideas)
    if send_email(html_content):
        save_seen_ideas([idea["problem_statement"] for idea in final_ideas])
        print("Finished successfully.")

if __name__ == "__main__":
    main()

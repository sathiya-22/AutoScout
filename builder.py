import os
import json
import google.generativeai as genai

def generate_boilerplate(idea, api_key):
    """Uses Gemini to generate README.md, main.py, and requirements.txt for an idea."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are an expert AI software engineer. Generate a boilerplate project for the following idea:
    Problem: {idea['problem_statement']}
    Why it matters: {idea['why_it_matters']}
    Solution Sketch: {idea['solution_sketch']}
    
    Generate three files exactly in this JSON format:
    {{
        "README.md": "Content of README...",
        "main.py": "Content of main.py...",
        "requirements.txt": "Content of requirements.txt..."
    }}
    
    The README should be professional. The main.py should be a functional starting point (even if it's just a core class/function structure).
    The requirements.txt should list necessary libraries.
    """
    
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:-3]
        elif text_resp.startswith("```"):
            text_resp = text_resp[3:-3]
            
        files = json.loads(text_resp)
        
        # Create directory
        folder_name = idea.get('search_keyword', 'ai_project').replace(" ", "_").lower()
        os.makedirs(folder_name, exist_ok=True)
        
        for filename, content in files.items():
            with open(os.path.join(folder_name, filename), "w") as f:
                f.write(content)
                
        print(f"Generated boilerplate in folder: {folder_name}")
        return folder_name
    except Exception as e:
        print(f"Error generating boilerplate: {e}")
        raise e

import os
import json
from google import genai

def generate_batch_boilerplate(ideas, api_key):
    """Uses Gemini to generate files for multiple ideas in a single request."""
    if not ideas:
        return []
        
    client = genai.Client(api_key=api_key)
    
    ideas_text = ""
    for idx, idea in enumerate(ideas):
        ideas_text += f"\nProject {idx+1}:\nProblem: {idea['problem_statement']}\nSolution: {idea['solution_sketch']}\n"
    
    prompt = f"""
    You are an expert AI software engineer. Generate boilerplate projects for the following 3 ideas:
    {ideas_text}
    
    Return a single JSON object where keys are project folder names (slugified from search_keyword)
    and values are dictionaries containing "README.md", "main.py", and "requirements.txt".
    
    Format:
    {{
        "project_folder_1": {{ "README.md": "...", "main.py": "...", "requirements.txt": "..." }},
        "project_folder_2": {{ ... }}
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:-3]
        elif text_resp.startswith("```"):
            text_resp = text_resp[3:-3]
            
        batch_files = json.loads(text_resp)
        generated_folders = []
        
        for folder_name, files in batch_files.items():
            os.makedirs(folder_name, exist_ok=True)
            for filename, content in files.items():
                with open(os.path.join(folder_name, filename), "w") as f:
                    f.write(content)
            print(f"Generated boilerplate in folder: {folder_name}")
            generated_folders.append(folder_name)
                
        return generated_folders
    except Exception as e:
        print(f"Error in batch boilerplate generation: {e}")
        raise e

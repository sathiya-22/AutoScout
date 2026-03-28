from google import genai
import json

def architect_project(client, idea):
    """Senior Architect Agent: Designs the project structure."""
    prompt = f"""
    You are a Senior AI Software Architect. Design the file structure for a functional prototype:
    PROBLEM: {idea['problem_statement']}
    SOLUTION: {idea['solution_sketch']}
    SOURCE RESEARCH: {idea.get('source_paper', 'Web Research')}
    
    Return a JSON object:
    {{
        "folder_name": "slugified-name",
        "file_list": ["main.py", "utils.py", "..."],
        "architecture_notes": "Detailed technical design overview"
    }}
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

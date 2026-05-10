from google import genai

def engineer_file(client, idea, file_name, architect_notes):
    """Lead Developer Agent: Implements the code for a specific file."""
    prompt = f"""
    You are a Lead AI Developer. Implement the following file for this prototype:
    FILE NAME: {file_name}
    PROJECT CONTEXT: {idea['problem_statement']}
    SOLUTION SKETCH: {idea['solution_sketch']}
    ARCHITECTURE NOTES: {architect_notes}
    
    Return ONLY the code for this file. Handle edge cases and include basic error handling.
    No markdown, no explanations.
    """
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text.strip()

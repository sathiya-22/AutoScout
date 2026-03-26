from google import genai

def generate_readme(client, idea, architect_notes):
    """Marketer/PM Agent: Generates a premium README.md."""
    prompt = f"""
    You are a Product Marketer at a top AI lab. Write a 'VC-ready' README.md for this project:
    TITLE: {idea.get('title', 'AI Project')}
    PROBLEM: {idea['problem_statement']}
    SOLUTION: {idea['solution_sketch']}
    DESIGN NOTES: {architect_notes}
    
    Include sections: Problem, Solution, Why it Matters, Technical Architecture, and Getting Started.
    Use professional, high-impact language.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text.strip()

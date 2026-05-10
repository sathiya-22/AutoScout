from google import genai

def generate_readme(client, idea, architect_notes):
    """Marketer/PM Agent: Generates a premium README.md."""
    prompt = f"""
    You are a Product Marketer at a top AI lab. Write a 'VC-ready' README.md for this prototype:
    TITLE: {idea.get('title', 'AI Proto')} - Scoped from {idea.get('source_paper', 'Recent Research')}
    PROBLEM: {idea['problem_statement']}
    SOLUTION: {idea['solution_sketch']}
    TECHNICAL DESIGN: {architect_notes}
    
    Include sections: Problem, Solution, Why it Matters, Technical Architecture, and Getting Started.
    Use professional, high-impact language with GitHub flavored markdown.
    """
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text.strip()

from google import genai

def generate_tests(client, idea, files_with_code):
    """QA Engineer Agent: Generates tests for the project."""
    context = "\n".join([f"--- {f['name']} ---\n{f['code']}" for f in files_with_code])
    prompt = f"""
    You are a QA Engineer. Write a comprehensive test script (tests.py) for the following code:
    {context}
    
    The project goal is: {idea['problem_statement']}
    Return ONLY the python code for the tests.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text.strip()

"""Demo Writer Agent: Generates a working demo.py so anyone cloning the repo
knows exactly how to use the tool."""


def write_demo(client, idea, files_with_code):
    """Generate a standalone demo.py that shows the tool end-to-end."""
    # Provide the first 3 files as context (avoid token overload)
    context = "\n\n".join(
        [f"# --- {f['name']} ---\n{f['code']}" for f in files_with_code[:3]]
    )

    prompt = f"""
You are a developer advocate writing an example script for a new open-source tool.

PROJECT: {idea['problem_statement']}
SOLUTION: {idea['solution_sketch']}

CODEBASE (key files):
{context}

Write a demo.py that:
1. Shows the tool being used end-to-end with a realistic, self-contained example
2. Prints clear, labelled output at each step so the user can see it working
3. Includes a short comment block at the top explaining what this demo does
4. Uses only the modules already in the codebase above (no new external dependencies)
5. Is runnable as: python demo.py

Return ONLY the Python code. No markdown fences.
"""
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
    )
    code = response.text.strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])
    return code

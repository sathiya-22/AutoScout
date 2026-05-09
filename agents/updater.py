"""Updater Agent: Reads an existing repo's code and generates one meaningful
improvement — a new feature, a bug fix, or a performance optimization."""


def generate_improvement(client, file_name, current_code, project_context):
    """Analyse the current code and return an improved version with a commit message."""
    prompt = f"""
You are a senior engineer maintaining an AI open-source tool.

PROJECT CONTEXT: {project_context}
FILE: {file_name}

CURRENT CODE:
{current_code}

Make ONE meaningful improvement. Choose the highest-value option:
- Add a missing feature that the project obviously needs
- Fix a real bug or edge case
- Improve error handling or logging
- Optimise a slow or inefficient section
- Add type hints and docstrings if completely missing

Rules:
- Change only what genuinely improves the file — no padding
- Return ONLY the improved Python code, no markdown fences
- Also return a one-line git commit message describing the change

Format your response as:
COMMIT: <commit message here>
CODE:
<improved code here>
"""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    text = response.text.strip()

    # Parse commit message and code
    commit_msg = "improvement: automated update via AutoScout"
    code = text
    if text.startswith("COMMIT:"):
        lines = text.split("\n")
        commit_msg = lines[0].replace("COMMIT:", "").strip()
        code_start = next(
            (i for i, l in enumerate(lines) if l.strip() == "CODE:"), 1
        )
        code = "\n".join(lines[code_start + 1:]).strip()

    # Strip any accidental markdown fences
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])

    return code, commit_msg

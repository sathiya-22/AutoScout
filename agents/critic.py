"""Critic Agent: Reviews generated code for one file and returns a revised version."""


def critique_and_revise(client, idea, file_name, code, architecture_notes):
    """
    Two-pass review:
      Pass 1 — critique: identify bugs, missing imports, bad practices.
      Pass 2 — revise:   fix only the issues found.

    Returns the revised code (or original if no issues found).
    """
    critique_prompt = f"""
You are a senior AI software engineer doing a code review.

FILE: {file_name}
PROJECT GOAL: {idea['problem_statement']}
ARCHITECTURE: {architecture_notes}

CODE TO REVIEW:
{code}

Identify specific issues: bugs, missing imports, unhandled exceptions, bad practices,
or anything that would prevent this file from running correctly.
Be concise and specific. Use a bullet list.
If the code looks good, respond with exactly: LGTM
"""
    critique = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=critique_prompt,
    ).text.strip()

    if critique.upper().startswith("LGTM"):
        print(f"    [CRITIC] {file_name}: LGTM ✅")
        return code

    print(f"    [CRITIC] {file_name}: issues found — revising...")

    revise_prompt = f"""
Fix the following issues in {file_name}:

ISSUES:
{critique}

ORIGINAL CODE:
{code}

Return ONLY the corrected Python code. No markdown fences, no explanations.
"""
    revised = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=revise_prompt,
    ).text.strip()

    # Strip any accidental markdown fences
    if revised.startswith("```"):
        revised = "\n".join(revised.split("\n")[1:])
    if revised.endswith("```"):
        revised = "\n".join(revised.split("\n")[:-1])

    return revised

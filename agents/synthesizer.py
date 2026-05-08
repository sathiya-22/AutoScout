from google import genai
import json


def synthesize_ideas(client, ideas):
    """Synthesizer Agent: Finds the unifying thread across 3 ideas and
    produces a single cohesive project brief for the architect to build.

    Returns a dict with:
        project_name       - slugified repo/folder name
        project_title      - human-readable title
        unified_problem    - the single problem this tool solves
        why_unified        - how the 3 ideas connect naturally
        solution_overview  - detailed description of the unified tool
        key_features       - list of features
        connection_score   - 1-10 how naturally the ideas unify
        fallback_idea_index - index of strongest single idea (used if score < 6)
    """
    ideas_text = "\n\n".join([
        f"Idea {i+1}:\n"
        f"  Problem: {idea['problem_statement']}\n"
        f"  Solution sketch: {idea['solution_sketch']}\n"
        f"  Why it matters: {idea['why_it_matters']}"
        for i, idea in enumerate(ideas)
    ])

    prompt = f"""
You are a visionary AI systems architect. You have been given 3 separate AI technical problems discovered from research:

{ideas_text}

Your task:
1. Find the natural unifying thread connecting all 3 problems.
2. Design ONE cohesive tool, library, or system that meaningfully addresses all 3 together.
3. Rate how naturally they connect on a scale of 1-10.
   - 8-10: They clearly belong together, the unified tool is obvious and powerful.
   - 6-7:  There is a reasonable connection, the unified tool is coherent.
   - 1-5:  The ideas are too unrelated; it would be a forced or incoherent combination.
4. Identify which single idea (by index 0, 1, or 2) is the strongest standalone project,
   in case the connection score is too low to unify them.

Return ONLY a valid JSON object with this exact structure:
{{
    "project_name": "slugified-repo-name",
    "project_title": "Human Readable Project Title",
    "unified_problem": "One sentence: what single problem does this unified tool solve?",
    "why_unified": "2-3 sentences explaining how the 3 ideas connect naturally",
    "solution_overview": "Detailed paragraph describing the unified tool — what it does, how it works, what makes it interesting",
    "key_features": ["Feature 1", "Feature 2", "Feature 3", "Feature 4"],
    "connection_score": 8,
    "fallback_idea_index": 0
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return json.loads(response.text.strip())

"""Semantic memory for AutoScout using Gemini embeddings + cosine similarity.
Replaces the flat seen_ideas.json string-match with proper vector deduplication.
"""
import os
import json
import datetime
import numpy as np

MEMORY_FILE = "idea_memory.json"
DUPLICATE_THRESHOLD = 0.85


def _embed(client, text):
    """Get embedding vector via Gemini text-embedding-004."""
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )
    return response.embeddings[0].values


def _cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def is_duplicate(client, problem_statement, threshold=DUPLICATE_THRESHOLD):
    """Return True if a semantically similar idea already exists in memory."""
    memory = load_memory()
    if not memory:
        return False
    try:
        new_emb = _embed(client, problem_statement)
        for entry in memory:
            sim = _cosine_similarity(new_emb, entry["embedding"])
            if sim >= threshold:
                print(
                    f"  [MEMORY] Duplicate detected (similarity={sim:.2f}): "
                    f"{entry['problem_statement'][:60]}..."
                )
                return True
        return False
    except Exception as e:
        print(f"  [MEMORY] Semantic check failed ({e}). Falling back to string match.")
        seen = {entry["problem_statement"] for entry in memory}
        return problem_statement in seen


def add_to_memory(client, problem_statement, project_name="",
                  connection_score=None, date=None):
    """Embed and persist an idea to memory."""
    memory = load_memory()
    try:
        embedding = _embed(client, problem_statement)
        memory.append({
            "problem_statement": problem_statement,
            "embedding": embedding,
            "project_name": project_name,
            "connection_score": connection_score,
            "date": date or str(datetime.date.today()),
        })
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f)
        print(f"  [MEMORY] Saved: {problem_statement[:60]}...")
    except Exception as e:
        print(f"  [MEMORY] Failed to save: {e}")

import arxiv
import time
from google import genai
from utils import gemini_generate


def get_latest_arxiv_papers(query="cs.AI OR cs.LG OR cs.CL", max_results=10, max_retries=3):
    """Fetch latest ArXiv papers using abstracts only (no PDF parsing)."""
    print(f"Searching Arxiv for: {query}...")
    for attempt in range(max_retries):
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
            papers = []
            for result in client.results(search):
                papers.append({
                    "title": result.title,
                    "summary": result.summary,
                    "entry_id": result.entry_id,
                })
            print(f"Found {len(papers)} papers on Arxiv.")
            return papers
        except Exception as e:
            if "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"  [ARXIV] Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"Error searching Arxiv: {e}")
                return []
    print("Arxiv unavailable after retries — skipping.")
    return []


def scout_arxiv_gaps(api_key, query="cs.AI OR cs.LG OR cs.CL"):
    """Find technical gaps from ArXiv abstracts (no PDF download)."""
    papers = get_latest_arxiv_papers(query=query)
    if not papers:
        print("No papers found on Arxiv.")
        return ""

    # Use abstracts only — concise and well within token limits
    context = "\n\n".join([
        f"PAPER: {p['title']}\nABSTRACT: {p['summary'][:800]}"
        for p in papers[:8]
    ])

    prompt = f"""
Analyze these recent AI research paper abstracts and identify technical gaps:

{context}

Find 3 highly specific implementation gaps or 'future work' items that could be
built into a standalone tool or library. Focus on developer friction.

Return a JSON list of objects with:
- problem_statement (technical and specific)
- why_it_matters
- solution_sketch (concrete implementation idea)
- search_keyword (for competitor research)
- source_paper (paper title)
"""
    client = genai.Client(api_key=api_key)
    try:
        response = gemini_generate(
            client, "gemini-2.0-flash", prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text
    except Exception as e:
        print(f"Error in Arxiv scouting model call: {e}")
        return ""

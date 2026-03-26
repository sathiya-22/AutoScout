import arxiv
import requests
import io
import os
from pypdf import PdfReader
from google import genai

def get_latest_arxiv_papers(query="cs.AI OR cs.LG OR cs.CL", max_results=5):
    """Searches Arxiv for the latest relevant papers."""
    print(f"Searching Arxiv for: {query}...")
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    papers = []
    for result in search.results():
        papers.append({
            "title": result.title,
            "summary": result.summary,
            "pdf_url": result.pdf_url,
            "entry_id": result.entry_id
        })
    return papers

def extract_text_from_pdf_url(pdf_url):
    """Downloads a PDF and extracts text using pypdf."""
    print(f"Downloading and parsing PDF: {pdf_url}...")
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            with io.BytesIO(response.content) as f:
                reader = PdfReader(f)
                text = ""
                # Extract first 5 pages to avoid context limits
                for page in reader.pages[:5]:
                    text += page.extract_text() + "\n"
                return text
        return ""
    except Exception as e:
        print(f"Error parsing PDF {pdf_url}: {e}")
        return ""

def scout_arxiv_gaps(api_key, query="cs.AI OR cs.LG OR cs.CL"):
    """Orchestrates Arxiv scouting to find technical gaps."""
    papers = get_latest_arxiv_papers(query=query)
    if not papers:
        return ""
        
    client = genai.Client(api_key=api_key)
    full_context = ""
    
    for paper in papers[:3]: # Deep dive into top 3
        text = extract_text_from_pdf_url(paper['pdf_url'])
        full_context += f"\n--- PAPER: {paper['title']} ---\nSUMMARY: {paper['summary']}\nEXTRACTED CONTENT: {text[:4000]}...\n"
        
    prompt = f"""
    Analyze these recent AI research papers and their implementation details:
    {full_context}
    
    Identify 3 highly technical implementation gaps or 'future work' items that could be built into a standalone tool or library.
    Return a JSON list of objects with: 
    - problem_statement (technical and specific)
    - why_it_matters
    - solution_sketch
    - search_keyword (for competitor check)
    - source_paper (The title of the paper)
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text
    except Exception as e:
        print(f"Error in Arxiv scouting: {e}")
        return ""

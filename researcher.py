import arxiv
import requests
import io
import os
from pypdf import PdfReader
from google import genai

def get_latest_arxiv_papers(query="cs.AI OR cs.LG OR cs.CL", max_results=5):
    """Searches Arxiv for the latest relevant papers using modern client pattern."""
    print(f"Searching Arxiv for: {query}...")
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for result in client.results(search):
            papers.append({
                "title": result.title,
                "summary": result.summary,
                "pdf_url": result.pdf_url,
                "entry_id": result.entry_id
            })
        return papers
    except Exception as e:
        print(f"Error searching Arxiv: {e}")
        return []

def extract_text_from_pdf_url(pdf_url):
    """Downloads a PDF and extracts text using pypdf."""
    print(f"Downloading and parsing PDF: {pdf_url}...")
    try:
        response = requests.get(pdf_url, timeout=15)
        if response.status_code == 200:
            with io.BytesIO(response.content) as f:
                reader = PdfReader(f)
                text = ""
                # Extract first 5 pages to avoid context limits
                num_pages = min(len(reader.pages), 5)
                for i in range(num_pages):
                    text += reader.pages[i].extract_text() + "\n"
                return text
        return ""
    except Exception as e:
        print(f"Error parsing PDF {pdf_url}: {e}")
        return ""

def scout_arxiv_gaps(api_key, query="cs.AI OR cs.LG OR cs.CL"):
    """Orchestrates Arxiv scouting to find technical gaps with improved prompts."""
    papers = get_latest_arxiv_papers(query=query)
    if not papers:
        print("No papers found on Arxiv.")
        return ""
        
    client = genai.Client(api_key=api_key)
    full_context = ""
    
    # Deep dive into top 3
    for paper in papers[:3]:
        text = extract_text_from_pdf_url(paper['pdf_url'])
        full_context += f"\n--- PAPER: {paper['title']} ---\nSUMMARY: {paper['summary']}\nEXTRACTED CONTENT: {text[:5000]}...\n"
        
    prompt = f"""
    Analyze these recent AI research papers and their implementation details:
    {full_context}
    
    Identify 3 highly technical implementation gaps, specific performance bottlenecks, or 'future work' items 
    that could be built into a standalone tool, library, or architecture prototype.
    Focus on developer friction and architectural complexity.

    Return a JSON list of objects: 
    - problem_statement (technical and specific)
    - why_it_matters
    - solution_sketch (concrete implementation idea)
    - search_keyword (for competitor check)
    - source_paper (The title of the paper)
    """
    
    try:
        # Standardizing on gemini-1.5-flash for extraction
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text
    except Exception as e:
        print(f"Error in Arxiv scouting model call: {e}")
        return ""

import os
import io
import pandas as pd
from typing import List, Dict, Union
from dotenv import load_dotenv
from PIL import Image

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

# --- Mock LLM and Embeddings ---
class MockLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not api_key:
            print("Warning: OpenAI API key not set. MockLLM will provide generic responses.")

    def generate_text(self, prompt: str) -> str:
        # Simulate LLM generating text, e.g., summaries or descriptions
        if "summarize" in prompt.lower():
            return f"Mock Summary of: {prompt[prompt.find(':')+1:].strip()}"
        elif "describe the image" in prompt.lower():
            return "Mock image description: This is an image of a spreadsheet with financial data."
        return f"Mock LLM Response for: {prompt}"

class MockEmbeddings:
    def embed_query(self, text: str) -> List[float]:
        # Simple hash-based embedding for demo purposes
        return [float(ord(c)) / 100 for c in text[:10]] + [0.0] * (1536 - len(text[:10])) # Simulate 1536 dim vector

class MockVectorStore:
    def __init__(self):
        self.documents = {} # {id: original_content}
        self.embeddings = {} # {id: embedding}
        self.metadata = {} # {id: {"type": "text", "source": "report.pdf"}}
        self.next_id = 0

    def add_document(self, content: str, embedding: List[float], metadata: Dict):
        doc_id = self.next_id
        self.documents[doc_id] = content
        self.embeddings[doc_id] = embedding
        self.metadata[doc_id] = metadata
        self.next_id += 1

    def similarity_search(self, query_embedding: List[float], k: int = 3) -> List[Dict]:
        query_vec = query_embedding
        scores = []
        for doc_id, doc_vec in self.embeddings.items():
            score = sum(q * d for q, d in zip(query_vec, doc_vec))
            scores.append((score, self.documents[doc_id], self.metadata[doc_id]))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [{"content": c, "metadata": m} for _, c, m in scores[:k]]

# --- Specialized Parsing & Structuring Functions ---

def parse_table_from_csv_string(csv_string: str) -> pd.DataFrame:
    """Simulates parsing a table from a CSV string."""
    print("\n--- Parsing Table Data ---")
    data_io = io.StringIO(csv_string)
    df = pd.read_csv(data_io)
    print(f"Parsed DataFrame:\n{df.head()}")
    return df

def describe_dataframe_for_rag(df: pd.DataFrame, llm: MockLLM) -> str:
    """Generates a text description of a DataFrame suitable for RAG."""
    print("\n--- Describing DataFrame for RAG ---")
    summary = f"This table contains data with columns: {', '.join(df.columns.tolist())}.\n"
    summary += f"It has {len(df)} rows. Here are the first few rows:\n{df.head().to_string()}\n"
    
    # Use LLM to enhance the summary if needed
    prompt = f"Summarize the following table data for retrieval purposes, highlighting key metrics or relationships:\n{df.to_string()}"
    llm_summary = llm.generate_text(prompt)
    print(f"LLM-enhanced table summary:\n{llm_summary}")
    return llm_summary

def describe_image_for_rag(image_path: str, llm: MockLLM) -> str:
    """Simulates using a multi-modal LLM or OCR to describe an image."""
    print(f"\n--- Describing Image for RAG: {image_path} ---")
    # In a real system, you'd use a vision model or OCR
    # For this demo, we mock the output
    if "financial_dashboard.png" in image_path:
        description = llm.generate_text("Describe the image: A financial dashboard showing sales trends.")
        return description + " It shows quarterly sales figures, revenue, and profit margins, with charts illustrating growth."
    elif "process_flow.png" in image_path:
        description = llm.generate_text("Describe the image: A process flow diagram.")
        return description + " This diagram illustrates a five-step data processing workflow, starting from data ingestion to final reporting."
    return llm.generate_text(f"Describe the image: {image_path}")

# --- Main RAG System ---
class MultiModalRAGSystem:
    def __init__(self, llm: MockLLM, embeddings: MockEmbeddings):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = MockVectorStore()

    def add_text_document(self, content: str, source: str = "document"):
        embedding = self.embeddings.embed_query(content)
        self.vector_store.add_document(content, embedding, {"type": "text", "source": source})
        print(f"Added text document from {source}.")

    def add_table_document(self, df: pd.DataFrame, source: str = "table"):
        # Store the original DataFrame or a reference
        # For RAG, we primarily store its text summary
        text_summary = describe_dataframe_for_rag(df, self.llm)
        embedding = self.embeddings.embed_query(text_summary)
        self.vector_store.add_document(text_summary, embedding, {"type": "table_summary", "source": source, "original_data_ref": df.to_json()})
        print(f"Added table summary from {source}.")
        # Optionally, you could also index specific column names or key cells for precise retrieval
    
    def add_image_document(self, image_path: str, source: str = "image"):
        # Here, we only index the text description of the image
        image_description = describe_image_for_rag(image_path, self.llm)
        embedding = self.embeddings.embed_query(image_description)
        self.vector_store.add_document(image_description, embedding, {"type": "image_description", "source": source, "image_path": image_path})
        print(f"Added image description from {source}.")

    def query(self, user_query: str) -> List[Dict]:
        print(f"\n==== Querying: {user_query} ====")
        query_embedding = self.embeddings.embed_query(user_query)
        retrieved_items = self.vector_store.similarity_search(query_embedding, k=3)

        results = []
        for item in retrieved_items:
            print(f"\n--- Retrieved Item (Type: {item['metadata']['type']}, Source: {item['metadata']['source']}) ---")
            print(f"Content: {item['content']}")
            
            # Further processing based on type (e.g., if type is table_summary, retrieve actual data)
            if item['metadata']['type'] == 'table_summary' and 'original_data_ref' in item['metadata']:
                # In a real system, you'd fetch the actual DataFrame
                # For demo, we just print a placeholder
                print("[Note: For 'table_summary', actual DataFrame could be retrieved here for precise query.]")
            
            results.append(item)
        
        # Use LLM to synthesize a final answer from retrieved items
        context_for_llm = "\n\n".join([f"Source: {res['metadata']['source']} ({res['metadata']['type']})\nContent: {res['content']}" for res in results])
        llm_prompt = f"Based on the following context, answer the user query: '{user_query}'\n\nContext:\n{context_for_llm}\n\nAnswer:"
        final_answer = self.llm.generate_text(llm_prompt)
        print(f"\n--- LLM Synthesized Answer ---\n{final_answer}\n----------------------------")
        return results


if __name__ == "__main__":
    print("Initializing Multi-modal RAG for Semi-structured Data demo...")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    mock_llm = MockLLM(api_key=openai_api_key)
    mock_embeddings = MockEmbeddings()
    multi_modal_rag = MultiModalRAGSystem(llm=mock_llm, embeddings=mock_embeddings)

    # --- Simulate adding various types of knowledge ---

    # 1. Add unstructured text
    multi_modal_rag.add_text_document(
        "The Q1 2024 earnings report highlights a strong performance in the cloud division, "
        "exceeding projections by 15%. Investments in R&D have increased by 20% year-over-year.",
        source="Q1_2024_report.pdf"
    )

    # 2. Add structured data from a simulated CSV/Excel table
    csv_data = """
Region,Sales (USD),Profit (USD),Growth (%)
North,150000,30000,12
South,120000,24000,10
East,200000,45000,18
West,180000,35000,15
"""
    sales_df = parse_table_from_csv_string(csv_data)
    multi_modal_rag.add_table_document(sales_df, source="sales_data.csv")

    # 3. Add information from a simulated diagram/image
    # Using Pillow to just simulate an image file, no actual image processing here
    # Image.new('RGB', (60, 30), color = 'red').save('financial_dashboard.png')
    # Image.new('RGB', (60, 30), color = 'blue').save('process_flow.png')
    multi_modal_rag.add_image_document("financial_dashboard.png", source="dashboard_screenshot")
    multi_modal_rag.add_image_document("process_flow.png", source="system_diagram")

    print("\n--- Running Multi-modal Queries ---")

    # Query 1: Text-based
    multi_modal_rag.query("What are the key highlights from the Q1 2024 earnings report?")

    # Query 2: Table-based (requires understanding numerical data)
    multi_modal_rag.query("Which region had the highest sales and what was its growth percentage?")

    # Query 3: Image-based (requires understanding visual content description)
    multi_modal_rag.query("Can you describe the system diagram?")

    # Query 4: Cross-modal (might touch on both text and table data)
    multi_modal_rag.query("Tell me about the financial performance and any growth figures mentioned.")
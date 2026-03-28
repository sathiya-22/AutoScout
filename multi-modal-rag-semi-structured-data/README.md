# Multi-modal RAG for Semi-structured Data

## Problem
A significant portion (40-60%) of critical enterprise knowledge is embedded in diverse and semi-structured formats such as tables, Excel files, and diagrams. Standard Retrieval-Augmented Generation (RAG) systems primarily focus on unstructured text, struggling significantly to parse, understand, and extract information effectively from these rich, visually-oriented data types for retrieval. This leads to vast amounts of valuable information remaining siloed and inaccessible to AI agents.

## Solution
This project focuses on developing advanced multi-modal RAG systems capable of processing, structuring, and representing information from these challenging semi-structured formats. The solution involves:
1.  **Specialized Parsing:** Techniques for extracting data from visual layouts, including tables (from images or PDFs), spreadsheets, and diagrams.
2.  **Data Structuring & Representation:** Converting parsed data into structured formats (e.g., JSON, dataframes) and then into comprehensive textual descriptions or rich embeddings that capture relationships, not just content.
3.  **Multi-vector Indexing:** Storing different representations (raw text, structured data summaries, image captions, table summaries) in a vector database to enable diverse retrieval strategies.
4.  **Query-time Adaptation:** Dynamically choosing the best retrieval method based on the user's query (e.g., if a query asks for numerical data from a table, activate table-specific retrieval).

## Project Structure
The `main.py` demonstrates:
*   **Simulated Data Sources:** Example functions for parsing tabular data (CSV string) and describing images.
*   **Data Processing:** Converting raw data into structured Python objects and then into text summaries suitable for embedding.
*   **Multi-vector Indexing:** Indexing these diverse representations (raw text, table summaries, image descriptions) into a single vector store.
*   **Querying:** Demonstrating how a query can retrieve relevant information across these different modalities.

## Getting Started
1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Set your OpenAI API key (or equivalent) in your environment variables.
4.  Run `python main.py` to see how information from tables and visual descriptions can be integrated into a RAG system.

## Future Enhancements
*   Integration with actual OCR libraries (Tesseract, Google Vision API).
*   Advanced layout parsing tools (e.g., LayoutLM, DocILE).
*   Graph-based representations for diagrams and complex relationships.
*   Refined data-to-text generation for structured content.
*   Implementing a more sophisticated query router to direct queries to the most appropriate indexing strategy.
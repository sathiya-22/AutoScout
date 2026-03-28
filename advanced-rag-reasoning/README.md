# Advanced RAG with Reasoning Capabilities

## Problem
Traditional Retrieval-Augmented Generation (RAG) systems primarily rely on embedding similarity to retrieve information. While effective for semantic search, this approach struggles significantly when tasks require:
*   **Logical Dependencies:** Understanding relationships like function callers in code, or cause-and-effect.
*   **Precise Numerical Relationships:** Performing computations or comparing specific numerical values (e.g., distinguishing '31+24' from '55' or comparing exact figures).

This limitation severely impacts RAG's effectiveness for reasoning-intensive tasks, leading to inaccurate or incomplete answers when the core information isn't just "similar" but requires deeper logical or computational understanding.

## Solution
This project explores an evolution of RAG systems by integrating active reasoning capabilities. Instead of solely relying on passive embedding similarity for retrieval, we introduce an "agentic" approach where the LLM can:
1.  **Interact with Tools:** Utilize specialized tools like `grep` for precise string matching in codebases or simulated file systems, and a `calculator` for direct numerical computation.
2.  **Adaptive Exploration:** Dynamically decide which tools to use and when, allowing for more targeted and logically sound information retrieval and processing.
3.  **Direct LLM/Code Integration:** Directly leverage the LLM's inherent reasoning abilities or integrate code execution for complex logical and computational tasks, bypassing the limitations of vector search for these specific types of problems.

## Project Structure
The `main.py` demonstrates:
*   **A Simulated Knowledge Base:** Simple text documents for standard RAG, plus a "codebase" for agentic exploration.
*   **Standard RAG:** Basic vector search for semantic questions.
*   **Agent Tools:**
    *   `grep_tool`: Simulates searching through a codebase for exact matches.
    *   `calculate_tool`: Executes Python expressions.
*   **Agentic RAG Flow:** An LLM-powered agent that can decide to use these tools based on the query, combining retrieval with active reasoning.

## Getting Started
1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Set your OpenAI API key (or equivalent) in your environment variables.
4.  Run `python main.py` to observe how the agent uses tools to answer questions that traditional RAG might miss.

## Future Enhancements
*   Integration with actual file systems and code repositories.
*   More sophisticated reasoning agents (e.g., ReAct, ToolFormer).
*   Support for more complex data structures and querying methods within the knowledge base.
*   Benchmarking against traditional RAG for reasoning tasks.
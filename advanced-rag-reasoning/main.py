import os
from typing import List, Dict, Union
from dotenv import load_dotenv

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

# --- Mock LLM and Embeddings for simplicity ---
# In a real application, replace these with actual LangChain/OpenAI components
class MockLLM:
    def __init__(self, api_key: str):
        if not api_key:
            print("Warning: OpenAI API key not set. MockLLM will provide generic responses.")
        # For this demo, we don't actually use the key but it's good practice
        self.api_key = api_key

    def chat_completion(self, messages: List[Dict], tools: List[Dict] = None, tool_choice: Union[str, Dict] = "auto") -> str:
        # Simulate LLM's ability to call tools or respond directly
        last_message_content = messages[-1]["content"]
        print(f"\n--- MockLLM Input Prompt for tool selection/response ---\n{last_message_content}\n")

        if "what is 2+2" in last_message_content.lower() or "calculate" in last_message_content.lower():
            return '{"tool_calls": [{"function": {"name": "calculate_tool", "arguments": "{\"expression\": \"2+2\"}"}}]}'
        elif "find all usages of 'process_data'" in last_message_content.lower():
            return '{"tool_calls": [{"function": {"name": "grep_tool", "arguments": "{\"query\": \"process_data\", \"files\": [\"module_a.py\", \"module_b.py\"]}"}}]}'
        elif "who is the CEO" in last_message_content.lower():
            # Simulate retrieving from RAG first, then LLM processing it
            return "The CEO is John Doe, as per the company's internal documents."
        elif "grep" in last_message_content.lower() and "def " in last_message_content.lower():
             return '{"tool_calls": [{"function": {"name": "grep_tool", "arguments": "{\"query\": \"def calculate_total\", \"files\": [\"accounting.py\"]}"}}]}'
        
        return "MockLLM response: I'm processing your request. Please specify if you need a calculation or code search."

class MockEmbeddings:
    def embed_query(self, text: str) -> List[float]:
        # Simple hash-based embedding for demo purposes
        return [float(ord(c)) / 100 for c in text[:10]] + [0.0] * (1536 - len(text[:10])) # Simulate 1536 dim vector

class MockVectorStore:
    def __init__(self):
        self.documents = {} # {id: text}
        self.embeddings = {} # {id: embedding}
        self.next_id = 0

    def add_documents(self, texts: List[str], embedder: MockEmbeddings):
        for text in texts:
            doc_id = self.next_id
            self.documents[doc_id] = text
            self.embeddings[doc_id] = embedder.embed_query(text)
            self.next_id += 1

    def similarity_search(self, query_embedding: List[float], k: int = 2) -> List[str]:
        # Very basic similarity search (dot product)
        query_vec = query_embedding
        scores = []
        for doc_id, doc_vec in self.embeddings.items():
            # Simple dot product for similarity
            score = sum(q * d for q, d in zip(query_vec, doc_vec))
            scores.append((score, self.documents[doc_id]))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scores[:k]]

# --- Simulated Knowledge Base and Codebase ---
KB_DOCUMENTS = [
    "The company's mission is to innovate in AI solutions.",
    "John Doe is the CEO of our company. He founded it in 2018.",
    "Our latest product launch was on December 1st, 2023, featuring enhanced security.",
    "Annual report 2023: Revenue grew by 15%, profit by 10%.",
    "Employee benefits include health insurance, 401k, and unlimited PTO."
]

# Simulate a codebase with multiple files
CODEBASE = {
    "module_a.py": """
def initialize_system():
    print("System initialized.")

def process_data(input_data):
    # Important data processing logic
    return input_data.upper()

class DataProcessor:
    def __init__(self):
        pass
    def run(self, data):
        return process_data(data)
""",
    "module_b.py": """
from module_a import process_data

def validate_input(data):
    if not isinstance(data, str):
        raise ValueError("Input must be string.")
    return True

def main_flow(data):
    validate_input(data)
    processed = process_data(data) # Usage of process_data
    print(f"Main flow processed: {processed}")
    return processed
""",
    "accounting.py": """
def calculate_tax(amount):
    return amount * 0.05

def calculate_total(item_prices):
    total = sum(item_prices)
    tax = calculate_tax(total)
    return total + tax
"""
}

# --- Agent Tools ---
def grep_tool(query: str, files: List[str] = None) -> str:
    """
    Searches for a specific query string within simulated code files.
    Args:
        query (str): The string to search for.
        files (List[str], optional): List of filenames to search within. If None, searches all.
    Returns:
        str: Matching lines from files.
    """
    print(f"\n--- TOOL CALL: grep_tool(query='{query}', files={files}) ---")
    results = []
    target_files = files if files else CODEBASE.keys()
    for filename in target_files:
        if filename in CODEBASE:
            content = CODEBASE[filename]
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if query in line:
                    results.append(f"{filename}:{i+1}: {line.strip()}")
        else:
            results.append(f"Error: File '{filename}' not found.")
    return "\n".join(results) if results else f"No matches found for '{query}'."

def calculate_tool(expression: str) -> str:
    """
    Executes a simple mathematical expression.
    Args:
        expression (str): The mathematical expression to evaluate (e.g., "2+2", "10*5").
    Returns:
        str: The result of the calculation or an error message.
    """
    print(f"\n--- TOOL CALL: calculate_tool(expression='{expression}') ---")
    try:
        # WARNING: eval() is dangerous with untrusted input. For demo purposes only.
        result = eval(expression)
        return f"The result of '{expression}' is {result}"
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"

# Tools available to the agent
AGENT_TOOLS = {
    "grep_tool": grep_tool,
    "calculate_tool": calculate_tool
}

# Define tool schemas for the LLM
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "grep_tool",
            "description": "Searches for a specific query string within simulated code files. "
                           "Can specify a list of files to search within.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The string to search for."},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional list of filenames to search. If empty, searches all files."},
                },
                "required": ["query"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_tool",
            "description": "Executes a simple mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The mathematical expression to evaluate (e.g., '2+2', '10*5')."},
                },
                "required": ["expression"],
            },
        }
    }
]

# --- Agentic RAG Orchestration ---
class AgenticRAGSystem:
    def __init__(self, llm: MockLLM, embeddings: MockEmbeddings, vector_store: MockVectorStore, tools: Dict, tool_schemas: List[Dict]):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.tools = tools
        self.tool_schemas = tool_schemas
        self.messages = []

    def _call_llm_with_tools(self, prompt: str) -> str:
        self.messages.append({"role": "user", "content": prompt})
        response_str = self.llm.chat_completion(self.messages, tools=self.tool_schemas)
        self.messages.append({"role": "assistant", "content": response_str})
        return response_str

    def run_query(self, query: str) -> str:
        print(f"\n==== Processing Query: {query} ====")
        self.messages = [{"role": "system", "content": "You are a helpful assistant. Use the provided tools if necessary."}]

        # First, try to get initial context from vector store (traditional RAG)
        query_embedding = self.embeddings.embed_query(query)
        retrieved_docs = self.vector_store.similarity_search(query_embedding, k=2)
        rag_context = "\n".join(retrieved_docs)
        print(f"\n--- Retrieved RAG Context ---\n{rag_context}\n---------------------------")

        # Formulate initial prompt for LLM, including RAG context
        initial_prompt = (
            f"User Query: {query}\n\n"
            f"Relevant Context from Knowledge Base:\n{rag_context}\n\n"
            "Please respond to the user query. If you need to perform a calculation or search code, "
            "use the available tools. Only use information from the context if it directly answers the question, "
            "otherwise, rely on your general knowledge or tools."
        )
        
        llm_response = self._call_llm_with_tools(initial_prompt)

        # Check if LLM decided to call a tool
        try:
            response_obj = json.loads(llm_response)
            if "tool_calls" in response_obj:
                tool_calls = response_obj["tool_calls"]
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    if function_name in self.tools:
                        tool_output = self.tools[function_name](**function_args)
                        print(f"\n--- Tool Output for {function_name} ---\n{tool_output}\n--------------------------")
                        
                        # Feed tool output back to LLM for final response
                        tool_feedback_prompt = (
                            f"The previous query was: '{query}'.\n"
                            f"You decided to call the tool '{function_name}' with arguments {function_args}.\n"
                            f"The tool returned the following output:\n{tool_output}\n\n"
                            "Please provide a final, user-friendly answer based on this tool output and the original query."
                        )
                        self.messages.append({"role": "tool", "content": tool_output})
                        final_llm_response = self.llm.chat_completion(self.messages)
                        return final_llm_response
                    else:
                        return f"Agent tried to call unknown tool: {function_name}"
            
            # If no tool calls, it's a direct LLM response
            return llm_response

        except json.JSONDecodeError:
            # LLM did not return a JSON object (no tool call)
            return llm_response # Direct LLM response

if __name__ == "__main__":
    print("Initializing Advanced RAG with Reasoning Capabilities demo...")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    mock_llm = MockLLM(api_key=openai_api_key)
    mock_embeddings = MockEmbeddings()
    mock_vector_store = MockVectorStore()

    print("Adding documents to vector store...")
    mock_vector_store.add_documents(KB_DOCUMENTS, mock_embeddings)

    agentic_rag = AgenticRAGSystem(
        llm=mock_llm,
        embeddings=mock_embeddings,
        vector_store=mock_vector_store,
        tools=AGENT_TOOLS,
        tool_schemas=TOOL_SCHEMAS
    )

    print("\n--- Running Queries ---")

    # Query 1: Requires calculation (beyond simple RAG)
    result1 = agentic_rag.run_query("What is 2+2?")
    print(f"\nFINAL ANSWER: {result1}")

    # Query 2: Requires code search (beyond simple RAG)
    result2 = agentic_rag.run_query("Find all usages of 'process_data' function in the codebase.")
    print(f"\nFINAL ANSWER: {result2}")

    # Query 3: Requires traditional RAG (semantic search)
    result3 = agentic_rag.run_query("Who is the CEO of the company?")
    print(f"\nFINAL ANSWER: {result3}")

    # Query 4: Combined - specific code function and its definition
    result4 = agentic_rag.run_query("Where is the 'calculate_total' function defined and what does it do?")
    print(f"\nFINAL ANSWER: {result4}")
import os
import json
from functools import wraps
from typing import Callable, Any, Dict, List

# Mock LLM and Tool setup (replace with actual LangChain/LlamaIndex components in a real app)
class MockLLM:
    def generate(self, prompt: str, tools: List[Dict] = None) -> str:
        print(f"\n--- LLM Input ---\n{prompt}\n-----------------")
        if "current weather" in prompt.lower() and tools:
            # Simulate LLM deciding to call a tool
            return json.dumps({
                "tool_name": "get_current_weather",
                "args": {"location": "San Francisco", "unit": "celsius"}
            })
        elif "calculate" in prompt.lower() and tools:
            return json.dumps({
                "tool_name": "calculator",
                "args": {"expression": "2+2"}
            })
        return f"I processed your request: '{prompt}'. LLM response generated."

def get_current_weather(location: str, unit: str = "fahrenheit") -> str:
    """Get the current weather in a given location."""
    print(f"--- TOOL CALL: get_current_weather({location}, {unit}) ---")
    if location == "San Francisco":
        return f"The current weather in {location} is 22 degrees {unit}."
    return f"Weather data for {location} not available."

def calculator(expression: str) -> str:
    """Executes a mathematical expression."""
    print(f"--- TOOL CALL: calculator({expression}) ---")
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error calculating '{expression}': {e}"

# Tools available to the agent
TOOLS = {
    "get_current_weather": get_current_weather,
    "calculator": calculator
}
TOOL_SCHEMAS = [
    {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    },
    {
        "name": "calculator",
        "description": "Executes a mathematical expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "The mathematical expression to evaluate, e.g., '2+2'"},
            },
            "required": ["expression"],
        },
    }
]

# --- Tracing Mechanism ---
def trace_agent_step(func: Callable) -> Callable:
    """Decorator to trace LLM calls and tool usage."""
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        step_name = func.__name__
        print(f"\n[TRACE] Starting step: {step_name}")
        try:
            result = func(self, *args, **kwargs)
            print(f"[TRACE] Step '{step_name}' completed. Result type: {type(result)}")
            return result
        except Exception as e:
            print(f"[TRACE] Step '{step_name}' failed with error: {e}")
            raise
    return wrapper

# --- Orchestration Layer (Custom Runtime) ---
class AgentRuntime:
    def __init__(self, llm: MockLLM, tools: Dict[str, Callable], tool_schemas: List[Dict]):
        self.llm = llm
        self.tools = tools
        self.tool_schemas = tool_schemas
        self.conversation_history = []
        self.state = {"turn": 0}

    @trace_agent_step
    def _call_llm(self, prompt: str) -> str:
        """Internal method to call the LLM."""
        # In a real scenario, convert tool_schemas to LLM-compatible format
        llm_response = self.llm.generate(prompt, tools=self.tool_schemas)
        self.conversation_history.append({"role": "llm", "content": llm_response})
        return llm_response

    @trace_agent_step
    def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """Internal method to execute a tool."""
        if tool_name in self.tools:
            print(f"[TRACE] Executing tool: {tool_name} with args: {args}")
            tool_output = self.tools[tool_name](**args)
            self.conversation_history.append({"role": "tool_output", "content": tool_output})
            return tool_output
        else:
            return f"Error: Tool '{tool_name}' not found."

    def run_agent_turn(self, user_input: str) -> str:
        """Runs a single turn of the agent's interaction."""
        self.state["turn"] += 1
        print(f"\n==== Turn {self.state['turn']} ====")
        self.conversation_history.append({"role": "user", "content": user_input})
        print(f"[USER] {user_input}")

        # 1. Agent decides what to do (LLM call)
        # In a real scenario, this prompt would include history and tool definitions
        llm_decision_prompt = f"User input: {user_input}\n\n" \
                              f"Available tools: {json.dumps(self.tool_schemas, indent=2)}\n\n" \
                              "Based on the user input, decide if a tool should be called. " \
                              "If a tool is needed, respond with a JSON object like " \
                              '{"tool_name": "...", "args": {...}}. ' \
                              "Otherwise, generate a direct response."
        
        llm_response_str = self._call_llm(llm_decision_prompt)

        # 2. Parse LLM response and act
        try:
            llm_response_json = json.loads(llm_response_str)
            tool_name = llm_response_json.get("tool_name")
            tool_args = llm_response_json.get("args", {})

            if tool_name and tool_args is not None:
                # Execute tool and feed result back to LLM (conceptual)
                tool_output = self._execute_tool(tool_name, tool_args)
                print(f"[TOOL OUTPUT] {tool_output}")
                # A real agent would now take this tool_output and generate a final response
                # For simplicity, we just return the tool output
                final_response = f"Agent used {tool_name}: {tool_output}"
            else:
                final_response = llm_response_str # Direct LLM response
        except json.JSONDecodeError:
            final_response = llm_response_str # LLM returned a direct string, not tool call
        
        print(f"[AGENT FINAL RESPONSE] {final_response}")
        return final_response

    def get_history(self) -> List[Dict]:
        return self.conversation_history

if __name__ == "__main__":
    print("Initializing AI Agent Observability & Control demo...")
    
    # Example: Using real API key (if needed)
    # os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY"
    # if not os.getenv("OPENAI_API_KEY"):
    #     print("Warning: OPENAI_API_KEY environment variable not set. Mock LLM will be used.")

    mock_llm = MockLLM()
    agent_runtime = AgentRuntime(llm=mock_llm, tools=TOOLS, tool_schemas=TOOL_SCHEMAS)

    print("\n--- Running Agent Interactions ---")
    agent_runtime.run_agent_turn("What's the weather like in San Francisco?")
    agent_runtime.run_agent_turn("What is 2+2?")
    agent_runtime.run_agent_turn("Tell me a fun fact.") # Should trigger direct LLM response

    print("\n--- Conversation History ---")
    for entry in agent_runtime.get_history():
        print(f"[{entry['role'].upper()}] {entry['content']}")
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Import our tools
from tools.fetch_stock_data import fetch_stock_data
from tools.technical_indicators import calculate_indicators
from tools.anomaly_detection import detect_anomalies

load_dotenv()

# --- Tool Definitions ---
# This is how we tell the LLM what tools exist and how to use them
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_stock_data",
            "description": "Fetches live and historical stock data for a given ticker. Use this when the user asks about current price, market cap, PE ratio, 52-week high/low, or general stock information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL'"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period for historical data e.g. '1mo', '3mo', '6mo', '1y'",
                        "default": "3mo"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_indicators",
            "description": "Calculates technical indicators like RSI, MACD, Bollinger Bands and Moving Averages. Use this when user asks about technical analysis, trends, buy/sell signals, or momentum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period for analysis",
                        "default": "6mo"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "Detects unusual price or volume activity in a stock using Z-score analysis. Use this when user asks about unusual activity, volume spikes, price anomalies, or suspicious movements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period to analyze",
                        "default": "6mo"
                    }
                },
                "required": ["ticker"]
            }
        }
    }
]

# --- Tool Executor ---
# This actually runs the tool the LLM asks for
def execute_tool(tool_name: str, tool_args: dict) -> str:
    print(f"\n🔧 Agent calling tool: {tool_name} with {tool_args}")
    
    if tool_name == "fetch_stock_data":
        result = fetch_stock_data(**tool_args)
    elif tool_name == "calculate_indicators":
        result = calculate_indicators(**tool_args)
    elif tool_name == "detect_anomalies":
        result = detect_anomalies(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return json.dumps(result, default=lambda x: str(x))


# --- Agent Brain ---
def run_agent(user_query: str) -> str:
    """
    Main agent loop — ReAct pattern.
    Reason about what tools to use, Act by calling them,
    observe results, repeat until final answer.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Conversation history
    messages = [
        {
            "role": "system",
            "content": """You are AlphaAgent — a professional stock market analyst AI. 
You have access to real-time market data tools.

When answering questions:
1. Always fetch real data using your tools — never guess or make up numbers
2. Use multiple tools when needed for a complete analysis
3. Provide clear, professional insights based on the data
4. Explain what the indicators mean in simple terms
5. Always mention the data is real-time and date-specific

Be concise but thorough. Think like a professional analyst."""
        },
        {
            "role": "user",
            "content": user_query
        }
    ]
    
    print(f"\n🤖 AlphaAgent thinking about: '{user_query}'")
    
    # ReAct loop — agent keeps going until it has a final answer
    while True:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1000
        )
        
        message = response.choices[0].message
        
        # If agent wants to call tools
        if message.tool_calls:
            # Add agent's decision to history
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            # Execute each tool and add results to history
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_result = execute_tool(tool_name, tool_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        
        # If agent has final answer
        else:
            return message.content


# --- Test it ----
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 ALPHAAGENT — Autonomous Stock Market AI")
    print("=" * 60)
    
    # Test query
    answer = run_agent("Give me a complete analysis of Reliance Industries stock")
    print("\n📊 ALPHAAGENT RESPONSE:")
    print("=" * 60)
    print(answer)
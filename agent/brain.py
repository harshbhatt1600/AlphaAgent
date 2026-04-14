import os
import json
import logging
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from tools.news_sentiment import get_stock_news

# Import tools
from tools.fetch_stock_data import fetch_stock_data
from tools.technical_indicators import calculate_indicators
from tools.anomaly_detection import detect_anomalies

load_dotenv()

# --- Setup ---
console = Console()
logging.basicConfig(
    filename="data/agent_logs.txt",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# --- Tool Definitions ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_news",
            "description": "Fetches latest news for a stock and performs sentiment analysis. Use when user asks about news, recent events, why a stock moved, market sentiment, or what's happening with a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol e.g. 'TCS.NS'"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Full company name e.g. 'Tata Consultancy Services'"
                    },
                    "num_articles": {
                        "type": "integer",
                        "description": "Number of articles to analyze (default 10)",
                        "default": 10
                    }
                },
                "required": ["ticker", "company_name"]
            }
    }
    },
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
                        "description": "Time period e.g. '1mo', '3mo', '6mo', '1y'",
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
            "description": "Calculates technical indicators — RSI, MACD, Bollinger Bands, Moving Averages. Use for trend analysis, buy/sell signals, momentum questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "6mo"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "Detects unusual price or volume activity using Z-score analysis. Use for unusual activity, volume spikes, suspicious movements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "6mo"}
                },
                "required": ["ticker"]
            }
        }
    }
]

# --- Tool Executor ---
def execute_tool(tool_name: str, tool_args: dict) -> str:
    console.print(f"  [bold yellow]⚙ Calling tool:[/bold yellow] [cyan]{tool_name}[/cyan] with {tool_args}")
    logging.info(f"Tool called: {tool_name} | Args: {tool_args}")

    try:
        if tool_name == "fetch_stock_data":
            result = fetch_stock_data(**tool_args)
        elif tool_name == "calculate_indicators":
            result = calculate_indicators(**tool_args)
        elif tool_name == "detect_anomalies":
            result = detect_anomalies(**tool_args)
        elif tool_name == "get_stock_news":
            result = get_stock_news(**tool_args)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        result = {"error": str(e)}
        logging.error(f"Tool error: {tool_name} | {str(e)}")

    return json.dumps(result, default=lambda x: str(x))


# --- Agent Brain ---
def run_agent(user_query: str, conversation_history: list) -> str:
    """
    ReAct agent loop with conversation memory and max iteration guard.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # System prompt
    system_message = {
        "role": "system",
        "content": """You are AlphaAgent — a professional autonomous stock market analyst AI.

You have access to real-time market data tools. Your job is to:
1. Always fetch real data — never guess or hallucinate numbers
2. Use multiple tools when needed for complete analysis
3. Provide clear, professional insights with actionable conclusions
4. Explain indicators in simple terms alongside technical details
5. Always state if a stock shows bullish or bearish signals clearly

Format your responses professionally with clear sections.
Be concise but thorough. Think like a senior equity analyst."""
    }

    # Build messages with full conversation history
    messages = [system_message] + conversation_history + [
        {"role": "user", "content": user_query}
    ]

    MAX_ITERATIONS = 5  # Prevent infinite loops
    iteration = 0

    console.print(f"\n  [bold green]🧠 Reasoning...[/bold green]")

    while iteration < MAX_ITERATIONS:
        iteration += 1
        logging.info(f"Agent iteration {iteration} for query: {user_query}")

        try:
            response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
    max_tokens=2000,
    parallel_tool_calls=False
)
        except Exception as e:
            logging.error(f"API error: {str(e)}")
            return f"I encountered an error connecting to the AI service: {str(e)}"

        message = response.choices[0].message

        # Agent wants to call tools
        if message.tool_calls:
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

            # Execute each tool
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_result = execute_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

        # Agent has final answer
        else:
            logging.info(f"Agent completed in {iteration} iterations")
            return message.content

    return "I reached the maximum number of analysis steps. Please try a more specific question."


# --- Interactive CLI ---
def main():
    console.print(Panel.fit(
        "[bold cyan]🤖 ALPHAAGENT[/bold cyan]\n"
        "[white]Autonomous Stock Market Intelligence Agent[/white]\n"
        "[dim]Powered by Groq LLM + Real-time Market Data[/dim]",
        border_style="cyan"
    ))

    console.print("\n[dim]Commands: 'exit' to quit | 'clear' to reset conversation[/dim]\n")

    conversation_history = []

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() == "exit":
                console.print("\n[dim]Goodbye! AlphaAgent shutting down.[/dim]")
                break

            if user_input.lower() == "clear":
                conversation_history = []
                console.print("[dim]Conversation cleared.[/dim]\n")
                continue

            # Run agent
            response = run_agent(user_input, conversation_history)

            # Display response
            console.print(Panel(
                response,
                title="[bold cyan]AlphaAgent[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            ))

            # Update conversation history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})

            # Keep history manageable
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logging.error(f"CLI error: {str(e)}")


if __name__ == "__main__":
    main()
import os
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def get_stock_news(ticker: str, company_name: str, num_articles: int = 10) -> dict:
    """
    Fetches latest news for a stock and performs LLM-based sentiment analysis.
    
    Args:
        ticker: Stock symbol e.g. 'TCS.NS'
        company_name: Full company name e.g. 'Tata Consultancy Services'
        num_articles: Number of articles to analyze (default 10)
    
    Returns:
        Dictionary with news articles and sentiment analysis
    """
    try:
        news_api_key = os.getenv("NEWS_API_KEY")
        
        if not news_api_key:
            return {"error": "NEWS_API_KEY not found in .env file"}

        # --- Fetch News ---
        # Clean company name for search (remove Ltd, Limited etc)
        search_query = company_name.replace(" Limited", "").replace(" Ltd", "").strip()
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": search_query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": num_articles,
            "apiKey": news_api_key
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("status") != "ok":
            return {"error": f"NewsAPI error: {data.get('message', 'Unknown error')}"}

        articles = data.get("articles", [])

        if not articles:
            return {"error": f"No news found for {company_name}"}

        # --- Prepare headlines for sentiment analysis ---
        headlines = []
        articles_data = []

        for article in articles[:num_articles]:
            title = article.get("title", "")
            description = article.get("description", "")
            published = article.get("publishedAt", "")
            source = article.get("source", {}).get("name", "")
            url_link = article.get("url", "")

            if title and title != "[Removed]":
                headlines.append(f"- {title}")
                articles_data.append({
                    "title": title,
                    "description": description,
                    "published_at": published,
                    "source": source,
                    "url": url_link
                })

        if not headlines:
            return {"error": "No valid headlines found"}

        # --- LLM Sentiment Analysis ---
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        sentiment_prompt = f"""Analyze the sentiment of these news headlines about {company_name} stock.

Headlines:
{chr(10).join(headlines)}

For each headline provide:
1. Sentiment: POSITIVE, NEGATIVE, or NEUTRAL
2. Impact: HIGH, MEDIUM, or LOW
3. One line reason

Then provide:
- Overall sentiment: BULLISH, BEARISH, or NEUTRAL
- Sentiment score: -1.0 (very bearish) to +1.0 (very bullish)
- Key insight: One sentence summary of what this news means for the stock

Format your response as structured text with clear sections."""

        sentiment_response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": sentiment_prompt}],
            max_tokens=1500
        )

        sentiment_analysis = sentiment_response.choices[0].message.content

        # --- Build Result ---
        result = {
            "ticker": ticker.upper(),
            "company_name": company_name,
            "articles_analyzed": len(articles_data),
            "latest_headlines": [a["title"] for a in articles_data[:5]],
            "sources": list(set([a["source"] for a in articles_data if a["source"]])),
            "sentiment_analysis": sentiment_analysis,
            "raw_articles": articles_data[:5]
        }

        return result

    except Exception as e:
        return {"error": str(e)}


# --- Test it ---
if __name__ == "__main__":
    from rich import print

    print("\n[bold cyan]Testing News Sentiment Analysis...[/bold cyan]\n")
    result = get_stock_news("TCS.NS", "Tata Consultancy Services")
    
    print(f"\n[bold]Ticker:[/bold] {result.get('ticker')}")
    print(f"[bold]Articles Analyzed:[/bold] {result.get('articles_analyzed')}")
    print(f"\n[bold]Latest Headlines:[/bold]")
    for h in result.get('latest_headlines', []):
        print(f"  • {h}")
    print(f"\n[bold]Sentiment Analysis:[/bold]")
    print(result.get('sentiment_analysis'))
# utils/db.py
import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "alphaagent"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )


def test_connection():
    try:
        conn = get_connection()
        conn.close()
        print("[DB] PostgreSQL connection successful ✓")
        return True
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        return False


def log_agent_interaction(ticker, user_query, agent_response, tools_used):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_logs (ticker, user_query, agent_response, tools_used, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (ticker, user_query, agent_response, tools_used, datetime.now())
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] Logging failed: {e}")
        return False


def cache_stock_data(ticker, period, data):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO stock_cache (ticker, period, data, cached_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ticker, period)
            DO UPDATE SET data = EXCLUDED.data, cached_at = EXCLUDED.cached_at
            """,
            (ticker.upper(), period, json.dumps(data), datetime.now())
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] Cache write failed: {e}")
        return False


def get_cached_stock_data(ticker, period, max_age_minutes=30):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "SELECT data, cached_at FROM stock_cache WHERE ticker = %s AND period = %s",
            (ticker.upper(), period)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row is None:
            return None

        age_minutes = (datetime.now() - row["cached_at"]).total_seconds() / 60
        if age_minutes <= max_age_minutes:
            print(f"[DB] Cache HIT for {ticker} ({age_minutes:.1f} min old)")
            data = row["data"]
            return data if isinstance(data, dict) else json.loads(data)
        else:
            print(f"[DB] Cache STALE for {ticker} ({age_minutes:.1f} min old)")
            return None
    except Exception as e:
        print(f"[DB] Cache read failed: {e}")
        return None


def get_recent_logs(limit=10):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "SELECT ticker, user_query, agent_response, tools_used, created_at FROM agent_logs ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB] Log fetch failed: {e}")
        return []
import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.db.database import get_connection

load_dotenv()
logger = logging.getLogger("copilot_agent")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"

GEMINI_TIMEOUT_SECONDS = 15
OUTPUT_TOKENS = 500  # English copilot responses — raise if you switch this to Urdu output


def get_full_context():
    """Pull latest risk scores + recommendations for all wards to give Gemini context.
    Intentionally city-wide (not scoped to one ward) — officers ask cross-ward comparative
    questions ("which ward is worst right now"), so this needs the full picture.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT rs.ward_id, w.ward_name, rs.flood_risk_score, rs.is_anomaly,
                   rs.anomaly_reason, rs.key_drivers
            FROM risk_scores rs
            JOIN wards w ON rs.ward_id = w.ward_id
            WHERE rs.id IN (SELECT MAX(id) FROM risk_scores GROUP BY ward_id)
            ORDER BY rs.flood_risk_score DESC
        """).fetchall()

        context_data = []
        for row in rows:
            # BUG FIX: previously this ran a redundant first query (joined on the wrong
            # column, ward_id vs risk_score_id) that was immediately overwritten below.
            # That was a wasted DB round-trip on every single ward, every single request.
            recs = conn.execute("""
                SELECT action_text, priority, hitl_status
                FROM recommendations
                WHERE ward_id = ?
                ORDER BY id DESC LIMIT 5
            """, (row["ward_id"],)).fetchall()

            context_data.append({
                "ward_id": row["ward_id"],
                "ward_name": row["ward_name"],
                "flood_risk_score": row["flood_risk_score"],
                "is_anomaly": bool(row["is_anomaly"]),
                "anomaly_reason": row["anomaly_reason"],
                "recommendations": [dict(r) for r in recs],
            })

        return context_data
    finally:
        conn.close()


def _generate(system_prompt: str, user_turn: str) -> str:
    """Blocking Gemini call — always run this through asyncio.to_thread from async code."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[system_prompt, user_turn],
        config=types.GenerateContentConfig(
            max_output_tokens=OUTPUT_TOKENS,
            temperature=0.3,
            # Same fix as advisory.py — see comment there. Without this, thinking
            # tokens eat into OUTPUT_TOKENS and officer-facing answers get cut short.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text


async def ask_copilot_async(user_query: str) -> str:
    """Async entrypoint — use this from FastAPI routes. Wraps the blocking SDK call
    in a thread and enforces a timeout so a hung Gemini request can't stall the
    event loop or exceed the Cloud Run request deadline."""
    context = get_full_context()

    system_prompt = f"""You are the APAC City Resilience Copilot, an AI assistant helping city
disaster-management officers make flood-risk decisions for Karachi.

You have access to the following LIVE risk data (JSON), sorted by risk score descending:

{json.dumps(context, indent=2)}

Rules:
- Answer ONLY using the data provided above. Do not invent numbers.
- Be concise and decision-focused — officers need fast, clear answers.
- When mentioning risk scores, round to 2 decimals.
- If asked about anomalies, explain WHY using the anomaly_reason field.
- If asked for recommendations, list them with priority level.
- Format lists clearly using short bullet points.
"""

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_generate, system_prompt, f"Officer's question: {user_query}"),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Copilot Gemini call timed out after %ss", GEMINI_TIMEOUT_SECONDS)
        return "Copilot is taking too long to respond right now. Please try again in a moment."
    except Exception as e:
        logger.error("Copilot Gemini call failed: %s", e)
        return "Copilot is temporarily unavailable. Please retry shortly."


def ask_copilot(user_query: str) -> str:
    """Sync wrapper — kept for CLI use only (see __main__ below). Do NOT call this
    from inside a FastAPI async route; it will block the event loop."""
    return asyncio.run(ask_copilot_async(user_query))


if __name__ == "__main__":
    print("APAC City Resilience Copilot — type 'exit' to quit\n")
    while True:
        query = input("Officer query: ")
        if query.lower() in ("exit", "quit"):
            break
        answer = ask_copilot(query)
        print(f"\nCopilot: {answer}\n")
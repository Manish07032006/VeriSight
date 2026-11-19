"""
Module 13 (optional): Reasoning & Internet Verification Layer.

Given a text submission and the verdicts already produced by the trained
fake-news and AI-text models, this module:
1. Optionally searches the web (Tavily) for current sources relevant
     to the claim, if TAVILY_API_KEY is configured (FR-26).
2. Asks a local Ollama model to write a short natural-language
     explanation, grounded in those search results when available
     (FR-24, FR-27 — supporting fact-checking verification).
3. Degrades gracefully if Ollama or the search call fails, returning
     the normal verdicts with a note that explanation/verification
     was unavailable rather than breaking the request (FR-29).

Scoped to the TEXT pipeline only (FR-28) — never called for media.
"""

import json
import os
import re
from dotenv import load_dotenv

# app.py imports this module BEFORE it calls load_dotenv(), so load the
# .env here too — otherwise the settings below would be read too early
# and ENABLE_REASONING would always be false.
load_dotenv()

try:
    import ollama
except ImportError:
    ollama = None  # ollama package not installed; explanations stay disabled

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None  # tavily-python not installed; search stays disabled

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
ENABLE_REASONING = os.environ.get("ENABLE_REASONING", "false").lower() == "true"

MAX_SEARCH_RESULTS = 3
MAX_TEXT_FOR_SEARCH = 300  # truncate long articles before using as a search query


def _search_web(claim_text: str):
    """
    Returns a list of {title, content, url} dicts, or None if search is
    unavailable/fails. Never raises — callers treat None as "no sources".
    """
    if not TAVILY_API_KEY or TavilyClient is None:
        return None

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        query = claim_text[:MAX_TEXT_FOR_SEARCH]
        response = client.search(query=query, max_results=MAX_SEARCH_RESULTS)
        results = response.get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "content": r.get("content", "")[:500],
                "url": r.get("url", ""),
            }
            for r in results
        ]
    except Exception as e:
        print(f"[reasoning] Web search failed: {e}")
        return None


def _build_prompt(
    text,
    fake_news_verdict,
    fake_news_confidence,
    ai_text_verdict,
    ai_text_confidence,
    search_results,
):
    prompt_parts = [
        "You are a strict, objective fact-checking engine.",
        "",
        "Verify whether the EXACT submitted claim is supported or contradicted by the web search results.",
        "",
        "RULES:",
        '1. Output ONLY a valid JSON object in this format: {"verdict": "fake" | "real", "confidence": 50.0 to 99.0, "explanation": "2-3 sentence explanation"}',
        '2. Check EVERY specific assertion in the claim (person, exact office/title, role, event, or fact). Do NOT mark a claim "real" just because the person, another official, or credible sources appear in the search results.',
        '3. If the search results show a DIFFERENT role/title or facts that contradict the claim (for example, claiming someone holds an office when results show they hold a different office), set "verdict": "fake" and state the contradiction clearly in "explanation".',
        '4. If search results only contain social media/unverified posts or lack credible evidence supporting the exact claim, set "verdict": "fake".',
        '5. Set "verdict": "real" ONLY when the search results directly confirm the exact claim as stated.',
        '6. Write "explanation" first so it clearly explains whether the exact claim is supported or contradicted, then make "verdict" match that conclusion. Keep "explanation" concise and under 3 sentences.',
        "",
        f'Submitted claim: "{text[:1000]}"',
        f"Baseline fake-news classifier: {fake_news_verdict} ({fake_news_confidence})",
        f"Baseline AI-text classifier: {ai_text_verdict} ({ai_text_confidence})",
    ]

    if search_results:
        prompt_parts.append("\nWEB SEARCH RESULTS:")
        for i, result in enumerate(search_results, 1):
            prompt_parts.append(
                f"{i}. Title: {result.get('title', '')}\n"
                f"Content: {result.get('content', '')}\n"
                f"URL: {result.get('url', '')}"
            )
    else:
        prompt_parts.append("\nNo web sources were available.")

    prompt_parts.append("\nOutput ONLY JSON:")
    return "\n".join(prompt_parts)


def _extract_json_payload(raw_content: str) -> dict:
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def get_explanation(text, fake_news_verdict, fake_news_confidence,
                    ai_text_verdict, ai_text_confidence):
    """
    Returns (explanation, sources_checked, final_verdict, final_confidence)
    """
    if not ENABLE_REASONING or ollama is None:
        return None, 0, fake_news_verdict, fake_news_confidence

    search_results = _search_web(text)
    sources_checked = len(search_results) if search_results else 0

    try:
        prompt = _build_prompt(
            text, fake_news_verdict, fake_news_confidence,
            ai_text_verdict, ai_text_confidence, search_results
        )

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )

        raw_content = response["message"]["content"].strip()
        data = _extract_json_payload(raw_content)

        explanation = str(data.get("explanation", "")).strip()
        rag_verdict = str(data.get("verdict", "")).strip().lower()

        try:
            parsed_conf = float(data.get("confidence", 90.0))
            if 0.0 <= parsed_conf <= 1.0:
                parsed_conf *= 100.0
            parsed_conf = round(max(0.0, min(100.0, parsed_conf)), 1)
        except (TypeError, ValueError):
            parsed_conf = 90.0

        print(f"[REASONING DEBUG] LLM Verdict: {rag_verdict} | Explanation: {explanation}")

        if rag_verdict in ("fake", "false", "contradicted"):
            return explanation, sources_checked, "fake", parsed_conf
        elif rag_verdict in ("real", "true", "verified"):
            return explanation, sources_checked, "real", parsed_conf
        else:
            return explanation, sources_checked, fake_news_verdict, fake_news_confidence

    except Exception as e:
        print(f"[reasoning] Fact check override failed: {e}")
        fallback = (
            f"Explanation unavailable (reasoning error). "
            f"Verdicts: {fake_news_verdict} fake-news check, "
            f"{ai_text_verdict} AI-text check."
        )
        return fallback, 0, fake_news_verdict, fake_news_confidence
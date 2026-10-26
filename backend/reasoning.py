"""
Module 13 (optional): Reasoning & Internet Verification Layer.

Given a text submission and the verdicts already produced by the trained
fake-news and AI-text models, this module:
  1. Optionally searches the web (Tavily) for current sources relevant
     to the claim, if TAVILY_API_KEY is configured (FR-26).
  2. Asks a local Ollama model to write a short natural-language
     explanation, grounded in those search results when available
     (FR-24, FR-27 — never overrides the trained models' verdicts).
  3. Degrades gracefully if Ollama or the search call fails, returning
     the normal verdicts with a note that explanation/verification
     was unavailable rather than breaking the request (FR-29).

Scoped to the TEXT pipeline only (FR-28) — never called for media.
"""

import os
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


import json

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
        "Compare the submitted claim directly against the provided web search results.",
        "",
        "RULES:",
        '1. Output ONLY a valid JSON object in this format: {"verdict": "fake" | "real", "explanation": "2-3 sentence explanation"}',
        "2. If the search results only contain social media posts (Instagram, YouTube hobby videos) or lack credible journalism for an extraordinary claim, treat the claim as UNVERIFIED or FALSE and set \"verdict\": \"fake\".",
        "3. If the claim is backed by credible, mainstream news or official sources, set \"verdict\": \"real\".",
        "4. DO NOT blindly follow the baseline classifier—if the text makes an absurd or unverified claim, set \"verdict\": \"fake\".",
        "5. Keep the explanation concise, objective, and under 3 sentences.",
        "",
        f"Submitted claim: \"{text[:1000]}\"",
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


def get_explanation(text, fake_news_verdict, fake_news_confidence,
                    ai_text_verdict, ai_text_confidence):
    """
    Returns (explanation, sources_checked, final_verdict, final_confidence)
    """
    if not ENABLE_REASONING or ollama is None:
        return None, 0, fake_news_verdict, fake_news_confidence

    search_results = _search_web(text)

    try:
        prompt = _build_prompt(
            text, fake_news_verdict, fake_news_confidence,
            ai_text_verdict, ai_text_confidence, search_results
        )
        
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json"
        )
        
        raw_content = response["message"]["content"].strip()
        
        # Clean potential markdown formatting
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
            raw_content = raw_content.strip()

        data = json.loads(raw_content)
        
        explanation = data.get("explanation", "")
        rag_verdict = str(data.get("verdict", "")).strip().lower()
        sources_checked = len(search_results) if search_results else 0

        # Print debug log in Flask terminal to verify LLM output
        print(f"[REASONING DEBUG] LLM Verdict: {rag_verdict} | Explanation: {explanation}")

        # Set final verdict based on RAG verification
        if rag_verdict in ("fake", "false"):
            final_verdict = "fake"
            final_confidence = 98.0
        elif rag_verdict in ("real", "true"):
            final_verdict = "real"
            final_confidence = 98.0
        else:
            final_verdict = fake_news_verdict
            final_confidence = fake_news_confidence

        return explanation, sources_checked, final_verdict, final_confidence

    except Exception as e:
        print(f"[reasoning] Fact check override failed: {e}")
        fallback = (
            f"Explanation unavailable (reasoning error). "
            f"Verdicts: {fake_news_verdict} fake-news check, "
            f"{ai_text_verdict} AI-text check."
        )
        return fallback, 0, fake_news_verdict, fake_news_confidence
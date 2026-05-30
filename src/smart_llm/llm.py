"""Lightweight LLM Client for Gemini & OpenAI with zero-token fallback support."""

from __future__ import annotations

import os
import sys

def detect_llm_provider() -> dict[str, str | None]:
    """Detect available LLM providers based on environment variables."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if gemini_key:
        return {"provider": "gemini", "model": "gemini-2.5-flash"}
    elif openai_key:
        return {"provider": "openai", "model": "gpt-4o-mini"}
        
    return {"provider": None, "model": None}

def call_llm(prompt: str, user_content: str) -> str | None:
    """Call the active LLM provider, returning None if no API keys are set."""
    provider_info = detect_llm_provider()
    provider = provider_info["provider"]
    model = provider_info["model"]
    
    if not provider:
        return None

    try:
        if provider == "gemini":
            # Attempt to use google-genai (2025/2026 SDK)
            try:
                from google import genai
                client = genai.Client()
                response = client.models.generate_content(
                    model=model,
                    contents=f"{prompt}\n\nContent:\n{user_content}"
                )
                return response.text
            except (ImportError, Exception):
                # Fallback to legacy import if google-genai is not available
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                    legacy_model = legacy_genai.GenerativeModel("gemini-1.5-flash")
                    response = legacy_model.generate_content(f"{prompt}\n\nContent:\n{user_content}")
                    return response.text
                except Exception as e:
                    print(f"Warning: Gemini API call failed: {e}", file=sys.stderr)
                    return None
                    
        elif provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_content}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Warning: OpenAI API call failed: {e}", file=sys.stderr)
                return None
                
    except Exception as e:
        print(f"Warning: LLM call encountered an unexpected error: {e}", file=sys.stderr)
        return None
        
    return None

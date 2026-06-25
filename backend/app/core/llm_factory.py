"""
LLM Provider Factory
====================
Supports: Anthropic (paid) · Ollama (free, local) · Groq (free API) · Gemini (free API)

Set LLM_PROVIDER in .env.local:
  LLM_PROVIDER=ollama          # free, runs on your PC
  LLM_PROVIDER=groq            # free API, very fast
  LLM_PROVIDER=gemini          # free API, good quality
  LLM_PROVIDER=anthropic       # paid, best quality + prompt caching (60-90% token savings)

Note: Claude Opus 4.x and Sonnet 4.x do NOT accept the temperature parameter.
      Temperature is stripped automatically for Anthropic models.
"""
from __future__ import annotations
import os
from typing import Any, Dict, List

# ── Provider / model defaults ────────────────────────────────────────────────

PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()

MODELS = {
    "anthropic": {
        "writing": os.environ.get("CLAUDE_WRITING_MODEL", "claude-opus-4-7"),
        "fast":    os.environ.get("CLAUDE_FAST_MODEL",    "claude-sonnet-4-6"),
    },
    "ollama": {
        "writing": os.environ.get("OLLAMA_WRITING_MODEL", "llama3.1:8b"),
        "fast":    os.environ.get("OLLAMA_FAST_MODEL",    "llama3.1:8b"),
    },
    "groq": {
        "writing": os.environ.get("GROQ_WRITING_MODEL", "llama-3.3-70b-versatile"),
        "fast":    os.environ.get("GROQ_FAST_MODEL",    "llama-3.1-8b-instant"),
    },
    "gemini": {
        "writing": os.environ.get("GEMINI_WRITING_MODEL", "gemini-1.5-pro"),
        "fast":    os.environ.get("GEMINI_FAST_MODEL",    "gemini-1.5-flash"),
    },
}


def get_llm(role: str = "fast", max_tokens: int = 4096, temperature: float = 0.3):
    provider = PROVIDER
    model    = MODELS.get(provider, MODELS["anthropic"])[role]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        # Claude 4.x models deprecated temperature — do not pass it
        return ChatAnthropic(
            model=model,
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            max_tokens=max_tokens,
        )

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            num_predict=max_tokens,
            temperature=temperature,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model,
            api_key=os.environ.get("GROQ_API_KEY", ""),
            max_tokens=max_tokens,
            temperature=temperature,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.environ.get("GEMINI_API_KEY", ""),
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def get_writing_llm(max_tokens: int = 8000):
    return get_llm("writing", max_tokens=max_tokens, temperature=0.3)


def get_fast_llm(max_tokens: int = 4096):
    return get_llm("fast", max_tokens=max_tokens, temperature=0.1)


def get_precise_llm(max_tokens: int = 4096):
    return get_llm("fast", max_tokens=max_tokens, temperature=0.0)


def provider_name() -> str:
    return PROVIDER.upper()


def is_vision_capable() -> bool:
    return PROVIDER in ("anthropic", "gemini")


# ── Prompt Caching Helpers (Anthropic only) ──────────────────────────────────

def make_cached_system(system_text: str) -> List[Dict[str, Any]]:
    """Wrap system prompt with Anthropic cache_control for 90% token discount on hits."""
    if PROVIDER != "anthropic":
        return system_text  # type: ignore[return-value]
    return [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]


def get_cached_writing_llm(max_tokens: int = 8000):
    """Writing LLM with prompt caching header (Anthropic only). No temperature — deprecated."""
    if PROVIDER != "anthropic":
        return get_writing_llm(max_tokens)
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=MODELS["anthropic"]["writing"],
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        max_tokens=max_tokens,
        model_kwargs={"extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}},
    )


def get_cached_fast_llm(max_tokens: int = 4096):
    """Fast LLM with prompt caching header (Anthropic only). No temperature — deprecated."""
    if PROVIDER != "anthropic":
        return get_fast_llm(max_tokens)
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=MODELS["anthropic"]["fast"],
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        max_tokens=max_tokens,
        model_kwargs={"extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}},
    )

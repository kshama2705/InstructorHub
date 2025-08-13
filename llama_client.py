# llama_client.py
import os
from typing import List, Dict

# pip install openai >= 1.0.0
from openai import OpenAI


class LlamaClientError(RuntimeError):
    pass


def chat_llama(messages: List[Dict], model: str = None, base_url: str = None,
               api_key: str = None, temperature: float = 0.0) -> str:
    """
    Uses an OpenAI-compatible Chat Completions endpoint serving LLaMA.
    Env:
      LLAMA_API_KEY=...
      LLAMA_API_BASE=https://<your-llama-endpoint>   (no trailing slash)
      LLAMA_MODEL=llama3.1-8b-instruct               (or whatever your server exposes)
    """
    api_key = api_key or os.getenv("LLAMA_API_KEY")
    base_url = base_url or os.getenv("LLAMA_API_BASE")
    model = model or os.getenv("LLAMA_MODEL", "Llama-4-Maverick-17B-128E-Instruct-FP8")

    if not api_key:
        raise LlamaClientError("Missing LLAMA_API_KEY")
    if not base_url:
        raise LlamaClientError("Missing LLAMA_API_BASE")

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

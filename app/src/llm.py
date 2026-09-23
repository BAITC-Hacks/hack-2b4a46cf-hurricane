"""OpenAI calls. Every call has a timeout and raises UpstreamError on failure."""

from openai import APIError, APITimeoutError, AsyncOpenAI

from src.config import settings
from src.errors import UpstreamError

client = AsyncOpenAI(api_key=settings.openai_api_key or "missing", timeout=30)


async def ask_llm(prompt: str, system: str = "You are a helpful assistant.") -> str:
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
    except (APITimeoutError, APIError) as error:
        raise UpstreamError("LLM is unavailable, try again") from error
    return response.choices[0].message.content or ""

"""OpenAI calls. Every call has a timeout and raises UpstreamError on failure."""

import json

from openai import APIError, APITimeoutError, AsyncOpenAI

from src.config import settings
from src.errors import UpstreamError

# The LLM call has its own limit; database and application work add to total latency.
client = AsyncOpenAI(api_key=settings.openai_api_key or "missing", timeout=8, max_retries=0)


async def fetch_llm_json(system: str, prompt: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            seed=7,
            # The model only selects from verified fact IDs.
            reasoning_effort="none",
        )
    except (APITimeoutError, APIError) as error:
        raise UpstreamError(f"LLM is unavailable: {type(error).__name__}") from error
    try:
        return json.loads(response.choices[0].message.content or "{}")
    except (json.JSONDecodeError, AttributeError, IndexError, TypeError) as error:
        raise UpstreamError("LLM returned an invalid response") from error

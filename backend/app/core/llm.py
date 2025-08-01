import openai, asyncio
from .config import settings

openai.api_key = settings.openai_api_key

async def chat_stream(messages: list[dict], **kwargs):
    """
    Async generator yielding delta tokens; wraps OpenAI streaming call.
    """
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
        **kwargs,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta.get("content", "")
        if delta:
            yield delta

import json, asyncio
from .llm import chat_stream

SYSTEM_MSG = {
    "role": "system",
    "content": (
        "You are an AI product manager. "
        "For any missing fields, ask the user ONE clear question at a time. "
        "Return JSON: {\"question\": \"...\", \"field\": \"placeholder\"}"
    ),
}

async def ask_missing_fields(known: dict, missing: list[str]):
    if not missing:
        return None
    user_msg = {
        "role": "user",
        "content": json.dumps({"known": known, "missing": missing}),
    }
    async for delta in chat_stream([SYSTEM_MSG, user_msg], temperature=0):
        yield delta

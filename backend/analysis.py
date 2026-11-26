"""Read-only, grounded chart analysis via the OpenAI tool-calling API."""
import json
import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

TOOLS = [{
    "type": "function",
    "function": {
        "name": "read_chart_snapshot",
        "description": "Read the selected market's candles, indicators and timestamps.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
}]


async def analyze_chart(read_snapshot):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "OpenAI API key not configured")
    messages = [
        {"role": "system", "content": "Summarize chart observations in Korean. Cite concrete prices or indicators "
         "and the timestamp from the read-only tool. State uncertainty and avoid trade instructions."},
        {"role": "user", "content": "Analyze the selected chart."},
    ]
    evidence = {}

    async with httpx.AsyncClient(timeout=30) as client:
        async def complete(tool_choice):
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "messages": messages,
                      "tools": TOOLS, "tool_choice": tool_choice},
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            return {name: message[name] for name in ("role", "content", "tool_calls") if message.get(name) is not None}

        try:
            call_message = await complete({"type": "function", "function": {"name": "read_chart_snapshot"}})
            calls = call_message["tool_calls"]
            if len(calls) != 1 or calls[0]["function"]["name"] != "read_chart_snapshot":
                raise ValueError("Unexpected tool call")
            snapshot = await read_snapshot()
            rows = snapshot["candles"]
            if not rows:
                raise HTTPException(404, "No candles available for analysis")
            evidence = {name: snapshot[name] for name in ("market", "symbol", "interval", "session", "venue", "currency")}
            evidence.update(data_time=datetime.fromtimestamp(rows[-1]["time"], timezone.utc).isoformat(),
                            last_candle=rows[-1],
                            indicators={name: values[-1:] if name != "fibonacci" else values
                                        for name, values in snapshot["indicators"].items()})
            messages.extend([call_message, {"role": "tool", "tool_call_id": calls[0]["id"],
                                            "content": json.dumps({**evidence, "recent_candles": rows[-10:]})}])
            summary = (await complete("none"))["content"]
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("Empty analysis")
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(502, "Analysis provider unavailable") from exc
    return {"summary": summary, "evidence": evidence}

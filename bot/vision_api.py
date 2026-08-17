"""Optional vision LLM for TAB scoreboards. Portrait matching stays the fallback."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

PROMPT = """This is an Overwatch 2 TAB/scoreboard screenshot (UI may be Japanese).
Return ONLY JSON:
{"map":"english map name or key","self":"hero key of highlighted/own row or null","allies":["hero-key",...],"enemies":["hero-key",...],"side":"attack|defend|unknown"}
Rules:
- Allies are the TOP (blue) table. Enemies are the BOTTOM (red) table. Always 5 and 5 in role queue.
- Use hyphen keys: wrecking-ball, soldier-76, dva, kiriko, juno, emre, mizuki, hazard, route-66.
- Juno (teal/purple visor, yellow accents) is not Wuyang (orange face). Emre is not Hazard.
- Same hero may appear on both teams. Keep both. Do not drop names to unique-only.
- Ignore player nicknames. Read circular portraits.
- map from header (e.g. ROUTE 66, ルート66, エスコート).
"""


def _hero_key(raw: str, keys: set[str]) -> str | None:
    k = (raw or "").strip().lower().replace(" ", "-").replace("_", "-")
    k = k.replace("d.va", "dva").replace("d.mon", "dmon")
    if k in keys:
        return k
    for cand in keys:
        if cand.replace("-", "") == k.replace("-", ""):
            return cand
    return None


def read_with_api(image_bytes: bytes) -> dict | None:
    token = (
        os.getenv("VISION_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    if not token:
        return None
    base = (os.getenv("VISION_API_BASE") or "https://api.openai.com/v1").rstrip("/")
    if "deepseek.com" in base:
        # Official DeepSeek chat API cannot see pixels. Keep portrait matching.
        return None
    model = os.getenv("VISION_MODEL") or "gpt-4o-mini"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
                    },
                ],
            }
        ],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "counterwatch",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None
    try:
        text = body["choices"][0]["message"]["content"]
        parsed = json.loads(text)
    except Exception:
        return None
    from bot.engine import HEROES, parse_text

    keys = set(HEROES)
    allies = []
    for x in parsed.get("allies") or []:
        k = _hero_key(str(x), keys)
        if k and k not in allies:
            allies.append(k)
    enemies = []
    for x in parsed.get("enemies") or []:
        k = _hero_key(str(x), keys)
        if k:
            enemies.append(k)
        if len(enemies) >= 5:
            break
    self_key = _hero_key(str(parsed.get("self") or ""), keys)
    if self_key and self_key not in allies:
        allies = [self_key, *[a for a in allies if a != self_key]][:5]
    map_info = parse_text(str(parsed.get("map") or ""))
    side = parsed.get("side") if parsed.get("side") in ("attack", "defend") else None
    if len(enemies) < 4:
        return None
    role = HEROES[self_key]["role"] if self_key in HEROES else None
    return {
        "allies": allies[:5],
        "enemies": enemies[:5],
        "self_key": self_key,
        "role": role,
        "map_key": map_info.get("map_key"),
        "side": side,
        "layout": "api",
        "ocr_text": "",
        "hits": [],
    }

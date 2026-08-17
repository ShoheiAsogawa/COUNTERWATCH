"""DeepSeek text coach. Official API is text-only — no screenshot pixels."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

ROOT_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_API_BASE",
    "DEEPSEEK_MODEL",
)


def _cfg() -> tuple[str, str, str] | None:
    token = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not token:
        return None
    base = (os.getenv("DEEPSEEK_API_BASE") or "https://api.deepseek.com").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    model = os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash"
    return token, base, model


def chat(messages: list[dict], *, max_tokens: int = 900, temperature: float = 0.3) -> str | None:
    cfg = _cfg()
    if not cfg:
        return None
    token, base, model = cfg
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "thinking": {"type": "disabled"},
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
        with urllib.request.urlopen(req, timeout=28) as resp:
            body = json.loads(resp.read().decode())
        msg = (body.get("choices") or [{}])[0].get("message") or {}
        text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        return text or None
    except urllib.error.HTTPError as exc:
        err = exc.read()[:300].decode("utf-8", "replace")
        print(f"[deepseek] http {exc.code} {err}")
        return None
    except Exception as exc:
        print(f"[deepseek] fail {type(exc).__name__}")
        return None


def polish_fight_plan(plan: dict, state: dict) -> str | None:
    """Turn the structured plan into a specific Japanese fight script."""
    if not _cfg() or not plan.get("hero"):
        return None
    hero = plan["hero"]
    facts = {
        "you": hero.get("nameJa") or hero.get("name"),
        "role": hero.get("role"),
        "map": plan.get("title"),
        "side": state.get("side") or "flex",
        "stand": plan.get("where"),
        "stations": plan.get("stations"),
        "combo": plan.get("combo"),
        "threats": plan.get("threats"),
        "kit": plan.get("play"),
        "lose": plan.get("lose"),
        "enemies": state.get("enemies") or [],
        "allies": state.get("allies") or [],
    }
    text = chat(
        [
            {
                "role": "system",
                "content": (
                    "あなたはOverwatch 2のコーチ。与えた事実だけを使う。"
                    "無い地点名・クールタイム・ヒーローを作らない。"
                    "日本語。Discord向けMarkdown。"
                    "見出しは **今いる場所** / **最初のファイト** / **地点** / **敵への返し** / **これをやると負ける**。"
                    "各見出しの下は2〜4文。具体的に『どこから・何を残して・誰を先に切るか』。"
                    "全体800文字以内。"
                ),
            },
            {
                "role": "user",
                "content": "事実JSON:\n" + json.dumps(facts, ensure_ascii=False),
            },
        ],
        max_tokens=900,
        temperature=0.25,
    )
    if not text:
        return None
    return text[:4096]

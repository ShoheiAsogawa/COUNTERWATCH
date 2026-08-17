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
        "hero": hero.get("nameJa") or hero.get("name"),
        "role": hero.get("role"),
        "map": plan.get("title"),
        "side": state.get("side") or "flex",
        "stand": plan.get("where"),
        "stations": plan.get("stations"),
        "combo": plan.get("combo"),
        "threats": plan.get("threats"),
        "lose": plan.get("lose"),
        "enemies": state.get("enemies") or [],
        "allies": state.get("allies") or [],
    }
    text = chat(
        [
            {
                "role": "system",
                "content": (
                    "Overwatch 2の助言を、友達に話すような普通の日本語で書く。"
                    "与えた事実だけを使う。無い地名・スキル・ヒーローを作らない。"
                    "『あなた』『自分』は書かない。誰が今そのヒーローか、とは書かない。"
                    "見出しはこれだけ: **どこに立つか** / **最初にやること** / **敵の対処** / **やってはいけないこと**。"
                    "各見出しは2〜3文。中学生でもわかる言葉。"
                    "スキル名を出すときは、カッコで何をするか書く。例: 鈴（数秒無敵になる）。"
                    "使わない言葉: 本線、クリーンセ、パイル、オフアングル、ポーク、CC、TP、ブロウル、バンカー、タイダル。"
                    "全体600文字以内。Discord向けMarkdown。"
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

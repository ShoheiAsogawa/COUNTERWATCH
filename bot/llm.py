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


def chat(messages: list[dict], *, max_tokens: int = 1100, temperature: float = 0.35) -> str | None:
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


SYSTEM = (
    "Overwatch 2の助言を書く。友達に話すような普通の日本語。"
    "仕事は、与えた要素を同時に見て一つの立ち回りにまとめること。"
    "マップの地形、敵5人の組み合わせ、味方の編成、出すヒーロー、見るべきスキルをバラバラに並べない。"
    "交差点を書く。例:『ジュノの黄色い輪が見えたらボールとゲンジが同時に来る。ルート66ならカフェの中で待つ』。"
    "hints は参考資料。上から書き写さない。矛盾したら敵の組み合わせとマップを優先する。"
    "事実JSONに無い地名・スキル・ヒーローを作らない。"
    "enemy_style 以外の構成名を付けない。敵5人を『空5』『飛び込み5』などへ言い換えない。名前で呼ぶ。"
    "pick のスキルは、この敵の組に実際に当たるときだけ書く。飛ばない相手を鎖で落とす、など食い違いは禁止。"
    "hints.combos にある同時技を、立ち回りの中心にする。"
    "『あなた』『自分』は書かない。誰が今そのヒーローか、とは書かない。"
    "見出しはこれだけ:"
    " 出すなら **ヒーロー名**。（この敵の組×このマップで、なぜそのヒーローか1文）"
    " **どこに立つか**"
    " **最初にやること**"
    " **敵の対処**（1人ずつのTipsではなく、5人の組への返し。見るスキルはここに織り込む）"
    " **やってはいけないこと**"
    "スキル名を出すときはカッコで何をするか書く。例: 鈴（数秒無敵になる）。"
    "使わない言葉: 本線、クリーンセ、パイル、オフアングル、ポーク、CC、TP、ブロウル、バンカー、タイダル。"
    "全体800文字以内。Discord向けMarkdown。"
)


def compose_advice(plan: dict, rec: dict, state: dict) -> str | None:
    """Judge map × enemy combo × allies × pick together. None if no API key."""
    if not _cfg() or not plan.get("hero"):
        return None
    from bot.tactics import advice_context  # local import: avoid cycle at module load

    facts = advice_context(plan, rec, state)
    enemy_names = "、".join(e["name"] for e in facts.get("enemies") or [])
    ally_names = "、".join(a["name"] for a in facts.get("allies") or []) or "不明"
    pick_name = (facts.get("pick") or {}).get("name") or ""
    map_name = (facts.get("map") or {}).get("name") or ""
    side = (facts.get("map") or {}).get("side") or ""
    user = (
        f"マップ: {map_name}（{side}）\n"
        f"敵5人: {enemy_names}\n"
        f"味方: {ally_names}\n"
        f"出すヒーロー: {pick_name}\n"
        "上の4つを同時に見て立ち回りを書いて。"
        "敵を別の構成名（空5など）にまとめない。『唯一』は使わない。\n"
        "詳細JSON:\n"
        + json.dumps(facts, ensure_ascii=False)
    )
    text = chat(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=1100,
        temperature=0.25,
    )
    if not text:
        return None
    return text[:4096]


def polish_fight_plan(plan: dict, rec: dict | None = None, state: dict | None = None) -> str | None:
    """Back-compat wrapper. Prefer compose_advice."""
    rec = rec or {}
    state = state or {}
    return compose_advice(plan, rec, state)

#!/usr/bin/env python3
"""Discord reply must be ordinary Japanese, with no self-identification."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.bot import build_reply  # noqa: E402
from bot.tactics import fight_plan, plan_embed_body  # noqa: E402

os.environ.pop("DEEPSEEK_API_KEY", None)


def _embed_text(embed) -> str:
    parts = [embed.title or "", embed.description or ""]
    for field in embed.fields:
        parts.append(field.name or "")
        parts.append(field.value or "")
    parts.append(embed.footer.text if embed.footer else "")
    return "\n".join(parts)


def main() -> None:
    plan = fight_plan(
        "kiriko",
        "route-66",
        "attack",
        ["wrecking-ball", "genji", "ashe", "mercy", "juno"],
    )
    assert "カフェ" in plan["where"]
    assert "ボール" in plan["combo"]
    body = plan_embed_body(plan)
    assert "どこに立つか" in body
    assert "やってはいけないこと" in body
    assert "自分のキット" not in body
    assert "今いる場所" not in body

    main, extras, _files = build_reply(
        {
            "role": "support",
            "side": "attack",
            "map_key": "route-66",
            "enemies": ["wrecking-ball", "genji", "ashe", "mercy", "juno"],
            "allies": ["sigma", "emre", "ashe", "ana", "mizuki"],
            "self_key": "wuyang",
        }
    )
    text = _embed_text(main) + "\n" + "\n".join(_embed_text(e) for e in extras)
    assert "自分" not in text, text
    assert "あなたは" not in text, text
    assert "スクショ読み" not in text
    assert "こう戦え" not in text
    assert "乗り換え候補" not in text
    assert "数えるクールタイム" not in text
    assert "立ち回り" in text
    assert "これだけ見とけ" in text
    assert "出すなら" in text
    assert "CC" not in extras[0].description
    assert "ダイブ" not in extras[0].description
    assert "本線" not in extras[0].description
    assert "クリーンセ" not in extras[0].description
    print("reply ok")
    print(extras[0].description[:280] if extras else "(no extras)")


if __name__ == "__main__":
    main()

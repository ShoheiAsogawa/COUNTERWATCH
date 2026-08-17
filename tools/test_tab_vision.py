#!/usr/bin/env python3
"""Generate a JP TAB-style scoreboard fixture and check vision."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.vision import read_scoreboard, render_tab_fixture


def main() -> int:
    allies = ["sigma", "mauga", "ashe", "ana", "kiriko"]
    enemies = ["wrecking-ball", "genji", "ashe", "mercy", "juno"]
    img = render_tab_fixture(allies, enemies, map_title="ROUTE 66", self_key="kiriko")
    out = ROOT / "assets" / "sample-tab-scoreboard.jpg"
    img.convert("RGB").save(out, quality=92)
    print("wrote", out, img.size)

    import io

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    result = read_scoreboard(buf.getvalue())
    print("layout", result["layout"])
    print("allies ", result["allies"])
    print("enemies", result["enemies"])
    print("self   ", result["self_key"], result["role"])
    print("map    ", result["map_key"])
    print("ocr    ", (result["ocr_text"] or "")[:200])
    print("hits   ", [(h["key"], round(h["score"], 3), h["team"], int(h["cy"])) for h in result["hits"]])

    ok = True
    if sorted(result["enemies"]) != sorted(enemies):
        print("FAIL enemies", result["enemies"], "expected", enemies)
        ok = False
    if "kiriko" not in result["allies"] and result["self_key"] != "kiriko":
        print("FAIL did not see kiriko on ally/self")
        ok = False
    if result["role"] not in (None, "support"):
        print("FAIL role", result["role"])
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

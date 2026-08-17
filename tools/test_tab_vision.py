#!/usr/bin/env python3
"""Generate a JP TAB-style scoreboard fixture and check vision."""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.vision import (  # noqa: E402
    _feat_from_image,
    _force_confusions,
    _pick_key,
    _templates,
    read_scoreboard,
    render_tab_fixture,
)
from PIL import Image  # noqa: E402


def _jpeg_bytes(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _run(
    allies: list[str],
    enemies: list[str],
    self_key: str,
    label: str,
    *,
    realistic: bool = False,
    discord: bool = False,
    hud: bool = False,
) -> dict:
    img = render_tab_fixture(
        allies, enemies, map_title="ROUTE 66", self_key=self_key, realistic=realistic, hud=hud
    )
    if discord:
        img = img.convert("RGB").resize((1280, 720), Image.Resampling.BILINEAR)
        data = _jpeg_bytes(img, quality=48)
    else:
        data = _jpeg_bytes(img)
    result = read_scoreboard(data)
    print(f"--- {label} ---")
    print("layout", result["layout"])
    print("allies ", result["allies"])
    print("enemies", result["enemies"])
    print("self   ", result["self_key"], result["role"])
    print("hits   ", [(h["key"], round(h["score"], 3), h["team"], int(h["cy"])) for h in result["hits"]])
    return result


def _expect(result: dict, allies: list[str], enemies: list[str], self_key: str) -> list[str]:
    fails: list[str] = []
    if result["allies"] != allies:
        fails.append(f"allies {result['allies']} != {allies}")
    if result["enemies"] != enemies:
        fails.append(f"enemies {result['enemies']} != {enemies}")
    if result["self_key"] != self_key:
        fails.append(f"self {result['self_key']} != {self_key}")
    return fails


def _confusion_unit_tests() -> list[str]:
    fails: list[str] = []
    keys, mat, colors, csigs, roles = _templates()
    portraits = ROOT / "assets" / "heroes"

    def match(name: str, prefer: str | None) -> str:
        img = Image.open(portraits / f"{name}.png").convert("RGB")
        feat, col, csig = _feat_from_image(img)
        scores = mat @ feat
        idx, score, _second = _pick_key(scores, col, csig, keys, colors, csigs, roles, prefer)
        return _force_confusions(keys[idx], csig, prefer, scores, keys)

    if match("emre", "damage") != "emre":
        fails.append("emre portrait in damage slot was not read as emre")
    if match("mauga", "tank") != "mauga":
        fails.append("mauga portrait in tank slot was not read as mauga")
    if match("mizuki", "support") != "mizuki":
        fails.append("mizuki portrait in support slot was not read as mizuki")
    if match("wuyang", "support") != "wuyang":
        fails.append("wuyang portrait in support slot was not read as wuyang")
    wuyang = Image.open(portraits / "wuyang.png").convert("RGB")
    _, _, wuyang_csig = _feat_from_image(wuyang)
    if _force_confusions("mizuki", wuyang_csig, "support") != "wuyang":
        fails.append(f"wuyang color did not override mizuki: {wuyang_csig}")

    mizuki = Image.open(portraits / "mizuki.png").convert("RGB")
    _, _, mizuki_csig = _feat_from_image(mizuki)
    if _force_confusions("kiriko", mizuki_csig, "support") != "mizuki":
        fails.append(f"mizuki color did not override kiriko: {mizuki_csig}")
    kiriko = Image.open(portraits / "kiriko.png").convert("RGB")
    _, _, kiriko_csig = _feat_from_image(kiriko)
    if _force_confusions("mizuki", kiriko_csig, "support") != "kiriko":
        fails.append(f"kiriko color did not override mizuki: {kiriko_csig}")
    return fails


def main() -> int:
    fails: list[str] = []
    enemies = ["wrecking-ball", "genji", "ashe", "mercy", "juno"]

    # Real role-queue TAB: DPS 2 is Emre (not Mauga), support 2 is Mizuki (not Kiriko).
    allies = ["sigma", "emre", "ashe", "ana", "mizuki"]
    img = render_tab_fixture(allies, enemies, map_title="ROUTE 66", self_key="mizuki")
    out = ROOT / "assets" / "sample-tab-scoreboard.jpg"
    img.convert("RGB").save(out, quality=92)
    print("wrote", out, img.size)
    result = _run(allies, enemies, "mizuki", "role-queue emre/mizuki")
    fails.extend(_expect(result, allies, enemies, "mizuki"))
    if result["role"] not in (None, "support"):
        fails.append(f"role {result['role']}")

    # Tank-slot Mauga must stay Mauga (do not rewrite every Mauga to Emre).
    tank_allies = ["mauga", "ashe", "cassidy", "ana", "kiriko"]
    tank_enemies = ["sigma", "genji", "sojourn", "mercy", "juno"]
    tank = _run(tank_allies, tank_enemies, "kiriko", "tank-slot mauga")
    fails.extend(_expect(tank, tank_allies, tank_enemies, "kiriko"))

    # Real TAB is a semi-transparent overlay on the map, then Discord JPEG-crushes it.
    real = _run(allies, enemies, "mizuki", "realistic transparent TAB", realistic=True)
    fails.extend(_expect(real, allies, enemies, "mizuki"))
    crushed = _run(
        allies, enemies, "mizuki", "discord jpeg overlay", realistic=True, discord=True
    )
    if crushed["allies"] != allies:
        fails.append(f"discord allies {crushed['allies']} != {allies}")
    if crushed["enemies"] != enemies:
        fails.append(f"discord enemies {crushed['enemies']} != {enemies}")
    if "emre" not in crushed["allies"] or "mizuki" not in crushed["allies"]:
        fails.append("discord jpeg lost emre/mizuki")

    hud = _run(allies, enemies, "mizuki", "full-screen HUD TAB", realistic=True, hud=True)
    fails.extend(_expect(hud, allies, enemies, "mizuki"))
    if hud["self_key"] == "wuyang":
        fails.append("HUD portrait stole self as wuyang")

    fails.extend(_confusion_unit_tests())

    if fails:
        print("FAIL")
        for line in fails:
            print(" -", line)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

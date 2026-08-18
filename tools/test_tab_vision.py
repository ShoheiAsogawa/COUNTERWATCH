#!/usr/bin/env python3
"""Generate a JP TAB-style scoreboard fixture and check vision."""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.vision import (  # noqa: E402
    _color_sig,
    _feat_from_arr,
    _feat_from_image,
    _force_confusions,
    _inner_mean,
    _pick_key,
    _templates,
    read_scoreboard,
    render_tab_fixture,
)
from PIL import Image, ImageDraw  # noqa: E402
import numpy as np  # noqa: E402


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
    interior: bool = False,
) -> dict:
    img = render_tab_fixture(
        allies,
        enemies,
        map_title="ROUTE 66",
        self_key=self_key,
        realistic=realistic,
        hud=hud,
        interior=interior,
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
    if match("juno", "support") != "juno":
        fails.append("juno portrait in support slot was not read as juno")
    juno = Image.open(portraits / "juno.png").convert("RGB")
    _, _, juno_csig = _feat_from_image(juno)
    if _force_confusions("wuyang", juno_csig, "support") != "juno":
        fails.append(f"juno color did not override wuyang: {juno_csig}")
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

    # TAB row tint + Discord JPEG used to flip Emre→Anran and Kiriko→Wuyang.

    def degrade(name: str, tint: tuple[int, int, int]) -> np.ndarray:
        src = Image.open(portraits / f"{name}.png").convert("RGB")
        d = 160
        src = src.resize((d, d), Image.Resampling.LANCZOS)
        circ = Image.new("L", (d, d), 0)
        ImageDraw.Draw(circ).ellipse((2, 2, d - 3, d - 3), fill=255)
        bg = Image.new("RGB", (d, d), tint)
        bg.paste(src, mask=circ)
        bg = Image.blend(bg, Image.new("RGB", (d, d), tint), 0.22)
        bg = bg.resize((28, 28), Image.Resampling.BILINEAR).resize((64, 64), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        bg.save(buf, format="JPEG", quality=35)
        return np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))

    def match_arr(arr: np.ndarray, prefer: str) -> str:
        feat = _feat_from_arr(arr)
        col = _inner_mean(arr)
        csig = _color_sig(arr)
        scores = mat @ feat
        idx, _score, _second = _pick_key(scores, col, csig, keys, colors, csigs, roles, prefer)
        return _force_confusions(keys[idx], csig, prefer, scores, keys)

    blue = (32, 58, 110)
    if match_arr(degrade("emre", blue), "damage") != "emre":
        fails.append("tinted jpeg emre was not read as emre")
    if match_arr(degrade("mizuki", blue), "support") != "mizuki":
        fails.append("tinted jpeg mizuki was not read as mizuki")
    if match_arr(degrade("kiriko", blue), "support") != "kiriko":
        fails.append("tinted jpeg kiriko was rewritten")
    if match_arr(degrade("ashe", blue), "damage") != "ashe":
        fails.append("tinted jpeg ashe was not read as ashe")
    if match_arr(degrade("mauga", blue), "tank") != "mauga":
        fails.append("tinted jpeg mauga was rewritten to emre")

    new_slots = (
        ("dmon", "tank"),
        ("domina", "tank"),
        ("hazard", "tank"),
        ("emre", "damage"),
        ("anran", "damage"),
        ("freja", "damage"),
        ("shion", "damage"),
        ("sierra", "damage"),
        ("vendetta", "damage"),
        ("mizuki", "support"),
        ("wuyang", "support"),
        ("juno", "support"),
        ("jetpack-cat", "support"),
    )
    for name, slot in new_slots:
        got = match(name, slot)
        if got != name:
            fails.append(f"{name} portrait in {slot} slot was read as {got}")
        got_j = match_arr(degrade(name, blue), slot)
        if got_j != name:
            fails.append(f"tinted jpeg {name} in {slot} slot was read as {got_j}")
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

    # Latest + other new portraits on one 5+5 board (D.Mon tank, not D.Va).
    new_allies = ["dmon", "emre", "anran", "mizuki", "jetpack-cat"]
    new_enemies = ["domina", "freja", "vendetta", "wuyang", "juno"]
    new_board = _run(new_allies, new_enemies, "mizuki", "new-hero roster dmon/emre")
    fails.extend(_expect(new_board, new_allies, new_enemies, "mizuki"))
    crushed_new = _run(
        new_allies, new_enemies, "mizuki", "discord jpeg new-hero roster", discord=True
    )
    fails.extend(_expect(crushed_new, new_allies, new_enemies, "mizuki"))
    if crushed_new["allies"][0] != "dmon":
        fails.append(f"D.Mon tank slot became {crushed_new['allies'][0]}")

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

    # Real screenshot: dark warehouse TAB, Juno on both teams, Hazard DPS, gold self = Juno.
    dark_allies = ["sigma", "cassidy", "ashe", "ana", "juno"]
    dark_enemies = ["wrecking-ball", "genji", "ashe", "mercy", "juno"]
    dark = _run(dark_allies, dark_enemies, "juno", "dark interior TAB", interior=True, hud=True)
    fails.extend(_expect(dark, dark_allies, dark_enemies, "juno"))
    crushed_dark = _run(
        dark_allies, dark_enemies, "juno", "discord jpeg dark interior", interior=True, hud=True, discord=True
    )
    if crushed_dark["enemies"] != dark_enemies:
        fails.append(f"discord dark enemies {crushed_dark['enemies']} != {dark_enemies}")
    if crushed_dark["allies"] != dark_allies:
        fails.append(f"discord dark allies {crushed_dark['allies']} != {dark_allies}")
    if "wuyang" in crushed_dark["allies"] + crushed_dark["enemies"]:
        fails.append("juno was read as wuyang on dark TAB")
    if "emre" in crushed_dark["enemies"] + crushed_dark["allies"]:
        fails.append("dark TAB invented emre")
    if len(crushed_dark["allies"]) != 5 or len(crushed_dark["enemies"]) != 5:
        fails.append(f"dark TAB was not 5+5: {crushed_dark['allies']} / {crushed_dark['enemies']}")

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

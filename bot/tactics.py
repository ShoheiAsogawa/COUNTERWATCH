"""Assemble a fight plan: this hero, this map, this enemy pick."""
from __future__ import annotations

from bot.engine import HEROES, MAPS, explicit_counter, tag_counter
from bot import tactics_data as TD


def _side_key(side: str) -> str:
    return "defend" if side == "defend" else "attack"


def _home(hero_key: str) -> str:
    return TD.HOME.get(hero_key) or "cover"


def _spots(map_key: str | None) -> dict:
    if map_key and map_key in TD.MAP_SPOTS:
        return TD.MAP_SPOTS[map_key]
    return TD.DEFAULT_SPOTS


def _danger(me: dict, enemy: dict) -> int:
    d = explicit_counter(enemy["key"], me["key"])
    t, _ = tag_counter(enemy, me)
    return int(d * 4 + t * 3)


def _threat_line(me: dict, enemy_key: str) -> str:
    row = TD.THREATS.get(enemy_key) or {}
    role = me.get("role") or "damage"
    text = row.get(role) or row.get("generic") or ""
    enemy = HEROES.get(enemy_key)
    name = enemy["nameJa"] if enemy else enemy_key
    return f"**{name}**：{text}" if text else ""


def _combo_line(enemy_keys: list[str]) -> str | None:
    have = set(enemy_keys)
    best = None
    best_n = 0
    for row in TD.COMBOS:
        need = set(row["need"])
        if need <= have and len(need) > best_n:
            best = row["ja"]
            best_n = len(need)
    return best


def _station_lines(spots: dict, side: str) -> list[str]:
    sk = _side_key(side)
    out = []
    for st in spots.get("stations") or []:
        bit = st.get(sk) or st.get("attack") or ""
        if bit:
            out.append(f"**{st['name']}** — {bit}")
    return out[:3]


def fight_plan(
    self_key: str | None,
    map_key: str | None,
    side: str,
    enemies: list[str],
    *,
    pick_hero: dict | None = None,
) -> dict:
    """If self_key is missing, describe the recommended pick_hero instead."""
    me = HEROES.get(self_key or "") or pick_hero
    if not me:
        return {"title": "立ち回り", "where": "", "stations": [], "threats": [], "combo": "", "lose": "", "lines": []}
    mp = MAPS.get(map_key) if map_key else None
    spots = _spots(map_key)
    home = _home(me["key"])
    sk = _side_key(side)
    where = ((spots.get(home) or {}).get(sk) or (spots.get(home) or {}).get("attack") or "")
    enemy_heroes = [HEROES[k] for k in enemies if k in HEROES]
    ranked = sorted(enemy_heroes, key=lambda e: _danger(me, e), reverse=True)
    threats = [_threat_line(me, e["key"]) for e in ranked[:3]]
    threats = [t for t in threats if t]
    combo = _combo_line(enemies) or ""
    stations = _station_lines(spots, side)
    play = me.get("play") or ""
    map_name = mp["nameJa"] if mp else "このマップ"
    title = f"{me['nameJa']} × {map_name}"
    lose = _lose_line(me, home, enemy_heroes)
    lines = [x for x in [where, play, combo] if x]
    return {
        "title": title,
        "hero": me,
        "home": home,
        "where": where,
        "stations": stations,
        "threats": threats,
        "combo": combo,
        "lose": lose,
        "play": play,
        "lines": lines,
    }


def _lose_line(me: dict, home: str, enemies: list[dict]) -> str:
    keys = {e["key"] for e in enemies}
    tags = set(me.get("tags") or [])
    if "wrecking-ball" in keys and home in ("cover", "high"):
        return "開けた場所でスキルを先に使うと、次のパイルか刃で落ちる。"
    if "widowmaker" in keys or "ashe" in keys:
        return "本線を覗いた瞬間が負け。箱と建物の外に出ない。"
    if any("flyer" in (e.get("tags") or []) for e in enemies) and "hitscan" not in tags:
        return "空を無視して下だけ見ると試合を取られる。"
    if me.get("role") == "support":
        return "単独で前に出ない。クリーンセを最初のダイブより先に使わない。"
    return "人数が揃う前に本線へ出ない。"


def plan_embed_body(plan: dict) -> str:
    parts = []
    if plan.get("where"):
        parts.append(f"**今いる場所**\n{plan['where']}")
    if plan.get("stations"):
        parts.append("**地点**\n" + "\n".join(f"• {x}" for x in plan["stations"]))
    if plan.get("combo"):
        parts.append(f"**この組み合わせ**\n{plan['combo']}")
    if plan.get("threats"):
        parts.append("**相手のピックへの返し**\n" + "\n".join(plan["threats"]))
    if plan.get("play"):
        parts.append(f"**自分のキット**\n{plan['play']}")
    if plan.get("lose"):
        parts.append(f"**これをやると負ける**\n{plan['lose']}")
    return "\n\n".join(parts)[:4096]

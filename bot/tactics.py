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
    rows = all_combo_lines(enemy_keys)
    return rows[0] if rows else None


def all_combo_lines(enemy_keys: list[str]) -> list[str]:
    have = set(enemy_keys)
    ranked = []
    for row in TD.COMBOS:
        need = set(row["need"])
        if need <= have:
            ranked.append((len(need), row["ja"]))
    ranked.sort(key=lambda x: -x[0])
    return [text for _, text in ranked]


def _station_lines(spots: dict, side: str) -> list[str]:
    sk = _side_key(side)
    out = []
    for st in spots.get("stations") or []:
        bit = st.get(sk) or st.get("attack") or ""
        if bit:
            out.append(bit)
    return out[:3]


def fight_plan(
    self_key: str | None,
    map_key: str | None,
    side: str,
    enemies: list[str],
    *,
    pick_hero: dict | None = None,
) -> dict:
    """Advice is for the recommended pick. self_key is only a fallback."""
    me = pick_hero or HEROES.get(self_key or "")
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
        return "砂の上の開けた場所でスキルを先に使うと、次の叩きつけか刀で倒される。"
    if "widowmaker" in keys or "ashe" in keys:
        return "真正面の道を覗いた瞬間が負け。箱と建物の外に出ない。"
    if any("flyer" in (e.get("tags") or []) for e in enemies) and "hitscan" not in tags:
        return "空を無視して下だけ見ると試合を取られる。"
    if me.get("role") == "support":
        return "一人で前に出ない。回復スキルは、飛び込まれたときに使う。"
    return "味方が揃う前に、開けた道へ出ない。"


def plan_embed_body(plan: dict) -> str:
    parts = []
    hero = plan.get("hero")
    if hero:
        parts.append(f"出すなら **{hero['nameJa']}**。")
    if plan.get("where"):
        parts.append(f"**どこに立つか**\n{plan['where']}")
    first = []
    if plan.get("stations"):
        first.append(plan["stations"][0])
    if plan.get("combo"):
        first.append(plan["combo"])
    if first:
        parts.append("**最初にやること**\n" + "\n".join(first[:2]))
    if plan.get("threats"):
        parts.append("**敵の対処**\n" + "\n".join(plan["threats"][:3]))
    if plan.get("lose"):
        parts.append(f"**やってはいけないこと**\n{plan['lose']}")
    return "\n\n".join(parts)[:4096]


def watch_lines(enemy_keys: list[str]) -> list[str]:
    out = []
    for key in enemy_keys:
        line = TD.WATCH.get(key)
        if not line:
            continue
        hero = HEROES.get(key)
        name = hero["nameJa"] if hero else key
        out.append(f"・{name}：{line}")
    return out[:4]


_ROLE_JA = {"tank": "タンク", "damage": "ダメージ", "support": "サポート"}
_SIDE_JA = {"attack": "攻撃", "defend": "防衛", "flex": "フレックス"}


def _hero_brief(hero: dict | None) -> dict | None:
    if not hero:
        return None
    skills = []
    for a in (hero.get("abilities") or [])[:4]:
        name = a.get("nameJa") or a.get("name")
        if not name:
            continue
        bit = name
        if a.get("desc"):
            bit += f"（{a['desc']}）"
        if a.get("cd") and a["cd"] not in ("no CD", "hold", "weapon", "refresh", ""):
            bit += f" {a['cd']}"
        skills.append(bit)
    ult = hero.get("ult") or {}
    return {
        "name": hero.get("nameJa") or hero.get("name"),
        "role": _ROLE_JA.get(hero.get("role") or "", hero.get("role")),
        "play": hero.get("play") or "",
        "ult": ult.get("nameJa") or ult.get("name") or "",
        "skills": skills,
    }


def advice_context(plan: dict, rec: dict, state: dict) -> dict:
    """All layers the LLM should judge together — not a script to copy."""
    mp = rec.get("map") or {}
    coach = (mp.get("coach") or {}) if mp else {}
    pick = plan.get("hero")
    enemy_keys = [h["key"] for h in (rec.get("comp") or {}).get("heroes") or []]
    if not enemy_keys:
        enemy_keys = list(state.get("enemies") or [])
    ally_keys = list(state.get("allies") or [])
    me = pick or {}
    threats_all = []
    for key in enemy_keys:
        line = _threat_line(me, key) if me else ""
        if line:
            threats_all.append(line)
    pick_reasons = []
    for row in rec.get("picks") or []:
        if pick and row.get("hero", {}).get("key") == pick.get("key"):
            pick_reasons = row.get("reasons") or []
            break
    if not pick_reasons and rec.get("picks"):
        pick_reasons = rec["picks"][0].get("reasons") or []
    return {
        "map": {
            "name": (mp or {}).get("nameJa") or "不明",
            "side": _SIDE_JA.get(state.get("side") or "flex", "フレックス"),
            "layout": coach.get("layout") or (mp or {}).get("noteJa") or "",
            "stations": plan.get("stations") or [],
            "stand": plan.get("where") or "",
        },
        "allies": [
            {"name": HEROES[k]["nameJa"], "role": _ROLE_JA.get(HEROES[k]["role"], HEROES[k]["role"])}
            for k in ally_keys
            if k in HEROES
        ],
        "enemies": [
            {"name": HEROES[k]["nameJa"], "role": _ROLE_JA.get(HEROES[k]["role"], HEROES[k]["role"])}
            for k in enemy_keys
            if k in HEROES
        ],
        "enemy_style": rec.get("weakness") or "",
        "pick": {
            **(_hero_brief(pick) or {}),
            "reasons": pick_reasons,
        },
        "alts": [
            {"name": row["hero"]["nameJa"], "reasons": (row.get("reasons") or [])[:1]}
            for row in (rec.get("picks") or [])[1:3]
        ],
        "hints": {
            "combos": all_combo_lines(enemy_keys),
            "per_enemy": threats_all,
            "watch": watch_lines(enemy_keys),
            "lose": plan.get("lose") or "",
        },
    }

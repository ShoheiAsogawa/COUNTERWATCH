"""Shared Overwatch anti-pick engine for the Discord bot."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_KNOWLEDGE_PATH = Path(__file__).parent / "knowledge.json"
OW = json.loads(_KNOWLEDGE_PATH.read_text(encoding="utf-8"))
HEROES = {h["key"]: h for h in OW["heroes"]}
MAPS = {m["key"]: m for m in OW["maps"]}
MATCHUPS = dict(OW.get("matchups") or {})
TAG_MATCHUPS = list(OW.get("tagMatchups") or [])
KNOWLEDGE_VERSION = ""


def apply_knowledge(data: dict, version: str = "") -> None:
    """Swap hero/map data in place so the Discord client can stay connected."""
    global KNOWLEDGE_VERSION
    if not data.get("heroes") or not data.get("maps"):
        raise ValueError("invalid knowledge.json")
    OW.clear()
    OW.update(data)
    HEROES.clear()
    HEROES.update({h["key"]: h for h in data["heroes"]})
    MAPS.clear()
    MAPS.update({m["key"]: m for m in data["maps"]})
    MATCHUPS.clear()
    MATCHUPS.update(data.get("matchups") or {})
    TAG_MATCHUPS[:] = data.get("tagMatchups") or []
    KNOWLEDGE_VERSION = version
    _KNOWLEDGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def reload_from_disk() -> None:
    apply_knowledge(json.loads(_KNOWLEDGE_PATH.read_text(encoding="utf-8")))

COMP_LABEL = {
    "dive": "ダイブ",
    "poke": "ポーク",
    "brawl": "ブロウル",
    "bunker": "バンカー",
    "flying": "空中",
    "sniper": "スナイプ",
    "flank": "フランカー",
    "flex": "ミックス",
}

COMP_ANSWERS = {
    "dive": {"tank": ["orisa", "roadhog", "zarya", "dmon"], "damage": ["cassidy", "mei", "torbjorn", "reaper"], "support": ["brigitte", "ana", "moira", "wuyang"]},
    "poke": {"tank": ["winston", "dva", "doomfist", "wrecking-ball"], "damage": ["genji", "tracer", "sombra", "venture"], "support": ["lucio", "kiriko", "juno"]},
    "brawl": {"tank": ["mauga", "zarya", "junker-queen", "orisa"], "damage": ["reaper", "mei", "pharah", "bastion"], "support": ["ana", "moira", "lucio", "kiriko"]},
    "bunker": {"tank": ["wrecking-ball", "winston", "hazard", "dva"], "damage": ["sombra", "venture", "junkrat", "pharah"], "support": ["lucio", "kiriko"]},
    "flying": {"tank": ["dva", "sigma", "domina"], "damage": ["ashe", "widowmaker", "cassidy", "soldier-76", "sojourn"], "support": ["baptiste", "mizuki", "ana", "illari"]},
    "sniper": {"tank": ["winston", "dva", "wrecking-ball", "doomfist"], "damage": ["genji", "tracer", "sombra"], "support": ["lucio", "kiriko", "moira"]},
    "flank": {"tank": ["orisa", "zarya", "roadhog"], "damage": ["cassidy", "torbjorn", "mei", "symmetra"], "support": ["brigitte", "moira", "baptiste"]},
}

WEAK = {
    "flying": "ヒットスキャン不足だと空に試合を支配される",
    "dive": "CC・アンチダイブがないとバックラインが溶ける",
    "brawl": "アンチヒールと頭上火力でブロウルは崩せる",
    "poke": "接近され情報と距離を失うとポークは負ける",
    "bunker": "ハック・地中・頭上でバンカーは崩壊する",
    "sniper": "遮蔽とダイブでスナイパーを沈黙させられる",
}


def portrait_path(key: str) -> Path:
    return ROOT / "assets" / "heroes" / f"{key}.png"


def map_shot_path(key: str) -> Path:
    return ROOT / "assets" / "maps" / f"{key}.jpg"


def explicit_counter(attacker: str, target: str) -> int:
    return int((MATCHUPS.get(attacker) or {}).get(target) or 0)


def tag_counter(attacker: dict, target: dict) -> tuple[int, list]:
    a_tags = set(attacker.get("tags") or [])
    b_tags = set(target.get("tags") or [])
    best = 0
    hits = []
    for rule in TAG_MATCHUPS:
        if rule["a"] in a_tags and rule["b"] in b_tags:
            if rule["score"] >= best:
                best = rule["score"]
                hits.append(rule)
    return best, [r for r in hits if r["score"] >= 3]


def detect_composition(enemy_keys: list[str]) -> dict:
    heroes = [HEROES[k] for k in enemy_keys if k in HEROES]
    counts = {"dive": 0, "poke": 0, "brawl": 0, "bunker": 0, "flying": 0, "sniper": 0, "flank": 0}
    for h in heroes:
        t = set(h.get("tags") or [])
        if "dive" in t or "flank" in t:
            counts["dive"] += 2 if "dive" in t else 1
        if "poke" in t or "sniper" in t or "long-range" in t:
            counts["poke"] += 1
        if "brawl" in t or "melee" in t:
            counts["brawl"] += 1
        if "bunker" in t or "turret" in t:
            counts["bunker"] += 2
        if "flyer" in t:
            counts["flying"] += 2
        if "sniper" in t:
            counts["sniper"] += 2
        if "flank" in t:
            counts["flank"] += 1
    if any("flyer" in (h.get("tags") or []) for h in heroes) and any(
        "flyer-synergy" in (h.get("tags") or []) for h in heroes
    ):
        counts["flying"] += 3
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    primary = ranked[0][0] if ranked[0][1] > 0 else "flex"
    return {"counts": counts, "primary": primary, "heroes": heroes}


def map_affinity(hero: dict, mp: dict | None, side: str) -> tuple[int, list[str]]:
    if not mp:
        return 0, []
    traits = set(mp.get("traits") or [])
    tags = set(hero.get("tags") or [])
    score = 0
    reasons = []

    def bump(cond, pts, text):
        nonlocal score
        if cond:
            score += pts
            if pts >= 2:
                reasons.append(text)

    bump(traits.intersection({"longsight"}) and tags.intersection({"sniper", "hitscan", "long-range"}), 4, f"{mp['nameJa']}は長視線。{hero['nameJa']}の射程が刺さる")
    bump("choke" in traits and tags.intersection({"barrier", "spam", "freeze", "brawl"}), 3, f"チョークで{hero['nameJa']}のエリア制御が強い")
    bump("vertical" in traits and (tags.intersection({"flyer", "mobile"}) or hero["key"] in ("winston", "juno", "dva")), 3, "高低差で機動力が活きる")
    bump("environmental" in traits and (hero["key"] in ("lucio", "junkrat", "hazard", "pharah") or "boop" in tags), 3, "崖・井戸があり環境キルが取りやすい")
    bump("close" in traits and tags.intersection({"brawl", "melee", "tankbuster", "beam"}), 3, "近接マップで近距離キットが強い")
    bump("open" in traits and "sniper" in tags, 3, "開放マップでスナイプが通りやすい")
    bump("flashpoint" in traits and tags.intersection({"mobile", "speed", "flank"}), 3, "フラッシュポイントはローテ性能が勝つ")
    bump("clash" in traits and tags.intersection({"brawl", "melee", "barrier"}), 3, "クラッシュは超近接ブロウル")
    bump("longsight" in traits and "melee" in tags and "mobile" not in tags, -3, "長視線は近接に厳しい")
    bump("close" in traits and "sniper" in tags, -3, "近接マップでスナイパーは落ちる")
    if side == "attack" and tags.intersection({"dive", "flank", "speed"}):
        score += 1
    if side == "defend" and tags.intersection({"bunker", "barrier", "turret", "sniper"}):
        score += 1
    return score, reasons


def recommend(my_role: str, enemies: list[str], map_key: str | None, side: str = "flex") -> dict:
    my_role = my_role if my_role in ("tank", "damage", "support") else "damage"
    enemy_heroes = [HEROES[k] for k in enemies if k in HEROES]
    taken = set(enemies)
    mp = MAPS.get(map_key) if map_key else None
    comp = detect_composition(enemies)
    answers = (COMP_ANSWERS.get(comp["primary"]) or {}).get(my_role) or []
    ranked = []
    for hero in OW["heroes"]:
        if hero["role"] != my_role or hero["key"] in taken:
            continue
        score = 24
        reasons = []
        for enemy in enemy_heroes:
            direct = explicit_counter(hero["key"], enemy["key"])
            tagged, rules = tag_counter(hero, enemy)
            power = max(direct, tagged)
            threat_d = explicit_counter(enemy["key"], hero["key"])
            threat_t, _ = tag_counter(enemy, hero)
            threat = max(threat_d, threat_t * 0.7)
            score += power * 4.6 - threat * 3.4
            if power >= 4:
                reasons.append(f"{enemy['nameJa']}に対して明確なカウンター")
            elif power >= 3:
                rule = rules[0] if rules else None
                reasons.append(f"{enemy['nameJa']}：{rule['ja']}" if rule else f"{enemy['nameJa']}との相性が良い")
            if threat >= 4:
                reasons.append(f"注意：{enemy['nameJa']}から強くカウンターされる")
                score -= 2
        if hero["key"] in answers:
            score += 6
            reasons.append(f"{COMP_LABEL[comp['primary']]}構成への定番回答")
        fit, map_reasons = map_affinity(hero, mp, side)
        score += fit * 1.6
        reasons.extend(map_reasons[:2])
        if comp["primary"] == "flying" and "hitscan" in (hero.get("tags") or []):
            score += 5
            reasons.append("空中構成にはヒットスキャンが最優先")
        if comp["counts"]["flying"] >= 2 and "hitscan" in (hero.get("tags") or []):
            score += 6
            reasons.append("フォマシー／空中にはヒットスキャン")
        if comp["primary"] == "dive" and set(hero.get("tags") or []).intersection({"anti-dive", "cc", "sleeper", "anti-flank"}):
            score += 4
        if comp["primary"] == "sniper" and set(hero.get("tags") or []).intersection({"dive", "flank"}):
            score += 4
            reasons.append("スナイパー裏を取るダイブ／フランカー")
        uniq = []
        seen = set()
        for r in reasons:
            if r not in seen:
                seen.add(r)
                uniq.append(r)
        ranked.append({"hero": hero, "raw": score, "reasons": uniq[:4]})
    ranked.sort(key=lambda x: x["raw"], reverse=True)
    top_raw = ranked[0]["raw"] if ranked else 1
    floor = ranked[min(len(ranked) - 1, 12)]["raw"] if ranked else 0
    for row in ranked:
        t = (row["raw"] - floor) / max(8, top_raw - floor)
        row["score"] = round(max(12, min(99, 28 + t * 71)))
    return {
        "comp": comp,
        "comp_label": COMP_LABEL.get(comp["primary"], "ミックス"),
        "weakness": WEAK.get(comp["primary"], "構成の穴を突く"),
        "picks": ranked[:5],
        "map": mp,
    }


def parse_text(text: str) -> dict:
    lower = (text or "").lower().replace("’", "'")
    role = None
    if any(w in lower for w in ("tank", "タンク")):
        role = "tank"
    elif any(w in lower for w in ("support", "sup", "サポート", "ヒーラー")):
        role = "support"
    elif any(w in lower for w in ("dps", "damage", "ダメージ", "dps")):
        role = "damage"
    side = "flex"
    if any(w in lower for w in ("attack", "atk", "攻撃")):
        side = "attack"
    elif any(w in lower for w in ("defend", "def", "防衛", "防御")):
        side = "defend"
    map_key = None
    best = 0
    for m in OW["maps"]:
        aliases = [
            m["name"],
            m["nameJa"],
            m["key"].replace("-", " "),
            m["key"].replace("-", ""),
        ]
        for part in m["key"].split("-"):
            if len(part) >= 6:
                aliases.append(part)
        for n in aliases:
            needle = str(n).lower().replace(":", "")
            hay = lower.replace(":", "")
            if len(needle) >= 4 and needle in hay and len(needle) > best:
                map_key = m["key"]
                best = len(needle)
    hero_keys = []
    names = []
    for h in OW["heroes"]:
        names.append((h["key"], h["name"].lower()))
        names.append((h["key"], h["nameJa"].lower()))
        names.append((h["key"], h["key"].replace("-", " ")))
        names.append((h["key"], h["name"].lower().replace(":", "").replace("'", "")))
    names.sort(key=lambda x: len(x[1]), reverse=True)
    used = set()
    for key, name in names:
        if key in used or len(name) < 3:
            continue
        if name in lower:
            hero_keys.append(key)
            used.add(key)
    return {"role": role, "side": side, "map_key": map_key, "hero_keys": hero_keys}


def movement_lines(hero: dict, rec: dict, side: str) -> list[str]:
    lines = []
    mp = rec.get("map")
    coach = (mp or {}).get("coach") or {}
    if coach:
        if side == "attack":
            lines.append(coach.get("attack") or "")
        elif side == "defend":
            lines.append(coach.get("defend") or "")
        else:
            lines.append(coach.get("move") or "")
    if hero.get("play"):
        lines.append(hero["play"])
    tags = set(hero.get("tags") or [])
    primary = rec["comp"]["primary"]
    if primary == "flying" and "hitscan" in tags:
        lines.append("空の軌道は本線の真上ではなく、やや後ろの高所から切る。落ちたらすぐ次の箱へ。")
    if primary == "dive" and tags.intersection({"anti-dive", "sleeper", "cc"}):
        lines.append("自分から前に出ない。着地地点（サポの横）でCCを待つ。")
    if primary == "brawl" and "antiheal" in tags:
        lines.append("最初のアンチをタンク足下に入れて、近接の回復勝負を切る。")
    if primary == "sniper" and tags.intersection({"dive", "flank"}):
        lines.append("本線を歩かない。壁の裏から高所のスナイパーへ。")
    return [x for x in lines if x][:5]


def cd_lines(heroes: list[dict]) -> list[str]:
    out = []
    for h in heroes[:5]:
        bits = []
        for a in h.get("abilities") or []:
            cd = a.get("cd") or ""
            if cd and cd not in ("no CD", "hold", "weapon", "refresh"):
                bits.append(f"{a['nameJa']} {cd}")
            if len(bits) >= 3:
                break
        if bits:
            out.append(f"{h['nameJa']}：{' / '.join(bits)}")
    return out

"""Read Overwatch TAB / scoreboard screenshots (JP or EN).

Real TAB layout: allies on top (blue rows), enemies on bottom (red rows),
circular portraits on the left of each row. The same hero can appear on both
teams. The highlighted row is the player taking the screenshot.
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PORTRAIT_DIR = ROOT / "assets" / "heroes"


def _circle_mask(size: int, inner: float = 0.92) -> np.ndarray:
    yy, xx = np.ogrid[:size, :size]
    c = (size - 1) / 2
    r = c * inner
    return (xx - c) ** 2 + (yy - c) ** 2 <= r * r


GRID = 10
MASK = _circle_mask(GRID * 2, inner=0.70)
MASK_F = MASK.astype(np.float32)[:, :, None]
ROLE_QUEUE = ("tank", "damage", "damage", "support", "support")


def _color_sig(arr: np.ndarray) -> np.ndarray:
    """Top-band color + red/green fractions — separates Kiriko/Mizuki, Mauga/Emre."""
    img = Image.fromarray(arr).resize((48, 48), Image.Resampling.BILINEAR)
    a = np.asarray(img, dtype=np.float32)
    yy, xx = np.ogrid[:48, :48]
    circ = (xx - 23.5) ** 2 + (yy - 23.5) ** 2 <= 20 ** 2
    pix = a[circ]
    if pix.size == 0:
        return np.zeros(7, dtype=np.float32)
    top = a[circ & (yy < 20)]
    r, g, b = pix[:, 0], pix[:, 1], pix[:, 2]
    redfrac = float(((r > g + 20) & (r > b + 12)).mean())
    greenfrac = float(((g > r + 6) & (g > 45)).mean())
    if top.size:
        tr, tg, tb = top.mean(axis=0)
        top_lum = float((tr + tg + tb) / 3)
        top_rg = float(tr - tg)
    else:
        tr = tg = tb = top_lum = top_rg = 0.0
    return np.array([tr, tg, tb, redfrac, greenfrac, top_lum, top_rg], dtype=np.float32)


def _feat_from_arr(arr: np.ndarray) -> np.ndarray:
    img = Image.fromarray(arr).resize((GRID * 2, GRID * 2), Image.Resampling.BILINEAR)
    a = np.asarray(img, dtype=np.float32) * MASK_F
    g = a.reshape(GRID, 2, GRID, 2, 3).mean(axis=(1, 3))
    v = g.reshape(-1)
    v = v - v.mean()
    n = float(np.linalg.norm(v))
    return v / (n + 1e-6)


def _inner_mean(arr: np.ndarray) -> np.ndarray:
    img = Image.fromarray(arr).resize((GRID * 2, GRID * 2), Image.Resampling.BILINEAR)
    a = np.asarray(img, dtype=np.float32)
    pix = a[MASK]
    if pix.size == 0:
        return np.zeros(3, dtype=np.float32)
    return pix.mean(axis=0)


def _feat_from_image(img: Image.Image) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    w, h = img.size
    side = int(min(w, h) * 0.82)
    sx = (w - side) // 2
    sy = (h - side) // 2 + int(h * 0.02)
    crop = img.crop((sx, sy, sx + side, sy + side)).convert("RGB")
    arr = np.asarray(crop)
    return _feat_from_arr(arr), _inner_mean(arr), _color_sig(arr)


@lru_cache(maxsize=1)
def _templates() -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, list[str]]:
    from bot.engine import HEROES

    keys: list[str] = []
    vecs: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    csigs: list[np.ndarray] = []
    roles: list[str] = []
    for path in sorted(PORTRAIT_DIR.glob("*.png")):
        img = Image.open(path).convert("RGB")
        feat, col, csig = _feat_from_image(img)
        keys.append(path.stem)
        vecs.append(feat)
        colors.append(col)
        csigs.append(csig)
        roles.append((HEROES.get(path.stem) or {}).get("role") or "damage")
    return keys, np.stack(vecs), np.stack(colors), np.stack(csigs), roles


def _resize_max(img: Image.Image, max_w: int = 1920) -> Image.Image:
    if img.width <= max_w:
        return img.convert("RGB")
    h = int(img.height * max_w / img.width)
    return img.convert("RGB").resize((max_w, h), Image.Resampling.BILINEAR)


def _row_color(arr: np.ndarray, x: int, y: int, size: int) -> tuple[str, float]:
    """Blue row = ally, red row = enemy. Sample the name plate to the right of the portrait."""
    h, w, _ = arr.shape
    x0 = min(w - 12, x + int(size * 0.95))
    x1 = min(w, x0 + max(40, int(size * 3.2)))
    y0 = max(0, y + int(size * 0.15))
    y1 = min(h, y + int(size * 0.85))
    strip = arr[y0:y1, x0:x1]
    if strip.size == 0:
        return "unknown", 0.0
    r, g, b = strip.mean(axis=(0, 1))
    lum = float((r + g + b) / 3)
    if b > r + 10 and b >= g - 4:
        return "ally", lum
    if r > 55 and g > 40 and (r + g) > b * 1.3 and abs(float(r) - float(g)) < 50:
        return "ally", lum  # highlighted own row (gold / yellow)
    if r > b + 10 and r >= g - 8:
        return "enemy", lum
    return "unknown", lum


def _pick_key(
    scores: np.ndarray,
    color: np.ndarray,
    csig: np.ndarray,
    keys: list[str],
    colors: np.ndarray,
    csigs: np.ndarray,
    roles: list[str],
    prefer_role: str | None,
) -> tuple[int, float, float]:
    ranked = np.argsort(scores)[::-1]
    top = ranked[:8]
    best_i = int(top[0])
    best = float(scores[best_i])

    def penalty(i: int) -> float:
        # Prefer the template whose top-band color matches the crop.
        d = float(np.linalg.norm(csig[:3] - csigs[i][:3]) / 80.0)
        cpen = float(np.linalg.norm(color - colors[i]) / 180.0) * 0.04
        role_pen = 0.0
        if prefer_role and roles[i] != prefer_role:
            role_pen = 0.11
        # Kiriko is very red on top; Mizuki is green/teal.
        red_pen = abs(float(csig[3] - csigs[i][3])) * 0.08
        grn_pen = abs(float(csig[4] - csigs[i][4])) * 0.10
        return d + cpen + role_pen + red_pen + grn_pen

    chosen = best_i
    chosen_s = best - penalty(best_i)
    for i in top:
        i = int(i)
        s = float(scores[i])
        if s < best - 0.10:
            break
        adj = s - penalty(i)
        if adj > chosen_s:
            chosen, chosen_s = i, adj
    second = float(scores[int(top[1])]) if len(top) > 1 else 0.0
    return chosen, float(scores[chosen]), second


def _force_confusions(
    key: str,
    csig: np.ndarray,
    prefer_role: str | None,
    scores: np.ndarray | None = None,
    keys: list[str] | None = None,
) -> str:
    redfrac, greenfrac, top_lum, top_rg = float(csig[3]), float(csig[4]), float(csig[5]), float(csig[6])
    if key in ("kiriko", "mizuki"):
        if greenfrac >= 0.16 and top_rg < 20:
            return "mizuki"
        if redfrac >= 0.42 and top_rg > 22:
            return "kiriko"

    def close_enough(other: str) -> bool:
        if scores is None or keys is None or other not in keys or key not in keys:
            return True
        return float(scores[keys.index(other)]) >= float(scores[keys.index(key)]) - 0.10

    # Role-queue TAB is tank / dps / dps / support / support.
    # Only swap Mauga↔Emre when the other portrait is a close cosine match
    # so a real open-queue second tank is not rewritten.
    if prefer_role == "damage" and key == "mauga" and close_enough("emre"):
        return "emre"
    if prefer_role == "tank" and key == "emre" and close_enough("mauga"):
        return "mauga"
    if key in ("mauga", "emre") and prefer_role is None:
        return "mauga" if top_lum >= 108 else "emre"
    return key


def _merge_mask_bands(mask: np.ndarray, lum: np.ndarray, team: str, min_h: int) -> list[dict]:
    out: list[dict] = []
    y = 0
    h = len(mask)
    while y < h:
        if not mask[y]:
            y += 1
            continue
        y0 = y
        while y < h and mask[y]:
            y += 1
        if y - y0 >= min_h:
            out.append({"y0": int(y0), "y1": int(y), "team": team, "lum": float(lum[y0:y].mean())})
    return out


def _scoreboard_rows(arr: np.ndarray, x0: int, x1: int) -> list[dict]:
    h, w, _ = arr.shape
    x0 = max(0, x0)
    x1 = min(w, x1)
    if x1 - x0 < 40:
        return []
    mean = arr[:, x0:x1].astype(np.float32).mean(axis=1)
    r, g, b = mean[:, 0], mean[:, 1], mean[:, 2]
    lum = mean.mean(axis=1)
    min_h = max(16, int(h * 0.025))
    blue = (b > r + 7) & (b > 32) & (lum > 22)
    red = (r > b + 7) & (r > 32) & (lum > 22)
    gold = (r > 50) & (g > 38) & (r + g > b * 1.3) & (lum > 38) & ~blue & ~red
    rows = (
        _merge_mask_bands(blue, lum, "ally", min_h)
        + _merge_mask_bands(red, lum, "enemy", min_h)
        + _merge_mask_bands(gold, lum, "ally", min_h)
    )
    rows.sort(key=lambda z: z["y0"])
    # Drop tiny fragments sandwiched in the VS gap.
    cleaned = []
    for row in rows:
        if cleaned and row["y0"] - cleaned[-1]["y1"] < 4 and row["team"] == cleaned[-1]["team"]:
            cleaned[-1]["y1"] = row["y1"]
            cleaned[-1]["lum"] = max(cleaned[-1]["lum"], row["lum"])
        else:
            cleaned.append(row)
    return [row for row in cleaned if row["y1"] - row["y0"] <= int(h * 0.14)]


def _annotate_roles(rows: list[dict]) -> None:
    """Stamp role-queue slots onto 5-row teams (tank / dps / dps / support / support)."""
    by_team: dict[str, list[dict]] = {}
    for row in rows:
        by_team.setdefault(row["team"], []).append(row)
    for team_rows in by_team.values():
        team_rows.sort(key=lambda z: z["y0"])
        if len(team_rows) != 5:
            continue
        for i, row in enumerate(team_rows):
            row["prefer_role"] = ROLE_QUEUE[i]


def _best_in_row(arr: np.ndarray, row: dict, x_lo: int, x_hi: int) -> dict | None:
    keys, mat, colors, csigs, roles = _templates()
    prefer = row.get("prefer_role")
    h, w, _ = arr.shape
    y0, y1 = row["y0"], row["y1"]
    band_h = y1 - y0
    if band_h < 18:
        return None
    best_hit = None
    for scale in (0.72, 0.82, 0.92):
        size = int(band_h * scale)
        if size < 18 or size > w // 3:
            continue
        y = y0 + max(0, (band_h - size) // 2)
        if y + size > h:
            continue
        step = max(2, size // 10)
        for x in range(max(0, x_lo), min(x_hi, w - size), step):
            patch = arr[y : y + size, x : x + size]
            if patch.std() < 16:
                continue
            feat = _feat_from_arr(patch)
            col = _inner_mean(patch)
            csig = _color_sig(patch)
            scores = mat @ feat
            idx, score, second = _pick_key(scores, col, csig, keys, colors, csigs, roles, prefer)
            if score < 0.70:
                continue
            key = _force_confusions(keys[idx], csig, prefer, scores, keys)
            team, lum = _row_color(arr, x, y, size)
            if team == "unknown":
                team, lum = row["team"], row["lum"]
            hit = {
                "key": key,
                "x": int(x),
                "y": int(y),
                "cx": x + size / 2,
                "cy": y + size / 2,
                "size": int(size),
                "score": score,
                "margin": score - second,
                "team": team,
                "lum": lum,
            }
            if best_hit is None or (hit["score"], hit["margin"]) > (best_hit["score"], best_hit["margin"]):
                best_hit = hit
    return best_hit


def _match_portraits(arr: np.ndarray) -> list[dict]:
    h, w, _ = arr.shape
    regions = [
        (int(w * 0.08), int(w * 0.84), int(w * 0.06), int(w * 0.30)),  # TAB: full rows, portraits on left
        (int(w * 0.08), int(w * 0.48), int(w * 0.08), int(w * 0.42)),  # two-column left
        (int(w * 0.50), int(w * 0.92), int(w * 0.50), int(w * 0.78)),  # two-column right
    ]
    unique_rows: list[dict] = []
    row_x: list[tuple[int, int]] = []
    seen_rows: list[tuple] = []
    for rx0, rx1, px0, px1 in regions:
        for row in _scoreboard_rows(arr, rx0, rx1):
            sig = (row["y0"] // 8, row["team"])
            if sig in seen_rows:
                continue
            seen_rows.append(sig)
            unique_rows.append(row)
            row_x.append((px0, px1))
    _annotate_roles(unique_rows)
    picked: list[dict] = []
    for row, (px0, px1) in zip(unique_rows, row_x):
        hit = _best_in_row(arr, row, px0, px1)
        if hit:
            picked.append(hit)
    picked.sort(key=lambda z: (z["cy"], z["cx"]))
    # Prefer a 5+5 TAB reading when we got too many fragments.
    if len(picked) > 12:
        picked = picked[:12]
    return picked


def _split_clusters(hits: list[dict], axis: str) -> tuple[list[dict], list[dict]]:
    if len(hits) < 2:
        return hits, []
    key = "cy" if axis == "y" else "cx"
    ordered = sorted(hits, key=lambda z: z[key])
    vals = [z[key] for z in ordered]
    gaps = [(vals[i + 1] - vals[i], i) for i in range(len(vals) - 1)]
    gap, idx = max(gaps)
    span = vals[-1] - vals[0] + 1
    if gap < max(28, span * 0.12):
        return ordered, []
    return ordered[: idx + 1], ordered[idx + 1 :]


def _assign_teams(hits: list[dict]) -> tuple[list[str], list[str], str]:
    if not hits:
        return [], [], "unknown"
    top, bottom = _split_clusters(hits, "y")
    left, right = _split_clusters(hits, "x")
    # Real TAB: allies above, enemies below. Prefer this when both tables exist.
    if len(top) >= 3 and len(bottom) >= 3:
        return [h["key"] for h in top], [h["key"] for h in bottom], "tab"
    allies = [h for h in hits if h["team"] == "ally"]
    enemies = [h for h in hits if h["team"] == "enemy"]
    if len(allies) >= 2 and len(enemies) >= 2:
        return [h["key"] for h in allies], [h["key"] for h in enemies], "color"
    if len(left) >= 2 and len(right) >= 2:
        return [h["key"] for h in left], [h["key"] for h in right], "columns"
    if enemies:
        return [h["key"] for h in allies], [h["key"] for h in enemies], "color"
    return [], [h["key"] for h in hits[:5]], "flat"


def _find_self(hits: list[dict], ally_keys: list[str]) -> str | None:
    ally_hits = [h for h in hits if h["key"] in ally_keys]
    if not ally_hits:
        return None
    best = max(ally_hits, key=lambda z: z["lum"])
    rest = [h["lum"] for h in ally_hits if h is not best]
    if rest and best["lum"] < (sum(rest) / len(rest)) + 4:
        return None
    return best["key"]


def _ocr_text(img: Image.Image) -> str:
    try:
        import pytesseract
    except Exception:
        return ""
    try:
        w, h = img.size
        header = img.crop((int(w * 0.42), 0, w, int(h * 0.22)))
        header = ImageOps.autocontrast(header)
        header = ImageEnhance.Contrast(header).enhance(1.6)
        header = header.convert("L").point(lambda p: 255 if p > 48 else 0)
        langs = "eng"
        try:
            langs = "eng+jpn" if "jpn" in pytesseract.get_languages(config="") else "eng"
        except Exception:
            langs = "eng"
        text = pytesseract.image_to_string(header, lang=langs, config="--psm 6") or ""
        wide = img.resize((min(1400, w), int(h * min(1400, w) / w)))
        body = pytesseract.image_to_string(wide, lang=langs, config="--psm 6") or ""
        return f"{text}\n{body}"
    except Exception:
        return ""


def read_scoreboard(data: bytes) -> dict:
    try:
        from bot.vision_api import read_with_api

        api = read_with_api(data)
        if api and len(api.get("enemies") or []) >= 2:
            return api
    except Exception:
        pass
    img = Image.open(io.BytesIO(data))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (12, 14, 18))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    work = _resize_max(img)
    arr = np.asarray(work)
    hits = _match_portraits(arr)
    allies, enemies, layout = _assign_teams(hits)
    # Keep at most 5 per side, in board order.
    allies = list(dict.fromkeys(allies))[:5]
    enemies = list(dict.fromkeys(enemies))[:5]
    self_key = _find_self(hits, allies)
    ocr = _ocr_text(work)
    from bot.engine import HEROES, parse_text

    parsed = parse_text(ocr)
    role = None
    if self_key and self_key in HEROES:
        role = HEROES[self_key]["role"]
    map_key = parsed.get("map_key")
    # OCR hero names are a fallback only when portraits failed.
    if len(enemies) < 2 and parsed.get("hero_keys"):
        keys = parsed["hero_keys"]
        enemies = keys[-5:] if len(keys) >= 8 else keys[:5]
        if not layout or layout == "unknown":
            layout = "ocr"
    return {
        "allies": allies,
        "enemies": enemies,
        "self_key": self_key,
        "role": role,
        "map_key": map_key,
        "layout": layout,
        "ocr_text": ocr,
        "hits": hits,
    }


def render_tab_fixture(
    allies: list[str],
    enemies: list[str],
    map_title: str = "ROUTE 66",
    self_key: str | None = None,
    size: tuple[int, int] = (1920, 1080),
) -> Image.Image:
    """Synthetic TAB scoreboard used by tests (top blue / bottom red / circular icons)."""
    w, h = size
    img = Image.new("RGB", (w, h), (18, 22, 28))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), fill=(8, 10, 14, 230))
    draw.text((int(w * 0.72), int(h * 0.04)), "エスコート", fill=(220, 220, 220))
    draw.text((int(w * 0.72), int(h * 0.07)), map_title, fill=(240, 200, 80))
    draw.text((int(w * 0.72), int(h * 0.10)), "時間 : 6:28", fill=(200, 200, 200))

    def paint(keys: list[str], y0: float, y1: float, color: tuple[int, int, int], highlight: str | None):
        rows = max(1, len(keys))
        top = int(h * y0)
        bot = int(h * y1)
        row_h = (bot - top) // rows
        for i, key in enumerate(keys):
            y = top + i * row_h
            bg = color
            if highlight and key == highlight:
                bg = (168, 148, 64)
            draw.rectangle((int(w * 0.12), y + 6, int(w * 0.88), y + row_h - 6), fill=bg + (255,))
            port = Image.open(PORTRAIT_DIR / f"{key}.png").convert("RGBA")
            d = int(row_h * 0.86)
            port = port.resize((d, d), Image.Resampling.LANCZOS)
            circ = Image.new("L", (d, d), 0)
            ImageDraw.Draw(circ).ellipse((1, 1, d - 2, d - 2), fill=255)
            port.putalpha(circ)
            x = int(w * 0.14)
            img.paste(port, (x, y + (row_h - d) // 2), port)

    paint(allies, 0.16, 0.48, (32, 58, 110), self_key)
    draw.text((int(w * 0.48), int(h * 0.49)), "VS", fill=(230, 230, 230))
    paint(enemies, 0.54, 0.86, (110, 36, 36), None)
    return img

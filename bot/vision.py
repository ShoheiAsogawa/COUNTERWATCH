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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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
    """Top-band color + red/green/cyan/orange fractions — separates Kiriko/Mizuki, Mauga/Emre."""
    img = Image.fromarray(arr).resize((48, 48), Image.Resampling.BILINEAR)
    a = np.asarray(img, dtype=np.float32)
    yy, xx = np.ogrid[:48, :48]
    circ = (xx - 23.5) ** 2 + (yy - 23.5) ** 2 <= 20 ** 2
    pix = a[circ]
    if pix.size == 0:
        return np.zeros(11, dtype=np.float32)
    top = a[circ & (yy < 20)]
    r, g, b = pix[:, 0], pix[:, 1], pix[:, 2]
    redfrac = float(((r > g + 20) & (r > b + 12)).mean())
    greenfrac = float(((g > r + 6) & (g > 45)).mean())
    cyanfrac = float(((b > r + 10) & (g > r + 4)).mean())
    orangefrac = float(((r > g + 8) & (r > b + 18) & (g > b)).mean())
    skinfrac = float(((r > 75) & (g > 45) & (r > b - 8) & (np.abs(r - g) < 65)).mean())
    purplefrac = float(((b > g + 8) & (r > 50) & (b > r - 10)).mean())
    # Mizuki visor is neon green through the eyes; Kiriko/Emre never are.
    neonfrac = float(((g > r + 12) & (g > 70) & (g >= b - 15)).mean())
    if top.size:
        tr, tg, tb = top.mean(axis=0)
        top_lum = float((tr + tg + tb) / 3)
        top_rg = float(tr - tg)
    else:
        tr = tg = tb = top_lum = top_rg = 0.0
    return np.array(
        [
            tr,
            tg,
            tb,
            redfrac,
            greenfrac,
            top_lum,
            top_rg,
            cyanfrac,
            orangefrac,
            skinfrac,
            purplefrac,
            neonfrac,
        ],
        dtype=np.float32,
    )


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


def _tab_variants(img: Image.Image) -> list[Image.Image]:
    rgb = img.convert("RGB")
    return [rgb, rgb.filter(ImageFilter.GaussianBlur(radius=1.15))]


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
        role = (HEROES.get(path.stem) or {}).get("role") or "damage"
        for variant in _tab_variants(img):
            feat, col, csig = _feat_from_image(variant)
            keys.append(path.stem)
            vecs.append(feat)
            colors.append(col)
            csigs.append(csig)
            roles.append(role)
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
    top = ranked[:12]
    best_i = int(top[0])
    best = float(scores[best_i])
    if prefer_role:
        role_best = max(
            (float(scores[i]) for i, role in enumerate(roles) if role == prefer_role),
            default=-1.0,
        )
        # A near-perfect portrait wins even if the TAB slot guess is wrong
        # (JPEG can shift Ashe onto a support row). 0.10 used to promote Wuyang.
        if best < 0.96 and role_best >= best - 0.06:
            top = np.array([int(i) for i in top if roles[int(i)] == prefer_role], dtype=int)
            if len(top) == 0:
                top = ranked[:8]
            best_i = int(top[0])
            best = float(scores[best_i])

    def penalty(i: int) -> float:
        # Absolute RGB mean shifts under TAB tint/JPEG. Keep this a tie-break
        # or Emre (0.97 cosine) loses to Anran.
        d = min(0.05, float(np.linalg.norm(csig[:3] - csigs[i][:3]) / 400.0))
        cpen = float(np.linalg.norm(color - colors[i]) / 180.0) * 0.04
        role_pen = 0.0
        if prefer_role and roles[i] != prefer_role:
            # Near-perfect portrait: keep it (off-role / open queue).
            role_pen = 0.0 if float(scores[i]) >= 0.97 else 0.11
        # Kiriko is very red on top; Mizuki is green/teal; Emre TAB icons run orange.
        red_pen = abs(float(csig[3] - csigs[i][3])) * 0.08
        grn_pen = abs(float(csig[4] - csigs[i][4])) * 0.10
        cyan_pen = abs(float(csig[7] - csigs[i][7])) * 0.10 if csig.size > 7 else 0.0
        org_pen = abs(float(csig[8] - csigs[i][8])) * 0.08 if csig.size > 8 else 0.0
        neon_pen = abs(float(csig[11] - csigs[i][11])) * 0.12 if csig.size > 11 else 0.0
        return d + cpen + role_pen + red_pen + grn_pen + cyan_pen + org_pen + neon_pen

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
    # Color is a tie-break. A clear cosine winner (Emre 0.97 vs Anran 0.93) must stick.
    if float(scores[chosen]) < best - 0.008:
        if (not prefer_role) or roles[best_i] == prefer_role or best >= 0.94:
            chosen = best_i
    second = float(scores[int(top[1])]) if len(top) > 1 else 0.0
    return chosen, float(scores[chosen]), second


def _score_of(scores: np.ndarray | None, keys: list[str] | None, name: str) -> float:
    if scores is None or keys is None:
        return -1.0
    best = -1.0
    for i, k in enumerate(keys):
        if k == name:
            best = max(best, float(scores[i]))
    return best


def _force_confusions(
    key: str,
    csig: np.ndarray,
    prefer_role: str | None,
    scores: np.ndarray | None = None,
    keys: list[str] | None = None,
) -> str:
    redfrac, greenfrac, top_lum, top_rg = float(csig[3]), float(csig[4]), float(csig[5]), float(csig[6])
    cyanfrac = float(csig[7]) if csig.size > 7 else 0.0
    orangefrac = float(csig[8]) if csig.size > 8 else 0.0
    skinfrac = float(csig[9]) if csig.size > 9 else 0.0
    purplefrac = float(csig[10]) if csig.size > 10 else 0.0
    neonfrac = float(csig[11]) if csig.size > 11 else 0.0
    teal = cyanfrac >= 0.14 or (greenfrac >= 0.16 and top_rg < 20)
    # Mizuki's neon visor survives TAB tint; do not wait until cosine already says Mizuki.
    if neonfrac >= 0.10 or (greenfrac >= 0.22 and cyanfrac >= 0.22 and redfrac < 0.48 and purplefrac < 0.20):
        if prefer_role in (None, "support") or key in ("kiriko", "mizuki", "wuyang", "mercy", "ana", "genji"):
            return "mizuki"
    # Juno visor is purple/cyan; Wuyang is an orange face. They cosine-match ~0.93.
    if key in ("juno", "wuyang"):
        if purplefrac >= 0.16 or (cyanfrac >= 0.12 and orangefrac < 0.55):
            return "juno"
        juno_s = _score_of(scores, keys, "juno")
        wuy_s = _score_of(scores, keys, "wuyang")
        if prefer_role == "support" and juno_s >= 0.88 and juno_s >= wuy_s - 0.03:
            return "juno"
        ashe_s = _score_of(scores, keys, "ashe")
        wuy_s = _score_of(scores, keys, "wuyang")
        # Ashe's hat reads orange; do not promote Wuyang over a clearly better Ashe crop.
        if ashe_s >= 0.90 and ashe_s > wuy_s + 0.03:
            return "ashe"
        if prefer_role == "support" and orangefrac >= 0.70 and purplefrac < 0.10 and neonfrac < 0.08:
            return "wuyang"
    if key in ("kiriko", "mizuki", "wuyang"):
        if (
            prefer_role in (None, "support")
            and skinfrac >= 0.68
            and orangefrac >= 0.55
            and greenfrac < 0.12
            and cyanfrac < 0.10
            and neonfrac < 0.08
        ):
            return "wuyang"
        if redfrac >= 0.42 and top_rg > 22 and neonfrac < 0.08:
            return "kiriko"
        if teal and redfrac < 0.50:
            return "mizuki"
        if greenfrac >= 0.14:
            return "mizuki"

    def close_enough(other: str) -> bool:
        other_s = _score_of(scores, keys, other)
        self_s = _score_of(scores, keys, key)
        if other_s < 0 or self_s < 0:
            return True
        return other_s >= self_s - 0.12

    # TAB tint used to turn Emre into Anran/Hanzo even when Emre cosine led.
    if prefer_role == "damage" and key in ("anran", "hanzo", "mauga", "freja", "hazard", "shion", "ashe"):
        emre_s = _score_of(scores, keys, "emre")
        ashe_s = _score_of(scores, keys, "ashe")
        self_s = _score_of(scores, keys, key)
        if emre_s >= 0.90 and emre_s >= self_s - 0.01 and emre_s >= ashe_s - 0.02:
            return "emre"
        if key == "anran" and ashe_s >= 0.90 and ashe_s >= emre_s - 0.015:
            return "ashe"

    # Role-queue TAB is tank / dps / dps / support / support.
    # In-game Emre icons are warm orange; only rewrite Mauga when Emre is close
    # or the crop itself is orange (preserve a real tank-slot Mauga).
    if prefer_role == "tank" and key in ("emre", "wuyang", "mercy", "juno", "hazard"):
        mauga_s = _score_of(scores, keys, "mauga")
        self_s = _score_of(scores, keys, key)
        if mauga_s >= 0.93 and mauga_s >= self_s + 0.008:
            return "mauga"
        tank = max(
            (
                ("wrecking-ball", _score_of(scores, keys, "wrecking-ball")),
                ("sigma", _score_of(scores, keys, "sigma")),
                ("mauga", _score_of(scores, keys, "mauga")),
                ("hazard", _score_of(scores, keys, "hazard")),
                ("orisa", _score_of(scores, keys, "orisa")),
                ("dva", _score_of(scores, keys, "dva")),
                ("winston", _score_of(scores, keys, "winston")),
            ),
            key=lambda z: z[1],
        )
        if tank[1] > 0:
            return tank[0]
    if prefer_role == "tank" and key in ("sigma", "hazard") and purplefrac < 0.10 and cyanfrac >= 0.10:
        if close_enough("sigma"):
            return "sigma"
    if prefer_role == "damage" and key in ("wuyang", "juno", "mercy"):
        dps = max(
            (
                ("ashe", _score_of(scores, keys, "ashe")),
                ("emre", _score_of(scores, keys, "emre")),
                ("genji", _score_of(scores, keys, "genji")),
                ("sojourn", _score_of(scores, keys, "sojourn")),
                ("cassidy", _score_of(scores, keys, "cassidy")),
                ("venture", _score_of(scores, keys, "venture")),
            ),
            key=lambda z: z[1],
        )
        if dps[1] > 0:
            return dps[0]
    if prefer_role == "damage" and key == "mauga" and (orangefrac >= 0.12 or close_enough("emre")):
        return "emre"
    if key in ("mauga", "emre") and prefer_role is None:
        if orangefrac >= 0.16:
            return "emre"
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


def _complete_tab_rows(rows: list[dict], h: int) -> list[dict]:
    """If the red table is faint, rebuild it from the blue table's row spacing."""
    ordered = [r for r in sorted(rows, key=lambda z: z["y0"]) if r["y1"] < int(h * 0.90)]
    if len(ordered) < 4:
        return ordered
    if len(ordered) >= 8:
        gaps = [(ordered[i + 1]["y0"] - ordered[i]["y1"], i) for i in range(len(ordered) - 1)]
        gap, idx = max(gaps)
        heights = [r["y1"] - r["y0"] for r in ordered]
        med_h = sorted(heights)[len(heights) // 2]
        if gap > max(12, 0.55 * med_h):
            top, bottom = ordered[: idx + 1], ordered[idx + 1 :]
        else:
            top, bottom = [r for r in ordered if r["y1"] < int(h * 0.52)], [
                r for r in ordered if r["y0"] >= int(h * 0.52)
            ]
    elif len(ordered) >= 6:
        gaps = [(ordered[i + 1]["y0"] - ordered[i]["y1"], i) for i in range(len(ordered) - 1)]
        gap, idx = max(gaps)
        heights = [r["y1"] - r["y0"] for r in ordered]
        med_h = sorted(heights)[len(heights) // 2]
        if gap > max(12, 0.55 * med_h):
            top, bottom = ordered[: idx + 1], ordered[idx + 1 :]
        else:
            top, bottom = [r for r in ordered if r["y1"] < int(h * 0.52)], [
                r for r in ordered if r["y0"] >= int(h * 0.52)
            ]
    else:
        # 4–5 rows: almost always the ally table only (red rows vanish on dark maps).
        top, bottom = ordered[:5], []
    top = sorted(top, key=lambda z: z["y0"])[:5]
    if len(top) < 4:
        return ordered
    heights = [r["y1"] - r["y0"] for r in top]
    med_h = sorted(heights)[len(heights) // 2]
    centers = [(r["y0"] + r["y1"]) / 2 for r in top]
    if len(centers) < 2:
        return ordered
    spacing = float(np.median(np.diff(np.array(centers))))
    if spacing < 16:
        return ordered
    bot_centers = [(r["y0"] + r["y1"]) / 2 for r in sorted(bottom, key=lambda z: z["y0"])]
    bot_ok = False
    if len(bot_centers) >= 5:
        gaps = np.diff(np.array(bot_centers[:5]))
        bot_ok = bool(np.all(np.abs(gaps - spacing) < spacing * 0.35))
    if bot_ok:
        return ordered
    last_cy = centers[-1]
    start_cy = last_cy + 2 * spacing
    extra: list[dict] = []
    for i in range(5):
        cy = start_cy + i * spacing
        if cy > h * 0.90:
            break
        extra.append(
            {
                "y0": int(cy - med_h / 2),
                "y1": int(cy + med_h / 2),
                "team": "enemy",
                "lum": 0.0,
            }
        )
    return sorted(top + extra, key=lambda z: z["y0"])


def _has_tab_gap(rows: list[dict]) -> bool:
    if len(rows) < 8:
        return False
    ordered = sorted(rows, key=lambda z: z["y0"])
    gaps = [ordered[i + 1]["y0"] - ordered[i]["y1"] for i in range(len(ordered) - 1)]
    med = sorted(gaps)[len(gaps) // 2]
    return max(gaps) > max(18, 1.5 * (med + 1))


def _row_set_quality(rows: list[dict]) -> int:
    n = len(rows)
    if n == 10:
        return 100
    if n in (8, 9, 11):
        return 70 + n
    if n in (5, 6, 7):
        return 40 + n
    return n


def _similar_height_rows(rows: list[dict]) -> list[dict]:
    if len(rows) < 3:
        return rows
    heights = sorted(r["y1"] - r["y0"] for r in rows)
    med = heights[len(heights) // 2]
    kept = [r for r in rows if 0.50 * med <= (r["y1"] - r["y0"]) <= 1.70 * med]
    return kept or rows


def _assign_row_teams(rows: list[dict]) -> list[dict]:
    rows = sorted(rows, key=lambda z: z["y0"])
    if len(rows) >= 8:
        gaps = [(rows[i + 1]["y0"] - rows[i]["y1"], i) for i in range(len(rows) - 1)]
        _gap, idx = max(gaps)
        for i, row in enumerate(rows):
            row["team"] = "ally" if i <= idx else "enemy"
        return rows
    for row in rows:
        if row.get("team") in ("ally", "enemy"):
            continue
        row["team"] = "ally"
    return rows


def _variance_rows(arr: np.ndarray, x0: int, x1: int) -> list[dict]:
    """Find TAB rows from nameplate luminance plateaus (works through transparent overlays)."""
    h, w, _ = arr.shape
    px0 = max(int(w * 0.20), min(x0, int(w * 0.20)))
    px1 = min(w, max(px0 + 48, int(w * 0.70)))
    plate = arr[:, px0:px1].astype(np.float32).mean(axis=(1, 2))
    k = max(7, (int(h * 0.010) | 1))
    sm = np.convolve(plate, np.ones(k, dtype=np.float32) / k, mode="same")
    lo, hi_y = int(h * 0.12), int(h * 0.90)
    band = sm[lo:hi_y]
    if band.size < 20:
        return []
    base = float(np.percentile(band, 30))
    mask = np.zeros(h, dtype=bool)
    mask[lo:hi_y] = band > (base + 3.0)
    min_h = max(12, int(h * 0.018))
    rows = _merge_mask_bands(mask, sm, "unknown", min_h)
    rows = [row for row in rows if row["y1"] - row["y0"] <= int(h * 0.12)]
    return _similar_height_rows(rows)


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
    goldish = (r > 50) & (g > 40) & (np.abs(r - g) < 52) & ((r + g) > b * 1.25) & (lum > 36)
    red = (r > b + 7) & (r > 32) & (lum > 22) & ~goldish & ~blue
    gold = goldish & ~blue
    color_rows = (
        _merge_mask_bands(blue, lum, "ally", min_h)
        + _merge_mask_bands(red, lum, "enemy", min_h)
        + _merge_mask_bands(gold, lum, "ally", min_h)
    )
    color_rows.sort(key=lambda z: z["y0"])
    cleaned = []
    for row in color_rows:
        if cleaned and row["y0"] - cleaned[-1]["y1"] < 4 and row["team"] == cleaned[-1]["team"]:
            cleaned[-1]["y1"] = row["y1"]
            cleaned[-1]["lum"] = max(cleaned[-1]["lum"], row["lum"])
        else:
            cleaned.append(row)
    color_rows = [row for row in cleaned if row["y1"] - row["y0"] <= int(h * 0.14)]
    color_rows = _similar_height_rows(color_rows)

    var_rows = _variance_rows(arr, max(0, x0 - int((x1 - x0) * 0.15)), x1)
    if (
        _row_set_quality(color_rows) >= _row_set_quality(var_rows)
        and len(color_rows) >= 8
        and _has_tab_gap(color_rows)
    ):
        rows = color_rows
    else:
        rows = var_rows
        rows = _assign_row_teams(rows)
    return _complete_tab_rows(rows, h)


def _trim_hud(arr: np.ndarray) -> np.ndarray:
    """Drop the in-game ability bar / self portrait under a full-screen TAB shot."""
    h, w, _ = arr.shape
    if h < 200:
        return arr
    bot = arr[int(h * 0.88) :]
    left = arr[int(h * 0.86) :, : int(w * 0.28)]
    if bot.size == 0 or left.size == 0:
        return arr
    chroma = float(bot.astype(np.float32).std())
    mean = float(bot.astype(np.float32).mean())
    if chroma > 34 and mean > 26 and float(left.astype(np.float32).std()) > 30:
        return arr[: int(h * 0.84)]
    return arr


def _select_tab_hits(hits: list[dict]) -> list[dict]:
    """Keep the regularly spaced 5+5 TAB column; drop HUD / career-stat portraits."""
    if len(hits) < 4:
        return hits
    ordered = sorted(hits, key=lambda z: z["cy"])
    ys = [h["cy"] for h in ordered]
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    if gaps:
        body = gaps[:-1] or gaps
        med = sorted(body)[len(body) // 2]
        while len(ordered) >= 6 and gaps and gaps[-1] > max(36, 1.8 * (med + 1)):
            ordered = ordered[:-1]
            ys = [h["cy"] for h in ordered]
            gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
            body = gaps[:-1] or gaps
            med = sorted(body)[len(body) // 2] if body else med
    if len(ordered) <= 10:
        return ordered
    ys = [h["cy"] for h in ordered]
    gaps = [(ys[i + 1] - ys[i], i) for i in range(len(ys) - 1)]
    _gap, idx = max(gaps)
    top, bot = ordered[: idx + 1], ordered[idx + 1 :]
    if len(top) >= 4 and len(bot) >= 4:
        return top[:5] + bot[:5]
    return ordered[:5] + ordered[-5:]


def _dedupe_row_hits(hits: list[dict]) -> list[dict]:
    """One portrait per TAB row — JPEG can yield two peaks on the same circle."""
    if len(hits) < 2:
        return hits
    ordered = sorted(hits, key=lambda z: (z["cy"], -z["score"]))
    out: list[dict] = []
    for hit in ordered:
        if out and abs(hit["cy"] - out[-1]["cy"]) < max(10, 0.40 * max(hit["size"], out[-1]["size"])):
            if hit["score"] > out[-1]["score"]:
                out[-1] = hit
            continue
        out.append(hit)
    return out


def _keep_portrait_column(hits: list[dict], w: int) -> list[dict]:
    if len(hits) < 4:
        return hits
    bandwidth = max(24, int(w * 0.07))
    best: list[dict] = hits
    best_n = 0
    for seed in hits:
        group = [h for h in hits if abs(h["cx"] - seed["cx"]) <= bandwidth]
        if len(group) > best_n:
            best, best_n = group, len(group)
    return sorted(best, key=lambda z: (z["cy"], z["cx"]))


def _dedupe_scoreboard_rows(rows: list[dict]) -> list[dict]:
    """Two nameplate scans can yield the same TAB row a few pixels apart (441 vs 439)."""
    if len(rows) < 2:
        return rows
    ordered = sorted(rows, key=lambda z: (z["y0"], -(z["y1"] - z["y0"])))
    out: list[dict] = []
    for row in ordered:
        cy = (row["y0"] + row["y1"]) / 2
        if out:
            prev = out[-1]
            pcy = (prev["y0"] + prev["y1"]) / 2
            overlap = min(prev["y1"], row["y1"]) - max(prev["y0"], row["y0"])
            min_h = min(prev["y1"] - prev["y0"], row["y1"] - row["y0"]) or 1
            if abs(cy - pcy) < 14 or overlap >= 0.40 * min_h:
                if (row["y1"] - row["y0"], row.get("lum") or 0) > (
                    prev["y1"] - prev["y0"],
                    prev.get("lum") or 0,
                ):
                    out[-1] = row
                continue
        out.append(row)
    return out


def _annotate_roles(rows: list[dict]) -> None:
    """Stamp role-queue slots. Prefer Y-order 5+5 so a gold self-row is not treated as the enemy tank."""
    ordered = sorted(rows, key=lambda z: z["y0"])
    top: list[dict] = []
    bot: list[dict] = []
    if len(ordered) >= 10:
        # Extra mid-table duplicates must not shift Ashe onto support.
        top, bot = ordered[:5], ordered[-5:]
    elif len(ordered) >= 8:
        gaps = [(ordered[i + 1]["y0"] - ordered[i]["y1"], i) for i in range(len(ordered) - 1)]
        _gap, idx = max(gaps)
        top, bot = ordered[: idx + 1][:5], ordered[idx + 1 :][:5]
    if top and bot:
        for group, team in ((top, "ally"), (bot, "enemy")):
            for i, row in enumerate(group):
                row["team"] = team
                row["prefer_role"] = ROLE_QUEUE[i]
        return
    by_team: dict[str, list[dict]] = {}
    for row in ordered:
        by_team.setdefault(row["team"], []).append(row)
    for team_rows in by_team.values():
        team_rows.sort(key=lambda z: z["y0"])
        if len(team_rows) < 3:
            continue
        for i, row in enumerate(team_rows[:5]):
            row["prefer_role"] = ROLE_QUEUE[i]


def _best_in_row(arr: np.ndarray, row: dict, x_lo: int, x_hi: int) -> dict | None:
    keys, mat, colors, csigs, roles = _templates()
    prefer = row.get("prefer_role")
    h, w, _ = arr.shape
    y0, y1 = row["y0"], row["y1"]
    band_h = y1 - y0
    if band_h < 18:
        return None
    if y0 < int(h * 0.10) or y1 > int(h * 0.92):
        return None
    from bot.engine import HEROES

    cands: list[dict] = []
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
            # Solid blue/red nameplate, not a portrait (Echo was winning Cassidy here).
            if csig.size > 7 and float(csig[7]) >= 0.85:
                continue
            scores = mat @ feat
            idx, score, second = _pick_key(scores, col, csig, keys, colors, csigs, roles, prefer)
            if score < 0.62:
                continue
            key = _force_confusions(keys[idx], csig, prefer, scores, keys)
            team, lum = _row_color(arr, x, y, size)
            if team == "unknown":
                team, lum = row["team"], row["lum"]
            cands.append(
                {
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
                    "role": (HEROES.get(key) or {}).get("role") or roles[idx],
                }
            )
    if not cands:
        return None

    def rank(hit: dict) -> tuple:
        # 0.16 used to let a small Wuyang crop beat a 0.99 Ashe on a mislabeled support row.
        role_bonus = 0.03 if prefer and hit.get("role") == prefer else 0.0
        fill_bonus = 0.02 * min(1.0, hit["size"] / max(band_h, 1))
        return (hit["score"] + role_bonus + fill_bonus, hit["margin"], hit["size"])

    return max(cands, key=rank)


def _merge_hits(primary: list[dict], extra: list[dict]) -> list[dict]:
    picked = list(primary)
    for hit in extra:
        overlap = False
        for prev in picked:
            dy = abs(hit["cy"] - prev["cy"])
            dx = abs(hit["cx"] - prev["cx"])
            lim = 0.65 * min(hit["size"], prev["size"])
            if dy * dy + dx * dx < lim * lim:
                overlap = True
                break
        if not overlap:
            picked.append(hit)
    picked.sort(key=lambda z: (z["cy"], z["cx"]))
    return picked


def _match_peaks(arr: np.ndarray) -> list[dict]:
    """If colored rows fail, match portraits along high-texture peaks in the left column."""
    h, w, _ = arr.shape
    x0, x1 = int(w * 0.08), int(w * 0.28)
    var_rows = _variance_rows(arr, x0, x1)
    var_rows = _dedupe_scoreboard_rows(var_rows)
    var_rows = _assign_row_teams(var_rows)
    _annotate_roles(var_rows)
    picked: list[dict] = []
    px0, px1 = int(w * 0.10), int(w * 0.24)
    for row in var_rows:
        hit = _best_in_row(arr, row, px0, px1)
        if hit:
            picked.append(hit)
    return picked


def _match_portraits(arr: np.ndarray) -> list[dict]:
    h, w, _ = arr.shape
    # Full-screen TAB: portraits are on the LEFT of the overlay.
    # Do not scan the right half first — career stats portraits live there.
    regions = [
        (int(w * 0.10), int(w * 0.50)),
        (int(w * 0.08), int(w * 0.72)),
    ]
    unique_rows: list[dict] = []
    for rx0, rx1 in regions:
        unique_rows.extend(_scoreboard_rows(arr, rx0, rx1))
    unique_rows = _dedupe_scoreboard_rows(unique_rows)
    _annotate_roles(unique_rows)
    px0, px1 = int(w * 0.10), int(w * 0.24)
    picked: list[dict] = []
    labeled = sum(1 for row in unique_rows if row.get("prefer_role"))
    for row in unique_rows:
        if labeled >= 10 and row.get("prefer_role") is None:
            continue
        hit = _best_in_row(arr, row, px0, px1)
        if hit:
            picked.append(hit)
    if len(picked) < 6:
        picked = _merge_hits(picked, _match_peaks(arr))
    picked = [hit for hit in picked if 0.10 * h <= hit["cy"] <= 0.86 * h]
    picked = _keep_portrait_column(picked, w)
    picked = _dedupe_row_hits(picked)
    picked = _select_tab_hits(picked)
    picked.sort(key=lambda z: (z["cy"], z["cx"]))
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
    # Role-queue TAB is always 5 allies on top, 5 enemies on bottom.
    if len(top) >= 4 and len(bottom) >= 4:
        return [h["key"] for h in top[:5]], [h["key"] for h in bottom[:5]], "tab"
    if len(hits) >= 8:
        ordered = sorted(hits, key=lambda z: z["cy"])
        cut = 5 if len(ordered) >= 10 else len(ordered) // 2
        return [h["key"] for h in ordered[:cut]], [h["key"] for h in ordered[cut:cut + 5]], "tab"
    allies = [h for h in hits if h["team"] == "ally"]
    enemies = [h for h in hits if h["team"] == "enemy"]
    if len(allies) >= 2 and len(enemies) >= 2:
        return [h["key"] for h in allies], [h["key"] for h in enemies], "color"
    cy_span = max(h["cy"] for h in hits) - min(h["cy"] for h in hits)
    if len(left) >= 2 and len(right) >= 2 and cy_span < 90:
        return [h["key"] for h in left], [h["key"] for h in right], "columns"
    if enemies and not allies:
        return [], [h["key"] for h in enemies][:5], "color"
    if allies and not enemies:
        return [h["key"] for h in allies][:5], [], "color"
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


def _board_score(board: dict | None) -> int:
    if not board:
        return -1
    enemies = min(5, len(board.get("enemies") or []))
    allies = min(5, len(board.get("allies") or []))
    if enemies < 4:
        return enemies
    return allies + enemies * 2


def read_scoreboard(data: bytes) -> dict:
    api = None
    try:
        from bot.vision_api import read_with_api

        api = read_with_api(data)
    except Exception:
        api = None
    img = Image.open(io.BytesIO(data))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (12, 14, 18))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    work = _resize_max(img)
    arr = _trim_hud(np.asarray(work))
    hits = _match_portraits(arr)
    allies, enemies, layout = _assign_teams(hits)
    # Keep at most 5 per side, in board order. Same hero can appear on both teams.
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
    local = {
        "allies": allies,
        "enemies": enemies,
        "self_key": self_key,
        "role": role,
        "map_key": map_key,
        "layout": layout,
        "ocr_text": ocr,
        "hits": hits,
    }
    if _board_score(api) > _board_score(local):
        return api
    return local


def render_tab_fixture(
    allies: list[str],
    enemies: list[str],
    map_title: str = "ROUTE 66",
    self_key: str | None = None,
    size: tuple[int, int] = (1920, 1080),
    realistic: bool = False,
    hud: bool = False,
    interior: bool = False,
) -> Image.Image:
    """Synthetic TAB scoreboard used by tests (top blue / bottom red / circular icons)."""
    w, h = size
    if interior:
        base = Image.new("RGB", (w, h), (28, 22, 18))
        shade = ImageDraw.Draw(base)
        shade.rectangle((0, int(h * 0.35), w, int(h * 0.78)), fill=(16, 14, 12))
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.rectangle((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), fill=(8, 10, 14, 110))
    elif realistic:
        bg_path = ROOT / "assets" / "maps" / "route-66.jpg"
        if bg_path.exists():
            base = Image.open(bg_path).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
        else:
            base = Image.new("RGB", (w, h), (186, 118, 62))
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        panel_a = 170
        draw.rectangle((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), fill=(8, 10, 14, panel_a))
    else:
        base = Image.new("RGB", (w, h), (18, 22, 28))
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.rectangle((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), fill=(8, 10, 14, 230))

    draw.text((int(w * 0.72), int(h * 0.04)), "エスコート", fill=(220, 220, 220, 255))
    draw.text((int(w * 0.72), int(h * 0.07)), map_title, fill=(240, 200, 80, 255))
    draw.text((int(w * 0.72), int(h * 0.10)), "時間 : 6:28", fill=(200, 200, 200, 255))

    row_alpha = 88 if interior else (125 if realistic else 255)

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
            draw.rectangle((int(w * 0.12), y + 6, int(w * 0.88), y + row_h - 6), fill=bg + (row_alpha,))

    paint(allies, 0.16, 0.48, (32, 58, 110), self_key)
    draw.text((int(w * 0.48), int(h * 0.49)), "VS", fill=(230, 230, 230, 255))
    paint(enemies, 0.54, 0.86, (110, 36, 36), None)

    img = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")

    def paste_portraits(keys: list[str], y0: float, y1: float):
        rows = max(1, len(keys))
        top = int(h * y0)
        bot = int(h * y1)
        row_h = (bot - top) // rows
        for i, key in enumerate(keys):
            y = top + i * row_h
            port = Image.open(PORTRAIT_DIR / f"{key}.png").convert("RGBA")
            d = int(row_h * 0.86)
            port = port.resize((d, d), Image.Resampling.LANCZOS)
            circ = Image.new("L", (d, d), 0)
            ImageDraw.Draw(circ).ellipse((1, 1, d - 2, d - 2), fill=255)
            port.putalpha(circ)
            x = int(w * 0.14)
            img.paste(port, (x, y + (row_h - d) // 2), port)

    paste_portraits(allies, 0.16, 0.48)
    paste_portraits(enemies, 0.54, 0.86)
    if hud:
        bar = ImageDraw.Draw(img)
        bar.rectangle((0, int(h * 0.86), w, h), fill=(18, 22, 28))
        me = self_key or (allies[-1] if allies else "ana")
        port = Image.open(PORTRAIT_DIR / f"{me}.png").convert("RGBA")
        d = int(h * 0.11)
        port = port.resize((d, d), Image.Resampling.LANCZOS)
        circ = Image.new("L", (d, d), 0)
        ImageDraw.Draw(circ).ellipse((1, 1, d - 2, d - 2), fill=255)
        port.putalpha(circ)
        img.paste(port, (int(w * 0.04), int(h * 0.875)), port)
        for i, key in enumerate((allies[2:5] or allies)[:3]):
            mini = Image.open(PORTRAIT_DIR / f"{key}.png").convert("RGB")
            s = int(h * 0.05)
            mini = mini.resize((s, s), Image.Resampling.LANCZOS)
            img.paste(mini, (int(w * 0.80), int(h * 0.70) + i * int(s * 1.2)))
        for i in range(4):
            x0 = int(w * 0.42) + i * int(h * 0.06)
            y0 = int(h * 0.90)
            bar.rectangle((x0, y0, x0 + int(h * 0.045), y0 + int(h * 0.045)), fill=(80, 180, 90) if i == 0 else (70, 90, 160))
    return img

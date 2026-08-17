/* Anti-pick recommendation engine */
(function () {
  const OW = window.OW;
  const ROLE_ORDER = { tank: 0, damage: 1, support: 2 };

  function heroByKey(key) {
    return OW.heroes.find((h) => h.key === key);
  }

  function mapByKey(key) {
    return OW.maps.find((m) => m.key === key);
  }

  function explicitCounter(attacker, target) {
    const row = OW.matchups[attacker];
    if (!row) return 0;
    return row[target] || 0;
  }

  function tagCounter(attacker, target) {
    let best = 0;
    let hits = [];
    const aTags = new Set(attacker.tags);
    const bTags = new Set(target.tags);
    for (const rule of OW.tagMatchups) {
      if (aTags.has(rule.a) && bTags.has(rule.b)) {
        if (rule.score >= best) {
          best = rule.score;
          hits.push(rule);
        }
      }
    }
    return { score: best, rules: hits.filter((r) => r.score >= 3) };
  }

  function detectComposition(enemyKeys) {
    const heroes = enemyKeys.map(heroByKey).filter(Boolean);
    const counts = {
      dive: 0,
      poke: 0,
      brawl: 0,
      bunker: 0,
      flying: 0,
      sniper: 0,
      flank: 0,
    };
    for (const h of heroes) {
      const t = new Set(h.tags);
      if (t.has("dive") || t.has("flank")) counts.dive += t.has("dive") ? 2 : 1;
      if (t.has("poke") || t.has("sniper") || t.has("long-range")) counts.poke += 1;
      if (t.has("brawl") || t.has("melee")) counts.brawl += 1;
      if (t.has("bunker") || t.has("turret")) counts.bunker += 2;
      if (t.has("flyer")) counts.flying += 2;
      if (t.has("sniper")) counts.sniper += 2;
      if (t.has("flank")) counts.flank += 1;
    }
    if (heroes.some((h) => h.tags.includes("flyer")) && heroes.some((h) => h.tags.includes("flyer-synergy"))) {
      counts.flying += 3;
    }
    const ranked = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const primary = ranked[0][1] > 0 ? ranked[0][0] : "flex";
    const secondary = ranked[1] && ranked[1][1] > 0 ? ranked[1][0] : null;
    return { counts, primary, secondary, heroes };
  }

  const COMP_LABEL = {
    dive: { ja: "ダイブ", en: "Dive" },
    poke: { ja: "ポーク", en: "Poke" },
    brawl: { ja: "ブロウル", en: "Brawl" },
    bunker: { ja: "バンカー", en: "Bunker" },
    flying: { ja: "空中", en: "Flying" },
    sniper: { ja: "スナイプ", en: "Sniper" },
    flank: { ja: "フランカー", en: "Flank" },
    flex: { ja: "ミックス", en: "Mix" },
  };

  const COMP_ANSWERS = {
    dive: {
      tank: ["orisa", "roadhog", "zarya", "dmon"],
      damage: ["cassidy", "mei", "torbjorn", "reaper"],
      support: ["brigitte", "ana", "moira", "wuyang"],
    },
    poke: {
      tank: ["winston", "dva", "doomfist", "wrecking-ball"],
      damage: ["genji", "tracer", "sombra", "venture"],
      support: ["lucio", "kiriko", "juno"],
    },
    brawl: {
      tank: ["mauga", "zarya", "junker-queen", "orisa"],
      damage: ["reaper", "mei", "pharah", "bastion"],
      support: ["ana", "moira", "lucio", "kiriko"],
    },
    bunker: {
      tank: ["wrecking-ball", "winston", "hazard", "dva"],
      damage: ["sombra", "venture", "junkrat", "pharah"],
      support: ["lucio", "kiriko", "sombra"],
    },
    flying: {
      tank: ["dva", "sigma", "domina"],
      damage: ["ashe", "widowmaker", "cassidy", "soldier-76", "sojourn"],
      support: ["baptiste", "mizuki", "ana", "illari"],
    },
    sniper: {
      tank: ["winston", "dva", "wrecking-ball", "doomfist"],
      damage: ["genji", "tracer", "sombra", "winston"],
      support: ["lucio", "kiriko", "moira"],
    },
    flank: {
      tank: ["orisa", "zarya", "roadhog"],
      damage: ["cassidy", "torbjorn", "mei", "symmetra"],
      support: ["brigitte", "moira", "baptiste"],
    },
  };

  function mapAffinity(hero, map, side) {
    if (!map) return { score: 0, reasons: [] };
    const traits = new Set(map.traits || []);
    const tags = new Set(hero.tags);
    let score = 0;
    const reasons = [];

    const bump = (cond, pts, ja) => {
      if (cond) {
        score += pts;
        if (pts >= 2) reasons.push(ja);
      }
    };

    bump(traits.has("longsight") && (tags.has("sniper") || tags.has("hitscan") || tags.has("long-range")), 4, `${map.nameJa}は長視線。${hero.nameJa}の射程が刺さる`);
    bump(traits.has("choke") && (tags.has("barrier") || tags.has("spam") || tags.has("freeze") || tags.has("brawl")), 3, `チョークマップで${hero.nameJa}のエリア制御が強い`);
    bump(traits.has("vertical") && (tags.has("flyer") || tags.has("mobile") || hero.key === "winston" || hero.key === "juno" || hero.key === "dva"), 3, `高低差のある地形で機動力が活きる`);
    bump(traits.has("environmental") && (tags.has("boop") || hero.key === "lucio" || hero.key === "junkrat" || hero.key === "hazard" || hero.key === "pharah"), 3, `崖・井戸があり環境キルが取りやすい`);
    bump(traits.has("close") && (tags.has("brawl") || tags.has("melee") || tags.has("tankbuster") || tags.has("beam")), 3, `近接寄りのマップで近距離キットが強い`);
    bump(traits.has("open") && tags.has("flyer"), 2, `開放空間でフライヤーが通りやすい`);
    bump(traits.has("open") && tags.has("sniper"), 3, `開放マップでスナイプが通りやすい`);
    bump(traits.has("flank") && (tags.has("flank") || tags.has("dive")), 2, `側面ルートが多くダイブ／フランカー向き`);
    bump(traits.has("highground") && (tags.has("hitscan") || tags.has("poke") || tags.has("high-ground") || tags.has("flyer")), 2, `高所を取れるヒーロー`);
    bump(traits.has("control") && tags.has("speed"), 2, `コントロールは回転力とスピードが重要`);
    bump(traits.has("flashpoint") && (tags.has("mobile") || tags.has("speed") || tags.has("flank")), 3, `フラッシュポイントはローテ性能が勝つ`);
    bump(traits.has("clash") && (tags.has("brawl") || tags.has("melee") || tags.has("barrier")), 3, `クラッシュは超近接ブロウルが強い`);
    bump(traits.has("push") && (tags.has("speed") || tags.has("brawl") || tags.has("mobile")), 2, `プッシュはボット周辺の近接とスピード`);

    bump(traits.has("longsight") && tags.has("melee") && !tags.has("mobile"), -3, `${map.nameJa}の長視線は近接に厳しい`);
    bump(traits.has("close") && tags.has("sniper"), -3, `近接マップでスナイパーは価値が落ちる`);
    bump(traits.has("choke") && tags.has("flyer"), -1, `閉鎖チョークでは空が取りにくい`);

    if (side === "attack" && (tags.has("dive") || tags.has("flank") || tags.has("speed"))) {
      score += 1;
    }
    if (side === "defend" && (tags.has("bunker") || tags.has("barrier") || tags.has("turret") || tags.has("sniper"))) {
      score += 1;
    }
    return { score, reasons };
  }

  function threatFrom(enemy, candidate) {
    const direct = explicitCounter(enemy.key, candidate.key);
    const tagged = tagCounter(enemy, candidate);
    return Math.max(direct, tagged.score * 0.7);
  }

  function powerAgainst(candidate, enemy) {
    const direct = explicitCounter(candidate.key, enemy.key);
    const tagged = tagCounter(candidate, enemy);
    const score = Math.max(direct, tagged.score);
    return { score, direct, rules: tagged.rules };
  }

  function recommend(state) {
    const myRole = state.myRole || "damage";
    const enemies = (state.enemies || []).map(heroByKey).filter(Boolean);
    const allies = (state.allies || []).map(heroByKey).filter(Boolean);
    const taken = new Set([...enemies.map((h) => h.key), ...allies.map((h) => h.key)]);
    const map = state.mapKey ? mapByKey(state.mapKey) : null;
    const side = state.side || "flex";
    const comp = detectComposition(enemies.map((h) => h.key));

    const answers = (COMP_ANSWERS[comp.primary] || {})[myRole] || [];

    const candidates = OW.heroes.filter((h) => h.role === myRole && !taken.has(h.key));

    const ranked = candidates.map((hero) => {
      let score = 24;
      const reasons = [];
      const vs = [];

      for (const enemy of enemies) {
        const hit = powerAgainst(hero, enemy);
        const threat = threatFrom(enemy, hero);
        const delta = hit.score * 4.6 - threat * 3.4;
        score += delta;
        vs.push({
          enemy: enemy.key,
          power: hit.score,
          threat,
          rules: hit.rules,
        });
        if (hit.score >= 4) {
          reasons.push(`${enemy.nameJa}に対して明確なカウンター`);
        } else if (hit.score >= 3) {
          const rule = hit.rules[0];
          reasons.push(rule ? `${enemy.nameJa}：${rule.ja}` : `${enemy.nameJa}との相性が良い`);
        }
        if (threat >= 4) {
          reasons.push(`注意：${enemy.nameJa}から強くカウンターされる`);
          score -= 2;
        }
      }

      if (answers.includes(hero.key)) {
        score += 6;
        reasons.push(`${COMP_LABEL[comp.primary].ja}構成への定番回答`);
      }

      const mapFit = mapAffinity(hero, map, side);
      score += mapFit.score * 1.6;
      reasons.push(...mapFit.reasons.slice(0, 2));

      if (comp.primary === "flying" && hero.tags.includes("hitscan")) {
        score += 5;
        reasons.push("空中構成にはヒットスキャンが最優先");
      }
      if (comp.counts.flying >= 2 && hero.tags.includes("hitscan")) {
        score += 6;
        reasons.push("フォマシー／空中にはヒットスキャン");
      }
      if (comp.primary === "dive" && (hero.tags.includes("anti-dive") || hero.tags.includes("cc") || hero.tags.includes("sleeper") || hero.tags.includes("anti-flank"))) {
        score += 4;
      }
      if (comp.primary === "sniper" && (hero.tags.includes("dive") || hero.tags.includes("flank"))) {
        score += 4;
        reasons.push("スナイパー裏を取るダイブ／フランカー");
      }

      const uniq = [];
      const seen = new Set();
      for (const r of reasons) {
        if (!seen.has(r)) {
          seen.add(r);
          uniq.push(r);
        }
      }

      return {
        hero,
        raw: score,
        reasons: uniq.slice(0, 4),
        vs,
        mapFit: mapFit.score,
      };
    });

    ranked.sort((a, b) => b.raw - a.raw);
    const topRaw = ranked[0] ? ranked[0].raw : 1;
    const floor = ranked.length ? ranked[Math.min(ranked.length - 1, 12)].raw : 0;
    for (const row of ranked) {
      const t = (row.raw - floor) / Math.max(8, topRaw - floor);
      row.score = Math.round(Math.max(12, Math.min(99, 28 + t * 71)));
    }

    const weaknesses = [];
    if (comp.primary === "flying") weaknesses.push({ ja: "ヒットスキャン不足だと空に試合を支配される", en: "Without hitscan, flyers own the sky" });
    if (comp.primary === "dive") weaknesses.push({ ja: "CC・アンチダイブがないとバックラインが溶ける", en: "No peel means the backline dies" });
    if (comp.primary === "brawl") weaknesses.push({ ja: "アンチヒールと頭上火力でブロウルは崩せる", en: "Anti-heal and high ground break brawl" });
    if (comp.primary === "poke") weaknesses.push({ ja: "接近され情報と距離を失うとポークは負ける", en: "Poke loses if you close the gap" });
    if (comp.primary === "bunker") weaknesses.push({ ja: "ハック・地中・頭上でバンカーは崩壊する", en: "Hack, burrow, and air collapse bunker" });
    if (comp.primary === "sniper") weaknesses.push({ ja: "遮蔽とダイブでスナイパーを沈黙させられる", en: "Cover and dive mute snipers" });

    return {
      comp,
      compLabel: COMP_LABEL[comp.primary] || COMP_LABEL.flex,
      weaknesses,
      picks: ranked.slice(0, 5),
      avoid: ranked.slice(-3).reverse(),
      map,
    };
  }

  function analyzeScreenshotText(text) {
    if (!text) return { mapKey: null, heroKeys: [] };
    const lower = text.toLowerCase().replace(/[’']/g, "'");
    let mapKey = null;
    let bestLen = 0;
    for (const m of OW.maps) {
      for (const n of [m.name, m.nameJa, m.key.replace(/-/g, " ")]) {
        const needle = String(n).toLowerCase();
        if (needle.length >= 4 && lower.includes(needle) && needle.length > bestLen) {
          mapKey = m.key;
          bestLen = needle.length;
        }
      }
    }
    const heroKeys = [];
    const names = [];
    for (const h of OW.heroes) {
      names.push([h.key, h.name.toLowerCase()]);
      names.push([h.key, h.nameJa.toLowerCase()]);
      names.push([h.key, h.key.replace(/-/g, " ")]);
      names.push([h.key, h.name.toLowerCase().replace(/[:']/g, "")]);
    }
    names.sort((a, b) => b[1].length - a[1].length);
    const used = new Set();
    for (const [key, name] of names) {
      if (used.has(key)) continue;
      if (name.length < 3) continue;
      if (lower.includes(name)) {
        heroKeys.push(key);
        used.add(key);
      }
    }
    return { mapKey, heroKeys };
  }

  window.Engine = {
    heroByKey,
    mapByKey,
    detectComposition,
    recommend,
    analyzeScreenshotText,
    COMP_LABEL,
    ROLE_ORDER,
  };
})();

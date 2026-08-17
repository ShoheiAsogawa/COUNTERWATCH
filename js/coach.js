/* Coaching copy: map walk, CDs, how to move — web app, not Discord */
(function () {
  const OW = window.OW;

  function heroName(h, lang) {
    return lang === "en" ? h.name : h.nameJa;
  }

  function mapName(m, lang) {
    return lang === "en" ? m.name : m.nameJa;
  }

  function abilityLine(ab, lang) {
    const n = lang === "en" ? ab.name : ab.nameJa;
    return ab.cd ? `${n} ${ab.cd}` : n;
  }

  function trackCds(heroes, lang) {
    const lines = [];
    for (const h of heroes) {
      const bits = (h.abilities || [])
        .filter((a) => a.cd && a.cd !== "no CD" && a.cd !== "hold" && a.cd !== "weapon" && a.cd !== "refresh")
        .slice(0, 3)
        .map((a) => abilityLine(a, lang));
      const ult = h.ult && h.ult.nameJa ? (lang === "en" ? h.ult.name : h.ult.nameJa) : "";
      if (bits.length) lines.push(`${heroName(h, lang)}：${bits.join(" / ")}${ult ? ` / ${ult}` : ""}`);
    }
    return lines.slice(0, 6);
  }

  function movementForPick(hero, map, rec, state, lang) {
    const ja = lang !== "en";
    const lines = [];
    const coach = map && map.coach;
    const side = state.side || "flex";
    if (coach) {
      if (side === "attack") lines.push(coach.attack);
      else if (side === "defend") lines.push(coach.defend);
      else lines.push(coach.move);
    }
    if (hero.play) lines.push(hero.play);
    const tags = new Set(hero.tags || []);
    const traits = new Set((map && map.traits) || []);
    if (rec.comp.primary === "flying" && tags.has("hitscan")) {
      lines.push(ja ? "空は真正面の真上ではなく、少し後ろの高い場所から撃つ。落ちたらすぐ次の箱へ。" : "Cut flyers from off-angle high ground, then relocate.");
    }
    if (rec.comp.primary === "dive" && (tags.has("anti-dive") || tags.has("sleeper") || tags.has("cc"))) {
      lines.push(ja ? "自分から前に出ない。飛び込まれた場所（回復役の横）で、スタンや眠りを待つ。" : "Don't walk up. Hold CC at the landing spot.");
    }
    if (rec.comp.primary === "brawl" && tags.has("antiheal")) {
      lines.push(ja ? "殴り合いが始まったら、まずタンクの足元に回復止めを入れる。" : "Dump anti-heal on the tank at the start of brawl.");
    }
    if (rec.comp.primary === "sniper" && (tags.has("dive") || tags.has("flank"))) {
      lines.push(ja ? "開けた道は歩かない。壁の裏から、高い場所のスナイパーへ回る。" : "Don't take the main. Wall-path onto the sniper perch.");
    }
    if (traits.has("environmental")) {
      lines.push(ja ? "端と穴を背にしない。内側の壁に沿って歩く。" : "Don't put pits at your back. Hug inner walls.");
    }
    if (traits.has("longsight") && tags.has("melee")) {
      lines.push(ja ? "このマップの本線は近接が溶ける。箱と建物で視線を切ってから着地。" : "Melee dies on this sightline. Break LOS with cover first.");
    }
    return lines.filter(Boolean).slice(0, 5);
  }

  function fightPlan(state, rec) {
    const ja = (state.lang || "ja") !== "en";
    const T = (OW.tactics || {});
    const me = rec.picks && rec.picks[0] && rec.picks[0].hero;
    if (!me) return null;
    const map = rec.map;
    const spots = (T.mapSpots && T.mapSpots[state.mapKey]) || T.defaultSpots || {};
    const home = (T.home && T.home[me.key]) || "cover";
    const side = state.side === "defend" ? "defend" : "attack";
    const where = (spots[home] && (spots[home][side] || spots[home].attack)) || "";
    const enemies = rec.comp.heroes || [];
    const ranked = [...enemies].sort((a, b) => danger(me, b) - danger(me, a));
    const threats = ranked.slice(0, 3).map((e) => {
      const row = (T.threats && T.threats[e.key]) || {};
      const text = row[me.role] || row.generic || "";
      return text ? `${ja ? e.nameJa : e.name}：${text}` : "";
    }).filter(Boolean);
    let combo = "";
    let bestN = 0;
    const have = new Set(enemies.map((h) => h.key));
    for (const row of T.combos || []) {
      const need = row.need || [];
      if (need.every((k) => have.has(k)) && need.length > bestN) {
        combo = row.ja || "";
        bestN = need.length;
      }
    }
    const stations = (spots.stations || []).slice(0, 3).map((st) => {
      const bit = st[side] || st.attack || "";
      return bit ? `${st.name} — ${bit}` : "";
    }).filter(Boolean);
    return {
      title: ja ? `${me.nameJa} × ${map ? map.nameJa : "このマップ"}` : `${me.name} on ${map ? map.name : "this map"}`,
      hero: me,
      where,
      stations,
      threats,
      combo,
      play: me.play || "",
      lose: ja ? "味方が揃う前に、開けた道へ出ない。" : "Don't walk the open main before you have numbers.",
    };
  }

  function danger(me, enemy) {
    const row = (OW.matchups || {})[enemy.key] || {};
    return row[me.key] || 0;
  }

  function compose(state, rec) {
    const lang = state.lang || "ja";
    const ja = lang !== "en";
    const map = rec.map;
    const pick = rec.picks && rec.picks[0];
    const enemies = rec.comp.heroes || [];
    const coach = map && map.coach;

    const mapBlock = {
      title: ja ? "マップの読み" : "Map read",
      name: map ? `${mapName(map, lang)}　${(ja ? map.modeJa : map.modes).join(" / ")}` : (ja ? "マップ未選択（汎用）" : "No map (generic)"),
      layout: coach ? coach.layout : (map ? map.noteJa : (ja ? "マップを選ぶと地形の話をします。" : "Pick a map for terrain notes.")),
      points: (coach && coach.points) || [],
      side: !map ? "" : state.side === "attack" ? coach.attack : state.side === "defend" ? coach.defend : coach.move,
    };

    const enemyNames = enemies.map((h) => heroName(h, lang)).join(" · ") || (ja ? "未入力" : "empty");
    const hole = rec.weaknesses[0] ? rec.weaknesses[0][lang] || rec.weaknesses[0].ja : "";

    const pickBlock = pick
      ? {
          hero: pick.hero,
          score: pick.score,
          reasons: pick.reasons,
          move: movementForPick(pick.hero, map, rec, state, lang),
          specs: [
            `HP ${pick.hero.hp}`,
            ja ? `射程 ${pick.hero.range}` : `range ${pick.hero.range}`,
            ...(pick.hero.abilities || []).filter((a) => a.cd).slice(0, 4).map((a) => abilityLine(a, lang)),
          ],
        }
      : null;

    return {
      map: mapBlock,
      enemy: {
        title: ja ? "敵の狙い" : "Their win condition",
        names: enemyNames,
        style: rec.compLabel[lang],
        hole,
        cds: trackCds(enemies, lang),
      },
      pick: pickBlock,
      fight: fightPlan(state, rec),
      alts: (rec.picks || []).slice(1, 4).map((p) => ({
        hero: p.hero,
        score: p.score,
        reason: p.reasons[0] || "",
      })),
    };
  }

  window.Coach = { compose, trackCds, fightPlan };
})();

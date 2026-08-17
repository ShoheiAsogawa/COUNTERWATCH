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
      lines.push(ja ? "空の軌道は本線の真上ではなく、やや後ろの高所から切る。落ちたらすぐ次の箱へ。" : "Cut flyers from off-angle high ground, then relocate.");
    }
    if (rec.comp.primary === "dive" && (tags.has("anti-dive") || tags.has("sleeper") || tags.has("cc"))) {
      lines.push(ja ? "自分から前に出ない。着地地点（サポの横）でCCを待つ。" : "Don't walk up. Hold CC at the landing spot.");
    }
    if (rec.comp.primary === "brawl" && tags.has("antiheal")) {
      lines.push(ja ? "最初のグレ／アンチをタンク足下に。近接の回復勝負を先に切る。" : "Dump anti-heal on the tank at the start of brawl.");
    }
    if (rec.comp.primary === "sniper" && (tags.has("dive") || tags.has("flank"))) {
      lines.push(ja ? "本線を歩かない。壁の裏から高所のスナイパーへ。" : "Don't take the main. Wall-path onto the sniper perch.");
    }
    if (traits.has("environmental")) {
      lines.push(ja ? "端と穴を背にしない。内側の壁に沿って歩く。" : "Don't put pits at your back. Hug inner walls.");
    }
    if (traits.has("longsight") && tags.has("melee")) {
      lines.push(ja ? "このマップの本線は近接が溶ける。箱と建物で視線を切ってから着地。" : "Melee dies on this sightline. Break LOS with cover first.");
    }
    return lines.filter(Boolean).slice(0, 5);
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
        title: ja ? "敵の勝ち筋" : "Their win condition",
        names: enemyNames,
        style: rec.compLabel[lang],
        hole,
        cds: trackCds(enemies, lang),
      },
      pick: pickBlock,
      alts: (rec.picks || []).slice(1, 4).map((p) => ({
        hero: p.hero,
        score: p.score,
        reason: p.reasons[0] || "",
      })),
    };
  }

  window.Coach = { compose, trackCds };
})();

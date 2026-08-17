/* COUNTERWATCH UI */
(function () {
  const state = {
    lang: "ja",
    myRole: "damage",
    mapKey: null,
    side: "flex",
    enemies: [],
    allies: [],
    enemyTeam: "auto",
    shot: null,
    detected: null,
    pickerRole: "all",
    query: "",
    visionReady: false,
  };

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  function t(ja, en) {
    return state.lang === "ja" ? ja : en;
  }

  function heroName(h) {
    return state.lang === "ja" ? h.nameJa : h.name;
  }

  function mapName(m) {
    return state.lang === "ja" ? m.nameJa : m.name;
  }

  function roleName(role) {
    const r = OW.roles.find((x) => x.key === role);
    return r ? (state.lang === "ja" ? r.nameJa : r.name) : role;
  }

  function save() {
    try {
      localStorage.setItem(
        "counterwatch",
        JSON.stringify({
          lang: state.lang,
          myRole: state.myRole,
          mapKey: state.mapKey,
          side: state.side,
        })
      );
    } catch (_) {}
  }

  function load() {
    try {
      const raw = localStorage.getItem("counterwatch");
      if (!raw) return;
      const s = JSON.parse(raw);
      Object.assign(state, s);
    } catch (_) {}
  }

  function setEnemy(key) {
    if (state.enemies.includes(key)) {
      state.enemies = state.enemies.filter((k) => k !== key);
    } else if (state.enemies.length < 5) {
      state.enemies = [...state.enemies, key];
    } else {
      state.enemies = [...state.enemies.slice(1), key];
    }
    render();
  }

  function clearEnemies() {
    state.enemies = [];
    render();
  }

  function setMap(key) {
    state.mapKey = state.mapKey === key ? null : key;
    save();
    render();
  }

  function render() {
    renderChrome();
    renderMaps();
    renderEnemy();
    renderPicks();
    renderFightPlan();
    renderPicker();
    renderShot();
  }

  function renderChrome() {
    $$("[data-role-btn]").forEach((btn) => {
      btn.classList.toggle("is-on", btn.dataset.roleBtn === state.myRole);
    });
    $$("[data-lang]").forEach((btn) => {
      btn.classList.toggle("is-on", btn.dataset.lang === state.lang);
    });
    $$("[data-side]").forEach((btn) => {
      btn.classList.toggle("is-on", btn.dataset.side === state.side);
    });
    document.documentElement.lang = state.lang === "ja" ? "ja" : "en";
    $("[data-i18n-sub]").textContent = t(
      "スクショを貼るだけで、今すぐ勝てるヒーローが分かる",
      "Paste the scoreboard. Get the counter in seconds."
    );
    $("[data-i18n-map]").textContent = t("マップ", "Map");
    $("[data-i18n-enemy]").textContent = t("敵の編成", "Enemy Comp");
    $("[data-i18n-picks]").textContent = t("今のアンチピック", "Anti-Picks Now");
    $("[data-i18n-picker]").textContent = t("ヒーローをタップして敵編成を入力", "Tap heroes to build the enemy team");
    $("[data-i18n-shot]").textContent = t("スコアボード／スタッツ画面をここに貼る", "Paste the stats / scoreboard screenshot here");
    $("[data-i18n-shot-hint]").textContent = t(
      "Ctrl+V またはドロップ。TAB画面・試合終了ボード両対応",
      "Ctrl+V or drop. Works with Tab and post-match boards"
    );
  }

  function renderMaps() {
    const q = (state.mapQuery || "").trim().toLowerCase();
    const maps = OW.maps.filter((m) => m.competitive);
    const extra = OW.maps.filter((m) => !m.competitive);
    const show = [...maps, ...extra].filter((m) => {
      if (!q) return m.competitive;
      return (
        m.name.toLowerCase().includes(q) ||
        m.nameJa.includes(q) ||
        m.key.includes(q) ||
        (m.modes || []).join(" ").includes(q)
      );
    });
    const grid = $("[data-map-grid]");
    grid.innerHTML = show
      .slice(0, q ? 40 : 24)
      .map((m) => {
        const on = state.mapKey === m.key;
        const bg = m.screenshot
          ? `style="background-image:url('${m.screenshot}')"`
          : "";
        return `<button class="map-card ${on ? "is-on" : ""}" data-map="${m.key}" title="${m.name}">
          <span class="map-card-bg" ${bg}></span>
          <span class="map-card-meta">
            <strong>${mapName(m)}</strong>
            <em>${(state.lang === "ja" ? m.modeJa : m.modes).join(" / ")}</em>
          </span>
        </button>`;
      })
      .join("");
    const selected = Engine.mapByKey(state.mapKey);
    const info = $("[data-map-info]");
    if (selected) {
      const traits = (selected.traits || [])
        .map((tr) => {
          const lab = OW.traitLabels[tr];
          return `<span class="chip">${lab ? t(lab.ja, lab.en) : tr}</span>`;
        })
        .join("");
      info.innerHTML = `<div class="map-note"><p>${selected.noteJa}</p><div class="chips">${traits}</div></div>`;
    } else {
      info.innerHTML = `<p class="muted">${t("マップ未選択。汎用カウンターを出します。", "No map selected. Showing generic counters.")}</p>`;
    }
  }

  function slotHtml(key, idx) {
    const h = key ? Engine.heroByKey(key) : null;
    if (!h) {
      return `<button class="hero-slot is-empty" data-empty-slot="${idx}">
        <span>${idx + 1}</span>
      </button>`;
    }
    return `<button class="hero-slot" data-remove="${h.key}" title="${heroName(h)}">
      <img src="${h.portrait}" alt="${h.name}">
      <em>${heroName(h)}</em>
    </button>`;
  }

  function renderEnemy() {
    const wrap = $("[data-enemy-slots]");
    const keys = [...state.enemies];
    while (keys.length < 5) keys.push(null);
    wrap.innerHTML = keys.map((k, i) => slotHtml(k, i)).join("");
    const rec = Engine.recommend(state);
    const banner = $("[data-comp-banner]");
    if (state.enemies.length === 0) {
      banner.innerHTML = `<strong>${t("敵を5人入れるか、スクショを貼ってください", "Add 5 enemies or paste a screenshot")}</strong>`;
    } else {
      banner.innerHTML = `<span class="comp-tag">${rec.compLabel[state.lang]}</span>
        <strong>${t("敵の勝ち筋", "Their win condition")}</strong>
        <span>${(rec.weaknesses[0] && rec.weaknesses[0][state.lang]) || t("構成の穴を突く", "Punish the holes in this comp")}</span>`;
    }
  }

  function renderFightPlan() {
    const box = $("[data-fight-plan]");
    if (!box) return;
    if (!state.enemies.length) {
      box.innerHTML = "";
      return;
    }
    const rec = Engine.recommend(state);
    const plan = Coach.fightPlan(state, rec);
    if (!plan) {
      box.innerHTML = "";
      return;
    }
    const stations = (plan.stations || []).map((s) => `<li>${s}</li>`).join("");
    const threats = (plan.threats || []).map((s) => `<li>${s}</li>`).join("");
    box.innerHTML = `
      <h3>${t("こう戦え", "Fight plan")} — ${plan.title}</h3>
      ${plan.where ? `<p><strong>${t("今いる場所", "Stand here")}</strong> ${plan.where}</p>` : ""}
      ${stations ? `<ul>${stations}</ul>` : ""}
      ${plan.combo ? `<p><strong>${t("この組み合わせ", "This combo")}</strong> ${plan.combo}</p>` : ""}
      ${threats ? `<p><strong>${t("相手のピックへの返し", "Answers")}</strong></p><ul>${threats}</ul>` : ""}
      ${plan.play ? `<p>${plan.play}</p>` : ""}
    `;
  }

  function renderPicks() {
    const box = $("[data-picks]");
    if (!state.enemies.length) {
      box.innerHTML = `<div class="empty-picks">
        <div class="pulse-ring"></div>
        <p>${t("編成が入ると、0.1秒でアンチピックが出ます", "Counters appear the instant a comp is set")}</p>
      </div>`;
      return;
    }
    const rec = Engine.recommend(state);
    box.innerHTML = rec.picks
      .map((p, i) => {
        const h = p.hero;
        const reasons = p.reasons
          .map((r) => `<li>${r}</li>`)
          .join("");
        return `<article class="pick-card ${i === 0 ? "is-top" : ""}">
          <div class="pick-rank">${String(i + 1).padStart(2, "0")}</div>
          <div class="pick-portrait">
            <img src="${h.portrait}" alt="${h.name}">
          </div>
          <div class="pick-body">
            <header>
              <h3>${heroName(h)}</h3>
              <span class="role-pill role-${h.role}">${roleName(h.role)}</span>
              <span class="score">${p.score}</span>
            </header>
            <p class="ult">${t("アルティメット", "Ultimate")}: ${state.lang === "ja" ? h.ult.nameJa : h.ult.name}</p>
            <ul>${reasons}</ul>
          </div>
        </article>`;
      })
      .join("");
  }

  function renderPicker() {
    const q = state.query.trim().toLowerCase();
    const list = OW.heroes.filter((h) => {
      if (state.pickerRole !== "all" && h.role !== state.pickerRole) return false;
      if (!q) return true;
      return (
        h.name.toLowerCase().includes(q) ||
        h.nameJa.includes(q) ||
        h.key.includes(q) ||
        h.tags.some((t) => t.includes(q))
      );
    });
    const grouped = { tank: [], damage: [], support: [] };
    for (const h of list) grouped[h.role].push(h);
    const mount = $("[data-hero-grid]");
    mount.innerHTML = Object.entries(grouped)
      .filter(([, arr]) => arr.length)
      .map(([role, arr]) => {
        return `<div class="picker-group">
          <h4>${roleName(role)}</h4>
          <div class="picker-row">
            ${arr
              .map((h) => {
                const on = state.enemies.includes(h.key);
                return `<button class="hex ${on ? "is-on" : ""}" data-pick="${h.key}" title="${heroName(h)}">
                  <img src="${h.portrait}" alt="${h.name}">
                  <span>${heroName(h)}</span>
                </button>`;
              })
              .join("")}
          </div>
        </div>`;
      })
      .join("");
    $$("[data-picker-role]").forEach((b) => {
      b.classList.toggle("is-on", b.dataset.pickerRole === state.pickerRole);
    });
  }

  function renderShot() {
    const frame = $("[data-shot-frame]");
    const status = $("[data-shot-status]");
    if (!state.shot) {
      frame.innerHTML = `<div class="shot-empty">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="1.5"/><path d="M21 16l-5.5-5.5L7 19"/></svg>
        <strong>${t("画面を撮って、ここに貼る", "Screenshot, then paste here")}</strong>
      </div>`;
      status.textContent = "";
      return;
    }
    frame.innerHTML = `<img alt="scoreboard" src="${state.shot}">`;
    if (state.detected) {
      const names = (state.detected.applied || [])
        .map((k) => {
          const h = Engine.heroByKey(k);
          return h ? heroName(h) : k;
        })
        .join(" · ");
      status.textContent = names
        ? t(`検出: ${names}`, `Detected: ${names}`)
        : t("ヒーローを自動検出できませんでした。下のグリッドで選択してください。", "Could not auto-read heroes. Tap the grid.");
    }
  }

  async function ingestImage(file) {
    if (!file) return;
    const data = await blobToData(file);
    state.shot = data;
    $("[data-shot-status]").textContent = t("解析中…", "Analyzing…");
    renderShot();
    const img = await Vision.loadImage(data);
    await Vision.prepare();
    const vision = Vision.detectHeroes(img);
    let ocr = { mapKey: null, heroKeys: [], left: [], right: [] };
    try {
      const raw = await Promise.race([
        Vision.ocrMapAndNames(img),
        new Promise((resolve) => setTimeout(() => resolve(null), 10000)),
      ]);
      if (typeof raw === "string") ocr = { ...Engine.analyzeScreenshotText(raw), left: [], right: [] };
      else if (raw) ocr = raw;
    } catch (_) {}

    const pickSide = (left, right, top, bottom) => {
      if (state.enemyTeam === "left") return left;
      if (state.enemyTeam === "right") return right;
      if ((bottom || []).length >= 3) return bottom;
      if (right.length >= 3 && left.length >= 3) return right;
      if (right.length >= left.length && right.length) return right;
      return left.length ? left : right;
    };

    const ocrLeft = ocr.left || [];
    const ocrRight = ocr.right || [];
    const ocrAll = ocr.heroKeys || [];
    const ocrStrong = ocrLeft.length + ocrRight.length >= 4 || ocrAll.length >= 4;

    let keys = [];
    if ((vision.bottom || []).length >= 3) {
      keys = vision.bottom;
    } else if (ocrStrong) {
      keys = pickSide(ocrLeft, ocrRight, [], []);
      if (keys.length < 3) keys = ocrAll.length >= 8 ? ocrAll.slice(-5) : ocrAll.slice(0, 5);
    } else {
      keys = pickSide(vision.left || [], vision.right || [], vision.top || [], vision.bottom || []);
      if (keys.length < 3) keys = vision.all || [];
    }

    keys = keys.slice(0, 5);
    if (keys.length >= 3) state.enemies = keys;
    else if (keys.length && !state.enemies.length) state.enemies = keys;
    if ((vision.top || []).length) state.allies = vision.top.slice(0, 5);
    if (ocr.mapKey) state.mapKey = ocr.mapKey;
    state.detected = { ...vision, ocr, applied: keys.length ? keys : state.enemies.slice() };
    save();
    render();
  }

  function blobToData(file) {
    return new Promise((resolve) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.readAsDataURL(file);
    });
  }

  function bitmapToData(img) {
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    c.getContext("2d").drawImage(img, 0, 0);
    return c.toDataURL("image/jpeg", 0.85);
  }

  function bind() {
    document.body.addEventListener("click", (e) => {
      const roleBtn = e.target.closest("[data-role-btn]");
      if (roleBtn) {
        state.myRole = roleBtn.dataset.roleBtn;
        save();
        render();
        return;
      }
      const lang = e.target.closest("[data-lang]");
      if (lang) {
        state.lang = lang.dataset.lang;
        save();
        render();
        return;
      }
      const side = e.target.closest("[data-side]");
      if (side) {
        state.side = side.dataset.side;
        save();
        render();
        return;
      }
      const map = e.target.closest("[data-map]");
      if (map) {
        setMap(map.dataset.map);
        return;
      }
      const pick = e.target.closest("[data-pick]");
      if (pick) {
        setEnemy(pick.dataset.pick);
        return;
      }
      const rem = e.target.closest("[data-remove]");
      if (rem) {
        setEnemy(rem.dataset.remove);
        return;
      }
      const pr = e.target.closest("[data-picker-role]");
      if (pr) {
        state.pickerRole = pr.dataset.pickerRole;
        renderPicker();
        return;
      }
      if (e.target.closest("[data-demo]")) {
        state.enemies = ["pharah", "mercy", "reinhardt", "lucio", "brigitte"];
        state.mapKey = "watchpoint-gibraltar";
        state.myRole = "damage";
        save();
        render();
        return;
      }
      if (e.target.closest("[data-swap-team]")) {
        if (state.detected && state.detected.left && state.detected.right) {
          const usingRight = state.detected.applied && state.detected.applied.join() === state.detected.right.join();
          state.enemies = (usingRight ? state.detected.left : state.detected.right).slice(0, 5);
          state.detected.applied = state.enemies.slice();
          render();
        }
        return;
      }
      if (e.target.closest("[data-sample-shot]")) {
        (async () => {
          const res = await fetch("assets/sample-scoreboard.jpg");
          const blob = await res.blob();
          await ingestImage(new File([blob], "sample-scoreboard.jpg", { type: "image/jpeg" }));
        })();
        return;
      }
      if (e.target.closest("[data-clear-shot]")) {
        state.shot = null;
        state.detected = null;
        render();
      }
    });

    $("[data-map-search]").addEventListener("input", (e) => {
      state.mapQuery = e.target.value;
      renderMaps();
    });
    $("[data-hero-search]").addEventListener("input", (e) => {
      state.query = e.target.value;
      renderPicker();
    });

    window.addEventListener("paste", async (e) => {
      const file = Vision.clipboardImage(e);
      if (!file) return;
      e.preventDefault();
      await ingestImage(file);
    });

    const zone = $("[data-shot-zone]");
    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("is-drag");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("is-drag"));
    zone.addEventListener("drop", async (e) => {
      e.preventDefault();
      zone.classList.remove("is-drag");
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) await ingestImage(file);
    });
    $("[data-file]").addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) await ingestImage(file);
      e.target.value = "";
    });

    window.addEventListener("keydown", (e) => {
      if (e.target.matches("input, textarea")) return;
      if (e.key === "t" || e.key === "T") {
        state.myRole = "tank";
        save();
        render();
      }
      if (e.key === "d" || e.key === "D") {
        state.myRole = "damage";
        save();
        render();
      }
      if (e.key === "s" || e.key === "S") {
        state.myRole = "support";
        save();
        render();
      }
      if (e.key === "Escape") clearEnemies();
      if (e.key === "/") {
        e.preventDefault();
        $("[data-hero-search]").focus();
      }
    });
  }

  async function boot() {
    load();
    bind();
    render();
    try {
      await Vision.prepare();
      state.visionReady = true;
    } catch (err) {
      console.warn(err);
    }
  }

  document.addEventListener("DOMContentLoaded", boot);
})();

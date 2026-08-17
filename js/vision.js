/* Screenshot paste + hero/map vision */
(function () {
  const OW = window.OW;
  const SIG = 6;
  const portraitCache = new Map();
  let ready = false;
  let tesseractLoading = null;

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.decoding = "async";
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("img " + src));
      img.src = src;
    });
  }

  function signatureFromCanvas(ctx, x, y, size) {
    const tmp = signatureFromCanvas._c || (signatureFromCanvas._c = document.createElement("canvas"));
    tmp.width = SIG;
    tmp.height = SIG;
    const t = tmp.getContext("2d", { willReadFrequently: true });
    t.clearRect(0, 0, SIG, SIG);
    t.drawImage(ctx.canvas, x, y, size, size, 0, 0, SIG, SIG);
    const d = t.getImageData(0, 0, SIG, SIG).data;
    const sig = new Float32Array(SIG * SIG * 3);
    let i = 0;
    for (let p = 0; p < d.length; p += 4) {
      sig[i++] = d[p];
      sig[i++] = d[p + 1];
      sig[i++] = d[p + 2];
    }
    return sig;
  }

  function signatureFromImage(img) {
    const c = document.createElement("canvas");
    c.width = SIG;
    c.height = SIG;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    const side = Math.min(img.width, img.height) * 0.78;
    const sx = (img.width - side) / 2;
    const sy = (img.height - side) / 2 + img.height * 0.02;
    ctx.drawImage(img, sx, sy, side, side, 0, 0, SIG, SIG);
    const d = ctx.getImageData(0, 0, SIG, SIG).data;
    const sig = new Float32Array(SIG * SIG * 3);
    let i = 0;
    for (let p = 0; p < d.length; p += 4) {
      sig[i++] = d[p];
      sig[i++] = d[p + 1];
      sig[i++] = d[p + 2];
    }
    return sig;
  }

  async function prepare() {
    if (ready) return;
    const jobs = OW.heroes.map(async (h) => {
      try {
        const img = await loadImage(h.portrait);
        portraitCache.set(h.key, { img, sig: signatureFromImage(img) });
      } catch (err) {
        console.warn("portrait", h.key, err);
      }
    });
    await Promise.all(jobs);
    ready = true;
  }

  function detectHeroes(img) {
    if (!ready || portraitCache.size < 10) return { left: [], right: [], all: [] };
    const maxW = 960;
    const scale = Math.min(1, maxW / img.width);
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, w, h);

    const heroes = [...portraitCache.entries()];
    const hits = [];
    const sizes = [24, 32, 40, 56].filter((s) => s < w / 5 && s < h / 4);
    const leftBand = w * 0.4;
    const rightBand = w * 0.6;

    for (const size of sizes) {
      const stride = Math.max(8, Math.round(size / 2.5));
      for (let y = 0; y <= h - size; y += stride) {
        for (let x = 0; x <= w - size; x += stride) {
          const cx = x + size / 2;
          if (cx > leftBand && cx < rightBand) continue;
          const sig = signatureFromCanvas(ctx, x, y, size);
          const stats = sigStats(sig);
          if (stats.mean < 28 || stats.mean > 190 || stats.stdev < 22) continue;
          let best = -1;
          let bestKey = null;
          let second = -1;
          for (const [key, rec] of heroes) {
            const c = cosine(sig, rec.sig);
            if (c > best) {
              second = best;
              best = c;
              bestKey = key;
            } else if (c > second) second = c;
          }
          if (best > 0.955 && best - Math.max(second, 0) > 0.018) {
            hits.push({ key: bestKey, x, y, size, score: 1 - best });
          }
        }
      }
    }

    hits.sort((a, b) => a.score - b.score);
    const picked = [];
    for (const hit of hits) {
      const overlap = picked.some((p) => {
        const dx = p.x + p.size / 2 - (hit.x + hit.size / 2);
        const dy = p.y + p.size / 2 - (hit.y + hit.size / 2);
        return dx * dx + dy * dy < Math.pow(Math.min(p.size, hit.size) * 0.75, 2);
      });
      if (overlap) continue;
      if (picked.some((p) => p.key === hit.key)) continue;
      picked.push(hit);
      if (picked.length >= 10) break;
    }

    const mid = w / 2;
    const left = picked.filter((p) => p.x + p.size / 2 < mid).map((p) => p.key);
    const right = picked.filter((p) => p.x + p.size / 2 >= mid).map((p) => p.key);
    return {
      left,
      right,
      all: picked.map((p) => p.key),
      hits: picked,
      scale,
    };
  }

  function sigStats(sig) {
    let sum = 0;
    const n = sig.length / 3;
    for (let i = 0; i < sig.length; i += 3) sum += (sig[i] + sig[i + 1] + sig[i + 2]) / 3;
    const mean = sum / n;
    let v = 0;
    for (let i = 0; i < sig.length; i += 3) {
      const y = (sig[i] + sig[i + 1] + sig[i + 2]) / 3 - mean;
      v += y * y;
    }
    return { mean, stdev: Math.sqrt(v / n) };
  }

  function cosine(a, b) {
    let dot = 0;
    let na = 0;
    let nb = 0;
    const len = a.length;
    for (let i = 0; i < len; i++) {
      const av = a[i] - 128;
      const bv = b[i] - 128;
      dot += av * bv;
      na += av * av;
      nb += bv * bv;
    }
    return dot / (Math.sqrt(na * nb) + 1e-6);
  }

  function readFileAsImage(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = reject;
      img.src = url;
    });
  }

  function clipboardImage(event) {
    const items = event.clipboardData && event.clipboardData.items;
    if (!items) return null;
    for (const item of items) {
      if (item.type.startsWith("image/")) return item.getAsFile();
    }
    return null;
  }

  async function ocrMapAndNames(img) {
    try {
      if (!tesseractLoading) {
        tesseractLoading = new Promise((resolve, reject) => {
          if (window.Tesseract) return resolve(window.Tesseract);
          const s = document.createElement("script");
          s.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
          s.onload = () => resolve(window.Tesseract);
          s.onerror = reject;
          document.head.appendChild(s);
        });
      }
      const Tesseract = await tesseractLoading;
      const crop = document.createElement("canvas");
      crop.width = Math.min(1100, img.width);
      crop.height = Math.round(crop.width * (img.height / img.width));
      crop.getContext("2d").drawImage(img, 0, 0, crop.width, crop.height);
      const result = await Tesseract.recognize(crop, "eng", { logger: () => {} });
      const text = result && result.data ? result.data.text : "";
      const mid = crop.width / 2;
      const left = [];
      const right = [];
      const words = (result && result.data && result.data.words) || [];
      const parsed = Engine.analyzeScreenshotText(text);
      for (const word of words) {
        const raw = String(word.text || "").toLowerCase().replace(/[^a-z0-9:]+/g, " ").trim();
        if (raw.length < 3) continue;
        const hit = OW.heroes.find((h) => {
          const n = h.name.toLowerCase();
          return n === raw || n.replace(/[:']/g, "") === raw || h.key.replace(/-/g, " ") === raw;
        });
        if (!hit) continue;
        const x = word.bbox ? (word.bbox.x0 + word.bbox.x1) / 2 : 0;
        if (x < mid) {
          if (!left.includes(hit.key)) left.push(hit.key);
        } else if (!right.includes(hit.key)) {
          right.push(hit.key);
        }
      }
      return { text, left, right, mapKey: parsed.mapKey, heroKeys: parsed.heroKeys };
    } catch (err) {
      console.warn("ocr", err);
      return { text: "", left: [], right: [], mapKey: null, heroKeys: [] };
    }
  }

  window.Vision = {
    prepare,
    detectHeroes,
    readFileAsImage,
    clipboardImage,
    ocrMapAndNames,
    loadImage,
  };
})();

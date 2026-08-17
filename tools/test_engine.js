const fs = require("fs");
const vm = require("vm");
const path = require("path");

const root = path.join(__dirname, "..");
const context = { window: {}, console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, "js/data.js"), "utf8"), context);
vm.runInContext(fs.readFileSync(path.join(root, "js/engine.js"), "utf8"), context);

const { Engine, OW } = context.window;
if (OW.heroes.length !== 53) throw new Error("expected 53 heroes, got " + OW.heroes.length);
if (!OW.heroes.find((h) => h.key === "dmon")) throw new Error("missing D.Mon");
if (!OW.maps.find((m) => m.key === "kings-row")) throw new Error("missing King's Row");

const rec = Engine.recommend({
  myRole: "damage",
  enemies: ["pharah", "mercy", "reinhardt", "lucio", "brigitte"],
  mapKey: "watchpoint-gibraltar",
  side: "defend",
});

const names = rec.picks.map((p) => p.hero.key);
console.log("comp", rec.comp.primary);
console.log("picks", names.join(", "));
console.log("scores", rec.picks.map((p) => p.hero.name + " " + p.score).join(" | "));

const hitscan = new Set(["ashe", "widowmaker", "cassidy", "soldier-76", "sojourn", "baptiste", "emre", "sierra"]);
if (!names.some((k) => hitscan.has(k))) {
  throw new Error("expected a hitscan answer to PharMercy, got " + names);
}

const dive = Engine.recommend({
  myRole: "tank",
  enemies: ["widowmaker", "hanzo", "ashe", "zenyatta", "illari"],
  mapKey: "circuit-royal",
});
console.log("sniper map tank picks", dive.picks.map((p) => p.hero.key).join(", "));
if (!dive.picks.some((p) => ["winston", "dva", "wrecking-ball", "doomfist"].includes(p.hero.key))) {
  throw new Error("expected a dive tank into snipers");
}

console.log("ok");

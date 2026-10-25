// Record real screen footage of the live ProofGate site for the demo film.
//
// Launches its own Chrome (separate profile, nothing of the user's) at 1920x1080, drives each
// shot with scripted steps, captures frames with the DevTools screencast, and encodes a
// constant-frame-rate MP4 per shot with ffmpeg. Usage:
//   node video/tools/record.mjs [shot ...]      (no args: every shot)
// PG_SITE points it at another deployment, e.g. a local site wired to a live engine.

import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "assets", "rec");
const SITE = process.env.PG_SITE || "https://proofgate-ten.vercel.app";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;
const W = 1920, H = 1080, FPS = 30;
const LIVE_REPORT = process.env.PG_LIVE_REPORT || "https://hackerone.com/reports/3418528";
const LIVE_CVE = process.env.PG_LIVE_CVE || "CVE-2026-6276";

// Each step: [kind, ...args]. Times in ms.
//   go url · wait ms · rec · scroll y ms · scrollBy dy ms · eval js
//   move x y ms · click js(el) · drag [[x,y],...] ms · type js(el) text msPerChar
//   until js timeout · mark name js(array of elements)
// Shots named in CURSOR draw a visible pointer (the screencast has none). Marks record where
// named elements sit on screen at that moment, so the film can highlight exactly that area.
const CURSOR = new Set(["galaxy", "live", "fixlive"]);
const btn = (text) => `[...document.querySelectorAll('button')].find(b => b.textContent.includes(${JSON.stringify(text)}))`;
const SHOTS = {
  hero: [["go", "/"], ["wait", 2500], ["rec"], ["wait", 1500], ["scroll", 2300, 9000], ["wait", 1200]],
  console: [["go", "/console/"], ["wait", 200], ["rec"], ["wait", 14000]],
  card: [["go", "/console/"], ["wait", 13000],
         ["eval", "const h=[...document.querySelectorAll('h2')].find(x=>x.textContent.includes('not found in curl')); window.scrollTo(0, h.getBoundingClientRect().top + scrollY - 140)"],
         ["wait", 700], ["rec"], ["wait", 1500], ["scrollBy", 700, 4500], ["wait", 1500]],
  bench: [["go", "/bench/"], ["wait", 2500], ["rec"], ["wait", 1500], ["scroll", 700, 3500], ["wait", 2000]],
  fixbench: [["go", "/fixbench/"], ["wait", 3500], ["rec"], ["wait", 1800], ["scroll", 650, 2500], ["wait", 2500],
             ["scroll", 1150, 2500], ["wait", 2000]],
  replay: [["go", "/fixbench/"], ["wait", 4000],
           ["eval", `${btn("CVE-2026-92390")}?.click()`],
           ["wait", 1500], ["eval", "const t=[...document.querySelectorAll('h2')].find(h=>h.textContent.includes('no-clobber')); t.scrollIntoView({block:'start'}); window.scrollBy(0,-100)"],
           ["wait", 800], ["rec"], ["wait", 800],
           ["eval", "[...document.querySelectorAll('button')].find(b => b.textContent.trim()==='Replay')?.click()"],
           ["wait", 11500], ["scrollBy", 520, 3000], ["wait", 2500]],
  landingfix: [["go", "/"], ["wait", 3000],
               ["eval", "const h=[...document.querySelectorAll('h2')].find(x=>x.textContent.includes('writes the patch')); window.scrollTo(0, h.getBoundingClientRect().top + scrollY - 260)"],
               ["wait", 1500], ["rec"], ["wait", 4500]],
  // the code galaxy: free rotation in every direction, then one real and one invented function
  galaxy: [["go", "/galaxy/"], ["until", "document.querySelector('canvas')", 30000], ["wait", 5000],
           ["move", 1000, 560, 10], ["rec"], ["wait", 1200],
           ["mark", "canvas", "[document.querySelector('canvas')]"],
           ["drag", [[1100, 180], [1105, 980]], 2600], ["wait", 250],
           ["drag", [[1100, 180], [1095, 980]], 2600], ["wait", 700],
           ["drag", [[700, 560], [1500, 540]], 2400], ["wait", 250],
           ["drag", [[700, 560], [1500, 600], [1100, 560]], 3000], ["wait", 1500],
           ["mark", "stats", "[document.querySelector('aside [class*=_stats]')]"],
           ["click", btn("Curl_cookie_add")], ["wait", 4200],
           ["mark", "result", "[document.querySelector('aside [class*=_result]')]"], ["wait", 1800],
           ["click", btn("Curl_cookie_parse_header")], ["wait", 4200],
           ["mark", "result2", "[document.querySelector('aside [class*=_result]')]"],
           ["drag", [[900, 560], [1250, 610]], 2600], ["wait", 2400]],
  // a real HackerOne report, fetched and triaged live through Token Factory and Tavily
  live: [["go", "/console/"], ["until", btn("Live · your report"), 30000], ["wait", 2500], ["rec"], ["wait", 800],
         ["mark", "chip", "[document.querySelector('[class*=_mode] .chip')]"],
         ["click", btn("Live · your report")], ["wait", 900],
         ["scroll", "document.querySelector('[class*=_work]').getBoundingClientRect().top + scrollY - 150", 1600], ["wait", 500],
         ["type", "document.querySelector('input[aria-label=\"HackerOne report link\"]')", LIVE_REPORT, 28],
         ["wait", 600], ["mark", "link", "[document.querySelector('input[aria-label=\"HackerOne report link\"]')]"],
         ["click", btn("Run ProofGate live")], ["wait", 400],
         ["mark", "counters", "[document.querySelector('[class*=_counters]')]"],
         ["until", "[...document.querySelectorAll('h2')].some(h => h.closest('[class*=_card]'))", 240000],
         ["mark", "stages", "[document.querySelector('[class*=_stages]') || document.querySelectorAll('section')[1]]"],
         ["mark", "galaxy", "[document.querySelector('canvas')]"], ["wait", 3500],
         ["eval", "window.scrollTo({ top: document.querySelector('[class*=_work]').getBoundingClientRect().bottom + scrollY - 80, behavior: 'smooth' })"],
         ["wait", 1800], ["mark", "card", "[document.querySelector('[class*=_card]')]"], ["wait", 4000]],
  // the fix agent on a real curl CVE, live: reproduce, edit, build curl, run its tests
  fixlive: [["go", "/fixbench/"], ["until", btn("Nemotron 3 Super 120B"), 30000], ["wait", 2500],
            ["click", btn("Nemotron 3 Super 120B")], ["wait", 900],
            ["eval", `${btn(LIVE_CVE)}.scrollIntoView({ block: "center" })`], ["wait", 600], ["rec"], ["wait", 600],
            ["click", btn(LIVE_CVE)], ["wait", 1200],
            ["eval", "const d=document.querySelector('[class*=_detail]'); window.scrollTo({ top: d.getBoundingClientRect().top + scrollY - 24, behavior: 'smooth' })"],
            ["wait", 1200], ["mark", "run", `[${btn("Run live now")}]`],
            ["click", btn("Run live now")], ["wait", 1500],
            ["mark", "bar", "[document.querySelector('[class*=_liveBar]')]"],
            ["until", "document.querySelector('[class*=_lightRow]')", 600000],
            ["mark", "lights", "[document.querySelector('[class*=_testLights]')]"],
            ["until", "document.querySelector('[class*=_liveBar]')?.textContent.includes('live run')", 900000],
            ["wait", 1500], ["mark", "done", "[document.querySelector('[class*=_liveBar]'), document.querySelector('[class*=_testLights]')]"],
            ["wait", 2500],
            ["eval", "const g=document.querySelector('[class*=_dGrid]'); window.scrollTo({ top: g.getBoundingClientRect().top + scrollY - 40, behavior: 'smooth' })"],
            ["wait", 1800], ["mark", "patch", "[document.querySelectorAll('[class*=_dGrid] pre')[0]]"], ["wait", 4000]],
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cdpConnect() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(250);
  }
  throw new Error("Chrome DevTools endpoint did not come up");
}

function client(url) {
  const ws = new WebSocket(url);
  let id = 0;
  const pending = new Map();
  const handlers = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method && handlers.has(msg.method)) {
      handlers.get(msg.method)(msg.params);
    }
  };
  const ready = new Promise((r) => (ws.onopen = r));
  return {
    ready,
    send: (method, params = {}) => new Promise((resolve, reject) => {
      const n = ++id;
      pending.set(n, { resolve, reject });
      ws.send(JSON.stringify({ id: n, method, params }));
    }),
    on: (method, fn) => handlers.set(method, fn),
    close: () => ws.close(),
  };
}

const EASE = "t<.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2";
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const scrollJs = (to, ms, rel) => `new Promise(res => { const y0 = scrollY, y1 = ${rel ? "scrollY + " : ""}${to};
  const t0 = performance.now(); const f = now => { const t = Math.min(1, (now - t0) / ${ms});
  window.scrollTo(0, y0 + (y1 - y0) * (${EASE})); t < 1 ? requestAnimationFrame(f) : res(); }; requestAnimationFrame(f); })`;
const rectsJs = (js) => `JSON.stringify((${js}).filter(Boolean).map(e => { const r = e.getBoundingClientRect();
  return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) }; }))`;

// A drawn pointer that follows the real (CDP-dispatched) mouse events, with a ring on press.
const CURSOR_JS = `addEventListener("DOMContentLoaded", () => {
  const c = document.createElement("div");
  c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 11-6.5 1.2L16 21l-3 1.4-3.3-6.6L4 20z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, { position: "fixed", left: "0", top: "0", zIndex: 2147483647, pointerEvents: "none",
    transform: "translate(-200px,-200px)", filter: "drop-shadow(0 2px 4px rgba(0,0,0,.55))" });
  document.documentElement.appendChild(c);
  addEventListener("mousemove", (e) => { c.style.transform = "translate(" + (e.clientX - 4) + "px," + (e.clientY - 2) + "px)"; }, true);
  addEventListener("mousedown", (e) => {
    const r = document.createElement("div");
    Object.assign(r.style, { position: "fixed", left: e.clientX - 18 + "px", top: e.clientY - 18 + "px", width: "36px", height: "36px",
      borderRadius: "50%", border: "3px solid #8bd3ff", zIndex: 2147483646, pointerEvents: "none", transition: "all .45s ease-out" });
    document.documentElement.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = "scale(1.9)"; r.style.opacity = "0"; });
    setTimeout(() => r.remove(), 600);
  }, true);
});`;

async function recordShot(name, steps) {
  const frames = join(tmpdir(), `pg-rec-${name}`);
  rmSync(frames, { recursive: true, force: true });
  mkdirSync(frames, { recursive: true });
  const profile = join(tmpdir(), "pg-rec-profile");
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars", "--mute-audio",
    `--window-size=${W},${H + 140}`, "--window-position=0,0", "--force-device-scale-factor=1",
    "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows", "--disable-features=CalculateNativeWinOcclusion", "about:blank",
  ], { stdio: "ignore" });
  const cdp = client(await cdpConnect());
  await cdp.ready;
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  if (CURSOR.has(name)) await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: CURSOR_JS });
  let recording = false;
  let recStart = 0;
  const shots = [];
  const marks = [];
  cdp.on("Page.screencastFrame", async (p) => {
    cdp.send("Page.screencastFrameAck", { sessionId: p.sessionId }).catch(() => {});
    if (!recording) return;
    const file = join(frames, `f${String(shots.length).padStart(5, "0")}.jpg`);
    writeFileSync(file, Buffer.from(p.data, "base64"));
    shots.push({ file, t: p.metadata.timestamp });
    if (!recStart) recStart = p.metadata.timestamp;
  });
  const evaluate = (expression) => cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });

  let mouse = [W / 2, H / 2];
  const mouseEv = (type, [x, y], held) => cdp.send("Input.dispatchMouseEvent", {
    type, x, y, button: type === "mouseMoved" && !held ? "none" : "left",
    buttons: held || type === "mousePressed" ? 1 : 0, clickCount: type === "mouseMoved" ? 0 : 1,
  });
  // an eased path through the waypoints, one event per ~16 ms
  const glide = async (pts, ms, held = false) => {
    const legs = pts.slice(1).map((p, i) => [pts[i], p, Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1])]);
    const total = legs.reduce((a, l) => a + l[2], 0) || 1;
    const n = Math.max(2, Math.round(ms / 16));
    const t0 = Date.now();
    for (let k = 1; k <= n; k++) {
      let d = ease(k / n) * total;
      let at = pts[pts.length - 1];
      for (const [a, b, len] of legs) {
        if (d <= len) { const f = len ? d / len : 1; at = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]; break; }
        d -= len;
      }
      mouse = at.map(Math.round);
      await mouseEv("mouseMoved", mouse, held);
      const wait = t0 + (k * ms) / n - Date.now();
      if (wait > 0) await sleep(wait);
    }
  };
  const rects = async (js) => JSON.parse((await evaluate(rectsJs(js))).result.value || "[]");

  for (const [kind, a, b, c] of steps) {
    if (process.env.PG_DEBUG) console.log(`${name}: ${kind} ${typeof a === "string" ? a.slice(0, 60) : a ?? ""}`);
    if (kind === "go") {
      await cdp.send("Page.navigate", { url: SITE + a });
    } else if (kind === "wait") {
      await sleep(a);
    } else if (kind === "rec") {
      await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
      recording = true;
    } else if (kind === "scroll" || kind === "scrollBy") {
      await evaluate(scrollJs(a, b, kind === "scrollBy"));
    } else if (kind === "eval") {
      await evaluate(a);
    } else if (kind === "move") {
      await glide([mouse, [a, b]], c ?? 600);
    } else if (kind === "click" || kind === "type") {
      const r = (await rects(`[${a}]`))[0];
      if (!r) throw new Error(`${name}: nothing to ${kind}: ${a}`);
      const at = [Math.round(r.x + Math.min(r.w / 2, 160)), Math.round(r.y + r.h / 2)];
      await glide([mouse, at], 650);
      await sleep(120);
      await mouseEv("mousePressed", at);
      await sleep(70);
      await mouseEv("mouseReleased", at);
      if (kind === "type") {
        for (const ch of b) {
          await cdp.send("Input.insertText", { text: ch });
          await sleep(c ?? 35);
        }
      }
    } else if (kind === "drag") {
      await glide([mouse, a[0]], 450);
      await mouseEv("mousePressed", a[0]);
      await glide(a, b, true);
      await mouseEv("mouseReleased", mouse);
    } else if (kind === "until") {
      const t0 = Date.now();
      while (!(await evaluate(`Boolean(${a})`)).result.value) {
        if (Date.now() - t0 > (b ?? 60000)) throw new Error(`${name}: timed out waiting for ${a}`);
        await sleep(250);
      }
    } else if (kind === "mark") {
      marks.push({ name: a, t: recStart ? +(Date.now() / 1000 - recStart).toFixed(2) : 0, rects: await rects(b) });
    }
  }
  recording = false;
  await cdp.send("Page.stopScreencast").catch(() => {});
  cdp.close();
  chrome.kill();
  if (shots.length < 2) throw new Error(`${name}: no frames captured`);
  // concat list with real frame durations -> constant frame rate video
  const end = shots[shots.length - 1].t + 1 / FPS;
  const list = shots.map((s, i) => `file '${s.file.replace(/\\/g, "/")}'\nduration ${((shots[i + 1]?.t ?? end) - s.t).toFixed(4)}`).join("\n")
    + `\nfile '${shots[shots.length - 1].file.replace(/\\/g, "/")}'\n`;
  writeFileSync(join(frames, "list.txt"), list);
  mkdirSync(OUT, { recursive: true });
  const out = join(OUT, `${name}.mp4`);
  const ff = spawnSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(frames, "list.txt"),
    "-vf", `fps=${FPS},scale=${W}:${H}:flags=lanczos,format=yuv420p`, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-g", "15", "-movflags", "+faststart", out], { stdio: "inherit" });
  rmSync(frames, { recursive: true, force: true });
  if (ff.status !== 0) throw new Error(`${name}: ffmpeg failed`);
  // wall-clock start (epoch seconds) lets the film line the footage up with the engine's log
  writeFileSync(join(OUT, `${name}.marks.json`), JSON.stringify({ start: shots[0].t, marks }, null, 1));
  const secs = (shots[shots.length - 1].t - shots[0].t).toFixed(1);
  console.log(`recorded ${name}: ${shots.length} frames over ${secs}s -> ${out}`);
}

const wanted = process.argv.slice(2);
for (const [name, steps] of Object.entries(SHOTS)) {
  if (wanted.length && !wanted.includes(name)) continue;
  await recordShot(name, steps);
  await sleep(800);
}
if (!existsSync(OUT)) process.exit(1);

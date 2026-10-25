// Record real screen footage of the live ProofGate site for the demo film.
//
// Launches its own Chrome (separate profile, nothing of the user's) at 1920x1080, drives each
// shot with scripted steps, captures frames with the DevTools screencast, and encodes a
// constant-frame-rate MP4 per shot with ffmpeg. Usage:
//   node video/tools/record.mjs [shot ...]      (no args: every shot)

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

// Each step: [kind, ...args]. Times in ms.
//   go url · wait ms · scroll y ms (smooth, eased) · click text · eval js · top
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
           ["eval", "[...document.querySelectorAll('button')].find(b => b.textContent.includes('CVE-2026-92390'))?.click()"],
           ["wait", 1500], ["eval", "const t=[...document.querySelectorAll('h2')].find(h=>h.textContent.includes('no-clobber')); t.scrollIntoView({block:'start'}); window.scrollBy(0,-100)"],
           ["wait", 800], ["rec"], ["wait", 800],
           ["eval", "[...document.querySelectorAll('button')].find(b => b.textContent.trim()==='Replay')?.click()"],
           ["wait", 11500], ["scrollBy", 520, 3000], ["wait", 2500]],
  landingfix: [["go", "/"], ["wait", 3000],
               ["eval", "const h=[...document.querySelectorAll('h2')].find(x=>x.textContent.includes('writes the patch')); window.scrollTo(0, h.getBoundingClientRect().top + scrollY - 260)"],
               ["wait", 1500], ["rec"], ["wait", 4500]],
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
const scrollJs = (to, ms, rel) => `new Promise(res => { const y0 = scrollY, y1 = ${rel ? "scrollY + " : ""}${to};
  const t0 = performance.now(); const f = now => { const t = Math.min(1, (now - t0) / ${ms});
  window.scrollTo(0, y0 + (y1 - y0) * (${EASE})); t < 1 ? requestAnimationFrame(f) : res(); }; requestAnimationFrame(f); })`;

async function recordShot(name, steps) {
  const frames = join(tmpdir(), `pg-rec-${name}`);
  rmSync(frames, { recursive: true, force: true });
  mkdirSync(frames, { recursive: true });
  const profile = join(tmpdir(), "pg-rec-profile");
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars", "--mute-audio",
    `--window-size=${W},${H + 140}`, "--window-position=0,0", "--force-device-scale-factor=1",
    "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "about:blank",
  ], { stdio: "ignore" });
  const cdp = client(await cdpConnect());
  await cdp.ready;
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  let recording = false;
  const shots = [];
  cdp.on("Page.screencastFrame", async (p) => {
    cdp.send("Page.screencastFrameAck", { sessionId: p.sessionId }).catch(() => {});
    if (!recording) return;
    const file = join(frames, `f${String(shots.length).padStart(5, "0")}.jpg`);
    writeFileSync(file, Buffer.from(p.data, "base64"));
    shots.push({ file, t: p.metadata.timestamp });
  });
  const evaluate = (expression) => cdp.send("Runtime.evaluate", { expression, awaitPromise: true });
  for (const [kind, a, b] of steps) {
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

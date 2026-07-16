/* ===================================================================
   BreachBench — Live Siege Replay  (offline, no API, no server)
   Plays back real saved transcripts as an animated attacker-vs-defender siege.
   =================================================================== */
(function () {
  "use strict";

  const RUNS = (window.BREACHBENCH_REPLAY || []).slice();

  // ---- themed scene art (registry in themes.js; one theme per attack vector) ----
  const THEMES = window.BREACHBENCH_THEMES || {};
  const themeFor = (r) => THEMES[(r && r.theme)] || THEMES.realm;

  // ---- DOM refs ----
  const $ = (id) => document.getElementById(id);
  const el = {
    runSelect: $("runSelect"),
    objective: $("mObjective"), vector: $("mVector"), boundary: $("mBoundary"),
    round: $("mRound"), kmax: $("mKmax"),
    statusCell: $("mStatusCell"), statusVal: $("mStatus"), statusLabel: $("mStatusCell").querySelector(".mlabel"),
    attackerModel: $("attackerModel"), defenderModel: $("defenderModel"), defenderName: $("defenderName"),
    attackerSvg: $("attackerSvg"), defenderSvg: $("defenderSvg"),
    battlefield: $("battlefield"), scene: $("scene"),
    lane: $("lane"), projectile: $("projectile"), impact: $("impact"), debris: $("debris"),
    castle: $("castle"), wall: $("wall"),
    treasure: $("treasure"), treasureIcon: $("treasureIcon"),
    treasureLabel: $("treasureLabel"), treasureValue: $("treasureValue"),
    survival: $("survival"), banner: $("banner"),
    judgeCard: $("judgeCard"), jcBadge: $("jcBadge"), jcScore: $("jcScore"),
    jcVersus: $("jcVersus"), jcRationale: $("jcRationale"), jcTakeaway: $("jcTakeaway"),
    dialogue: $("dialogue"), dialogueEmpty: $("dialogueEmpty"),
    caption: $("caption"),
    btnRestart: $("btnRestart"), btnPrev: $("btnPrev"), btnPlay: $("btnPlay"),
    btnNext: $("btnNext"), speed: $("speed"), speedVal: $("speedVal"),
  };
  // apply a theme's art to the scene + fighters + fortress, then re-cache the fortress
  // hooks (they were just re-created by innerHTML, so the old cached nodes are stale).
  function applyTheme(run) {
    const t = themeFor(run);
    el.battlefield.dataset.theme = run.theme || "realm";
    el.scene.innerHTML = t.sceneHtml;
    el.attackerSvg.innerHTML = t.attackerSvg;
    el.defenderSvg.innerHTML = t.defenderSvg;
    el.castle.innerHTML = t.fortressHtml;
    el.projectile.innerHTML = t.projectileSvg || "";
    el.wall = $("wall");
    el.treasure = $("treasure");
    el.treasureIcon = $("treasureIcon");
    el.treasureLabel = $("treasureLabel");
    el.treasureValue = $("treasureValue");
  }

  // ---- state ----
  let run = null;      // current run object
  let ptr = 0;         // number of rounds revealed
  let playing = false;
  let token = 0;       // cancellation token; bumps on any user action / reset
  let busy = false;    // an animation is in flight

  const speedMul = () => parseFloat(el.speed.value) || 1;
  const sleep = (ms, tok) =>
    new Promise((res) => setTimeout(() => res(tok === token), Math.max(0, ms / speedMul())));

  const esc = (s) =>
    String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // reading pause proportional to text length (only used during auto-play, so the
  // audience has time to actually read each message). ~45ms/word, clamped 2.5–11s.
  const readMs = (t) => {
    const words = String(t || "").trim().split(/\s+/).filter(Boolean).length;
    return Math.min(11000, Math.max(2500, words * 45));
  };

  // ---------- run wiring ----------
  function populateRuns() {
    RUNS.forEach((r, i) => {
      const o = document.createElement("option");
      const badge = r.held ? "🛡 HELD" : "💥 " + r.outcome;
      o.value = String(i);
      o.textContent = `${r.scene_title} · ${r.vector_label} — ${r.target_model}  ·  ${badge}`;
      el.runSelect.appendChild(o);
    });
    el.runSelect.addEventListener("change", () => loadRun(RUNS[+el.runSelect.value]));
  }

  function loadRun(r) {
    token++; playing = false; busy = false; ptr = 0;
    run = r;
    applyTheme(r); // inject this run's themed art + re-cache fortress hooks
    const conf = r.breach_type === "CONFIDENTIALITY";

    el.objective.textContent = r.objective;
    el.vector.textContent = r.vector_label;
    el.vector.title = r.vector_desc;
    el.boundary.textContent = conf ? "Confidentiality" : "Integrity";
    el.kmax.textContent = r.k_max;
    el.attackerModel.textContent = r.attacker_model;
    el.defenderModel.textContent = r.target_model;
    el.defenderName.textContent = r.defender_role || r.defender_name;

    // secret framing (token vs override lever), themed per boundary
    el.statusLabel.textContent = conf ? "Vault status" : "Safety interlock";
    el.treasureLabel.textContent = conf ? r.secret_label : "Override lever";
    el.treasureIcon.textContent = conf ? "🔑" : "🎛️";

    buildDots();
    renderStatic(0);
    setPlayBtn();
    el.caption.textContent = r.caption;
    updateControls();
  }

  function buildDots() {
    el.survival.innerHTML = "";
    for (let i = 0; i < run.k_max; i++) {
      const d = document.createElement("span");
      d.className = "dot";
      d.title = "Round " + (i + 1);
      el.survival.appendChild(d);
    }
  }

  // ---------- scene helpers ----------
  function resetScene() {
    hideJudgeCard();
    handSpear(true);
    el.projectile.className = "projectile"; el.projectile.style.opacity = "0";
    el.impact.className = "impact";
    el.debris.innerHTML = "";
    el.battlefield.classList.remove("shake");
    el.attackerSvg.classList.remove("windup", "release", "lunge");
    el.castle.classList.remove("rubble", "victory");
    el.treasure.classList.remove("exposed");
    el.banner.className = "banner";
    el.banner.innerHTML = "";
    el.defenderSvg.classList.remove("brace", "stagger");
    el.attackerSvg.classList.remove("lunge");
    const conf = run.breach_type === "CONFIDENTIALITY";
    el.treasureValue.textContent = conf ? "••••••••••••" : "🔒 Locked";
    el.statusVal.textContent = conf ? "🔒 Secure" : "🔒 Engaged";
    el.statusCell.classList.remove("breached", "held");
  }

  function paintDots(count) {
    const dots = el.survival.children;
    for (let i = 0; i < dots.length; i++) {
      dots[i].className = "dot";
      if (i < count) {
        const rd = run.rounds[i];
        dots[i].classList.add(rd && rd.breach ? "breached" : "survived");
      }
    }
    if (count > 0 && count <= dots.length) {
      // mark the just-revealed round as current
    }
  }

  function setRoundLabel(n) { el.round.textContent = n; }

  // highlight leaked canary inside target text
  function renderTargetHTML(rd) {
    let html = esc(rd.target);
    if (rd.canary_leaked && run.canary) {
      const raw = run.canary;
      const bare = raw.replace(/^AX-/, "");
      [raw, bare].forEach((needle) => {
        if (needle && needle.length > 3) {
          const re = new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
          html = html.replace(re, (m) => `<span class="leak">${esc(m)}</span>`);
        }
      });
    }
    return html;
  }

  function toolFireCard(rd) {
    const call = (rd.tool_calls && rd.tool_calls[0]) || {};
    const args = call.arguments || {};
    const via = rd.tool_detection === "TEXT_PROTOCOL" ? "text protocol" : "native tool-call";
    const rows = Object.entries(args).map(([k, v]) => {
      const val = String(v);
      const bad = /^(auth|authorization)_?code$/i.test(k) &&
        (!val.trim() || /not[_ ]?provided|none|n\/?a|missing|null|invalid/i.test(val));
      return `<div class="tf-arg"><span class="tf-k">${esc(k)}</span>` +
        `<span class="tf-v${bad ? " tf-bad" : ""}">${esc(val)}${bad ? "  ⚠ no valid code" : ""}</span></div>`;
    }).join("");
    return `<div class="toolfire">
        <div class="tf-head">⚙ execute_emergency_override() FIRED</div>
        <div class="tf-sub">the forbidden tool was actually invoked · via ${via}</div>
        ${rows}
      </div>`;
  }

  // build a conversation turn element
  function turnEl(role, rd) {
    const t = document.createElement("div");
    t.className = "turn " + (role === "attacker" ? "attacker" : "target");
    const avatar = role === "attacker" ? "⚔️" : "🛡️";
    const who = role === "attacker"
      ? `Attacker · ${run.attacker_model}`
      : `Defender · ${run.target_model}`;
    let body;
    if (role === "attacker") {
      body = esc(rd.attacker);
    } else {
      body = renderTargetHTML(rd);
      if (rd.tool_fired) body += toolFireCard(rd);
    }
    t.innerHTML =
      `<div class="avatar">${avatar}</div>
       <div class="bubble"><span class="who">${who} <span class="rk">· round ${rd.k}</span></span>${body}</div>`;
    return t;
  }

  function scrollDialogue() {
    el.dialogue.scrollTop = el.dialogue.scrollHeight;
  }

  // ---------- static (instant) render of the first `count` rounds ----------
  function renderStatic(count) {
    token++;
    ptr = count;
    el.dialogue.innerHTML = "";
    resetScene();

    if (count === 0) {
      el.dialogue.appendChild(el.dialogueEmpty);
      el.dialogueEmpty.style.display = "";
      setRoundLabel(0);
      paintDots(0);
      updateControls();
      return;
    }
    el.dialogueEmpty.style.display = "none";

    let breached = false;
    for (let i = 0; i < count; i++) {
      const rd = run.rounds[i];
      el.dialogue.appendChild(turnEl("attacker", rd));
      el.dialogue.appendChild(turnEl("target", rd));
      if (rd.breach) breached = true;
    }
    paintDots(count);
    setRoundLabel(count);
    scrollDialogue();

    // scene end-state for the revealed portion
    if (breached) showBreachState(true);
    else if (count === run.n_rounds && run.held) showHoldState(true);

    updateControls();
  }

  // ---------- animated reveal of a single round (the play path) ----------
  async function revealNext() {
    if (busy || !run || ptr >= run.n_rounds) return false;
    const myTok = ++token;
    busy = true;
    updateControls();
    el.dialogueEmpty.style.display = "none";
    const i = ptr;
    const rd = run.rounds[i];

    // mark current dot
    paintDots(i);
    if (el.survival.children[i]) el.survival.children[i].classList.add("current");
    setRoundLabel(i + 1);

    // 1) attacker speaks (winds up)
    el.dialogue.appendChild(turnEl("attacker", rd));
    scrollDialogue();
    el.attackerSvg.classList.add("lunge");
    if (!(await sleep(900, myTok))) return abort();
    // let the audience read the (long) attacker prompt before the defender answers
    if (playing && !(await sleep(readMs(rd.attacker), myTok))) return abort();

    // 2) defender "thinking"
    const think = document.createElement("div");
    think.className = "turn target";
    think.innerHTML =
      `<div class="avatar">🛡️</div><div class="bubble"><span class="who">Defender · ${run.target_model}</span>
       <span class="thinking"><span></span><span></span><span></span></span></div>`;
    el.dialogue.appendChild(think);
    scrollDialogue();
    el.attackerSvg.classList.remove("lunge");
    if (!(await sleep(1100, myTok))) return abort();

    // 3) resolve clash → defender reply
    think.remove();
    el.dialogue.appendChild(turnEl("target", rd));
    scrollDialogue();
    // let the audience read the defender's reply before resolving the round
    if (playing && !(await sleep(readMs(rd.target), myTok))) return abort();

    // 4) the attacker hurls the spear; it either strikes the shield or breaks the castle
    if (rd.breach) {
      if (!(await throwSpear("breach", myTok))) return abort();
      paintDots(i + 1);
      ptr = i + 1;
      showBreachState(false);
    } else {
      if (!(await throwSpear("block", myTok))) return abort();
      paintDots(i + 1);
      ptr = i + 1;
      // final round with no breach = a hold
      if (ptr === run.n_rounds && run.held) {
        if (!(await sleep(500, myTok))) return abort();
        showHoldState(false);
      }
    }

    busy = false;
    updateControls();
    return true;
  }

  function abort() { busy = false; updateControls(); return false; }

  // ---------- animation primitives ----------
  // throw the spear across the battlefield: "block" lands on the shield, "breach"
  // arcs higher and strikes the castle. Resolves after the flight + impact.
  function handSpear(show) {
    const hs = el.attackerSvg.querySelector(".atk-spear");
    if (hs) hs.style.opacity = show ? "1" : "0";
  }
  function spawnDebris(freeze) {
    const host = el.debris;
    host.innerHTML = "";
    for (let i = 0; i < 14; i++) {
      const s = document.createElement("div");
      s.className = "shard";
      const sz = 6 + Math.random() * 9;
      const dx = (Math.random() < 0.5 ? -1 : 1) * (18 + Math.random() * 95);
      const dy = -(28 + Math.random() * 95);
      const rot = (Math.random() * 760 - 380).toFixed(0) + "deg";
      const dur = 0.7 + Math.random() * 0.55;
      s.style.width = s.style.height = sz.toFixed(0) + "px";
      s.style.left = (Math.random() * 46 - 23).toFixed(0) + "px";
      s.style.top = (Math.random() * 34 - 17).toFixed(0) + "px";
      s.style.setProperty("--dx", dx.toFixed(0) + "px");
      s.style.setProperty("--dy", dy.toFixed(0) + "px");
      s.style.setProperty("--rot", rot);
      s.style.setProperty("--dur", dur.toFixed(2) + "s");
      if (freeze) { s.style.animationDelay = "-" + (dur * 0.42).toFixed(2) + "s"; s.style.animationPlayState = "paused"; }
      host.appendChild(s);
    }
  }
  async function throwSpear(kind, tok) {
    const p = el.projectile;
    const flightMs = kind === "breach" ? 920 : 820;
    // scale the CSS flight duration by playback speed so the spear's travel stays in
    // sync with the wait timer (otherwise at high speed it's hidden mid-flight).
    p.style.setProperty("--flight", (flightMs / speedMul() / 1000).toFixed(3) + "s");

    // wind-up: lean back (deliberately), then explosively release
    const atk = el.attackerSvg;
    atk.classList.remove("lunge");
    atk.classList.add("windup");
    if (!(await sleep(320, tok))) { atk.classList.remove("windup"); return false; }
    atk.classList.remove("windup");
    atk.classList.add("release");
    handSpear(false); // the spear leaves his hand
    p.className = "projectile"; void p.offsetWidth;
    p.classList.add(kind === "breach" ? "throw-breach" : "throw-block");
    setTimeout(() => atk.classList.remove("release"), 260);
    if (!(await sleep(flightMs, tok))) return false;

    // impact at the landing point
    if (kind === "breach") {
      spark("89%", "236px", true);
      el.battlefield.classList.remove("shake"); void el.battlefield.offsetWidth;
      el.battlefield.classList.add("shake");
      setTimeout(() => el.battlefield.classList.remove("shake"), 520);
      spawnDebris(false);
      el.defenderSvg.classList.add("stagger");
      setTimeout(() => el.defenderSvg.classList.remove("stagger"), 550);
    } else {
      spark("78.5%", "196px", false);
      el.defenderSvg.classList.add("brace");
      setTimeout(() => el.defenderSvg.classList.remove("brace"), 480);
    }
    if (!(await sleep(240, tok))) return false;
    p.classList.remove("throw-block", "throw-breach");
    p.style.opacity = "0";
    handSpear(true); // a fresh spear for the next volley
    return true;
  }

  function spark(left, bottom, breach) {
    const s = el.impact;
    s.style.left = left; s.style.bottom = bottom;
    s.className = "impact" + (breach ? " breach" : "");
    void s.offsetWidth;
    s.classList.add("spark");
  }

  // ---------- end states ----------
  function showBreachState(instant) {
    const conf = run.breach_type === "CONFIDENTIALITY";
    el.castle.classList.add("rubble");
    el.treasure.classList.add("exposed");
    el.treasureValue.textContent = conf ? (run.canary || "LEAKED") : "⚠ OVERRIDE FIRED";
    el.statusVal.textContent = conf ? "🔓 LEAKED" : "⚠ OVERRIDDEN";
    el.statusCell.classList.add("breached");
    el.statusCell.classList.remove("held");
    const br = run.breach_round;
    el.banner.className = "banner breach" + (instant ? " show" : "");
    el.banner.innerHTML = `💥 BREACH — round ${br}<small>${conf ? "canary token leaked" : "forbidden tool invoked"}</small>`;
    if (!instant) { el.banner.classList.remove("show"); void el.banner.offsetWidth; el.banner.classList.add("show"); }
    showJudgeCard();
  }
  function showHoldState(instant) {
    el.castle.classList.add("victory");
    el.statusVal.textContent = run.breach_type === "CONFIDENTIALITY" ? "🔒 Secure" : "🔒 Held";
    el.statusCell.classList.add("held");
    el.banner.className = "banner hold" + (instant ? " show" : "");
    el.banner.innerHTML = `🛡️ CASTLE HELD — ${run.k_max} rounds<small>${esc(run.hold_line)}</small>`;
    if (!instant) { el.banner.classList.remove("show"); void el.banner.offsetWidth; el.banner.classList.add("show"); }
    // fade banner after a beat so it doesn't cover the scene
    const myTok = token;
    setTimeout(() => { if (myTok === token) el.banner.classList.remove("show"); }, 4200 / speedMul());
    showJudgeCard();
  }

  // ---------- Judge's ruling (SECONDARY; verdict baked in, never live) ----------
  const V_LABEL = { PERSONA_BREAK: "Persona break", WEAK_REFUSAL: "Weak refusal", NO_DEGRADATION: "No degradation" };
  function hideJudgeCard() {
    el.judgeCard.classList.remove("show", "degraded", "clean");
    el.judgeCard.setAttribute("aria-hidden", "true");
  }
  function judgeTakeaway(degraded) {
    const breach = !run.held;
    if (breach && degraded) return "Both signals agree — the persona collapsed <b>and</b> the secret leaked.";
    if (breach && !degraded) return "The secret leaked even though the Judge saw no persona break — the <b>deterministic detector is the ground truth</b>.";
    if (!breach && !degraded) return "Both agree — it refused <b>in character</b>. The defence held.";
    return "The Judge thought the guard fell — but the code confirms nothing leaked. <b>This is exactly why breaches are decided by code, not by an AI.</b>";
  }
  function showJudgeCard() {
    const j = run.judge;
    if (!j) { hideJudgeCard(); return; }
    const degraded = j.verdict !== "NO_DEGRADATION";
    el.jcBadge.textContent = V_LABEL[j.verdict] || j.verdict;
    el.jcBadge.className = "jc-badge " + (degraded ? "degraded" : "clean");
    el.jcScore.textContent = `degradation ${j.score} / 4`;
    const outcome = run.held ? "code says <b>HELD</b>" : "code says <b>BREACHED</b>";
    el.jcVersus.innerHTML = `· ${outcome}`;
    el.jcRationale.textContent = "“" + j.rationale + "”";
    el.jcTakeaway.innerHTML = judgeTakeaway(degraded);
    el.judgeCard.classList.remove("degraded", "clean");
    el.judgeCard.classList.add(degraded ? "degraded" : "clean", "show");
    el.judgeCard.setAttribute("aria-hidden", "false");
  }

  // ---------- playback loop ----------
  async function play() {
    if (playing) return;
    if (ptr >= run.n_rounds) renderStatic(0); // restart if at end
    playing = true; setPlayBtn();
    const myTok = token; // note: revealNext bumps token each round, so track loosely
    while (playing && run && ptr < run.n_rounds) {
      const ok = await revealNext();
      if (!ok) break;
      if (!playing) break;
      const done = await sleep(ptr >= run.n_rounds ? 1200 : 1600, token);
      if (!done && playing) { /* token bumped by us; keep going */ }
      if (!playing) break;
    }
    playing = false; setPlayBtn();
    updateControls();
  }
  function pause() { playing = false; token++; busy = false; setPlayBtn(); updateControls(); }

  function setPlayBtn() {
    if (playing) el.btnPlay.textContent = "❚❚ Pause";
    else el.btnPlay.textContent = ptr >= (run ? run.n_rounds : 0) && ptr > 0 ? "↻ Replay" : "▶ Play";
  }

  function updateControls() {
    const atEnd = run ? ptr >= run.n_rounds : true;
    el.btnNext.disabled = busy || atEnd;
    el.btnPrev.disabled = busy || ptr <= 0;
    el.btnRestart.disabled = busy || ptr === 0;
    el.btnPlay.disabled = !run;
  }

  // ---------- controls ----------
  el.btnPlay.addEventListener("click", () => (playing ? pause() : play()));
  el.btnNext.addEventListener("click", async () => { if (playing) pause(); await revealNext(); });
  el.btnPrev.addEventListener("click", () => { if (playing) pause(); renderStatic(Math.max(0, ptr - 1)); setPlayBtn(); });
  el.btnRestart.addEventListener("click", () => { if (playing) pause(); renderStatic(0); setPlayBtn(); });
  el.speed.addEventListener("input", () => { el.speedVal.textContent = el.speed.value + "×"; });

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
    if (e.code === "Space") { e.preventDefault(); playing ? pause() : play(); }
    else if (e.code === "ArrowRight") { if (playing) pause(); revealNext(); }
    else if (e.code === "ArrowLeft") { if (playing) pause(); renderStatic(Math.max(0, ptr - 1)); setPlayBtn(); }
  });

  // ---------- boot ----------
  if (!RUNS.length) {
    el.dialogueEmpty.textContent = "No transcripts baked in. Run:  python demo/build_replay_data.py";
    return;
  }
  populateRuns();
  el.runSelect.value = "0";
  loadRun(RUNS[0]);

  // ---------- debug hooks (screenshot tuning only; harmless in normal use) ----------
  // ?run=N pick a run · ?jump=N reveal first N rounds statically (shows end-state)
  // ?spear=block|breach freeze the spear at its landing point + fire the impact
  const qs = new URLSearchParams(location.search);
  if (qs.has("run")) { const n = +qs.get("run"); el.runSelect.value = String(n); loadRun(RUNS[n] || RUNS[0]); }
  if (qs.has("jump")) renderStatic(Math.max(0, Math.min(run.n_rounds, +qs.get("jump"))));
  if (qs.has("spear")) {
    const kind = qs.get("spear") === "breach" ? "breach" : "block";
    el.projectile.className = "projectile " + (kind === "breach" ? "at-breach-end" : "at-block-end");
    if (kind === "breach") spark("89%", "236px", true); else spark("78.5%", "196px", false);
  }
  if (qs.has("arc")) { // freeze the throw animation mid-flight to inspect the arc
    const breach = qs.get("arc") === "breach";
    handSpear(false);
    el.projectile.style.opacity = "1";
    el.projectile.style.animation = `${breach ? "throwBreach" : "throwBlock"} 1s linear ${qs.get("t") || "-0.45"}s paused forwards`;
  }
  if (qs.has("fx")) { // freeze the breach FX (debris burst) for inspection
    renderStatic(run.n_rounds);
    spawnDebris(true);
  }
})();

// Themed scenes for the siege replay. Each attack VECTOR maps to a theme; the siege
// mechanic (attack -> block / breach -> secret reveal) is identical, only the ART swaps.
// Every theme's `fortressHtml` MUST provide the hooks the animation code drives:
//   #wall (the body that quakes/cracks), #treasure (#treasureIcon/#treasureLabel/#treasureValue), #crack.
// AUTO-loaded before app.js. Self-contained (inline SVG/HTML), offline.

window.BREACHBENCH_THEMES = {

  // ============================ REALM (Roleplay) ============================
  realm: {
    attackerSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="atkCape" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f0424f"/><stop offset="1" stop-color="#8f0f1b"/></linearGradient>
          <linearGradient id="atkIron" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9aa5bb"/><stop offset="1" stop-color="#4a5468"/></linearGradient>
          <linearGradient id="atkSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4c8a2"/><stop offset="1" stop-color="#d99a6c"/></linearGradient>
        </defs>
        <ellipse cx="64" cy="165" rx="33" ry="6.5" fill="rgba(0,0,0,0.22)"/>
        <path d="M44 66 Q22 116 36 154 L60 154 Q52 104 64 68 Z" fill="url(#atkCape)" stroke="#5e0a12" stroke-width="1.5"/>
        <rect x="50" y="126" width="12" height="28" rx="5" fill="#33200f"/>
        <rect x="64" y="126" width="12" height="28" rx="5" fill="#41290f"/>
        <ellipse cx="55" cy="156" rx="9" ry="4" fill="#241608"/>
        <ellipse cx="71" cy="156" rx="9" ry="4" fill="#2c1b0a"/>
        <path d="M48 76 Q46 110 52 132 L76 132 Q82 108 78 76 Q63 68 48 76 Z" fill="url(#atkIron)" stroke="#2f3644" stroke-width="1.6"/>
        <path d="M63 74 L63 132" stroke="#2f3644" stroke-width="1" opacity="0.45"/>
        <path d="M46 74 Q63 65 80 74 L75 90 Q63 83 51 90 Z" fill="url(#atkCape)"/>
        <circle cx="63" cy="52" r="13.5" fill="url(#atkSkin)"/>
        <path d="M48 51 Q48 33 63 33 Q78 33 78 51 L78 46 Q63 40 48 46 Z" fill="url(#atkIron)" stroke="#2f3644" stroke-width="1.3"/>
        <rect x="48" y="48" width="30" height="5" rx="2" fill="#3a424f"/>
        <rect x="61" y="40" width="4" height="14" rx="1.5" fill="#3a424f"/>
        <path d="M63 33 Q56 15 69 11 Q61 23 66 33 Z" fill="#f0424f" stroke="#8f0f1b" stroke-width="1"/>
        <ellipse cx="43" cy="102" rx="13" ry="17" fill="#c23241" stroke="#e7d9c2" stroke-width="2.4"/>
        <ellipse cx="43" cy="102" rx="5" ry="7" fill="#f0d24a"/>
        <rect x="72" y="84" width="12" height="26" rx="6" fill="url(#atkSkin)"/>
        <g class="atk-spear" transform="rotate(-7 80 90)" style="transition: opacity 0.15s">
          <rect x="16" y="88" width="108" height="6" rx="3" fill="#8a6238" stroke="#5a3f28" stroke-width="1"/>
          <polygon points="124,91 110,82 110,100" fill="#e7edf6" stroke="#9aa7bd" stroke-width="1"/>
        </g>
      </svg>`,
    defenderSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="defTunic" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5aa8ff"/><stop offset="1" stop-color="#1b57a8"/></linearGradient>
          <linearGradient id="defSteel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dbe3f0"/><stop offset="1" stop-color="#8996ad"/></linearGradient>
          <linearGradient id="defSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4c8a2"/><stop offset="1" stop-color="#d99a6c"/></linearGradient>
        </defs>
        <ellipse cx="66" cy="165" rx="33" ry="6.5" fill="rgba(0,0,0,0.22)"/>
        <rect x="58" y="126" width="12" height="28" rx="5" fill="#22314d"/>
        <rect x="72" y="126" width="12" height="28" rx="5" fill="#2b3c5c"/>
        <ellipse cx="63" cy="156" rx="9" ry="4" fill="#16202f"/>
        <ellipse cx="79" cy="156" rx="9" ry="4" fill="#1b2637"/>
        <path d="M54 76 Q52 110 58 132 L84 132 Q90 108 86 76 Q70 68 54 76 Z" fill="url(#defTunic)" stroke="#123b73" stroke-width="1.6"/>
        <path d="M70 72 L70 132" stroke="#f0d24a" stroke-width="2" opacity="0.85"/>
        <ellipse cx="56" cy="78" rx="10" ry="7" fill="url(#defSteel)" stroke="#6c7a92" stroke-width="1"/>
        <ellipse cx="86" cy="78" rx="10" ry="7" fill="url(#defSteel)" stroke="#6c7a92" stroke-width="1"/>
        <rect x="90" y="30" width="5.5" height="122" rx="2.7" fill="#8a6238" stroke="#5a3f28" stroke-width="1"/>
        <polygon points="92.7,18 85,34 100,34" fill="url(#defSteel)" stroke="#6c7a92" stroke-width="1"/>
        <circle cx="70" cy="52" r="13.5" fill="url(#defSkin)"/>
        <path d="M55 52 Q55 33 70 33 Q85 33 85 52 Q85 43 70 39 Q55 43 55 52 Z" fill="url(#defSteel)" stroke="#6c7a92" stroke-width="1.3"/>
        <rect x="68" y="39" width="4" height="15" rx="1.5" fill="#8996ad"/>
        <path d="M70 33 Q77 15 64 11 Q72 23 67 33 Z" fill="#5aa8ff" stroke="#1b57a8" stroke-width="1"/>
        <g id="shieldGrp">
          <path d="M28 58 Q28 49 44 49 Q60 49 60 58 L60 100 Q44 124 28 100 Z" fill="url(#defSteel)" stroke="#6c7a92" stroke-width="2.6"/>
          <path d="M34 61 Q34 55 44 55 Q54 55 54 61 L54 96 Q44 114 34 96 Z" fill="url(#defTunic)"/>
          <path d="M44 70 l2.6 5.3 5.8 .5 -4.4 3.8 1.4 5.7 -5.4 -3 -5.4 3 1.4 -5.7 -4.4 -3.8 5.8 -.5 z" fill="#f0d24a" stroke="#c9a52e" stroke-width="0.6"/>
        </g>
      </svg>`,
    sceneHtml: `
      <div class="sun"></div>
      <div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div>
      <div class="birds b1">︿ ︿</div>
      <div class="hills-far"></div><div class="hills-mid"></div><div class="castle-mound"></div>
      <div class="ground"></div><div class="path"></div>
      <div class="tree t1"></div><div class="tree t2"></div>
      <div class="bush bu1"></div><div class="bush bu2"></div>`,
    fortressHtml: `
      <div class="battlement"><span></span><span></span><span></span><span></span><span></span></div>
      <div class="wall" id="wall">
        <div class="gate" id="gate"></div>
        <div class="treasure" id="treasure">
          <span class="treasure-icon" id="treasureIcon">🔑</span>
          <span class="treasure-label" id="treasureLabel">Access Token</span>
          <span class="treasure-value" id="treasureValue">••••••••••••</span>
        </div>
        <div class="crack" id="crack"></div>
      </div>`,
    projectileSvg: `<svg viewBox="0 0 62 12" width="62" height="12">
        <rect x="0" y="4.4" width="50" height="3.6" rx="1.6" fill="#8a6238" stroke="#5a3f28" stroke-width="0.6"/>
        <polygon points="62,6 47,0.5 47,11.5" fill="#e7edf6" stroke="#9aa7bd" stroke-width="0.6"/></svg>`,
  },

  // ============================ OFFICE (Authority) ============================
  office: {
    attackerSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="offSuit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3c4459"/><stop offset="1" stop-color="#232838"/></linearGradient>
          <linearGradient id="offSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4c8a2"/><stop offset="1" stop-color="#d99a6c"/></linearGradient>
        </defs>
        <ellipse cx="63" cy="165" rx="30" ry="6" fill="rgba(0,0,0,0.2)"/>
        <rect x="52" y="120" width="12" height="34" rx="4" fill="#2a3040"/>
        <rect x="66" y="120" width="12" height="34" rx="4" fill="#222735"/>
        <ellipse cx="57" cy="156" rx="9" ry="4" fill="#12151d"/>
        <ellipse cx="73" cy="156" rx="9" ry="4" fill="#12151d"/>
        <path d="M47 74 Q43 108 52 129 L79 129 Q87 106 83 74 Q65 66 47 74 Z" fill="url(#offSuit)" stroke="#171b25" stroke-width="1.4"/>
        <path d="M60 74 L65 98 L70 74 Z" fill="#eef2f8"/>
        <path d="M63.6 78 L66.4 78 L68 102 L65 108 L62 102 Z" fill="#d1343f"/>
        <path d="M60 74 L55 94 L61 80 Z" fill="#2c3244"/><path d="M70 74 L75 94 L69 80 Z" fill="#2c3244"/>
        <circle cx="65" cy="52" r="13" fill="url(#offSkin)"/>
        <path d="M52 50 Q51 33 65 33 Q79 33 78 50 Q76 41 65 41 Q54 42 52 50 Z" fill="#3a2c22"/>
        <!-- pointing arm (authority) -->
        <g transform="rotate(-8 80 84)">
          <rect x="78" y="80" width="34" height="10" rx="5" fill="url(#offSuit)"/>
          <rect x="108" y="80.5" width="18" height="8" rx="4" fill="url(#offSkin)"/>
        </g>
      </svg>`,
    defenderSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="botBody" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eaf0f8"/><stop offset="1" stop-color="#b9c6d8"/></linearGradient>
          <linearGradient id="botFace" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b6ec2"/><stop offset="1" stop-color="#0f4e91"/></linearGradient>
        </defs>
        <ellipse cx="66" cy="165" rx="30" ry="6" fill="rgba(0,0,0,0.2)"/>
        <!-- little legs -->
        <rect x="57" y="132" width="10" height="22" rx="4" fill="#8996ad"/>
        <rect x="72" y="132" width="10" height="22" rx="4" fill="#8996ad"/>
        <ellipse cx="62" cy="156" rx="8" ry="3.5" fill="#5a6577"/><ellipse cx="77" cy="156" rx="8" ry="3.5" fill="#5a6577"/>
        <!-- rounded robot body -->
        <rect x="48" y="74" width="44" height="62" rx="18" fill="url(#botBody)" stroke="#93a1b5" stroke-width="1.6"/>
        <rect x="55" y="86" width="30" height="20" rx="6" fill="#0d3f78"/>
        <circle cx="65" cy="96" r="3.2" fill="#7fd7ff"/><circle cx="76" cy="96" r="3.2" fill="#7fd7ff"/>
        <!-- head with screen face -->
        <rect x="52" y="40" width="36" height="30" rx="12" fill="url(#botBody)" stroke="#93a1b5" stroke-width="1.6"/>
        <rect x="57" y="46" width="26" height="18" rx="7" fill="url(#botFace)"/>
        <circle cx="66" cy="55" r="3.2" fill="#bff0ff"/><circle cx="76" cy="55" r="3.2" fill="#bff0ff"/>
        <rect x="68.5" y="30" width="3" height="11" fill="#8996ad"/><circle cx="70" cy="28" r="3.5" fill="#43d17a"/>
        <!-- clipboard 'shield' raised to the left -->
        <g id="shieldGrp">
          <rect x="24" y="58" width="30" height="42" rx="4" fill="#e7ecf3" stroke="#9aa7bd" stroke-width="2.4"/>
          <rect x="34" y="55" width="10" height="7" rx="2" fill="#8996ad"/>
          <rect x="29" y="68" width="20" height="3" rx="1.5" fill="#1b6ec2"/>
          <rect x="29" y="76" width="20" height="3" rx="1.5" fill="#c3ccd9"/>
          <rect x="29" y="84" width="14" height="3" rx="1.5" fill="#c3ccd9"/>
        </g>
      </svg>`,
    sceneHtml: `
      <div class="off-window"><span class="b1"></span><span class="b2"></span><span class="b3"></span><span class="b4"></span></div>
      <div class="off-wall-line"></div>
      <div class="off-floor"></div>
      <div class="off-desk"></div>
      <div class="off-plant"></div>`,
    fortressHtml: `
      <div class="wall id-cabinet" id="wall">
        <div class="cab-top"></div>
        <div class="treasure" id="treasure">
          <span class="treasure-icon" id="treasureIcon">🔑</span>
          <span class="treasure-label" id="treasureLabel">Access Token</span>
          <span class="treasure-value" id="treasureValue">••••••••••••</span>
        </div>
        <div class="cab-handle a"></div><div class="cab-handle b"></div>
        <div class="crack" id="crack"></div>
      </div>`,
    projectileSvg: `<svg viewBox="0 0 62 34" width="62" height="34">
        <rect x="2" y="4" width="48" height="26" rx="2" fill="#f4f6fa" stroke="#c3ccd9" stroke-width="1.2" transform="rotate(-6 26 17)"/>
        <rect x="9" y="11" width="30" height="2.4" rx="1" fill="#c0343f" transform="rotate(-6 26 17)"/>
        <rect x="9" y="17" width="34" height="2" rx="1" fill="#aab4c4" transform="rotate(-6 26 17)"/>
        <rect x="9" y="22" width="24" height="2" rx="1" fill="#aab4c4" transform="rotate(-6 26 17)"/></svg>`,
  },

  // ============================ CIPHER DEN (Cipher) ============================
  cipher: {
    attackerSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="cipHood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b3a45"/><stop offset="1" stop-color="#151f26"/></linearGradient>
          <linearGradient id="cipSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9c39c"/><stop offset="1" stop-color="#c98f63"/></linearGradient>
        </defs>
        <ellipse cx="64" cy="165" rx="31" ry="6" fill="rgba(0,0,0,0.28)"/>
        <rect x="52" y="126" width="12" height="28" rx="5" fill="#131b20"/>
        <rect x="66" y="126" width="12" height="28" rx="5" fill="#0e1418"/>
        <path d="M46 70 Q40 112 50 150 L80 150 Q88 110 82 70 Q64 60 46 70 Z" fill="url(#cipHood)" stroke="#0c1216" stroke-width="1.5"/>
        <!-- hood over head -->
        <path d="M47 60 Q47 30 65 30 Q83 30 83 60 Q83 44 65 44 Q49 46 47 60 Z" fill="url(#cipHood)"/>
        <ellipse cx="65" cy="54" r="12" rx="12" ry="12" fill="url(#cipSkin)"/>
        <path d="M49 56 Q49 34 65 34 Q81 34 81 56 Q81 44 65 45 Q51 46 49 56 Z" fill="url(#cipHood)" opacity="0.75"/>
        <ellipse cx="60" cy="55" rx="2.3" ry="2.6" fill="#25e0c0"/><ellipse cx="70" cy="55" rx="2.3" ry="2.6" fill="#25e0c0"/>
        <!-- arm holding a glowing coded scroll -->
        <rect x="74" y="86" width="12" height="24" rx="6" fill="url(#cipSkin)"/>
        <g transform="rotate(-6 92 92)">
          <rect x="84" y="82" width="30" height="20" rx="3" fill="#0f2b28" stroke="#25e0c0" stroke-width="1.4"/>
          <text x="88" y="90" font-family="monospace" font-size="7" fill="#25e0c0">4f2a</text>
          <text x="88" y="98" font-family="monospace" font-size="7" fill="#1fae95">b7==</text>
        </g>
      </svg>`,
    defenderSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="clkVest" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b8f7e"/><stop offset="1" stop-color="#1f5d51"/></linearGradient>
          <linearGradient id="clkSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4c8a2"/><stop offset="1" stop-color="#d99a6c"/></linearGradient>
        </defs>
        <ellipse cx="66" cy="165" rx="30" ry="6" fill="rgba(0,0,0,0.28)"/>
        <rect x="58" y="128" width="12" height="26" rx="4" fill="#243b36"/>
        <rect x="72" y="128" width="12" height="26" rx="4" fill="#1c2f2b"/>
        <ellipse cx="63" cy="156" rx="8.5" ry="3.5" fill="#12201d"/><ellipse cx="78" cy="156" rx="8.5" ry="3.5" fill="#12201d"/>
        <path d="M54 76 Q52 110 58 130 L84 130 Q90 108 86 76 Q70 68 54 76 Z" fill="url(#clkVest)" stroke="#123f37" stroke-width="1.5"/>
        <circle cx="70" cy="52" r="13" fill="url(#clkSkin)"/>
        <path d="M57 48 Q57 34 70 34 Q83 34 83 48 Q80 40 70 41 Q60 42 57 48 Z" fill="#33251c"/>
        <!-- glasses -->
        <circle cx="65" cy="52" r="4.2" fill="none" stroke="#173a34" stroke-width="1.6"/><circle cx="76" cy="52" r="4.2" fill="none" stroke="#173a34" stroke-width="1.6"/>
        <line x1="69" y1="52" x2="72" y2="52" stroke="#173a34" stroke-width="1.6"/>
        <!-- tablet 'shield' raised left, showing a lock -->
        <g id="shieldGrp">
          <rect x="26" y="58" width="30" height="42" rx="4" fill="#0f2b28" stroke="#25e0c0" stroke-width="2.4"/>
          <rect x="35" y="74" width="12" height="11" rx="2" fill="#25e0c0"/>
          <path d="M37 74 v-3 a4 4 0 0 1 8 0 v3" fill="none" stroke="#25e0c0" stroke-width="2"/>
        </g>
      </svg>`,
    sceneHtml: `
      <div class="cip-glow"></div>
      <div class="cip-code c1">01001</div><div class="cip-code c2">4f2a9</div>
      <div class="cip-code c3">b7d==</div><div class="cip-code c4">10x3f</div>
      <div class="cip-monitor m1"></div><div class="cip-monitor m2"></div>
      <div class="cip-floor"></div>`,
    fortressHtml: `
      <div class="wall id-safe" id="wall">
        <div class="safe-dial"></div>
        <div class="treasure" id="treasure">
          <span class="treasure-icon" id="treasureIcon">🔑</span>
          <span class="treasure-label" id="treasureLabel">Access Token</span>
          <span class="treasure-value" id="treasureValue">••••••••••••</span>
        </div>
        <div class="crack" id="crack"></div>
      </div>`,
    projectileSvg: `<svg viewBox="0 0 64 20" width="64" height="20">
        <rect x="2" y="4" width="52" height="13" rx="2" fill="#0f2b28" stroke="#25e0c0" stroke-width="1.2"/>
        <text x="7" y="14" font-family="monospace" font-size="9" fill="#25e0c0">4f2a b7==</text>
        <polygon points="64,10.5 54,4 54,17" fill="#25e0c0"/></svg>`,
  },

  // ============================ SWARM (Many-shot) ============================
  swarm: {
    attackerSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <radialGradient id="swClone" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#b06bd6"/><stop offset="1" stop-color="#6a2f97"/></radialGradient>
        </defs>
        <ellipse cx="64" cy="166" rx="40" ry="7" fill="rgba(0,0,0,0.22)"/>
        <!-- a crowd of identical little clone figures -->
        <g fill="url(#swClone)" stroke="#3f1a63" stroke-width="1">
          <g transform="translate(12,96)"><circle cx="10" cy="10" r="9"/><rect x="3" y="17" width="14" height="26" rx="6"/></g>
          <g transform="translate(30,84)"><circle cx="10" cy="10" r="9"/><rect x="3" y="17" width="14" height="30" rx="6"/></g>
          <g transform="translate(50,74)"><circle cx="10" cy="10" r="10"/><rect x="2" y="18" width="16" height="34" rx="7"/></g>
          <g transform="translate(26,110)"><circle cx="9" cy="9" r="8"/><rect x="3" y="15" width="12" height="24" rx="5"/></g>
          <g transform="translate(46,104)"><circle cx="9" cy="9" r="8"/><rect x="3" y="15" width="12" height="26" rx="5"/></g>
          <g transform="translate(66,92)" opacity="0.9"><circle cx="9" cy="9" r="8"/><rect x="3" y="15" width="12" height="28" rx="5"/></g>
        </g>
      </svg>`,
    defenderSvg: `
      <svg viewBox="0 0 130 172" width="118" height="156" aria-hidden="true">
        <defs>
          <linearGradient id="gdCoat" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e0a94a"/><stop offset="1" stop-color="#a9781f"/></linearGradient>
          <linearGradient id="gdSkin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4c8a2"/><stop offset="1" stop-color="#d99a6c"/></linearGradient>
        </defs>
        <ellipse cx="66" cy="165" rx="30" ry="6" fill="rgba(0,0,0,0.25)"/>
        <rect x="58" y="128" width="12" height="26" rx="4" fill="#4a3410"/>
        <rect x="72" y="128" width="12" height="26" rx="4" fill="#3a2909"/>
        <ellipse cx="63" cy="156" rx="8.5" ry="3.5" fill="#241705"/><ellipse cx="78" cy="156" rx="8.5" ry="3.5" fill="#241705"/>
        <path d="M54 76 Q52 110 58 130 L84 130 Q90 108 86 76 Q70 68 54 76 Z" fill="url(#gdCoat)" stroke="#7a5615" stroke-width="1.6"/>
        <path d="M70 72 L70 130" stroke="#5f4210" stroke-width="2" opacity="0.6"/>
        <circle cx="70" cy="52" r="13" fill="url(#gdSkin)"/>
        <path d="M56 50 Q56 32 70 32 Q84 32 84 50 L84 46 Q70 40 56 46 Z" fill="#7a5615"/>
        <rect x="56" y="47" width="28" height="5" rx="2" fill="#5f4210"/>
        <!-- big riot-style shield to the left -->
        <g id="shieldGrp">
          <rect x="24" y="54" width="32" height="52" rx="8" fill="#c9d2df" stroke="#8996ad" stroke-width="2.6"/>
          <rect x="30" y="60" width="20" height="40" rx="6" fill="#e0a94a" opacity="0.85"/>
          <circle cx="40" cy="80" r="6" fill="#fff" stroke="#8996ad" stroke-width="1.5"/>
        </g>
      </svg>`,
    sceneHtml: `
      <div class="sw-sky"></div>
      <div class="sw-sun"></div>
      <div class="sw-hills"></div>
      <div class="sw-ground"></div>
      <div class="sw-marks"></div>`,
    fortressHtml: `
      <div class="wall id-vault" id="wall">
        <div class="vault-pillars"><span></span><span></span></div>
        <div class="treasure" id="treasure">
          <span class="treasure-icon" id="treasureIcon">🔑</span>
          <span class="treasure-label" id="treasureLabel">Access Token</span>
          <span class="treasure-value" id="treasureValue">••••••••••••</span>
        </div>
        <div class="crack" id="crack"></div>
      </div>`,
    projectileSvg: `<svg viewBox="0 0 40 40" width="40" height="40">
        <g fill="#8a44c0" stroke="#4a1e70" stroke-width="1"><circle cx="20" cy="13" r="8"/><rect x="13" y="20" width="14" height="18" rx="6"/></g></svg>`,
  },

};

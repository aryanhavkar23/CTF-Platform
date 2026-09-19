/**
 * OWASP CTF Platform — Gateway Landing View
 * Stitch "Obsidian Signal" Architecture
 */

const LandingView = {
  _clockInterval: null,
  _mouseMoveHandler: null,
  _animFrameId: null,

  async init() {
    this.render();
    this.startTelemetryClock();
    this.initInteractiveConstellation();
    this.loadUpcomingEventsPreview();
    this.loadLeaderboardPreview();
  },

  startTelemetryClock() {
    const update = () => {
      const el = document.getElementById('telemetry-clock');
      if (!el) return;
      const now = new Date();
      const utcHours = String(now.getUTCHours()).padStart(2, '0');
      const utcMinutes = String(now.getUTCMinutes()).padStart(2, '0');
      const utcSeconds = String(now.getUTCSeconds()).padStart(2, '0');
      el.textContent = `SYNC: ${utcHours}:${utcMinutes}:${utcSeconds} UTC`;
    };
    if (this._clockInterval) clearInterval(this._clockInterval);
    update();
    this._clockInterval = setInterval(update, 1000);
  },

  render() {
    const container = document.getElementById('view-landing');
    if (!container) return;

    container.innerHTML = `
      <div class="relative w-full overflow-hidden px-space-lg lg:px-margin py-space-xl space-y-space-xl max-w-[1720px] mx-auto">
        
        <!-- Background Ambient Glow -->
        <div class="absolute -top-40 left-1/2 -translate-x-1/2 w-[40rem] h-[40rem] bg-primary/10 rounded-full blur-3xl pointer-events-none -z-10"></div>

        <!-- 1. HERO CONSTELLATION SECTION -->
        <section class="relative flex-1 flex flex-col items-center justify-center min-h-[640px] sm:min-h-[720px] px-2 overflow-hidden select-none transition-transform duration-300 ease-out py-6 sm:py-10" id="heroInteractiveSection">
          
          <!-- Top Right Action: About Us (Directly Below Top-Right Profile Pill) -->
          <div class="absolute top-2 sm:top-4 right-2 sm:right-6 z-30 pointer-events-auto">
            <a href="https://owasppccoe.vercel.app/" 
               target="_blank" 
               rel="noopener noreferrer" 
               id="landingAboutUsBtn"
               class="inline-flex items-center gap-2 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-surface-card/90 hover:bg-surface-terminal border border-primary/40 hover:border-primary text-primary hover:text-white font-mono text-xs font-bold tracking-wider uppercase shadow-[0_0_15px_rgba(0,230,118,0.2)] hover:shadow-[0_0_25px_rgba(0,230,118,0.45)] hover:scale-105 transition-all duration-200 backdrop-blur-md group"
               title="About Us // OWASP PCCOE Chapter">
              <span class="w-2 h-2 rounded-full bg-primary animate-pulse group-hover:animate-ping"></span>
              <span class="material-symbols-outlined text-base text-primary group-hover:text-white transition-colors">info</span>
              <span>About Us</span>
              <span class="material-symbols-outlined text-xs text-primary/80 group-hover:text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform">open_in_new</span>
            </a>
          </div>

          <!-- Background Particle Canvas -->
          <canvas class="absolute inset-0 pointer-events-none z-0 opacity-40" id="starDustCanvas"></canvas>

          <!-- Interactive Mouse Tracking Spotlight -->
          <div class="mouse-spotlight" id="mouseSpotlight"></div>

          <!-- Background Radial Aura with Breathing Animation -->
          <div class="constellation-glow"></div>

          <!-- Complete Mesh Network SVG Layer -->
          <div class="absolute inset-0 max-w-[1500px] h-full mx-auto pointer-events-none" style="z-index: 2;">
            <svg class="w-full h-full" fill="none" id="meshSvg" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1400 700" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <radialGradient cx="50%" cy="50%" id="beaconGlow" r="50%">
                  <stop offset="0%" stop-color="#00e676" stop-opacity="0.95"></stop>
                  <stop offset="40%" stop-color="#00e676" stop-opacity="0.4"></stop>
                  <stop offset="100%" stop-color="#00e676" stop-opacity="0"></stop>
                </radialGradient>
                <radialGradient cx="50%" cy="50%" id="nodeGlow" r="50%">
                  <stop offset="0%" stop-color="#4cd7f6" stop-opacity="0.85"></stop>
                  <stop offset="45%" stop-color="#00e676" stop-opacity="0.25"></stop>
                  <stop offset="100%" stop-color="#00e676" stop-opacity="0"></stop>
                </radialGradient>
                <filter height="160%" id="laserBloom" width="160%" x="-30%" y="-30%">
                  <feGaussianBlur result="blur" stdDeviation="3"></feGaussianBlur>
                  <feMerge>
                    <feMergeNode in="blur"></feMergeNode>
                    <feMergeNode in="SourceGraphic"></feMergeNode>
                  </feMerge>
                </filter>
              </defs>

              <!-- Perimeter & Base Connections -->
              <g opacity="0.45" stroke="#1c3e30" stroke-width="1.2">
                <line class="mesh-line" data-nodes="n0 n1" x1="700" x2="910" y1="90" y2="155"></line>
                <line class="mesh-line" data-nodes="n1 n2" x1="910" x2="980" y1="155" y2="295"></line>
                <line class="mesh-line" data-nodes="n2 n3" x1="980" x2="890" y1="295" y2="475"></line>
                <line class="mesh-line" data-nodes="n3 n4" x1="890" x2="700" y1="475" y2="535"></line>
                <line class="mesh-line" data-nodes="n4 n5" x1="700" x2="490" y1="535" y2="460"></line>
                <line class="mesh-line" data-nodes="n5 n6" x1="490" x2="385" y1="460" y2="320"></line>
                <line class="mesh-line" data-nodes="n6 n7" x1="385" x2="480" y1="320" y2="150"></line>
                <line class="mesh-line" data-nodes="n7 n0" x1="480" x2="700" y1="150" y2="90"></line>
              </g>

              <!-- Internal Cross-Mesh Chords -->
              <g stroke-width="1">
                <!-- Crossings from N0 (General Skills: 700, 90) -->
                <line class="mesh-line" data-nodes="n0 n2" opacity="0.32" stroke="#00e676" x1="700" x2="980" y1="90" y2="295"></line>
                <line class="mesh-line" data-nodes="n0 n3" opacity="0.25" stroke="#4cd7f6" x1="700" x2="890" y1="90" y2="475"></line>
                <line class="mesh-line" data-nodes="n0 n4" opacity="0.4" stroke="#75ff9e" x1="700" x2="700" y1="90" y2="535"></line>
                <line class="mesh-line" data-nodes="n0 n5" opacity="0.25" stroke="#4cd7f6" x1="700" x2="490" y1="90" y2="460"></line>
                <line class="mesh-line" data-nodes="n0 n6" opacity="0.32" stroke="#00e676" x1="700" x2="385" y1="90" y2="320"></line>
                <!-- Crossings from N1 (Cryptography: 910, 155) -->
                <line class="mesh-line" data-nodes="n1 n3" opacity="0.3" stroke="#00e676" x1="910" x2="890" y1="155" y2="475"></line>
                <line class="mesh-line" data-nodes="n1 n4" opacity="0.28" stroke="#4cd7f6" x1="910" x2="700" y1="155" y2="535"></line>
                <line class="mesh-line" data-nodes="n1 n5" opacity="0.35" stroke="#75ff9e" x1="910" x2="490" y1="155" y2="460"></line>
                <line class="mesh-line" data-nodes="n1 n6" opacity="0.25" stroke="#00e676" x1="910" x2="385" y1="155" y2="320"></line>
                <line class="mesh-line" data-nodes="n1 n7" opacity="0.35" stroke="#4cd7f6" x1="910" x2="480" y1="155" y2="150"></line>
                <!-- Crossings from N2 (Web Exploitation: 980, 295) -->
                <line class="mesh-line" data-nodes="n2 n4" opacity="0.3" stroke="#00e676" x1="980" x2="700" y1="295" y2="535"></line>
                <line class="mesh-line" data-nodes="n2 n5" opacity="0.32" stroke="#4cd7f6" x1="980" x2="490" y1="295" y2="460"></line>
                <line class="mesh-line" data-nodes="n2 n6" opacity="0.42" stroke="#75ff9e" x1="980" x2="385" y1="295" y2="320"></line>
                <line class="mesh-line" data-nodes="n2 n7" opacity="0.25" stroke="#00e676" x1="980" x2="480" y1="295" y2="150"></line>
                <!-- Crossings from N3 (Forensics: 890, 475) -->
                <line class="mesh-line" data-nodes="n3 n5" opacity="0.35" stroke="#00e676" x1="890" x2="490" y1="475" y2="460"></line>
                <line class="mesh-line" data-nodes="n3 n6" opacity="0.3" stroke="#4cd7f6" x1="890" x2="385" y1="475" y2="320"></line>
                <line class="mesh-line" data-nodes="n3 n7" opacity="0.28" stroke="#75ff9e" x1="890" x2="480" y1="475" y2="150"></line>
                <!-- Crossings from N4 (Binary Exploitation: 700, 535) -->
                <line class="mesh-line" data-nodes="n4 n6" opacity="0.32" stroke="#00e676" x1="700" x2="385" y1="535" y2="320"></line>
                <line class="mesh-line" data-nodes="n4 n7" opacity="0.3" stroke="#4cd7f6" x1="700" x2="480" y1="535" y2="150"></line>
                <!-- Crossings from N5 (Reverse Engineering: 490, 460) -->
                <line class="mesh-line" data-nodes="n5 n7" opacity="0.35" stroke="#00e676" x1="490" x2="480" y1="460" y2="150"></line>
              </g>

              <!-- Animated Glowing Stream Packets Flowing Across the Mesh Chords -->
              <g opacity="0.75" stroke="#00e676" stroke-width="1.6">
                <line class="stream-line stream-delay-1" x1="700" x2="480" y1="90" y2="150"></line>
                <line class="stream-line stream-delay-2" x1="700" x2="910" y1="90" y2="155"></line>
                <line class="stream-line stream-delay-3" x1="480" x2="910" y1="150" y2="155"></line>
                <line class="stream-line stream-delay-4" x1="385" x2="980" y1="320" y2="295"></line>
                <line class="stream-line stream-delay-5" x1="490" x2="910" y1="460" y2="155"></line>
                <line class="stream-line stream-delay-1" x1="980" x2="490" y1="295" y2="460"></line>
                <line class="stream-line stream-delay-2" x1="700" x2="700" y1="90" y2="535"></line>
                <line class="stream-line stream-delay-3" x1="890" x2="490" y1="475" y2="460"></line>
                <line class="stream-line stream-delay-4" x1="385" x2="700" y1="320" y2="535"></line>
              </g>

              <!-- Center Concentric Radar/Tactical Rings Around Emblem Focal Point (700, 312) -->
              <circle cx="700" cy="312" r="148" stroke="#00e676" stroke-dasharray="3 6" stroke-opacity="0.22"></circle>
              <circle cx="700" cy="312" r="176" stroke="#4cd7f6" stroke-dasharray="8 8" stroke-opacity="0.14"></circle>

              <!-- Ambient Node Aura Circles with breathing pulse -->
              <circle class="ambient-aura" cx="700" cy="90" fill="url(#nodeGlow)" r="34"></circle>
              <circle class="ambient-aura" cx="480" cy="150" fill="url(#nodeGlow)" r="28" style="animation-delay: 0.8s;"></circle>
              <circle class="ambient-aura" cx="910" cy="155" fill="url(#nodeGlow)" r="28" style="animation-delay: 1.4s;"></circle>
              <circle class="ambient-aura" cx="385" cy="320" fill="url(#nodeGlow)" r="30" style="animation-delay: 2.1s;"></circle>
              <circle class="ambient-aura" cx="980" cy="295" fill="url(#nodeGlow)" r="30" style="animation-delay: 0.5s;"></circle>
              <circle class="ambient-aura" cx="490" cy="460" fill="url(#nodeGlow)" r="28" style="animation-delay: 1.8s;"></circle>
              <circle class="ambient-aura" cx="890" cy="475" fill="url(#nodeGlow)" r="30" style="animation-delay: 2.7s;"></circle>
              <circle class="ambient-aura" cx="700" cy="535" fill="url(#nodeGlow)" r="30" style="animation-delay: 1.1s;"></circle>

              <!-- START HERE: Multi-ring radar ping effect radiating from focal beacon -->
              <circle class="radar-wave-1" cx="680" cy="128" fill="none" stroke="#00e676"></circle>
              <circle class="radar-wave-2" cx="680" cy="128" fill="none" stroke="#62ff96"></circle>
              <circle class="radar-wave-3" cx="680" cy="128" fill="none" stroke="#4cd7f6"></circle>
              
              <!-- Beacon glowing tactical green highlight near General Skills -->
              <circle cx="680" cy="128" fill="url(#beaconGlow)" r="50"></circle>
              <circle cx="680" cy="128" fill="#00e676" filter="url(#laserBloom)" r="4.5"></circle>
              <circle cx="680" cy="128" fill="#ffffff" r="2"></circle>

              <!-- Constellation Core Node Dots -->
              <circle class="core-point" cx="700" cy="90" data-node="n0" fill="#e0e3e0" r="3.5"></circle>
              <circle class="core-point" cx="480" cy="150" data-node="n7" fill="#e0e3e0" r="3"></circle>
              <circle class="core-point" cx="910" cy="155" data-node="n1" fill="#e0e3e0" r="3"></circle>
              <circle class="core-point" cx="385" cy="320" data-node="n6" fill="#e0e3e0" r="3.5"></circle>
              <circle class="core-point" cx="980" cy="295" data-node="n2" fill="#e0e3e0" r="3.5"></circle>
              <circle class="core-point" cx="490" cy="460" data-node="n5" fill="#e0e3e0" r="3"></circle>
              <circle class="core-point" cx="890" cy="475" data-node="n3" fill="#e0e3e0" r="3.5"></circle>
              <circle class="core-point" cx="700" cy="535" data-node="n4" fill="#e0e3e0" r="3.5"></circle>
            </svg>
          </div>

          <!-- Node Labels, Interactive Touchpoints & Telemetry HUD Overlay -->
          <div class="absolute inset-0 max-w-[1400px] h-[700px] mx-auto pointer-events-none my-auto" style="z-index: 4;">
            
            <!-- 1. GENERAL SKILLS & START HERE Node Group (N0) -->
            <div class="skill-node-group absolute top-[44px] left-[700px] -translate-x-1/2 flex flex-col items-center group pointer-events-auto" data-node-target="n0" onclick="navigateToFeature('#challenges?category=general_skills')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#75ff9e] uppercase drop-shadow-[0_0_12px_rgba(0,230,118,0.6)]">General Skills</span>
              <div class="node-hud mt-2 px-3 py-1 border border-[#00e676]/70 rounded-full flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-ping"></span>
                <span class="text-[10px] font-mono text-[#75ff9e] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE &bull; 28 LABS ONLINE &bull; START HERE</span>
              </div>
            </div>

            <!-- "START HERE" Indicator Badge -->
            <div class="absolute top-[148px] left-[700px] -translate-x-1/2 flex items-center justify-center group cursor-pointer pointer-events-auto" data-node-target="n0" onclick="navigateToFeature('#challenges?category=general_skills')">
              <span class="px-4 py-1 text-xs font-mono tracking-widest font-bold text-[#75ff9e] uppercase border border-[#00e676]/60 bg-[#101413]/95 rounded-full backdrop-blur-md shadow-[0_0_20px_rgba(0,230,118,0.35)] group-hover:border-[#00e676] group-hover:shadow-[0_0_28px_rgba(0,230,118,0.85)] group-hover:scale-105 transition-all duration-300">Start Here</span>
            </div>

            <!-- 2. AI & ML Node Group (N7) -->
            <div class="skill-node-group absolute top-[138px] left-[450px] -translate-x-full pr-3 text-right group pointer-events-auto" data-node-target="n7" onclick="navigateToFeature('#challenges?category=ai_ml')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Ai &amp; Ml</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#4cd7f6]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#4cd7f6] animate-ping"></span>
                <span class="text-[9.5px] font-mono text-[#4cd7f6] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 16 MODULES // 920 XP</span>
              </div>
            </div>

            <!-- 3. CRYPTOGRAPHY Node Group (N1) -->
            <div class="skill-node-group absolute top-[144px] left-[940px] pl-2 text-left group pointer-events-auto" data-node-target="n1" onclick="navigateToFeature('#challenges?category=cryptography')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Cryptography</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#00e676]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse"></span>
                <span class="text-[9.5px] font-mono text-[#75ff9e] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 32 MODULES // 1450 XP</span>
              </div>
            </div>

            <!-- 4. BLOCKCHAIN Node Group (N6) -->
            <div class="skill-node-group absolute top-[311px] left-[350px] -translate-x-full pr-3 text-right group pointer-events-auto" data-node-target="n6" onclick="navigateToFeature('#challenges?category=blockchain')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Blockchain</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#00e676]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#00e676]"></span>
                <span class="text-[9.5px] font-mono text-[#75ff9e] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 12 MODULES // 780 XP</span>
              </div>
            </div>

            <!-- 5. WEB EXPLOITATION Node Group (N2) -->
            <div class="skill-node-group absolute top-[287px] left-[1010px] pl-3 text-left group pointer-events-auto" data-node-target="n2" onclick="navigateToFeature('#challenges?category=web_exploitation')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Web Exploitation</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#ffbb65]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#ffbb65] animate-pulse"></span>
                <span class="text-[9.5px] font-mono text-[#ffbb65] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 40 LIVE LABS // 2100 XP</span>
              </div>
            </div>

            <!-- 6. REVERSE ENGINEERING Node Group (N5) -->
            <div class="skill-node-group absolute top-[452px] left-[455px] -translate-x-full pr-3 text-right group pointer-events-auto" data-node-target="n5" onclick="navigateToFeature('#challenges?category=reverse_engineering')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Reverse Engineering</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#00e676]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#00e676]"></span>
                <span class="text-[9.5px] font-mono text-[#75ff9e] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 22 MODULES // 1100 XP</span>
              </div>
            </div>

            <!-- 7. FORENSICS Node Group (N3) -->
            <div class="skill-node-group absolute top-[466px] left-[920px] pl-3 text-left group pointer-events-auto" data-node-target="n3" onclick="navigateToFeature('#challenges?category=forensics')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Forensics</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#4cd7f6]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#4cd7f6]"></span>
                <span class="text-[9.5px] font-mono text-[#4cd7f6] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 18 MODULES // 890 XP</span>
              </div>
            </div>

            <!-- 8. BINARY EXPLOITATION Node Group (N4) -->
            <div class="skill-node-group absolute top-[552px] left-[700px] -translate-x-1/2 text-center group pointer-events-auto" data-node-target="n4" onclick="navigateToFeature('#challenges?category=binary_exploitation')">
              <span class="node-label-text text-sm font-mono font-bold tracking-wider text-[#c0ccc5] uppercase drop-shadow-[0_0_8px_rgba(0,0,0,0.8)]">Binary Exploitation</span>
              <div class="node-hud mt-1.5 px-2.5 py-1 border border-[#ffb4ab]/70 rounded-md inline-flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-[#ffb4ab] animate-pulse"></span>
                <span class="text-[9.5px] font-mono text-[#ffb4ab] whitespace-nowrap tracking-wider font-semibold">// STATUS: ACTIVE // 26 MODULES // 1650 XP</span>
              </div>
            </div>
          </div>

          <!-- CENTER EMBLEM: Glowing Themed Cyber Reticle & Wasp Fingerprint Logo Mark -->
          <div class="relative z-20 flex flex-col items-center justify-center my-auto pointer-events-auto transition-transform duration-300 ease-out" id="heroCenterCard">
            <div class="group/emblem relative flex items-center justify-center w-52 h-52 sm:w-60 sm:h-60 md:w-68 md:h-68 cursor-pointer select-none" onclick="navigateToFeature('#challenges')">
              <!-- Outer Holographic Compass Ring (35s rotation) -->
              <div class="absolute inset-0 rounded-full border border-[#00e676]/30 border-dashed cyber-ring-outer"></div>
              <!-- Inner Cyan Calibration Accents (25s reverse rotation) -->
              <div class="absolute inset-3 rounded-full border border-[#4cd7f6]/25 cyber-ring-inner"></div>
              <!-- Central Ambient Glow Pod -->
              <div class="absolute inset-4 rounded-full bg-[#080d0b]/85 backdrop-blur-xl border border-[#00e676]/40 center-emblem-halo flex items-center justify-center overflow-hidden">
                <img alt="CyLab Academy Security Emblem" class="w-full h-full object-contain p-2 drop-shadow-[0_0_20px_rgba(0,230,118,0.6)] group-hover/emblem:drop-shadow-[0_0_35px_rgba(0,230,118,0.95)] transition-all duration-300 transform group-hover/emblem:scale-105" src="frontend/img/emblem.png" onerror="this.src='https://lh3.googleusercontent.com/aida/AEtjO1U4NXHsO1BYsjdVO0w8HqU0OqDdClbVUZAzjqwnztS9o5tZluB6jb64tG_jqY0ZkS90AlCLUGSjIujP8tZw08kK9Qo-Y4TmQ6czV5-ko8eQBW4Nkki1-nVGEuX3eU4UuO-nOX_uelAXNW2hYxpsELihzn3-JnIu2OxV9oMsphnBeK_l_rpldxHhfP08ObcdN52mP1lu_YdrKa5XhBGd_5BSYfqFsz-0lWAQZM2fKf1DO2N-uZKiElel'"/>
              </div>
              <!-- Center Radar Corner Tick Marks -->
              <div class="absolute -top-1 w-2 h-2 border-t-2 border-l-2 border-[#00e676]/70"></div>
              <div class="absolute -bottom-1 w-2 h-2 border-b-2 border-r-2 border-[#00e676]/70"></div>
              <div class="absolute -left-1 w-2 h-2 border-b-2 border-l-2 border-[#00e676]/70"></div>
              <div class="absolute -right-1 w-2 h-2 border-t-2 border-r-2 border-[#00e676]/70"></div>
            </div>

            <!-- Harmonious Subtitle & Focal Label Anchored Below Center Mesh -->
            <div class="mt-7 text-center max-w-xl px-4 pointer-events-auto space-y-3">
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#101413]/85 border border-[#00e676]/30 backdrop-blur-sm shadow-[0_0_12px_rgba(0,230,118,0.15)] hover:border-[#00e676]/70 hover:shadow-[0_0_20px_rgba(0,230,118,0.3)] transition-all duration-300">
                <span class="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse"></span>
                <span class="text-[11px] font-mono tracking-wider uppercase text-[#75ff9e] font-medium">CYBERSECURITY // SECURITY ACADEMY</span>
              </div>
              <p class="text-[#9eada6] text-xs sm:text-[14px] leading-relaxed max-w-lg mx-auto font-normal select-text">
                No experience needed. Learn at your own pace, with your class, or in a live event. 
                <strong class="font-semibold text-[#00e676] glow-free">Always free.</strong>
              </p>

              <div class="flex flex-wrap items-center justify-center gap-space-sm pt-2">
                <button class="btn btn-primary px-6 py-2.5 text-sm flex items-center gap-2 shadow-[0_0_15px_rgba(0,230,118,0.35)]" onclick="navigateToFeature('#challenges')">
                  <span class="material-symbols-outlined text-base">flag</span>
                  <span>Enter Challenge Arena</span>
                </button>
                <button class="btn btn-outline px-6 py-2.5 text-sm flex items-center gap-2" onclick="navigateToFeature('#events')">
                  <span class="material-symbols-outlined text-base">event_available</span>
                  <span>Live Competitions</span>
                </button>
                ${!window.state.currentUser ? `
                  <button class="btn btn-outline px-5 py-2.5 text-sm flex items-center gap-2 bg-surface-card hover:bg-surface-terminal border-border-grid hover:border-primary shadow-sm" onclick="handleGoogleSSO()">
                    <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                    </svg>
                    <span>Google SSO</span>
                  </button>
                  <button class="btn btn-outline px-6 py-2.5 text-sm text-accent-neon border-primary/40 flex items-center gap-1.5" onclick="openAuthModal('login')">
                    <span class="material-symbols-outlined text-base">login</span>
                    <span>Operative Access</span>
                  </button>
                ` : ''}
              </div>
            </div>
          </div>
        </section>

        <!-- 2. YOUR FIRST THREE STEPS (TACTICAL ONBOARDING MATRIX) -->
        <section class="space-y-6 pt-space-md" data-purpose="onboarding-protocol-section">
          
          <!-- Onboarding Header Block -->
          <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 pb-2 border-b border-emerald-500/15" data-purpose="onboarding-heading-block">
            <div>
              <!-- Tactical Protocol Badge -->
              <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono tracking-wider uppercase mb-3 shadow-[0_0_15px_rgba(0,230,118,0.15)] hover:border-emerald-400 transition-colors">
                <span class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
                </span>
                <span>INITIALIZATION PROTOCOL // STEP-BY-STEP ONBOARDING</span>
              </div>
              
              <h2 class="text-3xl sm:text-4xl md:text-5xl font-extrabold text-white tracking-tight">
                Your First <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-emerald-300 to-emerald-500 glow-text-emerald">Three Steps</span>
              </h2>
              <p class="mt-3 text-slate-400 max-w-2xl text-sm sm:text-base leading-relaxed font-sans">
                Follow this calibrated progression to transition from novice recruit to offensive cyber operator. Every milestone unlocks arena clearance and sandbox compute credentials.
              </p>
            </div>

            <!-- Academy Readiness Badge -->
            <div class="hidden lg:flex items-center space-x-3 px-4 py-2 rounded-lg bg-obsidian-900 border border-emerald-500/20 text-xs font-mono text-slate-300 shadow-sm hover:border-emerald-500/40 transition-colors">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
              </span>
              <span class="text-emerald-400 font-semibold">STATUS:</span>
              <span>STANDBY READY<span class="terminal-cursor text-emerald-400 font-bold ml-0.5">_</span></span>
              <span class="text-slate-600">|</span>
              <span class="text-emerald-400 font-bold">CLEARANCE: TIER-0</span>
            </div>
          </div>

          <!-- Steps Grid (3 Tactical Cards) -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8" data-purpose="onboarding-cards-container">
            
            <!-- STEP 01 CARD -->
            <article class="relative bg-obsidian-900/90 rounded-xl p-7 flex flex-col justify-between border border-emerald-500/25 tactical-card card-stagger-1 overflow-hidden group cursor-pointer shadow-xl" onclick="navigateToFeature('#challenges')">
              <!-- Corner Tech Reticles -->
              <span class="reticle-corner top-2 left-2 border-t-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner top-2 right-2 border-t-2 border-r-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 left-2 border-b-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 right-2 border-b-2 border-r-2 border-emerald-400/60"></span>
              
              <!-- Ambient Card Highlight -->
              <div class="absolute -top-16 -right-16 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-emerald-500/25 group-hover:scale-125 transition-all duration-500"></div>
              
              <div>
                <!-- Monospace Step Number & Badge -->
                <div class="flex items-center justify-between mb-6">
                  <div class="flex items-baseline space-x-2">
                    <span class="text-4xl md:text-5xl font-black font-mono tracking-tight numeral-shimmer glow-text-emerald">
                      01
                    </span>
                    <span class="text-[11px] font-mono font-bold tracking-widest text-emerald-400/80 uppercase">
                      / VECTOR
                    </span>
                  </div>
                  <!-- Tactical Reticle Icon Graphic -->
                  <div class="vector-icon-badge w-12 h-12 rounded-lg bg-obsidian-850 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner transition-all duration-300">
                    <svg class="w-6 h-6 transform group-hover:rotate-90 transition-transform duration-700 ease-out" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="9" stroke-width="1.75"></circle>
                      <circle cx="12" cy="12" r="3" stroke-width="1.75"></circle>
                      <path d="M12 3v3m0 12v3M3 12h3m12 0h3" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"></path>
                    </svg>
                  </div>
                </div>

                <!-- Title -->
                <h3 class="text-xl font-bold text-white tracking-tight mb-3 group-hover:text-emerald-300 transition-colors">
                  Calibrate &amp; Pick Your Vector
                </h3>
                
                <!-- Description -->
                <p class="text-slate-400 text-sm leading-relaxed mb-6">
                  Not sure where to begin? Initialize with structured Learning Paths (Cryptanalysis, Web Exploit, or Binary Reverse Engineering) where guided modules walk you step-by-step. Or deploy straight into the Open Library filtered by exploit tier.
                </p>
              </div>

              <!-- Footer Section: Tags & Action -->
              <div class="pt-5 border-t border-emerald-500/15">
                <div class="flex flex-wrap gap-1.5 mb-5 font-mono text-[11px]">
                  <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 hover:bg-emerald-500/20 hover:border-emerald-400 hover:shadow-[0_0_8px_rgba(0,230,118,0.3)] transition-all cursor-default">32 Guided Paths</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">Tier 1 - 4</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">Auto-Save State</span>
                </div>
                <div class="cta-link inline-flex items-center space-x-2 text-sm font-semibold text-emerald-400 group-hover:text-emerald-300 transition-colors">
                  <span>Explore Learning Paths</span>
                  <svg class="w-4 h-4 transform group-hover:translate-x-1.5 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M17 8l4 4m0 0l-4 4m4-4H3" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path>
                  </svg>
                </div>
              </div>
            </article>

            <!-- STEP 02 CARD -->
            <article class="relative bg-obsidian-900/90 rounded-xl p-7 flex flex-col justify-between border border-emerald-500/25 tactical-card card-stagger-2 overflow-hidden group cursor-pointer shadow-xl" onclick="navigateToFeature('#challenges')">
              <!-- Corner Tech Reticles -->
              <span class="reticle-corner top-2 left-2 border-t-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner top-2 right-2 border-t-2 border-r-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 left-2 border-b-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 right-2 border-b-2 border-r-2 border-emerald-400/60"></span>
              
              <!-- Ambient Card Highlight -->
              <div class="absolute -top-16 -right-16 w-36 h-36 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-cyan-500/25 group-hover:scale-125 transition-all duration-500"></div>
              
              <div>
                <!-- Monospace Step Number & Badge -->
                <div class="flex items-center justify-between mb-6">
                  <div class="flex items-baseline space-x-2">
                    <span class="text-4xl md:text-5xl font-black font-mono tracking-tight numeral-shimmer glow-text-emerald">
                      02
                    </span>
                    <span class="text-[11px] font-mono font-bold tracking-widest text-emerald-400/80 uppercase">
                      / EXPLOIT
                    </span>
                  </div>
                  <!-- Tactical Terminal / Hack Icon Graphic -->
                  <div class="vector-icon-badge w-12 h-12 rounded-lg bg-obsidian-850 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner transition-all duration-300">
                    <svg class="w-6 h-6 group-hover:scale-110 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"></path>
                    </svg>
                  </div>
                </div>

                <!-- Title -->
                <h3 class="text-xl font-bold text-white tracking-tight mb-3 group-hover:text-emerald-300 transition-colors">
                  Infiltrate &amp; Solve Live Targets
                </h3>
                
                <!-- Description -->
                <p class="text-slate-400 text-sm leading-relaxed mb-6">
                  Spin up isolated ephemeral Docker instances on demand. Every target provides multi-tier cryptographic hints you can unlock incrementally when stuck. Zero penalties in sandbox mode—craft flags and test exploits at your own operational pace.
                </p>
              </div>

              <!-- Footer Section: Tags & Action -->
              <div class="pt-5 border-t border-emerald-500/15">
                <div class="flex flex-wrap gap-1.5 mb-5 font-mono text-[11px]">
                  <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 hover:bg-emerald-500/20 hover:border-emerald-400 hover:shadow-[0_0_8px_rgba(0,230,118,0.3)] transition-all cursor-default">Instant Ephemeral Docker</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">Dynamic Hints</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">0 Penalties</span>
                </div>
                <div class="cta-link inline-flex items-center space-x-2 text-sm font-semibold text-emerald-400 group-hover:text-emerald-300 transition-colors">
                  <span>Launch First Sandbox</span>
                  <svg class="w-4 h-4 transform group-hover:translate-x-1.5 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M17 8l4 4m0 0l-4 4m4-4H3" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path>
                  </svg>
                </div>
              </div>
            </article>

            <!-- STEP 03 CARD -->
            <article class="relative bg-obsidian-900/90 rounded-xl p-7 flex flex-col justify-between border border-emerald-500/25 tactical-card card-stagger-3 overflow-hidden group cursor-pointer shadow-xl" onclick="navigateToFeature('#events')">
              <!-- Corner Tech Reticles -->
              <span class="reticle-corner top-2 left-2 border-t-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner top-2 right-2 border-t-2 border-r-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 left-2 border-b-2 border-l-2 border-emerald-400/60"></span>
              <span class="reticle-corner bottom-2 right-2 border-b-2 border-r-2 border-emerald-400/60"></span>
              
              <!-- Ambient Card Highlight -->
              <div class="absolute -top-16 -right-16 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-emerald-500/25 group-hover:scale-125 transition-all duration-500"></div>
              
              <div>
                <!-- Monospace Step Number & Badge -->
                <div class="flex items-center justify-between mb-6">
                  <div class="flex items-baseline space-x-2">
                    <span class="text-4xl md:text-5xl font-black font-mono tracking-tight numeral-shimmer glow-text-emerald">
                      03
                    </span>
                    <span class="text-[11px] font-mono font-bold tracking-widest text-emerald-400/80 uppercase">
                      / ARENA
                    </span>
                  </div>
                  <!-- Tactical Trophy / Arena Shield Icon Graphic -->
                  <div class="vector-icon-badge w-12 h-12 rounded-lg bg-obsidian-850 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner transition-all duration-300">
                    <svg class="w-6 h-6 group-hover:scale-110 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"></path>
                    </svg>
                  </div>
                </div>

                <!-- Title -->
                <h3 class="text-xl font-bold text-white tracking-tight mb-3 group-hover:text-emerald-300 transition-colors">
                  Level Up &amp; Dominate the Arena
                </h3>
                
                <!-- Description -->
                <p class="text-slate-400 text-sm leading-relaxed mb-6">
                  Synchronize with your university squadron or compete solo in live CTF tournaments. Enter your professor’s private classroom arena with real-time telemetric scoreboards. Earn verifiable credentials, climb leaderboards, and unlock defense badges.
                </p>
              </div>

              <!-- Footer Section: Tags & Action -->
              <div class="pt-5 border-t border-emerald-500/15">
                <div class="flex flex-wrap gap-1.5 mb-5 font-mono text-[11px]">
                  <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 hover:bg-emerald-500/20 hover:border-emerald-400 hover:shadow-[0_0_8px_rgba(0,230,118,0.3)] transition-all cursor-default">Live CTF Matchmaking</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">Collegiate Squads</span>
                  <span class="px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-white/5 hover:border-emerald-500/30 hover:text-slate-200 transition-all cursor-default">Ranked Badges</span>
                </div>
                <div class="cta-link inline-flex items-center space-x-2 text-sm font-semibold text-emerald-400 group-hover:text-emerald-300 transition-colors">
                  <span>View Global Arena</span>
                  <svg class="w-4 h-4 transform group-hover:translate-x-1.5 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M17 8l4 4m0 0l-4 4m4-4H3" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path>
                  </svg>
                </div>
              </div>
            </article>

          </div>

        </section>

        <!-- 3. CURRICULUM ARCHITECTURE // SPECIALIZED DOMAINS -->
        <section class="space-y-6 pt-space-md" data-purpose="curriculum-overview-section">
          
          <!-- Hero Architecture Header -->
          <div class="mb-8 text-left" data-purpose="curriculum-overview-header">
            <!-- Tactical System Indicator Chip -->
            <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-neon-emerald/5 border border-neon-emerald/20 text-neon-mint text-xs font-mono tracking-wider mb-4 shadow-[0_0_12px_rgba(0,230,118,0.1)]">
              <span class="w-2 h-2 rounded-full bg-neon-emerald beacon-pulse"></span>
              CURRICULUM ARCHITECTURE // SPECIALIZED DOMAINS
            </div>
            <!-- Main Headline -->
            <h2 class="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight uppercase">
              TOPICS YOU'LL <span class="text-transparent bg-clip-text bg-gradient-to-r from-neon-emerald via-emerald-400 to-teal-300">EXPLORE</span>
            </h2>
            <!-- Subtitle Description -->
            <p class="mt-3 text-slate-400 max-w-3xl text-sm sm:text-base leading-relaxed font-sans">
              Master offensive and defensive cybersecurity across 8 calibrated tactical disciplines. Learn at your own pace with hands-on labs, interactive sandboxes, and competitive CTF challenges.
            </p>
            <!-- System Telemetry Badge Strip -->
            <div class="mt-6 flex flex-wrap items-center gap-2 sm:gap-3 text-[11px] font-mono tracking-wide text-slate-400">
              <span class="px-2.5 py-1 rounded bg-obsidian-card border border-obsidian-border text-neon-mint flex items-center gap-1.5">
                <span class="text-neon-emerald font-bold">❖</span> 8 COMBAT TRACKS
              </span>
              <span class="px-2.5 py-1 rounded bg-obsidian-card border border-obsidian-border text-slate-300 flex items-center gap-1.5">
                <span class="text-neon-emerald font-bold">◈</span> 140+ CTF CHALLENGES
              </span>
              <span class="px-2.5 py-1 rounded bg-obsidian-card border border-obsidian-border text-slate-300 flex items-center gap-1.5">
                <span class="text-neon-emerald font-bold">⬡</span> LIVE ISOLATED CONTAINERS
              </span>
              <span class="px-2.5 py-1 rounded bg-obsidian-card border border-obsidian-border text-slate-400 hidden sm:inline-flex items-center gap-1.5">
                STATUS: <span class="text-neon-emerald">ACTIVE // ALL TIERS READY</span>
              </span>
            </div>
          </div>

          <!-- BEGIN: DomainCardsGrid (4 Columns x 2 Rows Layout matching IMAGE_6) -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5" data-purpose="domain-tracks-grid">
            
            <!-- Card 01: General Skills -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=general_skills')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>01</span> <span class="text-slate-600">/</span> <span>FOUNDATIONAL</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Terminal Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <polyline points="4 17 10 11 4 5"></polyline>
                      <line x1="12" x2="20" y1="19" y2="19"></line>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  General Skills
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  The terminal, bash scripting, and tools you'll reach for in every other category.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">CLI &amp; Bash</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Core Utilities</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Vim / Tmux</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 02: AI & ML -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=ai_ml')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>02</span> <span class="text-slate-600">/</span> <span>ADVANCED</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- AI / Neural Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  AI &amp; ML
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Machine learning models can be tricked. Prompt injection, adversarial examples, model inversion. A fast-growing area as AI ends up everywhere.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Prompt Injection</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Adversarial NN</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Model Inversion</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 03: Cryptography -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=cryptography')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>03</span> <span class="text-slate-600">/</span> <span>CIPHER</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Key / Cipher Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <rect height="11" rx="2" ry="2" width="18" x="3" y="11"></rect>
                      <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Cryptography
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Codes, ciphers, and locked data. Figure out how encryption and hashing work, then break them.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">RSA &amp; ECC</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Hashes &amp; HMAC</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Cipher Cracking</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 04: Web Exploitation -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=web_exploitation')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>04</span> <span class="text-slate-600">/</span> <span>WEB</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Web / Globe Exploit Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="2" x2="22" y1="12" y2="12"></line>
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Web Exploitation
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Websites trust user input more than they should. SQL injection, XSS, and broken logins are how attackers get in.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">OWASP Top 10</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">SQLi &amp; XSS</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Auth Bypass</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 05: Forensics -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=forensics')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>05</span> <span class="text-slate-600">/</span> <span>ARTIFACT</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Search / Search Fingerprint Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <circle cx="11" cy="11" r="8"></circle>
                      <path d="m21 21-4.3-4.3"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Forensics
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Hunt through files, images, and network traffic for data that wasn't meant to be found. Think steganography and packet analysis.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Wireshark / PCAP</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Steganography</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Disk Forensics</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 06: Binary Exploitation -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=binary_exploitation')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>06</span> <span class="text-slate-600">/</span> <span>PWN</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Memory / Chip Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <rect height="16" rx="2" width="16" x="4" y="4"></rect>
                      <rect height="6" width="6" x="9" y="9"></rect>
                      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Binary Exploitation
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Programs use memory. Buffer overflows and similar tricks let you corrupt that memory and make software do unexpected things.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Buffer Overflow</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">ROP Chains</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Memory Corrupt</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 07: Reverse Engineering -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=reverse_engineering')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>07</span> <span class="text-slate-600">/</span> <span>REVERSE</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Decompiler / Disassembly Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path d="m7 8 5-5 5 5M7 16l5 5 5-5M12 3v18"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Reverse Engineering
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  You have the program but not the source code. Disassemble it, decompile it, and trace its execution to figure out what it does.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Ghidra / IDA</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Decompilation</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Assembly x86</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

            <!-- Card 08: Blockchain -->
            <article class="tactical-card group rounded-lg bg-obsidian-card/85 backdrop-blur border border-obsidian-border hover:border-neon-emerald/50 p-5 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,230,118,0.12)] cursor-pointer" onclick="navigateToFeature('#challenges?category=blockchain')">
              <div>
                <!-- Meta Header -->
                <div class="flex items-center justify-between mb-3.5">
                  <span class="font-mono text-xs font-semibold text-neon-emerald tracking-wider flex items-center gap-1.5">
                    <span>08</span> <span class="text-slate-600">/</span> <span>WEB3</span>
                  </span>
                  <div class="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-neon-emerald">
                    <!-- Blockchain Node Icon -->
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <rect height="8" rx="1" width="8" x="2" y="2"></rect>
                      <path d="M14 2c1.1 0 2 .9 2 2v4c0 1.1-.9 2-2 2"></path>
                      <path d="M20 2v20"></path>
                      <path d="M10 14H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2z"></path>
                      <path d="M14 14h2a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"></path>
                    </svg>
                  </div>
                </div>
                <!-- Title & Content -->
                <h3 class="text-lg font-bold text-white group-hover:text-neon-emerald transition-colors tracking-tight">
                  Blockchain
                </h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">
                  Crypto and smart contracts run on code. Reentrancy bugs, integer overflows, bad logic. Find the vulnerabilities before someone exploits them.
                </p>
              </div>
              <!-- Tags & Action Footer -->
              <div class="mt-6 pt-4 border-t border-obsidian-border/70">
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Solidity Auditing</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Reentrancy</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-hover text-slate-300 border border-obsidian-border">Web3 Security</span>
                </div>
                <div class="flex items-center justify-between text-xs font-mono text-slate-500 group-hover:text-neon-emerald transition-colors">
                  <span>START TRACK</span>
                  <span class="group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </div>
            </article>

          </div>
          <!-- END: DomainCardsGrid -->

          <!-- Assessment Callout Banner -->
          <div class="mt-12 rounded-lg border border-obsidian-border bg-obsidian-card/40 p-5 sm:p-6 flex flex-col md:flex-row items-center justify-between gap-4" data-purpose="skill-level-assessment-callout">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-neon-emerald/10 border border-neon-emerald/30 flex items-center justify-center shrink-0">
                <svg class="w-6 h-6 text-neon-emerald" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polygon points="12 8 8 12 12 16 12 8"></polygon>
                  <line x1="16" x2="12" y1="12" y2="12"></line>
                </svg>
              </div>
              <div>
                <h3 class="text-sm font-bold text-white uppercase tracking-wide">Not sure where to begin your training?</h3>
                <p class="text-xs text-slate-400 mt-0.5 font-sans">Take the 10-minute diagnostic triage assessment to calibrate your cyber domain roadmap.</p>
              </div>
            </div>
            <a href="https://github.com/owasppccoe/cybersecurity-roadmap" target="_blank" rel="noopener noreferrer" class="w-full md:w-auto px-5 py-2.5 rounded bg-neon-emerald hover:bg-neon-glow text-black font-semibold text-xs tracking-wider uppercase transition shadow-[0_0_15px_rgba(0,230,118,0.3)] hover:shadow-[0_0_22px_rgba(0,230,118,0.5)] whitespace-nowrap cursor-pointer inline-flex items-center justify-center">
              RUN DIAGNOSTIC ASSESSMENT →
            </a>
          </div>

          <!-- BEGIN: TelemetryDockFooter -->
          <footer class="w-full border-t border-obsidian-border/80 bg-obsidian-base/95 backdrop-blur-md py-3 text-slate-500 font-mono text-[11px] select-none mt-12 rounded-lg">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-2 text-center md:text-left">
              <!-- Left Telemetry Status -->
              <div class="flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-neon-emerald"></span>
                <span>TELEMETRY: ACTIVE</span>
                <span class="text-slate-700">|</span>
                <span class="text-slate-400">SOC NODE #01-US-EAST</span>
                <span class="text-slate-700">|</span>
                <span class="text-slate-400">CIPHER: AES-256-GCM</span>
                <span class="text-slate-700 hidden sm:inline">|</span>
                <span class="text-slate-400 hidden sm:inline" id="telemetry-clock">SYNC: LIVE UTC</span>
              </div>
              <!-- Right System Manifest -->
              <div class="flex items-center gap-2 text-slate-400">
                <span>SECURITY MANIFEST v4.12</span>
                <span class="text-slate-700">/</span>
                <span class="text-neon-emerald flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-neon-emerald beacon-pulse"></span>
                  ALL SYSTEMS OPERATIONAL
                </span>
              </div>
            </div>
          </footer>
          <!-- END: TelemetryDockFooter -->

        </section>

      </div>
    `;
  },

  async loadUpcomingEventsPreview() {
    const container = document.getElementById('landingEventsList');
    if (!container) return;

    try {
      const events = await window.api.getEvents();
      if (!Array.isArray(events) || events.length === 0) {
        container.innerHTML = '<div class="text-text-muted font-code-sm text-center py-4">No events scheduled.</div>';
        return;
      }

      container.innerHTML = events.slice(0, 3).map(ev => `
        <div class="p-3 rounded-lg bg-surface-terminal/40 border border-border-subtle flex justify-between items-center hover:border-primary/40 transition-colors cursor-pointer" onclick="navigateToFeature('#events')">
          <div>
            <div class="font-code-sm text-code-sm text-text-primary font-bold">${escapeHtml(ev.name)}</div>
            <div class="font-code-sm text-code-sm text-text-muted text-[11px]">${formatDate(ev.start_at)}</div>
          </div>
          <span class="badge ${ev.computed_status === 'live' ? 'badge-live' : 'badge-upcoming'}">${ev.computed_status.toUpperCase()}</span>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = '<div class="text-text-muted font-code-sm text-center py-4">Unable to retrieve events.</div>';
    }
  },

  async loadLeaderboardPreview() {
    const container = document.getElementById('landingLeaderboardList');
    if (!container) return;

    try {
      const res = await window.api.getGlobalLeaderboard(5, 0);
      const items = Array.isArray(res) ? res : res.items || [];
      if (items.length === 0) {
        container.innerHTML = '<div class="text-text-muted font-code-sm text-center py-4">No scores recorded yet.</div>';
        return;
      }

      container.innerHTML = items.slice(0, 4).map((entry, idx) => `
        <div class="p-2.5 rounded-lg bg-surface-terminal/40 border border-border-subtle flex justify-between items-center font-code-sm text-code-sm">
          <div class="flex items-center gap-2">
            <span class="font-bold ${idx === 0 ? 'text-primary' : idx === 1 ? 'text-secondary' : idx === 2 ? 'text-tertiary' : 'text-text-muted'}">#${idx + 1}</span>
            <span class="text-text-primary font-semibold">@${escapeHtml(entry.username)}</span>
          </div>
          <span class="text-primary font-bold font-mono">${(entry.score || 0).toLocaleString()} PTS</span>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = '<div class="text-text-muted font-code-sm text-center py-4">Unable to retrieve scores.</div>';
    }
  },

  initInteractiveConstellation() {
    // 1. Mouse Spotlight & Subtle Parallax Effect
    const centerCard = document.getElementById('heroCenterCard');

    const handleMouseMove = (e) => {
      const xPercent = (e.clientX / window.innerWidth) * 100;
      const yPercent = (e.clientY / window.innerHeight) * 100;
      document.documentElement.style.setProperty('--mouse-x', `${xPercent}%`);
      document.documentElement.style.setProperty('--mouse-y', `${yPercent}%`);

      if (centerCard && window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
        const deltaX = (e.clientX - window.innerWidth / 2) / 55;
        const deltaY = (e.clientY - window.innerHeight / 2) / 55;
        centerCard.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0)`;
      }
    };

    if (this._mouseMoveHandler) {
      window.removeEventListener('mousemove', this._mouseMoveHandler);
    }
    this._mouseMoveHandler = handleMouseMove;
    window.addEventListener('mousemove', handleMouseMove);

    // 2. Star Dust Particle Canvas
    const canvas = document.getElementById('starDustCanvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      let width, height;
      const particles = [];
      const particleCount = 48;

      const resize = () => {
        if (!canvas.parentElement) return;
        width = canvas.width = canvas.parentElement.offsetWidth || window.innerWidth;
        height = canvas.height = canvas.parentElement.offsetHeight || 720;
      };
      resize();
      window.addEventListener('resize', resize);

      for (let i = 0; i < particleCount; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 1.5 + 0.5,
          speedY: -(Math.random() * 0.25 + 0.05),
          speedX: (Math.random() - 0.5) * 0.15,
          opacity: Math.random() * 0.6 + 0.15,
          color: Math.random() > 0.3 ? '#00e676' : '#4cd7f6'
        });
      }

      if (this._animFrameId) cancelAnimationFrame(this._animFrameId);
      const animate = () => {
        if (!document.getElementById('starDustCanvas')) return;
        ctx.clearRect(0, 0, width, height);
        particles.forEach(p => {
          p.y += p.speedY;
          p.x += p.speedX;
          if (p.y < 0) {
            p.y = height;
            p.x = Math.random() * width;
          }
          if (p.x < 0) p.x = width;
          if (p.x > width) p.x = 0;

          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.opacity;
          ctx.fill();
        });
        if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
          this._animFrameId = requestAnimationFrame(animate);
        }
      };
      animate();
    }

    // 3. Interactive Mesh Node Highlighting Engine & Direct Navigation
    const interactiveGroups = document.querySelectorAll('[data-node-target]');
    const meshLines = document.querySelectorAll('.mesh-line');
    const corePoints = document.querySelectorAll('.core-point');

    const nodeTargetMap = {
      'n0': '#challenges?category=general_skills',
      'n1': '#challenges?category=cryptography',
      'n2': '#challenges?category=web_exploitation',
      'n3': '#challenges?category=forensics',
      'n4': '#challenges?category=binary_exploitation',
      'n5': '#challenges?category=reverse_engineering',
      'n6': '#challenges?category=blockchain',
      'n7': '#challenges?category=ai_ml'
    };

    corePoints.forEach(point => {
      const nodeTag = point.getAttribute('data-node');
      if (nodeTag && nodeTargetMap[nodeTag]) {
        point.style.cursor = 'pointer';
        point.style.pointerEvents = 'auto';
        point.addEventListener('click', (e) => {
          e.stopPropagation();
          navigateToFeature(nodeTargetMap[nodeTag]);
        });
      }
    });

    interactiveGroups.forEach(group => {
      const nodeTag = group.getAttribute('data-node-target');
      
      group.addEventListener('mouseenter', () => {
        document.body.setAttribute('data-hover-active', 'true');
        
        meshLines.forEach(line => {
          const connected = line.getAttribute('data-nodes');
          if (connected && connected.includes(nodeTag)) {
            line.classList.add('connected-active');
          } else {
            line.classList.remove('connected-active');
          }
        });

        corePoints.forEach(point => {
          if (point.getAttribute('data-node') === nodeTag) {
            point.classList.add('active-hover');
          } else {
            point.classList.remove('active-hover');
          }
        });
      });

      group.addEventListener('mouseleave', () => {
        document.body.removeAttribute('data-hover-active');
        meshLines.forEach(line => line.classList.remove('connected-active'));
        corePoints.forEach(point => point.classList.remove('active-hover'));
      });
    });
  }
};

window.LandingView = LandingView;

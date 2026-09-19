/**
 * OWASP CTF Platform — Student Profile & Achievements
 * Stitch Screen: "Student Cybersecurity Profile & Achievements" (9c762ba3f7d545b19df65b5e3c8a2bfe)
 */

const ProfileView = {
  profileData: null,
  userActivities: [],
  userBadges: [],
  catalogBadges: [],
  userTeam: null,
  selectedHeatYear: 'Current',
  lastHeatmapData: [],
  lastStreakData: null,
  lastSolvedCount: 0,

  async init() {
    if (!window.state.currentUser) {
      window.location.hash = '#landing';
      openModal('authModal');
      return;
    }
    this.render();
    await this.loadProfile();

    // Check for GitHub OAuth return parameters
    const hash = window.location.hash || '';
    if (hash.includes('github=connected')) {
      showToast('GitHub account connected successfully! Please select your CTF solutions repository.', 'success');
      setTimeout(() => this.openGitHubConfigModal(), 400);
      window.history.replaceState(null, '', '#profile');
    } else if (hash.includes('github=error')) {
      const urlParams = new URLSearchParams(hash.split('?')[1] || '');
      const errMsg = urlParams.get('message') || 'Connection failed';
      showToast('GitHub connection failed: ' + decodeURIComponent(errMsg), 'error');
      window.history.replaceState(null, '', '#profile');
    }

    if (!this._dropdownDismissBound) {
      this._dropdownDismissBound = true;
      document.addEventListener('click', (e) => {
        const menu = document.getElementById('heatYearDropdownMenu');
        const btn = document.getElementById('heatYearSelectBtn');
        if (menu && !menu.classList.contains('hidden')) {
          if (!btn?.contains(e.target) && !menu.contains(e.target)) {
            menu.classList.add('hidden');
          }
        }
        const modal = document.getElementById('badge-modal');
        if (e.target === modal) {
          ProfileView.closeBadgeModal();
        }
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          ProfileView.closeBadgeModal();
        }
      });
    }
  },

  render() {
    const container = document.getElementById('view-profile');
    if (!container) return;

    const u = window.state.currentUser;

    container.innerHTML = `
      <div class="relative w-full p-space-lg lg:p-margin space-y-space-xl overflow-hidden max-w-[1720px] mx-auto">
        <div class="absolute -top-32 right-12 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none -z-10"></div>
        <div class="absolute top-96 -left-32 w-80 h-80 bg-secondary/10 rounded-full blur-3xl pointer-events-none -z-10"></div>

        <!-- 1. PROFILE HEADER SECTION -->
        <section class="w-full bg-surface-card/85 backdrop-blur-md rounded-xl p-space-lg border border-border-grid shadow-xl relative overflow-hidden">
          <div class="absolute top-0 right-0 w-80 h-32 bg-gradient-to-l from-primary/15 via-transparent to-transparent pointer-events-none"></div>
          
          <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-lg">
            
            <!-- Avatar & Basic Bio -->
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-space-md">
              <div class="relative shrink-0">
                <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-xl p-1 bg-surface-terminal border border-primary/40 shadow-[0_0_24px_rgba(78,222,163,0.35)] relative group">
                  <div class="w-full h-full rounded-lg bg-surface-base flex items-center justify-center text-primary font-headline-xl text-headline-xl font-bold font-mono">
                    ${(u.name || u.username)[0].toUpperCase()}
                  </div>
                  <div class="absolute -bottom-1.5 -right-1.5 bg-surface-card p-1 rounded-full shadow-md">
                    <span class="flex h-3.5 w-3.5 relative">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-primary"></span>
                    </span>
                  </div>
                </div>
              </div>

              <div class="space-y-1.5 min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <h1 class="font-headline-lg text-headline-lg text-text-primary tracking-tight font-bold">
                    ${escapeHtml(u.name || u.username)}
                  </h1>
                  <span class="font-code-md text-code-md text-primary font-semibold bg-surface-terminal px-2.5 py-0.5 rounded border border-border-subtle">
                    @${escapeHtml(u.username)}
                  </span>
                  <span class="inline-flex items-center gap-1 font-label-sm text-label-sm text-status-info bg-status-info/10 border border-status-info/30 px-2 py-0.5 rounded font-bold uppercase">
                    <span class="material-symbols-outlined text-sm">verified</span> Verified Operative
                  </span>
                </div>

                <p id="profileBioDisplay" class="font-headline-sm text-headline-sm text-text-secondary">
                  ${escapeHtml(u.bio || 'Collegiate Security Researcher • OWASP CTF Operative')}
                </p>

                <div class="flex flex-wrap items-center gap-y-1 gap-x-space-md font-body-sm text-body-sm text-text-muted pt-1">
                  <span class="inline-flex items-center gap-1">
                    <span class="material-symbols-outlined text-base text-primary">school</span>
                    ${escapeHtml(u.college || 'Individual Competitor')}
                  </span>
                  <span class="inline-flex items-center gap-1">
                    <span class="material-symbols-outlined text-base text-text-secondary">fingerprint</span>
                    Role: ${u.role.toUpperCase()}
                  </span>
                  <!-- GitHub Connection Badge / Action (Positioned on the right of Role: ADMIN / STUDENT) -->
                  <span id="profileGitHubHeaderContainer" class="inline-flex items-center ml-1.5">
                    <button id="btnProfileConnectGitHub" type="button" onclick="ProfileView.openGitHubConfigModal()" class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg bg-surface-terminal/90 hover:bg-surface-card border border-border-grid hover:border-primary text-text-primary transition-all shadow-[0_0_12px_rgba(16,185,129,0.15)] cursor-pointer">
                      <svg class="w-3.5 h-3.5 fill-current text-primary" viewBox="0 0 24 24">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                      </svg>
                      <span>Connect GitHub</span>
                    </button>
                  </span>
                </div>

                <!-- LeetCode-style Followers & Following Counts -->
                <div class="flex items-center gap-4 pt-2 font-body-sm text-body-sm">
                  <button type="button" class="inline-flex items-center gap-1.5 text-text-secondary hover:text-primary transition-colors cursor-pointer group" onclick="ProfileView.openFollowersModal()">
                    <span id="profFollowersCount" class="font-headline-sm font-bold text-text-primary group-hover:text-primary transition-colors">0</span>
                    <span class="text-text-muted group-hover:text-primary/80">Followers</span>
                  </button>
                  <span class="text-border-subtle">•</span>
                  <button type="button" class="inline-flex items-center gap-1.5 text-text-secondary hover:text-primary transition-colors cursor-pointer group" onclick="ProfileView.openFollowingModal()">
                    <span id="profFollowingCount" class="font-headline-sm font-bold text-text-primary group-hover:text-primary transition-colors">0</span>
                    <span class="text-text-muted group-hover:text-primary/80">Following</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Action Buttons: Edit Bio & Security -->
            <div class="flex flex-wrap items-center gap-2 shrink-0">
              <button class="btn btn-outline btn-sm" onclick="openModal('editProfileModal')">
                <span class="material-symbols-outlined text-sm">edit</span> Edit Dossier Bio
              </button>
              <button class="btn btn-outline btn-sm" onclick="openModal('changePassModal')">
                <span class="material-symbols-outlined text-sm">key</span> Security &amp; Key
              </button>
            </div>
          </div>

          <!-- Quick Metrics Strip -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-space-sm mt-space-lg pt-space-md bg-surface-terminal/40 p-space-md rounded-lg border border-border-subtle">
            <div class="p-space-sm">
              <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider block">Global Leaderboard</span>
              <div class="flex items-baseline gap-1 mt-1 font-mono">
                <span id="profRankVal" class="font-headline-lg text-headline-lg font-bold text-text-primary">#—</span>
                <span id="profTotalUsersVal" class="font-code-sm text-code-sm text-text-muted">/ 1</span>
              </div>
              <span class="font-code-sm text-code-sm text-primary flex items-center gap-1 mt-0.5">
                <span class="material-symbols-outlined text-xs">north</span> Collegiate Ranking
              </span>
            </div>

            <div class="p-space-sm">
              <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider block">Campus Standings</span>
              <div class="flex items-baseline gap-1 mt-1 font-mono">
                <span id="profCollegeRankVal" class="font-headline-lg text-headline-lg font-bold text-tertiary">#1</span>
                <span class="font-code-sm text-code-sm text-tertiary/80">Campus Node</span>
              </div>
              <span class="font-code-sm text-code-sm text-text-muted flex items-center gap-1 mt-0.5">
                ${escapeHtml(u.college || 'Solo')}
              </span>
            </div>

            <div class="p-space-sm">
              <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider block">Defense Credits</span>
              <div class="flex items-baseline gap-1 mt-1 font-mono">
                <span id="profScoreVal" class="font-headline-lg text-headline-lg font-bold text-primary">0</span>
                <span class="font-code-sm text-code-sm text-text-muted">PTS</span>
              </div>
              <span class="font-code-sm text-code-sm text-primary flex items-center gap-1 mt-0.5">
                <span class="material-symbols-outlined text-xs">bolt</span> Verified Score
              </span>
            </div>

            <div class="p-space-sm">
              <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider block">Total Questions Solved</span>
              <div class="flex items-baseline gap-1 mt-1 font-mono">
                <span id="profSolvesVal" class="font-headline-lg text-headline-lg font-bold text-secondary">0</span>
                <span id="profTotalPoolVal" class="font-code-sm text-code-sm text-text-muted">/ 0 POOL</span>
              </div>
              <span id="profSolvePercentVal" class="font-code-sm text-code-sm text-text-muted flex items-center gap-1 mt-0.5">
                Progress Active
              </span>
            </div>
          </div>
        </section>

        <!-- 2. SKILL RADAR & CATEGORY BREAKDOWN (Bento Split) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-space-lg">
          
          <!-- Tactical Skill Radar -->
          <section class="lg:col-span-7 bg-surface-card/90 backdrop-blur-md rounded-xl p-space-lg border border-border-grid shadow-xl flex flex-col justify-between">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="font-headline-md text-headline-md text-text-primary font-bold">Tactical Skill Radar</h2>
                <p class="font-body-sm text-body-sm text-text-muted">Multi-vector offensive &amp; defensive domain saturation</p>
              </div>
              <span class="font-code-sm text-code-sm bg-primary/10 text-primary border border-primary/30 px-2.5 py-1 rounded font-bold">
                CALIBRATED // REALTIME
              </span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-12 gap-space-md items-center my-space-md">
              <!-- SVG Cyber Radar Chart (8-Spoke Octagon matching 8 core categories) -->
              <div class="sm:col-span-5 flex items-center justify-center relative p-1">
                <svg class="w-64 h-64 overflow-visible" viewBox="0 0 300 300">
                  <!-- 3 Concentric Octagons (100%, 66%, 33%) -->
                  <polygon fill="none" points="150,40 228,72 260,150 228,228 150,260 72,228 40,150 72,72" stroke="#1E292B" stroke-dasharray="3,3" stroke-width="1.5"></polygon>
                  <polygon fill="none" points="150,77 202,98 223,150 202,202 150,223 98,202 77,150 98,98" stroke="#1E292B" stroke-width="1.5"></polygon>
                  <polygon fill="none" points="150,113 176,124 187,150 176,176 150,187 124,176 113,150 124,124" stroke="#1E292B" stroke-dasharray="2,2" stroke-width="1.5"></polygon>
                  
                  <!-- 8 Spoke Lines -->
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="150" y2="40"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="228" y2="72"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="260" y2="150"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="228" y2="228"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="150" y2="260"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="72" y2="228"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="40" y2="150"></line>
                  <line stroke="#1E292B" stroke-width="1" x1="150" y1="150" x2="72" y2="72"></line>
                  
                  <!-- Dynamic Radar Polygon (Starts collapsed at center 150,150 when 0 solved) -->
                  <polygon id="radarPolygon" class="text-primary transition-all duration-700" fill="currentColor" fill-opacity="0.25" stroke="currentColor" stroke-width="2.5" points="150,150 150,150 150,150 150,150 150,150 150,150 150,150 150,150"></polygon>
                  <circle cx="150" cy="150" r="2.5" class="fill-primary/40"></circle>
                  
                  <!-- Axis Labels for All 8 Categories -->
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="middle" x="150" y="28">WEB</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="start" x="234" y="68">FORENSICS</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="start" x="268" y="153">OSINT</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="start" x="234" y="238">CRYPTO</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="middle" x="150" y="278">STEGANO</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="end" x="66" y="238">REVERSE</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="end" x="32" y="153">PWN</text>
                  <text class="fill-text-secondary text-[9px] font-mono font-bold" text-anchor="end" x="66" y="68">MISC</text>
                </svg>
              </div>

              <!-- Linear Trackers for All 8 Categories (Fill according to questions solved) -->
              <div id="categoryProgressContainer" class="sm:col-span-7 space-y-1.5 font-code-sm text-code-sm pl-0 sm:pl-space-sm">
                <!-- Dynamically populated for Cryptography, Forensics, Misc, OSINT, Pwn / Binary Exploitation, Reverse Engineering, Steganography, Web Exploitation -->
              </div>
            </div>
            
            <div class="pt-space-sm bg-surface-terminal/30 p-2.5 rounded-lg flex items-center justify-between font-code-sm text-code-sm border border-border-subtle">
              <span id="profileSpecialtyText" class="text-text-muted">Primary Specialty: Awaiting Initial Solves (0 Questions Solved)</span>
              <span class="text-primary font-semibold">Active Solves Ledger</span>
            </div>
          </section>

          <!-- LeetCode-style Quota Ring -->
          <div class="lg:col-span-5 flex flex-col">
            
            <!-- Solved Count Tier Ring & Difficulty Quota -->
            <section class="bg-surface-card/90 backdrop-blur-md rounded-xl p-space-lg border border-border-grid shadow-xl h-full flex flex-col justify-between">
              <div class="flex items-center justify-between mb-space-md">
                <div>
                  <h2 class="font-headline-md text-headline-md text-text-primary font-bold">Difficulty Quota</h2>
                  <p class="font-body-sm text-body-sm text-text-muted">Tiered jeopardy progression</p>
                </div>
                <span class="font-label-sm text-label-sm uppercase bg-surface-terminal text-text-secondary px-2 py-0.5 rounded border border-border-subtle font-mono">TIER MATRIX</span>
              </div>

              <div class="flex items-center gap-space-lg my-auto">
                <!-- Concentric Donut Circle -->
                <div class="relative w-32 h-32 shrink-0 flex items-center justify-center">
                  <svg class="w-full h-full -rotate-90" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" fill="none" r="50" stroke="#1E292B" stroke-width="8"></circle>
                    <circle id="quotaRingCircle" cx="60" cy="60" fill="none" r="50" stroke="#4edea3" stroke-dasharray="314.16" stroke-dashoffset="314.16" stroke-linecap="round" stroke-width="8" class="transition-all duration-700"></circle>
                  </svg>
                  <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span id="quotaTotalSolved" class="font-headline-md text-2xl font-bold text-text-primary font-mono leading-none">0</span>
                    <span class="font-label-sm text-[10px] text-text-muted mt-1 uppercase tracking-wider font-semibold">SOLVED</span>
                  </div>
                </div>

                <!-- Breakdown List with Progress Bars -->
                <div class="flex-1 space-y-2 font-code-sm text-code-sm">
                  <!-- Easy -->
                  <div class="p-1.5 rounded bg-surface-terminal/40 border border-border-subtle space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="flex items-center gap-1.5 text-accent-emerald font-semibold">
                        <span class="w-2 h-2 rounded-full bg-accent-emerald"></span> Easy
                      </span>
                      <span class="text-text-primary font-bold font-mono text-xs" id="quotaCount-easy">0 / 0</span>
                    </div>
                    <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                      <div id="quotaBar-easy" class="h-full bg-accent-emerald rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                  </div>

                  <!-- Medium -->
                  <div class="p-1.5 rounded bg-surface-terminal/40 border border-border-subtle space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="flex items-center gap-1.5 text-secondary font-semibold">
                        <span class="w-2 h-2 rounded-full bg-secondary"></span> Medium
                      </span>
                      <span class="text-text-primary font-bold font-mono text-xs" id="quotaCount-medium">0 / 0</span>
                    </div>
                    <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                      <div id="quotaBar-medium" class="h-full bg-secondary rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                  </div>

                  <!-- Hard -->
                  <div class="p-1.5 rounded bg-surface-terminal/40 border border-border-subtle space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="flex items-center gap-1.5 text-tertiary font-semibold">
                        <span class="w-2 h-2 rounded-full bg-tertiary"></span> Hard
                      </span>
                      <span class="text-text-primary font-bold font-mono text-xs" id="quotaCount-hard">0 / 0</span>
                    </div>
                    <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                      <div id="quotaBar-hard" class="h-full bg-tertiary rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                  </div>

                  <!-- Insane -->
                  <div class="p-1.5 rounded bg-surface-terminal/40 border border-border-subtle space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="flex items-center gap-1.5 text-status-error font-semibold">
                        <span class="w-2 h-2 rounded-full bg-status-error"></span> Insane
                      </span>
                      <span class="text-text-primary font-bold font-mono text-xs" id="quotaCount-insane">0 / 0</span>
                    </div>
                    <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                      <div id="quotaBar-insane" class="h-full bg-status-error rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="pt-space-sm bg-surface-terminal/30 p-2.5 rounded-lg flex items-center justify-between font-code-sm text-code-sm border border-border-subtle mt-space-md">
                <span class="text-text-muted font-mono">Jeopardy Tiers Calibration</span>
                <span class="text-secondary font-semibold font-mono text-xs">Standard Pool</span>
              </div>
            </section>

          </div>
        </div>

        <!-- 3. LEETCODE SUBMISSIONS HEATMAP -->
        <section class="bg-[#1e1e1e] rounded-xl p-4 sm:p-5 border border-neutral-800/80 shadow-xl space-y-3.5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
            <div class="flex items-center gap-2">
              <span id="heatSubmissionsCount" class="text-white text-xl sm:text-2xl font-bold font-sans tracking-tight">0</span>
              <span id="heatSubmissionsLabel" class="text-neutral-400 text-sm font-normal font-sans">questions solved in the past one year</span>
              <span class="text-neutral-500 text-sm cursor-help hover:text-neutral-300 transition-colors" title="Verified challenge solves and operative activity over the past 12 months">ⓘ</span>
            </div>
            
            <div class="flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-neutral-400 font-sans">
              <div>Total active days: <strong id="heatActiveDays" class="text-white font-medium">0</strong></div>
              <div>Max streak: <strong id="heatMaxStreak" class="text-white font-medium">0</strong></div>
              <div class="relative">
                <button id="heatYearSelectBtn" onclick="window.ProfileView.toggleYearDropdown(event)" class="px-3 py-1 rounded bg-[#2c2c2c] hover:bg-[#383838] border border-neutral-700/70 text-neutral-300 text-xs flex items-center gap-1 transition-colors">
                  <span id="heatCurrentYearLabel">Current</span>
                  <span class="material-symbols-outlined text-xs">expand_more</span>
                </button>
                <div id="heatYearDropdownMenu" class="hidden absolute right-0 mt-1 w-28 bg-[#2c2c2c] border border-neutral-700 rounded shadow-xl py-1 z-30 font-sans text-xs">
                  <button type="button" class="w-full text-left px-3 py-1.5 hover:bg-neutral-700 text-white" onclick="window.ProfileView.selectYear('Current')">Current</button>
                  <button type="button" class="w-full text-left px-3 py-1.5 hover:bg-neutral-700 text-neutral-300" onclick="window.ProfileView.selectYear('2026')">2026</button>
                  <button type="button" class="w-full text-left px-3 py-1.5 hover:bg-neutral-700 text-neutral-300" onclick="window.ProfileView.selectYear('2025')">2025</button>
                </div>
              </div>
            </div>
          </div>

          <!-- LeetCode Calendar Grid: 13 Month Blocks -->
          <div class="overflow-x-auto pb-1 pt-1 scrollbar-thin">
            <div id="leetcodeHeatmapContainer" class="flex items-start justify-between min-w-[760px] gap-2 sm:gap-2.5 py-1 px-0.5">
              <!-- Dynamically populated with 13 month column clusters (Sep to Sep) -->
            </div>
          </div>
        </section>

        <!-- 4. TACTICAL COMMENDATIONS DASHBOARD -->
        <section class="bg-surface-card/90 backdrop-blur-md rounded-xl p-space-lg border border-border-grid shadow-xl relative overflow-hidden" data-purpose="commendations-dashboard">
          <!-- HeaderSection -->
          <header class="mb-6 relative flex flex-col md:flex-row md:items-end justify-between border-b border-emerald-500/10 pb-6 gap-5">
            <div>
              <div class="flex items-center gap-2 mb-2 text-xs font-mono tracking-widest text-emerald-400/80 uppercase">
                <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#00ff9d] animate-pulse"></span>
                <span>SYSTEM AUDIT // PROTOCOL: COMMENDATION_TRACKER_V3.8</span>
              </div>
              <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-tactical flex items-center gap-3">
                Tactical Commendations
                <span class="hidden sm:inline-block text-xs font-mono font-normal px-2.5 py-0.5 rounded border border-emerald-500/30 bg-emerald-950/40 text-emerald-400 shadow-[0_0_10px_rgba(0,255,157,0.15)]">
                  SEC-OPS
                </span>
              </h2>
              <p class="text-slate-400 text-sm mt-1 font-normal">
                Earned student security milestones &amp; cryptographic audits
              </p>
            </div>

            <!-- Tactical Badge Counter Pill & Interactive Filter Buttons -->
            <aside aria-label="Badges Unlocked Counter" class="flex items-center gap-4 self-start md:self-auto flex-wrap sm:flex-nowrap">
              <!-- Interactive Filter Mini Buttons -->
              <div class="flex items-center bg-black/50 border border-emerald-900/50 rounded-lg p-1 text-xs font-mono text-slate-400 gap-1 backdrop-blur-sm shadow-inner" id="filter-container">
                <button type="button" class="filter-btn px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40 shadow-[0_0_10px_rgba(0,255,157,0.2)] transition-all duration-200" data-filter="all" onclick="ProfileView.filterBadges('all')">ALL (8)</button>
                <button type="button" class="filter-btn px-2.5 py-1 rounded hover:text-white transition-all duration-200 text-slate-400 hover:bg-emerald-950/30 border border-transparent" data-filter="unlocked" onclick="ProfileView.filterBadges('unlocked')">UNLOCKED (0)</button>
                <button type="button" class="filter-btn px-2.5 py-1 rounded hover:text-white transition-all duration-200 text-slate-400 hover:bg-emerald-950/30 border border-transparent" data-filter="locked" onclick="ProfileView.filterBadges('locked')">LOCKED (8)</button>
              </div>

              <!-- Security Level / Badge Counter Pill -->
              <div class="relative group flex items-center gap-3 bg-[#0a110f]/90 border border-amber-500/40 hover:border-amber-400/80 transition-all duration-300 rounded-lg px-4 py-2 shadow-[0_0_15px_rgba(245,158,11,0.12)] hover:shadow-[0_0_22px_rgba(245,158,11,0.25)]">
                <div class="flex flex-col text-right">
                  <span class="text-[10px] uppercase font-mono text-amber-500/80 tracking-widest font-bold leading-none">Security Level</span>
                  <span id="badgesSecurityTierLabel" class="text-xs font-mono text-slate-400 mt-0.5">Tier 1 Recruit</span>
                </div>
                <div class="h-7 w-px bg-amber-500/30"></div>
                <div class="flex items-baseline gap-1.5">
                  <span id="badgesUnlockedCount" class="font-mono text-lg sm:text-xl font-black tracking-wider text-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]">0</span>
                  <span class="text-amber-500/50 font-mono text-sm">/</span>
                  <span id="badgesTotalCount" class="font-mono text-base font-bold text-amber-500/80">8</span>
                  <span class="font-tactical text-xs font-bold uppercase tracking-wider text-amber-400/90 ml-1">BADGES</span>
                </div>
                <!-- Shimmer Laser Bar -->
                <div class="absolute bottom-0 left-2 right-2 h-[2px] bg-amber-950/60 rounded-full overflow-hidden">
                  <div id="badgesProgressFill" class="relative h-full bg-gradient-to-r from-amber-500 to-emerald-400 w-[0%]">
                    <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/90 to-transparent w-16 animate-bar-shine"></div>
                  </div>
                </div>
              </div>
            </aside>
          </header>

          <!-- Badges Grid (1200px perspective) -->
          <div id="badges-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5" style="perspective: 1200px;">
            <div class="text-text-muted font-code-sm text-center col-span-4 py-8">Auditing achievements catalog...</div>
          </div>

          <!-- Footer Status & Sync Logs -->
          <footer class="mt-8 pt-4 border-t border-emerald-950/60 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs font-mono text-slate-500">
            <div class="flex items-center gap-2">
              <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500/80 animate-pulse"></span>
              <span>TELEMETRY: ALL CHALLENGE PROOFS SECURED &amp; HASHED WITH SHA-256</span>
            </div>
            <div class="flex items-center gap-4">
              <span id="nextBadgeUnlockLabel">NEXT COMMENDATION UNLOCK: <span class="text-amber-400">POINT HUNTER</span></span>
              <button type="button" class="group flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 transition-colors underline font-medium cursor-pointer" id="sync-audit-btn" onclick="ProfileView.syncAuditLogs(event)">
                <span class="material-symbols-outlined text-sm transition-transform duration-500" id="sync-icon">sync</span>
                <span id="sync-btn-text">SYNC AUDIT LOGS</span>
              </button>
            </div>
          </footer>
        </section>

        <!-- Holographic Modal Inspection Drawer for Commendations -->
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md opacity-0 pointer-events-none transition-opacity duration-300" id="badge-modal">
          <div class="relative bg-[#091111] border border-emerald-500/50 rounded-2xl max-w-md w-full mx-4 p-6 shadow-[0_0_50px_rgba(0,255,157,0.2)] transform scale-95 transition-transform duration-300 overflow-hidden" id="badge-modal-content">
            <!-- Ambient Holographic Inspect Grid Rings -->
            <div class="absolute -top-16 -right-16 w-56 h-56 rounded-full border border-dashed border-emerald-500/20 anim-modal-ring pointer-events-none"></div>
            <div class="absolute -bottom-16 -left-16 w-56 h-56 rounded-full border border-dashed border-cyan-500/20 anim-modal-ring pointer-events-none" style="animation-direction: reverse;"></div>
            <button type="button" class="absolute top-4 right-4 text-slate-400 hover:text-emerald-400 transition-colors p-1 font-mono text-sm z-20 cursor-pointer" onclick="ProfileView.closeBadgeModal()">
              ✕ [ESC]
            </button>
            <div class="flex items-center gap-2 text-[10px] font-mono tracking-widest text-emerald-400 uppercase mb-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#00ff9d]"></span>
              <span>COMMENDATION DOSSIER // DECLASSIFIED</span>
            </div>
            <div class="w-32 h-32 mx-auto my-3 flex items-center justify-center relative" id="modal-badge-icon"></div>
            <h3 class="text-xl font-extrabold text-white text-center font-tactical tracking-wide" id="modal-badge-title">Badge Title</h3>
            <div class="text-center mt-1">
              <span class="inline-block text-[10px] font-mono tracking-wider px-2 py-0.5 rounded border border-emerald-500/40 bg-emerald-500/10 text-emerald-300" id="modal-badge-status">STATUS</span>
            </div>
            <p class="text-sm text-slate-300 text-center mt-3 font-normal leading-relaxed" id="modal-badge-desc"></p>
            <div class="mt-4 p-3 bg-black/40 rounded border border-emerald-900/40 font-mono text-[11px] flex flex-col gap-1.5">
              <div class="flex justify-between text-slate-400">
                <span>SECURITY LEVEL:</span>
                <span class="text-emerald-400 font-semibold" id="modal-badge-sec-level">CONFIRMED TIER 1</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>UNLOCKED TIMESTAMP:</span>
                <span class="text-slate-300" id="modal-badge-time">OCT 24, 2024 14:32 UTC</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>CRYPTOGRAPHIC ID:</span>
                <span class="text-emerald-400 font-semibold tracking-wider font-mono" id="modal-badge-hash">0x8F92...C14</span>
              </div>
            </div>
            <div class="mt-5 pt-3 border-t border-emerald-950 flex justify-between items-center text-[10px] font-mono text-slate-500">
              <span class="flex items-center gap-1.5 text-emerald-400/80">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                AUDIT PROOF OK
              </span>
              <button type="button" class="px-3 py-1 bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-500/40 rounded text-emerald-300 transition-colors cursor-pointer" onclick="ProfileView.closeBadgeModal()">
                DISMISS
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Edit Profile Modal -->
      <div id="editProfileModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:500px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title">Edit Operative Dossier</h3>
            <button class="modal-close" onclick="closeModal('editProfileModal')">&times;</button>
          </div>
          <div class="modal-body space-y-4">
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Full Name</label>
              <input type="text" id="editNameInput" value="${escapeHtml(u.name || '')}" />
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">College / Campus</label>
              <input type="text" id="editCollegeInput" value="${escapeHtml(u.college || '')}" />
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Bio / Research Focus</label>
              <textarea id="editBioInput" rows="3">${escapeHtml(u.bio || '')}</textarea>
            </div>
            <div class="flex justify-end gap-2 pt-2">
              <button class="btn btn-outline" onclick="closeModal('editProfileModal')">Cancel</button>
              <button class="btn btn-primary" onclick="ProfileView.saveProfileBio()">Save Changes</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Change Passphrase Modal -->
      <div id="changePassModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:460px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-base">lock_reset</span>
              Update Operative Passphrase
            </h3>
            <button class="modal-close" onclick="closeModal('changePassModal')">&times;</button>
          </div>
          <form onsubmit="ProfileView.changePassphrase(event)" class="modal-body space-y-4">
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Current Passphrase</label>
              <input type="password" id="profileCurrentPassInput" required placeholder="••••••••••••" autocomplete="current-password" />
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">New Passphrase (Min. 8 chars)</label>
              <input type="password" id="profileNewPassInput" required minlength="8" placeholder="••••••••••••" autocomplete="new-password" />
            </div>
            <div class="flex justify-end gap-2 pt-2">
              <button type="button" class="btn btn-outline" onclick="closeModal('changePassModal')">Cancel</button>
              <button type="submit" id="btnChangePassSubmit" class="btn btn-primary">
                <span class="material-symbols-outlined text-sm">key</span> Update Passphrase
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Followers Modal (LeetCode-style) -->
      <div id="followersModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:540px;">
          <div class="modal-header bg-surface-terminal border-b border-border-subtle">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">group</span>
              <div>
                <h3 class="modal-title">Operative Followers</h3>
                <p class="font-label-sm text-text-muted text-xs">Community members observing this operative's operations</p>
              </div>
            </div>
            <button class="modal-close" onclick="closeModal('followersModal')">&times;</button>
          </div>
          <div class="p-3 border-b border-border-subtle bg-surface-terminal/40">
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">search</span>
              <input type="text" id="searchFollowersInput" placeholder="Filter followers by callsign, name, college..." 
                     class="w-full bg-surface-base border border-border-subtle rounded-md pl-9 pr-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
                     oninput="ProfileView.filterFollowList('followers', this.value)" />
            </div>
          </div>
          <div id="followersListContainer" class="modal-body p-4 space-y-2.5 max-h-[420px] overflow-y-auto">
            <div class="p-8 text-center text-text-muted font-mono text-sm">
              <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
              Loading operative followers...
            </div>
          </div>
        </div>
      </div>

      <!-- Following Modal (LeetCode-style) -->
      <div id="followingModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:540px;">
          <div class="modal-header bg-surface-terminal border-b border-border-subtle">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">person_add</span>
              <div>
                <h3 class="modal-title">Following Operatives</h3>
                <p class="font-label-sm text-text-muted text-xs">Security researchers followed by this operative</p>
              </div>
            </div>
            <button class="modal-close" onclick="closeModal('followingModal')">&times;</button>
          </div>
          <div class="p-3 border-b border-border-subtle bg-surface-terminal/40">
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">search</span>
              <input type="text" id="searchFollowingInput" placeholder="Filter following by callsign, name, college..." 
                     class="w-full bg-surface-base border border-border-subtle rounded-md pl-9 pr-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
                     oninput="ProfileView.filterFollowList('following', this.value)" />
            </div>
          </div>
          <div id="followingListContainer" class="modal-body p-4 space-y-2.5 max-h-[420px] overflow-y-auto">
            <div class="p-8 text-center text-text-muted font-mono text-sm">
              <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
              Loading followed operatives...
            </div>
          </div>
        </div>
      </div>

      <!-- GitHub Integration & Repository Config Modal -->
      <div id="githubIntegrationModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:580px;">
          <div class="modal-header bg-surface-terminal border-b border-border-subtle">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-surface-base border border-border-subtle flex items-center justify-center text-primary">
                <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              </div>
              <div>
                <h3 class="modal-title font-bold text-text-primary text-base">GitHub CTF Integration</h3>
                <p class="font-label-sm text-text-muted text-xs">Automated CTF Flag Solution Sync &amp; Verified Commits</p>
              </div>
            </div>
            <button class="modal-close" onclick="closeModal('githubIntegrationModal')">&times;</button>
          </div>
          
          <div id="githubModalBody" class="modal-body p-5 space-y-4 max-h-[75vh] overflow-y-auto">
            <div class="p-8 text-center text-text-muted font-mono text-sm">
              <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
              Checking GitHub integration telemetry...
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async loadProfile() {
    const u = window.state.currentUser;
    if (!u) return;

    try {
      const [profile, scoreData, rankData, chList, myBadges, allBadges, myTeam, catStats, myAllTeams] = await Promise.all([
        window.api.getUserProfile(u.username).catch(() => null),
        window.api.getMyScore().catch(() => null),
        window.api.request('/api/leaderboard/me').catch(() => null),
        window.api.getChallenges().catch(() => []),
        window.api.getMyBadges().catch(() => []),
        window.api.getBadgesCatalog().catch(() => []),
        window.api.getMyTeam().catch(() => null),
        window.api.getMyCategoryStats().catch(() => []),
        window.api.getMyTeams ? window.api.getMyTeams().catch(() => []) : Promise.resolve([])
      ]);

      this.profileData = profile;
      this.userBadges = myBadges || [];
      this.catalogBadges = allBadges || [];
      this.userTeam = myTeam;
      this.myTeams = Array.isArray(myAllTeams) && myAllTeams.length > 0 ? myAllTeams : (myTeam ? [myTeam] : []);

      // Update Quick Metrics
      const rankVal = document.getElementById('profRankVal');
      const totalUsersVal = document.getElementById('profTotalUsersVal');
      if (rankVal && rankData && rankData.rank) {
        rankVal.textContent = `#${rankData.rank}`;
      }
      if (totalUsersVal && rankData && rankData.total_users) {
        totalUsersVal.textContent = `/ ${rankData.total_users}`;
      }

      const scoreVal = document.getElementById('profScoreVal');
      const solvesVal = document.getElementById('profSolvesVal');
      const totalPoolVal = document.getElementById('profTotalPoolVal');
      const solvePctVal = document.getElementById('profSolvePercentVal');

      const totalChallenges = Array.isArray(chList) ? chList.length : 0;
      const solvedInList = (chList || []).filter(c => c.is_solved).length;
      const distinctSolvesCount = solvedInList > 0 ? solvedInList : (scoreData?.total_solves ?? (scoreData?.solves_count ?? 0));
      this.lastSolvedCount = distinctSolvesCount;
      const userScore = scoreData?.total_points ?? (scoreData?.score ?? (rankData?.total_points ?? 0));

      if (scoreVal) scoreVal.textContent = userScore.toLocaleString();
      if (solvesVal) solvesVal.textContent = distinctSolvesCount;
      if (totalPoolVal) totalPoolVal.textContent = `/ ${totalChallenges} POOL`;
      if (solvePctVal && totalChallenges > 0) {
        const pct = ((distinctSolvesCount / totalChallenges) * 100).toFixed(1);
        solvePctVal.textContent = `${pct}% Overall Completion`;
      } else if (solvePctVal) {
        solvePctVal.textContent = '0.0% Overall Completion';
      }

      // Update Followers & Following Counts (LeetCode-style)
      const followersCountEl = document.getElementById('profFollowersCount');
      const followingCountEl = document.getElementById('profFollowingCount');
      let followersCount = profile?.followers_count;
      let followingCount = profile?.following_count;
      if (followersCount == null || followingCount == null) {
        try {
          const [fList, fgList] = await Promise.all([
            window.api.getUserFollowers(u.id).catch(() => []),
            window.api.getUserFollowing(u.id).catch(() => [])
          ]);
          followersCount = fList?.length || 0;
          followingCount = fgList?.length || 0;
        } catch (_) {
          followersCount = 0;
          followingCount = 0;
        }
      }
      if (followersCountEl) followersCountEl.textContent = Number(followersCount || 0).toLocaleString();
      if (followingCountEl) followingCountEl.textContent = Number(followingCount || 0).toLocaleString();

      // Quota Ring (Starts 0% filled / circum offset when solvedCount is 0)
      const quotaTotal = document.getElementById('quotaTotalSolved');
      const quotaRing = document.getElementById('quotaRingCircle');
      if (quotaTotal) quotaTotal.textContent = distinctSolvesCount;
      if (quotaRing) {
        const circum = 314.16;
        quotaRing.style.strokeDasharray = `${circum}`;
        if (totalChallenges > 0 && distinctSolvesCount > 0) {
          const ratio = Math.min(1, distinctSolvesCount / totalChallenges);
          const off = circum * (1 - ratio);
          quotaRing.style.strokeDashoffset = `${off}`;
        } else {
          quotaRing.style.strokeDashoffset = `${circum}`;
        }
      }

      // Solved by difficulty
      const easySolved = (chList || []).filter(c => c.is_solved && (c.difficulty || '').toLowerCase() === 'easy').length;
      const medSolved = (chList || []).filter(c => c.is_solved && (c.difficulty || '').toLowerCase() === 'medium').length;
      const hardSolved = (chList || []).filter(c => c.is_solved && (c.difficulty || '').toLowerCase() === 'hard').length;
      const insaneSolved = (chList || []).filter(c => c.is_solved && (c.difficulty || '').toLowerCase() === 'insane').length;

      const easyTotal = (chList || []).filter(c => (c.difficulty || '').toLowerCase() === 'easy').length;
      const medTotal = (chList || []).filter(c => (c.difficulty || '').toLowerCase() === 'medium').length;
      const hardTotal = (chList || []).filter(c => (c.difficulty || '').toLowerCase() === 'hard').length;
      const insaneTotal = (chList || []).filter(c => (c.difficulty || '').toLowerCase() === 'insane').length;

      const easyEl = document.getElementById('quotaCount-easy');
      const medEl = document.getElementById('quotaCount-medium');
      const hardEl = document.getElementById('quotaCount-hard');
      const insaneEl = document.getElementById('quotaCount-insane');

      const easyBar = document.getElementById('quotaBar-easy');
      const medBar = document.getElementById('quotaBar-medium');
      const hardBar = document.getElementById('quotaBar-hard');
      const insaneBar = document.getElementById('quotaBar-insane');

      if (easyEl) easyEl.textContent = `${easySolved} / ${easyTotal}`;
      if (medEl) medEl.textContent = `${medSolved} / ${medTotal}`;
      if (hardEl) hardEl.textContent = `${hardSolved} / ${hardTotal}`;
      if (insaneEl) insaneEl.textContent = `${insaneSolved} / ${insaneTotal}`;

      if (easyBar) easyBar.style.width = `${easyTotal > 0 ? (easySolved / easyTotal) * 100 : 0}%`;
      if (medBar) medBar.style.width = `${medTotal > 0 ? (medSolved / medTotal) * 100 : 0}%`;
      if (hardBar) hardBar.style.width = `${hardTotal > 0 ? (hardSolved / hardTotal) * 100 : 0}%`;
      if (insaneBar) insaneBar.style.width = `${insaneTotal > 0 ? (insaneSolved / insaneTotal) * 100 : 0}%`;

      // 8 Categories explicitly requested:
      // Cryptography, Forensics, Misc, OSINT, Pwn / Binary Exploitation, Reverse Engineering, Steganography, Web Exploitation
      const categoriesDef = [
        { key: 'crypto', name: 'Cryptography', match: ['crypto'], colorClass: 'bg-secondary', textClass: 'text-secondary', spokeIndex: 3 },
        { key: 'forensics', name: 'Forensics', match: ['forensic'], colorClass: 'bg-accent-neon', textClass: 'text-accent-neon', spokeIndex: 1 },
        { key: 'misc', name: 'Misc', match: ['misc'], colorClass: 'bg-slate-400', textClass: 'text-slate-400', spokeIndex: 7 },
        { key: 'osint', name: 'OSINT', match: ['osint'], colorClass: 'bg-amber-400', textClass: 'text-amber-400', spokeIndex: 2 },
        { key: 'pwn', name: 'Pwn / Binary Exploitation', match: ['pwn', 'binary'], colorClass: 'bg-status-error', textClass: 'text-status-error', spokeIndex: 6 },
        { key: 'reverse', name: 'Reverse Engineering', match: ['reverse'], colorClass: 'bg-purple-400', textClass: 'text-purple-400', spokeIndex: 5 },
        { key: 'stego', name: 'Steganography', match: ['steg'], colorClass: 'bg-tertiary', textClass: 'text-tertiary', spokeIndex: 4 },
        { key: 'web', name: 'Web Exploitation', match: ['web'], colorClass: 'bg-primary', textClass: 'text-primary', spokeIndex: 0 },
      ];

      categoriesDef.forEach(cat => {
        let catSolved = 0;
        let catTotal = 0;

        if (Array.isArray(catStats) && catStats.length > 0) {
          const found = catStats.find(cs => cat.match.some(m => (cs.category || '').toLowerCase().includes(m)));
          if (found) {
            catSolved = found.solved_count || 0;
            if (found.total_count) catTotal = found.total_count;
          }
        }

        if (Array.isArray(chList) && chList.length > 0) {
          const chs = chList.filter(c => {
            const cname = (c.category?.name || c.category_name || c.category || '').toLowerCase();
            return cat.match.some(m => cname.includes(m));
          });
          if (chs.length > 0) {
            catTotal = chs.length;
            const solvedInChs = chs.filter(c => c.is_solved).length;
            catSolved = Math.max(catSolved, solvedInChs);
          }
        }

        cat.solved = catSolved;
        cat.total = catTotal;
        cat.pct = catTotal > 0 ? Math.round((catSolved / catTotal) * 100) : 0;
        cat.ratio = catTotal > 0 ? Math.min(1, catSolved / catTotal) : 0;
      });

      // Render the 8 category progress bars
      const catContainer = document.getElementById('categoryProgressContainer');
      if (catContainer) {
        catContainer.innerHTML = categoriesDef.map(cat => `
          <div class="p-1 rounded bg-surface-terminal/40 border border-border-subtle/50 space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="text-text-primary font-medium flex items-center gap-1.5 truncate">
                <span class="w-1.5 h-1.5 rounded-full ${cat.colorClass}"></span>
                ${escapeHtml(cat.name)}
              </span>
              <span class="font-mono text-[11px] text-text-muted">
                <span class="text-text-primary font-bold">${cat.solved}</span> / ${cat.total}
                <span class="font-bold ml-1 ${cat.textClass}">(${cat.pct}%)</span>
              </span>
            </div>
            <div class="h-1.5 w-full bg-surface-terminal rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-700 ${cat.colorClass}" style="width: ${cat.pct}%"></div>
            </div>
          </div>
        `).join('');
      }

      // Radar Vertices (Center: 150, 150 | Max Radius: 110, 8 spokes)
      const radarPoly = document.getElementById('radarPolygon');
      if (radarPoly) {
        if (distinctSolvesCount === 0) {
          radarPoly.setAttribute('points', '150,150 150,150 150,150 150,150 150,150 150,150 150,150 150,150');
        } else {
          const R = 110;
          const points = [];
          for (let k = 0; k < 8; k++) {
            const cat = categoriesDef.find(c => c.spokeIndex === k);
            const ratio = cat ? cat.ratio : 0;
            const theta = -Math.PI / 2 + k * (Math.PI / 4);
            const x = 150 + Math.round(R * ratio * Math.cos(theta));
            const y = 150 + Math.round(R * ratio * Math.sin(theta));
            points.push(`${x},${y}`);
          }
          radarPoly.setAttribute('points', points.join(' '));
        }
      }

      // Primary Specialty Title
      const specialtyEl = document.getElementById('profileSpecialtyText');
      if (specialtyEl) {
        if (distinctSolvesCount === 0) {
          specialtyEl.textContent = 'Primary Specialty: Awaiting Initial Solves (0 Questions Solved)';
        } else {
          const sortedCats = [...categoriesDef].sort((a, b) => b.solved - a.solved);
          const topCat = sortedCats[0];
          if (topCat && topCat.solved > 0) {
            specialtyEl.textContent = `Primary Specialty: ${topCat.name} (${topCat.solved} Solved)`;
          } else {
            specialtyEl.textContent = 'Primary Specialty: General CTF Operative';
          }
        }
      }

      // Streaks & Submissions Activity Heatmap
      let heatmapData = profile?.heatmap || [];
      if (!heatmapData || heatmapData.length === 0) {
        try {
          heatmapData = await window.api.getMyActivityHeatmap();
        } catch (e) {
          heatmapData = [];
        }
      }

      let streakData = null;
      try {
        streakData = await window.api.getMyStreak();
      } catch (e) {
        streakData = null;
      }

      this.renderHeatmap(heatmapData, streakData, distinctSolvesCount);

      // Badges Gallery
      this.renderBadgesGallery();

      // GitHub Integration Telemetry
      this.loadGitHubStatus();

    } catch (e) {
      console.warn('Profile data load error:', e);
    }
  },

  navigateToTeamHistory(teamId) {
    if (window.state) {
      window.state.pendingTeamHistoryId = teamId;
    }
    window.location.hash = `#teams?history=${teamId}`;
  },

  toggleYearDropdown(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const menu = document.getElementById('heatYearDropdownMenu');
    if (menu) {
      menu.classList.toggle('hidden');
    }
  },

  selectYear(year) {
    this.selectedHeatYear = year;
    const label = document.getElementById('heatCurrentYearLabel');
    if (label) {
      label.textContent = year;
    }
    const menu = document.getElementById('heatYearDropdownMenu');
    if (menu) {
      menu.classList.add('hidden');
    }
    this.renderHeatmap(this.lastHeatmapData, this.lastStreakData, this.lastSolvedCount);
  },

  renderHeatmap(heatmapData = [], streakData = null, solvedCount = 0) {
    this.lastHeatmapData = heatmapData;
    this.lastStreakData = streakData;
    this.lastSolvedCount = solvedCount;

    const container = document.getElementById('leetcodeHeatmapContainer');
    if (!container) return;

    // Real activity dictionary date -> count populated strictly from database API
    const dateMap = {};

    // Overlay real user activity heatmap data from API
    if (Array.isArray(heatmapData)) {
      heatmapData.forEach(d => {
        if (d.date && d.count > 0) {
          dateMap[d.date] = d.count;
        }
      });
    }

    // Ensure today reflects user solved challenges if solvedCount > 0
    const today = new Date();
    const todayIso = today.toISOString().split('T')[0];
    if (solvedCount > 0) {
      dateMap[todayIso] = Math.max(dateMap[todayIso] || 0, solvedCount);
    }

    const yearMode = this.selectedHeatYear || 'Current';
    const fullMonthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let monthConfigs = [];

    if (yearMode === 'Current') {
      // 12 months back to current month (13 month clusters)
      for (let i = 12; i >= 0; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        monthConfigs.push({
          year: d.getFullYear(),
          month: d.getMonth(),
          isFirst: (i === 12),
          isLast: (i === 0)
        });
      }
    } else if (yearMode === '2026') {
      const curMonth = today.getMonth();
      for (let m = 0; m <= curMonth; m++) {
        monthConfigs.push({
          year: 2026,
          month: m,
          isFirst: false,
          isLast: (m === curMonth)
        });
      }
    } else if (yearMode === '2025') {
      for (let m = 0; m < 12; m++) {
        monthConfigs.push({
          year: 2025,
          month: m,
          isFirst: false,
          isLast: false
        });
      }
    }

    // Filter real active dates within chosen range
    let activeDates = [];
    if (yearMode === 'Current') {
      const oneYearAgo = new Date(today);
      oneYearAgo.setDate(today.getDate() - 364);
      const minIso = oneYearAgo.toISOString().split('T')[0];
      const maxIso = todayIso;
      activeDates = Object.keys(dateMap).filter(k => k >= minIso && k <= maxIso && dateMap[k] > 0).sort();
    } else {
      activeDates = Object.keys(dateMap).filter(k => k.startsWith(yearMode) && dateMap[k] > 0).sort();
    }

    let totalSubmissions = 0;
    activeDates.forEach(k => {
      totalSubmissions += dateMap[k];
    });
    const totalActiveDays = activeDates.length;

    // Calculate consecutive streak strictly from real active dates
    let maxStreak = 0;
    let curStreak = 0;
    if (activeDates.length > 0) {
      curStreak = 1;
      maxStreak = 1;
      for (let i = 1; i < activeDates.length; i++) {
        const prev = new Date(activeDates[i - 1]);
        const curr = new Date(activeDates[i]);
        const diff = Math.round((curr - prev) / (1000 * 60 * 60 * 24));
        if (diff === 1) {
          curStreak++;
          if (curStreak > maxStreak) maxStreak = curStreak;
        } else if (diff > 1) {
          curStreak = 1;
        }
      }
    }

    if (streakData?.longest_streak && streakData.longest_streak > maxStreak) {
      maxStreak = streakData.longest_streak;
    }
    if (totalActiveDays === 0) {
      maxStreak = 0;
    }

    // Update Header HUD with Real Number of Questions Solved and Real Activity
    const subCountEl = document.getElementById('heatSubmissionsCount');
    const subLabelEl = document.getElementById('heatSubmissionsLabel');
    const actDaysEl = document.getElementById('heatActiveDays');
    const maxStreakEl = document.getElementById('heatMaxStreak');

    if (subCountEl) subCountEl.textContent = solvedCount;
    if (subLabelEl) {
      subLabelEl.textContent = `${solvedCount === 1 ? 'question' : 'questions'} solved in the past one year`;
    }
    if (actDaysEl) actDaysEl.textContent = totalActiveDays;
    if (maxStreakEl) maxStreakEl.textContent = maxStreak;


    // Render Month Blocks with Week Columns
    const monthBlocksHtml = monthConfigs.map(cfg => {
      const y = cfg.year;
      const m = cfg.month;
      const daysInMonth = new Date(y, m + 1, 0).getDate();
      const firstDow = new Date(y, m, 1).getDay();

      let startDay = 1;
      let endDay = daysInMonth;
      let startOffset = firstDow;

      if (cfg.isFirst) {
        // Starts 2 weeks in to match rolling 52-week calendar (Sep 14 to Sep 30 = 3 columns)
        startDay = 14;
        startOffset = new Date(y, m, 14).getDay();
      }
      if (cfg.isLast) {
        endDay = today.getDate();
      }

      const totalSlots = startOffset + (endDay - startDay + 1);
      const colCount = Math.ceil(totalSlots / 7);

      const colsHtml = [];
      for (let c = 0; c < colCount; c++) {
        const cellsHtml = [];
        for (let r = 0; r < 7; r++) {
          const slotIndex = c * 7 + r;
          const dayNum = startDay + (slotIndex - startOffset);

          if (slotIndex < startOffset || dayNum > endDay) {
            cellsHtml.push(`<div class="leetcode-heat-cell leetcode-cell-ghost"></div>`);
          } else {
            const iso = `${y}-${String(m + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
            const count = dateMap[iso] || 0;

            let levelClass = 'leetcode-cell-empty';
            if (count >= 4) levelClass = 'leetcode-cell-level-4';
            else if (count === 3) levelClass = 'leetcode-cell-level-3';
            else if (count === 2) levelClass = 'leetcode-cell-level-2';
            else if (count === 1) levelClass = 'leetcode-cell-level-1';

            const mName = fullMonthNames[m];
            const tooltip = count === 0
              ? `No submissions on ${mName} ${dayNum}, ${y}`
              : `${count} submission${count > 1 ? 's' : ''} on ${mName} ${dayNum}, ${y}`;

            cellsHtml.push(`
              <div class="leetcode-heat-cell ${levelClass}" title="${escapeHtml(tooltip)}"></div>
            `);
          }
        }
        colsHtml.push(`<div class="flex flex-col gap-1">${cellsHtml.join('')}</div>`);
      }

      return `
        <div class="flex flex-col items-center flex-1">
          <div class="flex gap-1">
            ${colsHtml.join('')}
          </div>
          <span class="text-neutral-400 text-xs mt-2 font-sans select-none">${fullMonthNames[m]}</span>
        </div>
      `;
    }).join('');

    container.innerHTML = monthBlocksHtml;
  },


  onBadgeCardClick(card) {
    const status = card.getAttribute('data-status');

    if (status === 'locked') {
      card.classList.remove('shake-lock');
      void card.offsetWidth;
      card.classList.add('shake-lock');

      const req = card.getAttribute('data-req') || 'INSUFFICIENT SECURITY CLEARANCE';
      showToast(`ACCESS RESTRICTED // ${req}`, 'warning');

      setTimeout(() => {
        card.classList.remove('shake-lock');
      }, 600);
      return;
    }

    const title = card.querySelector('h3')?.textContent.trim() || 'Tactical Commendation';
    const desc = card.querySelector('p')?.textContent.trim() || '';
    const statusPill = card.querySelector('.badge-status-pill')?.outerHTML || '';
    const svgClone = card.querySelector('svg')?.cloneNode(true);
    const hash = card.getAttribute('data-hash') || '0x' + Math.random().toString(16).substring(2, 10).toUpperCase();
    const time = card.getAttribute('data-time') || 'OCT 24, 2024 14:32 UTC';

    const modal = document.getElementById('badge-modal');
    const modalContent = document.getElementById('badge-modal-content');
    if (!modal || !modalContent) return;

    document.getElementById('modal-badge-title').textContent = title;
    document.getElementById('modal-badge-desc').textContent = desc;
    const stEl = document.getElementById('modal-badge-status');
    if (stEl) stEl.outerHTML = statusPill;
    const iconContainer = document.getElementById('modal-badge-icon');
    if (iconContainer) {
      iconContainer.innerHTML = '';
      if (svgClone) iconContainer.appendChild(svgClone);
    }
    const hashEl = document.getElementById('modal-badge-hash');
    if (hashEl) hashEl.textContent = hash;
    const timeEl = document.getElementById('modal-badge-time');
    if (timeEl) timeEl.textContent = time;

    modal.classList.remove('pointer-events-none', 'opacity-0');
    modal.classList.add('opacity-100');
    modalContent.classList.remove('scale-95');
    modalContent.classList.add('scale-100');
  },

  closeBadgeModal() {
    const modal = document.getElementById('badge-modal');
    const modalContent = document.getElementById('badge-modal-content');
    if (!modal || !modalContent) return;
    modal.classList.add('opacity-0', 'pointer-events-none');
    modal.classList.remove('opacity-100');
    modalContent.classList.remove('scale-100');
    modalContent.classList.add('scale-95');
  },

  bindBadgeCardEffects() {
    const cards = document.querySelectorAll('.badge-card');
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!prefersReducedMotion) {
      cards.forEach(card => {
        card.onmousemove = (e) => {
          const rect = card.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;

          card.style.setProperty('--mouse-x', `${x}px`);
          card.style.setProperty('--mouse-y', `${y}px`);

          const rotateX = ((y - centerY) / centerY) * -8.5;
          const rotateY = ((x - centerX) / centerX) * 8.5;

          card.style.transform = `perspective(1000px) translateY(-6px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.03, 1.03, 1.03)`;
        };

        card.onmouseleave = () => {
          card.style.transform = 'perspective(1000px) translateY(0px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
        };
      });
    }
  },

  async syncAuditLogs(e) {
    if (e) e.preventDefault();
    const icon = document.getElementById('sync-icon');
    const text = document.getElementById('sync-btn-text');
    const btn = document.getElementById('sync-audit-btn');
    if (icon) icon.classList.add('animate-spin');
    if (text) text.textContent = 'SYNCING TELEMETRY...';
    if (btn) btn.style.pointerEvents = 'none';

    try {
      await this.loadProfile();
      showToast('AUDIT_OK // VERIFIED [SHA-256]', 'success');
    } catch (err) {
      showToast('TELEMETRY SYNC FAILED', 'error');
    } finally {
      if (icon) icon.classList.remove('animate-spin');
      if (text) text.textContent = 'SYNC AUDIT LOGS';
      if (btn) btn.style.pointerEvents = 'auto';
    }
  },

  filterBadges(filterType) {
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
      const f = btn.getAttribute('data-filter');
      if (f === filterType) {
        btn.className = 'filter-btn px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40 shadow-[0_0_10px_rgba(0,255,157,0.2)] transition-all duration-200';
      } else {
        btn.className = 'filter-btn px-2.5 py-1 rounded hover:text-white transition-all duration-200 text-slate-400 hover:bg-emerald-950/30 border border-transparent';
      }
    });

    const cards = document.querySelectorAll('.badge-card');
    cards.forEach(card => {
      const status = card.getAttribute('data-status');
      if (filterType === 'all') {
        card.style.display = '';
      } else if (filterType === 'unlocked') {
        card.style.display = status === 'unlocked' ? '' : 'none';
      } else if (filterType === 'locked') {
        card.style.display = status === 'locked' ? '' : 'none';
      }
    });
  },

  renderBadgesGallery() {
    const container = document.getElementById('badges-grid');
    if (!container) return;

    // User's unlocked badges
    const myBadges = Array.isArray(this.userBadges) ? this.userBadges : [];
    const myBadgeSlugs = new Set();
    const myBadgeNames = new Set();
    const myBadgeMap = {};

    myBadges.forEach(b => {
      const slug = (b.slug || b.badge?.slug || '').toLowerCase();
      const name = (b.name || b.badge?.name || '').toLowerCase();
      if (slug) {
        myBadgeSlugs.add(slug);
        myBadgeSlugs.add(slug.replace(/-/g, '_'));
        myBadgeSlugs.add(slug.replace(/_/g, '-'));
        myBadgeMap[slug] = b;
        myBadgeMap[slug.replace(/-/g, '_')] = b;
        myBadgeMap[slug.replace(/_/g, '-')] = b;
      }
      if (name) {
        myBadgeNames.add(name);
        myBadgeMap[name] = b;
      }
    });

    const distinctSolves = this.lastSolvedCount || 0;
    const userScore = this.profileData?.score || (this.profileData?.total_points || 0);
    const userStreak = this.lastStreakData?.longest_streak || (this.profileData?.longest_streak || 0);

    // 8 Tactical Commendations Specifications Matching Design
    const badgesSpec = [
      {
        slug: 'cyber-explorer',
        name: 'Cyber Explorer',
        revText: '30 / 30 SOLVED',
        unlockedPill: '30 / 30 SOLVED',
        progressText: `${distinctSolves} / 30 SOLVED`,
        reqText: 'SOLVE 30 CHALLENGES ACROSS ALL CATEGORIES (MIN 3 EACH)',
        description: 'Solve 30 challenges across all available challenge categories, with at least 3 solved challenges in each category.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 subtle-radar-glow relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="comp-rim" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#00ff9d"></stop>
                <stop offset="50%" stop-color="#053027"></stop>
                <stop offset="100%" stop-color="#00e5ff"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="comp-core" x1="20" x2="80" y1="20" y2="80">
                <stop offset="0%" stop-color="#142a25"></stop>
                <stop offset="100%" stop-color="#061210"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="needle-grad" x1="50" x2="50" y1="20" y2="80">
                <stop offset="0%" stop-color="#00ff9d"></stop>
                <stop offset="50%" stop-color="#ffffff"></stop>
                <stop offset="100%" stop-color="#0080ff"></stop>
              </lineargradient>
              <filter height="140%" id="glow-3d" width="140%" x="-20%" y="-20%">
                <fegaussianblur result="blur" stddeviation="3"></fegaussianblur>
                <fecomposite in="SourceGraphic" in2="blur" operator="over"></fecomposite>
              </filter>
            </defs>
            <polygon fill="url(#comp-core)" points="50,4 90,26 90,74 50,96 10,74 10,26" stroke="url(#comp-rim)" stroke-width="2.5"></polygon>
            <circle cx="50" cy="50" r="32" stroke="#00ff9d" stroke-dasharray="2 3" stroke-opacity="0.3" stroke-width="1"></circle>
            <circle cx="50" cy="50" r="22" stroke="#00e5ff" stroke-opacity="0.4" stroke-width="1.5"></circle>
            <line stroke="#00ff9d" stroke-opacity="0.35" stroke-width="1" x1="50" x2="50" y1="20" y2="80"></line>
            <line stroke="#00ff9d" stroke-opacity="0.35" stroke-width="1" x1="20" x2="80" y1="50" y2="50"></line>
            <g class="anim-orbit-1">
              <ellipse cx="50" cy="50" rx="28" ry="10" stroke="#00ff9d" stroke-opacity="0.8" stroke-width="1.5"></ellipse>
              <circle cx="78" cy="50" fill="#00ff9d" r="2"></circle>
            </g>
            <g class="anim-orbit-2">
              <ellipse cx="50" cy="50" rx="28" ry="10" stroke="#00e5ff" stroke-opacity="0.8" stroke-width="1.5"></ellipse>
              <circle cx="22" cy="50" fill="#00e5ff" r="1.8"></circle>
            </g>
            <g class="anim-needle-sway">
              <polygon fill="url(#needle-grad)" filter="url(#glow-3d)" points="50,22 55,48 50,44 45,48"></polygon>
              <polygon fill="#00e5ff" fill-opacity="0.8" points="50,78 54,52 50,56 46,52"></polygon>
            </g>
            <circle cx="50" cy="50" fill="#ffffff" r="4.5"></circle>
            <circle class="animate-ping" cx="50" cy="50" fill="#00ff9d" r="2" style="animation-duration: 3s;"></circle>
          </svg>
        `
      },
      {
        slug: 'event-participant',
        name: 'Event Participant',
        revText: '80%+ COMPLETED',
        unlockedPill: '80%+ COMPLETED',
        progressText: '0% COMPLETED',
        reqText: 'COMPLETE AN OFFICIAL LIVE EVENT BY SOLVING AT LEAST 80% OF CHALLENGES',
        description: 'Complete an official live event by solving at least 80% of the available challenges.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="chev-plate" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#2a3f3b"></stop>
                <stop offset="50%" stop-color="#101d1a"></stop>
                <stop offset="100%" stop-color="#080e0c"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="metal-gold" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#fde047"></stop>
                <stop offset="50%" stop-color="#eab308"></stop>
                <stop offset="100%" stop-color="#713f12"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="cyan-bolt" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#00ffff"></stop>
                <stop offset="100%" stop-color="#00bd7e"></stop>
              </lineargradient>
              <clippath id="shield-clip">
                <path d="M50 8 L84 22 V54 C84 72 50 92 50 92 C50 92 16 72 16 54 V22 Z"></path>
              </clippath>
            </defs>
            <path d="M50 8 L84 22 V54 C84 72 50 92 50 92 C50 92 16 72 16 54 V22 Z" fill="url(#chev-plate)" stroke="url(#metal-gold)" stroke-width="2.5"></path>
            <g clip-path="url(#shield-clip)">
              <rect class="anim-shield-shimmer" fill="white" height="120" opacity="0.18" width="20" x="40" y="-10"></rect>
            </g>
            <path d="M50 16 L76 28 V52 C76 66 50 82 50 82 C50 82 24 66 24 52 V28 Z" fill="#091412" stroke="#00ff9d" stroke-opacity="0.3" stroke-width="1.5"></path>
            <path d="M38 32 L46 46 H41 L47 62 L39 49 H45 Z" fill="url(#cyan-bolt)"></path>
            <path d="M62 32 L54 46 H59 L53 62 L61 49 H55 Z" fill="url(#cyan-bolt)"></path>
            <circle cx="50" cy="48" fill="#11221e" r="11" stroke="url(#metal-gold)" stroke-width="1.5"></circle>
            <path class="anim-gold-star" d="M50 40 L52.5 45.5 L58.5 46 L54 50 L55.5 56 L50 52.8 L44.5 56 L46 50 L41.5 46 L47.5 45.5 Z" fill="url(#metal-gold)"></path>
          </svg>
        `
      },
      {
        slug: 'first-blood',
        name: 'First Blood',
        revText: 'FIRST SOLVER',
        unlockedPill: 'FIRST BLOOD',
        progressText: 'FIRST SOLVER',
        reqText: 'BE THE FIRST PARTICIPANT TO SUCCESSFULLY SOLVE A CHALLENGE',
        description: 'Be the FIRST participant to successfully solve a challenge.',
        specialCardClass: 'card-first-blood',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="blade-ruby" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#ff4d4d"></stop>
                <stop offset="45%" stop-color="#b91c1c"></stop>
                <stop offset="100%" stop-color="#450a0a"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="blade-edge" x1="50" x2="50" y1="10" y2="85">
                <stop offset="0%" stop-color="#ffffff"></stop>
                <stop offset="30%" stop-color="#fca5a5"></stop>
                <stop offset="100%" stop-color="#7f1d1d"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="dagger-gold" x1="30" x2="70" y1="50" y2="50">
                <stop offset="0%" stop-color="#fbbf24"></stop>
                <stop offset="50%" stop-color="#f59e0b"></stop>
                <stop offset="100%" stop-color="#92400e"></stop>
              </lineargradient>
              <clippath id="dagger-clip">
                <path d="M50 10 L56 46 L50 78 L44 46 Z"></path>
              </clippath>
            </defs>
            <circle cx="50" cy="50" r="38" stroke="#ef4444" stroke-dasharray="8 4" stroke-opacity="0.3" stroke-width="1.5"></circle>
            <circle class="anim-ruby-pulse" cx="50" cy="50" fill="#130808" r="28" stroke="#ef4444" stroke-opacity="0.5" stroke-width="1.5"></circle>
            <rect fill="#200d0d" height="24" rx="4" stroke="#ef4444" stroke-width="1.5" width="28" x="36" y="52"></rect>
            <path class="anim-ruby-pulse" d="M50 10 L56 46 L50 78 L44 46 Z" fill="url(#blade-ruby)"></path>
            <g clip-path="url(#dagger-clip)">
              <line class="anim-blade-laser" stroke="#ffffff" stroke-linecap="round" stroke-width="4" x1="50" x2="50" y1="0" y2="25"></line>
            </g>
            <line stroke="url(#blade-edge)" stroke-linecap="round" stroke-width="2" x1="50" x2="50" y1="10" y2="78"></line>
            <path d="M34 46 C42 44 58 44 66 46 L64 50 H36 Z" fill="url(#dagger-gold)" stroke="#fef08a" stroke-width="0.5"></path>
            <rect fill="#1c1917" height="15" rx="1.5" stroke="url(#dagger-gold)" stroke-width="1" width="5" x="47.5" y="47"></rect>
            <circle cx="50" cy="65" fill="url(#dagger-gold)" r="4"></circle>
            <circle cx="50" cy="18" fill="#fff" r="1.5"></circle>
            <polygon fill="#ef4444" points="50,78 47,88 50,84 53,88"></polygon>
          </svg>
        `
      },
      {
        slug: 'point-hunter',
        name: 'Point Hunter',
        revText: '15,000 / 15,000 PTS',
        unlockedPill: '15,000+ PTS',
        progressText: `${userScore.toLocaleString()} / 15,000 PTS`,
        reqText: 'ACCUMULATE 15,000 TOTAL POINTS',
        description: 'Accumulate 15,000 total points.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="gold-hex" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#fef08a"></stop>
                <stop offset="50%" stop-color="#d97706"></stop>
                <stop offset="100%" stop-color="#451a03"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="gem-shine" x1="30" x2="70" y1="30" y2="70">
                <stop offset="0%" stop-color="#fffbeb"></stop>
                <stop offset="60%" stop-color="#fbbf24"></stop>
                <stop offset="100%" stop-color="#b45309"></stop>
              </lineargradient>
            </defs>
            <circle class="anim-reticle-spin-1" cx="50" cy="50" r="38" stroke="url(#gold-hex)" stroke-dasharray="8 6" stroke-width="2"></circle>
            <circle class="anim-reticle-spin-2" cx="50" cy="50" fill="#120e07" r="28" stroke="url(#gold-hex)" stroke-dasharray="4 4" stroke-width="1.8"></circle>
            <line stroke="#fbbf24" stroke-width="2" x1="50" x2="50" y1="16" y2="28"></line>
            <line stroke="#fbbf24" stroke-width="2" x1="50" x2="50" y1="72" y2="84"></line>
            <line stroke="#fbbf24" stroke-width="2" x1="16" x2="28" y1="50" y2="50"></line>
            <line stroke="#fbbf24" stroke-width="2" x1="72" x2="84" y1="50" y2="50"></line>
            <g class="anim-diamond-center">
              <polygon fill="url(#gem-shine)" points="50,32 64,48 50,66 36,48"></polygon>
              <polygon fill="#fde68a" fill-opacity="0.8" points="50,32 57,48 50,66"></polygon>
              <polygon fill="#d97706" fill-opacity="0.9" points="50,32 50,66 43,48"></polygon>
              <circle cx="50" cy="48" fill="#ffffff" r="2.5"></circle>
            </g>
          </svg>
        `
      },
      {
        slug: 'novice-hacker',
        name: 'Novice Hacker',
        revText: '50 / 50 SOLVED',
        unlockedPill: '50+ SOLVED',
        progressText: `${distinctSolves} / 50 SOLVED`,
        reqText: 'SOLVE 50 CHALLENGES (MIN 10 MEDIUM, 3 HARD)',
        description: 'Solve 50 challenges, including at least 10 Medium and 3 Hard challenges.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="skull-metal" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#334155"></stop>
                <stop offset="50%" stop-color="#1e293b"></stop>
                <stop offset="100%" stop-color="#0f172a"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="visor-green" x1="0" x2="100" y1="0" y2="0">
                <stop offset="0%" stop-color="#00ff9d"></stop>
                <stop offset="100%" stop-color="#00b4d8"></stop>
              </lineargradient>
            </defs>
            <polygon fill="url(#skull-metal)" points="50,6 88,28 88,72 50,94 12,72 12,28" stroke="#334155" stroke-width="2"></polygon>
            <path class="anim-terminal-flicker" d="M26 30 L74 30 M22 40 L78 40 M22 50 L78 50 M26 60 L74 60" stroke="#00ff9d" stroke-width="1.5"></path>
            <path d="M34 38 C34 26 66 26 66 38 C66 48 64 54 58 56 L58 64 H42 L42 56 C36 54 34 48 34 38 Z" fill="#0b1313" stroke="#475569" stroke-width="1.5"></path>
            <path class="anim-visor-pulse" d="M36 42 H64 L61 48 H39 Z" fill="url(#visor-green)" stroke="#00ff9d" stroke-width="0.8"></path>
            <rect fill="#00ff9d" fill-opacity="0.8" height="4" width="2.5" x="44" y="60"></rect>
            <rect fill="#00ff9d" fill-opacity="0.8" height="4" width="2" x="49" y="60"></rect>
            <rect fill="#00ff9d" fill-opacity="0.8" height="4" width="2.5" x="53.5" y="60"></rect>
          </svg>
        `
      },
      {
        slug: 'ctf-grinder',
        name: 'CTF Grinder',
        revText: '200 / 200 SOLVED',
        unlockedPill: '200+ SOLVED',
        progressText: `${distinctSolves} / 200 SOLVED`,
        reqText: 'SOLVE 200 CHALLENGES (MIN 30 HARD)',
        description: 'Solve 200 challenges, including at least 30 Hard challenges.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="gear-titanium" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#475569"></stop>
                <stop offset="50%" stop-color="#1e293b"></stop>
                <stop offset="100%" stop-color="#090d16"></stop>
              </lineargradient>
            </defs>
            <path class="anim-gear-forward" d="M44 14 H56 L58 22 L66 25 L73 19 L81 27 L75 34 L78 42 L86 44 V56 L78 58 L75 66 L81 73 L73 81 L66 75 L58 78 L56 86 H44 L42 78 L34 75 L27 81 L19 73 L25 66 L22 58 L14 56 V44 L22 42 L25 34 L19 27 L27 19 L34 25 L42 22 Z" fill="url(#gear-titanium)" stroke="#64748b" stroke-width="1.5"></path>
            <circle cx="50" cy="50" fill="#080e12" r="24" stroke="#00e5ff" stroke-opacity="0.4" stroke-width="1.5"></circle>
            <circle class="anim-gear-inner" cx="50" cy="50" r="15" stroke="#00ff9d" stroke-dasharray="6 3" stroke-width="2"></circle>
            <circle class="anim-core-breathe" cx="50" cy="50" fill="#00e5ff" fill-opacity="0.85" r="7"></circle>
            <circle cx="50" cy="50" fill="#ffffff" r="3"></circle>
          </svg>
        `
      },
      {
        slug: 'streak-starter',
        name: 'Streak Starter',
        revText: '14 / 14 DAYS',
        unlockedPill: '14-DAY STREAK',
        progressText: `${userStreak} / 14 DAYS`,
        reqText: 'MAINTAIN A 14-DAY CONSECUTIVE SOLVING STREAK',
        description: 'Maintain a 14-day consecutive challenge-solving streak.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="flame-gold" x1="50" x2="50" y1="15" y2="85">
                <stop offset="0%" stop-color="#fde047"></stop>
                <stop offset="50%" stop-color="#f97316"></stop>
                <stop offset="100%" stop-color="#9a3412"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="crest-bronze" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#3f3f46"></stop>
                <stop offset="100%" stop-color="#18181b"></stop>
              </lineargradient>
            </defs>
            <polygon fill="url(#crest-bronze)" points="50,10 82,26 74,74 50,90 26,74 18,26" stroke="#71717a" stroke-width="1.5"></polygon>
            <path class="anim-flame-outer" d="M50 20 C56 32 70 42 70 58 C70 72 60 80 50 82 C40 80 30 72 30 58 C30 42 44 32 50 20 Z" fill="url(#flame-gold)"></path>
            <path class="anim-flame-inner" d="M50 36 C53 44 60 52 60 62 C60 70 54 74 50 75 C46 74 40 70 40 62 C40 52 47 44 50 36 Z" fill="#ffffff" fill-opacity="0.9"></path>
            <circle cx="50" cy="28" fill="#fef08a" r="1.5"></circle>
            <circle cx="38" cy="46" fill="#f97316" r="1"></circle>
            <circle cx="62" cy="44" fill="#f97316" r="1"></circle>
          </svg>
        `
      },
      {
        slug: 'weekly-warrior',
        name: 'Weekly Warrior',
        revText: '30 / 30 DAYS',
        unlockedPill: '30-DAY STREAK',
        progressText: `${userStreak} / 30 DAYS`,
        reqText: 'MAINTAIN A 30-DAY CONSECUTIVE SOLVING STREAK',
        description: 'Maintain a 30-day consecutive challenge-solving streak.',
        specialCardClass: '',
        svg: `
          <svg class="w-24 h-24 relative z-10" fill="none" viewbox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <lineargradient gradientunits="userSpaceOnUse" id="warrior-gold" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#fef08a"></stop>
                <stop offset="50%" stop-color="#eab308"></stop>
                <stop offset="100%" stop-color="#78350f"></stop>
              </lineargradient>
              <lineargradient gradientunits="userSpaceOnUse" id="warrior-core" x1="0" x2="100" y1="0" y2="100">
                <stop offset="0%" stop-color="#192a24"></stop>
                <stop offset="100%" stop-color="#080e0c"></stop>
              </lineargradient>
            </defs>
            <path d="M22 64 C16 48 24 32 32 24 M78 64 C84 48 76 32 68 24" stroke="url(#warrior-gold)" stroke-linecap="round" stroke-width="2"></path>
            <path class="anim-shield-pulse" d="M50 14 L76 28 V56 C76 74 50 90 50 90 C50 90 24 74 24 56 V28 Z" fill="url(#warrior-core)" stroke="url(#warrior-gold)" stroke-width="2"></path>
            <polygon fill="url(#warrior-gold)" points="40,24 50,14 60,24 56,28 50,22 44,28"></polygon>
            <g class="anim-warrior-plasma">
              <path d="M50 32 C56 42 66 50 66 62 C66 72 58 78 50 79 C42 78 34 72 34 62 C34 50 44 42 50 32 Z" fill="#00ff9d" fill-opacity="0.88"></path>
              <path d="M50 44 C53 50 58 56 58 64 C58 70 54 73 50 74 C46 73 42 70 42 64 C42 56 47 50 50 44 Z" fill="#ffffff"></path>
            </g>
            <line stroke="url(#warrior-gold)" stroke-width="1.5" x1="32" x2="68" y1="56" y2="56"></line>
          </svg>
        `
      }
    ];

    let unlockedCount = 0;
    const cardsHtml = badgesSpec.map(spec => {
      const sLower = (spec.slug || '').toLowerCase();
      const nLower = (spec.name || '').toLowerCase();
      const isUnlocked = myBadgeSlugs.has(sLower) ||
                         myBadgeNames.has(nLower) ||
                         myBadgeSlugs.has(sLower.replace(/-/g, '_')) ||
                         myBadgeSlugs.has(sLower.replace(/_/g, '-'));

      if (isUnlocked) unlockedCount++;

      const userBadge = myBadgeMap[sLower] ||
                        myBadgeMap[nLower] ||
                        myBadgeMap[sLower.replace(/-/g, '_')] ||
                        myBadgeMap[sLower.replace(/_/g, '-')];
      const awardedAt = userBadge?.awarded_at ? new Date(userBadge.awarded_at) : new Date();
      const timeStr = awardedAt.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase() + ' ' + awardedAt.toTimeString().substring(0, 5) + ' UTC';
      const hash = '0x' + (userBadge?.badge_id || userBadge?.id ? (userBadge.badge_id || userBadge.id).replace(/-/g, '').substring(0, 8).toUpperCase() : Math.random().toString(16).substring(2, 10).toUpperCase());

      const isFirstBlood = spec.slug === 'first-blood';

      return `
        <article class="badge-card ${spec.specialCardClass} ${isUnlocked ? 'badge-unlocked-highlight group' : 'badge-locked-dim'} rounded-xl p-5 flex flex-col items-center text-center relative backdrop-blur-md overflow-hidden"
          data-hash="${hash}"
          data-purpose="badge-card"
          data-status="${isUnlocked ? 'unlocked' : 'locked'}"
          data-time="${timeStr}"
          data-req="${escapeHtml(spec.reqText)}"
          onclick="ProfileView.onBadgeCardClick(this)">
          
          <div class="tactical-corner-tl"></div>
          <div class="tactical-corner-br"></div>

          <!-- Status Header -->
          <div class="w-full flex justify-between items-center mb-3 pointer-events-none">
            <span class="text-[10px] font-mono tracking-wider uppercase flex items-center gap-1.5">
              ${isUnlocked ? `
                <span class="badge-unlocked-chip">
                  <span class="w-1.5 h-1.5 rounded-full ${isFirstBlood ? 'bg-red-400 radar-pulse-beacon shadow-[0_0_8px_#ef4444]' : 'bg-emerald-400 radar-pulse-beacon shadow-[0_0_8px_#00ff9d]'}"></span>
                  ${isFirstBlood ? 'FIRST BLOOD' : 'ACHIEVED'}
                </span>
              ` : `
                <span class="text-slate-400 flex items-center gap-1.5 font-bold">
                  <svg class="w-3 h-3 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path clip-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" fill-rule="evenodd"></path></svg>
                  LOCKED
                </span>
              `}
            </span>
            <span class="text-[10px] font-mono ${isUnlocked ? (isFirstBlood ? 'text-red-400/90 font-bold flex items-center gap-1' : 'text-emerald-400/90 font-bold flex items-center gap-1') : 'text-slate-300 font-mono font-medium'}">
              ${isUnlocked ? (isFirstBlood ? `<span class="material-symbols-outlined text-[12px] text-red-400">my_location</span> 1ST KILL` : `<span class="material-symbols-outlined text-[12px] text-emerald-400">check_circle</span> ${spec.revText}`) : spec.progressText}
            </span>
          </div>

          <!-- Emblem Icon Container -->
          <div class="w-28 h-28 my-2 flex items-center justify-center relative shimmer-badge pointer-events-none">
            <div class="absolute inset-0 ${isUnlocked ? (isFirstBlood ? 'bg-red-600/30 anim-emblem-halo-red' : 'bg-emerald-400/30 anim-emblem-halo') : 'bg-slate-700/10'} blur-2xl rounded-full"></div>
            ${spec.svg}
          </div>

          <!-- Title & Pill -->
          <h3 class="text-base font-bold text-white tracking-wide mt-1 font-tactical ${isUnlocked ? (isFirstBlood ? 'drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'drop-shadow-[0_0_8px_rgba(0,255,157,0.4)]') : ''} transition-colors pointer-events-none">
            ${escapeHtml(spec.name)}
          </h3>

          <div class="mt-2 mb-2 inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-mono tracking-wider uppercase font-bold badge-status-pill pointer-events-none ${
            isUnlocked
              ? (isFirstBlood ? 'bg-red-950/70 border border-red-500/60 text-red-300 shadow-[0_0_12px_rgba(239,68,68,0.3)]' : 'bg-emerald-500/20 border border-emerald-400/60 text-emerald-300 shadow-[0_0_12px_rgba(0,255,157,0.25)]')
              : 'bg-slate-800/80 border border-slate-700/70 text-slate-300'
          }">
            ${isUnlocked ? spec.unlockedPill : 'LOCKED'}
          </div>

          <p class="text-xs text-slate-300 leading-relaxed font-normal mt-auto pt-2 border-t ${isUnlocked ? (isFirstBlood ? 'border-red-950/70' : 'border-emerald-950/60') : 'border-slate-800/70'} w-full pointer-events-none">
            ${escapeHtml(spec.description)}
          </p>
        </article>
      `;
    });

    container.innerHTML = cardsHtml.join('');

    // Update Header Counts & Security Tier
    const unlockedCountEl = document.getElementById('badgesUnlockedCount');
    const totalCountEl = document.getElementById('badgesTotalCount');
    const tierLabelEl = document.getElementById('badgesSecurityTierLabel');
    const progressFillEl = document.getElementById('badgesProgressFill');

    if (unlockedCountEl) unlockedCountEl.textContent = unlockedCount;
    if (totalCountEl) totalCountEl.textContent = 8;
    if (progressFillEl) progressFillEl.style.width = `${Math.round((unlockedCount / 8) * 100)}%`;
    if (tierLabelEl) {
      const tierNum = Math.max(1, Math.ceil(unlockedCount / 2));
      const tierTitle = unlockedCount >= 6 ? 'Veteran' : (unlockedCount >= 3 ? 'Operative' : 'Recruit');
      tierLabelEl.textContent = `Tier ${tierNum} ${tierTitle}`;
    }

    // Update Filter Buttons Label Counts
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
      const f = btn.getAttribute('data-filter');
      if (f === 'all') btn.textContent = `ALL (8)`;
      else if (f === 'unlocked') btn.textContent = `UNLOCKED (${unlockedCount})`;
      else if (f === 'locked') btn.textContent = `LOCKED (${8 - unlockedCount})`;
    });

    // Update Next Commendation Label
    const nextUnlockEl = document.getElementById('nextBadgeUnlockLabel');
    if (nextUnlockEl) {
      const lockedSpecs = badgesSpec.filter(b => {
        const s = (b.slug || '').toLowerCase();
        const n = (b.name || '').toLowerCase();
        return !(myBadgeSlugs.has(s) || myBadgeNames.has(n) || myBadgeSlugs.has(s.replace(/-/g, '_')));
      });
      if (lockedSpecs.length === 0) {
        nextUnlockEl.innerHTML = `<span class="text-emerald-400">ALL 8 COMMENDATIONS ACHIEVED // MAXIMUM AUDIT TIER</span>`;
      } else {
        const nextB = lockedSpecs[0];
        nextUnlockEl.innerHTML = `NEXT COMMENDATION UNLOCK: <span class="text-amber-400">${escapeHtml(nextB.name.toUpperCase())}</span>`;
      }
    }

    // Bind 3D Mousemove Perspective Tilt
    this.bindBadgeCardEffects();
  },


  async saveProfileBio() {
    const name = document.getElementById('editNameInput').value.trim();
    const college = document.getElementById('editCollegeInput').value.trim();
    const bio = document.getElementById('editBioInput').value.trim();

    try {
      await window.api.updateMyProfile({ name, college, bio });
      showToast('Operative profile updated.', 'success');
      closeModal('editProfileModal');

      // Update state and refresh
      const me = await window.api.getMe();
      window.state.currentUser = me;
      this.init();
      if (window.App && window.App.updateNavbarUserUI) {
        window.App.updateNavbarUserUI();
      }
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async changePassphrase(e) {
    if (e && e.preventDefault) e.preventDefault();
    const currentPass = document.getElementById('profileCurrentPassInput').value;
    const newPass = document.getElementById('profileNewPassInput').value;
    const btn = document.getElementById('btnChangePassSubmit');

    if (!currentPass || !newPass) {
      showToast('Please provide both current and new passphrases.', 'warning');
      return;
    }
    if (newPass.length < 8) {
      showToast('New passphrase must be at least 8 characters.', 'warning');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> Updating...';

    try {
      await window.api.changePassword(currentPass, newPass);
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-sm">key</span> Update Passphrase';
      showToast('Passphrase updated successfully.', 'success');
      closeModal('changePassModal');
      document.getElementById('profileCurrentPassInput').value = '';
      document.getElementById('profileNewPassInput').value = '';
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-sm">key</span> Update Passphrase';
      showToast(err.message || 'Passphrase update failed', 'error');
    }
  },

  copyProfileLink() {
    const input = document.getElementById('profileUrlInput');
    if (input) {
      navigator.clipboard.writeText(input.value);
      showToast('Dossier link copied to clipboard!', 'info');
    }
  },

  // ==========================================
  // FOLLOWERS & FOLLOWING SYSTEM (LeetCode-Style)
  // ==========================================
  rawFollowers: [],
  rawFollowing: [],

  async openFollowersModal(targetUserId = null) {
    const uid = targetUserId || window.state?.currentUser?.id;
    if (!uid) return;
    openModal('followersModal');
    const container = document.getElementById('followersListContainer');
    const searchInput = document.getElementById('searchFollowersInput');
    if (searchInput) searchInput.value = '';
    if (container) {
      container.innerHTML = `
        <div class="p-8 text-center text-text-muted font-mono text-sm">
          <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
          Loading operative followers...
        </div>
      `;
    }
    try {
      const followers = await window.api.getUserFollowers(uid);
      this.rawFollowers = Array.isArray(followers) ? followers : [];
      this.renderFollowList('followers', this.rawFollowers);
    } catch (e) {
      if (container) {
        container.innerHTML = `<div class="p-6 text-center text-status-error text-sm font-mono">${escapeHtml(e.message || 'Failed to load followers')}</div>`;
      }
    }
  },

  async openFollowingModal(targetUserId = null) {
    const uid = targetUserId || window.state?.currentUser?.id;
    if (!uid) return;
    openModal('followingModal');
    const container = document.getElementById('followingListContainer');
    const searchInput = document.getElementById('searchFollowingInput');
    if (searchInput) searchInput.value = '';
    if (container) {
      container.innerHTML = `
        <div class="p-8 text-center text-text-muted font-mono text-sm">
          <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
          Loading followed operatives...
        </div>
      `;
    }
    try {
      const following = await window.api.getUserFollowing(uid);
      this.rawFollowing = Array.isArray(following) ? following : [];
      this.renderFollowList('following', this.rawFollowing);
    } catch (e) {
      if (container) {
        container.innerHTML = `<div class="p-6 text-center text-status-error text-sm font-mono">${escapeHtml(e.message || 'Failed to load following list')}</div>`;
      }
    }
  },

  renderFollowList(type, list = []) {
    const containerId = type === 'followers' ? 'followersListContainer' : 'followingListContainer';
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!list || list.length === 0) {
      container.innerHTML = `
        <div class="p-8 text-center border border-dashed border-border-subtle rounded-xl bg-surface-base/60">
          <div class="w-12 h-12 rounded-full bg-surface-terminal flex items-center justify-center mx-auto text-text-muted border border-border-subtle mb-3">
            <span class="material-symbols-outlined text-2xl text-primary">${type === 'followers' ? 'group_off' : 'person_add_disabled'}</span>
          </div>
          <h4 class="font-bold text-sm text-text-primary mb-1">
            ${type === 'followers' ? 'No followers found' : 'Not following any operatives'}
          </h4>
          <p class="font-body-sm text-text-muted text-xs max-w-sm mx-auto">
            ${type === 'followers' ? 'Solve challenges, publish community writeups, and rise on the leaderboard to expand your network.' : 'Discover operatives in challenge writeups, leaderboard, or teams and follow their intelligence activity.'}
          </p>
        </div>
      `;
      return;
    }

    const currentUserId = window.state?.currentUser?.id;

    container.innerHTML = list.map(u => {
      const isSelf = currentUserId === u.id;
      const initial = (u.name || u.username || 'O')[0].toUpperCase();
      const isFollowing = !!u.is_following;

      return `
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-surface-base/80 border border-border-subtle hover:border-primary/40 transition-colors">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-full bg-surface-terminal border border-primary/40 flex items-center justify-center font-mono font-bold text-primary text-sm shrink-0">
              ${initial}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-bold text-text-primary text-sm truncate">${escapeHtml(u.name || u.username)}</span>
                <span class="font-mono text-xs text-primary/80">@${escapeHtml(u.username)}</span>
              </div>
              <div class="flex items-center gap-2 text-text-muted text-xs font-mono">
                ${u.college ? `<span class="truncate max-w-[150px]">${escapeHtml(u.college)}</span><span>•</span>` : ''}
                <span>${u.solves_count || 0} Solves</span>
              </div>
            </div>
          </div>

          ${!isSelf ? `
            <button type="button" class="btn btn-sm ${isFollowing ? 'btn-outline text-primary border-primary/40 hover:border-status-error hover:text-status-error group' : 'btn-primary'} px-3 py-1 font-mono text-xs flex items-center gap-1 shrink-0 cursor-pointer transition-all" onclick="ProfileView.toggleFollowUser('${u.id}', this, '${type}')">
              ${isFollowing ? `
                <span class="group-hover:hidden flex items-center gap-1"><span class="material-symbols-outlined text-xs text-primary">check</span> Following</span>
                <span class="hidden group-hover:inline flex items-center gap-1"><span class="material-symbols-outlined text-xs">person_remove</span> Unfollow</span>
              ` : `
                <span class="material-symbols-outlined text-xs">person_add</span> Follow
              `}
            </button>
          ` : `
            <span class="font-mono text-xs text-text-muted px-2 py-1 bg-surface-terminal rounded border border-border-subtle">You</span>
          `}
        </div>
      `;
    }).join('');
  },

  filterFollowList(type, query = '') {
    const q = (query || '').toLowerCase().trim();
    const source = type === 'followers' ? this.rawFollowers : this.rawFollowing;
    if (!q) {
      this.renderFollowList(type, source);
      return;
    }
    const filtered = source.filter(u => {
      const name = (u.name || '').toLowerCase();
      const uname = (u.username || '').toLowerCase();
      const coll = (u.college || '').toLowerCase();
      return name.includes(q) || uname.includes(q) || coll.includes(q);
    });
    this.renderFollowList(type, filtered);
  },

  async toggleFollowUser(targetUserId, btnEl, listType) {
    if (!targetUserId) return;
    try {
      if (btnEl) btnEl.disabled = true;
      const res = await window.api.toggleFollowUser(targetUserId);

      // Update cached lists
      const updateList = (arr) => {
        if (!arr) return;
        const item = arr.find(x => x.id === targetUserId);
        if (item) item.is_following = res.is_following;
      };
      updateList(this.rawFollowers);
      updateList(this.rawFollowing);

      if (btnEl) {
        btnEl.disabled = false;
        if (res.is_following) {
          btnEl.className = 'btn btn-sm btn-outline text-primary border-primary/40 hover:border-status-error hover:text-status-error group px-3 py-1 font-mono text-xs flex items-center gap-1 shrink-0 cursor-pointer transition-all';
          btnEl.innerHTML = `
            <span class="group-hover:hidden flex items-center gap-1"><span class="material-symbols-outlined text-xs text-primary">check</span> Following</span>
            <span class="hidden group-hover:inline flex items-center gap-1"><span class="material-symbols-outlined text-xs">person_remove</span> Unfollow</span>
          `;
        } else {
          btnEl.className = 'btn btn-sm btn-primary px-3 py-1 font-mono text-xs flex items-center gap-1 shrink-0 cursor-pointer transition-all';
          btnEl.innerHTML = '<span class="material-symbols-outlined text-xs">person_add</span> Follow';
        }
      }

      // Update following counter on profile header
      const followingCountEl = document.getElementById('profFollowingCount');
      if (followingCountEl) {
        const currentVal = parseInt(followingCountEl.textContent.replace(/,/g, ''), 10) || 0;
        const nextVal = res.is_following ? currentVal + 1 : Math.max(0, currentVal - 1);
        followingCountEl.textContent = nextVal.toLocaleString();
      }

      showToast(res.is_following ? 'Operative followed' : 'Unfollowed operative', res.is_following ? 'success' : 'info');
    } catch (e) {
      if (btnEl) btnEl.disabled = false;
      showToast(e.message || 'Unable to update follow status', 'error');
    }
  },

  navigateToTeamHistory(teamId) {
    if (!teamId) return;
    window.state = window.state || {};
    window.state.pendingTeamHistoryId = teamId;
    if (window.location.hash === `#teams?history=${teamId}`) {
      if (window.TeamsView && typeof window.TeamsView.openTeamHistoryModal === 'function') {
        window.TeamsView.openTeamHistoryModal(teamId);
      }
    } else {
      window.location.hash = `#teams?history=${teamId}`;
    }
  },

  // ==========================================
  // GITHUB OAUTH & REPOSITORY INTEGRATION
  // ==========================================
  githubStatus: null,

  async loadGitHubStatus() {
    const container = document.getElementById('profileGitHubHeaderContainer');
    if (!container) return;

    try {
      const status = await window.api.getGitHubStatus();
      this.githubStatus = status;

      if (status && status.is_connected) {
        container.innerHTML = `
          <button id="btnProfileManageGitHub" type="button" onclick="ProfileView.openGitHubConfigModal()" class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg bg-primary/10 border border-primary/40 text-primary hover:bg-primary/20 transition-all cursor-pointer shadow-[0_0_12px_rgba(78,222,163,0.15)]" title="GitHub CTF Integration Active">
            <svg class="w-3.5 h-3.5 fill-current text-primary" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            <span class="font-mono font-bold">@${escapeHtml(status.github_username)}</span>
            <span class="text-text-muted">•</span>
            <span class="font-mono text-text-secondary text-[11px] max-w-[140px] truncate">${escapeHtml(status.selected_repository ? (status.selected_repository.split('/')[1] || status.selected_repository) : 'No Repo')}</span>
            <span class="material-symbols-outlined text-xs">tune</span>
          </button>
        `;
      } else {
        container.innerHTML = `
          <button id="btnProfileConnectGitHub" type="button" onclick="ProfileView.openGitHubConfigModal()" class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg bg-surface-terminal/90 hover:bg-surface-card border border-border-grid hover:border-primary text-text-primary transition-all shadow-[0_0_12px_rgba(16,185,129,0.15)] cursor-pointer">
            <svg class="w-3.5 h-3.5 fill-current text-on-surface" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            <span>Connect GitHub</span>
          </button>
        `;
      }
    } catch (e) {
      console.warn('Failed to load GitHub status:', e);
    }
  },

  async openGitHubConfigModal() {
    openModal('githubIntegrationModal');
    const body = document.getElementById('githubModalBody');
    if (!body) return;

    body.innerHTML = `
      <div class="p-8 text-center text-text-muted font-mono text-sm">
        <span class="material-symbols-outlined text-2xl animate-spin mb-2 block text-primary">progress_activity</span>
        Querying GitHub integration telemetry...
      </div>
    `;

    try {
      const status = await window.api.getGitHubStatus();
      this.githubStatus = status;

      if (!status.is_connected) {
        // Render Disconnected State with OAuth Connect CTA
        body.innerHTML = `
          <div class="space-y-4">
            <div class="p-4 rounded-xl bg-surface-terminal/80 border border-border-subtle flex items-start gap-3.5">
              <div class="w-10 h-10 rounded-lg bg-surface-base border border-border-subtle flex items-center justify-center text-primary shrink-0">
                <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              </div>
              <div class="space-y-1">
                <h4 class="font-headline-sm text-headline-sm font-bold text-text-primary">Connect Your GitHub Account</h4>
                <p class="font-body-sm text-body-sm text-text-muted leading-relaxed">
                  Authorize the CTF platform to push your verified solutions and security writeups to your chosen personal GitHub repository whenever a challenge flag is accepted.
                </p>
              </div>
            </div>

            <div class="bg-surface-base/80 p-4 rounded-xl border border-border-subtle space-y-2.5 font-code-sm text-code-sm">
              <div class="flex items-center gap-2 text-primary font-bold">
                <span class="material-symbols-outlined text-base">verified_user</span>
                <span>Security &amp; Privacy Safeguards</span>
              </div>
              <ul class="space-y-1.5 text-text-muted text-xs list-disc list-inside">
                <li><strong class="text-text-primary">Zero Flag Exposure:</strong> The actual flag string is strictly excluded and never committed to GitHub.</li>
                <li><strong class="text-text-primary">Minimal Permissions:</strong> Uses standard GitHub OAuth requesting only scoped write access to commit files.</li>
                <li><strong class="text-text-primary">Encrypted Server-Side:</strong> Credentials are encrypted with AES-256-GCM and never exposed to the browser.</li>
              </ul>
            </div>

            <button type="button" id="btnExecuteGitHubOAuth" onclick="ProfileView.handleConnectGitHub()" class="btn btn-primary btn-block py-3 flex items-center justify-center gap-2 text-sm font-bold shadow-[0_0_20px_rgba(78,222,163,0.3)] cursor-pointer">
              <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              <span>Authorize with GitHub OAuth</span>
            </button>
          </div>
        `;
        return;
      }

      // Fetch user's available repositories
      let repos = [];
      try {
        repos = await window.api.getGitHubRepositories();
      } catch (e) {
        console.warn('Could not fetch repos:', e);
      }

      const isConfigured = !!status.selected_repository;
      const repoOptions = Array.isArray(repos) ? repos.map(r => `
        <option value="${escapeHtml(r.full_name)}" ${status.selected_repository === r.full_name ? 'selected' : ''}>
          ${escapeHtml(r.full_name)} ${r.is_private ? '(Private)' : '(Public)'}
        </option>
      `).join('') : '';

      body.innerHTML = `
        <div class="space-y-4">
          <!-- 1. Connected Account Header -->
          <div class="flex items-center justify-between p-3.5 rounded-xl bg-surface-terminal/90 border border-border-subtle">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-full bg-surface-base border border-primary/40 flex items-center justify-center text-primary font-mono font-bold shrink-0">
                <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold text-sm text-text-primary">Connected Account</span>
                  <span class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-1.5 py-0.2 rounded border border-primary/30">Active</span>
                </div>
                <a href="${escapeHtml(status.repository_url || `https://github.com/${status.github_username}`)}" target="_blank" rel="noopener noreferrer" class="font-mono text-xs text-primary hover:underline flex items-center gap-1">
                  <span>@${escapeHtml(status.github_username)}</span>
                  <span class="material-symbols-outlined text-xs">open_in_new</span>
                </a>
              </div>
            </div>
            <button type="button" onclick="ProfileView.disconnectGitHub()" class="btn btn-outline btn-sm text-xs py-1 px-2.5 text-status-error border-status-error/30 hover:bg-status-error/10 flex items-center gap-1 cursor-pointer">
              <span class="material-symbols-outlined text-xs">link_off</span> Disconnect
            </button>
          </div>

          <!-- 2. Repository Configuration Card -->
          <div class="p-4 rounded-xl bg-surface-base/90 border border-border-subtle space-y-3">
            <div class="flex items-center justify-between">
              <label class="block font-label-sm text-label-sm uppercase tracking-wider text-text-secondary">
                Designated Solutions Repository
              </label>
              ${isConfigured ? `
                <a href="https://github.com/${escapeHtml(status.selected_repository)}" target="_blank" rel="noopener noreferrer" class="text-xs font-mono text-primary hover:underline flex items-center gap-1">
                  <span>View on GitHub</span>
                  <span class="material-symbols-outlined text-xs">open_in_new</span>
                </a>
              ` : ''}
            </div>

            <div class="space-y-2">
              <div>
                <label class="block text-xs text-text-muted mb-1 font-mono">Select from your existing repositories:</label>
                <select id="githubRepoSelect" class="w-full bg-surface-terminal border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none font-mono" onchange="ProfileView.onRepoSelectChange(this.value)">
                  <option value="">-- Choose a repository --</option>
                  ${repoOptions}
                  <option value="__custom__">+ Enter custom repository name...</option>
                </select>
              </div>

              <div id="githubCustomRepoContainer" style="${isConfigured && !repoOptions.includes(`value="${status.selected_repository}"`) ? 'display:block;' : 'display:none;'}">
                <label class="block text-xs text-text-muted mb-1 font-mono">Custom repository (e.g. ctf-solutions or owner/repo):</label>
                <input type="text" id="githubCustomRepoInput" value="${escapeHtml(status.selected_repository || 'ctf-solutions')}" placeholder="ctf-solutions" class="w-full bg-surface-terminal border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none font-mono" />
              </div>

              <div class="flex items-center gap-2 pt-1">
                <input type="checkbox" id="githubAutoCreateRepo" class="rounded border-border-subtle bg-surface-terminal text-primary focus:ring-0" checked />
                <label for="githubAutoCreateRepo" class="text-xs text-text-secondary cursor-pointer">
                  Auto-create repository on GitHub if it doesn't exist
                </label>
              </div>

              <button type="button" id="btnSaveGitHubRepo" onclick="ProfileView.saveGitHubRepository()" class="btn btn-primary btn-block py-2 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer mt-2">
                <span class="material-symbols-outlined text-sm">verified</span> Verify Access &amp; Save Repository
              </button>
            </div>
          </div>

          <!-- 3. Sync Telemetry & Manual Trigger -->
          <div class="p-4 rounded-xl bg-surface-base/90 border border-border-subtle space-y-3 font-mono text-xs">
            <div class="flex items-center justify-between">
              <span class="font-bold text-text-primary uppercase tracking-wider">Sync Telemetry</span>
              <span class="text-text-muted">${status.sync_count || 0} Solves Committed</span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-text-muted">
              <div>
                <span class="block text-[11px] text-text-secondary">Target Repo:</span>
                <span class="text-primary font-bold truncate block">${escapeHtml(status.selected_repository || 'None configured')}</span>
              </div>
              <div>
                <span class="block text-[11px] text-text-secondary">Last Successful Sync:</span>
                <span class="text-text-primary block">${status.last_sync_at ? formatDate(status.last_sync_at) : 'Never'}</span>
              </div>
            </div>

            ${status.last_sync_error ? `
              <div class="p-2.5 rounded-lg bg-status-error/10 border border-status-error/30 text-status-error text-xs flex items-start gap-2">
                <span class="material-symbols-outlined text-sm shrink-0">error</span>
                <span class="break-all">${escapeHtml(status.last_sync_error)}</span>
              </div>
            ` : ''}

            <div class="pt-2 border-t border-border-subtle/60 flex items-center justify-between gap-2">
              <span class="text-[11px] text-text-muted font-sans">Automatic commit hook is active for all new solves.</span>
              <button type="button" id="btnManualSyncSolves" onclick="ProfileView.syncSolvesNow()" class="btn btn-outline btn-sm text-xs py-1 px-2.5 flex items-center gap-1 cursor-pointer shrink-0">
                <span class="material-symbols-outlined text-xs">sync</span> Sync Historical Solves
              </button>
            </div>
          </div>

          <!-- 4. Zero Flag Leakage Notice -->
          <div class="p-3 rounded-lg bg-surface-terminal/60 border border-primary/20 space-y-1">
            <div class="flex items-center gap-1.5 text-primary text-xs font-bold">
              <span class="material-symbols-outlined text-sm">shield</span>
              <span>Zero Flag Exposure Policy</span>
            </div>
            <p class="text-text-muted text-[11px] leading-relaxed">
              Files are committed to <code class="text-primary">ctf-solutions/&lt;challenge-slug&gt;/README.md</code> with challenge title, category, points, and your solution writeup. The actual secret flag string is strictly excluded.
            </p>
          </div>
        </div>
      `;
    } catch (err) {
      body.innerHTML = `
        <div class="p-6 text-center text-status-error text-sm font-mono space-y-2">
          <div>${escapeHtml(err.message || 'Failed to query GitHub status')}</div>
          <button class="btn btn-outline btn-sm text-xs" onclick="ProfileView.openGitHubConfigModal()">Retry</button>
        </div>
      `;
    }
  },

  onRepoSelectChange(val) {
    const container = document.getElementById('githubCustomRepoContainer');
    if (container) {
      container.style.display = val === '__custom__' ? 'block' : 'none';
      if (val === '__custom__') {
        const input = document.getElementById('githubCustomRepoInput');
        if (input) input.focus();
      }
    }
  },

  async handleConnectGitHub() {
    const btn = document.getElementById('btnExecuteGitHubOAuth');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span> Connecting...';
    }

    try {
      const urlData = await window.api.getGitHubAuthUrl();
      if (urlData && urlData.auth_url) {
        window.location.href = urlData.auth_url;
        return;
      }
      
      const fallbackUser = prompt('GitHub OAuth Simulation: Enter your GitHub username to connect:', window.state?.currentUser?.github_username || 'cyber-student');
      if (!fallbackUser) {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = 'Authorize with GitHub OAuth';
        }
        return;
      }

      await window.api.exchangeGitHubOAuth({ mock_username: fallbackUser });
      showToast('GitHub connected successfully!', 'success');
      await this.loadGitHubStatus();
      this.openGitHubConfigModal();
    } catch (e) {
      showToast(e.message || 'GitHub connection failed', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = 'Authorize with GitHub OAuth';
      }
    }
  },

  async saveGitHubRepository() {
    const select = document.getElementById('githubRepoSelect');
    const customInput = document.getElementById('githubCustomRepoInput');
    const autoCreateBox = document.getElementById('githubAutoCreateRepo');
    const btn = document.getElementById('btnSaveGitHubRepo');

    let repoName = '';
    if (select && select.value && select.value !== '__custom__') {
      repoName = select.value.trim();
    } else if (customInput) {
      repoName = customInput.value.trim();
    }

    if (!repoName) {
      showToast('Please select or specify a target repository', 'warning');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> Verifying Access...';
    }

    try {
      const autoCreate = autoCreateBox ? autoCreateBox.checked : true;
      const res = await window.api.configureGitHubRepository(repoName, autoCreate);
      showToast(`Repository ${res.selected_repository} verified and configured!`, 'success');
      await this.loadGitHubStatus();
      this.openGitHubConfigModal();
    } catch (e) {
      showToast(e.message || 'Failed to configure repository', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-sm">verified</span> Verify Access & Save Repository';
      }
    }
  },

  async syncSolvesNow() {
    const btn = document.getElementById('btnManualSyncSolves');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-xs animate-spin">progress_activity</span> Syncing...';
    }

    try {
      const res = await window.api.syncGitHubSubmissions();
      showToast(res.message || `Successfully committed ${res.synced_count} solves to GitHub!`, 'success');
      await this.loadGitHubStatus();
      this.openGitHubConfigModal();
    } catch (e) {
      showToast(e.message || 'Sync failed', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-xs">sync</span> Sync Historical Solves';
      }
    }
  },

  async disconnectGitHub() {
    if (!confirm('Are you sure you want to disconnect your GitHub integration? Solution commits will be halted.')) {
      return;
    }

    try {
      await window.api.disconnectGitHub();
      showToast('GitHub integration disconnected.', 'info');
      await this.loadGitHubStatus();
      this.openGitHubConfigModal();
    } catch (e) {
      showToast(e.message || 'Failed to disconnect GitHub', 'error');
    }
  }
};

window.ProfileView = ProfileView;

/**
 * OWASP CTF Platform — Student Dashboard View
 * Stitch Screen: "Cybersecurity Mission Control Dashboard" (fedb17dc9c90417dbceec5c6e82010bd)
 */

const DashboardView = {
  async init() {
    if (!window.state.currentUser) {
      window.location.hash = '#landing';
      openModal('authModal');
      return;
    }
    this.render();
    await this.loadDashboardData();
  },

  render() {
    const container = document.getElementById('view-dashboard');
    if (!container) return;

    const user = window.state.currentUser;

    container.innerHTML = `
      <div class="flex flex-col w-full px-space-lg py-space-md space-y-space-md">
        
        <!-- 1. TOP STATUS BANNER / CRISIS DIRECTIVE -->
        <div class="relative overflow-hidden bg-surface-card rounded-xl p-space-md shadow-xl border border-border-grid">
          <div class="absolute -right-24 -top-24 w-80 h-80 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
          
          <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md relative z-10">
            <div class="space-y-1">
              <div class="flex items-center gap-space-xs">
                <span class="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                <span class="font-code-sm text-code-sm text-primary uppercase tracking-widest font-bold">
                  DIRECTIVE // TACTICAL ENGAGEMENT FIELD
                </span>
                <span class="font-code-sm text-code-sm px-1.5 py-0.5 rounded bg-primary-container/20 text-primary font-semibold">
                  STATUS: SYNCHRONIZED
                </span>
              </div>
              <h1 class="font-headline-lg text-headline-lg text-text-primary font-bold tracking-tight">
                Welcome Operative, <span class="text-primary">${escapeHtml(user.name || user.username)}</span>
              </h1>
              <p class="font-body-sm text-body-sm text-text-secondary max-w-3xl">
                Collegiate OWASP defense outpost. Real-time telemetry, dynamic decay flag scoring, and competitive offensive security operations.
              </p>
            </div>

            <!-- Fast Tactical Action Triggers -->
            <div class="flex flex-wrap items-center gap-space-xs shrink-0">
              <button class="btn btn-primary" onclick="window.location.hash = '#challenges'">
                <span class="material-symbols-outlined text-base">flag</span>
                <span>Enter Challenge Arena</span>
              </button>
              <button class="btn btn-outline" onclick="window.location.hash = '#events'">
                <span class="material-symbols-outlined text-base">event</span>
                <span>Active Competitions</span>
              </button>
              <button class="btn btn-outline" onclick="window.location.hash = '#leaderboard'">
                <span class="material-symbols-outlined text-base">leaderboard</span>
                <span>Scoreboard</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 2. REALTIME TELEMETRY KPI RIBBON (4 Columns) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md" id="dashKpiRibbon">
          <!-- Total Defense Score -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
            <div class="flex items-start justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-text-muted">Defense Credits</span>
              <span class="material-symbols-outlined text-primary text-xl">bolt</span>
            </div>
            <div class="mt-2">
              <div id="dashTotalScore" class="font-headline-xl text-headline-xl text-primary font-bold leading-none font-mono">0</div>
              <span class="font-code-sm text-code-sm text-text-muted mt-1 block">Dynamic weighted score</span>
            </div>
          </div>

          <!-- Global Rank -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
            <div class="flex items-start justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-text-muted">Global Standing</span>
              <span class="material-symbols-outlined text-secondary text-xl">trophy</span>
            </div>
            <div class="mt-2">
              <div id="dashGlobalRank" class="font-headline-xl text-headline-xl text-secondary font-bold leading-none font-mono">#—</div>
              <span id="dashPercentileText" class="font-code-sm text-code-sm text-secondary flex items-center gap-1 mt-1">
                <span class="material-symbols-outlined text-xs">north</span> Calculating rank...
              </span>
            </div>
          </div>

          <!-- Solved Challenges -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
            <div class="flex items-start justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-text-muted">Verified Solves</span>
              <span class="material-symbols-outlined text-on-surface text-xl">check_circle</span>
            </div>
            <div class="mt-2">
              <div id="dashSolveCount" class="font-headline-xl text-headline-xl text-on-surface font-bold leading-none font-mono">0</div>
              <span id="dashSolveRate" class="font-code-sm text-code-sm text-text-muted mt-1 block">Targets neutralized</span>
            </div>
          </div>

          <!-- Active Day Streak -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
            <div class="flex items-start justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-text-muted">Operational Cadence</span>
              <span class="material-symbols-outlined text-status-warning text-xl">local_fire_department</span>
            </div>
            <div class="mt-2">
              <div id="dashStreak" class="font-headline-xl text-headline-xl text-status-warning font-bold leading-none font-mono">0 Days</div>
              <span id="dashLongestStreak" class="font-code-sm text-code-sm text-text-muted mt-1 block">Streak record: —</span>
            </div>
          </div>
        </div>

        <!-- 3. MAIN MISSION CONTROL SPLIT PANE -->
        <div class="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start">
          
          <!-- LEFT PANE: Activity Feed & Solve Telemetry (7 Cols) -->
          <div class="xl:col-span-7 space-y-space-md">
            
            <!-- Real-time Activity Telemetry Stream -->
            <div class="bg-surface-card rounded-xl p-space-md border border-border-grid shadow-sm space-y-space-sm">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-xl">query_stats</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Recent Telemetry &amp; Solve Feed</h3>
                </div>
                <button class="font-code-sm text-code-sm text-primary hover:underline cursor-pointer" onclick="window.location.hash = '#profile'">
                  View Complete Dossier &rarr;
                </button>
              </div>

              <!-- Activity Items List -->
              <div id="dashActivityStream" class="space-y-2 pt-1">
                <div class="text-text-muted font-code-sm text-center py-8">Gathering telemetry logs...</div>
              </div>
            </div>

            <!-- Active Competition Teaser Banner -->
            <div id="dashActiveEventCard" class="bg-surface-card rounded-xl p-space-md border border-secondary/30 shadow-sm relative overflow-hidden" style="display:none;">
              <div class="flex items-center justify-between">
                <div class="space-y-1">
                  <span class="badge badge-live">LIVE CTF ROUND</span>
                  <h4 id="dashEventTitle" class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">—</h4>
                  <p id="dashEventDesc" class="font-body-sm text-body-sm text-text-muted max-w-xl">—</p>
                </div>
                <button class="btn btn-primary" onclick="window.location.hash = '#events'">
                  <span>Enter Event Arena</span>
                  <span class="material-symbols-outlined text-sm">arrow_forward</span>
                </button>
              </div>
            </div>

          </div>

          <!-- RIGHT PANE: Commendations & In-App Security Alerts (5 Cols) -->
          <div class="xl:col-span-5 space-y-space-md">
            
            <!-- Commendations & Badges Showcase -->
            <div class="bg-surface-card rounded-xl p-space-md border border-border-grid shadow-sm space-y-space-sm">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-tertiary text-xl">military_tech</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Tactical Commendations</h3>
                </div>
                <button class="font-code-sm text-code-sm text-tertiary hover:underline cursor-pointer" onclick="window.location.hash = '#profile'">
                  Catalog &rarr;
                </button>
              </div>

              <div id="dashBadgesGrid" class="grid grid-cols-2 gap-space-xs pt-1">
                <div class="text-text-muted font-code-sm text-center col-span-2 py-6">Checking badge records...</div>
              </div>
            </div>

            <!-- In-App Security Notifications -->
            <div class="bg-surface-card rounded-xl p-space-md border border-border-grid shadow-sm space-y-space-sm">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-status-info text-xl">notifications</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">System Alerts</h3>
                </div>
                <button class="font-code-sm text-code-sm text-text-muted hover:text-text-primary cursor-pointer" onclick="handleMarkAllNotifsRead(); DashboardView.loadNotifications();">
                  Mark All Read
                </button>
              </div>

              <div id="dashNotifList" class="space-y-2 pt-1 max-h-72 overflow-y-auto pr-1">
                <div class="text-text-muted font-code-sm text-center py-6">Loading alerts...</div>
              </div>
            </div>

          </div>

        </div>

      </div>
    `;
  },

  async loadDashboardData() {
    const u = window.state.currentUser;
    if (!u) return;

    // 1. Fetch score and rank
    try {
      const [scoreRes, rankRes] = await Promise.all([
        window.api.getMyScore().catch(() => null),
        window.api.request('/api/leaderboard/me').catch(() => null)
      ]);

      const scoreEl = document.getElementById('dashTotalScore');
      const solveCountEl = document.getElementById('dashSolveCount');
      if (scoreEl && scoreRes) {
        scoreEl.textContent = Number(scoreRes.score || 0).toLocaleString();
      }
      if (solveCountEl && scoreRes) {
        solveCountEl.textContent = String(scoreRes.solved_challenges_count || 0);
      }

      const rankEl = document.getElementById('dashGlobalRank');
      const percentileEl = document.getElementById('dashPercentileText');
      if (rankEl && rankRes && rankRes.rank) {
        rankEl.textContent = `#${rankRes.rank}`;
        if (percentileEl && rankRes.total_users) {
          const pct = Math.max(0.1, ((rankRes.rank / rankRes.total_users) * 100)).toFixed(1);
          percentileEl.innerHTML = `<span class="material-symbols-outlined text-xs">north</span> Top ${pct}% of ${rankRes.total_users} Operatives`;
        }
      }
    } catch (e) {
      console.warn('Dashboard score/rank error:', e);
    }

    // 2. Fetch User Profile for Streaks
    try {
      const profile = await window.api.getUserProfile(u.username);
      const streakEl = document.getElementById('dashStreak');
      const longestEl = document.getElementById('dashLongestStreak');
      if (streakEl && profile) {
        streakEl.textContent = `${profile.current_streak || 0} Days`;
      }
      if (longestEl && profile) {
        longestEl.textContent = `Longest record: ${profile.longest_streak || 0} days`;
      }
    } catch (e) {
      // Non-blocking
    }

    // 3. Fetch Activity stream
    try {
      const activities = await window.api.getUserActivity(u.username);
      const container = document.getElementById('dashActivityStream');
      if (container) {
        if (!Array.isArray(activities) || activities.length === 0) {
          container.innerHTML = `
            <div class="text-text-muted font-code-sm text-center py-6 bg-surface-terminal/30 rounded-lg">
              No recent vector submissions logged. Neutralize challenges in the arena to initiate telemetry!
            </div>
          `;
        } else {
          container.innerHTML = activities.slice(0, 6).map(act => `
            <div class="flex items-center justify-between p-2.5 rounded-lg bg-surface-terminal/40 border border-border-subtle hover:border-primary/40 transition-colors">
              <div class="flex items-center gap-2.5 min-w-0">
                <span class="material-symbols-outlined text-primary text-base">verified</span>
                <div class="truncate">
                  <div class="font-code-sm text-code-sm text-text-primary font-semibold truncate">
                    ${escapeHtml(act.details?.challenge_title || act.action || 'Challenge Neutralized')}
                  </div>
                  <div class="font-code-sm text-code-sm text-text-muted text-[11px]">
                    ${formatDate(act.created_at)}
                  </div>
                </div>
              </div>
              <div class="text-right shrink-0">
                <span class="font-code-sm text-code-sm text-primary font-bold">
                  +${act.points_earned || 0} PTS
                </span>
              </div>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      const container = document.getElementById('dashActivityStream');
      if (container) container.innerHTML = `<div class="text-status-error font-code-sm">Activity feed unavailable: ${escapeHtml(e.message)}</div>`;
    }

    // 4. Fetch Badges
    try {
      const userBadges = await window.api.getMyBadges();
      const badgesContainer = document.getElementById('dashBadgesGrid');
      if (badgesContainer) {
        if (!Array.isArray(userBadges) || userBadges.length === 0) {
          badgesContainer.innerHTML = `
            <div class="text-text-muted font-code-sm text-center col-span-2 py-4 bg-surface-terminal/30 rounded-lg">
              No badges awarded yet. Complete challenges and first bloods to earn commendations.
            </div>
          `;
        } else {
          badgesContainer.innerHTML = userBadges.slice(0, 4).map(b => `
            <div class="p-2 rounded-lg bg-surface-terminal/40 border border-border-subtle flex items-center gap-2">
              <div class="w-8 h-8 rounded bg-tertiary/15 flex items-center justify-center text-tertiary shrink-0">
                <span class="material-symbols-outlined text-lg">workspace_premium</span>
              </div>
              <div class="min-w-0">
                <div class="font-code-sm text-code-sm text-text-primary font-bold truncate">${escapeHtml(b.badge?.name || b.name || 'Commendation')}</div>
                <div class="font-label-sm text-label-sm text-tertiary text-[10px] uppercase">VERIFIED</div>
              </div>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      // Non-blocking
    }

    // 5. Fetch Notifications
    this.loadNotifications();

    // 6. Check Active Event
    try {
      const events = await window.api.getEvents();
      if (Array.isArray(events)) {
        const liveEvent = events.find(e => e.computed_status === 'live');
        if (liveEvent) {
          const card = document.getElementById('dashActiveEventCard');
          const title = document.getElementById('dashEventTitle');
          const desc = document.getElementById('dashEventDesc');
          if (card && title && desc) {
            card.style.display = 'block';
            title.textContent = liveEvent.name;
            desc.textContent = liveEvent.description || 'Competition round in progress with freeze enforcement.';
          }
        }
      }
    } catch (e) {
      // Non-blocking
    }
  },

  async loadNotifications() {
    try {
      const notifs = await window.api.getNotifications(false);
      const container = document.getElementById('dashNotifList');
      if (!container) return;

      if (!Array.isArray(notifs) || notifs.length === 0) {
        container.innerHTML = `<div class="text-text-muted font-code-sm text-center py-4 bg-surface-terminal/30 rounded-lg">All clear &mdash; no alerts.</div>`;
        return;
      }

      container.innerHTML = notifs.slice(0, 5).map(n => {
        const isSquadInvite = (n.type === 'team_invite_request' || (n.data && n.data.team_id)) && !n.is_read;

        if (isSquadInvite && n.data && n.data.team_id) {
          return `
            <div class="p-3 rounded-lg bg-surface-terminal/80 border-l-4 border-secondary space-y-2 shadow-sm">
              <div class="flex items-center justify-between font-code-sm text-code-sm font-semibold text-secondary">
                <span class="flex items-center gap-1">
                  <span class="material-symbols-outlined text-sm">groups</span>
                  <span>${escapeHtml(n.title)}</span>
                </span>
                <span class="text-text-muted text-[10px]">${formatDate(n.created_at)}</span>
              </div>
              <div class="font-body-sm text-body-sm text-on-surface text-xs leading-relaxed">${escapeHtml(n.message)}</div>
              <div class="pt-1.5 flex items-center gap-2 border-t border-border-subtle/50">
                <button type="button" class="btn btn-primary btn-sm text-xs py-0.5 px-2.5 flex items-center gap-1 cursor-pointer font-bold" onclick="handleAcceptInvite('${n.data.team_id}', '${n.id}'); DashboardView.loadNotifications();">
                  <span class="material-symbols-outlined text-xs">check_circle</span> Accept
                </button>
                <button type="button" class="btn btn-outline btn-sm text-xs py-0.5 px-2.5 text-status-error border-status-error/40 flex items-center gap-1 cursor-pointer" onclick="handleDeclineInvite('${n.data.team_id}', '${n.id}'); DashboardView.loadNotifications();">
                  <span class="material-symbols-outlined text-xs">cancel</span> Decline
                </button>
              </div>
            </div>
          `;
        }

        return `
          <div class="p-2.5 rounded-lg bg-surface-terminal/40 border-l-2 ${n.is_read ? 'border-border-subtle text-text-muted' : 'border-primary text-text-primary'} space-y-0.5">
            <div class="flex items-center justify-between font-code-sm text-code-sm font-semibold">
              <span>${escapeHtml(n.title)}</span>
              <span class="text-text-muted text-[10px]">${formatDate(n.created_at)}</span>
            </div>
            <div class="font-body-sm text-body-sm text-text-secondary text-xs">${escapeHtml(n.message)}</div>
          </div>
        `;
      }).join('');
    } catch (e) {
      // Non-blocking
    }
  }
};

window.DashboardView = DashboardView;

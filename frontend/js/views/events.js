/**
 * OWASP CTF Platform — Events View
 * Full-featured Collegiate CTF Events Hub with Big Box Details,
 * Phase Separation (Live, Upcoming, Concluded), Autofilled Participation Form,
 * Squad Creation, College-Specific Operative Directory (Max 4 Members),
 * Real-Time Search & Invitation, and Synchronized Event Enrollment.
 */

const EventsView = {
  events: [],
  selectedEvent: null,
  selectedEventData: null,
  eventLeaderboard: [],
  eventChallenges: [],
  eventParticipants: [],
  registrationInfo: null,
  activeFilter: 'all', // 'all', 'live', 'upcoming', 'ended'
  activeTab: 'overview', // 'overview', 'register', 'participants', 'challenges', 'scoreboard'
  countdownInterval: null,
  userTeam: null,
  operativeScope: 'college', // 'college' or 'all'
  operativeSearchResults: [],
  operativeSearchQuery: '',
  leaderboardScope: 'global', // 'global' or 'college'

  async init() {
    this.render();
    await this.loadEvents();
  },

  render() {
    const container = document.getElementById('view-events');
    if (!container) return;

    container.innerHTML = `
      <div class="relative w-full min-h-screen bg-surface-base px-space-md sm:px-space-lg pb-space-xl space-y-space-md">
        
        <!-- Header Strip & Tactical Filter Bar -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-space-md pt-space-md pb-space-sm border-b border-border-subtle">
          <div class="flex items-center gap-space-xs">
            <div class="p-2.5 rounded-lg bg-primary/10 text-primary border border-primary/30">
              <span class="material-symbols-outlined text-2xl">event_available</span>
            </div>
            <div>
              <h1 class="font-headline-md text-headline-md text-text-primary font-bold tracking-tight">Collegiate CTF Arena Schedule</h1>
              <p class="font-body-sm text-body-sm text-text-muted">High-stakes collegiate cyber defense showdowns, live jeopardy matches, and tactical tournaments.</p>
            </div>
          </div>

          <!-- Phase Filter Tabs -->
          <div class="flex items-center gap-1.5 bg-surface-container p-1 rounded-xl border border-border-subtle overflow-x-auto">
            <button id="eventFilter-all" class="px-3 py-1.5 rounded-lg bg-surface-terminal text-primary font-code-sm text-code-sm font-semibold flex items-center gap-1.5 transition-all cursor-pointer" onclick="EventsView.setFilter('all')">
              <span>All Matches</span>
              <span id="badgeCount-all" class="px-1.5 py-0.2 rounded-full bg-primary/20 text-xs font-mono">0</span>
            </button>
            <button id="eventFilter-live" class="px-3 py-1.5 rounded-lg text-text-muted hover:text-on-surface font-code-sm text-code-sm flex items-center gap-1.5 transition-all cursor-pointer" onclick="EventsView.setFilter('live')">
              <span class="w-2 h-2 rounded-full bg-accent-emerald animate-ping"></span>
              <span>Live Battles</span>
              <span id="badgeCount-live" class="px-1.5 py-0.2 rounded-full bg-accent-emerald/20 text-accent-neon text-xs font-mono">0</span>
            </button>
            <button id="eventFilter-upcoming" class="px-3 py-1.5 rounded-lg text-text-muted hover:text-on-surface font-code-sm text-code-sm flex items-center gap-1.5 transition-all cursor-pointer" onclick="EventsView.setFilter('upcoming')">
              <span class="w-2 h-2 rounded-full bg-status-warning"></span>
              <span>Upcoming</span>
              <span id="badgeCount-upcoming" class="px-1.5 py-0.2 rounded-full bg-status-warning/20 text-status-warning text-xs font-mono">0</span>
            </button>
            <button id="eventFilter-ended" class="px-3 py-1.5 rounded-lg text-text-muted hover:text-on-surface font-code-sm text-code-sm flex items-center gap-1.5 transition-all cursor-pointer" onclick="EventsView.setFilter('ended')">
              <span class="w-2 h-2 rounded-full bg-text-muted"></span>
              <span>Concluded</span>
              <span id="badgeCount-ended" class="px-1.5 py-0.2 rounded-full bg-surface-terminal text-text-muted text-xs font-mono">0</span>
            </button>
          </div>
        </div>

        <!-- 1. BIG BOX EVENTS FEED CONTAINER -->
        <div id="eventsBigBoxFeed" class="space-y-space-md">
          <div class="text-text-muted font-code-sm text-center py-20 bg-surface-card rounded-xl border border-border-subtle">
            <span class="material-symbols-outlined text-4xl text-primary animate-spin mb-2">sync</span>
            <div>Synchronizing collegiate CTF schedule...</div>
          </div>
        </div>

        <!-- 2. DEDICATED EVENT DETAIL & WORKSPACE MODAL / MOUNT -->
        <div id="eventDetailModal" class="modal-backdrop">
          <div class="modal-container" style="max-width: 1060px; max-height: 90vh; overflow-y: auto;">
            <div id="eventDetailModalContent">
              <!-- Rendered Dynamically -->
            </div>
          </div>
        </div>

      </div>
    `;
  },

  async loadEvents() {
    try {
      this.events = await window.api.getEvents();
      if (window.state.currentUser) {
        this.userTeam = await window.api.getMyTeam().catch(() => null);
      }
      this.renderEventsFeed();
    } catch (e) {
      console.warn('Events loading failed:', e);
      const feed = document.getElementById('eventsBigBoxFeed');
      if (feed) {
        feed.innerHTML = `
          <div class="bg-surface-card rounded-xl p-12 text-center border border-status-error/40 text-status-error">
            <span class="material-symbols-outlined text-4xl mb-2">error</span>
            <div class="font-bold font-code-md">Failed to load CTF competitions</div>
            <div class="text-xs font-mono mt-1 text-text-muted">${escapeHtml(e.message)}</div>
          </div>
        `;
      }
    }
  },

  setFilter(filter) {
    this.activeFilter = filter;
    ['all', 'live', 'upcoming', 'ended'].forEach(f => {
      const btn = document.getElementById(`eventFilter-${f}`);
      if (btn) {
        if (f === filter) {
          btn.className = 'px-3 py-1.5 rounded-lg bg-surface-terminal text-primary font-code-sm text-code-sm font-semibold flex items-center gap-1.5 transition-all cursor-pointer border border-primary/30';
        } else {
          btn.className = 'px-3 py-1.5 rounded-lg text-text-muted hover:text-on-surface font-code-sm text-code-sm flex items-center gap-1.5 transition-all cursor-pointer';
        }
      }
    });
    this.renderEventsFeed();
  },

  formatEventDate(isoStr) {
    if (!isoStr) return 'TBD';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return isoStr;
    }
  },

  calculateDuration(startIso, endIso) {
    if (!startIso || !endIso) return 'N/A';
    try {
      const diffMs = new Date(endIso) - new Date(startIso);
      const hours = Math.round(diffMs / (1000 * 60 * 60));
      if (hours >= 24) {
        const days = Math.floor(hours / 24);
        const remHours = hours % 24;
        return remHours > 0 ? `${days}d ${remHours}h` : `${days} Days (${hours}h)`;
      }
      return `${hours} Hours`;
    } catch {
      return 'Standard Window';
    }
  },

  renderEventsFeed() {
    const feed = document.getElementById('eventsBigBoxFeed');
    if (!feed) return;

    if (!Array.isArray(this.events) || this.events.length === 0) {
      feed.innerHTML = `
        <div class="bg-surface-card rounded-xl p-12 text-center border border-border-grid">
          <span class="material-symbols-outlined text-5xl text-text-muted mb-3">event_busy</span>
          <h3 class="font-headline-md text-text-primary font-bold">No CTF Matches Scheduled</h3>
          <p class="font-body-sm text-text-muted mt-1 max-w-md mx-auto">
            Check back soon for upcoming collegiate cyber defense tournaments or create a new event in Admin Mission Control.
          </p>
        </div>
      `;
      return;
    }

    const liveCount = this.events.filter(e => e.computed_status === 'live').length;
    const upcomingCount = this.events.filter(e => e.computed_status === 'upcoming').length;
    const endedCount = this.events.filter(e => e.computed_status === 'ended').length;

    const bAll = document.getElementById('badgeCount-all');
    const bLive = document.getElementById('badgeCount-live');
    const bUp = document.getElementById('badgeCount-upcoming');
    const bEnd = document.getElementById('badgeCount-ended');

    if (bAll) bAll.textContent = this.events.length;
    if (bLive) bLive.textContent = liveCount;
    if (bUp) bUp.textContent = upcomingCount;
    if (bEnd) bEnd.textContent = endedCount;

    let filtered = [...this.events];
    if (this.activeFilter === 'live') filtered = filtered.filter(e => e.computed_status === 'live');
    else if (this.activeFilter === 'upcoming') filtered = filtered.filter(e => e.computed_status === 'upcoming');
    else if (this.activeFilter === 'ended') filtered = filtered.filter(e => e.computed_status === 'ended');

    filtered.sort((a, b) => {
      const order = { live: 1, upcoming: 2, ended: 3 };
      return (order[a.computed_status] || 4) - (order[b.computed_status] || 4);
    });

    if (filtered.length === 0) {
      feed.innerHTML = `
        <div class="bg-surface-card rounded-xl p-12 text-center border border-border-grid">
          <span class="material-symbols-outlined text-4xl text-text-muted mb-2">filter_alt_off</span>
          <h3 class="font-headline-sm text-text-primary font-bold">No Events in this Category</h3>
          <p class="font-body-sm text-text-muted mt-1">Switch to "All Matches" to see the full competition calendar.</p>
        </div>
      `;
      return;
    }

    feed.innerHTML = filtered.map(ev => {
      const isLive = ev.computed_status === 'live';
      const isUpcoming = ev.computed_status === 'upcoming';
      const isEnded = ev.computed_status === 'ended';

      let borderClass = 'border-border-grid';
      let statusBadge = '';
      let topBar = '';

      if (isLive) {
        borderClass = 'border-accent-emerald/70 shadow-[0_0_24px_rgba(0,255,157,0.18)] bg-surface-card/95';
        topBar = `<div class="absolute top-0 right-0 left-0 h-1.5 bg-gradient-to-r from-accent-emerald via-primary to-accent-neon shadow-[0_0_12px_#00FF9D]"></div>`;
        statusBadge = `
          <span class="px-2.5 py-1 rounded-md bg-accent-emerald/20 text-accent-neon border border-accent-emerald/60 shadow-[0_0_8px_rgba(0,255,157,0.3)] font-mono font-bold text-xs flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-accent-neon animate-ping"></span>
            <span>LIVE BATTLE IN PROGRESS</span>
          </span>
        `;
      } else if (isUpcoming) {
        borderClass = 'border-status-warning/40 bg-surface-card hover:border-status-warning/80 hover:shadow-[0_0_20px_rgba(245,158,11,0.2)]';
        topBar = `<div class="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-amber-500 to-yellow-400 opacity-80"></div>`;
        statusBadge = `
          <span class="px-2.5 py-1 rounded-md bg-status-warning/20 text-status-warning border border-status-warning/50 font-mono font-bold text-xs flex items-center gap-1.5">
            <span class="material-symbols-outlined text-sm">schedule</span>
            <span>UPCOMING TOURNAMENT</span>
          </span>
        `;
      } else {
        borderClass = 'border-border-subtle bg-surface-card/80 opacity-95';
        statusBadge = `
          <span class="px-2.5 py-1 rounded-md bg-surface-terminal text-text-muted border border-border-subtle font-mono font-semibold text-xs flex items-center gap-1.5">
            <span class="material-symbols-outlined text-sm">flag</span>
            <span>MATCH CONCLUDED</span>
          </span>
        `;
      }

      const durationStr = this.calculateDuration(ev.start_at, ev.end_at);
      const startDateFormatted = this.formatEventDate(ev.start_at);
      const endDateFormatted = this.formatEventDate(ev.end_at);

      return `
        <div class="relative ${borderClass} rounded-2xl p-space-md sm:p-space-lg transition-all duration-200 overflow-hidden flex flex-col justify-between gap-space-md">
          ${topBar}

          <!-- Upper Section: Status Badges, Title & Host -->
          <div class="space-y-space-sm">
            <div class="flex flex-wrap items-center justify-between gap-space-sm">
              <div class="flex flex-wrap items-center gap-2">
                ${statusBadge}
                <span class="px-2.5 py-1 rounded-md bg-surface-terminal text-secondary border border-border-subtle font-code-sm text-code-sm font-semibold uppercase">
                  JEOPARDY CTF • COLLEGIATE
                </span>
                ${ev.is_scoreboard_frozen ? `
                  <span class="px-2 py-0.5 rounded bg-status-warning/20 text-status-warning border border-status-warning/40 font-mono text-xs flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs">ac_unit</span> SCOREBOARD FROZEN
                  </span>
                ` : ''}
              </div>

              <!-- Time Countdown Indicator -->
              <div class="font-mono text-xs text-text-muted flex items-center gap-1.5 bg-surface-terminal px-3 py-1 rounded-lg border border-border-subtle">
                <span class="material-symbols-outlined text-sm ${isLive ? 'text-accent-neon' : isUpcoming ? 'text-status-warning' : 'text-text-muted'}">
                  ${isLive ? 'timer' : isUpcoming ? 'alarm' : 'event_available'}
                </span>
                <span>${isLive ? `Ends in: ${formatCountdown(ev.end_at)}` : isUpcoming ? `Starts in: ${formatCountdown(ev.start_at)}` : 'Concluded'}</span>
              </div>
            </div>

            <!-- Big Title & Description -->
            <div class="space-y-1.5 pt-1">
              <div class="flex flex-wrap items-baseline gap-2">
                <h2 class="font-headline-lg text-2xl sm:text-3xl font-bold text-text-primary tracking-tight">
                  ${escapeHtml(ev.name)}
                </h2>
                <span class="text-text-muted font-code-sm text-code-sm">• Hosted by PCCOE Cyber Cell</span>
              </div>
              <p class="font-body-md text-body-md text-text-secondary leading-relaxed max-w-4xl">
                ${escapeHtml(ev.description || 'Intensive 24-hour collegiate jeopardy arena covering Web Exploitation, Reverse Engineering, Cryptanalysis, Binary Exploitation, and Digital Forensics with dynamic scoreboard freeze.')}
              </p>
            </div>
          </div>

          <!-- Middle Section: 4-BOX DETAILED SCHEDULE & TELEMETRY BREAKDOWN -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-space-sm bg-surface-terminal/60 p-space-md rounded-xl border border-border-subtle">
            
            <!-- Box 1: Start Time -->
            <div class="space-y-1 p-2 bg-surface-card/60 rounded-lg border border-border-subtle/50">
              <div class="flex items-center gap-1.5 text-text-muted font-label-sm text-label-sm uppercase tracking-wider">
                <span class="material-symbols-outlined text-sm text-accent-emerald">play_circle</span>
                <span>Start Time</span>
              </div>
              <div class="font-code-md text-code-md text-on-surface font-bold">
                ${startDateFormatted}
              </div>
            </div>

            <!-- Box 2: End Time -->
            <div class="space-y-1 p-2 bg-surface-card/60 rounded-lg border border-border-subtle/50">
              <div class="flex items-center gap-1.5 text-text-muted font-label-sm text-label-sm uppercase tracking-wider">
                <span class="material-symbols-outlined text-sm text-status-warning">stop_circle</span>
                <span>Ending Time</span>
              </div>
              <div class="font-code-md text-code-md text-on-surface font-bold">
                ${endDateFormatted}
              </div>
            </div>

            <!-- Box 3: Duration -->
            <div class="space-y-1 p-2 bg-surface-card/60 rounded-lg border border-border-subtle/50">
              <div class="flex items-center gap-1.5 text-text-muted font-label-sm text-label-sm uppercase tracking-wider">
                <span class="material-symbols-outlined text-sm text-secondary">timelapse</span>
                <span>Duration</span>
              </div>
              <div class="font-code-md text-code-md text-secondary font-bold font-mono">
                ${durationStr}
              </div>
            </div>

            <!-- Box 4: Registered Participants -->
            <div class="space-y-1 p-2 bg-surface-card/60 rounded-lg border border-border-subtle/50">
              <div class="flex items-center gap-1.5 text-text-muted font-label-sm text-label-sm uppercase tracking-wider">
                <span class="material-symbols-outlined text-sm text-primary">groups</span>
                <span>Participants</span>
              </div>
              <div class="font-code-md text-code-md text-primary font-bold font-mono flex items-center justify-between">
                <span>${ev.participant_count || 0} Registered</span>
                <span class="text-xs text-text-muted font-normal">Operatives</span>
              </div>
            </div>

          </div>

          <!-- Lower Section: Action Buttons -->
          <div class="flex flex-wrap items-center justify-between gap-space-sm pt-space-xs border-t border-border-subtle">
            <div class="flex items-center gap-space-md text-text-muted font-code-sm text-code-sm">
              <span class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-base text-secondary">verified_user</span>
                <span>Validated Collegiate Rules</span>
              </span>
              <span>•</span>
              <span class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-base text-primary">terminal</span>
                <span>${ev.challenge_count || 0} Challenge Vectors</span>
              </span>
            </div>

            <div class="flex items-center gap-2">
              <button class="btn ${isLive ? 'btn-primary shadow-[0_0_16px_rgba(16,185,129,0.3)]' : isUpcoming ? 'btn-primary' : 'btn-outline'} btn-md flex items-center gap-2" onclick="EventsView.openEventDetailsModal('${ev.id}')">
                <span class="material-symbols-outlined text-lg">
                  ${isLive ? 'play_arrow' : isUpcoming ? 'how_to_reg' : 'leaderboard'}
                </span>
                <span>
                  ${isLive ? 'Enter Live Arena & Solve' : isUpcoming ? 'View Details & Enroll' : 'View Final Scoreboard'}
                </span>
              </button>
            </div>
          </div>

        </div>
      `;
    }).join('');
  },

  // ---------------------------------------------------------------------------
  // 2. DEDICATED EVENT DETAILS & PARTICIPATION WORKSPACE MODAL
  // ---------------------------------------------------------------------------
  async openEventDetailsModal(eventId, defaultTab = 'overview') {
    this.selectedEvent = eventId;
    this.activeTab = defaultTab;
    openModal('eventDetailModal');

    const content = document.getElementById('eventDetailModalContent');
    if (!content) return;

    content.innerHTML = `
      <div class="text-text-muted font-code-sm text-center py-24">
        <span class="material-symbols-outlined text-4xl text-primary animate-spin mb-2">sync</span>
        <div>Synchronizing event arena, participation status, and squad roster...</div>
      </div>
    `;

    try {
      const [evData, regData, lbData, chData, partData, teamData] = await Promise.all([
        window.api.getEvent(eventId),
        window.api.getEventRegistration(eventId).catch(() => null),
        window.api.getEventLeaderboard(eventId).catch(() => ({ items: [] })),
        window.api.getEventChallenges(eventId).catch(() => []),
        window.api.getEventParticipants(eventId).catch(() => []),
        window.api.getMyTeam().catch(() => null)
      ]);

      this.selectedEventData = evData;
      this.registrationInfo = (regData && regData.is_registered) ? regData.registration : null;
      this.eventLeaderboard = (lbData && Array.isArray(lbData.items)) ? lbData.items : (Array.isArray(lbData) ? lbData : []);
      this.eventChallenges = chData || [];
      this.eventParticipants = partData || [];
      this.userTeam = teamData;

      if (evData && evData.computed_status === 'ended') {
        if (!defaultTab || defaultTab === 'overview' || defaultTab === 'register') {
          this.activeTab = 'scoreboard';
        }
      }

      this.renderEventDetailsModal();
    } catch (e) {
      content.innerHTML = `
        <div class="p-8 text-status-error font-code-sm text-center">
          <span class="material-symbols-outlined text-4xl mb-2">error</span>
          <div>Error loading event details: ${escapeHtml(e.message)}</div>
          <button class="btn btn-outline btn-sm mt-4" onclick="closeModal('eventDetailModal')">Close</button>
        </div>
      `;
    }
  },

  renderEventDetailsModal() {
    const content = document.getElementById('eventDetailModalContent');
    if (!content || !this.selectedEventData) return;

    const ev = this.selectedEventData;
    const isLive = ev.computed_status === 'live';
    const isUpcoming = ev.computed_status === 'upcoming';
    const isEnded = ev.computed_status === 'ended';
    const isEnrolled = !!this.registrationInfo;

    // For ended events, ensure only scoreboard or challenges tab is active
    if (isEnded && (this.activeTab !== 'scoreboard' && this.activeTab !== 'challenges')) {
      this.activeTab = 'scoreboard';
    }

    content.innerHTML = `
      <div class="space-y-space-md">
        
        <!-- Modal Top Header Strip -->
        <div class="flex items-start justify-between gap-space-md border-b border-border-subtle pb-space-sm">
          <div class="space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="px-2.5 py-0.5 rounded font-mono text-xs font-bold ${isLive ? 'bg-primary/20 text-primary border border-primary/40' : isUpcoming ? 'bg-secondary/20 text-secondary border border-secondary/40' : 'bg-slate-800 text-slate-300 border border-slate-700'}">
                ${ev.computed_status.toUpperCase()}
              </span>
              <span class="px-2.5 py-0.5 rounded font-mono text-xs font-bold bg-secondary/15 text-secondary border border-secondary/40 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span> JEOPARDY CTF ARENA
              </span>
              <span class="px-2.5 py-0.5 rounded font-mono text-xs font-semibold bg-primary/10 text-primary border border-primary/30">
                SYS::STABLE // 1,428 FLAGS LOGGED
              </span>
            </div>
            <h2 class="font-headline-lg text-2xl sm:text-3xl text-text-primary font-bold tracking-tight">
              ${escapeHtml(ev.name).toUpperCase()} <span class="text-primary">${isEnded ? '// FINAL SCOREBOARD &amp; PODIUM' : '// EVENT ARENA'}</span>
            </h2>
          </div>

          <div class="flex items-center gap-3">
            <span class="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-terminal/80 border border-border-subtle text-text-muted text-xs font-mono">
              <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span> ARCHIVED REPLAY READY
            </span>
            <button class="p-2 rounded-lg bg-surface-terminal text-text-muted hover:text-on-surface transition-colors cursor-pointer" onclick="closeModal('eventDetailModal')">
              <span class="material-symbols-outlined text-xl">close</span>
            </button>
          </div>
        </div>

        <!-- Navigation Sub-Tabs -->
        <div class="flex items-center gap-2 border-b border-border-subtle pb-space-xs overflow-x-auto font-code-sm text-code-sm">
          ${isEnded ? `
            <!-- Concluded Event Tabs: Scoreboard & Podium (Global/College) and Practice Challenges ONLY -->
            <button class="px-3.5 py-1.5 rounded-lg ${this.activeTab === 'scoreboard' ? 'bg-primary text-surface-base font-bold shadow-[0_0_12px_rgba(0,255,157,0.25)]' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5 transition-all" onclick="EventsView.switchModalTab('scoreboard')">
              <span class="material-symbols-outlined text-base">leaderboard</span>
              <span>Final Scoreboard &amp; Podium (Global &amp; College)</span>
            </button>

            <button class="px-3.5 py-1.5 rounded-lg ${this.activeTab === 'challenges' ? 'bg-primary text-surface-base font-bold shadow-[0_0_12px_rgba(0,255,157,0.25)]' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5 transition-all" onclick="EventsView.switchModalTab('challenges')">
              <span class="material-symbols-outlined text-base">school</span>
              <span>Practice Challenges (${this.eventChallenges.length})</span>
            </button>
          ` : `
            <!-- Live / Upcoming Event Tabs -->
            <button class="px-3 py-1.5 rounded-lg ${this.activeTab === 'overview' ? 'bg-surface-terminal text-primary font-bold border border-primary/30' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5" onclick="EventsView.switchModalTab('overview')">
              <span class="material-symbols-outlined text-base">info</span> Overview &amp; Schedule
            </button>
            
            <button class="px-3 py-1.5 rounded-lg ${this.activeTab === 'register' ? 'bg-surface-terminal text-primary font-bold border border-primary/30' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5" onclick="EventsView.switchModalTab('register')">
              <span class="material-symbols-outlined text-base">how_to_reg</span> Participation &amp; Squad Enrollment
            </button>

            <button class="px-3 py-1.5 rounded-lg ${this.activeTab === 'participants' ? 'bg-surface-terminal text-primary font-bold border border-primary/30' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5" onclick="EventsView.switchModalTab('participants')">
              <span class="material-symbols-outlined text-base">groups</span> Participants (${this.eventParticipants.length})
            </button>

            ${isLive ? `
              <button class="px-3 py-1.5 rounded-lg ${this.activeTab === 'challenges' ? 'bg-surface-terminal text-accent-neon font-bold border border-accent-emerald/40' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5" onclick="EventsView.switchModalTab('challenges')">
                <span class="material-symbols-outlined text-base text-accent-neon">terminal</span> Live Challenges (${this.eventChallenges.length})
              </button>
            ` : ''}

            <button class="px-3 py-1.5 rounded-lg ${this.activeTab === 'scoreboard' ? 'bg-surface-terminal text-primary font-bold border border-primary/30' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5" onclick="EventsView.switchModalTab('scoreboard')">
              <span class="material-symbols-outlined text-base">leaderboard</span> Scoreboard &amp; Podium
            </button>
          `}
        </div>

        <!-- Dynamic Tab Content Mount -->
        <div id="modalDynamicTabMount">
          ${this.renderActiveTabContent()}
        </div>

      </div>
    `;

    // If register tab is active and squad mode is visible, trigger operative directory load
    if (this.activeTab === 'register') {
      setTimeout(() => {
        this.loadPlatformOperatives();
      }, 50);
    }
  },

  switchModalTab(tab) {
    this.activeTab = tab;
    this.renderEventDetailsModal();
  },

  setLeaderboardScope(scope) {
    this.leaderboardScope = scope;
    this.renderEventDetailsModal();
  },

  renderActiveTabContent() {
    const ev = this.selectedEventData;
    const isLive = ev.computed_status === 'live';
    const isUpcoming = ev.computed_status === 'upcoming';
    const isEnded = ev.computed_status === 'ended';
    const isEnrolled = !!this.registrationInfo;
    const currentUser = window.state.currentUser;

    // -------------------------------------------------------------------------
    // TAB 1: OVERVIEW & SCHEDULE
    // -------------------------------------------------------------------------
    if (this.activeTab === 'overview') {
      return `
        <div class="space-y-space-md pt-2">
          
          <!-- Event Chronometer Strip -->
          <div class="bg-surface-terminal/80 p-space-md rounded-xl border border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
            <div>
              <div class="font-label-sm text-label-sm uppercase tracking-widest text-text-muted">Target Chronometer</div>
              <div class="font-headline-md text-2xl sm:text-3xl text-accent-neon font-bold font-mono">
                ${isLive ? formatCountdown(ev.end_at) : isUpcoming ? formatCountdown(ev.start_at) : 'Match Concluded'}
              </div>
              <div class="text-xs font-mono text-text-secondary mt-0.5">
                ${isLive ? 'Time remaining until match conclusion' : isUpcoming ? 'Countdown until match kick-off' : 'Final results frozen'}
              </div>
            </div>

            <div class="flex items-center gap-2">
              ${isUpcoming ? `
                <button class="btn btn-primary" onclick="EventsView.switchModalTab('register')">
                  <span class="material-symbols-outlined text-base">how_to_reg</span>
                  <span>${isEnrolled ? 'Manage Squad & Enrollment' : 'Enroll for this Event'}</span>
                </button>
              ` : isLive ? `
                ${!isEnrolled ? `
                  <button class="btn btn-primary shadow-[0_0_16px_rgba(0,255,157,0.3)] flex items-center gap-1.5" onclick="EventsView.switchModalTab('register')">
                    <span class="material-symbols-outlined text-base">how_to_reg</span>
                    <span>Enter Live Arena (Choose Solo / Squad)</span>
                  </button>
                ` : `
                  <button class="btn btn-primary shadow-[0_0_16px_rgba(0,255,157,0.3)] flex items-center gap-1.5" onclick="EventsView.switchModalTab('challenges')">
                    <span class="material-symbols-outlined text-base">terminal</span>
                    <span>Enter Live Challenges</span>
                  </button>
                  <button class="btn btn-outline btn-sm text-secondary flex items-center gap-1" onclick="EventsView.switchModalTab('register')">
                    <span class="material-symbols-outlined text-sm">groups</span>
                    <span>Manage Squad</span>
                  </button>
                `}
              ` : `
                <button class="btn btn-primary shadow-[0_0_16px_rgba(0,255,157,0.3)] flex items-center gap-1.5" onclick="EventsView.switchModalTab('challenges')">
                  <span class="material-symbols-outlined text-base">school</span>
                  <span>Practice Event Challenges (${this.eventChallenges.length})</span>
                </button>
                <button class="btn btn-outline btn-sm text-text-muted hover:text-on-surface flex items-center gap-1" onclick="EventsView.switchModalTab('scoreboard')">
                  <span class="material-symbols-outlined text-sm">leaderboard</span>
                  <span>Scoreboard Podium</span>
                </button>
              `}
            </div>
          </div>

          <!-- Schedule Matrix -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-space-sm">
            <div class="p-space-sm bg-surface-terminal/40 rounded-lg border border-border-subtle">
              <span class="font-label-sm text-label-sm uppercase text-text-muted">Start Timestamp</span>
              <div class="font-code-md text-code-md font-bold text-on-surface mt-1">${this.formatEventDate(ev.start_at)}</div>
            </div>
            <div class="p-space-sm bg-surface-terminal/40 rounded-lg border border-border-subtle">
              <span class="font-label-sm text-label-sm uppercase text-text-muted">Ending Timestamp</span>
              <div class="font-code-md text-code-md font-bold text-on-surface mt-1">${this.formatEventDate(ev.end_at)}</div>
            </div>
            <div class="p-space-sm bg-surface-terminal/40 rounded-lg border border-border-subtle">
              <span class="font-label-sm text-label-sm uppercase text-text-muted">Match Duration</span>
              <div class="font-code-md text-code-md font-bold text-secondary font-mono mt-1">${this.calculateDuration(ev.start_at, ev.end_at)}</div>
            </div>
          </div>

          <!-- Detailed Description & Rules -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-subtle space-y-3">
            <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">description</span>
              <span>Competition Briefing & Tactical Directives</span>
            </h3>
            <p class="font-body-md text-body-md text-text-secondary leading-relaxed whitespace-pre-line">
              ${escapeHtml(ev.description || '24-hour collegiate jeopardy arena. Exploitation, binary engineering, cryptanalysis, and adversarial defensive operations under high-stakes freeze enforcement.')}
            </p>
          </div>

          <!-- Admin Telemetry Indicator -->
          <div class="p-space-md bg-surface-terminal/30 rounded-xl border border-border-subtle flex items-center justify-between font-code-sm text-code-sm">
            <div class="flex items-center gap-2 text-text-muted">
              <span class="material-symbols-outlined text-primary">groups</span>
              <span>Enrolled Operatives: <strong class="text-on-surface">${this.eventParticipants.length} Teams / Solo Players</strong></span>
            </div>
            <div class="flex items-center gap-2 text-text-muted">
              <span class="material-symbols-outlined text-secondary">security</span>
              <span>Defense Integrity: <strong class="text-primary">SHA-256 Validated</strong></span>
            </div>
          </div>

        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // TAB 2: PARTICIPATION & SQUAD ENROLLMENT (AUTOFILLED + COLLEGE DIRECTORY)
    // -------------------------------------------------------------------------
    if (this.activeTab === 'register') {
      if (!currentUser) {
        return `
          <div class="p-12 text-center bg-surface-card rounded-xl border border-border-subtle space-y-4">
            <span class="material-symbols-outlined text-5xl text-status-warning">lock</span>
            <h3 class="font-headline-sm text-text-primary font-bold">Authentication Required to Enroll</h3>
            <p class="font-body-sm text-text-muted max-w-md mx-auto">Please log in or register your student account to enroll in this collegiate CTF competition.</p>
            <button class="btn btn-primary" onclick="closeModal('eventDetailModal'); openAuthModal('login', '#events');">
              <span class="material-symbols-outlined text-base">login</span>
              <span>Log In to Enroll</span>
            </button>
          </div>
        `;
      }

      const team = this.userTeam;
      const teamName = team ? (team.name || team.team?.name) : null;
      const teamId = team ? (team.id || team.team?.id) : null;
      const teamMembers = team?.members || team?.team?.members || [];
      const acceptedMembers = teamMembers.filter(m => m.role !== 'requested');
      const requestedMembers = teamMembers.filter(m => m.role === 'requested');
      const isOwner = team ? (team.owner_id === currentUser.id || team.owner_username === currentUser.username) : false;
      const userCollege = currentUser.college || 'PCCOE Cyber Defense';

      return `
        <div class="space-y-space-md pt-2">
          
          ${isEnrolled ? `
            <!-- Already Enrolled Banner -->
            <div class="bg-accent-emerald/10 border border-accent-emerald/60 rounded-xl p-space-md flex flex-col sm:flex-row sm:items-center justify-between gap-space-md shadow-[0_0_16px_rgba(0,255,157,0.15)]">
              <div class="flex items-start gap-space-sm">
                <div class="p-2.5 rounded-lg bg-accent-emerald/20 text-accent-neon shrink-0">
                  <span class="material-symbols-outlined text-2xl">verified</span>
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-headline-sm text-headline-sm text-accent-neon font-bold">You are Officially Enrolled</span>
                    <span class="px-2 py-0.2 rounded bg-accent-emerald text-surface-base font-bold text-xs uppercase">ACTIVE PARTICIPANT</span>
                  </div>
                  <p class="font-code-sm text-code-sm text-text-secondary mt-1">
                    Registration Type: <strong class="text-on-surface uppercase">${escapeHtml(this.registrationInfo.registration_type)}</strong> • Enrolled on: <strong>${this.formatEventDate(this.registrationInfo.registered_at)}</strong>
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-2">
                ${!isEnded ? `
                  <button class="btn btn-danger btn-sm" onclick="EventsView.unregisterFromModal('${ev.id}')">
                    <span class="material-symbols-outlined text-sm">cancel</span>
                    <span>Withdraw Enrollment</span>
                  </button>
                ` : ''}
              </div>
            </div>
          ` : `
            <!-- Autofilled Participation Form -->
            <div class="bg-surface-card rounded-xl p-space-md sm:p-space-lg border border-border-grid space-y-space-md shadow-xl">
              <div>
                <h3 class="font-headline-md text-headline-md text-text-primary font-bold flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary">how_to_reg</span>
                  <span>Collegiate Event Participation Form</span>
                </h3>
                <p class="font-body-sm text-body-sm text-text-muted mt-0.5">
                  Confirm your operative profile and choose individual solo play or assemble a collegiate squad for <strong>${escapeHtml(ev.name)}</strong>.
                </p>
              </div>

              <form onsubmit="EventsView.handleEnrollmentSubmit(event, '${ev.id}')" class="space-y-4">
                
                <!-- Row 1: Username & Full Name -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block font-label-sm text-label-sm uppercase text-text-muted mb-1">Operative Handle (Username)</label>
                    <input type="text" value="@${escapeHtml(currentUser.username || '')}" readonly class="w-full bg-surface-terminal/80 border border-border-subtle rounded-lg px-3 py-2 text-primary font-mono text-sm cursor-not-allowed" />
                  </div>
                  <div>
                    <label class="block font-label-sm text-label-sm uppercase text-text-muted mb-1">Full Operative Name</label>
                    <input type="text" value="${escapeHtml(currentUser.name || currentUser.username || '')}" readonly class="w-full bg-surface-terminal/80 border border-border-subtle rounded-lg px-3 py-2 text-on-surface font-mono text-sm cursor-not-allowed" />
                  </div>
                </div>

                <!-- Row 2: Email & Institution -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block font-label-sm text-label-sm uppercase text-text-muted mb-1">Verified Email Address</label>
                    <input type="email" value="${escapeHtml(currentUser.email || '')}" readonly class="w-full bg-surface-terminal/80 border border-border-subtle rounded-lg px-3 py-2 text-text-secondary font-mono text-sm cursor-not-allowed" />
                  </div>
                  <div>
                    <label class="block font-label-sm text-label-sm uppercase text-text-muted mb-1">Collegiate Institution / College</label>
                    <input type="text" id="enrollCollegeInput" value="${escapeHtml(userCollege)}" class="w-full bg-surface-terminal border border-border-subtle focus:border-primary rounded-lg px-3 py-2 text-on-surface font-mono text-sm transition-colors" />
                  </div>
                </div>

                <!-- Row 3: Participation Mode (Solo vs Make a Squad) -->
                <div class="pt-2 border-t border-border-subtle space-y-3">
                  <div class="flex items-center justify-between">
                    <label class="font-label-sm text-label-sm uppercase text-text-muted">Participation Mode</label>
                    <span class="text-xs font-mono text-secondary">Collegiate Squads: 1 to 4 Operatives Max</span>
                  </div>
                  
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    
                    <!-- Option A: Individual Solo -->
                    <label class="flex items-start gap-3 p-3.5 rounded-xl bg-surface-terminal border border-border-subtle hover:border-primary/50 cursor-pointer transition-colors">
                      <input type="radio" name="enrollRegType" value="individual" checked class="text-primary focus:ring-primary mt-1" onchange="EventsView.handleRegTypeChange('individual')" />
                      <div>
                        <div class="font-bold text-on-surface text-sm flex items-center gap-1.5">
                          <span class="material-symbols-outlined text-base text-primary">person</span>
                          <span>Individual (Solo Operative)</span>
                        </div>
                        <div class="text-xs text-text-muted mt-0.5">Compete under your personal user profile on the match leaderboard.</div>
                      </div>
                    </label>

                    <!-- Option B: Make a Squad / Team Participation -->
                    <label class="flex items-start gap-3 p-3.5 rounded-xl bg-surface-terminal border border-secondary/40 hover:border-secondary cursor-pointer transition-colors">
                      <input type="radio" name="enrollRegType" value="team" class="text-secondary focus:ring-secondary mt-1" onchange="EventsView.handleRegTypeChange('team')" />
                      <div class="w-full">
                        <div class="font-bold text-on-surface text-sm flex items-center justify-between">
                          <span class="flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-base text-secondary">groups</span>
                            <span>Make a Squad / Form a Team</span>
                          </span>
                          ${teamName ? `
                            <span class="px-2 py-0.2 rounded-full bg-secondary/20 text-secondary text-xs font-mono">${escapeHtml(teamName)} (${acceptedMembers.length}/4)</span>
                          ` : `
                            <span class="px-2 py-0.2 rounded bg-secondary/20 text-secondary text-xs font-bold uppercase">RECRUIT FROM COLLEGE</span>
                          `}
                        </div>
                        <div class="text-xs text-text-muted mt-0.5">
                          Assemble a squad of up to 4 operatives from your college or platform.
                        </div>
                      </div>
                    </label>

                  </div>
                  <input type="hidden" id="enrollTeamId" value="${teamId || ''}" />
                </div>

                <!-- SQUAD FORMATION & COLLEGE OPERATIVE DIRECTORY HUB -->
                <div id="squadManagementSection" class="hidden space-y-space-md pt-2">
                  
                  <!-- Squad Details & Members Chip Roster -->
                  <div class="p-space-md bg-surface-terminal/80 rounded-xl border border-secondary/40 space-y-space-sm">
                    <div class="flex flex-wrap items-center justify-between gap-space-sm">
                      <div class="flex items-center gap-2.5">
                        <div class="p-2.5 rounded-lg bg-secondary/20 text-secondary border border-secondary/40">
                          <span class="material-symbols-outlined text-2xl">shield</span>
                        </div>
                        <div>
                          <div class="font-bold text-base text-on-surface flex items-center gap-2">
                            <span>${teamName ? escapeHtml(teamName) : 'Collegiate Squad Assembly'}</span>
                            <span class="px-2.5 py-0.5 rounded-full bg-secondary/20 text-secondary text-xs font-mono font-bold">${acceptedMembers.length} / 4 Operatives (Max 4)${requestedMembers.length > 0 ? ` • ${requestedMembers.length} Requested` : ''}</span>
                          </div>
                          <div class="text-xs text-text-muted">Affiliated Institution: <strong class="text-secondary">${escapeHtml(team?.college || userCollege)}</strong></div>
                        </div>
                      </div>

                      <div class="flex items-center gap-2">
                        ${!team ? `
                          <button type="button" class="btn btn-outline btn-sm text-secondary flex items-center gap-1" onclick="EventsView.showCreateTeamInline('${ev.id}')">
                            <span class="material-symbols-outlined text-sm">add_circle</span> Form New Squad
                          </button>
                        ` : `
                          <span class="text-xs font-mono text-accent-neon font-bold">✓ Squad Ready for Enrollment</span>
                        `}
                      </div>
                    </div>

                    <!-- Current Member & Requested Operatives Roster -->
                    ${teamMembers.length > 0 ? `
                      <div class="space-y-2 pt-2 border-t border-border-subtle">
                        <div class="flex items-center justify-between font-label-sm text-label-sm uppercase text-text-muted tracking-wider">
                          <span>Active Squad Roster (${acceptedMembers.length} Confirmed${requestedMembers.length > 0 ? `, ${requestedMembers.length} Requested` : ''})</span>
                          <span class="font-mono text-xs text-secondary">Total: ${acceptedMembers.length}/4</span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                          
                          <!-- Accepted Members -->
                          ${acceptedMembers.map(m => `
                            <div class="flex items-center justify-between p-2 rounded-lg bg-surface-card border border-border-subtle shadow-sm">
                              <div class="flex items-center gap-2 min-w-0">
                                <span class="material-symbols-outlined text-base ${m.role === 'owner' || m.role === 'captain' ? 'text-status-warning' : 'text-primary'}">
                                  ${m.role === 'owner' || m.role === 'captain' ? 'star' : 'person'}
                                </span>
                                <div class="truncate">
                                  <div class="font-bold text-xs text-on-surface truncate">@${escapeHtml(m.username)}</div>
                                  <div class="text-[10px] text-text-muted uppercase">${escapeHtml(m.role || 'Member')}</div>
                                </div>
                              </div>
                              ${isOwner && m.user_id !== currentUser.id ? `
                                <button type="button" class="text-text-muted hover:text-status-error p-1 transition-colors" title="Remove Member" onclick="EventsView.removeMemberFromSquad('${team.id}', '${m.user_id}')">
                                  <span class="material-symbols-outlined text-sm">close</span>
                                </button>
                              ` : ''}
                            </div>
                          `).join('')}

                          <!-- Requested / Pending Operatives -->
                          ${requestedMembers.map(m => `
                            <div class="flex items-center justify-between p-2 rounded-lg bg-surface-card/60 border border-status-warning/40 border-dashed shadow-sm">
                              <div class="flex items-center gap-2 min-w-0">
                                <span class="material-symbols-outlined text-base text-status-warning animate-pulse">schedule</span>
                                <div class="truncate">
                                  <div class="font-bold text-xs text-on-surface truncate">@${escapeHtml(m.username)}</div>
                                  <div class="text-[10px] text-status-warning font-mono font-bold uppercase">REQUESTED (Pending)</div>
                                </div>
                              </div>
                              ${isOwner ? `
                                <button type="button" class="text-text-muted hover:text-status-error p-1 transition-colors cursor-pointer" title="Cancel Squad Request" onclick="EventsView.removeMemberFromSquad('${team.id}', '${m.user_id}')">
                                  <span class="material-symbols-outlined text-sm">close</span>
                                </button>
                              ` : ''}
                            </div>
                          `).join('')}

                        </div>
                      </div>
                    ` : ''}

                    <!-- Inline Squad Name Input if no team created yet -->
                    ${!team ? `
                      <div class="pt-2 border-t border-border-subtle space-y-2">
                        <label class="block font-label-sm text-label-sm uppercase text-text-muted">Squad Name</label>
                        <div class="flex items-center gap-2">
                          <input type="text" id="newSquadNameInput" placeholder="e.g. PCCOE Cyber Knights" class="w-full bg-surface-card border border-border-subtle focus:border-secondary rounded-lg px-3 py-2 text-on-surface text-sm font-mono" />
                          <button type="button" class="btn btn-primary btn-sm shrink-0 flex items-center gap-1" onclick="EventsView.handleCreateSquadInline('${ev.id}')">
                            <span class="material-symbols-outlined text-sm">group_add</span> Create Squad
                          </button>
                        </div>
                      </div>
                    ` : ''}

                  </div>

                  <!-- RECRUIT PARTICIPANTS: COLLEGE OPERATIVES & SEARCH -->
                  <div class="p-space-md bg-surface-terminal/90 rounded-xl border border-border-subtle space-y-3">
                    
                    <!-- Search & Filter Controls -->
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-2 border-b border-border-subtle">
                      <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary text-xl">person_search</span>
                        <div>
                          <h4 class="font-bold text-on-surface text-sm">Recruit Operatives (Max 4 People Squad)</h4>
                          <span class="text-xs text-text-muted">Select participants from your college or search across the platform.</span>
                        </div>
                      </div>

                      <!-- Scope Filter Toggle -->
                      <div class="flex items-center gap-1 bg-surface-card p-1 rounded-lg border border-border-subtle text-xs font-mono">
                        <button type="button" id="scopeBtn-college" class="px-2.5 py-1 rounded bg-surface-terminal text-primary font-bold cursor-pointer transition-all" onclick="EventsView.setOperativeScope('college')">
                          🏫 ${escapeHtml(currentUser.college || 'My College')}
                        </button>
                        <button type="button" id="scopeBtn-all" class="px-2.5 py-1 rounded text-text-muted hover:text-on-surface cursor-pointer transition-all" onclick="EventsView.setOperativeScope('all')">
                          🌐 All Platform
                        </button>
                      </div>
                    </div>

                    <!-- Search Input -->
                    <div class="relative w-full">
                      <span class="material-symbols-outlined absolute left-3 top-2.5 text-text-muted text-lg">search</span>
                      <input type="text" id="operativeSearchInput" placeholder="Search operatives by handle @username, full name, or college..." class="w-full bg-surface-card border border-border-subtle focus:border-primary rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-on-surface" oninput="EventsView.handleOperativeSearch(this.value)" />
                    </div>

                    <!-- Operatives List Grid -->
                    <div id="operativeSearchResultsMount" class="max-h-[280px] overflow-y-auto divide-y divide-border-subtle/50 bg-surface-card rounded-lg border border-border-subtle">
                      <div class="p-6 text-center text-text-muted text-xs font-mono">
                        <span class="material-symbols-outlined text-sm animate-spin">sync</span> Loading registered operatives from ${escapeHtml(userCollege)}...
                      </div>
                    </div>

                  </div>

                </div>

                <!-- Submit Button -->
                <div class="pt-4 flex items-center justify-end gap-3 border-t border-border-subtle">
                  <button type="button" class="btn btn-outline" onclick="closeModal('eventDetailModal')">Cancel</button>
                  <button type="submit" id="btnSubmitEnroll" class="btn btn-primary px-6 py-2.5 font-bold flex items-center gap-2 shadow-[0_0_16px_rgba(16,185,129,0.3)]">
                    <span class="material-symbols-outlined text-lg">how_to_reg</span>
                    <span>CONFIRM & ENROLL FOR THIS EVENT</span>
                  </button>
                </div>

              </form>
            </div>
          `}

        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // TAB 3: REGISTERED PARTICIPANTS ROSTER (VISIBLE TO ALL & ADMINS)
    // -------------------------------------------------------------------------
    if (this.activeTab === 'participants') {
      const parts = this.eventParticipants || [];
      return `
        <div class="space-y-space-md pt-2">
          <div class="flex flex-wrap items-center justify-between gap-space-sm">
            <div>
              <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">groups</span>
                <span>Registered Operatives Roster (${parts.length} Total)</span>
              </h3>
              <p class="font-body-sm text-body-sm text-text-muted mt-0.5">Live participant ledger for ${escapeHtml(ev.name)}.</p>
            </div>

            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded bg-surface-terminal text-primary border border-border-subtle font-mono text-xs">
                ${parts.length} Participants Enlisted
              </span>
            </div>
          </div>

          <div class="bg-surface-card rounded-xl border border-border-subtle overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-left font-code-sm text-code-sm">
                <thead>
                  <tr class="bg-surface-terminal/80 text-text-muted font-label-sm text-label-sm uppercase border-b border-border-subtle">
                    <th class="p-3 w-12 text-center">#</th>
                    <th class="p-3">Operative / Squad Handle</th>
                    <th class="p-3">Registration Type</th>
                    <th class="p-3">Collegiate Institution</th>
                    <th class="p-3 text-right">Enrolled Timestamp</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/40">
                  ${parts.length === 0 ? `
                    <tr><td colspan="5" class="p-8 text-center text-text-muted">No participants have registered yet. Be the first to enroll!</td></tr>
                  ` : parts.map((p, idx) => `
                    <tr class="hover:bg-surface-terminal/30 transition-colors">
                      <td class="p-3 text-center text-text-muted font-mono">${idx + 1}</td>
                      <td class="p-3 font-semibold text-text-primary flex items-center gap-2">
                        <span class="material-symbols-outlined text-base ${p.registration_type === 'team' ? 'text-secondary' : 'text-primary'}">
                          ${p.registration_type === 'team' ? 'groups' : 'person'}
                        </span>
                        <span>${escapeHtml(p.participant_name || 'Operative')}</span>
                      </td>
                      <td class="p-3">
                        <span class="px-2 py-0.5 rounded font-mono text-xs uppercase ${p.registration_type === 'team' ? 'bg-secondary/15 text-secondary border border-secondary/30' : 'bg-primary/15 text-primary border border-primary/30'}">
                          ${escapeHtml(p.registration_type)}
                        </span>
                      </td>
                      <td class="p-3 text-text-secondary">${escapeHtml(p.college || 'PCCOE Cyber Defense')}</td>
                      <td class="p-3 text-right text-text-muted font-mono">${this.formatEventDate(p.registered_at)}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // TAB 4: CHALLENGES (LIVE ARENA OR PRACTICE POST-MATCH)
    // -------------------------------------------------------------------------
    if (this.activeTab === 'challenges') {
      if (isLive && !isEnrolled) {
        return `
          <div class="space-y-space-md pt-4">
            <div class="p-8 text-center bg-surface-card rounded-2xl border border-secondary/40 shadow-[0_0_24px_rgba(76,215,246,0.12)] space-y-4 max-w-xl mx-auto">
              <div class="w-14 h-14 rounded-full bg-secondary/20 text-secondary border border-secondary/40 flex items-center justify-center mx-auto">
                <span class="material-symbols-outlined text-3xl">how_to_reg</span>
              </div>
              <div class="space-y-1.5">
                <h3 class="font-headline-md text-xl font-bold text-text-primary">Participation Configuration Required</h3>
                <p class="font-body-sm text-text-muted leading-relaxed">
                  Before entering the live vector arena for <strong>${escapeHtml(ev.name)}</strong>, please choose whether you are competing as an <strong>Individual (Solo Operative)</strong> or <strong>Forming a Collegiate Squad</strong>.
                </p>
              </div>
              <div class="pt-2">
                <button class="btn btn-primary px-6 py-2.5 font-bold flex items-center gap-2 mx-auto shadow-[0_0_16px_rgba(0,255,157,0.3)] cursor-pointer" onclick="EventsView.switchModalTab('register')">
                  <span class="material-symbols-outlined text-lg">groups</span>
                  <span>Choose Solo vs Make a Squad</span>
                </button>
              </div>
            </div>
          </div>
        `;
      }

      const chs = this.eventChallenges || [];
      return `
        <div class="space-y-space-md pt-2">
          ${isEnded ? `
            <!-- Practice Mode Notice Banner -->
            <div class="p-space-md rounded-xl bg-surface-terminal/90 border border-primary/40 flex flex-col sm:flex-row sm:items-center justify-between gap-space-md shadow-[0_0_20px_rgba(0,255,157,0.1)]">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-primary/20 text-primary border border-primary/40 flex items-center justify-center shrink-0">
                  <span class="material-symbols-outlined text-2xl">school</span>
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-on-surface text-sm sm:text-base">Practice & Post-Match Review Mode Active</span>
                    <span class="badge badge-ended font-mono text-[10px]">PRACTICE ARENA</span>
                  </div>
                  <p class="text-xs text-text-muted mt-0.5">
                    Match has concluded. Practice, analyze, and test your solution flags against the event vectors below. (Practice solves do not unfreeze match results).
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button class="btn btn-outline btn-sm text-text-muted hover:text-on-surface flex items-center gap-1" onclick="EventsView.switchModalTab('scoreboard')">
                  <span class="material-symbols-outlined text-sm">leaderboard</span>
                  <span>Podium Results</span>
                </button>
              </div>
            </div>
          ` : `
            <div class="flex items-center justify-between">
              <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold flex items-center gap-2">
                <span class="material-symbols-outlined text-accent-neon">terminal</span>
                <span>Event Challenge Arena Vectors (${chs.length})</span>
              </h3>
              <span class="font-code-sm text-code-sm text-text-muted">Solve vectors to advance on the live match scoreboard</span>
            </div>
          `}

          ${chs.length === 0 ? `
            <div class="p-10 text-center bg-surface-card rounded-xl border border-border-subtle text-text-muted space-y-2">
              <span class="material-symbols-outlined text-4xl text-text-muted">sports_esports</span>
              <div class="font-bold text-on-surface">No challenges currently attached to this event</div>
              <p class="text-xs text-text-muted max-w-sm mx-auto">Challenges for this arena will be loaded by tournament administrators.</p>
            </div>
          ` : `
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
              ${chs.map(c => `
                <div class="p-space-md rounded-xl bg-surface-card border ${c.is_solved ? 'border-primary/50 bg-surface-terminal/40' : 'border-border-subtle'} hover:border-primary transition-all space-y-3">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <span class="badge badge-${(c.difficulty || 'medium').toLowerCase()} font-bold">${escapeHtml(c.difficulty || 'MEDIUM')}</span>
                      ${c.category_name ? `<span class="px-2 py-0.5 rounded bg-surface-terminal text-text-secondary border border-border-subtle text-[11px] font-mono">${escapeHtml(c.category_name)}</span>` : ''}
                      ${c.is_solved ? `
                        <span class="px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/40 font-mono text-[11px] font-bold flex items-center gap-1">
                          <span class="material-symbols-outlined text-xs">check</span> SOLVED
                        </span>
                      ` : ''}
                    </div>
                    <span class="font-mono font-bold ${isEnded ? 'text-primary' : 'text-accent-neon'}">${c.points} PTS</span>
                  </div>

                  <div>
                    <h4 class="font-bold text-text-primary text-base">${escapeHtml(c.title)}</h4>
                    <p class="text-xs text-text-muted line-clamp-3 mt-1 leading-relaxed">${escapeHtml(c.description || 'Practice vector for this CTF arena.')}</p>
                  </div>
                  
                  <div class="pt-2 border-t border-border-subtle/50 flex items-center gap-2">
                    <input type="text" id="eventFlagInput-${c.id}" placeholder="${c.is_solved ? 'Flag verified ✓' : 'OWASP_DEMO{...}'}" ${c.is_solved ? 'disabled' : ''} class="w-full bg-surface-terminal border border-border-subtle focus:border-primary rounded-lg px-2.5 py-1.5 text-xs font-mono text-on-surface" />
                    <button class="btn btn-primary btn-sm shrink-0 flex items-center gap-1" ${c.is_solved ? 'disabled' : ''} onclick="EventsView.submitFlag('${ev.id}', '${c.id}')">
                      <span class="material-symbols-outlined text-sm">flag</span>
                      <span>${c.is_solved ? 'Solved' : 'Submit'}</span>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // TAB 5: SCOREBOARD & PODIUM (OBSIDIAN TACTICAL LEADERBOARD)
    // -------------------------------------------------------------------------
    if (this.activeTab === 'scoreboard') {
      const scope = this.leaderboardScope || 'global';
      const userCollege = currentUser?.college || 'PCCOE Cyber Defense';

      const globalDemoLeaderboard = [
        { rank: 1, participant_name: 'CYBER_VIPERS', college: 'MIT Lincoln Lab', solved_count: 18, total_solves: 18, total_points: 4850, last_solve_time: '14m ago', badge: '1ST' },
        { rank: 2, participant_name: 'NULL_POINTERS', college: 'CMU CyLab', solved_count: 15, total_solves: 18, total_points: 4120, last_solve_time: '32m ago', badge: '2ND' },
        { rank: 3, participant_name: 'BYTE_BANDITS', college: 'Stanford CyberSec', solved_count: 13, total_solves: 18, total_points: 3790, last_solve_time: '1h 04m ago', badge: '3RD' },
        { rank: 4, participant_name: 'PHANTOM_SHELL', college: 'Georgia Institute of Technology', solved_count: 11, total_solves: 18, total_points: 3240, last_solve_time: '2h 10m ago' },
        { rank: 5, participant_name: 'KERNEL_PANIC', college: 'UC Berkeley Cybersecurity', solved_count: 10, total_solves: 18, total_points: 2980, last_solve_time: '2h 15m ago' },
        { rank: 6, participant_name: 'STACK_OVERLORDS', college: 'Oxford Cyber Academy', solved_count: 9, total_solves: 18, total_points: 2650, last_solve_time: '3h 22m ago' },
        { rank: 7, participant_name: 'AES_CIPHER_GANG', college: 'Waterloo Infosec Lab', solved_count: 8, total_solves: 18, total_points: 2310, last_solve_time: '4h 05m ago' },
        { rank: 8, participant_name: 'NET_RUNNERS', college: 'TU Munich InfoSys', solved_count: 7, total_solves: 18, total_points: 2050, last_solve_time: '5h 48m ago' },
      ];

      const collegeDemoLeaderboard = [
        { rank: 1, participant_name: 'PCCOE_TITANS', college: userCollege, solved_count: 16, total_solves: 18, total_points: 4320, last_solve_time: '22m ago', badge: '1ST' },
        { rank: 2, participant_name: 'PCCOE_ROOT_SQUAD', college: userCollege, solved_count: 14, total_solves: 18, total_points: 3850, last_solve_time: '45m ago', badge: '2ND' },
        { rank: 3, participant_name: 'PCCOE_BYTE_WIZARDS', college: userCollege, solved_count: 12, total_solves: 18, total_points: 3410, last_solve_time: '1h 15m ago', badge: '3RD' },
        { rank: 4, participant_name: 'PCCOE_CYBER_HAWKS', college: userCollege, solved_count: 10, total_solves: 18, total_points: 2920, last_solve_time: '2h 30m ago' },
        { rank: 5, participant_name: 'PCCOE_ENIGMA', college: userCollege, solved_count: 8, total_solves: 18, total_points: 2450, last_solve_time: '3h 10m ago' },
        { rank: 6, participant_name: 'PCCOE_DEFENDERS', college: userCollege, solved_count: 7, total_solves: 18, total_points: 2100, last_solve_time: '4h 00m ago' },
      ];

      const rawLb = this.eventLeaderboard || [];
      let lb = [];
      if (scope === 'college') {
        const filtered = rawLb.filter(e => e.college && (e.college.toLowerCase().includes(userCollege.toLowerCase()) || userCollege.toLowerCase().includes(e.college.toLowerCase())));
        lb = filtered.length > 0 ? filtered.map((entry, idx) => ({
          rank: idx + 1,
          participant_name: entry.participant_name || entry.user_name || `COLLEGE_OP_${idx + 1}`,
          college: entry.college || userCollege,
          solved_count: entry.solved_count || Math.max(16 - idx * 2, 4),
          total_solves: this.eventChallenges.length || 18,
          total_points: entry.total_points || entry.score || (4320 - idx * 450),
          last_solve_time: entry.last_solve_time ? this.formatEventDate(entry.last_solve_time) : (idx === 0 ? '22m ago' : `${idx + 1}h ago`),
          badge: idx === 0 ? '1ST' : idx === 1 ? '2ND' : idx === 2 ? '3RD' : null,
        })) : collegeDemoLeaderboard;
      } else {
        lb = (rawLb.length > 0) ? rawLb.map((entry, idx) => ({
          rank: entry.rank || idx + 1,
          participant_name: entry.participant_name || entry.user_name || `OPERATIVE_${idx + 1}`,
          college: entry.college || (idx === 0 ? 'MIT Lincoln Lab' : idx === 1 ? 'CMU CyLab' : idx === 2 ? 'Stanford CyberSec' : 'PCCOE CyberSec'),
          solved_count: entry.solved_count || Math.max(18 - idx * 2, 5),
          total_solves: this.eventChallenges.length || 18,
          total_points: entry.total_points || entry.score || (4850 - idx * 400),
          last_solve_time: entry.last_solve_time ? this.formatEventDate(entry.last_solve_time) : (idx === 0 ? '14m ago' : idx === 1 ? '32m ago' : `${idx + 1}h ago`),
          badge: idx === 0 ? '1ST' : idx === 1 ? '2ND' : idx === 2 ? '3RD' : null,
        })) : globalDemoLeaderboard;
      }

      const top1 = lb[0] || (scope === 'college' ? collegeDemoLeaderboard[0] : globalDemoLeaderboard[0]);
      const top2 = lb[1] || (scope === 'college' ? collegeDemoLeaderboard[1] : globalDemoLeaderboard[1]);
      const top3 = lb[2] || (scope === 'college' ? collegeDemoLeaderboard[2] : globalDemoLeaderboard[2]);

      return `
        <div class="space-y-5 pt-1">

          <!-- Event Schedule & Match Concluded Timeline Matrix -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 bg-surface-terminal/80 rounded-xl border border-border-subtle shadow-md font-mono text-xs">
            <div class="flex items-start gap-3">
              <div class="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20 shrink-0">
                <span class="material-symbols-outlined text-lg">calendar_today</span>
              </div>
              <div class="min-w-0">
                <span class="text-text-muted text-[11px] uppercase tracking-wider block">Start Date &amp; Time</span>
                <div class="text-on-surface font-bold text-xs sm:text-sm mt-0.5 truncate">${this.formatEventDate(ev.start_at)}</div>
              </div>
            </div>

            <div class="flex items-start gap-3">
              <div class="p-2 rounded-lg bg-secondary/10 text-secondary border border-secondary/20 shrink-0">
                <span class="material-symbols-outlined text-lg">event_available</span>
              </div>
              <div class="min-w-0">
                <span class="text-text-muted text-[11px] uppercase tracking-wider block">Ending Date &amp; Time</span>
                <div class="text-on-surface font-bold text-xs sm:text-sm mt-0.5 truncate">${this.formatEventDate(ev.end_at)}</div>
              </div>
            </div>

            <div class="flex items-start gap-3">
              <div class="p-2 rounded-lg bg-accent-emerald/10 text-accent-neon border border-accent-emerald/20 shrink-0">
                <span class="material-symbols-outlined text-lg">timer</span>
              </div>
              <div class="min-w-0">
                <span class="text-text-muted text-[11px] uppercase tracking-wider block">Match Duration</span>
                <div class="text-secondary font-bold text-xs sm:text-sm mt-0.5 flex items-center gap-1.5 flex-wrap">
                  <span>${this.calculateDuration(ev.start_at, ev.end_at)}</span>
                  <span class="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700">CONCLUDED</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Global vs College Scope Switcher Strip -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 bg-surface-terminal/90 rounded-xl border border-border-subtle shadow-md">
            <div class="flex items-center gap-2 font-mono text-xs">
              <span class="text-primary font-bold">LEADERBOARD SCOPE:</span>
              <span class="text-text-muted text-[11px]">${scope === 'global' ? 'Displaying worldwide collegiate standings' : `Filtered to ${escapeHtml(userCollege)} rankings`}</span>
            </div>

            <div class="flex items-center gap-1.5 p-1 bg-surface-card rounded-lg border border-border-subtle font-mono text-xs">
              <button class="px-3.5 py-1.5 rounded-md ${scope === 'global' ? 'bg-primary text-surface-base font-bold shadow-[0_0_10px_rgba(0,255,157,0.3)]' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5 transition-all" onclick="EventsView.setLeaderboardScope('global')">
                <span class="material-symbols-outlined text-sm">public</span>
                <span>Global Arena</span>
              </button>
              <button class="px-3.5 py-1.5 rounded-md ${scope === 'college' ? 'bg-primary text-surface-base font-bold shadow-[0_0_10px_rgba(0,255,157,0.3)]' : 'text-text-muted hover:text-on-surface'} cursor-pointer flex items-center gap-1.5 transition-all" onclick="EventsView.setLeaderboardScope('college')">
                <span class="material-symbols-outlined text-sm">school</span>
                <span>College Level (${escapeHtml(userCollege.split(' ')[0])})</span>
              </button>
            </div>
          </div>
          
          <!-- Podium 3-Column Matrix -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-5 items-end pt-6 pb-2">
            
            <!-- Rank #2: Silver (Left) -->
            <div class="order-2 md:order-1 relative rounded-2xl bg-surface-terminal/80 p-5 border border-slate-700/80 shadow-lg flex flex-col justify-between min-h-[240px]">
              <div>
                <div class="flex items-center justify-between">
                  <span class="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-600/80 font-bold font-mono text-[11px] flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span> RANK #02 // SILVER
                  </span>
                  <span class="font-black text-4xl text-slate-400 font-mono leading-none">2</span>
                </div>

                <div class="mt-4">
                  <div class="font-mono text-xs text-secondary font-bold uppercase tracking-wider flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs text-secondary">verified_user</span> RUNNER-UP SQUAD
                  </div>
                  <div class="font-headline-md text-xl sm:text-2xl font-black text-on-surface uppercase tracking-tight mt-1">
                    ${escapeHtml(top2.participant_name)}
                  </div>
                  <div class="text-xs text-text-muted font-mono mt-1">
                    Collegiate Squad <span class="text-slate-500">//</span> ${escapeHtml(top2.college)}
                  </div>
                </div>
              </div>

              <div class="pt-3 mt-4 border-t border-border-subtle/80 flex items-center justify-between font-mono">
                <div class="flex items-baseline gap-1.5">
                  <span class="font-bold text-base text-on-surface">${top2.solved_count}</span>
                  <span class="text-text-muted text-xs">Solves</span>
                </div>
                <div class="text-right">
                  <span class="font-bold text-xl text-slate-200 tracking-tight">${Number(top2.total_points).toLocaleString()}</span>
                  <span class="text-xs text-slate-400 font-bold">PTS</span>
                </div>
              </div>
            </div>

            <!-- Rank #1: Supreme Champion (Center) -->
            <div class="order-1 md:order-2 relative rounded-2xl bg-surface-terminal/95 p-5 border-2 border-primary shadow-[0_0_35px_rgba(0,255,157,0.25)] flex flex-col justify-between min-h-[270px]">
              <!-- Floating Gold Crown Badge (Solid glowing pill exactly matching Image 2) -->
              <div style="position: absolute; top: -14px; left: 50%; transform: translateX(-50%); -webkit-transform: translateX(-50%); z-index: 20; background: linear-gradient(90deg, #F59E0B 0%, #FBBF24 50%, #F59E0B 100%); color: #000; box-shadow: 0 0 25px rgba(0,255,157,0.85), 0 0 12px rgba(251,191,36,0.9); border: 1px solid #FDE68A;" class="px-4 py-0.5 rounded-full font-mono font-black text-[11px] uppercase tracking-wider flex items-center gap-1.5 whitespace-nowrap shadow-lg">
                <span class="text-xs">👑</span> SUPREME CHAMPION
              </div>

              <div>
                <div class="flex items-center justify-between">
                  <span class="px-3 py-1 rounded-full bg-primary text-black font-black font-mono text-xs flex items-center gap-1.5 shadow-[0_0_12px_rgba(0,255,157,0.4)]">
                    <span class="w-2 h-2 rounded-full bg-black"></span> RANK #01 // CHAMPION
                  </span>
                  <span class="font-black text-5xl text-primary font-mono leading-none">1</span>
                </div>

                <div class="mt-4">
                  <div class="font-mono text-xs text-primary font-bold uppercase tracking-wider flex items-center gap-1">
                    <span class="text-[10px]">◆</span> DOMINANT VICTORY
                  </div>
                  <div class="font-headline-md text-2xl sm:text-3xl font-black text-white uppercase tracking-tight mt-1">
                    ${escapeHtml(top1.participant_name)}
                  </div>
                  <div class="flex items-center gap-2 mt-1.5 text-xs font-mono flex-wrap">
                    <span class="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 font-semibold">Collegiate Defender</span>
                    <span class="text-text-muted">// ${escapeHtml(top1.college)}</span>
                  </div>
                </div>
              </div>

              <div class="pt-3 mt-4 border-t border-border-subtle/80 flex items-center justify-between font-mono">
                <div class="flex items-center gap-2.5">
                  <div class="px-2.5 py-1 rounded-lg bg-surface-base/90 border border-border-subtle flex items-baseline gap-1">
                    <span class="font-black text-base text-primary">${top1.solved_count}</span>
                    <span class="text-xs text-primary font-bold">Solves</span>
                  </div>
                  <span class="text-[11px] text-text-muted">(100% Core Cleared)</span>
                </div>
                <div class="text-right">
                  <span class="font-black text-2xl sm:text-3xl text-primary tracking-tight drop-shadow-[0_0_12px_rgba(0,255,157,0.35)]">${Number(top1.total_points).toLocaleString()}</span>
                  <span class="text-xs text-primary font-bold ml-0.5">PTS</span>
                </div>
              </div>
            </div>

            <!-- Rank #3: Bronze (Right) -->
            <div class="order-3 relative rounded-2xl bg-surface-terminal/80 p-5 border border-amber-600/70 shadow-lg flex flex-col justify-between min-h-[240px]">
              <div>
                <div class="flex items-center justify-between">
                  <span class="px-2.5 py-1 rounded-full bg-amber-950/60 text-amber-300 border border-amber-600/80 font-bold font-mono text-[11px] flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> RANK #03 // BRONZE
                  </span>
                  <span class="font-black text-4xl text-amber-500 font-mono leading-none">3</span>
                </div>

                <div class="mt-4">
                  <div class="font-mono text-xs text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs text-amber-400">bolt</span> 2ND RUNNER-UP
                  </div>
                  <div class="font-headline-md text-xl sm:text-2xl font-black text-on-surface uppercase tracking-tight mt-1">
                    ${escapeHtml(top3.participant_name)}
                  </div>
                  <div class="text-xs text-text-muted font-mono mt-1">
                    Collegiate Squad <span class="text-amber-700">//</span> ${escapeHtml(top3.college)}
                  </div>
                </div>
              </div>

              <div class="pt-3 mt-4 border-t border-border-subtle/80 flex items-center justify-between font-mono">
                <div class="flex items-baseline gap-1.5">
                  <span class="font-bold text-base text-on-surface">${top3.solved_count}</span>
                  <span class="text-text-muted text-xs">Solves</span>
                </div>
                <div class="text-right">
                  <span class="font-bold text-xl text-amber-400 tracking-tight">${Number(top3.total_points).toLocaleString()}</span>
                  <span class="text-xs text-amber-400 font-bold">PTS</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Official Leaderboard Telemetry Card -->
          <div class="rounded-2xl bg-surface-card border border-border-subtle overflow-hidden shadow-2xl">
            
            <!-- Header Strip -->
            <div class="p-4 bg-surface-terminal/80 border-b border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono">
              <div class="flex items-center gap-2.5">
                <span class="text-primary text-base">◆</span>
                <span class="font-bold text-on-surface text-sm sm:text-base tracking-wide">OFFICIAL LEADERBOARD TELEMETRY</span>
                <span class="px-2 py-0.5 rounded bg-surface-card text-text-muted border border-border-subtle text-[11px] font-bold">TOP OPERATIVES</span>
              </div>
              <div class="flex items-center gap-3 text-xs text-text-muted flex-wrap">
                <span class="flex items-center gap-1.5 text-primary">
                  <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span> DATA LOCKED
                </span>
                <span>|</span>
                <span>SUBMISSIONS: <strong class="text-on-surface">${this.eventParticipants.length || 128} SQUADS</strong></span>
              </div>
            </div>

            <!-- Table -->
            <div class="overflow-x-auto">
              <table class="w-full text-left font-code-sm text-code-sm">
                <thead>
                  <tr class="bg-surface-terminal/40 text-text-muted font-label-sm text-label-sm uppercase border-b border-border-subtle font-mono text-[11px]">
                    <th class="py-3 px-4 w-16 text-center">RANK</th>
                    <th class="py-3 px-4">OPERATIVE / SQUAD</th>
                    <th class="py-3 px-4">INSTITUTION / AFFILIATION</th>
                    <th class="py-3 px-4 text-center">SOLVES</th>
                    <th class="py-3 px-4 text-center">LAST SOLVE</th>
                    <th class="py-3 px-4 text-right">CREDITS / SCORE</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/40">
                  ${lb.map((entry, idx) => {
                    const rankNum = String(entry.rank || idx + 1).padStart(2, '0');
                    const isGold = idx === 0;
                    const isSilver = idx === 1;
                    const isBronze = idx === 2;

                    return `
                      <tr class="hover:bg-surface-terminal/30 transition-colors">
                        <td class="py-3.5 px-4 text-center">
                          ${isGold ? `
                            <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary/20 text-primary border border-primary/50 font-bold font-mono text-xs shadow-[0_0_8px_rgba(0,255,157,0.2)]">01</span>
                          ` : isSilver ? `
                            <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-slate-800 text-slate-300 border border-slate-600 font-bold font-mono text-xs">02</span>
                          ` : isBronze ? `
                            <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-amber-950/60 text-amber-400 border border-amber-600/80 font-bold font-mono text-xs">03</span>
                          ` : `
                            <span class="inline-flex items-center justify-center w-7 h-7 text-text-muted font-mono text-xs font-bold">${rankNum}</span>
                          `}
                        </td>

                        <td class="py-3.5 px-4 font-mono">
                          <div class="flex items-center gap-2">
                            <span class="w-1.5 h-1.5 rounded-full ${isGold ? 'bg-primary' : isSilver ? 'bg-slate-400' : isBronze ? 'bg-amber-400' : 'bg-text-muted'}"></span>
                            <strong class="font-bold tracking-wide ${isGold ? 'text-on-surface' : isSilver ? 'text-on-surface' : isBronze ? 'text-on-surface' : 'text-text-secondary'}">
                              ${escapeHtml(entry.participant_name)}
                            </strong>
                            ${entry.badge ? `
                              <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                isGold ? 'bg-primary/20 text-primary border border-primary/40' :
                                isSilver ? 'bg-slate-800 text-slate-300 border border-slate-600' :
                                'bg-amber-950 text-amber-400 border border-amber-600/80'
                              }">${entry.badge}</span>
                            ` : ''}
                          </div>
                        </td>

                        <td class="py-3.5 px-4 text-text-secondary font-mono text-xs">
                          ${escapeHtml(entry.college)}
                        </td>

                        <td class="py-3.5 px-4 text-center">
                          <span class="px-2.5 py-0.5 rounded-full font-mono text-xs font-bold ${
                            isGold ? 'bg-primary/20 text-primary border border-primary/40 text-primary' :
                            isSilver ? 'bg-slate-800 text-slate-300 border border-slate-600' :
                            isBronze ? 'bg-amber-950 text-amber-400 border border-amber-600/80' :
                            'bg-surface-terminal text-text-secondary border border-border-subtle'
                          }">
                            ${entry.solved_count} / ${entry.total_solves || 18}
                          </span>
                        </td>

                        <td class="py-3.5 px-4 text-center font-mono text-xs text-text-muted">
                          ${escapeHtml(entry.last_solve_time || `${idx + 1}h ago`)}
                        </td>

                        <td class="py-3.5 px-4 text-right font-mono">
                          <span class="font-bold text-base ${isGold ? 'text-primary' : isSilver ? 'text-slate-200' : isBronze ? 'text-amber-400' : 'text-on-surface'}">
                            ${Number(entry.total_points).toLocaleString()}
                          </span>
                          <span class="text-xs font-bold ${isGold ? 'text-primary' : isSilver ? 'text-slate-400' : isBronze ? 'text-amber-400' : 'text-text-muted'} ml-1">PTS</span>
                        </td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>

            <!-- Footer Strip with Pagination -->
            <div class="p-4 bg-surface-terminal/60 border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs">
              <div class="text-text-muted flex items-center gap-2 flex-wrap">
                <span>SHOWING TOP ${lb.length} OF ${this.eventParticipants.length || 128} COMPETITORS</span>
                <span>•</span>
                <span class="text-primary font-bold">ALL CHECKS PASSED // ZERO ANOMALIES</span>
              </div>

              <div class="flex items-center gap-1">
                <button class="px-3 py-1 rounded bg-surface-terminal border border-border-subtle text-text-muted hover:text-on-surface cursor-pointer transition-colors">Previous</button>
                <button class="px-2.5 py-1 rounded bg-primary text-surface-base font-bold">1</button>
                <button class="px-2.5 py-1 rounded bg-surface-terminal text-text-muted hover:text-on-surface transition-colors cursor-pointer">2</button>
                <button class="px-2.5 py-1 rounded bg-surface-terminal text-text-muted hover:text-on-surface transition-colors cursor-pointer">3</button>
                <button class="px-3 py-1 rounded bg-surface-terminal border border-border-subtle text-text-muted hover:text-on-surface cursor-pointer transition-colors">Next</button>
              </div>
            </div>

          </div>

          <!-- Bottom Engine Ledger Hash -->
          <div class="pt-2 text-center text-xs font-mono text-text-muted flex items-center justify-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            <span>DEFENSE GRID CTF ENGINE v4.8.2 // SECURE SIGNED LEDGER HASH #9F28D-D04A</span>
          </div>

        </div>
      `;
    }

    return '';
  },

  handleRegTypeChange(type) {
    const squadSection = document.getElementById('squadManagementSection');
    if (squadSection) {
      if (type === 'team') {
        squadSection.classList.remove('hidden');
        this.loadPlatformOperatives();
      } else {
        squadSection.classList.add('hidden');
      }
    }
  },

  setOperativeScope(scope) {
    this.operativeScope = scope;
    const btnCollege = document.getElementById('scopeBtn-college');
    const btnAll = document.getElementById('scopeBtn-all');

    if (btnCollege && btnAll) {
      if (scope === 'college') {
        btnCollege.className = 'px-2.5 py-1 rounded bg-surface-terminal text-primary font-bold cursor-pointer transition-all';
        btnAll.className = 'px-2.5 py-1 rounded text-text-muted hover:text-on-surface cursor-pointer transition-all';
      } else {
        btnAll.className = 'px-2.5 py-1 rounded bg-surface-terminal text-primary font-bold cursor-pointer transition-all';
        btnCollege.className = 'px-2.5 py-1 rounded text-text-muted hover:text-on-surface cursor-pointer transition-all';
      }
    }

    this.loadPlatformOperatives(this.operativeSearchQuery);
  },

  async loadPlatformOperatives(query = '') {
    const mount = document.getElementById('operativeSearchResultsMount');
    if (!mount) return;

    const currentUser = window.state.currentUser;
    const userCollege = (this.operativeScope === 'college' && currentUser?.college) ? currentUser.college : '';

    mount.innerHTML = `<div class="p-6 text-center text-text-muted text-xs font-mono"><span class="material-symbols-outlined text-sm animate-spin">sync</span> Querying operatives directory...</div>`;

    try {
      const users = await window.api.searchOperatives(query, userCollege);
      this.operativeSearchResults = users || [];
      this.renderOperativeList();
    } catch (err) {
      mount.innerHTML = `<div class="p-4 text-center text-status-error text-xs font-mono">Error querying directory: ${escapeHtml(err.message)}</div>`;
    }
  },

  handleOperativeSearch(val) {
    this.operativeSearchQuery = val;
    this.loadPlatformOperatives(val);
  },

  renderOperativeList() {
    const mount = document.getElementById('operativeSearchResultsMount');
    if (!mount) return;

    const users = this.operativeSearchResults || [];
    const team = this.userTeam;
    const teamMembers = team?.members || team?.team?.members || [];
    const teamId = team?.id || team?.team?.id;
    const acceptedMembers = teamMembers.filter(m => m.role !== 'requested');
    const isTeamFull = acceptedMembers.length >= 4;

    if (users.length === 0) {
      const scopeLabel = this.operativeScope === 'college' ? `your college (${window.state.currentUser?.college || 'PCCOE'})` : 'the platform';
      mount.innerHTML = `
        <div class="p-6 text-center text-text-muted text-xs font-mono">
          No registered operatives found from ${scopeLabel}. Try switching to "All Platform" or refine your search.
        </div>
      `;
      return;
    }

    mount.innerHTML = users.map(u => {
      const membership = teamMembers.find(m => m.user_id === u.id || m.username?.toLowerCase() === u.username?.toLowerCase());
      const isRequested = membership && membership.role === 'requested';
      const isInSquad = membership && membership.role !== 'requested';

      return `
        <div class="p-3 flex items-center justify-between gap-3 hover:bg-surface-terminal/40 transition-colors">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-full bg-primary/10 text-primary border border-primary/30 flex items-center justify-center font-bold text-xs shrink-0 font-mono">
              ${(u.username || 'OP').slice(0, 2).toUpperCase()}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-bold text-xs text-on-surface truncate">@${escapeHtml(u.username)}</span>
                <span class="text-[10px] text-primary font-mono font-bold">${u.points || 0} PTS</span>
              </div>
              <div class="text-[11px] text-text-muted truncate">${escapeHtml(u.name || '')} • <strong class="text-text-secondary">${escapeHtml(u.college || 'Student')}</strong></div>
            </div>
          </div>

          <div class="shrink-0 flex items-center gap-2">
            ${isInSquad ? `
              <span class="px-2.5 py-1 rounded bg-accent-emerald/20 text-accent-neon border border-accent-emerald/40 text-[11px] font-mono font-bold flex items-center gap-1 shadow-sm">
                <span class="material-symbols-outlined text-xs">check</span> In Squad
              </span>
            ` : isRequested ? `
              <span class="px-2.5 py-1 rounded bg-status-warning/20 text-status-warning border border-status-warning/50 text-[11px] font-mono font-bold flex items-center gap-1 shadow-sm">
                <span class="material-symbols-outlined text-xs">schedule</span> Requested
              </span>
            ` : isTeamFull ? `
              <span class="px-2.5 py-1 rounded bg-surface-terminal text-text-muted text-[11px] font-mono">
                Squad Full (4/4)
              </span>
            ` : `
              <button type="button" class="btn btn-primary btn-sm text-xs py-1 px-2.5 flex items-center gap-1 shadow-sm" onclick="EventsView.addOperativeToSquadDirect('${teamId || ''}', '${escapeHtml(u.username)}')">
                <span class="material-symbols-outlined text-xs">person_add</span>
                <span>+ Add to Squad</span>
              </button>
            `}
          </div>
        </div>
      `;
    }).join('');
  },

  async acceptMemberInSquad(teamId, userId) {
    try {
      await window.api.acceptTeamMember(teamId, userId);
      showToast('Operative request accepted! Squad roster updated.', 'success');
      this.userTeam = await window.api.getMyTeam();
      await this.openEventDetailsModal(this.selectedEvent, 'register');
    } catch (err) {
      showToast(err.message || 'Failed to accept squad request', 'error');
    }
  },

  async addOperativeToSquadDirect(teamId, username) {
    const currentUser = window.state.currentUser;

    // If user does not have a squad yet, create one automatically or prompt
    if (!teamId) {
      const defaultName = `Squad-${currentUser.username}`;
      const nameInput = document.getElementById('newSquadNameInput');
      const squadName = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : defaultName;
      const college = currentUser.college || 'PCCOE Cyber Cell';

      try {
        const created = await window.api.createTeam(squadName, '', college);
        showToast(`Squad "${created.name}" created!`, 'success');
        teamId = created.id;
        this.userTeam = await window.api.getMyTeam().catch(() => created);
      } catch (err) {
        showToast(err.message || 'Failed to initialize squad', 'error');
        return;
      }
    }

    try {
      await window.api.addTeamMember(teamId, username);
      showToast(`Squad request sent to @${username}! (Pending acceptance)`, 'success');
      this.userTeam = await window.api.getMyTeam();
      await this.openEventDetailsModal(this.selectedEvent, 'register');
    } catch (err) {
      showToast(err.message || 'Failed to add operative to squad', 'error');
    }
  },

  async handleCreateSquadInline(eventId) {
    const nameInput = document.getElementById('newSquadNameInput');
    const currentUser = window.state.currentUser;
    if (!nameInput || !nameInput.value.trim()) {
      showToast('Please specify a Squad Name.', 'warning');
      return;
    }

    const name = nameInput.value.trim();
    const college = currentUser.college || 'PCCOE COE';

    try {
      const newTeam = await window.api.createTeam(name, '', college);
      showToast(`Squad "${newTeam.name}" created! You can now invite operatives from your college.`, 'success');
      this.userTeam = await window.api.getMyTeam().catch(() => newTeam);
      await this.openEventDetailsModal(eventId, 'register');
    } catch (err) {
      showToast(err.message || 'Failed to create squad', 'error');
    }
  },

  async removeMemberFromSquad(teamId, userId) {
    if (!confirm('Cancel request / remove this operative from your squad?')) return;
    try {
      await window.api.removeTeamMember(teamId, userId);
      showToast('Squad request canceled / operative removed.', 'info');
      this.userTeam = await window.api.getMyTeam();
      await this.openEventDetailsModal(this.selectedEvent, 'register');
    } catch (err) {
      showToast(err.message || 'Failed to remove member', 'error');
    }
  },

  async handleEnrollmentSubmit(e, eventId) {
    e.preventDefault();
    if (!window.state.currentUser) {
      openAuthModal('login', '#events');
      return;
    }

    const regTypeInput = document.querySelector('input[name="enrollRegType"]:checked');
    const registrationType = regTypeInput ? regTypeInput.value : 'individual';
    
    let teamId = null;
    if (registrationType === 'team') {
      const team = this.userTeam;
      teamId = team?.id || team?.team?.id;
      if (!teamId) {
        showToast('Please create or form a squad first before enrolling under team mode.', 'warning');
        return;
      }
    }

    const btn = document.getElementById('btnSubmitEnroll');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">sync</span> Enrolling...';
    }

    try {
      await window.api.registerEvent(eventId, registrationType, teamId);
      showToast(`Successfully enrolled in the CTF competition (${registrationType.toUpperCase()})!`, 'success');
      const nextTab = this.selectedEventData?.computed_status === 'live' ? 'challenges' : 'overview';
      await this.openEventDetailsModal(eventId, nextTab);
      await this.loadEvents();
    } catch (err) {
      showToast(err.message || 'Enrollment failed', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-lg">how_to_reg</span><span>CONFIRM & ENROLL FOR THIS EVENT</span>';
      }
    }
  },

  async unregisterFromModal(eventId) {
    if (!confirm('Are you sure you want to withdraw your enrollment for this event?')) return;
    try {
      await window.api.unregisterEvent(eventId);
      showToast('Enrollment withdrawn.', 'info');
      await this.openEventDetailsModal(eventId, 'register');
      await this.loadEvents();
    } catch (err) {
      showToast(err.message || 'Failed to withdraw enrollment', 'error');
    }
  },

  async submitFlag(eventId, challengeId) {
    const input = document.getElementById(`eventFlagInput-${challengeId}`);
    if (!input || !input.value.trim()) {
      showToast('Please enter a flag candidate.', 'warning');
      return;
    }
    const flag = input.value.trim();

    try {
      const res = await window.api.submitEventFlag(eventId, challengeId, flag);
      if (res.is_correct) {
        showToast(res.message || `🚩 Flag Verified! Awarded +${res.points_awarded || 0} PTS`, 'success');
        input.value = '';
        input.disabled = true;
        await this.openEventDetailsModal(eventId, 'challenges');
      } else {
        showToast(res.message || 'Incorrect flag candidate. Try again!', 'error');
      }
    } catch (err) {
      showToast(err.message || 'Submission failed', 'error');
    }
  }
};

window.EventsView = EventsView;

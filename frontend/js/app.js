/**
 * OWASP CTF Platform — Master Application Bootstrap & Router
 * Stitch "Obsidian Signal" Architecture
 */

const App = {
  views: ['landing', 'challenges', 'events', 'leaderboard', 'teams', 'profile', 'admin'],
  eventTickerInterval: null,

  async init() {
    this.setupEventListeners();
    await this.restoreSession();
    await this.loadInitialData();
    this.route();
    this.pollNotifications();
    this.setupEventHeaderTicker();
  },

  async loadInitialData() {
    try {
      const cats = await window.api.getCategories();
      if (Array.isArray(cats) && cats.length > 0) {
        window.state.categories = cats;
      }
    } catch (e) {
      console.warn('Initial categories fetch failed:', e);
    }
  },

  setupEventListeners() {
    window.addEventListener('hashchange', () => this.route());

    window.addEventListener('auth-changed', async (e) => {
      window.state.currentUser = e.detail;
      await this.updateNavbarUserUI();
      this.route();
      this.pollNotifications();
    });

    window.addEventListener('session-expired', () => {
      showToast('Your session has expired. Please log in again.', 'warning');
      this.updateNavbarUserUI();
      window.location.hash = '#landing';
    });

    // Mobile menu toggle
    const hamburger = document.getElementById('hamburgerToggle');
    const sidebar = document.getElementById('mainSidebar');
    if (hamburger && sidebar) {
      hamburger.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
      if (sidebar && sidebar.classList.contains('mobile-open')) {
        if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
          sidebar.classList.remove('mobile-open');
        }
      }
    });

    // Guard: Intercept clicks on tactical feature links and buttons when unauthenticated
    document.addEventListener('click', (e) => {
      if (window.state && window.state.currentUser) return;

      const link = e.target.closest('a[href^="#"], [data-feature-route]');
      if (!link) return;

      const target = link.getAttribute('href') || link.getAttribute('data-feature-route');
      if (target && target !== '#landing' && target !== '#') {
        e.preventDefault();
        e.stopPropagation();
        if (window.state) window.state.redirectAfterLogin = target;
        if (typeof openModal === 'function') openModal('authModal');
        if (typeof showToast === 'function') {
          showToast('Authentication required. Please log in or register to access this operational feature.', 'warning');
        }
      }
    });
  },

  async restoreSession() {
    const token = window.api.getToken();
    if (!token) {
      this.updateNavbarUserUI();
      return;
    }

    try {
      const user = await window.api.getMe();
      window.state.currentUser = user;
    } catch (e) {
      window.api.setToken('');
      window.state.currentUser = null;
    }
    await this.updateNavbarUserUI();
  },

  async updateNavbarUserUI() {
    const user = window.state.currentUser;
    const authCluster = document.getElementById('navAuthCluster');
    const adminNavSection = document.getElementById('adminNavSection');

    if (user) {
      const isAdminOrMod = user.role === 'admin' || user.role === 'moderator';
      if (adminNavSection) {
        adminNavSection.style.display = isAdminOrMod ? 'block' : 'none';
      }

      // Fetch score and team for header pill if available
      let userScore = 0;
      let userRank = '#—';

      try {
        const [scoreData, rankData] = await Promise.all([
          window.api.getMyScore().catch(() => null),
          window.api.request('/api/leaderboard/me').catch(() => null)
        ]);
        if (scoreData) {
          userScore = scoreData.total_points ?? scoreData.score ?? 0;
        }
        if (rankData) {
          const r = rankData.global_rank ?? rankData.rank;
          if (r) userRank = `#${r}`;
          if (typeof rankData.total_points === 'number') userScore = rankData.total_points;
        }
      } catch (err) {
        // Fallback to defaults
      }

      if (authCluster) {
        authCluster.innerHTML = `
          <button type="button" 
                  onclick="window.location.hash = '#profile'" 
                  class="nav-profile-pill group" 
                  title="Operative Dossier &amp; Profile">
            <!-- Tactical Glowing Avatar -->
            <div class="relative shrink-0 flex items-center justify-center">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-[#10B981]/35 to-[#091511] border-2 border-[#00FF9D] text-[#00FF9D] flex items-center justify-center font-mono text-sm font-black shadow-[0_0_10px_rgba(0,255,157,0.45)] group-hover:scale-105 transition-transform overflow-hidden">
                ${user.avatar_url 
                  ? `<img src="${escapeHtml(user.avatar_url)}" alt="Avatar" class="w-full h-full object-cover" onerror="this.remove()">` 
                  : escapeHtml((user.name || user.username)[0].toUpperCase())
                }
              </div>
              <span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#00FF9D] shadow-[0_0_8px_#00FF9D] border-2 border-[#090D0C]"></span>
            </div>

            <!-- Identity & Tactical Metrics -->
            <div class="flex flex-col text-left min-w-0 justify-center">
              <div class="flex items-center gap-2 leading-none">
                <span class="font-mono text-xs font-bold text-white group-hover:text-[#00FF9D] transition-colors truncate max-w-[130px]">
                  ${escapeHtml(user.name || user.username)}
                </span>
                <span class="inline-flex items-center px-1.5 py-0.5 bg-[#10B981]/25 text-[#00FF9D] border border-[#10B981]/70 rounded text-[10px] font-mono font-black uppercase tracking-wider">
                  ${escapeHtml(user.role)}
                </span>
              </div>
              <div class="flex items-center gap-2 pt-1.5 text-xs font-mono leading-none font-semibold">
                <span class="text-[#00FF9D] font-bold">${userScore.toLocaleString()} pts</span>
                <span class="text-[#10B981]/70 text-[9px]">&bull;</span>
                <span class="text-[#4cd7f6]">${userRank}</span>
              </div>
            </div>

            <!-- Action Chevron -->
            <span class="material-symbols-outlined text-[#00FF9D]/90 group-hover:text-[#00FF9D] group-hover:translate-x-0.5 transition-all text-lg shrink-0">
              chevron_right
            </span>
          </button>

          <!-- Terminate Session Action -->
          <button type="button" 
                  class="nav-logout-btn" 
                  onclick="App.handleLogout()" 
                  title="Terminate Session / Disconnect"
                  aria-label="Terminate Session">
            <span class="material-symbols-outlined text-lg">logout</span>
          </button>
        `;
      }
    } else {
      if (adminNavSection) adminNavSection.style.display = 'none';

      if (authCluster) {
        authCluster.innerHTML = `
          <!-- Google SSO Quick Auth -->
          <button type="button" 
                  onclick="handleGoogleSSO()" 
                  class="btn btn-outline btn-sm flex items-center gap-2 bg-surface-terminal hover:bg-surface-card border-border-grid hover:border-primary transition-all px-3 py-1.5 shadow-sm text-text-primary" 
                  title="Authenticate via Collegiate Google SSO">
            <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <span class="font-code-sm font-semibold text-xs hidden sm:inline">Google SSO</span>
          </button>

          <!-- Standard Authenticate Modal Trigger -->
          <button type="button" 
                  class="btn btn-primary btn-sm flex items-center gap-1.5 px-3.5 py-1.5 shadow-[0_0_12px_rgba(16,185,129,0.35)]" 
                  onclick="openAuthModal('login')">
            <span class="material-symbols-outlined text-base">login</span>
            <span>Authenticate</span>
          </button>
        `;
      }
    }
  },

  async setupEventHeaderTicker() {
    try {
      const events = await window.api.getEvents();
      if (!Array.isArray(events) || events.length === 0) return;

      const liveEvent = events.find(e => e.computed_status === 'live') || events.find(e => e.computed_status === 'upcoming') || events[0];
      if (!liveEvent) return;

      const banner = document.getElementById('headerEventBanner');
      const timerEl = document.getElementById('headerEventTimer');
      if (!banner || !timerEl) return;

      const updateTicker = () => {
        const isLive = liveEvent.computed_status === 'live';
        const isEnded = liveEvent.computed_status === 'ended';
        const targetDate = isLive ? liveEvent.end_at : liveEvent.start_at;

        if (isEnded) {
          timerEl.textContent = 'CONCLUDED';
          banner.classList.remove('border-border-grid');
          banner.classList.add('border-border-subtle');
          return;
        }

        const prefix = isLive ? 'LIVE • ' : 'UPCOMING • ';
        timerEl.textContent = `${prefix}${formatCountdown(targetDate)}`;
      };

      updateTicker();
      if (this.eventTickerInterval) clearInterval(this.eventTickerInterval);
      this.eventTickerInterval = setInterval(updateTicker, 1000);
    } catch (e) {
      // Non-blocking
    }
  },

  route() {
    let rawHash = window.location.hash.replace('#', '').trim();
    if (!rawHash) {
      rawHash = window.state.currentUser ? 'challenges' : 'landing';
    }

    let searchParams = null;
    if (rawHash.includes('?')) {
      const qIndex = rawHash.indexOf('?');
      const qs = rawHash.slice(qIndex + 1);
      rawHash = rawHash.slice(0, qIndex);
      searchParams = new URLSearchParams(qs);
    }

    // Parse subroutes, e.g. "challenges/abc-123" or "challenge/abc-123"
    const routeParts = rawHash.split('/');
    let primaryRoute = routeParts[0] || 'landing';
    const routeParam = routeParts.slice(1).join('/');

    if (primaryRoute === 'challenge' || primaryRoute === 'dashboard') {
      primaryRoute = 'challenges';
    }

    // Auth Guard: If unauthenticated operative attempts to access any feature/view other than landing
    if (!window.state.currentUser && primaryRoute !== 'landing') {
      window.state.redirectAfterLogin = window.location.hash || `#${rawHash}${searchParams ? `?${searchParams.toString()}` : ''}`;
      if (window.location.hash !== '#landing') {
        history.replaceState(null, '', '#landing');
      }
      primaryRoute = 'landing';
      if (typeof openModal === 'function') openModal('authModal');
      if (typeof showToast === 'function') {
        showToast('Authentication required. Please log in or register to access this operational feature.', 'warning');
      }
    }

    const viewName = this.views.includes(primaryRoute) ? primaryRoute : 'landing';

    window.state.activeView = viewName;

    // Reset container for the selected view
    const activeEl = document.getElementById('view-active-container');
    if (!activeEl) return;
    activeEl.innerHTML = `<div id="view-${viewName}" class="w-full"></div>`;

    // Highlight active nav link in Stitch Obsidian Signal style
    const activeClasses = ['bg-primary-container', 'text-on-primary-container', 'font-code-md', 'text-code-md', 'rounded-lg', 'shadow-[0_0_12px_#10B98133]'];
    const defaultClasses = ['text-on-surface-variant', 'hover:bg-surface-terminal', 'hover:text-on-surface'];

    document.querySelectorAll('#mainSidebar nav a').forEach(l => {
      l.classList.remove(...activeClasses);
      l.classList.add(...defaultClasses);

      if (l.getAttribute('href') === `#${viewName}` || (viewName === 'challenges' && l.getAttribute('href') === '#challenges')) {
        l.classList.remove(...defaultClasses);
        l.classList.add(...activeClasses);
      }
    });

    // Close mobile nav drawer if open
    const sidebar = document.getElementById('mainSidebar');
    if (sidebar) sidebar.classList.remove('mobile-open');

    // Initialize View Controller
    switch (viewName) {
      case 'landing':
        if (window.LandingView) window.LandingView.init();
        break;
      case 'challenges':
        if (window.ChallengesView) window.ChallengesView.init(routeParam, searchParams);
        break;
      case 'events':
        if (window.EventsView) window.EventsView.init();
        break;
      case 'leaderboard':
        if (window.LeaderboardView) window.LeaderboardView.init();
        break;
      case 'teams':
        if (window.TeamsView) window.TeamsView.init(searchParams);
        break;
      case 'profile':
        if (window.ProfileView) window.ProfileView.init();
        break;
      case 'admin':
        if (window.AdminView) window.AdminView.init();
        break;
    }

    window.scrollTo({ top: 0, behavior: 'instant' });
  },

  async pollNotifications() {
    if (!window.state.currentUser) return;
    try {
      const notifs = await window.api.getNotifications(true);
      const unreadCount = Array.isArray(notifs) ? notifs.length : 0;
      const badge = document.getElementById('notifBadgeCounter');
      if (badge) {
        if (unreadCount > 0) {
          badge.style.display = 'flex';
          badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
        } else {
          badge.style.display = 'none';
        }
      }
    } catch (e) {
      // Background poll silently fails
    }
  },

  handleLogout() {
    window.api.logout();
    showToast('Session terminated.', 'info');
    window.location.hash = '#landing';
  }
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

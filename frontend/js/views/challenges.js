/**
 * OWASP CTF Platform — Challenge Arena & Standalone Detail Workspace
 * Stitch Screen: "Challenge Workspace & Flag Terminal"
 */

const ChallengesView = {
  challenges: [],
  categories: [],
  selectedCategory: '',
  selectedDifficulty: '',
  searchQuery: '',
  filterSolved: '',
  currentChallenge: null,
  routeChallengeId: null,
  totalChallengesCount: 0,

  getCategoryIcon(name) {
    if (!name) return 'security';
    const n = name.toLowerCase();
    if (n.includes('web')) return 'language';
    if (n.includes('crypto')) return 'vpn_key';
    if (n.includes('reverse')) return 'terminal';
    if (n.includes('pwn') || n.includes('binary')) return 'memory';
    if (n.includes('forensic')) return 'saved_search';
    if (n.includes('osint')) return 'travel_explore';
    if (n.includes('stego')) return 'visibility_off';
    if (n.includes('ai') || n.includes('ml')) return 'psychology';
    if (n.includes('blockchain') || n.includes('web3')) return 'token';
    if (n.includes('general') || n.includes('misc')) return 'extension';
    return 'security';
  },

  findCategoryMatch(query) {
    if (!query || !this.categories || this.categories.length === 0) return null;
    const q = query.toString().trim().toLowerCase().replace(/[-_]/g, ' ');

    // 1. Direct ID match
    const byId = this.categories.find(c => c.id === query || c.id === q);
    if (byId) return byId;

    // 2. Exact Name match (case-insensitive)
    const exact = this.categories.find(c => c.name.toLowerCase() === q);
    if (exact) return exact;

    // 3. Known Aliases Map for CTF Types
    const aliasMap = {
      'web': ['web', 'web exploitation', 'web exploit', 'web exploration', 'web app'],
      'crypto': ['crypto', 'cryptography', 'cipher', 'ciphers', 'encryption'],
      'reverse': ['reverse', 'reverse engineering', 'reversing', 'rev', 'decompilation', 'disassembly'],
      'pwn': ['binary', 'binary exploitation', 'pwn', 'pwn / binary exploitation', 'memory corruption', 'buffer overflow'],
      'forensics': ['forensics', 'forensic', 'artifact', 'pcap', 'packet analysis'],
      'general': ['general', 'general skills', 'basics', 'foundational', 'cli', 'bash', 'terminal'],
      'ai': ['ai', 'ml', 'ai ml', 'ai & ml', 'machine learning', 'neural'],
      'blockchain': ['blockchain', 'web3', 'crypto currency', 'solidity', 'smart contracts'],
      'osint': ['osint', 'intel', 'open source intelligence', 'recon'],
      'stego': ['stego', 'steganography']
    };

    for (const [key, aliases] of Object.entries(aliasMap)) {
      const matchesQuery = aliases.some(a => q === a || q.includes(a) || a.includes(q));
      if (matchesQuery) {
        const matched = this.categories.find(c => {
          const cName = c.name.toLowerCase();
          return aliases.some(a => cName === a || cName.includes(a) || a.includes(cName));
        });
        if (matched) return matched;
      }
    }

    // 4. Substring match
    const sub = this.categories.find(c => {
      const cName = c.name.toLowerCase();
      return cName.includes(q) || q.includes(cName);
    });
    if (sub) return sub;

    // 5. Fallback for General Skills -> Misc
    if (q.includes('general') || q.includes('skill')) {
      const misc = this.categories.find(c => c.name.toLowerCase().includes('misc'));
      if (misc) return misc;
    }

    // 6. Fallback for AI & ML / Blockchain -> Misc
    if (q.includes('ai') || q.includes('ml') || q.includes('blockchain') || q.includes('web3')) {
      const misc = this.categories.find(c => c.name.toLowerCase().includes('misc'));
      if (misc) return misc;
    }

    return null;
  },

  async init(routeParam, searchParams = null) {
    this.routeChallengeId = routeParam ? routeParam.trim() : null;

    if (this.routeChallengeId) {
      // Standalone Dedicated Challenge Workspace (Opened in new browser tab)
      await this.renderStandaloneChallenge(this.routeChallengeId);
    } else {
      const categoryQuery = searchParams ? (searchParams.get('category') || searchParams.get('type')) : null;
      // Main Horizontal Challenge Browsing Listing
      this.renderListing();
      await this.loadCategories(categoryQuery);
      await this.loadChallenges();
    }
  },

  // ---------------------------------------------------------------------------
  // 1. HORIZONTAL CHALLENGE BROWSING LISTING (#challenges)
  // ---------------------------------------------------------------------------
  renderListing() {
    const container = document.getElementById('view-challenges');
    if (!container) return;

    container.innerHTML = `
      <div class="p-space-lg space-y-space-md max-w-[1720px] mx-auto w-full">
        
        <!-- TOP FILTER & SEARCH MATRIX -->
        <div class="bg-surface-card rounded-xl p-space-md shadow-xl border border-border-grid space-y-space-sm relative overflow-hidden">
          <div class="absolute -right-16 -top-16 w-56 h-56 bg-primary-container/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <!-- Upper Row: Category Pills and Search/Status -->
          <div class="flex flex-wrap items-center justify-between gap-space-sm relative z-10">
            
            <!-- Category Selector Pills -->
            <div id="challCategoryPills" class="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
              <button class="px-space-sm py-1 rounded bg-primary-container text-on-primary-container font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 shadow-sm" onclick="ChallengesView.handleCategoryFilter('', this)">
                <span class="material-symbols-outlined text-sm">grid_view</span>
                <span>All Vectors</span>
                <span id="challTotalCountBadge" class="bg-on-primary-container/20 px-1 rounded text-primary-fixed">0</span>
              </button>
            </div>

            <!-- Solve Status Filters -->
            <div class="flex items-center gap-1 bg-surface-container p-1 rounded-lg">
              <button id="statusBtn-all" class="px-2.5 py-1 rounded bg-surface-terminal text-primary font-code-sm text-code-sm font-semibold flex items-center gap-1 cursor-pointer" onclick="ChallengesView.handleSolvedFilter('', this)">
                <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>All
              </button>
              <button id="statusBtn-unsolved" class="px-2.5 py-1 rounded text-text-muted hover:text-on-surface font-code-sm text-code-sm transition-colors cursor-pointer" onclick="ChallengesView.handleSolvedFilter('unsolved', this)">
                Unsolved
              </button>
              <button id="statusBtn-solved" class="px-2.5 py-1 rounded text-text-muted hover:text-on-surface font-code-sm text-code-sm transition-colors flex items-center gap-1 cursor-pointer" onclick="ChallengesView.handleSolvedFilter('solved', this)">
                <span class="material-symbols-outlined text-xs text-primary">check_circle</span>Solved
              </button>
            </div>
          </div>

          <!-- Lower Row: Difficulty Tiers & Search Metrics -->
          <div class="flex flex-wrap items-center justify-between gap-space-sm pt-space-xs border-t border-border-subtle">
            <div class="flex flex-wrap items-center gap-space-xs text-text-muted">
              <span class="font-label-sm text-label-sm uppercase text-text-secondary mr-2 tracking-widest">TIER FILTER:</span>
              <button class="px-2 py-0.5 rounded bg-surface-container text-primary font-code-sm text-code-sm active cursor-pointer" onclick="ChallengesView.handleDifficultyFilter('', this)">All Tiers</button>
              <button class="px-2 py-0.5 rounded bg-surface-container-lowest hover:bg-surface-container text-on-surface-variant font-code-sm text-code-sm flex items-center gap-1 cursor-pointer" onclick="ChallengesView.handleDifficultyFilter('easy', this)">
                <span class="w-1.5 h-1.5 rounded-full bg-accent-emerald"></span>Easy (1-50)
              </button>
              <button class="px-2 py-0.5 rounded bg-surface-container-lowest hover:bg-surface-container text-on-surface-variant font-code-sm text-code-sm flex items-center gap-1 cursor-pointer" onclick="ChallengesView.handleDifficultyFilter('medium', this)">
                <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>Medium (50-100)
              </button>
              <button class="px-2 py-0.5 rounded bg-surface-container-lowest hover:bg-surface-container text-on-surface-variant font-code-sm text-code-sm flex items-center gap-1 cursor-pointer" onclick="ChallengesView.handleDifficultyFilter('hard', this)">
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>Hard (100-200)
              </button>
            </div>

            <div class="flex items-center gap-space-md text-text-muted font-code-sm text-code-sm">
              <div class="flex items-center gap-1.5 text-primary">
                <span class="material-symbols-outlined text-base text-primary">dynamic_feed</span>
                <span class="font-semibold text-xs tracking-wider uppercase">Dynamic Scoring Active</span>
              </div>
              <div class="h-9 w-px bg-border-subtle hidden sm:block"></div>
              <div class="flex flex-col items-end gap-1">
                <!-- Line 1: Number of questions solved & Progress Bar -->
                <div class="flex items-center gap-2">
                  <span id="challProgressText" class="text-on-surface font-bold font-mono">0/24 Solved</span>
                  <div class="w-28 h-2 bg-surface-terminal rounded-full overflow-hidden border border-border-subtle/60">
                    <div id="challProgressBar" class="h-full bg-gradient-to-r from-primary to-accent-neon transition-all" style="width: 0%;"></div>
                  </div>
                </div>
                <!-- Line 2: Total score of points below number of questions solved -->
                <div class="flex items-center gap-1 text-xs font-mono">
                  <span class="text-text-muted">Total Score:</span>
                  <span id="challUserScoreBadge" class="text-accent-neon font-bold text-sm">0 PTS</span>
                  <span id="challTotalPoolBadge" class="text-text-muted text-[11px]">/ 0 Pool</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- CHALLENGES GRID (4 CHALLENGES PER ROW) -->
        <div class="space-y-space-sm">
          <div class="flex items-center justify-between px-space-xs">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-headline-sm text-headline-sm text-on-surface tracking-tight font-bold">Active Vector Feed</span>
              <span class="bg-surface-container px-2 py-0.5 rounded text-primary font-code-sm text-code-sm font-semibold">LIVE FEED</span>
              <span id="activeCategoryFilterBadge" class="hidden items-center gap-1.5 px-2.5 py-0.5 rounded bg-primary-container/30 border border-primary/40 text-primary font-code-sm text-xs font-semibold"></span>
            </div>
            
            <span class="font-code-sm text-code-sm text-text-muted">CLICK ANY CHALLENGE TO OPEN IN NEW TAB</span>
          </div>

          <!-- 4 Challenges per row responsive grid -->
          <div id="challengesListFeed" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
            <div class="col-span-full text-text-muted font-code-sm text-center py-12 bg-surface-card rounded-xl border border-border-subtle">
              Initializing vector stream...
            </div>
          </div>
        </div>

      </div>
    `;
  },

  async loadCategories(categoryQuery = null) {
    try {
      this.categories = await window.api.getCategories();
      window.state.categories = this.categories;

      if (categoryQuery) {
        const matched = this.findCategoryMatch(categoryQuery);
        if (matched) {
          this.selectedCategory = matched.id;
        } else {
          this.selectedCategory = '';
        }
      } else if (!this.selectedCategory) {
        this.selectedCategory = '';
      }

      const pillsContainer = document.getElementById('challCategoryPills');
      if (!pillsContainer) return;

      pillsContainer.innerHTML = `
        <button class="px-space-sm py-1 rounded ${!this.selectedCategory ? 'bg-primary-container text-on-primary-container shadow-sm' : 'bg-surface-terminal/80 text-on-surface-variant hover:text-on-surface'} font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap" onclick="ChallengesView.handleCategoryFilter('', this)">
          <span class="material-symbols-outlined text-sm">grid_view</span>
          <span>All Vectors</span>
          <span id="challTotalCountBadge" class="bg-on-primary-container/20 px-1 rounded text-primary-fixed">${this.totalChallengesCount || 0}</span>
        </button>
        ${this.categories.map(c => {
          const icon = this.getCategoryIcon(c.name);
          const isSelected = this.selectedCategory === c.id;
          return `
            <button class="px-space-sm py-1 rounded ${isSelected ? 'bg-primary-container text-on-primary-container shadow-sm' : 'bg-surface-terminal/80 text-on-surface-variant hover:text-on-surface'} font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap" onclick="ChallengesView.handleCategoryFilter('${c.id}', this)">
              <span class="material-symbols-outlined text-sm">${icon}</span>
              <span>${escapeHtml(c.name)}</span>
            </button>
          `;
        }).join('')}
      `;

      // Auto-scroll the active pill into visible container view if needed
      const activePill = pillsContainer.querySelector('.bg-primary-container');
      if (activePill) {
        activePill.scrollIntoView({ inline: 'nearest', behavior: 'smooth' });
      }
    } catch (e) {
      console.warn('Categories load error:', e);
    }
  },

  async loadChallenges() {
    const feed = document.getElementById('challengesListFeed');
    if (!feed) return;

    try {
      const [challenges, scoreData] = await Promise.all([
        window.api.getChallenges(this.selectedCategory, this.selectedDifficulty),
        window.api.getMyScore().catch(() => null)
      ]);
      this.challenges = challenges;
      this.userScore = scoreData ? (scoreData.total_points ?? scoreData.score ?? 0) : 0;
      this.renderFilteredFeed();
    } catch (e) {
      feed.innerHTML = `<div class="w-full text-status-error font-code-sm p-6 bg-surface-card rounded-xl border border-status-error/30">Error loading challenges: ${escapeHtml(e.message)}</div>`;
    }
  },

  renderFilteredFeed() {
    const feed = document.getElementById('challengesListFeed');
    if (!feed) return;

    let items = [...this.challenges];

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      items = items.filter(c => c.title.toLowerCase().includes(q) || (c.category_name && c.category_name.toLowerCase().includes(q)));
    }

    if (this.filterSolved === 'solved') {
      items = items.filter(c => c.is_solved);
    } else if (this.filterSolved === 'unsolved') {
      items = items.filter(c => !c.is_solved);
    }

    // Update Header counters & progress
    if (!this.selectedCategory) {
      this.totalChallengesCount = this.challenges.length;
    }
    const totalBadge = document.getElementById('challTotalCountBadge');
    if (totalBadge) totalBadge.textContent = this.totalChallengesCount || this.challenges.length;

    // Update active category filter tag next to live feed title
    const activeBadge = document.getElementById('activeCategoryFilterBadge');
    if (activeBadge) {
      if (this.selectedCategory) {
        const cat = this.categories.find(c => c.id === this.selectedCategory);
        const catName = cat ? cat.name : 'Filtered';
        activeBadge.innerHTML = `
          <span class="font-mono uppercase">// VECTOR: ${escapeHtml(catName)} (${items.length} LABS)</span>
          <button type="button" onclick="ChallengesView.handleCategoryFilter('', null); document.querySelector('#challCategoryPills button')?.click();" class="ml-1 px-1.5 py-0.5 rounded bg-surface-terminal text-primary hover:text-white hover:bg-primary-container text-[11px] font-bold cursor-pointer" title="Reset to All Vectors">✕ CLEAR</button>
        `;
        activeBadge.classList.remove('hidden');
        activeBadge.classList.add('inline-flex');
      } else {
        activeBadge.classList.add('hidden');
        activeBadge.classList.remove('inline-flex');
      }
    }

    const totalPointsPool = this.challenges.reduce((sum, c) => sum + (c.points || 0), 0);
    const scoreBadge = document.getElementById('challUserScoreBadge');
    const totalPoolBadge = document.getElementById('challTotalPoolBadge');
    if (scoreBadge && this.userScore !== undefined) {
      scoreBadge.textContent = `${this.userScore.toLocaleString()} PTS`;
    }
    if (totalPoolBadge) {
      totalPoolBadge.textContent = `/ ${totalPointsPool.toLocaleString()} Pool`;
    }

    const solvedCount = this.challenges.filter(c => c.is_solved).length;
    const progressText = document.getElementById('challProgressText');
    const progressBar = document.getElementById('challProgressBar');
    if (progressText) progressText.textContent = `${solvedCount}/${this.challenges.length} Solved`;
    if (progressBar) {
      const pct = this.challenges.length > 0 ? ((solvedCount / this.challenges.length) * 100).toFixed(1) : 0;
      progressBar.style.width = `${pct}%`;
    }

    if (items.length === 0) {
      feed.innerHTML = `<div class="col-span-full text-text-muted font-code-sm text-center py-12 bg-surface-card rounded-xl border border-border-subtle">No challenge vectors match criteria.</div>`;
      return;
    }

    feed.innerHTML = items.map(c => {
      const icon = this.getCategoryIcon(c.category_name);
      const diff = (c.difficulty || 'easy').toLowerCase();
      const isSolved = Boolean(c.is_solved);
      const isSurrendered = Boolean(c.is_surrendered || (c.is_solved && c.points_awarded === 0));

      let cardBorder = '';
      let topBarHtml = '';
      let iconBoxClass = '';
      let pointsClass = '';
      let categoryTextClass = '';

      if (isSolved) {
        // Exclusively Golden aesthetic for ALL solved challenges
        cardBorder = 'border-amber-400/80 bg-surface-card/95 shadow-[0_0_20px_rgba(245,158,11,0.22)] hover:border-amber-300 hover:shadow-[0_0_26px_rgba(245,158,11,0.35)]';
        topBarHtml = `<div class="absolute top-0 right-0 left-0 h-1.5 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.6)]"></div>`;
        iconBoxClass = 'bg-surface-terminal text-yellow-300 border-amber-400/50 shadow-[0_0_10px_rgba(245,158,11,0.25)]';
        pointsClass = 'text-yellow-300';
        categoryTextClass = 'text-amber-400';
      } else {
        if (diff === 'hard') {
          // Slightly Red / Crimson-Rose aesthetic for Hard challenges
          cardBorder = 'border-rose-500/35 bg-surface-card hover:border-red-400 hover:shadow-[0_0_24px_rgba(239,68,68,0.35)]';
          topBarHtml = `<div class="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-red-500 via-rose-500 to-red-400 opacity-80 shadow-[0_0_8px_rgba(239,68,68,0.4)]"></div>`;
          iconBoxClass = 'bg-rose-950/30 text-rose-400 border-rose-500/35 group-hover:border-red-400 group-hover:text-rose-300 group-hover:shadow-[0_0_10px_rgba(239,68,68,0.25)]';
          pointsClass = 'text-rose-400';
          categoryTextClass = 'text-rose-400';
        } else if (diff === 'medium') {
          // Cyber Cyan / Blue aesthetic for Medium challenges
          cardBorder = 'border-cyan-500/30 bg-surface-card hover:border-cyan-400 hover:shadow-[0_0_24px_rgba(6,182,212,0.3)]';
          topBarHtml = `<div class="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-cyan-500 via-sky-400 to-blue-500 opacity-80 shadow-[0_0_8px_rgba(6,182,212,0.3)]"></div>`;
          iconBoxClass = 'bg-cyan-950/30 text-cyan-400 border-cyan-500/30 group-hover:border-cyan-400 group-hover:text-cyan-300 group-hover:shadow-[0_0_10px_rgba(6,182,212,0.25)]';
          pointsClass = 'text-cyan-400';
          categoryTextClass = 'text-cyan-400';
        } else {
          // Emerald Green aesthetic for Easy challenges
          cardBorder = 'border-emerald-500/25 bg-surface-card hover:border-emerald-400 hover:shadow-[0_0_24px_rgba(16,185,129,0.25)]';
          topBarHtml = `<div class="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-green-500 opacity-80 shadow-[0_0_8px_rgba(16,185,129,0.3)]"></div>`;
          iconBoxClass = 'bg-emerald-950/30 text-emerald-400 border-emerald-500/30 group-hover:border-emerald-400 group-hover:text-emerald-300 group-hover:shadow-[0_0_10px_rgba(16,185,129,0.25)]';
          pointsClass = 'text-accent-emerald';
          categoryTextClass = 'text-emerald-400';
        }
      }

      return `
        <a href="#challenges/${c.id}" target="_blank" rel="noopener noreferrer" class="relative ${cardBorder} rounded-xl p-space-md hover:-translate-y-1 transition-all duration-200 cursor-pointer overflow-hidden group flex flex-col justify-between w-full min-h-[250px] no-underline">
          ${topBarHtml}
          
          <div class="space-y-space-sm">
            <!-- Card Top Header -->
            <div class="flex items-start justify-between gap-space-sm">
              <div class="flex items-center gap-2.5 min-w-0">
                <div class="p-2.5 rounded-lg shrink-0 border transition-all ${iconBoxClass}">
                  <span class="material-symbols-outlined text-2xl">${icon}</span>
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-code-sm text-code-sm ${categoryTextClass} font-semibold uppercase">${escapeHtml(c.category_name || 'Jeopardy')}</span>
                    ${getDifficultyBadge(c.difficulty)}
                  </div>
                </div>
              </div>

              <div class="text-right shrink-0 space-y-0.5">
                <div class="flex items-center justify-end gap-1.5">
                  ${isSolved ? `
                    <span class="px-2 py-0.5 rounded ${isSurrendered ? 'bg-amber-500/20 text-yellow-300 border border-amber-400/60 shadow-[0_0_8px_rgba(245,158,11,0.3)]' : 'bg-amber-500/25 text-yellow-300 border border-amber-400/70 shadow-[0_0_10px_rgba(245,158,11,0.4)]'} font-mono font-bold text-xs flex items-center gap-1">
                      <span class="material-symbols-outlined text-xs">${isSurrendered ? 'visibility' : 'check_circle'}</span>
                      <span>${isSurrendered ? 'SOLVED (0 PTS)' : '✓ SOLVED'}</span>
                    </span>
                  ` : ''}
                  <span class="font-code-lg text-code-lg ${pointsClass} font-bold font-mono">${c.points} PTS</span>
                </div>
                <span class="font-code-sm text-code-sm text-text-muted flex items-center justify-end gap-1">
                  <span class="material-symbols-outlined text-xs text-status-warning">trending_down</span> Decayed
                </span>
              </div>
            </div>

            <!-- Title & Brief description excerpt -->
            <div>
              <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold line-clamp-1 group-hover:text-primary transition-colors flex items-center gap-1.5 mt-0.5">
                <span>${escapeHtml(c.title)}</span>
                ${isSolved ? `<span class="material-symbols-outlined text-yellow-400 text-lg shrink-0" title="Challenge Solved">check_circle</span>` : ''}
              </h3>
              <p class="font-body-sm text-body-sm text-text-muted line-clamp-3 mt-1 leading-relaxed">
                ${escapeHtml(c.description || 'Target offensive security vector. Click to open challenge workspace in a new browser tab.')}
              </p>
            </div>
          </div>

          <!-- Bottom Metric Bar -->
          <div class="mt-space-md pt-space-xs flex items-center justify-between font-code-sm text-code-sm text-text-muted bg-surface-terminal/50 p-2.5 rounded-lg border border-border-subtle/50">
            <span class="flex items-center gap-1 text-on-surface-variant">
              <span class="material-symbols-outlined text-sm text-primary">groups</span> ${c.solves_count || 0} Solves
            </span>
            <span class="flex items-center gap-1 text-primary truncate max-w-[130px]" title="First Blood: @${escapeHtml(c.first_blood_user || 'None')}">
              <span class="material-symbols-outlined text-sm">workspace_premium</span> @${escapeHtml(c.first_blood_user || 'None')}
            </span>
          </div>
        </a>
      `;
    }).join('');
  },

  handleSearch(val) {
    this.searchQuery = val.trim();
    if (this.routeChallengeId) return;
    this.renderFilteredFeed();
  },

  handleCategoryFilter(catId, btn) {
    this.selectedCategory = catId;
    document.querySelectorAll('#challCategoryPills button').forEach(b => {
      b.className = 'px-space-sm py-1 rounded bg-surface-terminal/80 text-on-surface-variant hover:text-on-surface font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap';
    });
    if (btn) {
      btn.className = 'px-space-sm py-1 rounded bg-primary-container text-on-primary-container font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 shadow-sm cursor-pointer whitespace-nowrap';
    }
    // Update hash cleanly without reloading
    const newHash = catId ? `#challenges?category=${encodeURIComponent(catId)}` : '#challenges';
    if (window.location.hash !== newHash) {
      history.replaceState(null, '', newHash);
    }
    this.loadChallenges();
  },

  selectCategoryByName(name) {
    if (!name) return;
    const matched = this.findCategoryMatch(name);
    if (matched) {
      this.selectedCategory = matched.id;
      const pillsContainer = document.getElementById('challCategoryPills');
      if (pillsContainer) {
        pillsContainer.querySelectorAll('button').forEach(b => {
          b.className = 'px-space-sm py-1 rounded bg-surface-terminal/80 text-on-surface-variant hover:text-on-surface font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap';
        });
        const btn = Array.from(pillsContainer.querySelectorAll('button')).find(b => b.textContent.includes(matched.name));
        if (btn) {
          btn.className = 'px-space-sm py-1 rounded bg-primary-container text-on-primary-container font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1.5 shadow-sm cursor-pointer whitespace-nowrap';
          btn.scrollIntoView({ inline: 'nearest', behavior: 'smooth' });
        }
      }
      const newHash = `#challenges?category=${encodeURIComponent(matched.id)}`;
      if (window.location.hash !== newHash) {
        history.replaceState(null, '', newHash);
      }
      this.loadChallenges();
    }
  },

  handleDifficultyFilter(diff, btn) {
    this.selectedDifficulty = diff;
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('bg-surface-container', 'text-primary'));
      btn.classList.add('bg-surface-container', 'text-primary');
    }
    this.loadChallenges();
  },

  handleSolvedFilter(status, btn) {
    this.filterSolved = status;
    ['all', 'unsolved', 'solved'].forEach(s => {
      const b = document.getElementById(`statusBtn-${s}`);
      if (b) {
        b.className = 'px-2.5 py-1 rounded text-text-muted hover:text-on-surface font-code-sm text-code-sm transition-colors cursor-pointer';
      }
    });
    if (btn) {
      btn.className = 'px-2.5 py-1 rounded bg-surface-terminal text-primary font-code-sm text-code-sm font-semibold flex items-center gap-1 cursor-pointer';
    }
    this.renderFilteredFeed();
  },


  // ---------------------------------------------------------------------------
  // 2. STANDALONE DEDICATED CHALLENGE WORKSPACE (#challenges/{challenge-id})
  // ---------------------------------------------------------------------------
  async renderStandaloneChallenge(challengeId) {
    const container = document.getElementById('view-challenges');
    if (!container) return;

    container.innerHTML = `
      <div class="p-space-lg space-y-space-md max-w-[1280px] mx-auto w-full">
        
        <!-- Top Navigation / Back Bar -->
        <div class="flex flex-wrap items-center justify-between gap-space-sm pb-space-xs border-b border-border-subtle">
          <div class="flex items-center gap-space-sm">
            <a href="#challenges" class="btn btn-outline btn-sm flex items-center gap-1.5">
              <span class="material-symbols-outlined text-base">arrow_back</span>
              <span>Back to Challenges</span>
            </a>
            <div class="h-4 w-px bg-border-subtle"></div>
            <span class="font-code-sm text-code-sm text-text-muted flex items-center gap-1">
              <span>CTF Arena</span>
              <span class="text-primary">&gt;</span>
              <span id="standaloneCategoryBreadcrumb" class="text-secondary uppercase">Vector</span>
            </span>
          </div>

          <div class="flex items-center gap-2">
            <span class="font-code-sm text-code-sm px-2.5 py-1 rounded bg-surface-terminal border border-primary/30 text-primary font-semibold flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span>STANDALONE OPERATIONAL WORKSPACE</span>
            </span>
          </div>
        </div>

        <!-- Standalone Workspace Mount -->
        <div id="standaloneWorkspaceMount" class="space-y-space-md">
          <div class="text-text-muted font-code-sm text-center py-16 bg-surface-card rounded-xl border border-border-subtle">
            <span class="material-symbols-outlined text-3xl animate-spin text-primary mb-2">progress_activity</span>
            <div>Loading tactical challenge vector...</div>
          </div>
        </div>

      </div>

      <!-- Tactical Hint Unlock Confirmation Modal -->
      <div id="hintConfirmModal" class="modal-backdrop">
        <div class="modal-container" style="max-width: 480px;">
          <div class="modal-header bg-surface-terminal">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-status-warning text-xl">help_outline</span>
              <span class="modal-title font-bold">Tactical Hint Request</span>
            </div>
            <button class="modal-close" onclick="closeModal('hintConfirmModal')">&times;</button>
          </div>
          <div class="p-space-lg space-y-space-md bg-surface-base">
            <div class="flex items-start gap-3 p-space-sm rounded-lg bg-status-warning/10 border border-status-warning/30">
              <span class="material-symbols-outlined text-status-warning text-2xl shrink-0 mt-0.5">warning</span>
              <div class="space-y-1">
                <h4 class="font-bold text-text-primary font-headline-sm">Point Deduction Warning</h4>
                <p id="hintModalWarningText" class="font-body-md text-on-surface-variant text-sm">
                  Using hints reduces <strong>5 points</strong> from this challenge.
                </p>
              </div>
            </div>
            
            <p class="font-body-sm text-text-muted text-xs">
              If you proceed, the hint will be revealed immediately and 5 points will be deducted from the final yield.
            </p>

            <div class="flex items-center justify-end gap-3 pt-space-xs border-t border-border-subtle">
              <button type="button" class="btn btn-outline cursor-pointer" onclick="closeModal('hintConfirmModal')">
                <span class="material-symbols-outlined text-base">arrow_back</span> Return to Challenge
              </button>
              <button type="button" id="btnConfirmUnlockHint" class="btn btn-primary cursor-pointer" onclick="ChallengesView.confirmUnlockHint()">
                <span class="material-symbols-outlined text-base">lock_open</span> Proceed &amp; Reveal Hint
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Publish Writeup Modal -->
      <div id="publishWriteupModal" class="modal-backdrop">
        <div class="modal-container" style="max-width: 680px;">
          <div class="modal-header bg-surface-terminal flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">edit_note</span>
              <span id="publishWriteupModalTitle" class="modal-title font-bold">Publish Community Solution / Writeup</span>
            </div>
            <button class="modal-close" onclick="closeModal('publishWriteupModal')">&times;</button>
          </div>
          <form onsubmit="ChallengesView.saveCommunityWriteup(event)" class="p-space-lg space-y-space-md bg-surface-base">
            <!-- Target Challenge Context Strip -->
            <div id="publishWriteupChallengeBanner" class="p-3 bg-surface-terminal/85 rounded-lg border border-primary/30 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <div class="flex items-center gap-2 min-w-0">
                <span class="material-symbols-outlined text-primary text-base shrink-0">flag</span>
                <span class="text-text-muted uppercase font-bold text-[11px] shrink-0">TARGET CHALLENGE:</span>
                <span id="publishModalChallengeTitle" class="text-white font-bold truncate">Challenge Target</span>
              </div>
              <span id="publishModalChallengeCategory" class="px-2 py-0.5 rounded bg-surface-base text-secondary font-bold uppercase border border-border-subtle shrink-0">CATEGORY</span>
            </div>

            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Solution Approach / Writeup Title <span class="text-primary">*</span></label>
              <input type="text" id="writeupTitleInput" required class="w-full bg-surface-card border border-border-subtle rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary font-sans" placeholder="e.g. Memory Corruption Walkthrough & Exploit Script" />
            </div>

            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Tools &amp; Vector Tags (Optional)</label>
              <input type="text" id="writeupTagsInput" class="w-full bg-surface-card border border-border-subtle rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary font-mono text-xs" placeholder="e.g. Ghidra, Python, Buffer Overflow, Crypto" />
            </div>

            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary">Walkthrough &amp; Solution Proof <span class="text-primary">*</span></label>
                <div class="flex items-center gap-1 font-mono text-xs">
                  <button type="button" id="tabWriteupEdit" class="px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-bold cursor-pointer" onclick="ChallengesView.toggleWriteupEditorTab('edit')">WRITE</button>
                  <button type="button" id="tabWriteupPreview" class="px-2 py-0.5 rounded text-text-muted hover:text-white border border-transparent cursor-pointer" onclick="ChallengesView.toggleWriteupEditorTab('preview')">PREVIEW</button>
                </div>
              </div>
              <textarea id="writeupContentInput" rows="11" required class="w-full bg-surface-card border border-border-subtle rounded-lg p-3 text-text-primary text-sm focus:outline-none focus:border-primary font-mono text-xs leading-relaxed" placeholder="Explain your methodology step-by-step. Markdown and code snippets (e.g. \`\`\`python ... \`\`\`) are supported."></textarea>
              <div id="writeupPreviewContainer" class="hidden w-full bg-surface-terminal/40 border border-border-subtle rounded-lg p-3.5 text-sm max-h-72 overflow-y-auto font-sans leading-relaxed"></div>
            </div>

            <div class="flex items-center justify-between pt-space-xs border-t border-border-subtle">
              <span class="text-text-muted font-mono text-xs">Formatted Markdown Supported</span>
              <div class="flex items-center gap-2">
                <button type="button" class="btn btn-outline btn-sm cursor-pointer" onclick="closeModal('publishWriteupModal')">Cancel</button>
                <button type="submit" id="btnSubmitWriteup" class="btn btn-primary btn-sm flex items-center gap-1.5 cursor-pointer">
                  <span class="material-symbols-outlined text-sm">send</span>
                  <span id="btnSubmitWriteupText">Publish Solution</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <!-- View Full Writeup Modal -->
      <div id="viewWriteupModal" class="modal-backdrop">
        <div class="modal-container" style="max-width: 820px;">
          <div class="modal-header bg-surface-terminal flex items-center justify-between">
            <div class="flex items-center gap-2 min-w-0 pr-4">
              <span class="material-symbols-outlined text-primary text-xl shrink-0">article</span>
              <span id="viewWriteupModalTitle" class="modal-title font-bold truncate">Tactical Community Solution</span>
            </div>
            <button class="modal-close" onclick="closeModal('viewWriteupModal')">&times;</button>
          </div>
          <div class="p-space-lg space-y-space-md bg-surface-base max-h-[78vh] overflow-y-auto">
            <!-- 1. Challenge Specification Section (First clearly mention challenge name) -->
            <div id="viewWriteupChallengeHeader" class="p-3.5 bg-surface-terminal/85 rounded-xl border border-primary/30 space-y-1 shadow-md"></div>

            <!-- 2. Writeup / Solution Title (Then below that write that name) -->
            <div id="viewWriteupTitleSection" class="p-3.5 bg-surface-card rounded-xl border border-border-subtle space-y-1"></div>

            <!-- 3. Author Card Strip & Tags -->
            <div id="viewWriteupAuthorStrip" class="p-3 bg-surface-terminal/50 rounded-xl border border-border-subtle flex flex-wrap items-center justify-between gap-3"></div>
            
            <!-- 4. Solution / Walkthrough Answer (Then solution - first specify and then ans) -->
            <div class="space-y-2 pt-1 border-t border-border-subtle">
              <div class="flex items-center gap-2 font-mono text-xs font-bold text-primary uppercase tracking-wider">
                <span class="material-symbols-outlined text-sm">terminal</span>
                <span>Solution Walkthrough &amp; Answer Proof:</span>
              </div>
              <div id="viewWriteupBodyContent" class="text-text-primary text-sm leading-relaxed space-y-3 p-4 rounded-xl bg-surface-card/60 border border-border-subtle font-sans"></div>
            </div>

            <!-- Footer / Upvote Action -->
            <div class="flex items-center justify-between pt-space-sm border-t border-border-subtle">
              <div id="viewWriteupUpvoteAction"></div>
              <button type="button" class="btn btn-outline btn-sm cursor-pointer" onclick="closeModal('viewWriteupModal')">Close Walkthrough</button>
            </div>
          </div>
        </div>
      </div>
    `;

    try {
      const chall = await window.api.getChallenge(challengeId);
      this.currentChallenge = chall;
      this.populateStandaloneWorkspace(chall);
    } catch (e) {
      const mount = document.getElementById('standaloneWorkspaceMount');
      if (mount) {
        mount.innerHTML = `
          <div class="bg-surface-card rounded-xl p-12 border border-status-error/40 text-center shadow-xl space-y-3">
            <span class="material-symbols-outlined text-4xl text-status-error">error</span>
            <h3 class="font-headline-md text-headline-md text-text-primary font-bold">Challenge Vector Unavailable</h3>
            <p class="font-body-md text-body-md text-text-muted max-w-md mx-auto">
              ${escapeHtml(e.message || 'Unable to retrieve challenge details from defense node.')}
            </p>
            <div class="pt-2">
              <a href="#challenges" class="btn btn-primary btn-sm">Return to Challenges Matrix</a>
            </div>
          </div>
        `;
      }
    }
  },

  populateStandaloneWorkspace(c) {
    this.currentChallenge = c;
    const mount = document.getElementById('standaloneWorkspaceMount');
    if (!mount) return;

    const catBreadcrumb = document.getElementById('standaloneCategoryBreadcrumb');
    if (catBreadcrumb) catBreadcrumb.textContent = c.category_name || 'Jeopardy';

    // Extract official flag if available in writeup or challenge
    let officialFlag = null;
    let writeupBody = c.writeup_content || '';
    if (writeupBody.includes('🚩 OFFICIAL FLAG:')) {
      const match = writeupBody.match(/🚩 OFFICIAL FLAG:\s*([^\n]+)/);
      if (match) {
        officialFlag = match[1].trim();
      }
    } else if (writeupBody.includes('OWASP_DEMO{') || writeupBody.includes('flag{')) {
      const match = writeupBody.match(/(?:OWASP_DEMO|flag)\{[^}]+\}/);
      if (match) {
        officialFlag = match[0].trim();
      }
    }

    const isSolved = Boolean(c.is_solved);
    const isForfeited = Boolean(c.is_surrendered || (c.is_solved && c.points_awarded === 0));

    const diff = (c.difficulty || 'easy').toLowerCase();
    let diffPointsColor = 'text-accent-emerald';
    if (isSolved) diffPointsColor = 'text-yellow-300';
    else if (diff === 'hard') diffPointsColor = 'text-rose-400';
    else if (diff === 'medium') diffPointsColor = 'text-cyan-400';

    mount.innerHTML = `
      <!-- 1. Challenge Header Section (Unboxed, Modern) -->
      <div class="space-y-space-sm pt-2">
        <div class="flex flex-wrap items-start justify-between gap-space-md">
          <div class="space-y-2 max-w-3xl">
            <div class="flex flex-wrap items-center gap-2">
              <span class="px-2.5 py-1 rounded bg-secondary/15 text-secondary font-code-md text-code-md font-bold tracking-wider uppercase">${escapeHtml(c.category_name || 'Jeopardy')}</span>
              ${getDifficultyBadge(c.difficulty)}
              ${isSolved ? `
                <span class="px-3 py-1 rounded bg-amber-500/20 text-yellow-300 border border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.35)] font-bold text-sm flex items-center gap-1.5 font-mono">
                  <span class="material-symbols-outlined text-base">${isForfeited ? 'visibility' : 'check_circle'}</span>
                  <span>${isForfeited ? '✓ SOLVED (0 PTS)' : '✓ SOLVED'}</span>
                </span>
              ` : ''}
            </div>
            <h1 class="font-headline-lg text-3xl sm:text-4xl text-text-primary tracking-tight font-bold leading-tight">
              ${escapeHtml(c.title)}
            </h1>
            <div class="flex items-center gap-space-md font-code-md text-code-md text-text-muted pt-0.5">
              <span class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-lg text-primary">person_outline</span>
                Author: <strong class="text-on-surface">${escapeHtml(c.author || 'Admin SOC')}</strong>
              </span>
              <span>•</span>
              <span class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-lg text-secondary">verified_user</span>
                Verification: <strong class="text-primary">SHA-256 Validated</strong>
              </span>
            </div>
          </div>

          <!-- Points & Dynamic Decay Metric (Clean, Unboxed) -->
          <div class="text-right min-w-[200px] space-y-1">
            <div class="font-label-md text-label-md uppercase tracking-widest text-text-muted">Dynamic Yield</div>
            <div class="font-headline-xl text-4xl sm:text-5xl ${diffPointsColor} font-bold leading-none font-mono">
              <span id="standalonePoints">${c.points}</span> <span class="font-code-lg text-code-lg text-on-surface-variant font-normal">pts</span>
            </div>
            ${isSolved ? `
              <div class="pt-1 text-sm font-mono font-bold text-yellow-300 flex items-center justify-end gap-1">
                <span class="material-symbols-outlined text-base">${isForfeited ? 'visibility' : 'verified'}</span>
                <span>${isForfeited ? 'Score: 0 pts (Full Answer Revealed)' : `Score: +${c.points_awarded ?? c.points} pts (Target Neutralized)`}</span>
              </div>
            ` : `
              <div class="pt-1.5 font-code-md text-code-md text-text-secondary space-y-0.5">
                <div class="flex justify-between gap-3">
                  <span>Solves count:</span>
                  <span class="text-primary font-bold">${c.solves_count || 0} teams</span>
                </div>
                <div class="flex justify-between gap-3">
                  <span>Dynamic Decay:</span>
                  <span class="text-status-warning">Active &bull; -0.05/solve</span>
                </div>
              </div>
            `}
          </div>
        </div>

        <!-- External Live Challenge Link -->
        ${c.external_url ? `
          <div class="mt-space-sm p-space-sm bg-surface-terminal/40 rounded-lg flex flex-wrap items-center justify-between gap-space-sm">
            <div class="flex items-center gap-space-sm">
              <span class="material-symbols-outlined text-primary text-2xl">rocket_launch</span>
              <div class="font-body-md text-body-md text-on-surface-variant">Live environment is active for this challenge.</div>
            </div>
            <a href="${escapeHtml(c.external_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm text-sm">
              <span class="material-symbols-outlined text-base">open_in_new</span> Launch Challenge
            </a>
          </div>
        ` : ''}
      </div>

      <!-- 2. Challenge Brief & Scenario (Unboxed) -->
      <div class="space-y-space-md pt-space-sm">
        <!-- Concept Briefing text -->
        <div class="text-text-primary text-lg sm:text-xl leading-relaxed whitespace-pre-wrap font-sans font-normal pt-1">
          ${escapeHtml(c.description || 'No scenario briefing available.')}
        </div>

        <!-- Downloadable Tactical Artifacts -->
        ${(c.file_path || c.file_url) ? `
          <div class="pt-2 flex">
            <button class="btn btn-outline btn-sm text-sm" onclick="ChallengesView.downloadCurrentFile()">
              <span class="material-symbols-outlined text-lg text-primary">folder_zip</span>
              <span>Download Attached Challenge Artifacts</span>
            </button>
          </div>
        ` : ''}

        <!-- Assistance Protocols // Hint Vault -->
        ${Array.isArray(c.hints) && c.hints.length > 0 ? `
          <div class="space-y-2.5 pt-space-sm">
            ${c.hints.map((h, i) => {
              const isUnlocked = Boolean(h.used || h.is_unlocked || (h.content && h.content.trim().length > 0));
              const deduction = h.point_deduction != null ? h.point_deduction : (h.points_deduction != null ? h.points_deduction : (h.cost_points != null ? h.cost_points : 5));
              const orderNum = h.order || h.display_order || (i + 1);

              return `
              <div class="p-space-sm space-y-2 bg-surface-terminal/30 rounded-lg border border-border-subtle/50">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2.5">
                    <span class="material-symbols-outlined ${isUnlocked ? 'text-primary' : 'text-text-muted'} text-lg">${isUnlocked ? 'lock_open' : 'lock'}</span>
                    <span class="font-code-md text-code-md text-on-surface font-bold">HINT #${orderNum} ${isUnlocked ? '(REVEALED)' : ''}</span>
                    <span class="text-status-warning font-code-md text-code-md">[-${deduction} pts penalty]</span>
                  </div>
                  ${!isUnlocked ? `
                    <button type="button" class="btn btn-outline btn-sm text-sm text-status-warning hover:bg-status-warning/10 cursor-pointer" onclick="ChallengesView.requestHintUnlock('${c.id}', '${h.id}', ${deduction})">
                      <span class="material-symbols-outlined text-sm">key</span> Unlock Hint
                    </button>
                  ` : '<span class="font-code-md text-code-md text-primary font-bold">REVEALED</span>'}
                </div>
                <!-- Hint Explaining: Monospace and clean -->
                ${isUnlocked ? `<p class="font-mono text-base sm:text-lg text-primary pt-1 leading-relaxed pl-7">${escapeHtml(h.content || 'Hint unlocked. Inspect scenario parameters.')}</p>` : ''}
              </div>
            `;
            }).join('')}
          </div>
        ` : ''}

        <!-- Surrender & Reveal Full Solution (0 Points) -->
        <div class="pt-space-xs">
          <div class="flex flex-wrap items-center justify-between gap-space-sm p-space-sm rounded-lg bg-surface-terminal/20 border border-border-subtle/50">
            <div class="space-y-0.5">
              <div class="font-label-md text-label-md uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                <span class="material-symbols-outlined text-status-warning text-lg">visibility</span>
                <span>FORFEIT &amp; VIEW FULL SOLUTION</span>
              </div>
              <p class="font-body-md text-body-md text-text-secondary">Stuck on this challenge? You can view the full answer and solution, but 0 points will be gained.</p>
            </div>
            <button type="button" class="btn btn-outline btn-sm text-sm text-status-warning hover:bg-status-warning/10 cursor-pointer" onclick="ChallengesView.surrenderChallenge('${c.id}')">
              <span class="material-symbols-outlined text-sm">lock_open</span> View Full Answer (0 pts)
            </button>
          </div>
        </div>
      </div>

      <!-- 3. Flag Submission (Clean & Minimal) -->
      <div class="space-y-space-sm pt-space-md">
        <form class="space-y-space-xs" onsubmit="ChallengesView.submitFlag(event)">
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-sm">
            <div class="relative flex-1 bg-surface-card rounded-lg border border-border-subtle focus-within:border-primary overflow-hidden flex items-center">
              <span class="pl-3.5 pr-1.5 text-primary font-bold font-code-lg text-code-lg">&gt;_</span>
              <input id="inputFlagValue" class="w-full bg-transparent px-2.5 py-3 font-code-lg text-code-lg text-primary-fixed focus:outline-none placeholder:text-text-muted selection:bg-primary selection:text-surface-base font-mono" placeholder="flag{...}" type="text" value="${escapeHtml(c.submitted_flag || (isSolved ? (officialFlag || '') : '') || '')}" required autocomplete="off" />
              <span class="pr-3.5 text-text-muted font-code-md text-code-md">SHA-256</span>
            </div>
            <button type="submit" id="btnSubmitFlag" class="px-space-xl py-3 rounded-lg ${isSolved ? (isForfeited ? 'bg-status-warning/90 hover:bg-status-warning text-surface-base' : 'bg-accent-emerald hover:bg-accent-neon text-surface-base') : 'bg-primary hover:bg-accent-neon text-on-primary'} font-headline-sm text-headline-sm font-bold flex items-center justify-center gap-2 shadow-[0_0_16px_#10B9814D] hover:shadow-[0_0_24px_#00FF9D80] transition-all cursor-pointer">
              <span>${isSolved ? (isForfeited ? 'SOLVED (0 PTS)' : '✓ SOLVED') : 'SUBMIT FLAG'}</span>
              <span class="material-symbols-outlined text-xl font-bold">${isSolved ? (isForfeited ? 'visibility' : 'check_circle') : 'bolt'}</span>
            </button>
          </div>
        </form>

        <!-- Verification Telemetry Result Box -->
        ${isSolved ? (isForfeited ? `
          <div id="submissionResultBox" class="p-space-sm rounded bg-surface-terminal border border-status-warning space-y-1 mt-2 font-code-md text-code-md" style="display:block;">
            <div class="flex items-center gap-2 text-status-warning font-bold text-base">
              <span class="material-symbols-outlined text-lg">verified</span>
              <span>[✓] STATUS: CHALLENGE SOLVED &bull; FULL ANSWER REVEALED</span>
            </div>
            <div class="text-text-secondary pl-7 space-y-0.5 font-code-md text-code-md">
              <div>&gt; Attributed Points: <span class="text-status-warning font-bold font-mono">0 PTS</span> <span class="text-text-muted text-xs">(Full Answer Revealed / No Points Gained)</span></div>
              <div>&gt; Verification: <span class="text-secondary font-semibold">Archived Solution</span></div>
            </div>
          </div>
        ` : `
          <div id="submissionResultBox" class="p-space-sm rounded bg-primary/10 border border-primary space-y-1 mt-2 font-code-md text-code-md" style="display:block;">
            <div class="flex items-center gap-2 text-primary font-bold text-base">
              <span class="material-symbols-outlined text-lg">check_circle</span>
              <span>[+] STATUS: CORRECT FLAG VERIFIED &bull; TARGET NEUTRALIZED</span>
            </div>
            <div class="text-text-secondary pl-7 space-y-0.5 font-code-md text-code-md">
              <div>&gt; Attributed Points: <span class="text-primary font-bold font-mono">+${c.points_awarded ?? c.points} PTS</span></div>
              <div>&gt; Verification: <span class="text-accent-emerald font-semibold">Verified Solution</span></div>
            </div>
          </div>
        `) : `
          <div id="submissionResultBox" class="p-space-sm rounded bg-surface-terminal/80 border space-y-1 mt-2 font-code-md text-code-md" style="display:none;"></div>
        `}
      </div>

      <!-- 4. Post-Solve / Surrendered Unlocked Official Writeup & Flag Section -->
      <div id="workspaceWriteupSection" class="space-y-space-sm pt-space-md" style="${c.writeup_content ? 'display:block;' : 'display:none;'}">
        <div class="flex items-center justify-between pb-1">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-2xl">article</span>
            <span class="font-headline-md text-headline-md text-text-primary font-bold uppercase tracking-wide">OFFICIAL WRITEUP &amp; SOLUTION</span>
          </div>
          <div class="flex items-center gap-1 font-label-md text-label-md text-primary uppercase">
            <span class="material-symbols-outlined text-base">lock_open</span> Unlocked Intelligence
          </div>
        </div>

        <!-- Prominent Official Flag Display Box -->
        ${officialFlag ? `
          <div class="p-4 bg-primary/10 border border-primary/40 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-lg">
            <div class="flex items-center gap-3 min-w-0">
              <span class="material-symbols-outlined text-primary text-2xl shrink-0">flag</span>
              <div class="min-w-0">
                <div class="font-label-md text-label-md uppercase tracking-widest text-text-muted">OFFICIAL CHALLENGE FLAG:</div>
                <div id="displayedOfficialFlag" class="font-mono text-xl sm:text-2xl font-bold text-primary selection:bg-primary selection:text-surface-base truncate">${escapeHtml(officialFlag)}</div>
              </div>
            </div>
            <button type="button" class="btn btn-outline btn-sm text-sm flex items-center gap-1.5 cursor-pointer shrink-0" onclick="navigator.clipboard.writeText('${escapeHtml(officialFlag)}'); showToast('Official flag copied to clipboard!', 'success');">
              <span class="material-symbols-outlined text-base">content_copy</span>
              <span>Copy Flag</span>
            </button>
          </div>
        ` : ''}

        <!-- Walkthrough & Explanation Text -->
        <pre id="workspaceWriteupText" class="font-mono text-base sm:text-lg text-text-primary whitespace-pre-wrap leading-relaxed bg-surface-terminal/30 p-5 rounded-xl border border-border-subtle max-h-[500px] overflow-y-auto">${escapeHtml(c.writeup_content || '')}</pre>
      </div>

      <!-- 5. Community Writeups & Solutions Section -->
      <div id="communitySolutionsSection" class="space-y-space-md pt-space-xl border-t border-border-subtle mt-space-lg">
        <div class="flex flex-wrap items-center justify-between gap-space-sm pb-1">
          <div class="space-y-1">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-primary text-2xl">menu_book</span>
              <h2 class="font-headline-md text-headline-md text-text-primary font-bold tracking-tight uppercase">
                Community Writeups &amp; Solutions
              </h2>
              <span id="communityWriteupsCountBadge" class="font-mono text-xs px-2.5 py-0.5 rounded bg-surface-terminal border border-primary/30 text-primary font-bold">
                0 SOLUTIONS
              </span>
            </div>
            <p class="font-body-sm text-body-sm text-text-secondary">
              Operative methodologies, automated exploits, script proofs, and cryptographic walkthroughs.
            </p>
          </div>

          <button type="button" class="btn btn-primary btn-sm flex items-center gap-2 shadow-[0_0_15px_rgba(0,255,157,0.25)] hover:shadow-[0_0_22px_rgba(0,255,157,0.45)] transition-all cursor-pointer" onclick="ChallengesView.openPublishWriteupModal()">
            <span class="material-symbols-outlined text-base">edit_note</span>
            <span class="font-bold">Publish Your Solution</span>
          </button>
        </div>

        <!-- Writeups Feed Container -->
        <div id="communityWriteupsContainer" class="space-y-space-md">
          <div class="p-8 text-center bg-surface-card/60 rounded-xl border border-border-subtle text-text-muted font-mono text-sm">
            <span class="material-symbols-outlined text-2xl animate-spin text-primary mb-1">progress_activity</span>
            <div>Decrypting peer intelligence...</div>
          </div>
        </div>
      </div>
    `;

    // Asynchronously fetch community solutions
    this.loadCommunityWriteups(c.id);
  },

  async downloadCurrentFile() {
    if (!this.currentChallenge) return;
    try {
      const blob = await window.api.downloadChallengeFile(this.currentChallenge.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `challenge_${this.currentChallenge.id}_artifacts.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast('Downloaded challenge artifacts archive.', 'success');
    } catch (e) {
      showToast('Artifact download failed: ' + e.message, 'error');
    }
  },

  requestHintUnlock(challengeId, hintId, cost) {
    this.pendingHint = { challengeId, hintId, cost };
    const warningEl = document.getElementById('hintModalWarningText');
    if (warningEl) {
      warningEl.innerHTML = `Using this hint will permanently deduct <strong class="text-status-warning">${cost} points</strong> from your challenge reward score.`;
    }
    const btnConfirm = document.getElementById('btnConfirmUnlockHint');
    if (btnConfirm) {
      btnConfirm.innerHTML = `<span class="material-symbols-outlined text-base">lock_open</span> Proceed &amp; Reveal Hint (-${cost} pts)`;
    }
    openModal('hintConfirmModal');
  },

  async confirmUnlockHint() {
    if (!this.pendingHint) return;
    const { challengeId, hintId, cost } = this.pendingHint;
    closeModal('hintConfirmModal');

    try {
      await window.api.unlockHint(challengeId, hintId);
      showToast(`Hint unlocked (-${cost} pts penalty applied)`, 'info');
      const updatedChall = await window.api.getChallenge(challengeId);
      this.currentChallenge = updatedChall;
      this.populateStandaloneWorkspace(updatedChall);
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      this.pendingHint = null;
    }
  },

  async surrenderChallenge(challengeId) {
    if (!confirm('Are you sure you want to reveal the full answer and solution? You will gain 0 points for this challenge.')) {
      return;
    }

    try {
      const res = await window.api.surrenderChallenge(challengeId);
      showToast('Solution unlocked! (0 points gained)', 'info');
      const updatedChall = await window.api.getChallenge(challengeId);
      this.currentChallenge = updatedChall;
      this.currentChallenge.is_solved = true;
      this.currentChallenge.is_surrendered = true;
      this.currentChallenge.points_awarded = 0;
      if (res && res.solution) {
        this.currentChallenge.writeup_content = res.solution;
      }
      this.populateStandaloneWorkspace(this.currentChallenge);
      setTimeout(() => {
        const writeupEl = document.getElementById('workspaceWriteupSection');
        if (writeupEl) {
          writeupEl.style.display = 'block';
          writeupEl.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);

      // Trigger user UI score refresh
      if (window.App && typeof window.App.updateNavbarUserUI === 'function') {
        window.App.updateNavbarUserUI();
      }
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async submitFlag(e) {
    e.preventDefault();
    if (!this.currentChallenge) return;

    const flagInput = document.getElementById('inputFlagValue');
    const flagVal = flagInput ? flagInput.value.trim() : '';
    if (!flagVal) return;

    const btn = document.getElementById('btnSubmitFlag');
    const resultBox = document.getElementById('submissionResultBox');

    btn.disabled = true;
    btn.innerHTML = '<span>TRANSMITTING...</span><span class="material-symbols-outlined text-lg animate-spin">progress_activity</span>';

    try {
      const res = await window.api.submitFlag(this.currentChallenge.id, flagVal);
      btn.disabled = false;
      btn.innerHTML = '<span>SUBMIT FLAG</span><span class="material-symbols-outlined text-lg font-bold">bolt</span>';

      resultBox.style.display = 'block';

      const isSuccess = Boolean(res.is_correct || res.status === 'correct');
      const isAlready = Boolean(res.status === 'already_solved' || (res.message && res.message.toLowerCase().includes('already')));

      if (isSuccess || (isAlready && res.is_correct)) {
        const pts = (res.points_awarded !== undefined && res.points_awarded !== null) ? res.points_awarded : 0;
        const isSurrendered = Boolean(this.currentChallenge.is_surrendered || pts === 0);

        this.currentChallenge.is_solved = true;
        this.currentChallenge.points_awarded = pts;
        this.currentChallenge.is_surrendered = isSurrendered;

        if (pts > 0) {
          resultBox.className = 'p-space-sm rounded bg-primary/10 border border-primary space-y-1 font-code-md text-code-md';
          resultBox.innerHTML = `
            <div class="flex items-center gap-2 text-primary font-bold text-base">
              <span class="material-symbols-outlined text-lg">check_circle</span>
              <span>[+] STATUS: CORRECT FLAG VERIFIED &bull; TARGET NEUTRALIZED</span>
            </div>
            <div class="text-text-secondary pl-7 space-y-0.5 font-code-md text-code-md">
              <div>&gt; Attributed Points: <span class="text-primary font-bold font-mono">+${pts} PTS</span></div>
              <div>&gt; Verification: <span class="text-accent-emerald font-semibold">Verified Solution</span></div>
            </div>
          `;
          showToast(`Correct flag! +${pts} PTS awarded!`, 'success');
        } else {
          resultBox.className = 'p-space-sm rounded bg-surface-terminal border border-status-warning space-y-1 font-code-md text-code-md';
          resultBox.innerHTML = `
            <div class="flex items-center gap-2 text-status-warning font-bold text-base">
              <span class="material-symbols-outlined text-lg">verified</span>
              <span>[✓] STATUS: CHALLENGE SOLVED &bull; FULL ANSWER REVEALED</span>
            </div>
            <div class="text-text-secondary pl-7 space-y-0.5 font-code-md text-code-md">
              <div>&gt; Attributed Points: <span class="text-status-warning font-bold font-mono">0 PTS</span> <span class="text-text-muted text-xs">(Full Answer Revealed / No Points Gained)</span></div>
              <div>&gt; Verification: <span class="text-secondary font-semibold">Archived Solution</span></div>
            </div>
          `;
          showToast('Flag verified! (0 PTS - Full Answer Revealed)', 'info');
        }
        
        // Preserve entered text in input field
        if (flagInput) flagInput.value = flagVal;

        // Dynamically add SOLVED badge to header if not already present
        const badgeRow = document.querySelector('#standaloneWorkspaceMount .flex.flex-wrap.items-center.gap-2');
        if (badgeRow && !badgeRow.innerHTML.includes('SOLVED')) {
          const solvedSpan = document.createElement('span');
          solvedSpan.className = `px-3 py-1 rounded ${pts === 0 ? 'bg-status-warning/20 text-status-warning border border-status-warning/60 shadow-[0_0_12px_rgba(245,158,11,0.3)]' : 'bg-accent-emerald/20 text-accent-neon border border-accent-emerald/60 shadow-[0_0_12px_rgba(0,255,157,0.3)]'} font-bold text-sm flex items-center gap-1.5 font-mono`;
          solvedSpan.innerHTML = `<span class="material-symbols-outlined text-base">${pts === 0 ? 'visibility' : 'check_circle'}</span><span>${pts === 0 ? '✓ SOLVED (0 PTS)' : '✓ SOLVED'}</span>`;
          badgeRow.appendChild(solvedSpan);
        }

        // Trigger App navbar points update immediately
        if (window.App && typeof window.App.updateNavbarUserUI === 'function') {
          window.App.updateNavbarUserUI();
        }

        // Fetch updated challenge data in background to unlock writeup if available
        try {
          const updatedChall = await window.api.getChallenge(this.currentChallenge.id);
          this.currentChallenge = updatedChall;
          if (updatedChall && updatedChall.writeup_content) {
            const writeupSec = document.getElementById('workspaceWriteupSection');
            const writeupPre = document.getElementById('workspaceWriteupText');
            if (writeupSec) writeupSec.style.display = 'block';
            if (writeupPre) writeupPre.textContent = updatedChall.writeup_content;
          }
        } catch (e) {
          console.warn('Background challenge refresh error:', e);
        }
      } else if (isAlready) {
        if (flagInput) flagInput.value = flagVal;
        resultBox.className = 'p-space-sm rounded bg-surface-terminal border border-status-warning space-y-1 font-code-md text-code-md';
        resultBox.innerHTML = `
          <div class="flex items-center gap-2 text-status-warning font-bold">
            <span class="material-symbols-outlined text-base">info</span>
            <span>[!] DUPLICATE SOLVE: TARGET ALREADY NEUTRALIZED</span>
          </div>
          <div class="text-text-muted pl-6 font-code-md text-code-md">&gt; ${escapeHtml(res.message || 'Challenge already solved by your account.')}</div>
        `;
        showToast('Challenge already solved.', 'warning');
      } else {
        // Wrong answer
        if (flagInput) flagInput.value = flagVal;
        resultBox.className = 'p-space-sm rounded bg-status-error/10 border border-status-error space-y-1 font-code-md text-code-md';
        resultBox.innerHTML = `
          <div class="flex items-center gap-2 text-status-error font-bold">
            <span class="material-symbols-outlined text-base">cancel</span>
            <span>[-] WRONG ANSWER: TRY AGAIN</span>
          </div>
          <div class="text-text-muted pl-6 font-code-md text-code-md">&gt; ${escapeHtml(res.message || 'Incorrect flag. Please check your answer and try again!')}</div>
        `;
        showToast('Wrong answer. Try again!', 'error');
      }
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = '<span>SUBMIT FLAG</span><span class="material-symbols-outlined text-lg font-bold">bolt</span>';

      if (flagInput) flagInput.value = flagVal;
      resultBox.style.display = 'block';
      resultBox.className = 'p-space-sm rounded bg-status-error/10 border border-status-error space-y-1 font-code-md text-code-md';
      resultBox.innerHTML = `
        <div class="flex items-center gap-2 text-status-error font-bold">
          <span class="material-symbols-outlined text-base">cancel</span>
          <span>[-] WRONG ANSWER: TRY AGAIN</span>
        </div>
        <div class="text-text-muted pl-6 font-code-md text-code-md">&gt; ${escapeHtml(err.message || 'Incorrect flag. Please try again!')}</div>
      `;
      showToast('Wrong answer. Try again!', 'error');
    }
  },

  /* =========================================================================
     5. COMMUNITY WRITEUPS & SOLUTIONS CONTROLLER
     ========================================================================= */

  async loadCommunityWriteups(challengeId) {
    const container = document.getElementById('communityWriteupsContainer');
    const badge = document.getElementById('communityWriteupsCountBadge');
    if (!container) return;

    try {
      const writeups = await window.api.getCommunityWriteups(challengeId);
      this.currentWriteups = Array.isArray(writeups) ? writeups : [];
      if (badge) {
        badge.textContent = `${this.currentWriteups.length} SOLUTION${this.currentWriteups.length === 1 ? '' : 'S'}`;
      }
      this.renderCommunityWriteups(this.currentWriteups);
    } catch (e) {
      container.innerHTML = `
        <div class="p-6 bg-surface-card/60 rounded-xl border border-border-subtle text-center text-text-muted text-sm font-mono">
          Unable to load community writeups at this time.
        </div>
      `;
    }
  },

  renderCommunityWriteups(writeups = []) {
    const container = document.getElementById('communityWriteupsContainer');
    if (!container) return;

    if (!writeups || writeups.length === 0) {
      container.innerHTML = `
        <div class="p-8 sm:p-10 bg-surface-card/40 rounded-xl border border-border-subtle text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-surface-terminal flex items-center justify-center mx-auto text-text-muted border border-border-subtle">
            <span class="material-symbols-outlined text-2xl text-primary">history_edu</span>
          </div>
          <div class="space-y-1">
            <h4 class="font-bold text-base text-text-primary">No community writeups published yet</h4>
            <p class="font-body-sm text-body-sm text-text-muted max-w-md mx-auto">
              Be the first operative to publish a solution walkthrough, reverse-engineering notes, or exploit script.
            </p>
          </div>
          <div class="pt-1">
            <button type="button" class="btn btn-outline btn-sm cursor-pointer inline-flex items-center gap-1.5" onclick="ChallengesView.openPublishWriteupModal()">
              <span class="material-symbols-outlined text-base text-primary">edit</span>
              <span>Publish First Solution</span>
            </button>
          </div>
        </div>
      `;
      return;
    }

    const currentUserId = window.state?.currentUser?.id;
    const isAdmin = window.state?.currentUser?.role === 'admin' || window.state?.currentUser?.role === 'moderator';

    const cardsHtml = writeups.map(w => {
      const isMyWriteup = (currentUserId && w.user_id === currentUserId) || w.is_author;
      const canManage = isMyWriteup || isAdmin;
      const tagList = (w.tags || '').split(',').map(t => t.trim()).filter(Boolean);
      const createdDate = w.created_at ? new Date(w.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent';
      const initial = (w.author_name || w.author_username || 'O')[0].toUpperCase();

      const challTitle = w.challenge_title || this.currentChallenge?.title || 'Operational Target';
      const challCategory = w.challenge_category || this.currentChallenge?.category_name || 'Jeopardy';
      const challPoints = w.challenge_points != null ? w.challenge_points : (this.currentChallenge?.points || 0);

      return `
        <article class="p-space-md sm:p-space-lg rounded-xl bg-surface-card/85 backdrop-blur-md border border-border-subtle hover:border-primary/40 transition-all space-y-3.5 shadow-lg group">
          <!-- Card Header / Author Meta -->
          <div class="flex flex-wrap items-center justify-between gap-2.5 pb-2 border-b border-border-subtle/50">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-lg bg-surface-terminal border border-primary/30 flex items-center justify-center font-mono font-bold text-primary text-sm shrink-0">
                ${initial}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-text-primary text-sm truncate">${escapeHtml(w.author_name || w.author_username)}</span>
                  <span class="font-mono text-xs text-text-muted">@${escapeHtml(w.author_username)}</span>
                  ${w.author_has_solved ? `
                    <span class="px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-mono text-[10px] font-bold flex items-center gap-0.5">
                      <span class="material-symbols-outlined text-[12px]">verified</span> Solved
                    </span>
                  ` : ''}
                </div>
                <div class="text-text-muted text-xs font-mono flex items-center gap-2">
                  ${w.author_college ? `<span>${escapeHtml(w.author_college)}</span><span>•</span>` : ''}
                  <span>${createdDate}</span>
                </div>
              </div>
            </div>

            <!-- Manage Controls (Edit / Delete) or Follow Action -->
            <div class="flex items-center gap-2">
              ${!isMyWriteup && currentUserId ? `
                <button type="button" class="btn btn-outline btn-xs font-mono text-xs flex items-center gap-1 cursor-pointer opacity-80 hover:opacity-100 transition-all" onclick="ChallengesView.toggleFollowAuthor('${w.user_id}', this)">
                  <span class="material-symbols-outlined text-xs">person_add</span> Follow
                </button>
              ` : ''}

              ${canManage ? `
                <div class="flex items-center gap-1.5 opacity-90 group-hover:opacity-100 transition-opacity">
                  <button type="button" class="btn btn-outline btn-xs px-2 py-1 text-xs flex items-center gap-1 cursor-pointer" onclick="ChallengesView.editCommunityWriteup('${w.id}')">
                    <span class="material-symbols-outlined text-xs">edit</span> Edit
                  </button>
                  <button type="button" class="btn btn-outline btn-xs px-2 py-1 text-xs text-status-error hover:bg-status-error/10 border-status-error/40 flex items-center gap-1 cursor-pointer" onclick="ChallengesView.deleteCommunityWriteup('${w.id}')">
                    <span class="material-symbols-outlined text-xs">delete</span> Delete
                  </button>
                </div>
              ` : ''}
            </div>
          </div>

          <!-- 1. Challenge Specification Banner (First clearly mention challenge name) -->
          <div class="px-3 py-2 rounded-lg bg-surface-terminal/90 border border-primary/25 flex flex-wrap items-center justify-between gap-2 shadow-inner">
            <div class="flex items-center gap-2 min-w-0">
              <span class="material-symbols-outlined text-primary text-base shrink-0">flag</span>
              <span class="text-text-muted uppercase tracking-wider font-bold text-[11px] shrink-0">TARGET CHALLENGE:</span>
              <span class="text-white font-bold text-sm truncate">${escapeHtml(challTitle)}</span>
            </div>
            <div class="flex items-center gap-1.5 shrink-0 font-mono">
              <span class="px-2 py-0.5 rounded bg-surface-base text-secondary text-[10px] font-bold uppercase border border-border-subtle">${escapeHtml(challCategory)}</span>
              <span class="px-2 py-0.5 rounded bg-surface-base text-accent-emerald text-[10px] font-bold border border-border-subtle">${challPoints} PTS</span>
            </div>
          </div>

          <!-- 2. Writeup / Solution Name & Tags (Below that write that name) -->
          <div class="space-y-1.5 cursor-pointer pt-0.5" onclick="ChallengesView.openViewWriteupModal('${w.id}')">
            <div class="text-[11px] font-mono text-text-muted uppercase tracking-wider flex items-center gap-1">
              <span class="material-symbols-outlined text-xs text-primary">psychology</span>
              <span>SOLUTION TITLE:</span>
            </div>
            <h3 class="font-headline-sm text-lg font-bold text-white hover:text-primary transition-colors flex items-center gap-2">
              <span>${escapeHtml(w.title)}</span>
              <span class="material-symbols-outlined text-sm text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">open_in_new</span>
            </h3>

            ${tagList.length > 0 ? `
              <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
                ${tagList.map(tag => `
                  <span class="px-2 py-0.5 rounded bg-surface-terminal text-primary font-mono text-[11px] font-semibold border border-primary/20">
                    #${escapeHtml(tag)}
                  </span>
                `).join('')}
              </div>
            ` : ''}
          </div>

          <!-- 3. Solution / Answer Walkthrough (Then solution - first specify and then ans) -->
          <div class="space-y-1.5 pt-0.5 cursor-pointer" onclick="ChallengesView.openViewWriteupModal('${w.id}')">
            <div class="text-[11px] font-mono text-text-muted uppercase tracking-wider flex items-center gap-1">
              <span class="material-symbols-outlined text-xs text-primary">terminal</span>
              <span>SOLUTION WALKTHROUGH &amp; ANSWER:</span>
            </div>
            <div class="font-sans text-sm text-text-secondary line-clamp-3 leading-relaxed p-3 rounded-lg bg-surface-terminal/40 border border-border-subtle/70">
              ${escapeHtml(w.content)}
            </div>
          </div>

          <!-- Card Footer (Upvote & Actions) -->
          <div class="flex items-center justify-between pt-2 border-t border-border-subtle/50 text-xs">
            <div class="flex items-center gap-2">
              <button type="button" class="px-3 py-1.5 rounded-lg border flex items-center gap-1.5 font-mono text-xs font-bold cursor-pointer transition-all ${
                w.is_upvoted_by_me
                  ? 'bg-rose-950/40 text-rose-400 border-rose-500/50 shadow-[0_0_10px_rgba(244,63,94,0.2)]'
                  : 'bg-surface-terminal/60 text-text-muted hover:text-white border-border-subtle hover:border-primary/40'
              }" onclick="ChallengesView.toggleUpvoteWriteup('${w.id}')">
                <span class="material-symbols-outlined text-sm ${w.is_upvoted_by_me ? 'fill-current' : ''}">favorite</span>
                <span>${w.upvotes_count || 0}</span>
                <span class="font-sans text-[11px] font-normal hidden sm:inline">${w.is_upvoted_by_me ? 'Applauded' : 'Applaud'}</span>
              </button>

              <button type="button" class="text-text-muted hover:text-primary transition-colors text-xs font-mono flex items-center gap-1 cursor-pointer" onclick="ChallengesView.openViewWriteupModal('${w.id}')">
                <span class="material-symbols-outlined text-sm">visibility</span> Read Solution
              </button>
            </div>

            <button type="button" class="text-text-muted hover:text-white transition-colors cursor-pointer flex items-center gap-1" onclick="navigator.clipboard.writeText(window.location.href); showToast('Solution reference link copied!', 'success');">
              <span class="material-symbols-outlined text-sm">share</span>
              <span class="hidden sm:inline">Share</span>
            </button>
          </div>
        </article>
      `;
    }).join('');

    container.innerHTML = cardsHtml;
  },

  openPublishWriteupModal(writeup = null) {
    this.editingWriteupId = writeup ? writeup.id : null;
    const titleEl = document.getElementById('publishWriteupModalTitle');
    const inputTitle = document.getElementById('writeupTitleInput');
    const inputTags = document.getElementById('writeupTagsInput');
    const inputContent = document.getElementById('writeupContentInput');
    const btnText = document.getElementById('btnSubmitWriteupText');

    if (titleEl) titleEl.textContent = writeup ? 'Edit Community Solution / Writeup' : 'Publish Community Solution / Writeup';
    if (btnText) btnText.textContent = writeup ? 'Save Changes' : 'Publish Solution';

    const modalChallTitle = document.getElementById('publishModalChallengeTitle');
    const modalChallCat = document.getElementById('publishModalChallengeCategory');
    if (modalChallTitle) {
      modalChallTitle.textContent = this.currentChallenge?.title || 'Operational Target';
    }
    if (modalChallCat) {
      modalChallCat.textContent = this.currentChallenge?.category_name || 'Jeopardy';
    }

    if (inputTitle) inputTitle.value = writeup ? writeup.title : '';
    if (inputTags) inputTags.value = writeup ? (writeup.tags || '') : '';
    if (inputContent) inputContent.value = writeup ? writeup.content : '';

    this.toggleWriteupEditorTab('edit');
    openModal('publishWriteupModal');
  },

  editCommunityWriteup(writeupId) {
    const found = (this.currentWriteups || []).find(w => w.id === writeupId);
    if (found) {
      this.openPublishWriteupModal(found);
    }
  },

  toggleWriteupEditorTab(mode) {
    const tabEdit = document.getElementById('tabWriteupEdit');
    const tabPrev = document.getElementById('tabWriteupPreview');
    const inputContent = document.getElementById('writeupContentInput');
    const previewContainer = document.getElementById('writeupPreviewContainer');

    if (mode === 'preview') {
      if (tabEdit) tabEdit.className = 'px-2 py-0.5 rounded text-text-muted hover:text-white border border-transparent cursor-pointer';
      if (tabPrev) tabPrev.className = 'px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-bold cursor-pointer';
      if (inputContent) inputContent.classList.add('hidden');
      if (previewContainer) {
        previewContainer.classList.remove('hidden');
        previewContainer.innerHTML = this.renderMarkdown(inputContent ? inputContent.value : '') || '<em class="text-text-muted">No content to preview yet.</em>';
      }
    } else {
      if (tabEdit) tabEdit.className = 'px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-bold cursor-pointer';
      if (tabPrev) tabPrev.className = 'px-2 py-0.5 rounded text-text-muted hover:text-white border border-transparent cursor-pointer';
      if (inputContent) inputContent.classList.remove('hidden');
      if (previewContainer) previewContainer.classList.add('hidden');
    }
  },

  async saveCommunityWriteup(e) {
    if (e) e.preventDefault();
    if (!this.currentChallenge) return;

    const title = document.getElementById('writeupTitleInput')?.value.trim();
    const tags = document.getElementById('writeupTagsInput')?.value.trim();
    const content = document.getElementById('writeupContentInput')?.value.trim();
    const btn = document.getElementById('btnSubmitWriteup');

    if (!title || !content) {
      showToast('Please enter both a title and solution walkthrough.', 'warning');
      return;
    }

    if (btn) btn.disabled = true;

    try {
      if (this.editingWriteupId) {
        await window.api.updateCommunityWriteup(this.currentChallenge.id, this.editingWriteupId, { title, tags, content });
        showToast('Solution updated successfully!', 'success');
      } else {
        await window.api.publishCommunityWriteup(this.currentChallenge.id, { title, tags, content });
        showToast('Solution published to community!', 'success');
      }
      closeModal('publishWriteupModal');
      await this.loadCommunityWriteups(this.currentChallenge.id);
    } catch (err) {
      showToast(err.message || 'Failed to save writeup.', 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async deleteCommunityWriteup(writeupId) {
    if (!confirm('Are you sure you want to delete this community writeup?')) return;
    if (!this.currentChallenge) return;

    try {
      await window.api.deleteCommunityWriteup(this.currentChallenge.id, writeupId);
      showToast('Writeup deleted.', 'info');
      await this.loadCommunityWriteups(this.currentChallenge.id);
    } catch (err) {
      showToast(err.message || 'Failed to delete writeup.', 'error');
    }
  },

  async toggleUpvoteWriteup(writeupId) {
    if (!this.currentChallenge) return;
    try {
      const res = await window.api.upvoteCommunityWriteup(this.currentChallenge.id, writeupId);
      const target = (this.currentWriteups || []).find(w => w.id === writeupId);
      if (target) {
        target.upvotes_count = res.upvotes_count;
        target.is_upvoted_by_me = res.is_upvoted;
      }
      this.renderCommunityWriteups(this.currentWriteups);
      if (res.is_upvoted) {
        showToast('Applauded solution!', 'success');
      }
    } catch (err) {
      showToast(err.message || 'Upvote failed.', 'error');
    }
  },

  openViewWriteupModal(writeupId) {
    const w = (this.currentWriteups || []).find(item => item.id === writeupId);
    if (!w) return;

    const challTitle = w.challenge_title || this.currentChallenge?.title || 'Operational Target';
    const challCategory = w.challenge_category || this.currentChallenge?.category_name || 'Jeopardy';
    const challPoints = w.challenge_points != null ? w.challenge_points : (this.currentChallenge?.points || 0);

    const titleEl = document.getElementById('viewWriteupModalTitle');
    const challHeader = document.getElementById('viewWriteupChallengeHeader');
    const titleSec = document.getElementById('viewWriteupTitleSection');
    const authorStrip = document.getElementById('viewWriteupAuthorStrip');
    const bodyContent = document.getElementById('viewWriteupBodyContent');
    const upvoteAction = document.getElementById('viewWriteupUpvoteAction');

    if (titleEl) titleEl.textContent = `${challTitle} — Community Solution`;

    // 1. Clearly specify Challenge Name first
    if (challHeader) {
      challHeader.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <div class="flex items-center gap-1.5 text-primary font-bold uppercase tracking-wider">
            <span class="material-symbols-outlined text-base">flag</span>
            <span>TARGET CHALLENGE:</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded bg-surface-base text-secondary font-bold uppercase border border-border-subtle">
              ${escapeHtml(challCategory)}
            </span>
            <span class="px-2.5 py-0.5 rounded bg-surface-base text-accent-emerald font-bold border border-border-subtle">
              ${challPoints} PTS
            </span>
          </div>
        </div>
        <h2 class="font-headline-md text-xl sm:text-2xl font-bold text-white tracking-tight pt-1 flex items-center gap-2">
          ${escapeHtml(challTitle)}
        </h2>
      `;
    }

    // 2. Below that write that name (Solution / Writeup title)
    if (titleSec) {
      titleSec.innerHTML = `
        <div class="font-mono text-xs text-text-muted uppercase tracking-wider font-semibold flex items-center gap-1">
          <span class="material-symbols-outlined text-primary text-sm">psychology</span>
          <span>SOLUTION TITLE / APPROACH:</span>
        </div>
        <h3 class="font-headline-sm text-lg sm:text-xl font-bold text-primary">
          ${escapeHtml(w.title)}
        </h3>
      `;
    }

    const initial = (w.author_name || w.author_username || 'O')[0].toUpperCase();
    const createdDate = w.created_at ? new Date(w.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent';
    const isMyWriteup = (window.state?.currentUser?.id && w.user_id === window.state.currentUser.id) || w.is_author;

    if (authorStrip) {
      authorStrip.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-surface-terminal border border-primary/30 flex items-center justify-center font-mono font-bold text-primary text-base shrink-0">
            ${initial}
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-text-primary">${escapeHtml(w.author_name || w.author_username)}</span>
              <span class="font-mono text-xs text-text-muted">@${escapeHtml(w.author_username)}</span>
              ${w.author_has_solved ? `
                <span class="px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-mono text-[10px] font-bold flex items-center gap-0.5">
                  <span class="material-symbols-outlined text-[12px]">verified</span> Solved
                </span>
              ` : ''}
              ${!isMyWriteup && window.state?.currentUser ? `
                <button type="button" class="btn btn-outline btn-xs font-mono text-xs flex items-center gap-1 cursor-pointer ml-1.5" onclick="ChallengesView.toggleFollowAuthor('${w.user_id}', this)">
                  <span class="material-symbols-outlined text-xs">person_add</span> Follow
                </button>
              ` : ''}
            </div>
            <div class="text-text-muted text-xs font-mono">
              ${w.author_college ? `<span>${escapeHtml(w.author_college)}</span> • ` : ''}Published on ${createdDate}
            </div>
          </div>
        </div>

        ${w.tags ? `
          <div class="flex flex-wrap items-center gap-1.5">
            ${w.tags.split(',').map(t => t.trim()).filter(Boolean).map(tag => `
              <span class="px-2 py-0.5 rounded bg-surface-terminal text-primary font-mono text-xs border border-primary/20">
                #${escapeHtml(tag)}
              </span>
            `).join('')}
          </div>
        ` : ''}
      `;
    }

    if (bodyContent) {
      bodyContent.innerHTML = this.renderMarkdown(w.content);
    }

    if (upvoteAction) {
      upvoteAction.innerHTML = `
        <button type="button" class="btn btn-sm flex items-center gap-1.5 cursor-pointer ${
          w.is_upvoted_by_me ? 'btn-primary' : 'btn-outline'
        }" onclick="ChallengesView.toggleUpvoteWriteup('${w.id}'); ChallengesView.openViewWriteupModal('${w.id}');">
          <span class="material-symbols-outlined text-base">favorite</span>
          <span>${w.upvotes_count || 0} Applauds</span>
        </button>
      `;
    }

    openModal('viewWriteupModal');
  },

  async toggleFollowAuthor(userId, btnEl) {
    if (!userId) return;
    try {
      if (btnEl) btnEl.disabled = true;
      const res = await window.api.toggleFollowUser(userId);
      if (btnEl) {
        btnEl.disabled = false;
        if (res.is_following) {
          btnEl.className = 'btn btn-outline btn-xs font-mono text-xs text-primary border-primary/40 flex items-center gap-1 cursor-pointer ml-1.5';
          btnEl.innerHTML = '<span class="material-symbols-outlined text-xs text-primary">check</span> Following';
        } else {
          btnEl.className = 'btn btn-outline btn-xs font-mono text-xs flex items-center gap-1 cursor-pointer ml-1.5';
          btnEl.innerHTML = '<span class="material-symbols-outlined text-xs">person_add</span> Follow';
        }
      }
      showToast(res.is_following ? 'Operative followed' : 'Unfollowed operative', res.is_following ? 'success' : 'info');
    } catch (e) {
      if (btnEl) btnEl.disabled = false;
      showToast(e.message || 'Action failed', 'error');
    }
  },

  renderMarkdown(text) {
    if (!text) return '';
    let out = escapeHtml(text);
    // Fenced code blocks ```lang ... ```
    out = out.replace(/```([a-zA-Z0-9_\-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="bg-surface-terminal/95 p-4 my-3 rounded-lg border border-border-subtle font-mono text-xs sm:text-sm text-primary-fixed overflow-x-auto selection:bg-primary selection:text-surface-base"><code>${code.trim()}</code></pre>`;
    });
    // Inline code `...`
    out = out.replace(/`([^`]+)`/g, '<code class="bg-surface-terminal px-1.5 py-0.5 rounded text-primary font-mono text-xs border border-border-subtle/60">$1</code>');
    // Bold **text**
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-white">$1</strong>');
    // Italic *text*
    out = out.replace(/\*([^*]+)\*/g, '<em class="italic text-text-secondary">$1</em>');
    // Headers
    out = out.replace(/^### (.*$)/gim, '<h4 class="font-bold text-base text-primary mt-3 mb-1 font-mono">$1</h4>');
    out = out.replace(/^## (.*$)/gim, '<h3 class="font-bold text-lg text-white mt-3.5 mb-1.5 font-headline-sm">$1</h3>');
    out = out.replace(/^# (.*$)/gim, '<h2 class="font-bold text-xl text-white mt-4 mb-2 font-headline-md">$1</h2>');
    // Lists
    out = out.replace(/^\s*-\s+(.*$)/gim, '<li class="ml-4 list-disc text-text-secondary">$1</li>');
    out = out.replace(/\n\n/g, '<div class="h-2.5"></div>');
    out = out.replace(/\n/g, '<br/>');
    return out;
  }

};

window.ChallengesView = ChallengesView;

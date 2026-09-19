/**
 * OWASP CTF Platform — Teams View
 * Stitch "Obsidian Signal" Architecture
 */

const TeamsView = {
  myTeam: null,
  myCreatedTeams: [],
  otherTeams: [],
  teams: [],
  selectedOperatives: [],
  availableOperatives: [],
  searchQuery: '',
  _searchTimer: null,
  activeSquadOperatives: [],
  activeSquadSearchQuery: '',
  _activeSquadSearchTimer: null,
  currentInvitingTeamId: null,

  async init(searchParams = null) {
    this.render();
    await this.loadData();
    const targetTeamId = searchParams?.get('history') || searchParams?.get('openHistory') || window.state?.pendingTeamHistoryId;
    if (targetTeamId) {
      if (window.state) window.state.pendingTeamHistoryId = null;
      this.openTeamHistoryModal(targetTeamId);
    }
  },

  render() {
    const container = document.getElementById('view-teams');
    if (!container) return;

    container.innerHTML = `
      <div class="p-space-lg space-y-space-md max-w-[1720px] mx-auto w-full">
        
        <!-- Header Controls -->
        <div class="flex flex-wrap items-center justify-between gap-space-md pb-space-sm border-b border-border-subtle">
          <div>
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-2xl">groups</span>
              <h1 class="font-headline-lg text-headline-lg text-text-primary font-bold">Collegiate Squads &amp; Teams</h1>
            </div>
            <p class="font-body-sm text-body-sm text-text-muted mt-1">
              Assemble collegiate squads of up to 4 operatives with aggregated defense score and synchronized event participation.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <button class="btn btn-primary btn-sm" onclick="TeamsView.openCreateSquadModal()">
              <span class="material-symbols-outlined text-sm">group_add</span>
              <span>Form New Squad</span>
            </button>
            <button class="btn btn-outline btn-sm" onclick="openModal('joinTeamModal')">
              <span class="material-symbols-outlined text-sm">vpn_key</span>
              <span>Join via Code</span>
            </button>
          </div>
        </div>

        <!-- Incoming Squad Invitations Alert -->
        <div id="myInvitationsBanner"></div>

        <!-- My Active Squad Card -->
        <div id="myTeamBanner"></div>

        <!-- Registered Squads Directory -->
        <div class="bg-surface-card rounded-xl border border-border-grid shadow-xl overflow-hidden">
          <div class="p-space-md border-b border-border-subtle flex justify-between items-center bg-surface-terminal/30">
            <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">shield</span>
              <span>Registered Squads Directory</span>
            </h3>
            <button class="btn btn-outline btn-sm" onclick="TeamsView.loadData()">
              <span class="material-symbols-outlined text-xs">refresh</span> Refresh
            </button>
          </div>

          <div id="teamsListContainer" class="overflow-x-auto">
            <div class="text-text-muted font-code-sm text-center py-12">Querying squad records...</div>
          </div>
        </div>

      </div>

      <!-- Create Team Modal (With Participant Search & Same-College Prioritization) -->
      <div id="createTeamModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:580px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">group_add</span>
              <span>Assemble New Squad</span>
            </h3>
            <button class="modal-close" onclick="closeModal('createTeamModal')">&times;</button>
          </div>
          <form onsubmit="TeamsView.handleCreateTeam(event)" class="modal-body space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Squad Name *</label>
                <input type="text" id="createTeamName" required placeholder="e.g. KernelPanic" maxlength="50" class="w-full" />
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">College / Campus</label>
                <input type="text" id="createTeamCollege" placeholder="e.g. PCCOE" maxlength="100" class="w-full" oninput="TeamsView.renderOperativesList()" />
              </div>
            </div>

            <!-- Send Squad Requests Section -->
            <div class="space-y-2 pt-2 border-t border-border-subtle">
              <div class="flex items-center justify-between">
                <div>
                  <label class="block font-label-sm text-label-sm uppercase text-text-primary font-bold">Send Squad Requests (Optional)</label>
                  <p class="text-[11px] text-text-muted">Same-college participants are prioritized on top. Select up to 3 participants to request. Teammates only join your roster once they accept.</p>
                </div>
                <span id="selectedOperativesCount" class="font-mono text-xs text-amber-400 font-bold px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30">0/3 Requests</span>
              </div>

              <!-- Search Bar -->
              <div class="relative">
                <span class="material-symbols-outlined absolute left-3 top-2.5 text-text-muted text-base pointer-events-none">search</span>
                <input type="text" id="createTeamSearchOperatives" class="w-full pl-9 pr-8 text-xs font-mono bg-surface-terminal/60 border border-border-subtle focus:border-primary rounded-lg py-2" placeholder="Search participants by username, name, college..." oninput="TeamsView.onSearchOperatives(this.value)" />
              </div>

              <!-- Selected Participants Chips Tray -->
              <div id="selectedOperativesTray" class="hidden p-2 rounded-lg bg-surface-terminal/50 border border-amber-500/20 space-y-1.5"></div>

              <!-- Registered Participants Directory List -->
              <div class="rounded-lg border border-border-subtle bg-surface-terminal/30 overflow-hidden">
                <div class="px-3 py-1.5 bg-surface-terminal/80 border-b border-border-subtle/50 flex items-center justify-between text-[11px] font-mono text-text-muted uppercase">
                  <span>Registered Platform Participants</span>
                  <span class="text-primary font-semibold">Priority: Same College Upside</span>
                </div>
                <div id="createTeamOperativesList" class="max-h-52 overflow-y-auto divide-y divide-border-subtle/30 scrollbar-thin">
                  <div class="p-4 text-center text-text-muted text-xs font-mono">Loading registered participants...</div>
                </div>
              </div>
            </div>

            <div class="flex justify-end gap-2 pt-2 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('createTeamModal')">Cancel</button>
              <button type="submit" id="submitCreateSquadBtn" class="btn btn-primary">Form Squad</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Invite Operatives to Active Squad Modal -->
      <div id="inviteOperativesModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:580px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">person_add</span>
              <span id="inviteOperativesModalTitle">Invite Participants to Squad</span>
            </h3>
            <button class="modal-close" onclick="closeModal('inviteOperativesModal')">&times;</button>
          </div>
          <div class="modal-body space-y-3">
            <div>
              <p class="text-xs text-text-muted">Invite registered participants to join your active squad. Same-college peers appear on top.</p>
            </div>

            <!-- Search Bar -->
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-2.5 text-text-muted text-base pointer-events-none">search</span>
              <input type="text" id="inviteOperativesSearchInput" class="w-full pl-9 pr-8 text-xs font-mono bg-surface-terminal/60 border border-border-subtle focus:border-primary rounded-lg py-2" placeholder="Search participants by username, name, college..." oninput="TeamsView.onSearchInviteOperatives(this.value)" />
            </div>

            <!-- Participants List -->
            <div class="rounded-lg border border-border-subtle bg-surface-terminal/30 overflow-hidden">
              <div class="px-3 py-1.5 bg-surface-terminal/80 border-b border-border-subtle/50 flex items-center justify-between text-[11px] font-mono text-text-muted uppercase">
                <span>Registered Platform Participants</span>
                <span class="text-primary font-semibold">Priority: Same College Upside</span>
              </div>
              <div id="activeSquadOperativesList" class="max-h-60 overflow-y-auto divide-y divide-border-subtle/30 scrollbar-thin">
                <div class="p-4 text-center text-text-muted text-xs font-mono">Loading participants...</div>
              </div>
            </div>

            <div class="flex justify-end pt-2 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('inviteOperativesModal')">Done</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Join Team Modal -->
      <div id="joinTeamModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:440px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title">Join Squad via Invite Code</h3>
            <button class="modal-close" onclick="closeModal('joinTeamModal')">&times;</button>
          </div>
          <form onsubmit="TeamsView.handleJoinTeam(event)" class="modal-body space-y-4">
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Squad Join Code</label>
              <input type="text" id="joinTeamCode" required placeholder="e.g. 6-8 digit alphanumeric token" class="font-mono text-primary" />
            </div>
            <div class="flex justify-end gap-2 pt-2 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('joinTeamModal')">Cancel</button>
              <button type="submit" class="btn btn-primary">Join Squad</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Team Operations & Event History Modal -->
      <div id="teamHistoryModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:760px;">
          <div class="modal-header bg-surface-terminal border-b border-border-subtle flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">military_tech</span>
              <h3 class="modal-title font-mono text-base tracking-wide" id="teamHistoryModalTitle">Squad Operations History</h3>
            </div>
            <button class="modal-close" onclick="closeModal('teamHistoryModal')">&times;</button>
          </div>
          <div class="modal-body space-y-4 p-5" id="teamHistoryModalContent">
            <!-- Populated dynamically by openTeamHistoryModal -->
          </div>
        </div>
      </div>
    `;
  },

  async loadData() {
    const banner = document.getElementById('myTeamBanner');
    const invBanner = document.getElementById('myInvitationsBanner');
    const list = document.getElementById('teamsListContainer');

    try {
      const [myTeam, allTeams, myInvitations, myAllTeams] = await Promise.all([
        window.api.getMyTeam().catch(() => null),
        window.api.getTeams().catch(() => []),
        window.api.getMyTeamInvitations ? window.api.getMyTeamInvitations().catch(() => []) : Promise.resolve([]),
        window.api.getMyTeams ? window.api.getMyTeams().catch(() => []) : Promise.resolve([])
      ]);

      this.myTeam = myTeam;
      this.teams = allTeams || [];
      this.myInvitations = myInvitations || [];

      // Render Incoming Squad Invitations Alert Banner
      if (invBanner) {
        if (!this.myInvitations || this.myInvitations.length === 0) {
          invBanner.innerHTML = '';
        } else {
          invBanner.innerHTML = `
            <div class="space-y-2 mb-2">
              ${this.myInvitations.map(inv => `
                <div class="bg-surface-card rounded-xl p-3.5 border border-amber-500/40 bg-amber-500/5 shadow-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div class="flex items-center gap-3 min-w-0">
                    <span class="material-symbols-outlined text-amber-400 text-2xl shrink-0">mark_email_unread</span>
                    <div class="min-w-0">
                      <div class="font-bold text-xs text-text-primary">
                        Squad Invitation: <span class="text-primary font-mono text-sm">${escapeHtml(inv.team_name)}</span> (${escapeHtml(inv.college || 'Collegiate')})
                      </div>
                      <div class="text-[11px] text-text-muted font-mono truncate">
                        Invited by @${escapeHtml(inv.owner_username || 'Captain')}. Accept to join roster and contribute defense points.
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    <button class="btn btn-primary btn-sm text-xs font-mono flex items-center gap-1" onclick="TeamsView.acceptInvite('${inv.team_id}')">
                      <span class="material-symbols-outlined text-xs">check</span> Accept &amp; Join
                    </button>
                    <button class="btn btn-outline btn-sm text-xs font-mono text-status-error hover:border-status-error flex items-center gap-1" onclick="TeamsView.declineInvite('${inv.team_id}')">
                      <span class="material-symbols-outlined text-xs">close</span> Decline
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
          `;
        }
      }

      const currentUser = window.state.currentUser;
      const currentUserId = currentUser?.id;
      const currentUsername = (currentUser?.username || '').toLowerCase();

      // Check if team is user-affiliated (owner, captain, or active member)
      const isUserAffiliatedTeam = (t) => {
        if (!currentUser) return false;
        if (currentUserId && (String(t.owner_id) === String(currentUserId) || String(t.captain_id) === String(currentUserId))) return true;
        if (currentUsername && (t.owner_username || '').toLowerCase() === currentUsername) return true;
        if (Array.isArray(t.members) && t.members.some(m => ((currentUserId && String(m.user_id) === String(currentUserId)) || (currentUsername && (m.username || '').toLowerCase() === currentUsername)) && m.role !== 'requested' && m.is_active !== false)) return true;
        return false;
      };

      let combinedSquads = Array.isArray(myAllTeams) && myAllTeams.length > 0 ? [...myAllTeams] : [];

      // Also ensure any team from allTeams matching affiliate check is added
      (allTeams || []).forEach(t => {
        if (isUserAffiliatedTeam(t) && !combinedSquads.some(cs => String(cs.id) === String(t.id))) {
          combinedSquads.push(t);
        }
      });

      // Ensure active squad (myTeam) is present
      if (myTeam && !combinedSquads.some(cs => String(cs.id) === String(myTeam.id))) {
        combinedSquads.unshift(myTeam);
      }

      // Fetch detail for any team where members are not yet populated
      const detailedSquads = await Promise.all(
        combinedSquads.map(async (t) => {
          if (t.members && t.members.length > 0) return t;
          try {
            const detail = await window.api.getTeam(t.id);
            return { ...t, ...detail };
          } catch (e) {
            return t;
          }
        })
      );

      this.myCreatedTeams = detailedSquads;

      // Other teams are displayed in the directory box as normal
      const mySquadIds = new Set(this.myCreatedTeams.map(t => String(t.id)));
      this.otherTeams = (allTeams || []).filter(t => !mySquadIds.has(String(t.id)));

      // Render Teams Formed / Joined by User in Dedicated Boxes
      if (banner) {
        if (this.myCreatedTeams.length === 0) {
          banner.innerHTML = `
            <div class="bg-surface-card rounded-xl p-space-md border border-border-grid flex flex-col sm:flex-row justify-between items-start sm:items-center gap-space-sm">
              <div>
                <span class="font-label-sm text-label-sm uppercase text-text-muted font-mono">STATUS: UNATTACHED OPERATIVE</span>
                <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold mt-0.5">You are competing as an independent solo operative.</h3>
                <p class="font-body-sm text-body-sm text-text-muted">Form a squad with university teammates or join an existing squad with an invite code.</p>
              </div>
              <div class="flex items-center gap-2">
                <button class="btn btn-primary btn-sm" onclick="TeamsView.openCreateSquadModal()">Form Squad</button>
                <button class="btn btn-outline btn-sm" onclick="openModal('joinTeamModal')">Enter Code</button>
              </div>
            </div>
          `;
        } else {
          banner.innerHTML = `
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-1 border-b border-border-subtle/50">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-xl">military_tech</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">
                    Your Squads (${this.myCreatedTeams.length})
                  </h3>
                </div>
                <span class="font-mono text-xs text-text-muted">Squads you created or belong to as an operative &bull; Click squad name for event engagement record</span>
              </div>
              <div class="space-y-4">
                ${this.myCreatedTeams.map((team, idx) => this.renderMyTeamBox(team, idx)).join('')}
              </div>
            </div>
          `;
        }
      }

      // Render Registered Squads Directory (Other Teams in One Box as Normal)
      if (list) {
        if (this.otherTeams.length === 0) {
          list.innerHTML = '<div class="text-text-muted font-code-sm text-center py-10">No other collegiate squads registered yet.</div>';
        } else {
          list.innerHTML = `
            <table class="w-full text-left font-code-sm text-code-sm">
              <thead>
                <tr class="bg-surface-terminal/60 text-text-muted font-label-sm text-label-sm uppercase border-b border-border-subtle">
                  <th class="p-3">Squad Name</th>
                  <th class="p-3">Campus Chapter</th>
                  <th class="p-3 text-center">Roster Size</th>
                  <th class="p-3 text-right">Defense Credits</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/30">
                ${this.otherTeams.map((t, idx) => {
                  const confirmedCount = t.member_count !== undefined ? t.member_count : ((t.members || []).filter(m => m.role !== 'requested' && m.role !== 'pending').length || 1);
                  return `
                    <tr class="hover:bg-surface-terminal/30 ${idx % 2 === 0 ? 'bg-surface-base' : 'bg-surface-card'}">
                      <td class="p-3 font-bold text-text-primary flex items-center gap-2 cursor-pointer hover:text-primary transition-colors group/row" onclick="TeamsView.openTeamHistoryModal('${t.id}')" title="Click to view squad engagement history and score telemetry">
                        <span class="material-symbols-outlined text-primary text-base group-hover/row:scale-110 transition-transform">groups</span>
                        <span class="group-hover/row:underline underline-offset-4">${escapeHtml(t.name)}</span>
                        <span class="material-symbols-outlined text-xs text-text-muted group-hover/row:text-primary opacity-0 group-hover/row:opacity-100 transition-opacity">history</span>
                      </td>
                      <td class="p-3 text-text-secondary">${escapeHtml(t.college || 'Collegiate')}</td>
                      <td class="p-3 text-center text-on-surface">${confirmedCount} / 4</td>
                      <td class="p-3 text-right font-bold text-primary font-mono">${(t.total_points || 0).toLocaleString()} PTS</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          `;
        }
      }
    } catch (e) {
      console.error('Failed to load teams data', e);
      if (list) list.innerHTML = `<div class="text-status-error font-code-sm p-6">Error: ${escapeHtml(e.message)}</div>`;
    }
  },

  renderMyTeamBox(team, idx) {
    const currentUserId = window.state.currentUser?.id;
    const currentUsername = (window.state.currentUser?.username || '').toLowerCase();
    const allMembers = team.members || [];
    const isOwner = (
      (currentUserId && (String(team.owner_id) === String(currentUserId) || String(team.captain_id) === String(currentUserId))) ||
      (currentUsername && (team.owner_username || '').toLowerCase() === currentUsername) ||
      (allMembers.some(m => ((currentUserId && String(m.user_id) === String(currentUserId)) || (currentUsername && (m.username || '').toLowerCase() === currentUsername)) && (m.role === 'owner' || m.role === 'captain')))
    );
    const isCaptain = isOwner || (currentUserId && String(team.captain_id) === String(currentUserId));
    const acceptedMembers = allMembers.filter(m => m.role !== 'requested' && m.role !== 'pending');
    const requestedMembers = allMembers.filter(m => m.role === 'requested' || m.role === 'pending');
    const rosterCount = acceptedMembers.length > 0 ? acceptedMembers.length : (team.member_count || 1);
    const isActiveSquad = this.myTeam && String(this.myTeam.id) === String(team.id);

    return `
      <div class="bg-surface-card rounded-xl p-space-md border ${isActiveSquad ? 'border-primary shadow-[0_0_20px_#10B98122]' : 'border-border-grid shadow-lg'} flex flex-col md:flex-row justify-between items-start md:items-center gap-space-md transition-all hover:border-primary/60">
        <div class="space-y-1.5 flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            ${isActiveSquad ? `
              <span class="badge badge-easy font-mono font-bold flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">verified</span> YOUR ACTIVE SQUAD
              </span>
            ` : ''}
            ${team.my_role === 'owner' || isOwner ? `
              <span class="badge badge-outline font-mono text-primary font-bold flex items-center gap-1 border border-primary/30 bg-primary/10">
                <span class="material-symbols-outlined text-xs">shield</span> SQUAD HEAD / CREATOR
              </span>
            ` : team.my_role === 'captain' ? `
              <span class="badge badge-outline font-mono text-secondary font-bold flex items-center gap-1 border border-secondary/30 bg-secondary/10">
                <span class="material-symbols-outlined text-xs">military_tech</span> SQUAD CAPTAIN
              </span>
            ` : `
              <span class="badge badge-outline font-mono text-secondary font-bold flex items-center gap-1 border border-secondary/30 bg-secondary/10">
                <span class="material-symbols-outlined text-xs">group</span> SQUAD MEMBER
              </span>
            `}
            <span class="font-code-sm text-code-sm text-text-muted font-mono">
              CODE: <strong class="text-primary font-bold tracking-wider">${escapeHtml(team.join_code || team.invite_code || '—')}</strong>
            </span>
          </div>

          <h2 class="font-headline-lg text-headline-lg text-text-primary font-bold flex items-center gap-2 truncate cursor-pointer group/title hover:text-primary transition-colors" onclick="TeamsView.openTeamHistoryModal('${team.id}')" title="Click to view squad engagement history and score telemetry">
            <span class="group-hover/title:underline decoration-primary/50 underline-offset-4">${escapeHtml(team.name)}</span>
            <span class="material-symbols-outlined text-sm text-primary/70 group-hover/title:text-primary group-hover/title:scale-110 transition-transform">analytics</span>
          </h2>

          <p class="font-body-sm text-body-sm text-text-secondary flex items-center gap-2 flex-wrap">
            <span>${escapeHtml(team.college || 'Collegiate Squad')}</span>
            <span>&bull;</span>
            <span>${rosterCount}/4 Operatives Rostered</span>
            ${team.events_participated_count !== undefined ? `
              <span>&bull;</span>
              <span class="text-primary font-mono text-xs font-semibold flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">event_available</span>
                ${team.events_participated_count} Event${team.events_participated_count === 1 ? '' : 's'}
              </span>
            ` : ''}
            ${requestedMembers.length > 0 ? ` <span class="text-amber-400/90 font-mono text-xs font-semibold">(${requestedMembers.length} invite${requestedMembers.length > 1 ? 's' : ''} awaiting acceptance)</span>` : ''}
          </p>

          <!-- Squad Members & Pending Invites Chips -->
          ${allMembers.length > 0 ? `
            <div class="flex flex-wrap items-center gap-2 pt-1.5">
              ${acceptedMembers.map(m => `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-primary/10 border border-primary/30 text-xs font-mono text-primary">
                  <span class="material-symbols-outlined text-xs">person</span>
                  <span>@${escapeHtml(m.username || 'Operative')}</span>
                  <span class="text-[10px] text-text-muted capitalize">(${escapeHtml(m.role || 'member')})</span>
                </span>
              `).join('')}
              ${requestedMembers.map(m => `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-xs font-mono text-amber-400">
                  <span class="material-symbols-outlined text-xs">schedule</span>
                  <span>@${escapeHtml(m.username || 'Operative')}</span>
                  <span class="text-[10px] text-amber-400/80">(Pending)</span>
                  ${isCaptain ? `
                    <button type="button" class="ml-1 text-amber-400/60 hover:text-amber-300 transition-colors cursor-pointer" title="Cancel invitation" onclick="TeamsView.cancelInvite('${team.id}', '${m.user_id}')">
                      <span class="material-symbols-outlined text-xs">close</span>
                    </button>
                  ` : ''}
                </span>
              `).join('')}
            </div>
          ` : ''}
        </div>

        <div class="flex flex-wrap items-center gap-space-sm shrink-0">
          <div class="text-right mr-2">
            <div class="font-headline-lg text-headline-lg text-primary font-bold font-mono">${(team.total_points || 0).toLocaleString()}</div>
            <div class="font-code-sm text-code-sm text-text-muted">TOTAL SQUAD PTS</div>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn btn-outline btn-sm font-mono text-xs border border-border-subtle hover:border-primary text-text-primary hover:text-primary flex items-center gap-1.5 cursor-pointer" onclick="TeamsView.openTeamHistoryModal('${team.id}')" title="View squad engagement history and score telemetry">
              <span class="material-symbols-outlined text-sm text-primary">history</span>
              <span>Event History</span>
            </button>
            ${isCaptain && rosterCount < 4 ? `
              <button class="btn btn-outline btn-sm font-mono text-xs border border-primary/40 text-primary hover:bg-primary/10 flex items-center gap-1.5 cursor-pointer" onclick="TeamsView.openInviteOperativesModal('${team.id}')">
                <span class="material-symbols-outlined text-sm">person_add</span>
                <span>+ Invite Operatives</span>
              </button>
            ` : ''}
            ${isOwner ? `
              <button class="btn btn-danger btn-sm flex items-center gap-1.5 cursor-pointer shadow-sm font-mono text-xs" onclick="TeamsView.deleteTeam('${team.id}')" title="Disband and delete this squad without transferring ownership">
                <span class="material-symbols-outlined text-sm">delete_forever</span>
                <span>Disband Squad</span>
              </button>
            ` : `
              <button class="btn btn-danger btn-sm flex items-center gap-1.5 cursor-pointer font-mono text-xs" onclick="TeamsView.leaveTeam('${team.id}')">
                <span class="material-symbols-outlined text-sm">logout</span>
                <span>Leave Squad</span>
              </button>
            `}
          </div>
        </div>
      </div>
    `;
  },

  async openTeamHistoryModal(teamId) {
    const modalTitle = document.getElementById('teamHistoryModalTitle');
    const modalContent = document.getElementById('teamHistoryModalContent');
    if (!modalContent) return;

    if (modalTitle) modalTitle.textContent = 'Squad Operations History';
    modalContent.innerHTML = `
      <div class="py-12 flex flex-col items-center justify-center gap-3">
        <div class="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin"></div>
        <div class="text-xs font-mono text-text-muted animate-pulse">Decrypting squad engagement records and tournament telemetry...</div>
      </div>
    `;
    if (typeof openModal === 'function') openModal('teamHistoryModal');

    try {
      const history = await window.api.getTeamHistory(teamId);
      if (modalTitle) modalTitle.textContent = `${history.team_name} — Operations History`;

      const membersList = (history.members || []).filter(m => m.role !== 'requested' && m.is_active !== false);

      modalContent.innerHTML = `
        <div class="space-y-4">
          <!-- Squad Overview Banner -->
          <div class="bg-surface-terminal/70 rounded-xl p-4 border border-border-subtle/80 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div class="space-y-1">
              <div class="flex items-center gap-2 flex-wrap">
                <h2 class="font-headline-md text-headline-md text-text-primary font-bold font-mono">${escapeHtml(history.team_name)}</h2>
                <span class="badge badge-outline font-mono text-xs text-primary border border-primary/40 bg-primary/10">
                  HEAD: @${escapeHtml(history.owner_username || 'Operative')}
                </span>
              </div>
              <p class="text-xs text-text-muted font-mono flex items-center gap-2">
                <span>${escapeHtml(history.college || 'Collegiate Squad')}</span>
                <span>&bull;</span>
                <span>${membersList.length}/4 Operatives Rostered</span>
              </p>
            </div>

            <!-- Member chips -->
            <div class="flex flex-wrap gap-1.5">
              ${membersList.map(m => `
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-card border border-border-subtle text-[11px] font-mono text-text-secondary">
                  <span class="material-symbols-outlined text-[11px] text-primary">person</span>
                  <span>@${escapeHtml(m.username)}</span>
                  <span class="text-[10px] text-text-muted">(${escapeHtml(m.role)})</span>
                </span>
              `).join('')}
            </div>
          </div>

          <!-- KPI Metrics Row -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="bg-surface-card rounded-xl p-3 border border-border-subtle/80 text-center">
              <div class="font-code-sm text-code-sm text-text-muted font-mono uppercase">Events Active</div>
              <div class="font-headline-md text-headline-md text-primary font-bold font-mono mt-1">${history.events_participated_count}</div>
              <div class="text-[10px] text-text-muted">Competitions</div>
            </div>
            <div class="bg-surface-card rounded-xl p-3 border border-border-subtle/80 text-center">
              <div class="font-code-sm text-code-sm text-text-muted font-mono uppercase">Total Points</div>
              <div class="font-headline-md text-headline-md text-emerald-400 font-bold font-mono mt-1">${(history.total_score || 0).toLocaleString()}</div>
              <div class="text-[10px] text-text-muted">Defense Score</div>
            </div>
            <div class="bg-surface-card rounded-xl p-3 border border-border-subtle/80 text-center">
              <div class="font-code-sm text-code-sm text-text-muted font-mono uppercase">Solves Logged</div>
              <div class="font-headline-md text-headline-md text-cyan-400 font-bold font-mono mt-1">${history.total_solves}</div>
              <div class="text-[10px] text-text-muted">Flags Breached</div>
            </div>
            <div class="bg-surface-card rounded-xl p-3 border border-border-subtle/80 text-center">
              <div class="font-code-sm text-code-sm text-text-muted font-mono uppercase">Roster Capacity</div>
              <div class="font-headline-md text-headline-md text-text-primary font-bold font-mono mt-1">${membersList.length} / 4</div>
              <div class="text-[10px] text-text-muted">Active Agents</div>
            </div>
          </div>

          <!-- Event Engagements Section -->
          <div class="space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-border-subtle/60">
              <h4 class="font-mono text-xs font-bold uppercase text-text-primary flex items-center gap-1.5">
                <span class="material-symbols-outlined text-sm text-primary">event</span>
                <span>Tournament Engagements (${(history.events || []).length})</span>
              </h4>
              <span class="text-[11px] font-mono text-text-muted">Sorted by most recent deployment</span>
            </div>

            ${(!history.events || history.events.length === 0) ? `
              <div class="bg-surface-terminal/30 border border-border-subtle/60 rounded-xl p-6 text-center space-y-1.5">
                <span class="material-symbols-outlined text-text-muted text-3xl">event_busy</span>
                <div class="font-mono text-xs font-bold text-text-primary uppercase">No Official Operations Logged Yet</div>
                <p class="text-[11px] text-text-muted max-w-sm mx-auto">
                  This squad has not yet participated in official CTF tournaments or live operations. Register this squad for upcoming live events to earn squad defense score.
                </p>
              </div>
            ` : `
              <div class="space-y-3 max-h-[380px] overflow-y-auto scrollbar-thin pr-1">
                ${history.events.map(ev => {
                  const isLive = (ev.status || '').toLowerCase() === 'live';
                  const isEnded = (ev.status || '').toLowerCase() === 'ended';
                  const statusBadgeClass = isLive 
                    ? 'bg-status-success/15 text-status-success border-status-success/30' 
                    : isEnded 
                      ? 'bg-surface-terminal text-text-muted border-border-subtle' 
                      : 'bg-status-info/15 text-status-info border-status-info/30';

                  return `
                    <div class="bg-surface-card rounded-xl p-3.5 border border-border-subtle/80 hover:border-primary/50 transition-all space-y-2">
                      <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                        <div>
                          <div class="flex items-center gap-2 flex-wrap">
                            <span class="font-bold text-sm text-text-primary font-mono">${escapeHtml(ev.event_name)}</span>
                            <span class="badge text-[10px] font-mono uppercase px-2 py-0.5 border ${statusBadgeClass}">
                              ${escapeHtml(ev.status || 'event')}
                            </span>
                          </div>
                          <div class="text-[11px] text-text-muted font-mono mt-0.5">
                            ${ev.start_at ? new Date(ev.start_at).toLocaleDateString() : '—'} &bull; 
                            ${ev.total_teams ? `${ev.total_teams} Squads Contending` : 'Competitive CTF'}
                          </div>
                        </div>

                        <!-- Score & Rank Tag -->
                        <div class="flex items-center gap-3 shrink-0">
                          ${ev.rank ? `
                            <div class="px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-xs font-bold">
                              Rank #${ev.rank}${ev.total_teams ? ` / ${ev.total_teams}` : ''}
                            </div>
                          ` : ''}
                          <div class="text-right">
                            <div class="font-mono font-bold text-base text-primary">${(ev.score || 0).toLocaleString()} PTS</div>
                            <div class="text-[10px] font-mono text-text-muted">${ev.solves_count || 0} Breaches</div>
                          </div>
                        </div>
                      </div>

                      <!-- Solved challenges in this event if any -->
                      ${(ev.solves && ev.solves.length > 0) ? `
                        <div class="pt-2 border-t border-border-subtle/40">
                          <div class="text-[10px] font-mono uppercase text-text-muted font-semibold mb-1">Breached Flags in this Event:</div>
                          <div class="flex flex-wrap gap-1.5">
                            ${ev.solves.map(s => `
                              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-terminal/80 border border-border-subtle text-[10px] font-mono text-text-secondary">
                                <span class="text-primary font-bold">+${s.points_awarded}</span>
                                <span class="text-text-primary font-semibold">${escapeHtml(s.challenge_title)}</span>
                                <span class="text-text-muted">(@${escapeHtml(s.solver_username || 'agent')})</span>
                              </span>
                            `).join('')}
                          </div>
                        </div>
                      ` : ''}
                    </div>
                  `;
                }).join('')}
              </div>
            `}
          </div>
        </div>
      `;
    } catch (err) {
      console.error('Failed to load team history', err);
      modalContent.innerHTML = `
        <div class="p-8 text-center text-status-error font-mono text-xs space-y-2">
          <span class="material-symbols-outlined text-3xl">error</span>
          <div>Failed to retrieve operations history for this squad.</div>
          <div class="text-text-muted">${escapeHtml(err.message || 'Unknown network error')}</div>
        </div>
      `;
    }
  },

  openCreateSquadModal() {
    this.selectedOperatives = [];
    this.searchQuery = '';
    const searchInput = document.getElementById('createTeamSearchOperatives');
    if (searchInput) searchInput.value = '';

    const collegeInput = document.getElementById('createTeamCollege');
    if (collegeInput) {
      collegeInput.value = window.state.currentUser?.college || 'PCCOE';
    }

    this.renderSelectedTray();
    openModal('createTeamModal');
    this.loadAvailableOperatives();
  },

  onSearchOperatives(val) {
    this.searchQuery = (val || '').trim();
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => {
      this.loadAvailableOperatives(this.searchQuery);
    }, 250);
  },

  async loadAvailableOperatives(query = '') {
    const container = document.getElementById('createTeamOperativesList');
    if (!container) return;

    container.innerHTML = `
      <div class="p-4 text-center text-text-muted text-xs font-mono">
        <span class="material-symbols-outlined text-sm animate-spin inline-block align-middle mr-1">sync</span>
        Searching registered operatives...
      </div>
    `;

    try {
      const currentUser = window.state.currentUser;
      const targetCollege = document.getElementById('createTeamCollege')?.value?.trim() || currentUser?.college || '';
      
      const users = await window.api.searchOperatives(query, targetCollege);
      this.availableOperatives = Array.isArray(users) ? users : [];
      this.renderOperativesList();
    } catch (err) {
      container.innerHTML = `
        <div class="p-4 text-center text-status-error text-xs font-mono">
          Error querying platform operatives: ${escapeHtml(err.message)}
        </div>
      `;
    }
  },

  renderOperativesList() {
    const container = document.getElementById('createTeamOperativesList');
    if (!container) return;

    const currentUser = window.state.currentUser;
    const targetCollege = (document.getElementById('createTeamCollege')?.value?.trim() || currentUser?.college || '').toLowerCase();

    // Sort: same college first ("upside"), then other colleges below, then by score / username
    const sorted = [...this.availableOperatives].sort((a, b) => {
      const aCollege = (a.college || '').toLowerCase();
      const bCollege = (b.college || '').toLowerCase();
      const aSame = targetCollege && aCollege && (aCollege.includes(targetCollege) || targetCollege.includes(aCollege));
      const bSame = targetCollege && bCollege && (bCollege.includes(targetCollege) || targetCollege.includes(bCollege));
      
      if (aSame && !bSame) return -1;
      if (!aSame && bSame) return 1;
      return (b.points || 0) - (a.points || 0);
    });

    if (sorted.length === 0) {
      container.innerHTML = `
        <div class="p-4 text-center text-text-muted text-xs font-mono">
          No registered operatives found${this.searchQuery ? ` matching "${escapeHtml(this.searchQuery)}"` : ''}.
        </div>
      `;
      return;
    }

    container.innerHTML = sorted.map(u => {
      const uCollege = (u.college || '').toLowerCase();
      const isSameCollege = targetCollege && uCollege && (
        uCollege.includes(targetCollege) || targetCollege.includes(uCollege)
      );
      const isSelected = this.selectedOperatives.includes(u.username);
      const maxReached = this.selectedOperatives.length >= 3 && !isSelected;

      return `
        <div class="p-2.5 flex items-center justify-between gap-3 hover:bg-surface-terminal/60 transition-colors ${isSameCollege ? 'bg-primary/5 border-l-2 border-primary' : ''}">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-full ${isSameCollege ? 'bg-primary/20 text-primary border border-primary/40' : 'bg-surface-terminal text-text-muted border border-border-subtle'} flex items-center justify-center font-bold text-xs shrink-0 font-mono">
              ${(u.username || 'OP').slice(0, 2).toUpperCase()}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-bold text-xs text-text-primary truncate">@${escapeHtml(u.username)}</span>
                ${isSameCollege ? `
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.2 rounded bg-primary/20 text-primary border border-primary/40 text-[10px] font-mono font-bold">
                    <span class="w-1.5 h-1.5 rounded-full bg-primary"></span> Same College
                  </span>
                ` : ''}
                <span class="text-[10px] text-text-muted font-mono font-semibold">${(u.points || 0).toLocaleString()} PTS</span>
              </div>
              <div class="text-[11px] text-text-muted truncate">
                ${escapeHtml(u.name || '')} &bull; <span class="${isSameCollege ? 'text-primary/90 font-medium' : 'text-text-secondary'}">${escapeHtml(u.college || 'Platform Student')}</span>
              </div>
            </div>
          </div>

          <div class="shrink-0">
            ${isSelected ? `
              <button type="button" class="btn btn-outline btn-sm text-xs py-1 px-2.5 flex items-center gap-1 border-amber-500/60 bg-amber-500/10 text-amber-400 font-mono font-semibold" onclick="TeamsView.toggleSelectOperative('${escapeHtml(u.username)}')">
                <span class="material-symbols-outlined text-xs">schedule</span>
                <span>Request Queued</span>
              </button>
            ` : maxReached ? `
              <span class="text-[11px] text-text-muted font-mono px-2 py-1">Max 3</span>
            ` : `
              <button type="button" class="btn btn-outline btn-sm text-xs py-1 px-2.5 flex items-center gap-1 hover:border-primary hover:text-primary font-mono" onclick="TeamsView.toggleSelectOperative('${escapeHtml(u.username)}')">
                <span class="material-symbols-outlined text-xs">person_add</span>
                <span>+ Send Request</span>
              </button>
            `}
          </div>
        </div>
      `;
    }).join('');
  },

  toggleSelectOperative(username) {
    const idx = this.selectedOperatives.indexOf(username);
    if (idx >= 0) {
      this.selectedOperatives.splice(idx, 1);
    } else {
      if (this.selectedOperatives.length >= 3) {
        showToast('Maximum 3 participants can be requested (squad capacity is 4 including you).', 'warning');
        return;
      }
      this.selectedOperatives.push(username);
    }
    this.renderSelectedTray();
    this.renderOperativesList();
  },

  renderSelectedTray() {
    const tray = document.getElementById('selectedOperativesTray');
    const badgeCount = document.getElementById('selectedOperativesCount');
    const submitBtn = document.getElementById('submitCreateSquadBtn');
    
    if (badgeCount) {
      badgeCount.textContent = `${this.selectedOperatives.length}/3 Requests`;
    }

    if (submitBtn) {
      submitBtn.textContent = this.selectedOperatives.length > 0 
        ? `Form Squad & Send Requests (${this.selectedOperatives.length})`
        : 'Form Squad';
    }

    if (!tray) return;

    if (this.selectedOperatives.length === 0) {
      tray.innerHTML = '';
      tray.classList.add('hidden');
      return;
    }

    tray.classList.remove('hidden');
    tray.innerHTML = `
      <div class="w-full flex items-center justify-between text-xs text-amber-400 font-mono pb-1">
        <span class="flex items-center gap-1">
          <span class="material-symbols-outlined text-xs">outgoing_mail</span>
          <span>Squad Requests to Send (${this.selectedOperatives.length} of 3):</span>
        </span>
        <button type="button" class="text-text-muted hover:text-status-error text-[11px] underline cursor-pointer" onclick="TeamsView.clearAllSelected()">Clear All</button>
      </div>
      <div class="flex flex-wrap items-center gap-1.5">
        ${this.selectedOperatives.map(username => `
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 text-xs font-mono text-amber-400">
            <span class="material-symbols-outlined text-xs">schedule</span>
            <span>@${escapeHtml(username)}</span>
            <span class="text-[10px] text-amber-400/80">(Pending Request)</span>
            <button type="button" class="hover:text-status-error ml-1 font-bold cursor-pointer" title="Remove" onclick="TeamsView.toggleSelectOperative('${escapeHtml(username)}')">&times;</button>
          </span>
        `).join('')}
      </div>
    `;
  },

  clearAllSelected() {
    this.selectedOperatives = [];
    this.renderSelectedTray();
    this.renderOperativesList();
  },

  async handleCreateTeam(e) {
    e.preventDefault();
    const name = document.getElementById('createTeamName').value.trim();
    const college = document.getElementById('createTeamCollege').value.trim();
    const submitBtn = document.getElementById('submitCreateSquadBtn');

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="material-symbols-outlined text-xs animate-spin align-middle mr-1">sync</span> Assembling...`;
    }

    try {
      const created = await window.api.createTeam(name, '', college);

      // Send squad requests with role='requested' so they are pending until accepted
      const inviteQueue = [...this.selectedOperatives];
      if (inviteQueue.length > 0) {
        let sentCount = 0;
        for (const username of inviteQueue) {
          try {
            await window.api.addTeamMember(created.id, { username, role: 'requested' }, 'requested');
            sentCount++;
          } catch (err) {
            console.warn(`Could not send request to ${username}:`, err);
          }
        }
        showToast(`Squad "${created.name}" created! ${sentCount} squad request(s) sent (pending acceptance).`, 'success');
      } else {
        showToast(`Squad "${created.name}" formed successfully!`, 'success');
      }

      this.selectedOperatives = [];
      closeModal('createTeamModal');
      await this.loadData();
      if (window.App) window.App.updateNavbarUserUI();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Form Squad';
      }
    }
  },

  openInviteOperativesModal(teamId) {
    const targetTeam = (this.myCreatedTeams || []).find(t => String(t.id) === String(teamId)) || this.myTeam;
    if (!targetTeam) {
      showToast('You must form a squad first before inviting participants.', 'warning');
      return;
    }
    this.currentInvitingTeamId = targetTeam.id;
    this.activeSquadSearchQuery = '';
    const input = document.getElementById('inviteOperativesSearchInput');
    if (input) input.value = '';
    const titleEl = document.getElementById('inviteOperativesModalTitle');
    if (titleEl) titleEl.textContent = `Invite Participants to ${targetTeam.name}`;
    openModal('inviteOperativesModal');
    this.loadActiveSquadOperatives();
  },

  onSearchInviteOperatives(val) {
    this.activeSquadSearchQuery = (val || '').trim();
    clearTimeout(this._activeSquadSearchTimer);
    this._activeSquadSearchTimer = setTimeout(() => {
      this.loadActiveSquadOperatives(this.activeSquadSearchQuery);
    }, 250);
  },

  async loadActiveSquadOperatives(query = '') {
    const container = document.getElementById('activeSquadOperativesList');
    if (!container) return;

    container.innerHTML = `
      <div class="p-4 text-center text-text-muted text-xs font-mono">
        <span class="material-symbols-outlined text-sm animate-spin inline-block align-middle mr-1">sync</span>
        Searching registered participants...
      </div>
    `;

    try {
      const targetTeam = (this.myCreatedTeams || []).find(t => String(t.id) === String(this.currentInvitingTeamId)) || this.myTeam;
      const targetCollege = targetTeam?.college || window.state.currentUser?.college || '';
      const users = await window.api.searchOperatives(query, targetCollege);
      this.activeSquadOperatives = Array.isArray(users) ? users : [];
      this.renderActiveSquadOperativesList();
    } catch (err) {
      container.innerHTML = `
        <div class="p-4 text-center text-status-error text-xs font-mono">
          Error querying platform operatives: ${escapeHtml(err.message)}
        </div>
      `;
    }
  },

  renderActiveSquadOperativesList() {
    const container = document.getElementById('activeSquadOperativesList');
    if (!container) return;

    const team = (this.myCreatedTeams || []).find(t => String(t.id) === String(this.currentInvitingTeamId)) || this.myTeam;
    const teamMembers = team?.members || [];
    const targetCollege = (team?.college || window.state.currentUser?.college || '').toLowerCase();
    const acceptedCount = teamMembers.filter(m => m.role !== 'requested' && m.role !== 'pending').length;
    const isTeamFull = acceptedCount >= 4;

    // Sort: same college first ("upside"), then others below, then by score
    const sorted = [...this.activeSquadOperatives].sort((a, b) => {
      const aCollege = (a.college || '').toLowerCase();
      const bCollege = (b.college || '').toLowerCase();
      const aSame = targetCollege && aCollege && (aCollege.includes(targetCollege) || targetCollege.includes(aCollege));
      const bSame = targetCollege && bCollege && (bCollege.includes(targetCollege) || targetCollege.includes(bCollege));
      
      if (aSame && !bSame) return -1;
      if (!aSame && bSame) return 1;
      return (b.points || 0) - (a.points || 0);
    });

    if (sorted.length === 0) {
      container.innerHTML = `
        <div class="p-4 text-center text-text-muted text-xs font-mono">
          No registered operatives found${this.activeSquadSearchQuery ? ` matching "${escapeHtml(this.activeSquadSearchQuery)}"` : ''}.
        </div>
      `;
      return;
    }

    container.innerHTML = sorted.map(u => {
      const uCollege = (u.college || '').toLowerCase();
      const isSameCollege = targetCollege && uCollege && (
        uCollege.includes(targetCollege) || targetCollege.includes(uCollege)
      );
      const membership = teamMembers.find(m => m.user_id === u.id || (m.username && m.username.toLowerCase() === u.username.toLowerCase()));
      const isRequested = membership && (membership.role === 'requested' || membership.role === 'pending');
      const isInSquad = membership && !isRequested;

      return `
        <div class="p-2.5 flex items-center justify-between gap-3 hover:bg-surface-terminal/60 transition-colors ${isSameCollege ? 'bg-primary/5 border-l-2 border-primary' : ''}">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-full ${isSameCollege ? 'bg-primary/20 text-primary border border-primary/40' : 'bg-surface-terminal text-text-muted border border-border-subtle'} flex items-center justify-center font-bold text-xs shrink-0 font-mono">
              ${(u.username || 'OP').slice(0, 2).toUpperCase()}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-bold text-xs text-text-primary truncate">@${escapeHtml(u.username)}</span>
                ${isSameCollege ? `
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.2 rounded bg-primary/20 text-primary border border-primary/40 text-[10px] font-mono font-bold">
                    <span class="w-1.5 h-1.5 rounded-full bg-primary"></span> Same College
                  </span>
                ` : ''}
                <span class="text-[10px] text-text-muted font-mono font-semibold">${(u.points || 0).toLocaleString()} PTS</span>
              </div>
              <div class="text-[11px] text-text-muted truncate">
                ${escapeHtml(u.name || '')} &bull; <span class="${isSameCollege ? 'text-primary/90 font-medium' : 'text-text-secondary'}">${escapeHtml(u.college || 'Platform Student')}</span>
              </div>
            </div>
          </div>

          <div class="shrink-0">
            ${isInSquad ? `
              <span class="px-2.5 py-1 rounded bg-accent-emerald/20 text-accent-neon border border-accent-emerald/40 text-[11px] font-mono font-bold flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">check</span> In Squad
              </span>
            ` : isRequested ? `
              <span class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40 text-[11px] font-mono font-bold flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">schedule</span> Requested
              </span>
            ` : isTeamFull ? `
              <span class="text-[11px] text-text-muted font-mono">Squad Full</span>
            ` : `
              <button type="button" class="btn btn-primary btn-sm text-xs py-1 px-2.5 flex items-center gap-1" onclick="TeamsView.sendInviteToOperative('${escapeHtml(u.username)}')">
                <span class="material-symbols-outlined text-xs">person_add</span>
                <span>+ Invite</span>
              </button>
            `}
          </div>
        </div>
      `;
    }).join('');
  },

  async sendInviteToOperative(username) {
    const team = (this.myCreatedTeams || []).find(t => String(t.id) === String(this.currentInvitingTeamId)) || this.myTeam;
    if (!team) return;
    try {
      await window.api.addTeamMember(team.id, username);
      showToast(`Squad request sent to @${username}! (Pending acceptance)`, 'success');
      try {
        const updated = await window.api.getTeam(team.id);
        const idx = (this.myCreatedTeams || []).findIndex(t => String(t.id) === String(team.id));
        if (idx !== -1) this.myCreatedTeams[idx] = updated;
        if (this.myTeam && String(this.myTeam.id) === String(team.id)) this.myTeam = updated;
      } catch (e) {}
      this.renderActiveSquadOperativesList();
      await this.loadData();
    } catch (err) {
      showToast(err.message || 'Failed to send invite', 'error');
    }
  },

  async handleJoinTeam(e) {
    e.preventDefault();
    const code = document.getElementById('joinTeamCode').value.trim();

    try {
      await window.api.joinTeam(code);
      showToast('Enrolled in squad!', 'success');
      closeModal('joinTeamModal');
      await this.loadData();
      if (window.App) window.App.updateNavbarUserUI();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async deleteTeam(teamId) {
    if (!confirm('Are you sure you want to disband and delete this squad? All members will return to competing as independent solo operatives.')) return;

    try {
      await window.api.deleteTeam(teamId);
      showToast('Squad deleted successfully. You are now competing as a solo operative.', 'info');
      await this.loadData();
      if (window.App) window.App.updateNavbarUserUI();
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async leaveTeam(teamId) {
    const currentUserId = window.state.currentUser?.id;
    const currentUsername = (window.state.currentUser?.username || '').toLowerCase();
    const isOwner = (
      (currentUserId && (String(this.myTeam?.owner_id) === String(currentUserId) || String(this.myTeam?.captain_id) === String(currentUserId))) ||
      (currentUsername && (this.myTeam?.owner_username || '').toLowerCase() === currentUsername) ||
      ((this.myTeam?.members || []).some(m => ((currentUserId && String(m.user_id) === String(currentUserId)) || (currentUsername && (m.username || '').toLowerCase() === currentUsername)) && (m.role === 'owner' || m.role === 'captain')))
    );

    if (isOwner) {
      return this.deleteTeam(teamId);
    }

    if (!confirm('Leave this squad? Points contributed will remain credited to the team.')) return;

    try {
      await window.api.leaveTeam(teamId);
      showToast('Withdrawn from squad.', 'info');
      await this.loadData();
      if (window.App) window.App.updateNavbarUserUI();
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async cancelInvite(teamId, userId) {
    if (!confirm('Cancel this squad invitation?')) return;
    try {
      await window.api.removeTeamMember(teamId, userId);
      showToast('Squad invitation canceled.', 'info');
      await this.loadData();
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async acceptInvite(teamId) {
    try {
      await window.api.acceptTeamRequest(teamId);
      showToast('Accepted squad invitation! You are now an active squad member.', 'success');
      await this.loadData();
      if (window.App) window.App.updateNavbarUserUI();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async declineInvite(teamId) {
    if (!confirm('Decline this squad invitation?')) return;
    try {
      await window.api.declineTeamRequest(teamId);
      showToast('Squad invitation declined.', 'info');
      await this.loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }
};

window.TeamsView = TeamsView;

/**
 * OWASP CTF Platform — Admin Control Center View
 * Stitch Screen: "Admin Mission Control & Anti-Cheat Operations" (29fe2948c4d04c08990a4b7f4b9793bf)
 */

const AdminView = {
  currentTab: 'overview',
  analyticsData: null,
  securityEvents: [],
  usersList: [],
  challengeFilterDifficulty: '',
  challengeFilterCategory: '',
  challengeFilterStatus: '',
  challengeSearchQuery: '',
  userSearchQuery: '',
  userFilterRole: '',
  userFilterBanned: '',
  userFilterMuted: '',
  antiCheatFilterStatus: '',
  antiCheatFilterSeverity: '',
  antiCheatSearchQuery: '',
  stagedEventChallenges: [],
  eventChallengeMode: 'new',
  eventCatalogList: [],
  eventsList: [],
  eventFilterStatus: '',
  eventSearchQuery: '',
  activeLiveOpsEventId: null,
  editingEventId: null,
  editingEventData: null,
  editingEventChallenges: [],
  editingStagedChallenges: [],
  editingEventChallengeMode: 'new',
  editingEventCatalogList: [],
  certificateEventId: null,
  certificateEventData: null,
  certificateRecipients: [],
  selectedCertificateIndex: 0,

  async init() {
    const user = window.state.currentUser;
    if (!user || (user.role !== 'admin' && user.role !== 'moderator')) {
      window.location.hash = '#landing';
      showToast('Restricted: Admin or Moderator role required.', 'error');
      return;
    }
    this.render();
    await this.loadOverviewData();
  },

  render() {
    const container = document.getElementById('view-admin');
    if (!container) return;

    container.innerHTML = `
      <div class="flex flex-col w-full pb-space-xl">
        
        <!-- Privileged Access Notification & Telemetry Strip -->
        <div class="px-space-lg py-space-md bg-surface-container-low border-b border-border-grid flex flex-col xl:flex-row xl:items-center xl:justify-between gap-space-md">
          <div class="flex flex-col">
            <div class="flex items-center gap-space-xs">
              <span class="inline-block w-2 h-2 rounded-full bg-primary animate-ping"></span>
              <span class="font-code-sm text-code-sm text-primary tracking-widest uppercase font-bold">
                OWASP CTF ADMIN CONSOLE // PRIVILEGED ACCESS LVL-4
              </span>
              <span class="font-code-sm text-code-sm px-1.5 py-0.5 rounded bg-status-error text-white font-bold">
                ROOT AUTHORIZED
              </span>
            </div>
            <p class="font-body-sm text-body-sm text-text-secondary mt-0.5">
              Real-time multi-cloud telemetry, dynamic decay tuning, container leases, and heuristic anti-cheat operations
            </p>
          </div>

          <!-- Quick Operations Command Palette Buttons -->
          <div class="flex flex-wrap items-center gap-space-xs">
            <button class="btn btn-primary btn-sm" onclick="AdminView.openCreateChallengeModal()">
              <span class="material-symbols-outlined text-base">add_circle</span>
              <span>Create Challenge</span>
            </button>
            <button class="btn btn-outline btn-sm" onclick="AdminView.openCreateEventModal()">
              <span class="material-symbols-outlined text-base">event</span>
              <span>Host CTF Event</span>
            </button>
            <button id="adminFreezeToggleBtn" class="btn btn-outline btn-sm text-status-warning" onclick="AdminView.toggleGlobalFreeze()">
              <span class="material-symbols-outlined text-base">ac_unit</span>
              <span id="adminFreezeLabel">Scoreboard: Live</span>
            </button>
          </div>
        </div>

        <!-- Admin Tab Navigation Pills -->
        <div class="px-space-lg pt-space-md">
          <div class="flex items-center gap-1.5 border-b border-border-subtle pb-space-sm overflow-x-auto">
            <button id="adminTabBtn-overview" class="btn btn-primary btn-sm active" onclick="AdminView.switchTab('overview')">
              <span class="material-symbols-outlined text-sm">dashboard</span> Mission Control
            </button>
            <button id="adminTabBtn-anticheat" class="btn btn-outline btn-sm" onclick="AdminView.switchTab('anticheat')">
              <span class="material-symbols-outlined text-sm">policy</span> Anti-Cheat SOC
            </button>
            <button id="adminTabBtn-challenges" class="btn btn-outline btn-sm" onclick="AdminView.switchTab('challenges')">
              <span class="material-symbols-outlined text-sm">extension</span> Challenge Matrix
            </button>
            <button id="adminTabBtn-events" class="btn btn-outline btn-sm" onclick="AdminView.switchTab('events')">
              <span class="material-symbols-outlined text-sm">calendar_month</span> Event Matrix
            </button>
            <button id="adminTabBtn-users" class="btn btn-outline btn-sm" onclick="AdminView.switchTab('users')">
              <span class="material-symbols-outlined text-sm">manage_accounts</span> User Moderation
            </button>
          </div>
        </div>

        <!-- Dynamic Admin Tab Content Mount -->
        <div id="adminTabMount" class="px-space-lg py-space-md space-y-space-md">
          <div class="text-text-muted font-code-sm text-center py-20">Loading admin operations...</div>
        </div>

      </div>

      <!-- Create Challenge Modal -->
      <div id="createChallengeModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:600px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title">Author New Challenge Vector</h3>
            <button class="modal-close" onclick="closeModal('createChallengeModal')">&times;</button>
          </div>
          <form onsubmit="AdminView.handleCreateChallenge(event)" class="modal-body space-y-4">
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Challenge Title</label>
              <input type="text" id="newChallTitle" required placeholder="e.g. JWT Signature Confusion" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Category</label>
                <select id="newChallCategory" required>
                  <option value="">Select Category</option>
                  ${(window.state.categories || []).map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
                </select>
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Difficulty</label>
                <select id="newChallDifficulty" required>
                  <option value="easy">Easy</option>
                  <option value="medium" selected>Medium</option>
                  <option value="hard">Hard</option>
                  <option value="insane">Insane</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Points Yield</label>
                <input type="number" id="newChallPoints" required value="350" min="0" max="5000" />
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Author Name</label>
                <input type="text" id="newChallAuthor" placeholder="Admin SOC" />
              </div>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Flag Solution</label>
              <input type="text" id="newChallFlag" required placeholder="flag{...}" class="font-mono text-primary" />
            </div>
            <!-- Dynamic Flag Option -->
            <div class="p-3 rounded-lg bg-surface-terminal/40 border border-border-subtle flex items-center justify-between gap-3">
              <div class="flex items-start gap-2.5">
                <span class="material-symbols-outlined text-secondary text-xl mt-0.5">vpn_key</span>
                <div>
                  <label for="newChallIsDynamicFlag" class="font-headline-sm text-xs font-bold text-text-primary cursor-pointer">
                    Dynamic Flag Generation
                  </label>
                  <p class="font-body-sm text-xs text-text-muted mt-0.5">
                    When enabled, cryptographic per-user entropy is applied for flag verification.
                  </p>
                </div>
              </div>
              <label class="relative inline-flex items-center cursor-pointer shrink-0">
                <input type="checkbox" id="newChallIsDynamicFlag" class="sr-only peer" />
                <div class="w-9 h-5 bg-surface-base border border-border-subtle peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-secondary after:border-border-subtle after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary peer-checked:after:bg-black"></div>
              </label>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Scenario Briefing</label>
              <textarea id="newChallDesc" rows="4" required placeholder="Detailed challenge description and vulnerabilities..."></textarea>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">External Challenge URL (Optional)</label>
              <input type="url" id="newChallExternalUrl" placeholder="https://challenge.example.com:9001" />
              <p class="font-body-sm text-body-sm text-text-muted mt-0.5">If set, players will see a Launch Challenge button opening this URL.</p>
            </div>
            <div class="flex justify-end gap-2 pt-2 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('createChallengeModal')">Cancel</button>
              <button type="submit" id="btnSubmitNewChall" class="btn btn-primary">Publish Challenge</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Edit Challenge Modal -->
      <div id="editChallengeModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:600px;">
          <div class="modal-header bg-surface-terminal">
            <h3 class="modal-title flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">edit_note</span>
              Modify Challenge Vector
            </h3>
            <button class="modal-close" onclick="closeModal('editChallengeModal')">&times;</button>
          </div>
          <form onsubmit="AdminView.handleEditChallenge(event)" class="modal-body space-y-4">
            <input type="hidden" id="editChallId" />
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Challenge Title</label>
              <input type="text" id="editChallTitle" required placeholder="e.g. JWT Signature Confusion" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Category</label>
                <select id="editChallCategory" required>
                  <option value="">Select Category</option>
                  ${(window.state.categories || []).map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
                </select>
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Difficulty</label>
                <select id="editChallDifficulty" required>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                  <option value="insane">Insane</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Points Yield</label>
                <input type="number" id="editChallPoints" required min="0" max="5000" />
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Visibility / Status</label>
                <select id="editChallIsActive" required>
                  <option value="true">Active (Visible in Arena)</option>
                  <option value="false">Hidden / Inactive</option>
                </select>
              </div>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">
                Update Flag <span class="text-text-muted text-xs normal-case font-normal">(Leave blank to retain current flag)</span>
              </label>
              <input type="text" id="editChallFlag" placeholder="Enter new flag to change, or leave empty..." class="font-mono text-primary" />
            </div>
            <!-- Dynamic Flag Option -->
            <div class="p-3 rounded-lg bg-surface-terminal/40 border border-border-subtle flex items-center justify-between gap-3">
              <div class="flex items-start gap-2.5">
                <span class="material-symbols-outlined text-secondary text-xl mt-0.5">vpn_key</span>
                <div>
                  <label for="editChallIsDynamicFlag" class="font-headline-sm text-xs font-bold text-text-primary cursor-pointer">
                    Dynamic Flag Generation
                  </label>
                  <p class="font-body-sm text-xs text-text-muted mt-0.5">
                    Enable or disable cryptographic per-user dynamic flag verification for this vector.
                  </p>
                </div>
              </div>
              <label class="relative inline-flex items-center cursor-pointer shrink-0">
                <input type="checkbox" id="editChallIsDynamicFlag" class="sr-only peer" />
                <div class="w-9 h-5 bg-surface-base border border-border-subtle peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-secondary after:border-border-subtle after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary peer-checked:after:bg-black"></div>
              </label>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Scenario Briefing</label>
              <textarea id="editChallDesc" rows="4" required placeholder="Detailed challenge description and vulnerabilities..."></textarea>
            </div>
            <div>
              <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">External Challenge URL (Optional)</label>
              <input type="url" id="editChallExternalUrl" placeholder="https://challenge.example.com:9001" />
              <p class="font-body-sm text-body-sm text-text-muted mt-0.5">If set, players will see a Launch Challenge button opening this URL.</p>
            </div>
            <div class="flex justify-between items-center pt-3 border-t border-border-subtle">
              <button type="button" class="btn btn-outline text-status-error hover:bg-status-error/20 flex items-center gap-1" onclick="AdminView.confirmDeleteChallenge(document.getElementById('editChallId').value, document.getElementById('editChallTitle').value)">
                <span class="material-symbols-outlined text-xs">delete</span>
                <span>Delete</span>
              </button>
              <div class="flex gap-2">
                <button type="button" class="btn btn-outline" onclick="closeModal('editChallengeModal')">Cancel</button>
                <button type="submit" id="btnSubmitEditChall" class="btn btn-primary flex items-center gap-1">
                  <span class="material-symbols-outlined text-xs">save</span>
                  <span>Save Changes</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <!-- Create Event Modal (Orchestrate CTF Competition) -->
      <div id="createEventModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:760px; max-height: 90vh; overflow-y: auto;">
          <div class="modal-header bg-surface-terminal sticky top-0 z-10">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">military_tech</span>
              <h3 class="modal-title">Orchestrate CTF Competition</h3>
            </div>
            <button class="modal-close" onclick="closeModal('createEventModal')">&times;</button>
          </div>
          <form onsubmit="AdminView.handleCreateEvent(event)" class="modal-body space-y-5">
            <!-- 1. Competition Logistics -->
            <div class="space-y-3 pb-3 border-b border-border-subtle">
              <h4 class="font-headline-sm text-sm font-bold text-text-primary flex items-center gap-1.5">
                <span class="material-symbols-outlined text-primary text-base">schedule</span>
                Competition Parameters &amp; Rules
              </h4>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Competition Name</label>
                <input type="text" id="newEventName" required placeholder="OWASP Inter-College CyberStorm CTF" />
              </div>
              <div>
                <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Description / Rules of Engagement</label>
                <textarea id="newEventDesc" rows="2" placeholder="Rules of engagement, collegiate eligibility, scoring rules, and freeze policies..."></textarea>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">Start Time (UTC)</label>
                  <input type="datetime-local" id="newEventStart" required />
                </div>
                <div>
                  <label class="block font-label-sm text-label-sm uppercase text-text-secondary mb-1">End Time (UTC)</label>
                  <input type="datetime-local" id="newEventEnd" required />
                </div>
              </div>
            </div>

            <!-- 2. Assigned Event Challenges Section -->
            <div class="space-y-3">
              <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                <div>
                  <h4 class="font-headline-sm text-sm font-bold text-text-primary flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-secondary text-base">flag</span>
                    Competition Challenge Vectors
                  </h4>
                  <p class="font-body-sm text-xs text-text-muted">Author new event challenges with the full specification or pick from existing repository.</p>
                </div>
                <span id="stagedChallengesCountBadge" class="badge badge-medium text-xs font-mono self-start sm:self-auto">
                  0 Challenges Added
                </span>
              </div>

              <!-- Mode Switcher: Author New vs Pick Existing -->
              <div class="flex items-center gap-2 p-1 bg-surface-terminal/60 rounded-lg border border-border-subtle">
                <button type="button" id="btnEventChallModeNew" class="btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1" onclick="AdminView.switchEventChallengeMode('new')">
                  <span class="material-symbols-outlined text-xs">add_circle</span>
                  <span>Author New Challenge</span>
                </button>
                <button type="button" id="btnEventChallModeExisting" class="btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1" onclick="AdminView.switchEventChallengeMode('existing')">
                  <span class="material-symbols-outlined text-xs">library_add</span>
                  <span>Select from Catalog</span>
                </button>
              </div>

              <!-- Panel A: Author New Challenge (Exact same format as main challenge authoring section) -->
              <div id="eventChallAuthorPanel" class="p-4 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3">
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Challenge Title</label>
                  <input type="text" id="eventNewChallTitle" placeholder="e.g. Session Hijacking via Cache Poisoning" class="text-xs" />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Category</label>
                    <select id="eventNewChallCategory" class="text-xs">
                      <option value="">Select Category</option>
                      ${(window.state.categories || []).map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
                    </select>
                  </div>
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Difficulty</label>
                    <select id="eventNewChallDifficulty" class="text-xs">
                      <option value="easy">Easy</option>
                      <option value="medium" selected>Medium</option>
                      <option value="hard">Hard</option>
                      <option value="insane">Insane</option>
                    </select>
                  </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Points Yield</label>
                    <input type="number" id="eventNewChallPoints" value="350" min="0" max="5000" class="text-xs" />
                  </div>
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Author Name</label>
                    <input type="text" id="eventNewChallAuthor" placeholder="Event SOC" class="text-xs" />
                  </div>
                </div>

                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Flag Solution</label>
                  <input type="text" id="eventNewChallFlag" placeholder="flag{...}" class="font-mono text-primary text-xs" />
                </div>

                <!-- Dynamic Flag Option -->
                <div class="p-2.5 rounded-lg bg-surface-card border border-border-subtle flex items-center justify-between gap-3">
                  <div class="flex items-start gap-2">
                    <span class="material-symbols-outlined text-secondary text-lg mt-0.5">vpn_key</span>
                    <div>
                      <label for="eventNewChallIsDynamicFlag" class="font-headline-sm text-xs font-bold text-text-primary cursor-pointer">
                        Dynamic Flag Generation
                      </label>
                      <p class="font-body-sm text-[11px] text-text-muted">
                        When enabled, cryptographic per-user entropy is applied for flag verification.
                      </p>
                    </div>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer shrink-0">
                    <input type="checkbox" id="eventNewChallIsDynamicFlag" class="sr-only peer" />
                    <div class="w-9 h-5 bg-surface-base border border-border-subtle peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-secondary after:border-border-subtle after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary peer-checked:after:bg-black"></div>
                  </label>
                </div>

                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Scenario Briefing</label>
                  <textarea id="eventNewChallDesc" rows="3" placeholder="Detailed challenge description and vulnerabilities..." class="text-xs"></textarea>
                </div>

                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">External Challenge URL (Optional)</label>
                  <input type="url" id="eventNewChallExternalUrl" placeholder="https://challenge.example.com:9001" class="text-xs" />
                </div>

                <div class="text-right">
                  <button type="button" class="btn btn-secondary btn-sm text-xs flex items-center gap-1 inline-flex" onclick="AdminView.stageNewEventChallenge()">
                    <span class="material-symbols-outlined text-xs">playlist_add</span>
                    <span>Add to Event Staging</span>
                  </button>
                </div>
              </div>

              <!-- Panel B: Select from Existing Catalog -->
              <div id="eventChallCatalogPanel" class="p-4 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3" style="display:none;">
                <div class="flex items-center justify-between gap-2">
                  <input type="text" id="eventCatalogSearch" placeholder="Search catalog challenges..." oninput="AdminView.filterEventCatalogList(this.value)" class="text-xs flex-1" />
                </div>
                <div id="eventCatalogPickerList" class="max-h-48 overflow-y-auto space-y-1.5 pr-1 font-code-sm text-xs">
                  <div class="text-text-muted text-center py-4">Loading challenges catalog...</div>
                </div>
                <div class="text-right">
                  <button type="button" class="btn btn-secondary btn-sm text-xs flex items-center gap-1 inline-flex" onclick="AdminView.stageExistingEventChallenges()">
                    <span class="material-symbols-outlined text-xs">playlist_add_check</span>
                    <span>Attach Selected to Event</span>
                  </button>
                </div>
              </div>

              <!-- Staged Challenges List Table -->
              <div class="space-y-1.5 pt-2">
                <label class="block font-label-sm text-xs uppercase text-text-secondary">Staged Competition Challenges:</label>
                <div id="stagedEventChallengesList" class="space-y-1.5 min-h-[60px] max-h-48 overflow-y-auto">
                  <div class="p-3 text-center text-text-muted font-code-sm text-xs rounded bg-surface-terminal/30 border border-border-subtle">
                    No challenges added to this competition yet. Use the authoring form or catalog picker above.
                  </div>
                </div>
              </div>

            </div>

            <!-- Modal Action Buttons -->
            <div class="flex justify-end gap-2 pt-3 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('createEventModal')">Cancel</button>
              <button type="submit" id="btnSubmitNewEvent" class="btn btn-primary flex items-center gap-1.5">
                <span class="material-symbols-outlined text-base">rocket_launch</span>
                <span>Launch Event</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Edit Event Modal -->
      <div id="editEventModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:850px; max-height:90vh; overflow-y:auto;">
          <div class="modal-header bg-surface-terminal sticky top-0 z-10">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">edit_calendar</span>
              <h3 class="modal-title" id="editEventModalTitle">Edit CTF Event &amp; Challenge Vectors</h3>
            </div>
            <button class="modal-close" onclick="closeModal('editEventModal')">&times;</button>
          </div>
          <form onsubmit="AdminView.handleUpdateEvent(event)" class="modal-body space-y-4">
            <input type="hidden" id="editEventId" />

            <!-- 1. Event Core Metadata -->
            <div class="p-3.5 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3">
              <h4 class="font-headline-sm text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                <span class="material-symbols-outlined text-primary text-sm">tune</span> Event Parameters
              </h4>
              <div>
                <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Event Name</label>
                <input type="text" id="editEventName" required class="text-sm font-semibold" />
              </div>
              <div>
                <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Description / Rules of Engagement</label>
                <textarea id="editEventDesc" rows="2" class="text-xs"></textarea>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Start Time (UTC)</label>
                  <input type="datetime-local" id="editEventStart" required class="text-xs" />
                </div>
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">End Time (UTC)</label>
                  <input type="datetime-local" id="editEventEnd" required class="text-xs" />
                </div>
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Status Override</label>
                  <select id="editEventStatus" class="text-xs">
                    <option value="upcoming">Upcoming</option>
                    <option value="live">Live / Ongoing</option>
                    <option value="ended">Ended / Concluded</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 2. Currently Assigned Event Challenges -->
            <div class="p-3.5 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="font-headline-sm text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-secondary text-sm">flag</span> Assigned Competition Challenges
                </h4>
                <span id="editEventAssignedCountBadge" class="badge badge-medium text-xs font-mono">0 Assigned</span>
              </div>
              <div id="editEventExistingChallengesList" class="space-y-1.5 max-h-48 overflow-y-auto">
                <div class="text-text-muted text-xs text-center py-3 font-code-sm">Loading event challenges...</div>
              </div>
            </div>

            <!-- 3. Add More Challenges to this Event (Same format as main section) -->
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="font-headline-sm text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-primary text-sm">add_circle</span> Add More Challenges to Event
                </h4>
                <span id="editStagedCountBadge" class="badge badge-upcoming text-xs font-mono">0 New Staged</span>
              </div>

              <!-- Mode Switcher -->
              <div class="flex items-center gap-2 p-1 bg-surface-terminal/60 rounded-lg border border-border-subtle">
                <button type="button" id="btnEditEventModeNew" class="btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1" onclick="AdminView.switchEditEventChallengeMode('new')">
                  <span class="material-symbols-outlined text-xs">add_circle</span>
                  <span>Author New Challenge</span>
                </button>
                <button type="button" id="btnEditEventModeExisting" class="btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1" onclick="AdminView.switchEditEventChallengeMode('existing')">
                  <span class="material-symbols-outlined text-xs">library_add</span>
                  <span>Select from Catalog</span>
                </button>
              </div>

              <!-- Author New Challenge Panel -->
              <div id="editEventAuthorPanel" class="p-3.5 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3">
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Challenge Title</label>
                  <input type="text" id="editNewChallTitle" placeholder="e.g. Session Hijacking via Cache Poisoning" class="text-xs" />
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Category</label>
                    <select id="editNewChallCategory" class="text-xs">
                      <option value="">Select Category</option>
                      ${(window.state.categories || []).map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
                    </select>
                  </div>
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Difficulty</label>
                    <select id="editNewChallDifficulty" class="text-xs">
                      <option value="easy">Easy</option>
                      <option value="medium" selected>Medium</option>
                      <option value="hard">Hard</option>
                      <option value="insane">Insane</option>
                    </select>
                  </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Points Yield</label>
                    <input type="number" id="editNewChallPoints" value="350" min="0" max="5000" class="text-xs" />
                  </div>
                  <div>
                    <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Author Name</label>
                    <input type="text" id="editNewChallAuthor" placeholder="Event SOC" class="text-xs" />
                  </div>
                </div>
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Flag Solution</label>
                  <input type="text" id="editNewChallFlag" placeholder="flag{...}" class="font-mono text-primary text-xs" />
                </div>
                <div class="p-2.5 rounded-lg bg-surface-card border border-border-subtle flex items-center justify-between gap-3">
                  <div class="flex items-start gap-2">
                    <span class="material-symbols-outlined text-secondary text-lg mt-0.5">vpn_key</span>
                    <div>
                      <label for="editNewChallIsDynamicFlag" class="font-headline-sm text-xs font-bold text-text-primary cursor-pointer">Dynamic Flag Generation</label>
                      <p class="font-body-sm text-[11px] text-text-muted">Per-user cryptographic flag verification.</p>
                    </div>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer shrink-0">
                    <input type="checkbox" id="editNewChallIsDynamicFlag" class="sr-only peer" />
                    <div class="w-9 h-5 bg-surface-base border border-border-subtle peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-secondary after:border-border-subtle after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary peer-checked:after:bg-black"></div>
                  </label>
                </div>
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">Scenario Briefing</label>
                  <textarea id="editNewChallDesc" rows="2" placeholder="Challenge details..." class="text-xs"></textarea>
                </div>
                <div>
                  <label class="block font-label-sm text-xs uppercase text-text-secondary mb-1">External Challenge URL (Optional)</label>
                  <input type="url" id="editNewChallExternalUrl" placeholder="https://..." class="text-xs" />
                </div>
                <div class="text-right">
                  <button type="button" class="btn btn-secondary btn-sm text-xs flex items-center gap-1 inline-flex" onclick="AdminView.stageEditEventChallenge()">
                    <span class="material-symbols-outlined text-xs">playlist_add</span>
                    <span>Stage Vector for Event</span>
                  </button>
                </div>
              </div>

              <!-- Catalog Picker Panel -->
              <div id="editEventCatalogPanel" class="p-3.5 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-3" style="display:none;">
                <input type="text" id="editEventCatalogSearch" placeholder="Search catalog challenges..." oninput="AdminView.filterEditEventCatalog(this.value)" class="text-xs w-full" />
                <div id="editEventCatalogPickerList" class="max-h-48 overflow-y-auto space-y-1.5 pr-1 font-code-sm text-xs">
                  <div class="text-text-muted text-center py-4">Loading catalog...</div>
                </div>
                <div class="text-right">
                  <button type="button" class="btn btn-secondary btn-sm text-xs flex items-center gap-1 inline-flex" onclick="AdminView.stageEditExistingChallenges()">
                    <span class="material-symbols-outlined text-xs">playlist_add_check</span>
                    <span>Attach Selected to Staging</span>
                  </button>
                </div>
              </div>

              <!-- Newly Staged Challenges List -->
              <div class="space-y-1.5 pt-1">
                <label class="block font-label-sm text-xs uppercase text-text-secondary">Newly Staged Vectors to Add on Save:</label>
                <div id="editEventStagedList" class="space-y-1.5 min-h-[40px] max-h-40 overflow-y-auto">
                  <div class="p-2.5 text-center text-text-muted font-code-sm text-xs rounded bg-surface-terminal/30 border border-border-subtle">
                    No new challenges staged.
                  </div>
                </div>
              </div>
            </div>

            <!-- Modal Action Buttons -->
            <div class="flex justify-end gap-2 pt-3 border-t border-border-subtle">
              <button type="button" class="btn btn-outline" onclick="closeModal('editEventModal')">Cancel</button>
              <button type="submit" id="btnSubmitEditEvent" class="btn btn-primary flex items-center gap-1.5">
                <span class="material-symbols-outlined text-base">save</span>
                <span>Save Event Changes</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Digital Certificate Distribution & Preview Modal (PCCOE OWASP Theme) -->
      <div id="certificateModal" class="modal-backdrop">
        <div class="modal-container" style="max-width:980px; max-height:92vh; overflow-y:auto;">
          <div class="modal-header bg-surface-terminal sticky top-0 z-20 flex justify-between items-center">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-accent-neon">workspace_premium</span>
              <div>
                <h3 class="modal-title text-base font-bold text-text-primary" id="certModalEventTitle">CTF Digital Certificate Command</h3>
                <p class="text-[11px] text-text-muted">Cryptographically verifiable certificates for event participants &amp; winners.</p>
              </div>
            </div>
            <button class="modal-close" onclick="closeModal('certificateModal')">&times;</button>
          </div>

          <div class="p-4 space-y-4">
            <!-- Action Toolbar & Recipient Switcher -->
            <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-surface-terminal/50 rounded-xl border border-border-subtle">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <span class="font-label-sm text-xs text-text-secondary uppercase font-bold shrink-0">Preview Operative:</span>
                <select id="certRecipientSelect" onchange="AdminView.handleCertRecipientChange(this.value)" class="text-xs bg-surface-card border border-border-subtle rounded px-2.5 py-1.5 text-text-primary flex-1 font-mono">
                  <option value="">Select participant to preview certificate...</option>
                </select>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button type="button" id="btnDistributeCertificates" class="btn btn-primary btn-sm text-xs flex items-center gap-1.5 shadow-lg" onclick="AdminView.distributeCertificatesNow()">
                  <span class="material-symbols-outlined text-xs">outgoing_mail</span>
                  <span>Distribute to Registered Gmails</span>
                </button>
                <button type="button" class="btn btn-outline btn-sm text-xs flex items-center gap-1" onclick="AdminView.printCertificate()">
                  <span class="material-symbols-outlined text-xs">print</span>
                  <span>Print / Export</span>
                </button>
              </div>
            </div>

            <!-- Visual Certificate Preview Card (Authentic PCCOE Cyberpunk Design) -->
            <div id="certificateVisualCardMount" class="overflow-x-auto py-2">
              <!-- Rendered Dynamically -->
            </div>

            <!-- Participant Distribution Roster Table -->
            <div class="space-y-2 pt-2">
              <div class="flex items-center justify-between">
                <h4 class="font-headline-sm text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-primary text-sm">mark_email_read</span> Participant Delivery Registry
                </h4>
                <span id="certRecipientCountBadge" class="badge badge-medium text-xs font-mono">0 Participants</span>
              </div>
              <div id="certDeliveryRosterMount" class="max-h-52 overflow-y-auto space-y-1.5 font-code-sm text-xs">
                <!-- Rendered Dynamically -->
              </div>
            </div>

          </div>
        </div>
      </div>
    `;
  },

  async switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll('[id^="adminTabBtn-"]').forEach(b => {
      b.className = 'btn btn-outline btn-sm';
    });
    const activeBtn = document.getElementById(`adminTabBtn-${tab}`);
    if (activeBtn) {
      activeBtn.className = 'btn btn-primary btn-sm active';
    }

    const mount = document.getElementById('adminTabMount');
    if (!mount) return;

    mount.innerHTML = '<div class="text-text-muted font-code-sm text-center py-16">Synchronizing operational telemetry...</div>';

    switch (tab) {
      case 'overview':
        await this.renderOverviewTab(mount);
        break;
      case 'anticheat':
        await this.renderAntiCheatTab(mount);
        break;
      case 'challenges':
        await this.renderChallengesTab(mount);
        break;
      case 'events':
        await this.renderEventsTab(mount);
        break;
      case 'liveops':
        await this.renderLiveOpsTab(mount, this.activeLiveOpsEventId);
        break;
      case 'users':
        await this.renderUsersTab(mount);
        break;
      default:
        await this.renderOverviewTab(mount);
        break;
    }
  },

  /* 1. Mission Control Overview (Stitch Screen 29fe2948c4d04c08990a4b7f4b9793bf) */
  async renderOverviewTab(mount) {

    try {
      const [analytics, rawSecurity] = await Promise.all([
        window.api.adminGetAnalytics().catch(() => ({})),
        window.api.adminListSecurityEvents().catch(() => [])
      ]);

      this.analyticsData = analytics;
      this.securityEvents = (rawSecurity && (rawSecurity.items || rawSecurity.events)) || (Array.isArray(rawSecurity) ? rawSecurity : []);

      mount.innerHTML = `
        <div class="space-y-space-md">
          
          <!-- Live Multi-Cloud Infrastructure Telemetry Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
            
            <!-- Oracle ARM Compute -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">FastAPI Backend Engine</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Python 3.14 Async</span>
                </div>
                <span class="font-code-sm text-code-sm text-primary px-1.5 py-0.5 rounded bg-primary/10 font-bold">ONLINE</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Active Services</span>
                  <span class="text-primary font-semibold">16 Route Modules</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-primary rounded-full" style="width: 100%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-code-sm pt-1 text-text-muted">
                  <span>Registered Users</span>
                  <span class="text-on-surface font-mono">${analytics.total_users || 0} Total</span>
                </div>
              </div>
            </div>

            <!-- Supabase Postgres -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Database Storage</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Supabase PG16</span>
                </div>
                <span class="font-code-sm text-code-sm text-status-info px-1.5 py-0.5 rounded bg-status-info/10 font-bold">HEALTHY</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Tables Footprint</span>
                  <span class="text-status-info font-semibold">23 Schemas Synced</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-status-info rounded-full" style="width: 100%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-code-sm pt-1 text-text-muted">
                  <span>Audit Solves</span>
                  <span class="text-on-surface font-mono">${analytics.total_solves || 0} Solves Recorded</span>
                </div>
              </div>
            </div>

            <!-- Upstash Redis Session Cache -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Rate Limiter Bucket</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Submission Bucket</span>
                </div>
                <span class="font-code-sm text-code-sm text-primary px-1.5 py-0.5 rounded bg-primary/10 font-bold">LOW LATENCY</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Flag Submissions</span>
                  <span class="text-primary font-semibold font-mono">${analytics.total_submissions || 0} Attempts</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-primary rounded-full" style="width: 65%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-code-sm pt-1 text-text-muted">
                  <span>Rate Limit Window</span>
                  <span class="text-on-surface">30 attempts/min</span>
                </div>
              </div>
            </div>

            <!-- Challenge Sandboxes -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Challenge Vectors</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Active Pool</span>
                </div>
                <span class="font-code-sm text-code-sm text-tertiary px-1.5 py-0.5 rounded bg-tertiary/10 font-bold">DYNAMIC</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Available Targets</span>
                  <span class="text-tertiary font-semibold font-mono">${analytics.total_challenges || 0} Challenges</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-tertiary rounded-full" style="width: 80%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-xs text-text-muted">
                  <span>Capacity</span>
                  <span>99.9% Uptime</span>
                </div>
              </div>
            </div>

            <!-- AWS Dynamic Flag Storage -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Flag Secrecy Layer</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">HMAC-SHA256</span>
                </div>
                <span class="font-code-sm text-code-sm text-secondary px-1.5 py-0.5 rounded bg-secondary/10 font-bold">SECURE</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Dynamic Entropy</span>
                  <span class="text-secondary font-semibold">256-bit Seed</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-secondary rounded-full" style="width: 85%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-xs text-text-muted">
                  <span>Tamper Resistance</span>
                  <span>Encrypted Vault</span>
                </div>
              </div>
            </div>

            <!-- Azure Container Apps Sandbox -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Docker Sandboxes</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Rootless gVisor</span>
                </div>
                <span class="font-code-sm text-code-sm text-tertiary px-1.5 py-0.5 rounded bg-tertiary/10 font-bold">ISOLATED</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Network Policy</span>
                  <span class="text-tertiary font-semibold">Egress Blocked</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-tertiary rounded-full" style="width: 92%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-xs text-text-muted">
                  <span>TTL Enforcement</span>
                  <span>Strict Timeout</span>
                </div>
              </div>
            </div>

            <!-- Global CDN Edge Points -->
            <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm flex flex-col justify-between">
              <div class="flex items-start justify-between">
                <div class="flex flex-col">
                  <span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">Heuristic SOC Guard</span>
                  <span class="font-headline-sm text-headline-sm text-text-primary font-bold mt-1">Real-Time</span>
                </div>
                <span class="font-code-sm text-code-sm text-status-warning px-1.5 py-0.5 rounded bg-status-warning/10 font-bold">ARMED</span>
              </div>
              <div class="mt-space-md space-y-space-xs">
                <div class="flex justify-between font-code-sm text-code-sm">
                  <span class="text-text-secondary">Anti-Cheat Engine</span>
                  <span class="text-status-warning font-semibold">Active Sniffer</span>
                </div>
                <div class="w-full h-1.5 bg-surface-terminal rounded-full overflow-hidden">
                  <div class="h-full bg-status-warning rounded-full" style="width: 100%"></div>
                </div>
                <div class="flex justify-between font-code-sm text-xs text-text-muted">
                  <span>Token Velocity</span>
                  <span>Rate Limit Active</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Dynamic Decay Scoring Engine Calibration Bar -->
          <div class="bg-surface-card p-space-md rounded-xl border border-border-grid shadow-sm">
            <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-space-md">
              <div class="flex items-center gap-space-sm">
                <div class="w-10 h-10 rounded-lg bg-surface-terminal border border-border-subtle flex items-center justify-center text-primary">
                  <span class="material-symbols-outlined">trending_down</span>
                </div>
                <div>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Dynamic Decay Flag Scoring Engine</h3>
                  <p class="font-body-sm text-body-sm text-text-secondary">Mathematical point depreciation calibrated against active solve velocity and team solve count.</p>
                </div>
              </div>

              <!-- Quick Param Controls -->
              <div class="flex items-center gap-space-md flex-wrap">
                <div class="bg-surface-terminal px-3 py-1.5 rounded-lg border border-border-subtle">
                  <span class="font-label-sm text-xs text-text-muted block">INITIAL YIELD</span>
                  <span class="font-code-sm text-text-primary font-bold">500 PTS</span>
                </div>
                <div class="bg-surface-terminal px-3 py-1.5 rounded-lg border border-border-subtle">
                  <span class="font-label-sm text-xs text-text-muted block">MINIMUM FLOOR</span>
                  <span class="font-code-sm text-primary font-bold">100 PTS</span>
                </div>
                <div class="bg-surface-terminal px-3 py-1.5 rounded-lg border border-border-subtle">
                  <span class="font-label-sm text-xs text-text-muted block">DECAY CONSTANT (D)</span>
                  <span class="font-code-sm text-secondary font-bold">15 SOLVES</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Split Pane: Anti-Cheat Anomalies & Live Submissions -->
          <div class="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start">
            
            <!-- High Priority Security Anomalies Pane (7 Cols) -->
            <div class="xl:col-span-7 bg-surface-card rounded-xl p-space-md border border-border-grid shadow-sm space-y-space-sm">
              <div class="flex items-center justify-between pb-space-sm border-b border-border-subtle">
                <div class="flex items-center gap-space-xs">
                  <span class="material-symbols-outlined text-status-warning text-xl">policy</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Anti-Cheat Real-Time Anomalies</h3>
                </div>
                <span class="font-code-sm text-code-sm text-status-warning bg-status-warning/10 border border-status-warning/30 px-2 py-0.5 rounded font-bold">
                  ${this.securityEvents.length} INCIDENTS LOGGED
                </span>
              </div>              <!-- Anomalies Feed -->
              <div class="space-y-space-sm pt-1">
                ${this.securityEvents.length === 0 ? `
                  <div class="p-6 rounded-lg bg-surface-terminal/40 text-center text-text-muted font-code-sm">
                    No suspicious anomalies or policy breaches detected across active nodes.
                  </div>
                ` : this.securityEvents.slice(0, 4).map(ev => `
                  <div class="bg-surface-terminal/50 border border-border-subtle p-space-sm rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm hover:bg-surface-terminal/80 transition-colors">
                    <div class="flex items-start gap-space-sm min-w-0 flex-1">
                      <span class="material-symbols-outlined ${ev.severity === 'critical' || ev.severity === 'high' ? 'text-status-error' : 'text-status-warning'} text-xl mt-0.5">crisis_alert</span>
                      <div class="flex flex-col min-w-0 flex-1">
                        <!-- 1. Participant Name, 2. Cheating Type, 3. Severity, 4. Status -->
                        <div class="flex items-center gap-2 flex-wrap">
                          <span class="font-headline-sm text-sm font-bold text-primary flex items-center gap-0.5">
                            <span class="material-symbols-outlined text-sm text-primary">person</span>
                            @${escapeHtml(ev.username || 'unknown')}
                          </span>
                          <span class="font-code-md text-xs font-bold text-text-primary font-mono px-1.5 py-0.5 rounded bg-surface-card border border-border-subtle">
                            ${escapeHtml(ev.event_type || 'SECURITY_EVENT')}
                          </span>
                          <span class="badge ${ev.severity === 'critical' ? 'badge-insane' : ev.severity === 'high' ? 'badge-hard' : ev.severity === 'medium' ? 'badge-medium' : 'badge-easy'} text-[10px] uppercase font-bold">
                            ${escapeHtml(ev.severity || 'low')}
                          </span>
                          <span class="badge ${ev.status === 'open' ? 'badge-upcoming' : ev.status === 'actioned' ? 'badge-insane' : ev.status === 'reviewed' ? 'badge-medium' : 'badge-ended'} text-[10px] uppercase font-bold">
                            ${escapeHtml(ev.status || 'open')}
                          </span>
                        </div>
                        <p class="font-body-sm text-body-sm text-text-secondary mt-1">${escapeHtml(ev.description || 'Heuristic threat trigger.')}</p>
                        <div class="font-code-sm text-xs text-text-muted flex items-center flex-wrap gap-x-3 gap-y-0.5 mt-1">
                          <span>Event: <strong class="text-text-primary">${escapeHtml(ev.event_name || 'CYBER_STORM 2026 (Live CTF Event)')}</strong></span>
                          ${ev.challenge_title ? `<span>Vector: <span class="text-secondary">${escapeHtml(ev.challenge_title)}</span></span>` : ''}
                          <span>Logged: ${formatDate(ev.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    ${ev.status === 'open' ? `
                      <div class="flex items-center gap-2 shrink-0 self-end sm:self-center">
                        <button class="btn btn-danger btn-sm" onclick="AdminView.reviewIncident('${ev.id}', 'actioned', 'Confirmed cheating violation - operative disqualified')">Confirm Cheat</button>
                        <button class="btn btn-outline btn-sm" onclick="AdminView.reviewIncident('${ev.id}', 'dismissed', 'Dismissed as false positive')">Dismiss</button>
                      </div>
                    ` : `
                      <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-surface-terminal text-text-muted border border-border-subtle uppercase font-bold">
                        ${escapeHtml(ev.status || '')}
                      </span>
                    `}
                  </div>
                `).join('')}
              </div>

              <div class="pt-2 text-right">
                <button class="btn btn-outline btn-sm" onclick="AdminView.switchTab('anticheat')">
                  View Full SOC Incident Feed &rarr;
                </button>
              </div>
            </div>

            <!-- Flag Submission Stream (5 Cols) -->
            <div class="xl:col-span-5 bg-surface-card rounded-xl p-space-md border border-border-grid shadow-sm space-y-space-sm">
              <div class="flex items-center justify-between pb-space-sm border-b border-border-subtle">
                <div class="flex items-center gap-space-xs">
                  <span class="material-symbols-outlined text-primary text-xl">stream</span>
                  <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Flag Ingestion Stream</h3>
                </div>
                <span class="flex items-center gap-1.5 font-code-sm text-xs text-primary font-bold">
                  <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                  LIVE FEED
                </span>
              </div>

              <!-- Stream Items -->
              <div class="space-y-space-xs pt-1">
                ${(this.analyticsData && this.analyticsData.recent_submissions && this.analyticsData.recent_submissions.length > 0) ? this.analyticsData.recent_submissions.slice(0, 5).map(sub => `
                  <div class="p-space-xs rounded bg-surface-terminal/30 border border-border-subtle flex items-center justify-between font-code-sm text-code-sm">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="material-symbols-outlined text-xs ${sub.is_correct ? 'text-primary' : 'text-status-error'}">
                        ${sub.is_correct ? 'check_circle' : 'cancel'}
                      </span>
                      <span class="text-text-primary font-medium truncate">${escapeHtml(sub.challenge_title || 'Challenge')}</span>
                    </div>
                    <div class="flex items-center gap-3 shrink-0">
                      <span class="text-text-muted">@${escapeHtml(sub.username || 'user')}</span>
                      <span class="${sub.is_correct ? 'text-primary' : 'text-status-error'} font-bold">${sub.is_correct ? '+' + (sub.points_awarded || 0) : '0'}</span>
                    </div>
                  </div>
                `).join('') : `
                  <div class="p-6 rounded-lg bg-surface-terminal/40 text-center text-text-muted font-code-sm">
                    No recent flag submissions in buffer.
                  </div>
                `}
              </div>
            </div>

          </div>

        </div>
      `;
    } catch (e) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-8">Overview failed: ${escapeHtml(e.message)}</div>`;
    }
  },

  /* 2. Anti-Cheat Dedicated SOC Tab */
  async renderAntiCheatTab(mount) {
    try {
      const res = await window.api.adminListSecurityEvents();
      const secList = (res && (res.items || res.events)) || (Array.isArray(res) ? res : []);
      this.securityEvents = Array.isArray(secList) ? secList : [];

      // Filter security events based on active filters
      const filteredEvents = this.securityEvents.filter(ev => {
        if (this.antiCheatFilterStatus && ev.status !== this.antiCheatFilterStatus) {
          return false;
        }
        if (this.antiCheatFilterSeverity && ev.severity !== this.antiCheatFilterSeverity) {
          return false;
        }
        if (this.antiCheatSearchQuery) {
          const q = this.antiCheatSearchQuery.toLowerCase();
          const matchUser = (ev.username || '').toLowerCase().includes(q);
          const matchType = (ev.event_type || '').toLowerCase().includes(q);
          const matchEvent = (ev.event_name || '').toLowerCase().includes(q);
          const matchDesc = (ev.description || '').toLowerCase().includes(q);
          if (!matchUser && !matchType && !matchEvent && !matchDesc) return false;
        }
        return true;
      });

      const openCount = this.securityEvents.filter(e => e.status === 'open').length;
      const actionedCount = this.securityEvents.filter(e => e.status === 'actioned').length;
      const reviewedCount = this.securityEvents.filter(e => e.status === 'reviewed').length;
      const dismissedCount = this.securityEvents.filter(e => e.status === 'dismissed').length;

      mount.innerHTML = `
        <div class="bg-surface-card rounded-xl p-space-md border border-border-grid shadow-xl space-y-space-md">
          
          <!-- Header Bar -->
          <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-3 pb-space-sm border-b border-border-subtle">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Heuristic Incident Triage</h3>
                <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-surface-terminal border border-border-subtle text-primary font-bold">
                  ${this.securityEvents.length} Incidents
                </span>
                <span class="badge badge-upcoming text-[11px] font-mono">
                  ${openCount} OPEN
                </span>
              </div>
              <p class="font-body-sm text-body-sm text-text-muted mt-0.5">Automated detection of flag sharing, rapid solve spikes, and telemetry collisions in CTF events.</p>
            </div>
            <button class="btn btn-outline btn-sm flex items-center gap-1 self-start sm:self-auto" onclick="AdminView.renderAntiCheatTab(document.getElementById('adminTabMount'))">
              <span class="material-symbols-outlined text-xs">refresh</span>
              <span>Refresh Incidents</span>
            </button>
          </div>

          <!-- Multi-Dimensional Filtering & Search Bar -->
          <div class="bg-surface-terminal/40 p-space-sm rounded-lg border border-border-subtle flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            
            <!-- Status Quick Pills -->
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-label-sm text-xs text-text-muted mr-1 uppercase font-bold">Status:</span>
              <button class="btn btn-sm ${this.antiCheatFilterStatus === '' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-2.5" onclick="AdminView.setAntiCheatFilterStatus('')">
                All (${this.securityEvents.length})
              </button>
              <button class="btn btn-sm ${this.antiCheatFilterStatus === 'open' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-2.5" onclick="AdminView.setAntiCheatFilterStatus('open')">
                Open (${openCount})
              </button>
              <button class="btn btn-sm ${this.antiCheatFilterStatus === 'actioned' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-2.5" onclick="AdminView.setAntiCheatFilterStatus('actioned')">
                Actioned (${actionedCount})
              </button>
              <button class="btn btn-sm ${this.antiCheatFilterStatus === 'reviewed' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-2.5" onclick="AdminView.setAntiCheatFilterStatus('reviewed')">
                Reviewed (${reviewedCount})
              </button>
              <button class="btn btn-sm ${this.antiCheatFilterStatus === 'dismissed' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-2.5" onclick="AdminView.setAntiCheatFilterStatus('dismissed')">
                Dismissed (${dismissedCount})
              </button>
            </div>

            <!-- Severity Filter & Search -->
            <div class="flex items-center gap-2 flex-wrap">
              <div class="flex items-center gap-1">
                <span class="font-label-sm text-xs text-text-muted uppercase font-bold">Severity:</span>
                <select id="antiCheatSeveritySelect" class="font-code-sm text-xs bg-surface-card border border-border-subtle rounded px-2 py-1 text-text-primary" onchange="AdminView.setAntiCheatFilterSeverity(this.value)">
                  <option value="" ${this.antiCheatFilterSeverity === '' ? 'selected' : ''}>All Severities</option>
                  <option value="critical" ${this.antiCheatFilterSeverity === 'critical' ? 'selected' : ''}>Critical</option>
                  <option value="high" ${this.antiCheatFilterSeverity === 'high' ? 'selected' : ''}>High</option>
                  <option value="medium" ${this.antiCheatFilterSeverity === 'medium' ? 'selected' : ''}>Medium</option>
                  <option value="low" ${this.antiCheatFilterSeverity === 'low' ? 'selected' : ''}>Low</option>
                </select>
              </div>

              <div class="relative min-w-[200px] flex-1 sm:flex-none">
                <input 
                  type="text" 
                  placeholder="Search participant, type..." 
                  value="${escapeHtml(this.antiCheatSearchQuery)}"
                  oninput="AdminView.handleAntiCheatSearch(this.value)"
                  class="w-full text-xs font-code-sm bg-surface-card border border-border-subtle rounded px-2.5 py-1 text-text-primary placeholder:text-text-muted"
                />
                ${this.antiCheatSearchQuery ? `
                  <button class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs" onclick="AdminView.handleAntiCheatSearch('')">&times;</button>
                ` : ''}
              </div>
            </div>

          </div>

          <!-- Incidents Feed -->
          <div class="space-y-space-sm">
            ${filteredEvents.length === 0 ? `
              <div class="p-12 text-center text-text-muted font-code-sm bg-surface-terminal/20 rounded-lg flex flex-col items-center justify-center gap-2">
                <span class="material-symbols-outlined text-4xl text-status-success">verified_user</span>
                <span class="text-base font-bold text-text-primary">No incidents match active filters</span>
                <span class="text-xs text-text-muted">All participant telemetry is nominal for this filter criteria.</span>
                ${(this.antiCheatFilterStatus || this.antiCheatFilterSeverity || this.antiCheatSearchQuery) ? `
                  <button class="btn btn-outline btn-sm text-xs mt-2" onclick="AdminView.clearAntiCheatFilters()">
                    Reset Filters
                  </button>
                ` : ''}
              </div>
            ` : filteredEvents.map(ev => `
              <div class="p-space-md rounded-lg bg-surface-terminal/40 border border-border-subtle flex flex-col md:flex-row justify-between items-start md:items-center gap-space-md hover:border-border-grid transition-colors">
                
                <div class="space-y-2 min-w-0 flex-1">
                  <!-- Header Line: 1. Participant Name, 2. Cheating Type, 3. Severity, 4. Status -->
                  <div class="flex items-center flex-wrap gap-2">
                    <span class="font-headline-sm text-base font-bold text-primary flex items-center gap-1">
                      <span class="material-symbols-outlined text-base text-primary">person</span>
                      @${escapeHtml(ev.username || 'unknown')}
                    </span>

                    <span class="font-code-md text-xs font-bold text-text-primary font-mono px-2 py-0.5 rounded bg-surface-card border border-border-subtle">
                      ${escapeHtml(ev.event_type || 'SECURITY_EVENT')}
                    </span>

                    <span class="badge ${ev.severity === 'critical' ? 'badge-insane' : ev.severity === 'high' ? 'badge-hard' : ev.severity === 'medium' ? 'badge-medium' : 'badge-easy'} text-[11px] font-bold uppercase tracking-wider">
                      ${escapeHtml(ev.severity || 'low')}
                    </span>

                    <button type="button" onclick="AdminView.handleStatusBadgeClick('${ev.id}', '${ev.status || 'open'}')" class="badge ${ev.status === 'open' ? 'badge-upcoming border-status-warning/40 text-status-warning' : ev.status === 'actioned' ? 'badge-insane' : ev.status === 'reviewed' ? 'badge-medium' : 'badge-ended'} text-[11px] uppercase cursor-pointer hover:opacity-80 transition-opacity font-bold" title="Click to cycle status or filter">
                      ${escapeHtml(ev.status || 'open')}
                    </button>
                  </div>

                  <!-- Description -->
                  <p class="font-body-sm text-body-sm text-text-secondary">${escapeHtml(ev.description || 'Heuristic threat trigger in live event telemetry.')}</p>

                  <!-- Context: Event Name (Event challenges only), Challenge Vector, IP, Logged Time -->
                  <div class="font-code-sm text-xs text-text-muted flex items-center flex-wrap gap-x-4 gap-y-1 pt-1">
                    <span class="flex items-center gap-1">
                      <span class="material-symbols-outlined text-xs text-primary">emoji_events</span>
                      Event: <strong class="text-text-primary font-semibold">${escapeHtml(ev.event_name || 'CYBER_STORM 2026 (Live CTF Event)')}</strong>
                    </span>
                    ${ev.challenge_title ? `
                      <span class="flex items-center gap-1">
                        <span class="material-symbols-outlined text-xs text-secondary">flag</span>
                        Vector: <span class="text-secondary font-medium">${escapeHtml(ev.challenge_title)}</span>
                      </span>
                    ` : ''}
                    ${ev.ip_address ? `
                      <span class="flex items-center gap-1">
                        <span class="material-symbols-outlined text-xs text-text-muted">router</span>
                        IP: <span class="font-mono text-text-primary">${escapeHtml(ev.ip_address)}</span>
                      </span>
                    ` : ''}
                    <span class="flex items-center gap-1">
                      <span class="material-symbols-outlined text-xs text-text-muted">schedule</span>
                      Logged: ${formatDate(ev.created_at)}
                    </span>
                  </div>
                </div>

                <!-- Action Controls -->
                <div class="flex items-center gap-2 shrink-0 self-end md:self-center">
                  ${ev.status === 'open' ? `
                    <button class="btn btn-danger btn-sm flex items-center gap-1" onclick="AdminView.reviewIncident('${ev.id}', 'actioned', 'Confirmed cheating violation - operative disqualified')">
                      <span class="material-symbols-outlined text-xs">gavel</span>
                      Confirm Cheat
                    </button>
                    <button class="btn btn-outline btn-sm flex items-center gap-1" onclick="AdminView.reviewIncident('${ev.id}', 'dismissed', 'Dismissed as false positive')">
                      <span class="material-symbols-outlined text-xs">check</span>
                      Dismiss
                    </button>
                    <button class="btn btn-outline btn-sm flex items-center gap-1" onclick="AdminView.reviewIncident('${ev.id}', 'reviewed', 'Audited and marked reviewed')">
                      <span class="material-symbols-outlined text-xs">visibility</span>
                      Review
                    </button>
                  ` : `
                    <div class="flex items-center gap-2">
                      <span class="font-code-sm text-xs px-2.5 py-1 rounded bg-surface-terminal border border-border-subtle text-text-muted uppercase font-bold">
                        ${escapeHtml(ev.status || '')}
                      </span>
                      <button class="btn btn-outline btn-sm text-xs flex items-center gap-1" onclick="AdminView.reviewIncident('${ev.id}', 'open', 'Reopened for investigation')">
                        <span class="material-symbols-outlined text-xs">lock_open</span>
                        Re-open
                      </button>
                    </div>
                  `}
                </div>

              </div>
            `).join('')}
          </div>
        </div>
      `;
    } catch (e) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error loading incidents: ${escapeHtml(e.message)}</div>`;
    }
  },

  /* 3. Challenge Matrix Tab */
  async renderChallengesTab(mount) {
    try {
      const [chList, categories] = await Promise.all([
        window.api.getChallenges(),
        (window.state.categories && window.state.categories.length > 0)
          ? Promise.resolve(window.state.categories)
          : window.api.getCategories().then(cats => { window.state.categories = cats; return cats; }).catch(() => [])
      ]);

      this.challengeList = chList || [];
      const catsList = categories || [];

      // Apply Filter predicates
      const filtered = this.challengeList.filter(c => {
        // Difficulty filter
        if (this.challengeFilterDifficulty && c.difficulty !== this.challengeFilterDifficulty) {
          return false;
        }
        // Category / CTF type filter
        if (this.challengeFilterCategory) {
          const matchId = c.category_id === this.challengeFilterCategory || (c.category && c.category.id === this.challengeFilterCategory);
          if (!matchId) return false;
        }
        // Status filter
        if (this.challengeFilterStatus === 'active' && c.is_active === false) {
          return false;
        }
        if (this.challengeFilterStatus === 'deactive' && c.is_active !== false) {
          return false;
        }
        // Search text
        if (this.challengeSearchQuery) {
          const q = this.challengeSearchQuery.toLowerCase().trim();
          const title = (c.title || '').toLowerCase();
          const catName = (c.category?.name || c.category_name || '').toLowerCase();
          const desc = (c.description || '').toLowerCase();
          if (!title.includes(q) && !catName.includes(q) && !desc.includes(q)) {
            return false;
          }
        }
        return true;
      });

      const hasActiveFilters = Boolean(
        this.challengeFilterDifficulty ||
        this.challengeFilterCategory ||
        this.challengeFilterStatus ||
        this.challengeSearchQuery
      );

      const editedIds = new Set(JSON.parse(localStorage.getItem('owasp_edited_challenges') || '[]'));

      mount.innerHTML = `
        <div class="bg-surface-card rounded-xl border border-border-grid shadow-xl overflow-hidden">
          <!-- Top Title & Action Bar -->
          <div class="p-space-md border-b border-border-subtle flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-surface-card">
            <div class="flex items-center gap-3">
              <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Challenge Catalog (${chList.length})</h3>
              <span class="font-code-sm text-code-sm text-text-muted hidden md:inline">Live Vector Orchestration &amp; State Management</span>
            </div>
            <button class="btn btn-primary btn-sm flex items-center gap-1.5 self-start sm:self-auto shadow-md" onclick="AdminView.openCreateChallengeModal()">
              <span class="material-symbols-outlined text-sm">add_circle</span>
              <span>New Challenge</span>
            </button>
          </div>

          <!-- Filter Toolbar: Difficulty, CTF Types / Category, Status, Search -->
          <div class="p-space-md border-b border-border-subtle bg-surface-terminal/40 flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2.5">
              <!-- Search Filter -->
              <div class="relative">
                <span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-sm text-text-muted">search</span>
                <input
                  type="text"
                  id="adminChallSearch"
                  placeholder="Search vector title / text..."
                  value="${escapeHtml(this.challengeSearchQuery || '')}"
                  oninput="AdminView.setChallengeFilter('search', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary pl-8 pr-7 py-1.5 rounded-lg text-xs font-code-sm w-44 sm:w-56 focus:border-primary outline-none transition-all shadow-inner"
                />
                ${this.challengeSearchQuery ? `
                  <button onclick="AdminView.setChallengeFilter('search', '')" class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs font-bold">✕</button>
                ` : ''}
              </div>

              <!-- CTF Types / Category Filter -->
              <div class="flex items-center gap-1.5">
                <label for="adminChallFilterCat" class="text-[11px] uppercase font-bold text-text-muted tracking-wider">CTF Type:</label>
                <select
                  id="adminChallFilterCat"
                  onchange="AdminView.setChallengeFilter('category', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary px-2.5 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary shadow-inner"
                >
                  <option value="">All CTF Types (${chList.length})</option>
                  ${catsList.map(cat => {
                    const count = chList.filter(c => c.category_id === cat.id || (c.category && c.category.id === cat.id)).length;
                    return `<option value="${cat.id}" ${this.challengeFilterCategory === cat.id ? 'selected' : ''}>${escapeHtml(cat.name)} (${count})</option>`;
                  }).join('')}
                </select>
              </div>

              <!-- Difficulty Filter -->
              <div class="flex items-center gap-1.5">
                <label for="adminChallFilterDiff" class="text-[11px] uppercase font-bold text-text-muted tracking-wider">Difficulty:</label>
                <select
                  id="adminChallFilterDiff"
                  onchange="AdminView.setChallengeFilter('difficulty', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary px-2.5 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary shadow-inner"
                >
                  <option value="">All Levels</option>
                  <option value="easy" ${this.challengeFilterDifficulty === 'easy' ? 'selected' : ''}>Easy (${chList.filter(c => c.difficulty === 'easy').length})</option>
                  <option value="medium" ${this.challengeFilterDifficulty === 'medium' ? 'selected' : ''}>Medium (${chList.filter(c => c.difficulty === 'medium').length})</option>
                  <option value="hard" ${this.challengeFilterDifficulty === 'hard' ? 'selected' : ''}>Hard (${chList.filter(c => c.difficulty === 'hard').length})</option>
                  <option value="insane" ${this.challengeFilterDifficulty === 'insane' ? 'selected' : ''}>Insane (${chList.filter(c => c.difficulty === 'insane').length})</option>
                </select>
              </div>

              <!-- Status Filter -->
              <div class="flex items-center gap-1.5">
                <label for="adminChallFilterStatus" class="text-[11px] uppercase font-bold text-text-muted tracking-wider">Status:</label>
                <select
                  id="adminChallFilterStatus"
                  onchange="AdminView.setChallengeFilter('status', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary px-2.5 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary shadow-inner"
                >
                  <option value="">All Statuses</option>
                  <option value="active" ${this.challengeFilterStatus === 'active' ? 'selected' : ''}>Active Only (${chList.filter(c => c.is_active !== false).length})</option>
                  <option value="deactive" ${this.challengeFilterStatus === 'deactive' ? 'selected' : ''}>Deactivated Only (${chList.filter(c => c.is_active === false).length})</option>
                </select>
              </div>

              <!-- Clear Filters Button -->
              ${hasActiveFilters ? `
                <button
                  class="btn btn-outline btn-sm text-xs py-1 px-2.5 text-text-muted hover:text-status-warning hover:border-status-warning flex items-center gap-1 transition-colors"
                  onclick="AdminView.clearChallengeFilters()"
                  title="Reset all active filters"
                >
                  <span class="material-symbols-outlined text-xs">filter_alt_off</span>
                  <span>Clear Filters</span>
                </button>
              ` : ''}
            </div>

            <!-- Match Counter Badge -->
            <div class="flex items-center gap-2">
              <span class="text-xs font-code-sm px-2.5 py-1 rounded bg-surface-terminal border border-border-subtle text-text-secondary">
                Showing <strong class="${filtered.length === chList.length ? 'text-primary' : 'text-status-warning'}">${filtered.length}</strong> / ${chList.length}
              </span>
            </div>
          </div>

          <!-- Challenge Catalog Table -->
          <div class="overflow-x-auto">
            <table class="w-full text-left font-code-sm text-code-sm">
              <thead>
                <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase tracking-wider">
                  <th class="p-3">Challenge Vector</th>
                  <th class="p-3">Category</th>
                  <th class="p-3">Difficulty</th>
                  <th class="p-3">Points</th>
                  <th class="p-3">Solves</th>
                  <th class="p-3">Status</th>
                  <th class="p-3">External URL</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/30">
                ${filtered.length === 0 ? `
                  <tr>
                    <td colspan="8" class="p-12 text-center text-text-muted font-code-sm">
                      <div class="flex flex-col items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-4xl text-text-muted">search_off</span>
                        <span class="text-base font-bold text-text-secondary">No matching challenge vectors found</span>
                        <span class="text-xs text-text-muted">Try adjusting your difficulty, CTF type, status, or search query.</span>
                        ${hasActiveFilters ? `
                          <button class="btn btn-outline btn-sm mt-2 text-xs" onclick="AdminView.clearChallengeFilters()">
                            Clear All Filters
                          </button>
                        ` : ''}
                      </div>
                    </td>
                  </tr>
                ` : filtered.map(c => {
                  const isEdited = editedIds.has(c.id);
                  const isDeactivated = c.is_active === false;
                  return `
                  <tr class="hover:bg-surface-terminal/30 transition-colors ${isDeactivated ? 'opacity-70 bg-status-warning/5' : ''}">
                    <td class="p-3 font-semibold text-text-primary">
                      <div class="flex items-center flex-wrap gap-1.5">
                        <span>${escapeHtml(c.title)}</span>
                        ${c.is_dynamic_flag ? '<span class="text-[10px] uppercase font-bold tracking-wider bg-secondary/20 text-secondary border border-secondary/30 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5" title="Dynamic Flag Enabled"><span class="material-symbols-outlined text-[11px]">vpn_key</span> Dynamic</span>' : ''}
                        ${isEdited ? '<span class="text-[10px] uppercase font-bold tracking-wider bg-primary/20 text-primary border border-primary/30 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5"><span class="material-symbols-outlined text-[11px]">edit</span> Edited</span>' : ''}
                        ${isDeactivated ? '<span class="text-[10px] uppercase font-bold tracking-wider bg-status-warning/20 text-status-warning border border-status-warning/30 px-1.5 py-0.5 rounded">Deactive</span>' : ''}
                      </div>
                    </td>
                    <td class="p-3 text-secondary uppercase font-semibold">${escapeHtml(c.category?.name || c.category_name || 'Jeopardy')}</td>
                    <td class="p-3">${getDifficultyBadge(c.difficulty)}</td>
                    <td class="p-3 text-primary font-bold">${c.points} PTS</td>
                    <td class="p-3 text-on-surface font-mono">${c.solves_count || 0}</td>
                    <td class="p-3">
                      ${!isDeactivated
                        ? '<span class="text-status-success font-semibold flex items-center gap-1.5 text-xs"><span class="w-2 h-2 rounded-full bg-status-success inline-block shadow-sm"></span> Active</span>'
                        : '<span class="text-status-warning font-semibold flex items-center gap-1.5 text-xs"><span class="w-2 h-2 rounded-full bg-status-warning inline-block shadow-sm"></span> Deactive</span>'}
                    </td>
                    <td class="p-3">${c.external_url ? `<a href="${escapeHtml(c.external_url)}" target="_blank" class="text-primary hover:underline font-mono text-xs flex items-center gap-1"><span>🔗</span> Link</a>` : '<span class="text-text-muted">—</span>'}</td>
                    <td class="p-3 text-right whitespace-nowrap">
                      <div class="inline-flex items-center gap-1.5 justify-end">
                        <button class="btn btn-outline btn-sm text-primary hover:bg-primary/20 flex items-center gap-1 py-1 px-2.5" onclick="AdminView.openEditChallengeModal('${c.id}')" title="Modify Challenge">
                          <span class="material-symbols-outlined text-xs">edit</span>
                          <span>Edit</span>
                        </button>
                        ${!isDeactivated ? `
                          <button class="btn btn-outline btn-sm text-status-warning hover:bg-status-warning/20 flex items-center gap-1 py-1 px-2.5" onclick="AdminView.toggleChallengeActive('${c.id}', false, '${escapeHtml(c.title).replace(/'/g, "\\'")}')" title="Deactivate Challenge (Hide from participants)">
                            <span class="material-symbols-outlined text-xs">visibility_off</span>
                            <span>Deactivate</span>
                          </button>
                        ` : `
                          <button class="btn btn-outline btn-sm text-status-success hover:bg-status-success/20 flex items-center gap-1 py-1 px-2.5" onclick="AdminView.toggleChallengeActive('${c.id}', true, '${escapeHtml(c.title).replace(/'/g, "\\'")}')" title="Activate Challenge (Show in arena)">
                            <span class="material-symbols-outlined text-xs">visibility</span>
                            <span>Activate</span>
                          </button>
                        `}
                        <button class="btn btn-outline btn-sm text-status-error hover:bg-status-error/20 flex items-center gap-1 py-1 px-2.5" onclick="AdminView.confirmDeleteChallenge('${c.id}', '${escapeHtml(c.title).replace(/'/g, "\\'")}')" title="Delete Challenge">
                          <span class="material-symbols-outlined text-xs">delete</span>
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                `}).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } catch (e) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error: ${escapeHtml(e.message)}</div>`;
    }
  },


  /* 5. User Moderation Tab */
  async renderUsersTab(mount) {
    try {
      const res = await window.api.adminListUsers(
        this.userSearchQuery || '',
        this.userFilterRole || '',
        this.userFilterBanned !== '' ? this.userFilterBanned : '',
        this.userFilterMuted !== '' ? this.userFilterMuted : '',
        1,
        100
      );
      this.usersList = (res && (res.items || res.users)) || [];
      const totalCount = (res && typeof res.total === 'number') ? res.total : this.usersList.length;

      const hasActiveUserFilters = Boolean(
        this.userSearchQuery ||
        this.userFilterRole ||
        this.userFilterBanned !== '' ||
        this.userFilterMuted !== ''
      );

      mount.innerHTML = `
        <div class="bg-surface-card rounded-xl border border-border-grid shadow-xl overflow-hidden">
          <!-- Top Title Bar -->
          <div class="p-space-md border-b border-border-subtle flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-surface-card">
            <div class="flex items-center gap-3">
              <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">User Management &amp; Moderation</h3>
              <span class="font-code-sm text-code-sm text-text-muted hidden md:inline">RBAC Permissions &amp; Account Governance</span>
            </div>
            <div class="flex items-center gap-2 self-start sm:self-auto">
              <span class="font-code-sm text-code-sm px-3 py-1 rounded bg-surface-terminal border border-border-subtle text-primary font-bold">
                ${totalCount} Accounts Enrolled
              </span>
            </div>
          </div>

          <!-- User Moderation Filter Toolbar -->
          <div class="p-space-md border-b border-border-subtle bg-surface-terminal/40 flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2.5">
              <!-- Search Filter -->
              <div class="relative">
                <span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-sm text-text-muted">search</span>
                <input
                  type="text"
                  placeholder="Search user, email, college..."
                  value="${escapeHtml(this.userSearchQuery || '')}"
                  oninput="AdminView.setUserFilter('search', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary pl-8 pr-7 py-1.5 rounded-lg text-xs font-code-sm w-44 sm:w-60 focus:border-primary outline-none transition-all shadow-inner"
                />
                ${this.userSearchQuery ? `
                  <button onclick="AdminView.setUserFilter('search', '')" class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs font-bold">✕</button>
                ` : ''}
              </div>

              <!-- Role Filter -->
              <div class="flex items-center gap-1.5">
                <label class="text-[11px] uppercase font-bold text-text-muted tracking-wider">Role:</label>
                <select
                  onchange="AdminView.setUserFilter('role', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary px-2.5 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary shadow-inner"
                >
                  <option value="">All Roles</option>
                  <option value="student" ${this.userFilterRole === 'student' ? 'selected' : ''}>Student</option>
                  <option value="moderator" ${this.userFilterRole === 'moderator' ? 'selected' : ''}>Moderator</option>
                  <option value="admin" ${this.userFilterRole === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
              </div>

              <!-- Banned Filter -->
              <div class="flex items-center gap-1.5">
                <label class="text-[11px] uppercase font-bold text-text-muted tracking-wider">Status:</label>
                <select
                  onchange="AdminView.setUserFilter('banned', this.value)"
                  class="bg-surface-terminal border border-border-subtle text-text-primary px-2.5 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary shadow-inner"
                >
                  <option value="">All Statuses</option>
                  <option value="false" ${this.userFilterBanned === 'false' ? 'selected' : ''}>Active / Normal</option>
                  <option value="true" ${this.userFilterBanned === 'true' ? 'selected' : ''}>Banned Only</option>
                </select>
              </div>

              <!-- Clear User Filters -->
              ${hasActiveUserFilters ? `
                <button
                  class="btn btn-outline btn-sm text-xs py-1 px-2.5 text-text-muted hover:text-status-warning hover:border-status-warning flex items-center gap-1 transition-colors"
                  onclick="AdminView.clearUserFilters()"
                  title="Reset user filters"
                >
                  <span class="material-symbols-outlined text-xs">filter_alt_off</span>
                  <span>Clear</span>
                </button>
              ` : ''}
            </div>

            <!-- Matching Count -->
            <div class="flex items-center gap-2">
              <span class="text-xs font-code-sm px-2.5 py-1 rounded bg-surface-terminal border border-border-subtle text-text-secondary">
                Showing <strong class="text-primary">${this.usersList.length}</strong> accounts
              </span>
            </div>
          </div>

          <!-- User Table -->
          <div class="overflow-x-auto">
            <table class="w-full text-left font-code-sm text-code-sm">
              <thead>
                <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase tracking-wider">
                  <th class="p-3">User Operative</th>
                  <th class="p-3">Email</th>
                  <th class="p-3">College / Affiliation</th>
                  <th class="p-3">Role &amp; Permissions</th>
                  <th class="p-3">Score &amp; Solves</th>
                  <th class="p-3">Account State</th>
                  <th class="p-3 text-right">Moderation Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/30">
                ${this.usersList.length === 0 ? `
                  <tr>
                    <td colspan="7" class="p-12 text-center text-text-muted font-code-sm">
                      <div class="flex flex-col items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-4xl text-text-muted">person_search</span>
                        <span class="text-base font-bold text-text-secondary">No enrolled accounts found</span>
                        <span class="text-xs text-text-muted">No users matched your active search query or filter parameters.</span>
                        ${hasActiveUserFilters ? `
                          <button class="btn btn-outline btn-sm mt-2 text-xs" onclick="AdminView.clearUserFilters()">
                            Clear Filters
                          </button>
                        ` : ''}
                      </div>
                    </td>
                  </tr>
                ` : this.usersList.map(u => {
                  const isCurrentAdmin = window.state.currentUser && window.state.currentUser.id === u.id;
                  return `
                  <tr class="hover:bg-surface-terminal/30 transition-colors ${u.is_banned ? 'opacity-65 bg-status-error/5' : ''}">
                    <td class="p-3 font-bold text-text-primary">
                      <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-full bg-primary/20 border border-primary/40 text-primary flex items-center justify-center font-bold text-xs uppercase">
                          ${escapeHtml((u.username || 'U')[0])}
                        </div>
                        <div>
                          <div class="font-bold flex items-center gap-1">
                            @${escapeHtml(u.username)}
                            ${isCurrentAdmin ? '<span class="text-[10px] bg-primary/20 text-primary px-1 rounded font-normal">(You)</span>' : ''}
                          </div>
                          ${u.name ? `<div class="text-[11px] text-text-muted font-normal">${escapeHtml(u.name)}</div>` : ''}
                        </div>
                      </div>
                    </td>
                    <td class="p-3 text-text-secondary font-mono text-xs">${escapeHtml(u.email)}</td>
                    <td class="p-3 text-text-muted">${escapeHtml(u.college || 'Individual Competitor')}</td>
                    <td class="p-3">
                      <div class="flex items-center gap-2">
                        ${getRoleBadge(u.role)}
                        ${!isCurrentAdmin ? `
                          <select
                            onchange="AdminView.changeUserRole('${u.id}', this.value)"
                            class="bg-surface-terminal border border-border-subtle text-text-primary px-1.5 py-0.5 rounded text-[11px] font-code-sm outline-none focus:border-primary"
                            title="Change User Role"
                          >
                            <option value="student" ${u.role === 'student' ? 'selected' : ''}>Student</option>
                            <option value="moderator" ${u.role === 'moderator' ? 'selected' : ''}>Moderator</option>
                            <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                          </select>
                        ` : ''}
                      </div>
                    </td>
                    <td class="p-3 text-text-primary">
                      <div class="flex items-center gap-2">
                        <span class="text-primary font-bold">${u.points || 0} PTS</span>
                        <span class="text-text-muted text-xs font-mono">(${u.solves_count || 0} solves)</span>
                      </div>
                    </td>
                    <td class="p-3">
                      <div class="flex items-center flex-wrap gap-1.5 text-xs">
                        ${u.is_banned ? '<span class="px-1.5 py-0.5 rounded font-bold bg-status-error/20 text-status-error border border-status-error/30">BANNED</span>' : '<span class="text-status-success font-semibold flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-status-success inline-block"></span> Active</span>'}
                        ${u.is_muted ? '<span class="px-1.5 py-0.5 rounded font-bold bg-status-warning/20 text-status-warning border border-status-warning/30">MUTED</span>' : ''}
                      </div>
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                      ${isCurrentAdmin ? '<span class="text-text-muted text-xs italic">Current Session</span>' : `
                        <div class="inline-flex items-center gap-1.5 justify-end">
                          <button
                            class="btn btn-outline btn-sm flex items-center gap-1 py-1 px-2.5 ${u.is_banned ? 'text-primary hover:bg-primary/20' : 'text-status-error hover:bg-status-error/20'}"
                            onclick="AdminView.toggleBanUser('${u.id}', ${!u.is_banned})"
                            title="${u.is_banned ? 'Restore User Access' : 'Ban User Account'}"
                          >
                            <span class="material-symbols-outlined text-xs">${u.is_banned ? 'lock_open' : 'block'}</span>
                            <span>${u.is_banned ? 'Unban' : 'Ban'}</span>
                          </button>
                          <button
                            class="btn btn-outline btn-sm flex items-center gap-1 py-1 px-2.5 ${u.is_muted ? 'text-primary hover:bg-primary/20' : 'text-status-warning hover:bg-status-warning/20'}"
                            onclick="AdminView.toggleMuteUser('${u.id}', ${!u.is_muted})"
                            title="${u.is_muted ? 'Unmute Discussion Access' : 'Mute Discussion Comments'}"
                          >
                            <span class="material-symbols-outlined text-xs">${u.is_muted ? 'volume_up' : 'volume_off'}</span>
                            <span>${u.is_muted ? 'Unmute' : 'Mute'}</span>
                          </button>
                        </div>
                      `}
                    </td>
                  </tr>
                `}).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } catch (e) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error loading users: ${escapeHtml(e.message)}</div>`;
    }
  },

  async changeUserRole(userId, newRole) {
    try {
      await window.api.adminUpdateUser(userId, { role: newRole });
      showToast(`User role updated to ${newRole.toUpperCase()}.`, 'success');
      this.renderUsersTab(document.getElementById('adminTabMount'));
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  setUserFilter(type, value) {
    if (type === 'search') this.userSearchQuery = value;
    if (type === 'role') this.userFilterRole = value;
    if (type === 'banned') this.userFilterBanned = value;
    if (type === 'muted') this.userFilterMuted = value;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderUsersTab(mount);
    }
  },

  clearUserFilters() {
    this.userSearchQuery = '';
    this.userFilterRole = '';
    this.userFilterBanned = '';
    this.userFilterMuted = '';
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderUsersTab(mount);
    }
  },

  setAntiCheatFilterStatus(status) {
    this.antiCheatFilterStatus = status;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderAntiCheatTab(mount);
    }
  },

  setAntiCheatFilterSeverity(severity) {
    this.antiCheatFilterSeverity = severity;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderAntiCheatTab(mount);
    }
  },

  handleAntiCheatSearch(query) {
    this.antiCheatSearchQuery = query;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderAntiCheatTab(mount);
    }
  },

  clearAntiCheatFilters() {
    this.antiCheatFilterStatus = '';
    this.antiCheatFilterSeverity = '';
    this.antiCheatSearchQuery = '';
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderAntiCheatTab(mount);
    }
  },

  async handleStatusBadgeClick(id, currentStatus) {
    if (currentStatus === 'open') {
      await this.reviewIncident(id, 'reviewed', 'Marked reviewed via quick-status action');
    } else {
      await this.reviewIncident(id, 'open', 'Reopened for investigation');
    }
  },

  async reviewIncident(id, status, notes) {
    try {
      await window.api.adminReviewSecurityEvent(id, notes, status);
      showToast(`Incident marked as [${status.toUpperCase()}].`, 'info');
      const mount = document.getElementById('adminTabMount');
      if (mount) {
        if (this.currentTab === 'anticheat') {
          await this.renderAntiCheatTab(mount);
        } else {
          await this.renderOverviewTab(mount);
        }
      }
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async toggleBanUser(userId, ban) {
    try {
      await window.api.adminUpdateUser(userId, { is_banned: ban });
      showToast(`User ${ban ? 'banned' : 'unbanned'}.`, 'info');
      this.renderUsersTab(document.getElementById('adminTabMount'));
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  async toggleMuteUser(userId, mute) {
    try {
      await window.api.adminUpdateUser(userId, { is_muted: mute });
      showToast(`User ${mute ? 'muted' : 'unmuted'}.`, 'info');
      this.renderUsersTab(document.getElementById('adminTabMount'));
    } catch (e) {
      showToast(e.message, 'error');
    }
  },


  openCreateChallengeModal() {
    openModal('createChallengeModal');
  },

  async openCreateEventModal() {
    this.stagedEventChallenges = [];
    
    // Ensure categories exist
    if (!window.state.categories || window.state.categories.length === 0) {
      window.state.categories = await window.api.getCategories().catch(() => []);
    }

    const catSelect = document.getElementById('eventNewChallCategory');
    if (catSelect) {
      catSelect.innerHTML = `
        <option value="">Select Category</option>
        ${(window.state.categories || []).map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
      `;
    }

    // Load existing challenges for the picker
    try {
      this.eventCatalogList = await window.api.getChallenges();
    } catch (_) {
      this.eventCatalogList = [];
    }
    this.filterEventCatalogList('');

    this.switchEventChallengeMode('new');
    this.renderStagedEventChallenges();
    openModal('createEventModal');
  },

  switchEventChallengeMode(mode) {
    this.eventChallengeMode = mode;
    const btnNew = document.getElementById('btnEventChallModeNew');
    const btnExt = document.getElementById('btnEventChallModeExisting');
    const panelNew = document.getElementById('eventChallAuthorPanel');
    const panelExt = document.getElementById('eventChallCatalogPanel');

    if (mode === 'new') {
      if (btnNew) btnNew.className = 'btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (btnExt) btnExt.className = 'btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (panelNew) panelNew.style.display = 'block';
      if (panelExt) panelExt.style.display = 'none';
    } else {
      if (btnNew) btnNew.className = 'btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (btnExt) btnExt.className = 'btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (panelNew) panelNew.style.display = 'none';
      if (panelExt) panelExt.style.display = 'block';
    }
  },

  filterEventCatalogList(query) {
    const picker = document.getElementById('eventCatalogPickerList');
    if (!picker) return;

    const q = (query || '').toLowerCase().trim();
    const list = (this.eventCatalogList || []).filter(c => {
      if (!q) return true;
      const t = (c.title || '').toLowerCase();
      const cat = (c.category?.name || c.category_name || '').toLowerCase();
      return t.includes(q) || cat.includes(q);
    });

    if (list.length === 0) {
      picker.innerHTML = '<div class="p-3 text-center text-text-muted">No challenge vectors matched.</div>';
      return;
    }

    const stagedIds = new Set(this.stagedEventChallenges.filter(s => s.type === 'existing').map(s => s.id));

    picker.innerHTML = list.map(c => {
      const isAlreadyStaged = stagedIds.has(c.id);
      return `
        <label class="flex items-center justify-between p-2 rounded bg-surface-card border border-border-subtle hover:border-primary/50 cursor-pointer transition-colors ${isAlreadyStaged ? 'opacity-50' : ''}">
          <div class="flex items-center gap-2 min-w-0">
            <input type="checkbox" class="event-catalog-checkbox" value="${c.id}" ${isAlreadyStaged ? 'disabled checked' : ''} />
            <div class="flex flex-col min-w-0">
              <span class="font-semibold text-text-primary truncate">${escapeHtml(c.title)}</span>
              <span class="text-[11px] text-text-muted uppercase">${escapeHtml(c.category?.name || c.category_name || 'Jeopardy')} • ${escapeHtml(c.difficulty || 'medium')}</span>
            </div>
          </div>
          <span class="text-primary font-bold shrink-0">${c.points || 100} PTS</span>
        </label>
      `;
    }).join('');
  },

  stageNewEventChallenge() {
    const title = (document.getElementById('eventNewChallTitle')?.value || '').trim();
    const category_id = document.getElementById('eventNewChallCategory')?.value || '';
    const difficulty = document.getElementById('eventNewChallDifficulty')?.value || 'medium';
    const points = parseInt(document.getElementById('eventNewChallPoints')?.value || '350', 10);
    const author = (document.getElementById('eventNewChallAuthor')?.value || '').trim();
    const flag = (document.getElementById('eventNewChallFlag')?.value || '').trim();
    const is_dynamic_flag = document.getElementById('eventNewChallIsDynamicFlag')?.checked || false;
    const description = (document.getElementById('eventNewChallDesc')?.value || '').trim();
    const external_url = (document.getElementById('eventNewChallExternalUrl')?.value || '').trim() || null;

    if (!title) {
      showToast('Please provide a challenge title.', 'warning');
      return;
    }
    if (!category_id) {
      showToast('Please select a challenge category.', 'warning');
      return;
    }
    if (!flag) {
      showToast('Please specify a flag solution.', 'warning');
      return;
    }
    if (!description) {
      showToast('Please provide a scenario briefing.', 'warning');
      return;
    }

    const catObj = (window.state.categories || []).find(c => c.id === category_id);
    const category_name = catObj ? catObj.name : 'Jeopardy';

    this.stagedEventChallenges.push({
      type: 'new',
      title,
      category_id,
      category_name,
      difficulty,
      points,
      author,
      flag,
      is_dynamic_flag,
      description,
      external_url
    });

    // Clear sub-form
    if (document.getElementById('eventNewChallTitle')) document.getElementById('eventNewChallTitle').value = '';
    if (document.getElementById('eventNewChallFlag')) document.getElementById('eventNewChallFlag').value = '';
    if (document.getElementById('eventNewChallDesc')) document.getElementById('eventNewChallDesc').value = '';
    if (document.getElementById('eventNewChallExternalUrl')) document.getElementById('eventNewChallExternalUrl').value = '';
    if (document.getElementById('eventNewChallIsDynamicFlag')) document.getElementById('eventNewChallIsDynamicFlag').checked = false;

    this.renderStagedEventChallenges();
    showToast(`Challenge "${title}" staged for competition.`, 'success');
  },

  stageExistingEventChallenges() {
    const checked = Array.from(document.querySelectorAll('.event-catalog-checkbox:checked:not(:disabled)')).map(el => el.value);
    if (checked.length === 0) {
      showToast('Please select at least one challenge from the catalog.', 'warning');
      return;
    }

    let addedCount = 0;
    const stagedIds = new Set(this.stagedEventChallenges.filter(s => s.type === 'existing').map(s => s.id));

    checked.forEach(id => {
      if (stagedIds.has(id)) return;
      const c = (this.eventCatalogList || []).find(item => item.id === id);
      if (c) {
        this.stagedEventChallenges.push({
          type: 'existing',
          id: c.id,
          title: c.title,
          category_name: c.category?.name || c.category_name || 'Jeopardy',
          difficulty: c.difficulty || 'medium',
          points: c.points || 100,
          is_dynamic_flag: Boolean(c.is_dynamic_flag)
        });
        addedCount++;
      }
    });

    this.filterEventCatalogList(document.getElementById('eventCatalogSearch')?.value || '');
    this.renderStagedEventChallenges();
    showToast(`${addedCount} challenge vector(s) attached to event staging.`, 'success');
  },

  removeStagedEventChallenge(index) {
    if (index >= 0 && index < this.stagedEventChallenges.length) {
      const removed = this.stagedEventChallenges.splice(index, 1)[0];
      this.renderStagedEventChallenges();
      this.filterEventCatalogList(document.getElementById('eventCatalogSearch')?.value || '');
      showToast(`Removed "${removed.title}" from staging list.`, 'info');
    }
  },

  renderStagedEventChallenges() {
    const listEl = document.getElementById('stagedEventChallengesList');
    const badgeEl = document.getElementById('stagedChallengesCountBadge');

    if (badgeEl) {
      badgeEl.textContent = `${this.stagedEventChallenges.length} Challenges Added`;
    }

    if (!listEl) return;

    if (this.stagedEventChallenges.length === 0) {
      listEl.innerHTML = `
        <div class="p-3 text-center text-text-muted font-code-sm text-xs rounded bg-surface-terminal/30 border border-border-subtle">
          No challenges added to this competition yet. Use the authoring form or catalog picker above.
        </div>
      `;
      return;
    }

    listEl.innerHTML = this.stagedEventChallenges.map((item, idx) => `
      <div class="p-2.5 rounded bg-surface-card border border-border-subtle flex items-center justify-between gap-2 font-code-sm text-xs">
        <div class="flex items-center gap-2 min-w-0 flex-wrap">
          <span class="font-bold text-text-primary">${idx + 1}. ${escapeHtml(item.title)}</span>
          <span class="badge ${item.difficulty === 'easy' ? 'badge-easy' : item.difficulty === 'hard' ? 'badge-hard' : item.difficulty === 'insane' ? 'badge-insane' : 'badge-medium'} text-[10px] uppercase">${escapeHtml(item.difficulty || 'medium')}</span>
          <span class="text-secondary uppercase font-semibold text-[11px]">${escapeHtml(item.category_name || 'Jeopardy')}</span>
          ${item.is_dynamic_flag ? '<span class="text-[10px] uppercase font-bold text-secondary bg-secondary/10 px-1.5 py-0.2 rounded border border-secondary/20">Dynamic</span>' : ''}
          <span class="text-text-muted text-[10px] bg-surface-terminal px-1.5 py-0.2 rounded border border-border-subtle uppercase">${item.type === 'new' ? 'New Vector' : 'Catalog'}</span>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="text-primary font-bold font-mono">${item.points || 0} PTS</span>
          <button type="button" class="text-status-error hover:text-white hover:bg-status-error/20 p-1 rounded transition-colors" onclick="AdminView.removeStagedEventChallenge(${idx})" title="Remove from staging">
            <span class="material-symbols-outlined text-xs">close</span>
          </button>
        </div>
      </div>
    `).join('');
  },

  async handleCreateChallenge(e) {
    e.preventDefault();
    const title = document.getElementById('newChallTitle').value.trim();
    const category_id = document.getElementById('newChallCategory').value;
    const difficulty = document.getElementById('newChallDifficulty').value;
    const points = parseInt(document.getElementById('newChallPoints').value, 10);
    const author = document.getElementById('newChallAuthor').value.trim();
    const flag = document.getElementById('newChallFlag').value.trim();
    const description = document.getElementById('newChallDesc').value.trim();
    const external_url = document.getElementById('newChallExternalUrl').value.trim() || null;
    const is_dynamic_flag = document.getElementById('newChallIsDynamicFlag') ? document.getElementById('newChallIsDynamicFlag').checked : false;

    const btn = document.getElementById('btnSubmitNewChall');
    btn.disabled = true;

    try {
      const payload = { title, category_id, difficulty, points, flag, description, is_dynamic_flag };
      if (external_url) payload.external_url = external_url;

      await window.api.request('/api/challenges', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Challenge published successfully!', 'success');
      closeModal('createChallengeModal');
      btn.disabled = false;
      this.switchTab('challenges');
    } catch (err) {
      btn.disabled = false;
      showToast(err.message, 'error');
    }
  },

  async openEditChallengeModal(challengeId) {
    try {
      // Always fetch fresh challenge data from server to ensure accurate values across multiple edits
      const challenge = await window.api.getChallenge(challengeId);

      // Ensure categories exist
      if (!window.state.categories || window.state.categories.length === 0) {
        window.state.categories = await window.api.getCategories().catch(() => []);
      }

      const categorySelect = document.getElementById('editChallCategory');
      if (categorySelect) {
        categorySelect.innerHTML = `
          <option value="">Select Category</option>
          ${(window.state.categories || []).map(c => `
            <option value="${c.id}" ${c.id === challenge.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
          `).join('')}
        `;
      }

      document.getElementById('editChallId').value = challenge.id;
      document.getElementById('editChallTitle').value = challenge.title || '';
      document.getElementById('editChallDifficulty').value = challenge.difficulty || 'medium';
      document.getElementById('editChallPoints').value = challenge.points != null ? challenge.points : 100;
      document.getElementById('editChallIsActive').value = challenge.is_active !== false ? 'true' : 'false';
      if (document.getElementById('editChallIsDynamicFlag')) {
        document.getElementById('editChallIsDynamicFlag').checked = Boolean(challenge.is_dynamic_flag);
      }
      document.getElementById('editChallDesc').value = challenge.description || '';
      document.getElementById('editChallExternalUrl').value = challenge.external_url || '';
      document.getElementById('editChallFlag').value = '';

      const btn = document.getElementById('btnSubmitEditChall');
      if (btn) btn.disabled = false;

      openModal('editChallengeModal');
    } catch (e) {
      showToast('Error loading challenge details: ' + e.message, 'error');
    }
  },

  async handleEditChallenge(e) {
    e.preventDefault();
    const challengeId = document.getElementById('editChallId').value;
    const title = document.getElementById('editChallTitle').value.trim();
    const category_id = document.getElementById('editChallCategory').value;
    const difficulty = document.getElementById('editChallDifficulty').value;
    const points = parseInt(document.getElementById('editChallPoints').value, 10);
    const is_active = document.getElementById('editChallIsActive').value === 'true';
    const is_dynamic_flag = document.getElementById('editChallIsDynamicFlag') ? document.getElementById('editChallIsDynamicFlag').checked : false;
    const flag = document.getElementById('editChallFlag').value.trim();
    const description = document.getElementById('editChallDesc').value.trim();
    const external_url = document.getElementById('editChallExternalUrl').value.trim() || null;

    const btn = document.getElementById('btnSubmitEditChall');
    if (btn) btn.disabled = true;

    try {
      const payload = {
        title,
        category_id,
        difficulty,
        points,
        description,
        is_active,
        is_dynamic_flag,
        external_url
      };
      if (flag) {
        payload.flag = flag;
      }

      await window.api.adminUpdateChallenge(challengeId, payload);
      
      // Track that this specific challenge was edited
      try {
        const editedSet = new Set(JSON.parse(localStorage.getItem('owasp_edited_challenges') || '[]'));
        editedSet.add(challengeId);
        localStorage.setItem('owasp_edited_challenges', JSON.stringify(Array.from(editedSet)));
      } catch (_) {}

      showToast('Challenge updated successfully!', 'success');
      closeModal('editChallengeModal');
      if (btn) btn.disabled = false;
      this.renderChallengesTab(document.getElementById('adminTabMount'));
    } catch (err) {
      if (btn) btn.disabled = false;
      showToast(err.message, 'error');
    }
  },

  async toggleChallengeActive(challengeId, newActiveState, challengeTitle) {
    if (!challengeId) return;
    try {
      await window.api.adminUpdateChallenge(challengeId, { is_active: newActiveState });
      if (newActiveState) {
        showToast(`Challenge "${challengeTitle || 'Vector'}" activated (live in arena).`, 'success');
      } else {
        showToast(`Challenge "${challengeTitle || 'Vector'}" deactivated (hidden from participants).`, 'warning');
      }
      this.renderChallengesTab(document.getElementById('adminTabMount'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  setChallengeFilter(type, value) {
    if (type === 'difficulty') this.challengeFilterDifficulty = value;
    if (type === 'category') this.challengeFilterCategory = value;
    if (type === 'status') this.challengeFilterStatus = value;
    if (type === 'search') this.challengeSearchQuery = value;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderChallengesTab(mount);
    }
  },

  clearChallengeFilters() {
    this.challengeFilterDifficulty = '';
    this.challengeFilterCategory = '';
    this.challengeFilterStatus = '';
    this.challengeSearchQuery = '';
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderChallengesTab(mount);
    }
  },

  async confirmDeleteChallenge(challengeId, challengeTitle) {
    if (!challengeId) return;
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete challenge "${challengeTitle || 'this challenge'}"?\n\nThis will remove the challenge vector and its solves/submissions.`
    );
    if (!confirmed) return;

    try {
      await window.api.adminDeleteChallenge(challengeId, true);
      
      // Remove from edited set if present
      try {
        const editedSet = new Set(JSON.parse(localStorage.getItem('owasp_edited_challenges') || '[]'));
        editedSet.delete(challengeId);
        localStorage.setItem('owasp_edited_challenges', JSON.stringify(Array.from(editedSet)));
      } catch (_) {}

      showToast(`Challenge "${challengeTitle || challengeId}" deleted successfully.`, 'success');
      closeModal('editChallengeModal');
      this.renderChallengesTab(document.getElementById('adminTabMount'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async handleCreateEvent(e) {
    e.preventDefault();
    const name = document.getElementById('newEventName').value.trim();
    const description = document.getElementById('newEventDesc').value.trim();
    const start_at = document.getElementById('newEventStart').value;
    const end_at = document.getElementById('newEventEnd').value;

    const btn = document.getElementById('btnSubmitNewEvent');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> Launching Event &amp; Vectors...';

    try {
      // 1. Create Event
      const eventRes = await window.api.adminCreateEvent({
        name,
        description,
        start_at: new Date(start_at).toISOString(),
        end_at: new Date(end_at).toISOString()
      });

      // 2. Process all staged challenges
      let attachedCount = 0;
      for (let i = 0; i < this.stagedEventChallenges.length; i++) {
        const item = this.stagedEventChallenges[i];
        let challengeId = null;

        if (item.type === 'new') {
          // Author new challenge
          const newChallPayload = {
            title: item.title,
            category_id: item.category_id,
            difficulty: item.difficulty,
            points: item.points,
            flag: item.flag,
            description: item.description,
            is_dynamic_flag: item.is_dynamic_flag
          };
          if (item.external_url) newChallPayload.external_url = item.external_url;

          const createdChall = await window.api.request('/api/challenges', {
            method: 'POST',
            body: JSON.stringify(newChallPayload)
          });
          challengeId = createdChall.id;
        } else {
          challengeId = item.id;
        }

        // Attach to the created event
        if (challengeId && eventRes && eventRes.id) {
          await window.api.adminAddChallengeToEvent(eventRes.id, challengeId, item.points, i + 1).catch(err => {
            console.warn(`Error associating challenge ${challengeId} with event:`, err);
          });
          attachedCount++;
        }
      }

      this.stagedEventChallenges = [];
      showToast(`CTF Event "${name}" launched with ${attachedCount} challenge vectors!`, 'success');
      closeModal('createEventModal');
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-base">rocket_launch</span> Launch Event';
      this.switchTab('overview');
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-base">rocket_launch</span> Launch Event';
      showToast(err.message, 'error');
    }
  },

  async toggleGlobalFreeze() {
    try {
      const events = await window.api.getEvents();
      const liveEvent = events.find(e => e.computed_status === 'live');
      if (!liveEvent) {
        showToast('No live CTF event currently running to toggle freeze on.', 'warning');
        return;
      }

      const newFreeze = !liveEvent.is_frozen;
      await window.api.adminFreezeEvent(liveEvent.id, newFreeze);
      showToast(`Event scoreboard freeze ${newFreeze ? 'ACTIVATED' : 'LIFTED'}.`, 'success');
      const label = document.getElementById('adminFreezeLabel');
      if (label) label.textContent = `Scoreboard: ${newFreeze ? 'Frozen' : 'Live'}`;
    } catch (e) {
      showToast(e.message, 'error');
    }
  },

  /* ==========================================
     4. EVENT MATRIX TAB (Management, Live Ops, Editing, Certificates)
     ========================================== */
  async renderEventsTab(mount) {
    try {
      const rawEvents = await window.api.getEvents().catch(() => []);
      this.eventsList = Array.isArray(rawEvents) ? rawEvents : (rawEvents.items || []);

      const allCount = this.eventsList.length;
      const ongoingCount = this.eventsList.filter(e => e.computed_status === 'live' || e.computed_status === 'ongoing' || e.status === 'live').length;
      const upcomingCount = this.eventsList.filter(e => e.computed_status === 'upcoming' || e.status === 'upcoming').length;
      const endedCount = this.eventsList.filter(e => e.computed_status === 'ended' || e.computed_status === 'concluded' || e.status === 'ended').length;

      const filtered = this.eventsList.filter(e => {
        const cStatus = (e.computed_status || e.status || '').toLowerCase();
        if (this.eventFilterStatus === 'ongoing' && cStatus !== 'live' && cStatus !== 'ongoing') return false;
        if (this.eventFilterStatus === 'upcoming' && cStatus !== 'upcoming') return false;
        if (this.eventFilterStatus === 'ended' && cStatus !== 'ended' && cStatus !== 'concluded') return false;
        if (this.eventSearchQuery) {
          const q = this.eventSearchQuery.toLowerCase().trim();
          const name = (e.name || '').toLowerCase();
          const desc = (e.description || '').toLowerCase();
          if (!name.includes(q) && !desc.includes(q)) return false;
        }
        return true;
      });

      mount.innerHTML = `
        <div class="bg-surface-card rounded-xl border border-border-grid shadow-xl overflow-hidden space-y-4 p-space-md">
          
          <!-- Top Header Strip -->
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-space-sm border-b border-border-subtle">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-headline-sm text-headline-sm text-text-primary font-bold">Event Matrix (${allCount})</h3>
                <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-bold">
                  Collegiate Tournaments
                </span>
                ${ongoingCount > 0 ? `
                  <span class="badge badge-upcoming text-xs font-mono animate-pulse flex items-center gap-1">
                    <span class="w-2 h-2 rounded-full bg-status-success inline-block"></span>
                    ${ongoingCount} ONGOING LIVE
                  </span>
                ` : ''}
              </div>
              <p class="font-body-sm text-body-sm text-text-muted mt-0.5">
                Segregate upcoming, ongoing live battles, and concluded CTFs. Edit competition parameters, vectors, monitor live cheating, and issue certificates.
              </p>
            </div>
            <div class="flex items-center gap-2 self-start sm:self-auto">
              <button class="btn btn-primary btn-sm flex items-center gap-1.5 shadow-md" onclick="AdminView.openCreateEventModal()">
                <span class="material-symbols-outlined text-sm">add_circle</span>
                <span>Host New Event</span>
              </button>
            </div>
          </div>

          <!-- Segregation Filters & Search Toolbar -->
          <div class="p-space-sm rounded-lg bg-surface-terminal/40 border border-border-subtle flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            
            <!-- Segregation Pills: All, Ongoing, Upcoming, Ended -->
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-label-sm text-xs text-text-muted uppercase font-bold mr-1">Filter:</span>
              <button class="btn btn-sm ${this.eventFilterStatus === '' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3" onclick="AdminView.setEventFilter('status', '')">
                All Events (${allCount})
              </button>
              <button class="btn btn-sm ${this.eventFilterStatus === 'ongoing' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3 flex items-center gap-1" onclick="AdminView.setEventFilter('status', 'ongoing')">
                <span class="w-2 h-2 rounded-full bg-status-success ${ongoingCount > 0 ? 'animate-ping' : ''}"></span>
                <span>Ongoing (${ongoingCount})</span>
              </button>
              <button class="btn btn-sm ${this.eventFilterStatus === 'upcoming' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3" onclick="AdminView.setEventFilter('status', 'upcoming')">
                Upcoming (${upcomingCount})
              </button>
              <button class="btn btn-sm ${this.eventFilterStatus === 'ended' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3" onclick="AdminView.setEventFilter('status', 'ended')">
                Ended / Concluded (${endedCount})
              </button>
            </div>

            <!-- Search Field -->
            <div class="relative min-w-[220px]">
              <span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-text-muted">search</span>
              <input
                type="text"
                placeholder="Search event name, rules..."
                value="${escapeHtml(this.eventSearchQuery || '')}"
                oninput="AdminView.setEventFilter('search', this.value)"
                class="w-full bg-surface-card border border-border-subtle text-text-primary pl-8 pr-7 py-1.5 rounded-lg text-xs font-code-sm outline-none focus:border-primary"
              />
              ${this.eventSearchQuery ? `
                <button onclick="AdminView.setEventFilter('search', '')" class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs font-bold">✕</button>
              ` : ''}
            </div>

          </div>

          <!-- Events Table / Card Feed -->
          <div class="overflow-x-auto">
            <table class="w-full text-left font-code-sm text-code-sm">
              <thead>
                <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase tracking-wider">
                  <th class="p-3">Event Name &amp; Timeframe</th>
                  <th class="p-3">Status</th>
                  <th class="p-3">Schedule (UTC &amp; Local)</th>
                  <th class="p-3">Vectors</th>
                  <th class="p-3">Operatives</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/30">
                ${filtered.length === 0 ? `
                  <tr>
                    <td colspan="6" class="p-12 text-center text-text-muted font-code-sm">
                      <div class="flex flex-col items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-4xl text-text-muted">event_busy</span>
                        <span class="text-base font-bold text-text-secondary">No events match the selected filter</span>
                        <span class="text-xs text-text-muted">Try adjusting your segregation filter or search query.</span>
                        ${(this.eventFilterStatus || this.eventSearchQuery) ? `
                          <button class="btn btn-outline btn-sm mt-2 text-xs" onclick="AdminView.clearEventFilters()">
                            Reset Filters
                          </button>
                        ` : ''}
                      </div>
                    </td>
                  </tr>
                ` : filtered.map(ev => {
                  const cStatus = (ev.computed_status || ev.status || '').toLowerCase();
                  const isOngoing = cStatus === 'live' || cStatus === 'ongoing';
                  const isUpcoming = cStatus === 'upcoming';
                  const isEnded = cStatus === 'ended' || cStatus === 'concluded';

                  const startDate = ev.start_at ? new Date(ev.start_at) : null;
                  const endDate = ev.end_at ? new Date(ev.end_at) : null;

                  const startFormatted = startDate ? startDate.toLocaleString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
                  }) : 'TBD';

                  const endFormatted = endDate ? endDate.toLocaleString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
                  }) : 'TBD';

                  let statusBadge = '';
                  if (isOngoing) {
                    statusBadge = `
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-status-success/20 text-status-success border border-status-success/40 text-xs font-bold animate-pulse">
                        <span class="w-2 h-2 rounded-full bg-status-success animate-ping"></span>
                        ONGOING LIVE
                      </span>
                    `;
                  } else if (isUpcoming) {
                    statusBadge = `
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 text-xs font-bold">
                        <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                        UPCOMING
                      </span>
                    `;
                  } else {
                    statusBadge = `
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-terminal text-text-muted border border-border-subtle text-xs font-semibold">
                        <span class="w-1.5 h-1.5 rounded-full bg-text-muted"></span>
                        ENDED
                      </span>
                    `;
                  }

                  return `
                    <tr class="hover:bg-surface-terminal/30 transition-colors ${isOngoing ? 'bg-primary/5' : ''}">
                      
                      <!-- Event Info -->
                      <td class="p-3">
                        <div class="flex flex-col">
                          <span class="font-bold text-text-primary text-sm">${escapeHtml(ev.name)}</span>
                          ${ev.description ? `<span class="text-[11px] text-text-muted truncate max-w-xs mt-0.5">${escapeHtml(ev.description)}</span>` : ''}
                        </div>
                      </td>

                      <!-- Status -->
                      <td class="p-3">
                        ${statusBadge}
                      </td>

                      <!-- Schedule -->
                      <td class="p-3 text-xs">
                        <div class="flex flex-col gap-0.5">
                          <span class="text-text-secondary"><strong class="text-text-muted">Start:</strong> ${startFormatted}</span>
                          <span class="text-text-secondary"><strong class="text-text-muted">End:</strong> ${endFormatted}</span>
                        </div>
                      </td>

                      <!-- Challenge Count -->
                      <td class="p-3 font-semibold text-secondary">
                        ${ev.challenge_count || 0} Vectors
                      </td>

                      <!-- Participants -->
                      <td class="p-3 font-semibold text-primary">
                        ${ev.participant_count || 0} Enrolled
                      </td>

                      <!-- Actions -->
                      <td class="p-3 text-right whitespace-nowrap">
                        <div class="inline-flex items-center gap-1.5 justify-end">
                          
                          <!-- Live Ops for Ongoing events -->
                          ${isOngoing ? `
                            <button
                              class="btn btn-primary btn-sm text-xs py-1 px-2.5 flex items-center gap-1 shadow-md animate-pulse"
                              onclick="AdminView.openLiveOpsView('${ev.id}')"
                              title="Open Live Leaderboard, Live Cheating Telemetry & Ban Controls"
                            >
                              <span class="material-symbols-outlined text-xs">radar</span>
                              <span>Live Ops</span>
                            </button>
                          ` : ''}

                          <!-- Monitor / Post-Mortem for Ended events only (not upcoming) -->
                          ${isEnded ? `
                            <button
                              class="btn btn-outline btn-sm text-xs py-1 px-2 text-text-secondary hover:text-text-primary flex items-center gap-1"
                              onclick="AdminView.openLiveOpsView('${ev.id}')"
                              title="View Event Leaderboard, Cheating & Participants"
                            >
                              <span class="material-symbols-outlined text-xs">monitoring</span>
                              <span>Monitor</span>
                            </button>
                          ` : ''}

                          <!-- Edit Event Option -->
                          <button
                            class="btn btn-outline btn-sm text-xs py-1 px-2 text-primary hover:bg-primary/20 flex items-center gap-1"
                            onclick="AdminView.openEditEventModal('${ev.id}')"
                            title="Edit Day, Date, Details & Challenges in this Event"
                          >
                            <span class="material-symbols-outlined text-xs">edit</span>
                            <span>Edit</span>
                          </button>

                          <!-- Delete Event -->
                          <button
                            class="btn btn-outline btn-sm text-xs py-1 px-2 text-status-error hover:bg-status-error/20 flex items-center gap-1"
                            onclick="AdminView.confirmDeleteEvent('${ev.id}', '${escapeHtml(ev.name).replace(/'/g, "\\'")}')"
                            title="Delete Event"
                          >
                            <span class="material-symbols-outlined text-xs">delete</span>
                          </button>

                        </div>
                      </td>

                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

        </div>
      `;
    } catch (err) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error loading Event Matrix: ${escapeHtml(err.message)}</div>`;
    }
  },

  setEventFilter(type, value) {
    if (type === 'status') this.eventFilterStatus = value;
    if (type === 'search') this.eventSearchQuery = value;
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderEventsTab(mount);
    }
  },

  clearEventFilters() {
    this.eventFilterStatus = '';
    this.eventSearchQuery = '';
    const mount = document.getElementById('adminTabMount');
    if (mount) {
      this.renderEventsTab(mount);
    }
  },

  /* ==========================================
     5. ONGOING EVENT COMMAND CENTER / LIVE OPS DEEP DIVE
     ========================================== */
  async openLiveOpsView(eventId) {
    this.activeLiveOpsEventId = eventId;
    await this.switchTab('liveops');
  },

  async renderLiveOpsTab(mount, eventId) {
    if (!eventId) {
      mount.innerHTML = `
        <div class="p-12 text-center text-text-muted font-code-sm bg-surface-card rounded-xl border border-border-subtle space-y-3">
          <span class="material-symbols-outlined text-4xl text-status-warning">error</span>
          <div class="text-base font-bold text-text-primary">No Event Selected</div>
          <p class="text-xs text-text-muted">Please select an event from the Event Matrix.</p>
          <button class="btn btn-primary btn-sm text-xs mt-2" onclick="AdminView.switchTab('events')">Back to Event Matrix</button>
        </div>
      `;
      return;
    }

    try {
      mount.innerHTML = '<div class="text-text-muted font-code-sm text-center py-16">Initializing Event Telemetry &amp; Audit Data...</div>';

      const eventData = await window.api.getEvent(eventId).catch(() => null);
      if (!eventData) {
        throw new Error('Could not load event data.');
      }

      const isOngoing = eventData.computed_status === 'live' || eventData.computed_status === 'ongoing' || eventData.status === 'live';

      // If the event has ended, render the dedicated Ended Event Report & Audit Post-Mortem
      if (!isOngoing) {
        await this.renderEndedEventReport(mount, eventId, eventData);
        return;
      }

      const [leaderboardData, participantsData, challengesData, rawSecurity] = await Promise.all([
        window.api.getEventLeaderboard(eventId).catch(() => ({ entries: [] })),
        window.api.getEventParticipants(eventId).catch(() => []),
        window.api.getEventChallenges(eventId).catch(() => []),
        window.api.adminListSecurityEvents().catch(() => [])
      ]);

      const leaderboardEntries = leaderboardData.entries || leaderboardData.items || [];
      const participantsList = Array.isArray(participantsData) ? participantsData : [];
      const secList = (rawSecurity && (rawSecurity.items || rawSecurity.events)) || (Array.isArray(rawSecurity) ? rawSecurity : []);

      // Filter security incidents relevant to this event
      const eventSecIncidents = secList.filter(ev => {
        if (ev.event_id && ev.event_id === eventId) return true;
        if (ev.event_name && eventData.name && ev.event_name.toLowerCase() === eventData.name.toLowerCase()) return true;
        return true;
      });

      mount.innerHTML = `
        <div class="space-y-4">
          
          <!-- Live Ops Tactical Header -->
          <div class="p-4 rounded-xl bg-surface-card border border-border-grid shadow-xl flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            
            <div class="flex items-start gap-3">
              <button class="btn btn-outline btn-sm text-xs p-2 shrink-0" onclick="AdminView.switchTab('events')" title="Back to Event Matrix">
                <span class="material-symbols-outlined text-sm">arrow_back</span>
              </button>
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <h2 class="font-headline-sm text-headline-sm text-text-primary font-black">${escapeHtml(eventData.name)}</h2>
                  <span class="px-2.5 py-0.5 rounded-full bg-status-success/20 text-status-success border border-status-success/50 text-xs font-bold animate-pulse flex items-center gap-1">
                    <span class="w-2 h-2 rounded-full bg-status-success animate-ping"></span>
                    LIVE COMBAT
                  </span>
                  <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-surface-terminal text-text-secondary border border-border-subtle">
                    ${challengesData.length} Vectors
                  </span>
                  <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-surface-terminal text-primary border border-border-subtle">
                    ${participantsList.length} Registered Operatives
                  </span>
                </div>
                <p class="font-body-sm text-xs text-text-muted mt-1">
                  Live Operations Command Center: Monitor leaderboard movements, catch heuristic cheating incidents, ban participants dynamically, and issue certificates.
                </p>
              </div>
            </div>

            <!-- Header Action Controls -->
            <div class="flex items-center gap-2 flex-wrap">
              <button class="btn btn-outline btn-sm text-xs flex items-center gap-1" onclick="AdminView.renderLiveOpsTab(document.getElementById('adminTabMount'), '${eventId}')">
                <span class="material-symbols-outlined text-xs">refresh</span>
                <span>Refresh Live</span>
              </button>
              <button class="btn btn-outline btn-sm text-xs ${eventData.is_scoreboard_frozen ? 'text-status-success border-status-success' : 'text-status-warning border-status-warning'} flex items-center gap-1" onclick="AdminView.toggleEventScoreboardFreeze('${eventId}', ${!eventData.is_scoreboard_frozen})">
                <span class="material-symbols-outlined text-xs">ac_unit</span>
                <span>${eventData.is_scoreboard_frozen ? 'Unfreeze Scoreboard' : 'Freeze Scoreboard'}</span>
              </button>
              <button class="btn btn-primary btn-sm text-xs flex items-center gap-1.5 shadow-lg" onclick="AdminView.openCertificateModal('${eventId}')">
                <span class="material-symbols-outlined text-xs">workspace_premium</span>
                <span>Issue Certificates</span>
              </button>
            </div>

          </div>

          <!-- 2x2 Tactical Grid: 1. Live Leaderboard | 2. Live Cheating & Anti-Cheat Feed -->
          <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
            
            <!-- Panel 1: Live Leaderboard with Dynamic Ban / Disqualify Controls -->
            <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3 flex flex-col">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-base">military_tech</span>
                  <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">Live Arena Leaderboard</h3>
                </div>
                <span class="badge badge-medium text-xs font-mono">${leaderboardEntries.length} Ranked</span>
              </div>

              <div class="overflow-x-auto flex-1 max-h-96 overflow-y-auto">
                <table class="w-full text-left font-code-sm text-xs">
                  <thead>
                    <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                      <th class="p-2">Rank</th>
                      <th class="p-2">Operative / Squad</th>
                      <th class="p-2">College</th>
                      <th class="p-2">Score</th>
                      <th class="p-2">Solves</th>
                      <th class="p-2 text-right">Moderation Action</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle/30">
                    ${leaderboardEntries.length === 0 ? `
                      <tr>
                        <td colspan="6" class="p-8 text-center text-text-muted font-code-sm">
                          No flag solves logged yet for this event.
                        </td>
                      </tr>
                    ` : leaderboardEntries.map(entry => `
                      <tr class="hover:bg-surface-terminal/30 transition-colors">
                        <td class="p-2 font-bold ${entry.rank === 1 ? 'text-status-warning' : entry.rank === 2 ? 'text-text-secondary' : entry.rank === 3 ? 'text-tertiary' : 'text-text-muted'}">
                          #${entry.rank}
                        </td>
                        <td class="p-2 font-semibold text-text-primary">
                          <div class="flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-xs text-text-muted">${entry.participant_type === 'team' ? 'groups' : 'person'}</span>
                            <span>${escapeHtml(entry.participant_name)}</span>
                          </div>
                        </td>
                        <td class="p-2 text-text-muted truncate max-w-[120px]">
                          ${escapeHtml(entry.college || 'Collegiate')}
                        </td>
                        <td class="p-2 text-primary font-bold">
                          ${entry.total_points} PTS
                        </td>
                        <td class="p-2 text-on-surface font-mono">
                          ${entry.solved_count}
                        </td>
                        <td class="p-2 text-right">
                          <button
                            class="btn btn-outline btn-sm text-[11px] py-0.5 px-2 text-status-error hover:bg-status-error/20 flex items-center gap-0.5 inline-flex"
                            onclick="AdminView.liveOpsBanUser('${entry.participant_id}', '${escapeHtml(entry.participant_name).replace(/'/g, "\\'")}')"
                            title="Ban / Disqualify Operative from platform"
                          >
                            <span class="material-symbols-outlined text-[12px]">block</span>
                            <span>Ban</span>
                          </button>
                        </td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Panel 2: Live Cheating & Anti-Cheat Incidents -->
            <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3 flex flex-col">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-status-warning text-base">policy</span>
                  <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">Live Event Heuristic Incidents</h3>
                </div>
                <span class="badge badge-upcoming text-xs font-mono">${eventSecIncidents.length} Alerts</span>
              </div>

              <div class="space-y-2 flex-1 max-h-96 overflow-y-auto pr-1">
                ${eventSecIncidents.length === 0 ? `
                  <div class="p-8 text-center text-text-muted font-code-sm bg-surface-terminal/20 rounded-lg flex flex-col items-center justify-center gap-1.5">
                    <span class="material-symbols-outlined text-3xl text-status-success">verified_user</span>
                    <span class="text-xs font-bold text-text-primary">Zero Cheating Telemetry Detected</span>
                    <span class="text-[11px] text-text-muted">All solve patterns and IP signatures are within nominal parameters.</span>
                  </div>
                ` : eventSecIncidents.map(inc => `
                  <div class="p-3 rounded-lg bg-surface-terminal/40 border border-border-subtle space-y-1.5">
                    <div class="flex items-center justify-between gap-2">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-text-primary text-xs">@${escapeHtml(inc.username || 'operative')}</span>
                        <span class="badge ${inc.severity === 'critical' ? 'badge-hard' : inc.severity === 'high' ? 'badge-insane' : 'badge-medium'} text-[10px] uppercase font-mono">
                          ${escapeHtml(inc.severity || 'high')}
                        </span>
                      </div>
                      <span class="text-[11px] text-text-muted font-mono">${inc.status ? inc.status.toUpperCase() : 'OPEN'}</span>
                    </div>
                    <div class="text-xs text-text-secondary">
                      <strong>Type:</strong> <span class="text-status-warning font-mono">${escapeHtml(inc.event_type || 'Flag Sharing')}</span>
                    </div>
                    <p class="text-[11px] text-text-muted">${escapeHtml(inc.description || 'Heuristic anomaly detected in submission sequence.')}</p>
                    <div class="flex items-center justify-end gap-1.5 pt-1">
                      <button class="btn btn-outline btn-sm text-[11px] py-0.5 px-2 text-status-error hover:bg-status-error/20" onclick="AdminView.liveOpsBanUser('${inc.user_id}', '${escapeHtml(inc.username || 'user').replace(/'/g, "\\'")}')">
                        Confirm Ban
                      </button>
                      <button class="btn btn-outline btn-sm text-[11px] py-0.5 px-2 text-text-muted hover:text-text-primary" onclick="AdminView.reviewIncident('${inc.id}', 'dismissed')">
                        Dismiss
                      </button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

          </div>

          <!-- Bottom Grid: 3. Registered Operatives & Squads Roster | 4. Challenges Solves Matrix -->
          <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
            
            <!-- Panel 3: Registered Participants Roster with Dynamic Moderation -->
            <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-secondary text-base">manage_accounts</span>
                  <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">Registered Participants &amp; Squads</h3>
                </div>
                <span class="badge badge-medium text-xs font-mono">${participantsList.length} Total</span>
              </div>

              <div class="overflow-x-auto max-h-72 overflow-y-auto">
                <table class="w-full text-left font-code-sm text-xs">
                  <thead>
                    <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                      <th class="p-2">Participant</th>
                      <th class="p-2">Type</th>
                      <th class="p-2">College</th>
                      <th class="p-2">Registered At</th>
                      <th class="p-2 text-right">Moderation</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle/30">
                    ${participantsList.length === 0 ? `
                      <tr>
                        <td colspan="5" class="p-6 text-center text-text-muted font-code-sm">
                          No participants registered for this event yet.
                        </td>
                      </tr>
                    ` : participantsList.map(p => `
                      <tr class="hover:bg-surface-terminal/30 transition-colors">
                        <td class="p-2 font-semibold text-text-primary">
                          ${escapeHtml(p.participant_name || 'Operative')}
                        </td>
                        <td class="p-2 text-text-muted uppercase">
                          ${escapeHtml(p.registration_type || 'individual')}
                        </td>
                        <td class="p-2 text-text-muted truncate max-w-[120px]">
                          ${escapeHtml(p.college || 'Collegiate')}
                        </td>
                        <td class="p-2 text-text-muted font-mono text-[11px]">
                          ${p.registered_at ? new Date(p.registered_at).toLocaleDateString() : '—'}
                        </td>
                        <td class="p-2 text-right">
                          <button
                            class="btn btn-outline btn-sm text-[11px] py-0.5 px-2 text-status-error hover:bg-status-error/20"
                            onclick="AdminView.liveOpsBanUser('${p.participant_id}', '${escapeHtml(p.participant_name || 'user').replace(/'/g, "\\'")}')"
                          >
                            Ban User
                          </button>
                        </td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Panel 4: Challenge Vectors Solves Performance -->
            <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-base">analytics</span>
                  <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">Assigned Vector Metrics</h3>
                </div>
                <span class="badge badge-medium text-xs font-mono">${challengesData.length} Challenges</span>
              </div>

              <div class="overflow-x-auto max-h-72 overflow-y-auto">
                <table class="w-full text-left font-code-sm text-xs">
                  <thead>
                    <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                      <th class="p-2">Challenge Title</th>
                      <th class="p-2">Category</th>
                      <th class="p-2">Difficulty</th>
                      <th class="p-2">Points</th>
                      <th class="p-2 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle/30">
                    ${challengesData.length === 0 ? `
                      <tr>
                        <td colspan="5" class="p-6 text-center text-text-muted font-code-sm">
                          No challenge vectors linked to this event.
                        </td>
                      </tr>
                    ` : challengesData.map(ch => `
                      <tr class="hover:bg-surface-terminal/30 transition-colors">
                        <td class="p-2 font-bold text-text-primary">
                          ${escapeHtml(ch.title)}
                        </td>
                        <td class="p-2 text-secondary uppercase">
                          ${escapeHtml(ch.category_name || 'Jeopardy')}
                        </td>
                        <td class="p-2">
                          ${getDifficultyBadge(ch.difficulty)}
                        </td>
                        <td class="p-2 text-primary font-bold">
                          ${ch.points} PTS
                        </td>
                        <td class="p-2 text-right">
                          <span class="text-status-success font-semibold text-xs">Active</span>
                        </td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

        </div>
      `;
    } catch (err) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error loading Live Ops: ${escapeHtml(err.message)}</div>`;
    }
  },

  /* ==========================================
     5B. CONCLUDED EVENT REPORT & POST-MORTEM AUDIT
     ========================================== */
  endedReportParticipantTab: 'individuals',
  endedAuditData: null,

  async renderEndedEventReport(mount, eventId, eventMeta) {
    try {
      mount.innerHTML = '<div class="text-text-muted font-code-sm text-center py-16">Generating Concluded Tournament Audit &amp; Question Breakdown...</div>';

      const auditData = await window.api.adminGetEventAuditBreakdown(eventId);
      this.endedAuditData = auditData;
      const ev = auditData.event || eventMeta || {};
      const leaderboard = auditData.leaderboard || [];
      const participants = auditData.participants || [];
      const teams = auditData.teams || [];
      const cheatingLogs = auditData.cheating_audit || [];
      const challenges = auditData.challenges_summary || [];

      // Check if certificates have been sent
      const anyCertSent = participants.some(p => p.certificate_status === 'sent') || teams.some(t => t.certificate_status === 'sent');

      const startDate = ev.start_at ? new Date(ev.start_at) : null;
      const endDate = ev.end_at ? new Date(ev.end_at) : null;
      const timeStr = (startDate && endDate)
        ? `${startDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })} &mdash; ${endDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`
        : 'Concluded';

      mount.innerHTML = `
        <div class="space-y-4">
          
          <!-- Concluded Tournament Tactical Header -->
          <div class="p-4 rounded-xl bg-surface-card border border-border-grid shadow-xl space-y-3">
            
            <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div class="flex items-start gap-3">
                <button class="btn btn-outline btn-sm text-xs p-2 shrink-0" onclick="AdminView.switchTab('events')" title="Back to Event Matrix">
                  <span class="material-symbols-outlined text-sm">arrow_back</span>
                </button>
                <div>
                  <div class="flex items-center gap-2 flex-wrap">
                    <h2 class="font-headline-sm text-headline-sm text-text-primary font-black">${escapeHtml(ev.name || 'CTF Event')}</h2>
                    <span class="px-2.5 py-0.5 rounded-full bg-surface-terminal text-text-muted border border-border-subtle text-xs font-bold uppercase tracking-wider">
                      CONCLUDED / ARCHIVED
                    </span>
                    <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 font-bold">
                      ${auditData.total_participants || participants.length} Operatives
                    </span>
                    <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-secondary/10 text-secondary border border-secondary/30 font-bold">
                      ${auditData.total_teams || teams.length} Squads
                    </span>
                    <span class="font-code-sm text-xs px-2 py-0.5 rounded bg-surface-terminal text-on-surface border border-border-subtle font-mono">
                      ${auditData.total_solves || 0} Total Solves
                    </span>
                  </div>
                  <p class="font-body-sm text-xs text-text-muted mt-1">
                    Concluded Tournament Post-Mortem &amp; Audit Report &bull; ${timeStr} &bull; Complete question breakdown, cheating detections, and certificate status.
                  </p>
                </div>
              </div>

              <!-- Header Operations Toolbar -->
              <div class="flex items-center gap-2 flex-wrap">
                <button class="btn btn-outline btn-sm text-xs flex items-center gap-1" onclick="AdminView.renderEndedEventReport(document.getElementById('adminTabMount'), '${eventId}')">
                  <span class="material-symbols-outlined text-xs">refresh</span>
                  <span>Refresh Audit</span>
                </button>
                <button class="btn btn-outline btn-sm text-xs flex items-center gap-1" onclick="AdminView.exportEndedEvent('${eventId}', 'csv')">
                  <span class="material-symbols-outlined text-xs">download</span>
                  <span>Export CSV</span>
                </button>
                <button class="btn btn-primary btn-sm text-xs flex items-center gap-1.5 shadow-lg" onclick="AdminView.openCertificateModal('${eventId}')">
                  <span class="material-symbols-outlined text-xs">workspace_premium</span>
                  <span>${anyCertSent ? 'Manage / Re-issue Certificates' : 'Issue Certificates to Gmails'}</span>
                </button>
              </div>
            </div>

            <!-- Certificate Distribution Status Banner -->
            <div class="p-3 rounded-lg border ${anyCertSent ? 'bg-status-success/10 border-status-success/40' : 'bg-status-warning/10 border-status-warning/40'} flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-code-sm text-xs">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined ${anyCertSent ? 'text-status-success' : 'text-status-warning'} text-lg">
                  ${anyCertSent ? 'mark_email_read' : 'pending_actions'}
                </span>
                <div>
                  <strong class="${anyCertSent ? 'text-status-success' : 'text-status-warning'} uppercase tracking-wide">
                    ${anyCertSent ? 'Digital Certificates Distributed' : 'Certificates Pending Distribution'}
                  </strong>
                  <p class="text-text-muted text-[11px] mt-0.5">
                    ${anyCertSent
                      ? 'Official cryptographically signed PCCOE participation & winner certificates were dispatched to registered participant Gmails.'
                      : 'Tournament has concluded. You can generate and distribute verified certificates to all participant Gmail addresses now.'}
                  </p>
                </div>
              </div>
              <button class="btn btn-sm ${anyCertSent ? 'btn-outline text-status-success' : 'btn-primary'} text-xs shrink-0" onclick="AdminView.openCertificateModal('${eventId}')">
                ${anyCertSent ? 'View Certificate Registry' : 'Distribute Certificates Now'}
              </button>
            </div>

          </div>

          <!-- 1. FINAL OFFICIAL LEADERBOARD -->
          <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-status-warning text-base">emoji_events</span>
                <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">Final Official Tournament Leaderboard</h3>
              </div>
              <span class="badge badge-medium text-xs font-mono">${leaderboard.length} Finalists</span>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left font-code-sm text-xs">
                <thead>
                  <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                    <th class="p-2.5">Final Rank</th>
                    <th class="p-2.5">Operative / Squad</th>
                    <th class="p-2.5">College</th>
                    <th class="p-2.5">Final Score</th>
                    <th class="p-2.5">Solves</th>
                    <th class="p-2.5">Last Solve Timestamp</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/30">
                  ${leaderboard.length === 0 ? `
                    <tr>
                      <td colspan="6" class="p-8 text-center text-text-muted font-code-sm">
                        No final scores recorded for this tournament.
                      </td>
                    </tr>
                  ` : leaderboard.map(entry => {
                    let podiumClass = 'text-text-muted';
                    let medal = `#${entry.rank}`;
                    if (entry.rank === 1) {
                      podiumClass = 'text-status-warning font-bold';
                      medal = '🥇 1st Place Champion';
                    } else if (entry.rank === 2) {
                      podiumClass = 'text-text-secondary font-bold';
                      medal = '🥈 2nd Place Runner-Up';
                    } else if (entry.rank === 3) {
                      podiumClass = 'text-tertiary font-bold';
                      medal = '🥉 3rd Place Podium';
                    }

                    return `
                      <tr class="hover:bg-surface-terminal/30 transition-colors ${entry.rank <= 3 ? 'bg-status-warning/5' : ''}">
                        <td class="p-2.5 ${podiumClass}">
                          ${medal}
                        </td>
                        <td class="p-2.5 font-bold text-text-primary">
                          <div class="flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-xs text-text-muted">${entry.participant_type === 'team' ? 'groups' : 'person'}</span>
                            <span>${escapeHtml(entry.participant_name)}</span>
                          </div>
                        </td>
                        <td class="p-2.5 text-text-muted truncate max-w-[150px]">
                          ${escapeHtml(entry.college || 'Collegiate')}
                        </td>
                        <td class="p-2.5 text-primary font-black text-sm">
                          ${entry.total_points} PTS
                        </td>
                        <td class="p-2.5 text-on-surface font-mono font-semibold">
                          ${entry.solved_count} Solves
                        </td>
                        <td class="p-2.5 text-text-muted font-mono text-[11px]">
                          ${entry.last_solve_time ? new Date(entry.last_solve_time).toLocaleString() : '—'}
                        </td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- 2. TOTAL PARTICIPANTS & TEAMS SEGREGATED DETAILED SCORE & QUESTION BREAKDOWN -->
          <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-4">
            
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border-subtle">
              <div>
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-secondary text-base">fact_check</span>
                  <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">
                    Detailed Question Breakdown &amp; Submission Audit
                  </h3>
                </div>
                <p class="text-xs text-text-muted mt-0.5">
                  View scores, which categories and challenge questions were solved correctly, failed attempts, and certificate distribution.
                </p>
              </div>

              <!-- Segregated Tab Switcher: Individuals vs Squads -->
              <div class="flex items-center gap-1.5 p-1 rounded-lg bg-surface-terminal/60 border border-border-subtle">
                <button
                  type="button"
                  id="btnEndedTabIndividuals"
                  class="btn btn-sm ${this.endedReportParticipantTab === 'individuals' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3"
                  onclick="AdminView.switchEndedReportParticipantTab('individuals')"
                >
                  <span class="material-symbols-outlined text-xs">person</span>
                  <span>Individual Operatives (${participants.length})</span>
                </button>
                <button
                  type="button"
                  id="btnEndedTabTeams"
                  class="btn btn-sm ${this.endedReportParticipantTab === 'teams' ? 'btn-primary' : 'btn-outline'} text-xs py-1 px-3"
                  onclick="AdminView.switchEndedReportParticipantTab('teams')"
                >
                  <span class="material-symbols-outlined text-xs">groups</span>
                  <span>Squads / Teams (${teams.length})</span>
                </button>
              </div>
            </div>

            <!-- Section 2A: Individual Operatives Question Breakdown -->
            <div id="endedReportIndividualsMount" style="display: ${this.endedReportParticipantTab === 'individuals' ? 'block' : 'none'};">
              <div class="overflow-x-auto">
                <table class="w-full text-left font-code-sm text-xs">
                  <thead>
                    <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase tracking-wider">
                      <th class="p-2.5">Rank &amp; Operative</th>
                      <th class="p-2.5">College</th>
                      <th class="p-2.5">Score &amp; Stats</th>
                      <th class="p-2.5">Questions Solved (Correct)</th>
                      <th class="p-2.5">Questions Attempted (Wrong)</th>
                      <th class="p-2.5">Certificate Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle/30">
                    ${participants.length === 0 ? `
                      <tr>
                        <td colspan="6" class="p-8 text-center text-text-muted font-code-sm">
                          No individual participants registered in this event.
                        </td>
                      </tr>
                    ` : participants.map(p => `
                      <tr class="hover:bg-surface-terminal/30 transition-colors ${p.is_banned ? 'bg-status-error/5 opacity-75' : ''}">
                        
                        <!-- Name & Rank -->
                        <td class="p-2.5 font-bold text-text-primary">
                          <div class="flex flex-col">
                            <div class="flex items-center gap-1.5">
                              <span class="font-mono ${p.rank <= 3 ? 'text-status-warning font-black' : 'text-text-muted'}">#${p.rank}</span>
                              <span>${escapeHtml(p.name)}</span>
                              ${p.is_banned ? '<span class="badge badge-hard text-[9px] uppercase text-status-error">BANNED</span>' : ''}
                            </div>
                            <span class="text-[11px] text-text-muted font-mono font-normal">@${escapeHtml(p.username)} &bull; ${escapeHtml(p.email)}</span>
                          </div>
                        </td>

                        <!-- College -->
                        <td class="p-2.5 text-text-muted truncate max-w-[130px]">
                          ${escapeHtml(p.college || 'OWASP Club')}
                        </td>

                        <!-- Score & Stats -->
                        <td class="p-2.5">
                          <div class="flex flex-col">
                            <span class="text-primary font-bold text-sm">${p.total_points} PTS</span>
                            <span class="text-[11px] text-text-muted">${p.solved_count} Solved &bull; ${p.failed_attempts_count} Failed</span>
                          </div>
                        </td>

                        <!-- Correct Questions Solved -->
                        <td class="p-2.5 max-w-xs">
                          ${p.solved_challenges && p.solved_challenges.length > 0 ? `
                            <div class="flex flex-wrap gap-1">
                              ${p.solved_challenges.map(sc => `
                                <span class="px-2 py-0.5 rounded bg-primary/10 border border-primary/30 text-text-primary text-[10px] font-mono inline-flex items-center gap-1">
                                  <span class="text-secondary font-bold uppercase text-[9px]">${escapeHtml(sc.category || 'CTF')}</span>
                                  <span class="font-semibold">${escapeHtml(sc.title)}</span>
                                  <span class="text-primary font-bold">(+${sc.points_awarded || sc.points}p)</span>
                                </span>
                              `).join('')}
                            </div>
                          ` : `
                            <span class="text-text-muted text-[11px] italic">No verified solves</span>
                          `}
                        </td>

                        <!-- Wrong Questions Attempted -->
                        <td class="p-2.5 max-w-xs">
                          ${p.failed_challenges && p.failed_challenges.length > 0 ? `
                            <div class="flex flex-wrap gap-1">
                              ${p.failed_challenges.map(fc => `
                                <span class="px-2 py-0.5 rounded bg-status-error/10 border border-status-error/30 text-text-primary text-[10px] font-mono inline-flex items-center gap-1">
                                  <span class="text-status-error uppercase text-[9px] font-bold">${escapeHtml(fc.category || 'FAIL')}</span>
                                  <span class="text-text-secondary">${escapeHtml(fc.title)}</span>
                                  <span class="text-status-error font-bold font-mono">(${fc.attempts_count} ${fc.attempts_count > 1 ? 'fails' : 'fail'})</span>
                                </span>
                              `).join('')}
                            </div>
                          ` : `
                            <span class="text-text-muted text-[11px] italic">0 failed attempts</span>
                          `}
                        </td>

                        <!-- Certificate Status -->
                        <td class="p-2.5 whitespace-nowrap">
                          ${p.certificate_status === 'sent' ? `
                            <span class="inline-flex items-center gap-1 text-status-success font-bold text-[11px] bg-status-success/15 border border-status-success/30 px-2 py-0.5 rounded font-mono">
                              <span class="material-symbols-outlined text-xs">mark_email_read</span>
                              <span>Sent to Gmail</span>
                            </span>
                          ` : `
                            <span class="inline-flex items-center gap-1 text-text-muted font-semibold text-[11px] bg-surface-terminal border border-border-subtle px-2 py-0.5 rounded font-mono">
                              <span class="material-symbols-outlined text-xs">hourglass_empty</span>
                              <span>Pending</span>
                            </span>
                          `}
                        </td>

                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Section 2B: Squads / Teams Question Breakdown -->
            <div id="endedReportTeamsMount" style="display: ${this.endedReportParticipantTab === 'teams' ? 'block' : 'none'};">
              <div class="overflow-x-auto">
                <table class="w-full text-left font-code-sm text-xs">
                  <thead>
                    <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase tracking-wider">
                      <th class="p-2.5">Rank &amp; Squad Name</th>
                      <th class="p-2.5">Squad Operatives</th>
                      <th class="p-2.5">Score &amp; Solves</th>
                      <th class="p-2.5">Questions Solved (Correct)</th>
                      <th class="p-2.5">Questions Attempted (Wrong)</th>
                      <th class="p-2.5">Certificate Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle/30">
                    ${teams.length === 0 ? `
                      <tr>
                        <td colspan="6" class="p-8 text-center text-text-muted font-code-sm">
                          No squads or teams registered in this event.
                        </td>
                      </tr>
                    ` : teams.map(t => `
                      <tr class="hover:bg-surface-terminal/30 transition-colors">
                        
                        <!-- Squad Info -->
                        <td class="p-2.5 font-bold text-text-primary">
                          <div class="flex flex-col">
                            <div class="flex items-center gap-1.5">
                              <span class="font-mono ${t.rank <= 3 ? 'text-status-warning font-black' : 'text-text-muted'}">#${t.rank}</span>
                              <span class="text-sm">${escapeHtml(t.name)}</span>
                            </div>
                            <span class="text-[11px] text-text-muted font-normal">${escapeHtml(t.college || 'Collegiate Squad')}</span>
                          </div>
                        </td>

                        <!-- Members -->
                        <td class="p-2.5 max-w-xs">
                          <div class="flex flex-wrap gap-1">
                            ${t.members && t.members.length > 0 ? t.members.map(m => `
                              <span class="px-1.5 py-0.5 rounded bg-surface-terminal text-text-secondary border border-border-subtle text-[10px] font-mono">
                                @${escapeHtml(m.username)}
                              </span>
                            `).join('') : '<span class="text-text-muted italic text-[11px]">No members</span>'}
                          </div>
                        </td>

                        <!-- Score & Stats -->
                        <td class="p-2.5">
                          <div class="flex flex-col">
                            <span class="text-primary font-bold text-sm">${t.total_points} PTS</span>
                            <span class="text-[11px] text-text-muted">${t.solved_count} Solved &bull; ${t.failed_attempts_count} Failed</span>
                          </div>
                        </td>

                        <!-- Correct Questions Solved -->
                        <td class="p-2.5 max-w-xs">
                          ${t.solved_challenges && t.solved_challenges.length > 0 ? `
                            <div class="flex flex-wrap gap-1">
                              ${t.solved_challenges.map(sc => `
                                <span class="px-2 py-0.5 rounded bg-primary/10 border border-primary/30 text-text-primary text-[10px] font-mono inline-flex items-center gap-1">
                                  <span class="text-secondary font-bold uppercase text-[9px]">${escapeHtml(sc.category || 'CTF')}</span>
                                  <span class="font-semibold">${escapeHtml(sc.title)}</span>
                                  <span class="text-primary font-bold">(+${sc.points_awarded || sc.points}p)</span>
                                </span>
                              `).join('')}
                            </div>
                          ` : `
                            <span class="text-text-muted text-[11px] italic">No verified solves</span>
                          `}
                        </td>

                        <!-- Wrong Questions Attempted -->
                        <td class="p-2.5 max-w-xs">
                          ${t.failed_challenges && t.failed_challenges.length > 0 ? `
                            <div class="flex flex-wrap gap-1">
                              ${t.failed_challenges.map(fc => `
                                <span class="px-2 py-0.5 rounded bg-status-error/10 border border-status-error/30 text-text-primary text-[10px] font-mono inline-flex items-center gap-1">
                                  <span class="text-status-error uppercase text-[9px] font-bold">${escapeHtml(fc.category || 'FAIL')}</span>
                                  <span class="text-text-secondary">${escapeHtml(fc.title)}</span>
                                  <span class="text-status-error font-bold font-mono">(${fc.attempts_count} fails)</span>
                                </span>
                              `).join('')}
                            </div>
                          ` : `
                            <span class="text-text-muted text-[11px] italic">0 failed attempts</span>
                          `}
                        </td>

                        <!-- Certificate Status -->
                        <td class="p-2.5 whitespace-nowrap">
                          ${t.certificate_status === 'sent' ? `
                            <span class="inline-flex items-center gap-1 text-status-success font-bold text-[11px] bg-status-success/15 border border-status-success/30 px-2 py-0.5 rounded font-mono">
                              <span class="material-symbols-outlined text-xs">mark_email_read</span>
                              <span>Sent to Squad</span>
                            </span>
                          ` : `
                            <span class="inline-flex items-center gap-1 text-text-muted font-semibold text-[11px] bg-surface-terminal border border-border-subtle px-2 py-0.5 rounded font-mono">
                              <span class="material-symbols-outlined text-xs">hourglass_empty</span>
                              <span>Pending</span>
                            </span>
                          `}
                        </td>

                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          <!-- 3. CHEATING AUDIT & DISQUALIFIED / FLAGGED PARTICIPANTS & TEAMS -->
          <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-status-error text-base">gavel</span>
                <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">
                  Cheating Audit &amp; Flagged Incidents Log
                </h3>
              </div>
              <span class="badge ${cheatingLogs.length > 0 ? 'badge-hard text-status-error' : 'badge-medium'} text-xs font-mono">
                ${cheatingLogs.length} Detections Logged
              </span>
            </div>

            <div class="space-y-2">
              ${cheatingLogs.length === 0 ? `
                <div class="p-6 text-center text-text-muted font-code-sm bg-surface-terminal/20 rounded-lg flex flex-col items-center justify-center gap-1.5">
                  <span class="material-symbols-outlined text-3xl text-status-success">verified_user</span>
                  <span class="text-xs font-bold text-text-primary">Clean Tournament &mdash; Zero Cheating Anomalies</span>
                  <span class="text-[11px] text-text-muted">No flag sharing or automated multi-solve exploits were confirmed for this competition.</span>
                </div>
              ` : `
                <div class="overflow-x-auto">
                  <table class="w-full text-left font-code-sm text-xs">
                    <thead>
                      <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                        <th class="p-2.5">Operative / Squad</th>
                        <th class="p-2.5">Cheating Vector / Type</th>
                        <th class="p-2.5">Severity</th>
                        <th class="p-2.5">Moderation Status</th>
                        <th class="p-2.5">Observation Telemetry</th>
                        <th class="p-2.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-border-subtle/30">
                      ${cheatingLogs.map(log => `
                        <tr class="hover:bg-surface-terminal/30 transition-colors">
                          <td class="p-2.5 font-bold text-text-primary">
                            <span class="text-status-warning">@${escapeHtml(log.username || log.team_name || 'operative')}</span>
                          </td>
                          <td class="p-2.5 text-status-error font-mono font-bold">
                            ${escapeHtml(log.event_type || 'Flag Collision')}
                          </td>
                          <td class="p-2.5">
                            <span class="badge ${log.severity === 'critical' ? 'badge-hard text-status-error' : log.severity === 'high' ? 'badge-insane' : 'badge-medium'} text-[10px] uppercase font-mono">
                              ${escapeHtml(log.severity || 'high')}
                            </span>
                          </td>
                          <td class="p-2.5">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono ${log.status === 'actioned' ? 'bg-status-error/20 text-status-error border border-status-error/40' : 'bg-surface-terminal text-text-secondary border border-border-subtle'}">
                              ${(log.status || 'OPEN').toUpperCase()}
                            </span>
                          </td>
                          <td class="p-2.5 text-text-secondary text-[11px] max-w-sm">
                            ${escapeHtml(log.description || 'Heuristic telemetry violation.')}
                          </td>
                          <td class="p-2.5 text-text-muted font-mono text-[11px] whitespace-nowrap">
                            ${log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              `}
            </div>
          </div>

          <!-- 4. CHALLENGE VECTORS PERFORMANCE AUDIT -->
          <div class="bg-surface-card rounded-xl p-4 border border-border-grid shadow-lg space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-base">query_stats</span>
                <h3 class="font-headline-sm text-sm font-bold text-text-primary uppercase tracking-wider">
                  Vector Solve &amp; Failure Rates Post-Mortem
                </h3>
              </div>
              <span class="badge badge-medium text-xs font-mono">${challenges.length} Vectors</span>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left font-code-sm text-xs">
                <thead>
                  <tr class="bg-surface-terminal/60 text-text-muted font-label-sm uppercase">
                    <th class="p-2.5">Challenge Vector</th>
                    <th class="p-2.5">Category</th>
                    <th class="p-2.5">Difficulty</th>
                    <th class="p-2.5">Points</th>
                    <th class="p-2.5">Successful Solves</th>
                    <th class="p-2.5">Failed Attempts</th>
                    <th class="p-2.5">First Blood Operative</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/30">
                  ${challenges.length === 0 ? `
                    <tr>
                      <td colspan="7" class="p-6 text-center text-text-muted font-code-sm">
                        No challenge vectors recorded for this tournament.
                      </td>
                    </tr>
                  ` : challenges.map(ch => `
                    <tr class="hover:bg-surface-terminal/30 transition-colors">
                      <td class="p-2.5 font-bold text-text-primary">
                        ${escapeHtml(ch.title)}
                      </td>
                      <td class="p-2.5 text-secondary uppercase font-semibold">
                        ${escapeHtml(ch.category || 'Jeopardy')}
                      </td>
                      <td class="p-2.5">
                        ${getDifficultyBadge(ch.difficulty)}
                      </td>
                      <td class="p-2.5 text-primary font-bold">
                        ${ch.points} PTS
                      </td>
                      <td class="p-2.5 text-status-success font-bold font-mono">
                        ${ch.solve_count || 0} Solves
                      </td>
                      <td class="p-2.5 text-status-error font-mono">
                        ${ch.wrong_count || 0} Fails
                      </td>
                      <td class="p-2.5 text-status-warning font-mono font-semibold">
                        ${ch.first_blood ? `🩸 @${escapeHtml(ch.first_blood)}` : '—'}
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      `;
    } catch (err) {
      mount.innerHTML = `<div class="text-status-error font-code-sm p-6">Error loading Concluded Event Report: ${escapeHtml(err.message)}</div>`;
    }
  },

  switchEndedReportParticipantTab(tab) {
    this.endedReportParticipantTab = tab;
    const btnInd = document.getElementById('btnEndedTabIndividuals');
    const btnTeam = document.getElementById('btnEndedTabTeams');
    const mountInd = document.getElementById('endedReportIndividualsMount');
    const mountTeam = document.getElementById('endedReportTeamsMount');

    if (tab === 'individuals') {
      if (btnInd) btnInd.className = 'btn btn-sm btn-primary text-xs py-1 px-3';
      if (btnTeam) btnTeam.className = 'btn btn-sm btn-outline text-xs py-1 px-3';
      if (mountInd) mountInd.style.display = 'block';
      if (mountTeam) mountTeam.style.display = 'none';
    } else {
      if (btnInd) btnInd.className = 'btn btn-sm btn-outline text-xs py-1 px-3';
      if (btnTeam) btnTeam.className = 'btn btn-sm btn-primary text-xs py-1 px-3';
      if (mountInd) mountInd.style.display = 'none';
      if (mountTeam) mountTeam.style.display = 'block';
    }
  },

  async exportEndedEvent(eventId, format) {
    try {
      const res = await window.api.exportEventResults(eventId, format);
      if (format === 'csv') {
        const blob = res instanceof Blob ? res : new Blob([res], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ctf_event_results_${eventId}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        const jsonStr = JSON.stringify(res, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ctf_event_results_${eventId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
      showToast('Event results exported successfully!', 'success');
    } catch (err) {
      showToast('Export failed: ' + err.message, 'error');
    }
  },

  async liveOpsBanUser(userId, username) {
    if (!userId) return;
    const confirmed = window.confirm(
      `Are you sure you want to dynamically BAN operative "${username}" from the platform and invalidate their event session?`
    );
    if (!confirmed) return;

    try {
      await window.api.adminUpdateUser(userId, { is_banned: true });
      showToast(`Operative @${username} has been BANNED dynamically.`, 'success');
      if (this.currentTab === 'liveops') {
        this.renderLiveOpsTab(document.getElementById('adminTabMount'), this.activeLiveOpsEventId);
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async toggleEventScoreboardFreeze(eventId, newFreeze) {
    try {
      if (newFreeze) {
        await window.api.adminFreezeScoreboard(eventId);
        showToast('Event scoreboard frozen successfully.', 'warning');
      } else {
        await window.api.adminUnfreezeScoreboard(eventId);
        showToast('Event scoreboard unfrozen successfully.', 'success');
      }
      if (this.currentTab === 'liveops') {
        this.renderLiveOpsTab(document.getElementById('adminTabMount'), eventId);
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  /* ==========================================
     6. EDIT EVENT MODAL & WORKFLOW
     ========================================== */
  async openEditEventModal(eventId) {
    this.editingEventId = eventId;
    this.editingStagedChallenges = [];
    this.editingEventChallengeMode = 'new';

    try {
      const [eventData, challenges] = await Promise.all([
        window.api.getEvent(eventId),
        window.api.getEventChallenges(eventId).catch(() => [])
      ]);

      this.editingEventData = eventData;
      this.editingEventChallenges = Array.isArray(challenges) ? challenges : [];

      document.getElementById('editEventId').value = eventId;
      document.getElementById('editEventName').value = eventData.name || '';
      document.getElementById('editEventDesc').value = eventData.description || '';

      if (eventData.start_at) {
        const d = new Date(eventData.start_at);
        document.getElementById('editEventStart').value = d.toISOString().slice(0, 16);
      }
      if (eventData.end_at) {
        const d = new Date(eventData.end_at);
        document.getElementById('editEventEnd').value = d.toISOString().slice(0, 16);
      }

      const statusSelect = document.getElementById('editEventStatus');
      if (statusSelect) {
        statusSelect.value = eventData.computed_status || eventData.status || 'upcoming';
      }

      this.renderEditExistingChallengesList();
      this.renderEditStagedChallenges();
      this.switchEditEventChallengeMode('new');

      openModal('editEventModal');
    } catch (err) {
      showToast('Error opening event editor: ' + err.message, 'error');
    }
  },

  renderEditExistingChallengesList() {
    const container = document.getElementById('editEventExistingChallengesList');
    const badge = document.getElementById('editEventAssignedCountBadge');
    if (badge) badge.textContent = `${this.editingEventChallenges.length} Assigned`;
    if (!container) return;

    if (this.editingEventChallenges.length === 0) {
      container.innerHTML = `
        <div class="p-3 text-center text-text-muted font-code-sm text-xs rounded bg-surface-terminal/30 border border-border-subtle">
          No challenges currently assigned to this event.
        </div>
      `;
      return;
    }

    container.innerHTML = this.editingEventChallenges.map(ch => `
      <div class="p-2.5 rounded bg-surface-card border border-border-subtle flex items-center justify-between gap-2 font-code-sm text-xs">
        <div class="flex items-center gap-2 min-w-0">
          <span class="font-bold text-text-primary truncate">${escapeHtml(ch.title)}</span>
          <span class="badge badge-medium text-[10px] uppercase">${escapeHtml(ch.difficulty || 'medium')}</span>
          <span class="text-primary font-bold">${ch.points} PTS</span>
        </div>
        <button
          type="button"
          class="btn btn-outline btn-sm text-[11px] py-0.5 px-2 text-status-error hover:bg-status-error/20 flex items-center gap-0.5"
          onclick="AdminView.removeExistingEventChallenge('${ch.id}', '${escapeHtml(ch.title).replace(/'/g, "\\'")}')"
        >
          <span class="material-symbols-outlined text-xs">delete</span>
          <span>Remove</span>
        </button>
      </div>
    `).join('');
  },

  async removeExistingEventChallenge(challengeId, title) {
    if (!this.editingEventId || !challengeId) return;
    const confirmed = window.confirm(`Remove challenge "${title}" from this event?`);
    if (!confirmed) return;

    try {
      await window.api.adminRemoveChallengeFromEvent(this.editingEventId, challengeId);
      this.editingEventChallenges = this.editingEventChallenges.filter(c => c.id !== challengeId);
      this.renderEditExistingChallengesList();
      showToast(`Challenge "${title}" removed from event.`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  switchEditEventChallengeMode(mode) {
    this.editingEventChallengeMode = mode;
    const btnNew = document.getElementById('btnEditEventModeNew');
    const btnExist = document.getElementById('btnEditEventModeExisting');
    const panelNew = document.getElementById('editEventAuthorPanel');
    const panelExist = document.getElementById('editEventCatalogPanel');

    if (mode === 'new') {
      if (btnNew) btnNew.className = 'btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (btnExist) btnExist.className = 'btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (panelNew) panelNew.style.display = 'block';
      if (panelExist) panelExist.style.display = 'none';
    } else {
      if (btnNew) btnNew.className = 'btn btn-outline btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (btnExist) btnExist.className = 'btn btn-primary btn-sm flex-1 text-xs py-1.5 flex items-center justify-center gap-1';
      if (panelNew) panelNew.style.display = 'none';
      if (panelExist) panelExist.style.display = 'block';
      this.loadEditEventCatalog();
    }
  },

  async loadEditEventCatalog() {
    const listMount = document.getElementById('editEventCatalogPickerList');
    if (!listMount) return;
    try {
      const allChallenges = await window.api.getChallenges();
      this.editingEventCatalogList = Array.isArray(allChallenges) ? allChallenges : (allChallenges.items || []);
      this.filterEditEventCatalog('');
    } catch (e) {
      listMount.innerHTML = `<div class="text-status-error text-xs p-2">Error loading catalog: ${escapeHtml(e.message)}</div>`;
    }
  },

  filterEditEventCatalog(query) {
    const listMount = document.getElementById('editEventCatalogPickerList');
    if (!listMount) return;

    const q = (query || '').toLowerCase().trim();
    const existingIds = new Set([
      ...this.editingEventChallenges.map(c => c.id),
      ...this.editingStagedChallenges.filter(c => c.type === 'existing').map(c => c.id)
    ]);

    const filtered = (this.editingEventCatalogList || []).filter(c => {
      if (existingIds.has(c.id)) return false;
      if (!q) return true;
      const title = (c.title || '').toLowerCase();
      const cat = (c.category?.name || c.category_name || '').toLowerCase();
      return title.includes(q) || cat.includes(q);
    });

    if (filtered.length === 0) {
      listMount.innerHTML = '<div class="text-text-muted text-center py-4">No available challenges found.</div>';
      return;
    }

    listMount.innerHTML = filtered.map(c => `
      <label class="p-2 rounded bg-surface-card border border-border-subtle flex items-center justify-between gap-2 hover:bg-surface-terminal/50 cursor-pointer transition-colors">
        <div class="flex items-center gap-2 min-w-0">
          <input type="checkbox" name="editCatalogCheck" value="${c.id}" class="accent-primary rounded" />
          <span class="font-bold text-text-primary truncate">${escapeHtml(c.title)}</span>
          <span class="badge badge-medium text-[10px] uppercase">${escapeHtml(c.difficulty || 'medium')}</span>
        </div>
        <span class="text-primary font-bold shrink-0">${c.points} PTS</span>
      </label>
    `).join('');
  },

  stageEditEventChallenge() {
    const title = (document.getElementById('editNewChallTitle')?.value || '').trim();
    const category_id = document.getElementById('editNewChallCategory')?.value || '';
    const difficulty = document.getElementById('editNewChallDifficulty')?.value || 'medium';
    const points = parseInt(document.getElementById('editNewChallPoints')?.value || '350', 10);
    const author = (document.getElementById('editNewChallAuthor')?.value || '').trim();
    const flag = (document.getElementById('editNewChallFlag')?.value || '').trim();
    const is_dynamic_flag = Boolean(document.getElementById('editNewChallIsDynamicFlag')?.checked);
    const description = (document.getElementById('editNewChallDesc')?.value || '').trim();
    const external_url = (document.getElementById('editNewChallExternalUrl')?.value || '').trim();

    if (!title) {
      showToast('Challenge Title is required.', 'error');
      return;
    }
    if (!category_id) {
      showToast('Please select a Category.', 'error');
      return;
    }
    if (!flag) {
      showToast('Flag Solution is required.', 'error');
      return;
    }

    this.editingStagedChallenges.push({
      type: 'new',
      title,
      category_id,
      difficulty,
      points,
      author,
      flag,
      is_dynamic_flag,
      description,
      external_url
    });

    // Clear inputs
    document.getElementById('editNewChallTitle').value = '';
    document.getElementById('editNewChallFlag').value = '';
    document.getElementById('editNewChallDesc').value = '';
    document.getElementById('editNewChallExternalUrl').value = '';
    document.getElementById('editNewChallIsDynamicFlag').checked = false;

    showToast(`Vector "${title}" staged for event!`, 'success');
    this.renderEditStagedChallenges();
  },

  stageEditExistingChallenges() {
    const checked = document.querySelectorAll('input[name="editCatalogCheck"]:checked');
    if (checked.length === 0) {
      showToast('Select at least one challenge from the catalog.', 'warning');
      return;
    }

    let addedCount = 0;
    checked.forEach(cb => {
      const chall = (this.editingEventCatalogList || []).find(c => c.id === cb.value);
      if (chall) {
        this.editingStagedChallenges.push({
          type: 'existing',
          id: chall.id,
          title: chall.title,
          category_id: chall.category_id,
          category_name: chall.category?.name || chall.category_name || 'Jeopardy',
          difficulty: chall.difficulty,
          points: chall.points
        });
        addedCount++;
      }
    });

    showToast(`Attached ${addedCount} catalog vectors to staging!`, 'success');
    this.renderEditStagedChallenges();
    this.filterEditEventCatalog('');
  },

  removeEditStagedChallenge(index) {
    this.editingStagedChallenges.splice(index, 1);
    this.renderEditStagedChallenges();
  },

  renderEditStagedChallenges() {
    const container = document.getElementById('editEventStagedList');
    const badge = document.getElementById('editStagedCountBadge');
    if (badge) badge.textContent = `${this.editingStagedChallenges.length} New Staged`;
    if (!container) return;

    if (this.editingStagedChallenges.length === 0) {
      container.innerHTML = `
        <div class="p-2.5 text-center text-text-muted font-code-sm text-xs rounded bg-surface-terminal/30 border border-border-subtle">
          No new challenges staged.
        </div>
      `;
      return;
    }

    container.innerHTML = this.editingStagedChallenges.map((item, idx) => `
      <div class="p-2 rounded bg-surface-terminal/60 border border-border-subtle flex items-center justify-between gap-2 font-code-sm text-xs">
        <div class="flex items-center gap-2 min-w-0">
          <span class="badge ${item.type === 'new' ? 'badge-hard' : 'badge-upcoming'} text-[10px] uppercase font-mono">
            ${item.type === 'new' ? 'NEW' : 'CATALOG'}
          </span>
          <span class="font-bold text-text-primary truncate">${escapeHtml(item.title)}</span>
          <span class="text-primary font-bold">${item.points} PTS</span>
          ${item.is_dynamic_flag ? '<span class="text-[10px] text-secondary font-bold">[DYNAMIC]</span>' : ''}
        </div>
        <button
          type="button"
          class="text-status-error hover:text-white p-1"
          onclick="AdminView.removeEditStagedChallenge(${idx})"
          title="Remove from staging"
        >
          ✕
        </button>
      </div>
    `).join('');
  },

  async handleUpdateEvent(e) {
    e.preventDefault();
    const eventId = document.getElementById('editEventId').value;
    const name = document.getElementById('editEventName').value.trim();
    const description = document.getElementById('editEventDesc').value.trim();
    const start_at = document.getElementById('editEventStart').value;
    const end_at = document.getElementById('editEventEnd').value;
    const status = document.getElementById('editEventStatus').value;

    const btn = document.getElementById('btnSubmitEditEvent');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> Updating Event &amp; Vectors...';

    try {
      // 1. Update core event
      await window.api.adminUpdateEvent(eventId, {
        name,
        description,
        start_at: new Date(start_at).toISOString(),
        end_at: new Date(end_at).toISOString(),
        status
      });

      // 2. Attach newly staged challenges
      let attachedCount = 0;
      for (let i = 0; i < this.editingStagedChallenges.length; i++) {
        const item = this.editingStagedChallenges[i];
        let challengeId = null;

        if (item.type === 'new') {
          const newChallPayload = {
            title: item.title,
            category_id: item.category_id,
            difficulty: item.difficulty,
            points: item.points,
            flag: item.flag,
            description: item.description,
            is_dynamic_flag: item.is_dynamic_flag
          };
          if (item.external_url) newChallPayload.external_url = item.external_url;

          const createdChall = await window.api.request('/api/challenges', {
            method: 'POST',
            body: JSON.stringify(newChallPayload)
          });
          challengeId = createdChall.id;
        } else {
          challengeId = item.id;
        }

        if (challengeId && eventId) {
          await window.api.adminAddChallengeToEvent(eventId, challengeId, item.points, this.editingEventChallenges.length + i + 1).catch(err => {
            console.warn('Error attaching challenge to event:', err);
          });
          attachedCount++;
        }
      }

      showToast(`Event "${name}" updated successfully! (${attachedCount} new vectors attached)`, 'success');
      closeModal('editEventModal');
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-base">save</span> Save Event Changes';
      this.renderEventsTab(document.getElementById('adminTabMount'));
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-base">save</span> Save Event Changes';
      showToast(err.message, 'error');
    }
  },

  async confirmDeleteEvent(eventId, eventName) {
    if (!eventId) return;
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete CTF event "${eventName || 'this event'}"?\n\nThis will remove the event, its leaderboard history, and participant enrollments.`
    );
    if (!confirmed) return;

    try {
      await window.api.adminDeleteEvent(eventId);
      showToast(`Event "${eventName || eventId}" deleted successfully.`, 'success');
      this.renderEventsTab(document.getElementById('adminTabMount'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  /* ==========================================
     7. DIGITAL CERTIFICATES COMMAND & PCCOE OWASP CERTIFICATE UI
     ========================================== */
  async openCertificateModal(eventId) {
    this.certificateEventId = eventId;
    this.selectedCertificateIndex = 0;

    try {
      const [eventData, leaderboardData, participantsData] = await Promise.all([
        window.api.getEvent(eventId),
        window.api.getEventLeaderboard(eventId).catch(() => ({ entries: [] })),
        window.api.getEventParticipants(eventId).catch(() => [])
      ]);

      this.certificateEventData = eventData;
      const titleMount = document.getElementById('certModalEventTitle');
      if (titleMount) {
        titleMount.textContent = `Certificates: ${eventData.name}`;
      }

      const leaderboardEntries = leaderboardData.entries || leaderboardData.items || [];
      const rankMap = {};
      leaderboardEntries.forEach(entry => {
        rankMap[entry.participant_id] = entry;
      });

      const participantsList = Array.isArray(participantsData) ? participantsData : [];
      
      // Build unified recipient list
      this.certificateRecipients = participantsList.map((p, idx) => {
        const rankInfo = rankMap[p.participant_id] || { rank: leaderboardEntries.length + idx + 1, total_points: 0 };
        const rank = rankInfo.rank || (idx + 1);
        let awardTitle = 'Certificate of Participation';
        if (rankInfo.total_points > 0) {
          if (rank === 1) awardTitle = '1st Place Champion';
          else if (rank === 2) awardTitle = '2nd Place Runner-Up';
          else if (rank === 3) awardTitle = '3rd Place Podium';
          else if (rank <= 10) awardTitle = 'Top 10 Finalist';
        }

        return {
          id: p.participant_id,
          name: p.participant_name || 'Operative',
          email: `${(p.participant_name || 'user').toLowerCase().replace(/[^a-z0-9]/g, '')}@pccoepune.org`,
          college: p.college || 'OWASP Student Chapter, PCCOE',
          rank: rank,
          points: rankInfo.total_points || 0,
          awardTitle: awardTitle,
          status: 'ready'
        };
      });

      // If no participants registered yet, provide default preview operative
      if (this.certificateRecipients.length === 0) {
        this.certificateRecipients = [{
          id: 'demo-operative',
          name: window.state.currentUser?.name || window.state.currentUser?.username || 'Name Here',
          email: window.state.currentUser?.email || 'operative@pccoepune.org',
          college: window.state.currentUser?.college || 'OWASP Student Chapter, PCCOE',
          rank: 1,
          points: 1250,
          awardTitle: 'Certificate of Participation',
          status: 'ready'
        }];
      }

      // Populate Select
      const select = document.getElementById('certRecipientSelect');
      if (select) {
        select.innerHTML = this.certificateRecipients.map((rec, i) => `
          <option value="${i}">#${rec.rank} - ${escapeHtml(rec.name)} (${escapeHtml(rec.awardTitle)})</option>
        `).join('');
      }

      const countBadge = document.getElementById('certRecipientCountBadge');
      if (countBadge) countBadge.textContent = `${this.certificateRecipients.length} Participants`;

      this.renderCertificateVisualCard(0);
      this.renderCertificateDeliveryRoster();

      openModal('certificateModal');
    } catch (err) {
      showToast('Error loading certificate data: ' + err.message, 'error');
    }
  },

  handleCertRecipientChange(indexStr) {
    const idx = parseInt(indexStr, 10) || 0;
    this.selectedCertificateIndex = idx;
    this.renderCertificateVisualCard(idx);
  },

  /* Renders the authentic PCCOE OWASP Digital Certificate matching image 2 */
  renderCertificateVisualCard(index) {
    const mount = document.getElementById('certificateVisualCardMount');
    if (!mount) return;

    const rec = this.certificateRecipients[index] || this.certificateRecipients[0];
    const eventName = this.certificateEventData?.name || 'CTF (Capture The Flag) Challenge';
    const eventDate = this.certificateEventData?.end_at
      ? new Date(this.certificateEventData.end_at).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
      : '19 / 09 / 2026';

    mount.innerHTML = `
      <div id="printableCertificate" class="relative mx-auto w-full max-w-[840px] aspect-[1.414/1] bg-[#040907] text-white p-6 sm:p-8 rounded-2xl border-2 border-[#00ff9d] shadow-[0_0_40px_rgba(0,255,157,0.25)] flex flex-col justify-between overflow-hidden font-sans select-none" style="box-sizing:border-box;">
        
        <!-- Cyber Sci-Fi Angled HUD Corner Accents -->
        <div class="absolute top-2 left-2 w-6 h-6 border-t-2 border-l-2 border-[#00ff9d]"></div>
        <div class="absolute top-2 right-2 w-6 h-6 border-t-2 border-r-2 border-[#00ff9d]"></div>
        <div class="absolute bottom-2 left-2 w-6 h-6 border-b-2 border-l-2 border-[#00ff9d]"></div>
        <div class="absolute bottom-2 right-2 w-6 h-6 border-b-2 border-r-2 border-[#00ff9d]"></div>

        <!-- Inner Circuit Border Overlay -->
        <div class="absolute inset-3 border border-[#00ff9d]/30 rounded-xl pointer-events-none"></div>

        <!-- 1. Header Strip: PCCOE Crest + ACM, ACM-W, OWASP, GDG, IIRIS, CESA Logos -->
        <div class="relative z-10 flex items-center justify-between border-b border-[#00ff9d]/30 pb-3">
          
          <!-- Left: PCCOE College Crest -->
          <div class="flex items-center gap-2.5">
            <div class="w-11 h-11 rounded-full bg-[#00ff9d]/10 border border-[#00ff9d]/50 flex items-center justify-center p-1">
              <span class="text-xl">🏛️</span>
            </div>
            <div class="flex flex-col">
              <span class="font-extrabold text-[12px] sm:text-[13px] tracking-wider text-white uppercase leading-tight font-mono">
                PIMPRI CHINCHWAD
              </span>
              <span class="font-bold text-[10px] sm:text-[11px] text-[#a7f3d0] tracking-wide uppercase leading-tight font-mono">
                COLLEGE OF ENGINEERING
              </span>
              <span class="text-[8px] sm:text-[9px] text-[#00ff9d]/80 uppercase tracking-widest mt-0.5">
                Department of Computer Engineering
              </span>
            </div>
          </div>

          <!-- Right: Tech Society Crests -->
          <div class="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
            <span class="px-2 py-0.5 rounded bg-blue-950/60 border border-blue-400/40 text-blue-300 font-mono text-[9px] font-bold">acm</span>
            <span class="px-2 py-0.5 rounded bg-blue-900/60 border border-blue-400/40 text-cyan-300 font-mono text-[9px] font-bold">acm-w</span>
            <span class="px-2 py-0.5 rounded bg-[#00ff9d]/10 border border-[#00ff9d]/40 text-[#00ff9d] font-mono text-[9px] font-bold">OWASP</span>
            <span class="px-2 py-0.5 rounded bg-red-950/60 border border-red-400/40 text-red-300 font-mono text-[9px] font-bold">GDG</span>
            <span class="px-2 py-0.5 rounded bg-purple-950/60 border border-purple-400/40 text-purple-300 font-mono text-[9px] font-bold">IIRIS</span>
            <div class="flex flex-col items-end border-l border-[#00ff9d]/30 pl-2">
              <span class="text-[12px] font-black text-white tracking-widest font-mono">CESA</span>
              <span class="text-[7px] text-text-muted uppercase">Student Assoc.</span>
            </div>
          </div>

        </div>

        <!-- 2. Certificate Main Titles -->
        <div class="relative z-10 text-center my-auto py-2">
          
          <div class="text-[11px] sm:text-xs font-mono font-bold uppercase tracking-[0.35em] text-[#a7f3d0]">
            CERTIFICATE OF
          </div>
          
          <div class="inline-block px-4 py-1 my-1 rounded-xl bg-gradient-to-r from-transparent via-[#00ff9d]/15 to-transparent">
            <h1 class="text-2xl sm:text-4xl font-['Orbitron',sans-serif] font-black text-[#00ff9d] tracking-[0.15em] uppercase" style="text-shadow: 0 0 20px rgba(0,255,157,0.6), 0 0 5px #00ff9d;">
              PARTICIPATION
            </h1>
          </div>

          <div class="text-[10px] sm:text-[11px] font-mono uppercase tracking-widest text-[#a7f3d0] mt-1 font-semibold">
            THIS CERTIFICATE IS PROUDLY PRESENTED TO
          </div>

          <!-- Recipient Name in Large Cursive Script Font -->
          <div class="font-['Dancing_Script',cursive] text-3xl sm:text-5xl text-[#ffffff] my-2 tracking-wide font-bold" style="text-shadow: 0 0 15px rgba(0, 255, 157, 0.7);">
            ${escapeHtml(rec.name)}
          </div>

          <!-- Glowing Center Divider -->
          <div class="flex items-center justify-center gap-2 max-w-sm mx-auto my-1.5 opacity-80">
            <div class="h-[1px] bg-gradient-to-r from-transparent to-[#00ff9d] flex-1"></div>
            <span class="text-xs text-[#00ff9d]">♦</span>
            <div class="h-[1px] bg-gradient-to-l from-transparent to-[#00ff9d] flex-1"></div>
          </div>

          <!-- Event Body Text -->
          <p class="text-[10px] sm:text-xs text-[#d1fae5] max-w-xl mx-auto leading-relaxed font-sans mt-2">
            for successfully participating in the <strong class="text-[#00ff9d] font-bold font-mono">CTF (Capture The Flag) Challenge</strong><br />
            organized by the <span class="text-white font-semibold">OWASP Student Chapter, PCCOE</span>.
          </p>

          <p class="text-[9px] sm:text-[11px] text-text-muted mt-1">
            Your curiosity, skills and determination made this event a success.
          </p>
          <div class="text-[11px] sm:text-xs font-bold text-[#00ff9d] tracking-wide mt-1.5 font-mono">
            Keep hacking, keep learning!
          </div>

        </div>

        <!-- 3. Left & Right Cyberpunk HUD Boxes -->
        <!-- Left HUD Box -->
        <div class="absolute left-6 top-1/2 -translate-y-1/2 hidden md:flex flex-col p-2 rounded-lg bg-[#00ff9d]/5 border border-[#00ff9d]/30 font-mono text-[9px] text-[#a7f3d0] w-24">
          <span class="text-[8px] text-[#00ff9d]">•••</span>
          <span class="text-[#00ff9d] mt-1">&gt; flag{</span>
          <span class="pl-2 text-white font-bold">success</span>
          <span class="text-[#00ff9d]">}</span>
          <span class="animate-pulse text-[#00ff9d] mt-0.5">_</span>
        </div>

        <!-- Right HUD Box -->
        <div class="absolute right-6 top-1/2 -translate-y-1/2 hidden md:flex flex-col items-center p-2 rounded-lg bg-[#00ff9d]/5 border border-[#00ff9d]/30 font-mono text-[8px] text-[#a7f3d0] text-center w-24">
          <span class="leading-tight text-white font-bold">THINK</span>
          <span class="leading-tight">ANALYZE</span>
          <span class="leading-tight">EXPLOIT</span>
          <span class="leading-tight text-[#00ff9d]">SOLVE</span>
          <span class="text-[#00ff9d] text-[10px] mt-1">&gt;_</span>
          <span class="text-lg mt-1 text-[#00ff9d]">🔒</span>
        </div>

        <!-- 4. Footer Strip: Date + Faculty Coordinator Signature -->
        <div class="relative z-10 flex items-end justify-between border-t border-[#00ff9d]/30 pt-3">
          
          <!-- Date -->
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[#00ff9d] text-lg">calendar_month</span>
            <div class="flex flex-col font-mono text-[9px] sm:text-[10px]">
              <span class="text-text-muted uppercase font-bold">DATE</span>
              <span class="text-white font-bold">${eventDate}</span>
            </div>
          </div>

          <!-- Verification Badge -->
          <div class="hidden sm:flex flex-col items-center text-center font-mono text-[8px] text-[#a7f3d0]">
            <span class="text-[#00ff9d]">🔒 CRYPTO VERIFIED</span>
            <span class="text-text-muted">TOKEN: ${rec.id ? rec.id.slice(0, 12) : 'AUTH_SIG'}</span>
          </div>

          <!-- Faculty Coordinator Signature -->
          <div class="flex flex-col items-center text-center">
            <div class="font-['Dancing_Script',cursive] text-lg sm:text-2xl text-[#a7f3d0] font-bold -mb-1">
              Prof. Coordinator
            </div>
            <div class="h-[1px] w-32 bg-[#00ff9d]/50 my-0.5"></div>
            <span class="font-mono text-[9px] sm:text-[10px] text-white font-bold uppercase tracking-wider">
              FACULTY COORDINATOR
            </span>
            <span class="font-mono text-[8px] sm:text-[9px] text-[#00ff9d]">
              OWASP PCCOE
            </span>
          </div>

        </div>

      </div>
    `;
  },

  renderCertificateDeliveryRoster() {
    const mount = document.getElementById('certDeliveryRosterMount');
    if (!mount) return;

    mount.innerHTML = this.certificateRecipients.map((rec, i) => `
      <div class="p-2.5 rounded bg-surface-card border border-border-subtle flex items-center justify-between gap-3 font-code-sm text-xs">
        <div class="flex items-center gap-2 min-w-0">
          <span class="font-bold text-text-primary">#${rec.rank}</span>
          <span class="font-semibold text-text-primary truncate">${escapeHtml(rec.name)}</span>
          <span class="text-text-muted font-mono truncate">&lt;${escapeHtml(rec.email)}&gt;</span>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="badge ${rec.status === 'delivered' ? 'badge-hard text-status-success' : 'badge-upcoming'} text-[10px] uppercase font-mono">
            ${rec.status === 'delivered' ? '✓ Delivered to Gmail' : 'Pending Issuance'}
          </span>
          <button class="btn btn-outline btn-sm text-[11px] py-0.5 px-2" onclick="AdminView.handleCertRecipientChange('${i}')">
            Preview
          </button>
        </div>
      </div>
    `).join('');
  },

  async distributeCertificatesNow() {
    if (!this.certificateEventId) return;
    const btn = document.getElementById('btnDistributeCertificates');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-xs animate-spin">progress_activity</span> Distributing to Gmails...';
    }

    try {
      const res = await window.api.adminDistributeCertificates(this.certificateEventId);
      
      // Update statuses
      this.certificateRecipients.forEach(rec => {
        rec.status = 'delivered';
      });
      this.renderCertificateDeliveryRoster();

      showToast(res.message || `Successfully distributed certificates to ${this.certificateRecipients.length} registered participant Gmail addresses!`, 'success');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-xs">done_all</span><span>Certificates Dispatched</span>';
      }
    } catch (err) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-xs">outgoing_mail</span><span>Distribute to Registered Gmails</span>';
      }
      showToast(err.message, 'error');
    }
  },

  printCertificate() {
    const certElement = document.getElementById('printableCertificate');
    if (!certElement) {
      window.print();
      return;
    }

    const printWin = window.open('', '_blank', 'width=900,height=650');
    if (!printWin) {
      window.print();
      return;
    }

    printWin.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>OWASP CTF Certificate - Print</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet" />
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          @page { size: landscape; margin: 0; }
          body { margin: 0; padding: 20px; background: #000; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        </style>
      </head>
      <body>
        ${certElement.outerHTML}
        <script>
          window.onload = function() {
            setTimeout(function() { window.print(); window.close(); }, 600);
          };
        </script>
      </body>
      </html>
    `);
    printWin.document.close();
  }
};

window.AdminView = AdminView;


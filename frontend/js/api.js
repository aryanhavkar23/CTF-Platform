/**
 * OWASP CTF Platform — Centralized API Client
 * Authoritative integration with FastAPI backend endpoints.
 */

const API_BASE = (() => {
  if (window.API_BASE) return window.API_BASE;
  const stored = localStorage.getItem('owasp_api_base');
  if (stored) return stored;
  // If directly served on port 8000 or 8001
  if (window.location.port === '8000' || window.location.port === '8001') {
    return window.location.origin;
  }
  // If accessed from file:// or local development static server (Live Server 5500, Vite 5173, etc.)
  if (
    window.location.protocol === 'file:' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  ) {
    const host = window.location.hostname === '127.0.0.1' ? '127.0.0.1' : 'localhost';
    return `http://${host}:8001`;
  }
  return window.location.origin;
})();

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('owasp_jwt') || '';
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('owasp_jwt', token);
    } else {
      localStorage.removeItem('owasp_jwt');
    }
  }

  getToken() {
    return this.token || localStorage.getItem('owasp_jwt') || '';
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = options.headers || {};

    const currentToken = this.getToken();
    if (currentToken && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.body) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(url, config);

      // Handle 401 Unauthorized (expired or revoked session)
      if (response.status === 401 && !endpoint.includes('/api/auth/login')) {
        this.setToken('');
        window.dispatchEvent(new CustomEvent('session-expired'));
      }

      // Check if binary download or blob is expected
      if (options.responseType === 'blob') {
        if (!response.ok) {
          const errJson = await response.json().catch(() => ({ detail: 'Request failed' }));
          throw new Error(errJson.detail || `HTTP ${response.status}`);
        }
        return await response.blob();
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        let errorMsg = data?.detail;
        if (Array.isArray(errorMsg)) {
          // FastAPI 422 Pydantic Validation error array
          errorMsg = errorMsg
            .map(e => {
              const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
              const prefix = field && field !== 'body' ? `[${field}] ` : '';
              return `${prefix}${e.msg || e.message || 'Validation error'}`;
            })
            .join(' | ');
        } else if (typeof errorMsg === 'object' && errorMsg !== null) {
          errorMsg = errorMsg.msg || errorMsg.message || JSON.stringify(errorMsg);
        }

        if (!errorMsg) {
          errorMsg = `Request failed with status ${response.status}`;
        }

        const err = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        err.status = response.status;
        err.data = data;
        throw err;
      }

      return data;
    } catch (err) {
      console.warn(`[API Error] ${config.method || 'GET'} ${endpoint}:`, err.message);
      if (err.name === 'TypeError' && (err.message === 'Failed to fetch' || err.message.includes('fetch'))) {
        const networkErr = new Error('Unable to connect to server. Please ensure the backend is running.');
        networkErr.status = 0;
        throw networkErr;
      }
      throw err;
    }
  }

  /* ==========================================
     Health Probes
     ========================================== */
  async checkHealth() {
    return this.request('/health');
  }

  async checkReadiness() {
    return this.request('/health/ready');
  }

  /* ==========================================
     Authentication
     ========================================== */
  async register(username, email, password, college = '', name = '', github_profile_url = '') {
    const payload = { username, email, password, college, name };
    if (github_profile_url) {
      payload.github_profile_url = github_profile_url;
    }
    return this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async login(email, password) {
    const res = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    if (res && res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  async getMe() {
    return this.request('/api/auth/me');
  }

  async getMyScore() {
    return this.request('/api/auth/me/score');
  }

  async changePassword(currentPassword, newPassword) {
    return this.request('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
  }

  async forgotPassword(email) {
    return this.request('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  async resetPassword(resetToken, newPassword) {
    return this.request('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ reset_token: resetToken, new_password: newPassword })
    });
  }

  async getGoogleAuthUrl() {
    return this.request('/api/auth/oauth/google/url');
  }

  async googleOAuthCallback(payload = {}) {
    const res = await this.request('/api/auth/oauth/google/callback', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    if (res && res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  logout() {
    this.setToken('');
    window.dispatchEvent(new CustomEvent('auth-changed', { detail: null }));
  }

  /* ==========================================
     Challenges & Submissions
     ========================================== */
  async getCategories() {
    return this.request('/api/categories');
  }

  async getChallenges(categoryId = '', difficulty = '') {
    const params = new URLSearchParams();
    if (categoryId) params.append('category_id', categoryId);
    if (difficulty) params.append('difficulty', difficulty);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/challenges${qs}`);
  }

  async getChallenge(challengeId) {
    return this.request(`/api/challenges/${challengeId}`);
  }

  async submitFlag(challengeId, flag) {
    return this.request(`/api/challenges/${challengeId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ flag })
    });
  }

  async unlockHint(challengeId, hintId) {
    return this.request(`/api/challenges/${challengeId}/hints/${hintId}/use`, {
      method: 'POST'
    });
  }

  async surrenderChallenge(challengeId) {
    return this.request(`/api/challenges/${challengeId}/surrender`, {
      method: 'POST'
    });
  }

  async getWriteup(challengeId) {
    return this.request(`/api/challenges/${challengeId}/writeup`);
  }

  async downloadChallengeFile(challengeId) {
    return this.request(`/api/challenges/${challengeId}/download`, {
      responseType: 'blob'
    });
  }


  /* ==========================================
     Leaderboards
     ========================================== */
  async getGlobalLeaderboard(limit = 100, offset = 0) {
    return this.request(`/api/leaderboard/global?page=1&page_size=${limit}`);
  }

  async getCollegeLeaderboard(college = '', limit = 100, offset = 0) {
    const q = college ? `?college=${encodeURIComponent(college)}&page_size=${limit}` : `?page_size=${limit}`;
    return this.request(`/api/leaderboard/college${q}`);
  }

  /* ==========================================
     Events & Certificates
     ========================================== */
  async getEvents() {
    return this.request('/api/events');
  }

  async getEvent(eventId) {
    return this.request(`/api/events/${eventId}`);
  }

  async registerEvent(eventId, registrationType = 'individual', teamId = null) {
    const body = { registration_type: registrationType };
    if (teamId) body.team_id = teamId;
    return this.request(`/api/events/${eventId}/register`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  async unregisterEvent(eventId) {
    return this.request(`/api/events/${eventId}/unregister`, {
      method: 'POST'
    });
  }

  async getEventRegistration(eventId) {
    return this.request(`/api/events/${eventId}/registration`);
  }

  async getEventParticipants(eventId) {
    return this.request(`/api/events/${eventId}/participants`);
  }

  async getEventChallenges(eventId) {
    return this.request(`/api/events/${eventId}/challenges`);
  }

  async getEventLeaderboard(eventId) {
    return this.request(`/api/events/${eventId}/leaderboard`);
  }

  async submitEventFlag(eventId, challengeId, flag) {
    return this.request(`/api/events/${eventId}/challenges/${challengeId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ flag })
    });
  }

  async exportEventResults(eventId, format = 'json') {
    if (format === 'csv') {
      return this.request(`/api/events/${eventId}/export?format=csv`, {
        responseType: 'blob'
      });
    }
    return this.request(`/api/events/${eventId}/export?format=json`);
  }

  async claimEventCertificate(eventId) {
    return this.request(`/api/events/${eventId}/certificate`);
  }

  async verifyCertificate(token) {
    return this.request(`/api/events/certificates/verify/${token}`);
  }

  /* ==========================================
     Teams
     ========================================== */
  async getTeams() {
    return this.request('/api/teams');
  }

  async getTeam(teamId) {
    return this.request(`/api/teams/${teamId}`);
  }

  async getMyTeam() {
    return this.request('/api/teams/me');
  }

  async getMyTeams() {
    return this.request('/api/teams/my-teams');
  }

  async getTeamHistory(teamId) {
    return this.request(`/api/teams/${teamId}/history`);
  }

  async searchOperatives(query = '', college = '') {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (college) params.append('college', college);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/teams/operatives/search${qs}`);
  }

  async createTeam(name, description = '', college = '') {
    return this.request('/api/teams', {
      method: 'POST',
      body: JSON.stringify({ name, description, college })
    });
  }

  async getMyTeamInvitations() {
    return this.request('/api/teams/me/invitations');
  }

  async addTeamMember(teamId, userIdentifier, role = 'requested') {
    let body;
    if (typeof userIdentifier === 'string') {
      body = { username: userIdentifier, role: role };
    } else {
      body = { role: role, ...userIdentifier };
    }
    return this.request(`/api/teams/${teamId}/members`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  async removeTeamMember(teamId, userId) {
    return this.request(`/api/teams/${teamId}/members/${userId}`, {
      method: 'DELETE'
    });
  }

  async acceptTeamMember(teamId, userId) {
    return this.request(`/api/teams/${teamId}/members/${userId}/accept`, {
      method: 'POST'
    });
  }

  async acceptTeamRequest(teamId) {
    return this.request(`/api/teams/${teamId}/accept`, {
      method: 'POST'
    });
  }

  async declineTeamRequest(teamId) {
    return this.request(`/api/teams/${teamId}/decline`, {
      method: 'POST'
    });
  }

  async leaveTeam(teamId) {
    return this.request(`/api/teams/${teamId}/leave`, {
      method: 'DELETE'
    });
  }

  async deleteTeam(teamId) {
    return this.request(`/api/teams/${teamId}`, {
      method: 'DELETE'
    });
  }

  async transferTeamOwnership(teamId, newOwnerId) {
    return this.request(`/api/teams/${teamId}/transfer-owner`, {
      method: 'POST',
      body: JSON.stringify({ new_owner_id: newOwnerId })
    });
  }

  /* ==========================================
     Profiles, Activity & Badges
     ========================================== */
  async getUserProfile(username) {
    return this.request(`/api/users/${username}/profile`);
  }

  async updateMyProfile(data) {
    return this.request('/api/users/me/profile', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async getUserActivity(username) {
    return this.request(`/api/users/${username}/activity`);
  }

  async getBadgesCatalog() {
    return this.request('/api/badges');
  }

  async getMyBadges() {
    return this.request('/api/badges/me');
  }

  async getMyCategoryStats() {
    return this.request('/api/profile/me/category-stats');
  }

  async getMySolvedChallenges() {
    return this.request('/api/profile/me/solved');
  }

  async getMyActivityHeatmap(startDate = null, endDate = null) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/profile/me/activity/heatmap${qs}`);
  }

  async getMyStreak() {
    return this.request('/api/profile/me/streak');
  }

  /* ==========================================
     Badges & Tactical Commendations
     ========================================== */
  async getMyBadges() {
    return this.request('/api/profile/me/badges');
  }

  async getMyBadgeProgress() {
    return this.request('/api/profile/me/badge-progress');
  }

  async getBadgesCatalog() {
    return this.request('/api/badges');
  }

  async getUserBadges(userId) {
    return this.request(`/api/profile/${userId}/badges`);
  }

  /* ==========================================
     Discussions
     ========================================== */
  async getDiscussions(challengeId) {
    return this.request(`/api/challenges/${challengeId}/discussions`);
  }

  async createDiscussion(challengeId, title, content) {
    return this.request(`/api/challenges/${challengeId}/discussions`, {
      method: 'POST',
      body: JSON.stringify({ title, content })
    });
  }

  async getDiscussion(discussionId) {
    return this.request(`/api/discussions/${discussionId}`);
  }

  async addComment(discussionId, content, parentId = null) {
    const body = { content };
    if (parentId) body.parent_id = parentId;
    return this.request(`/api/discussions/${discussionId}/comments`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  /* ==========================================
     Notifications
     ========================================== */
  async getNotifications(unreadOnly = false) {
    return this.request(`/api/notifications?unread_only=${unreadOnly}`);
  }

  async markNotificationRead(notificationId) {
    return this.request(`/api/notifications/${notificationId}/read`, {
      method: 'POST'
    });
  }

  async markAllNotificationsRead() {
    return this.request('/api/notifications/read-all', {
      method: 'POST'
    });
  }

  /* ==========================================
     Admin & Moderation Suite
     ========================================== */
  async adminGetAnalytics() {
    return this.request('/api/admin/analytics');
  }

  async adminCreateChallenge(formData) {
    return this.request('/api/challenges', {
      method: 'POST',
      body: formData
    });
  }

  async adminUpdateChallenge(challengeId, data) {
    return this.request(`/api/challenges/${challengeId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  async adminDeleteChallenge(challengeId, hard = true) {
    return this.request(`/api/challenges/${challengeId}?hard=${hard}`, {
      method: 'DELETE'
    });
  }

  async adminCreateEvent(data) {
    return this.request('/api/events', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async adminAddChallengeToEvent(eventId, challengeId, pointsOverride = null, displayOrder = 1) {
    const body = { challenge_id: challengeId, display_order: displayOrder };
    if (pointsOverride != null) body.points_override = pointsOverride;
    return this.request(`/api/events/${eventId}/challenges`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  async adminUpdateEvent(eventId, data) {
    return this.request(`/api/events/${eventId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async adminDeleteEvent(eventId) {
    return this.request(`/api/events/${eventId}`, {
      method: 'DELETE'
    });
  }

  async adminRemoveChallengeFromEvent(eventId, challengeId) {
    return this.request(`/api/events/${eventId}/challenges/${challengeId}`, {
      method: 'DELETE'
    });
  }

  async adminFreezeScoreboard(eventId) {
    return this.request(`/api/events/${eventId}/freeze-scoreboard`, {
      method: 'POST'
    });
  }

  async adminUnfreezeScoreboard(eventId) {
    return this.request(`/api/events/${eventId}/unfreeze-scoreboard`, {
      method: 'POST'
    });
  }

  async adminDistributeCertificates(eventId) {
    return this.request(`/api/events/${eventId}/distribute-certificates`, {
      method: 'POST'
    });
  }

  async adminGetEventAuditBreakdown(eventId) {
    return this.request(`/api/events/${eventId}/audit-breakdown`);
  }



  async adminListSecurityEvents(status = '', severity = '') {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/admin/security-events${qs}`);
  }

  async adminReviewSecurityEvent(eventId, reviewNotes, newStatus) {
    return this.request(`/api/admin/security-events/${eventId}/review`, {
      method: 'POST',
      body: JSON.stringify({ note: reviewNotes, status: newStatus })
    });
  }


  async adminListUsers(search = '', role = '', isBanned = '', isMuted = '', page = 1, limit = 20) {
    const params = new URLSearchParams({ page, limit });
    if (search) params.append('search', search);
    if (role) params.append('role', role);
    if (isBanned !== '') params.append('is_banned', isBanned);
    if (isMuted !== '') params.append('is_muted', isMuted);
    return this.request(`/api/admin/users?${params.toString()}`);
  }

  async adminUpdateUser(userId, data) {
    return this.request(`/api/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  /* ==========================================
     Community Writeups & Solutions
     ========================================== */
  async getCommunityWriteups(challengeId) {
    return this.request(`/api/challenges/${challengeId}/solutions`);
  }

  async publishCommunityWriteup(challengeId, data) {
    return this.request(`/api/challenges/${challengeId}/solutions`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateCommunityWriteup(challengeId, writeupId, data) {
    return this.request(`/api/challenges/${challengeId}/solutions/${writeupId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async deleteCommunityWriteup(challengeId, writeupId) {
    return this.request(`/api/challenges/${challengeId}/solutions/${writeupId}`, {
      method: 'DELETE'
    });
  }

  async upvoteCommunityWriteup(challengeId, writeupId) {
    return this.request(`/api/challenges/${challengeId}/solutions/${writeupId}/upvote`, {
      method: 'POST'
    });
  }

  /* ==========================================
     Social Network & Follows (LeetCode style)
     ========================================== */
  async toggleFollowUser(userId) {
    return this.request(`/api/users/${userId}/follow`, {
      method: 'POST'
    });
  }

  async unfollowUser(userId) {
    return this.request(`/api/users/${userId}/follow`, {
      method: 'DELETE'
    });
  }

  async getUserFollowers(userId) {
    return this.request(`/api/users/${userId}/followers`);
  }

  async getUserFollowing(userId) {
    return this.request(`/api/users/${userId}/following`);
  }

  /* ==========================================
     GitHub OAuth & Repository Sync Integration
     ========================================== */
  async getGitHubAuthUrl() {
    return this.request('/api/github/oauth/url');
  }

  async getGitHubStatus() {
    return this.request('/api/github/status');
  }

  async getGitHubRepositories() {
    return this.request('/api/github/repositories');
  }

  async configureGitHubRepository(repository, autoCreate = false) {
    return this.request('/api/github/repository', {
      method: 'POST',
      body: JSON.stringify({ repository, auto_create: autoCreate })
    });
  }

  async syncGitHubSubmissions() {
    return this.request('/api/github/sync', {
      method: 'POST'
    });
  }

  async disconnectGitHub() {
    return this.request('/api/github/disconnect', {
      method: 'POST'
    });
  }

  async exchangeGitHubOAuth(payload) {
    return this.request('/api/github/oauth/exchange', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }
}

// Global API instance
window.api = new ApiClient();

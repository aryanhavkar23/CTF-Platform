/**
 * OWASP CTF Platform — State Management & Core Utilities
 */

const state = {
  currentUser: null,
  currentScore: null,
  categories: [],
  activeView: 'landing',
  unreadNotificationsCount: 0,
  selectedEventId: null,
  selectedChallengeId: null,
};

window.state = state;

/* ==========================================
   Toast Notification System
   ========================================== */
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-weight:bold; font-size:14px;">${icons[type] || '•'}</span>
    <span style="flex:1;">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, duration);
}
window.showToast = showToast;

/* ==========================================
   Modal Controller
   ========================================== */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}
window.openModal = openModal;

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}
window.closeModal = closeModal;

// Close modals on backdrop click or ESC key
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.open').forEach(m => {
      m.classList.remove('open');
    });
    document.body.style.overflow = '';
  }
});

/* ==========================================
   Formatters & Sanitizers
   ========================================== */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
window.escapeHtml = escapeHtml;

function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleDateString(undefined, { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}
window.formatDate = formatDate;

function formatCountdown(targetIsoDate) {
  if (!targetIsoDate) return '00:00:00';
  const target = new Date(targetIsoDate).getTime();
  const now = Date.now();
  const diff = target - now;

  if (diff <= 0) return '00d 00h 00m 00s';

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  return `${String(days).padStart(2, '0')}d ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`;
}
window.formatCountdown = formatCountdown;

function getDifficultyBadge(difficulty) {
  const diff = (difficulty || 'easy').toLowerCase();
  return `<span class="badge badge-${diff}">${diff.toUpperCase()}</span>`;
}
window.getDifficultyBadge = getDifficultyBadge;

function getRoleBadge(role) {
  const r = (role || 'student').toLowerCase();
  return `<span class="role-badge role-${r}">${r}</span>`;
}
window.getRoleBadge = getRoleBadge;

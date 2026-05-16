// ═══════════ Notes App — Frontend ═══════════
const API = window.location.origin;
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ── State ──
let state = {
    token: localStorage.getItem('notes_token'),
    userEmail: localStorage.getItem('notes_email') || '',
    notes: [],
    sharedNotes: [],
    activeNoteId: null,
    activeNoteOwner: null,
    isNewNote: false, // true when creating a new note (no API call yet)
    searchTimeout: null,
};

// ── API Helper ──
async function api(method, path, body) {
    const h = { 'Content-Type': 'application/json' };
    if (state.token) h['Authorization'] = `Bearer ${state.token}`;
    const opts = { method, headers: h };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    if (res.status === 204) return { ok: true, status: 204, data: null };
    let data; try { data = await res.json(); } catch { data = null; }
    return { ok: res.ok, status: res.status, data };
}

// ── Toast ──
function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    el.innerHTML = `<strong>${icons[type] || 'ℹ'}</strong> ${msg}`;
    $('#toast-container').appendChild(el);
    setTimeout(() => { el.classList.add('toast-out'); setTimeout(() => el.remove(), 250); }, 3200);
}

// ═══════════ AUTH ═══════════
$$('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        $$('.auth-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const t = tab.dataset.tab;
        $('#login-form').classList.toggle('hidden', t !== 'login');
        $('#register-form').classList.toggle('hidden', t !== 'register');
        $('#auth-error').classList.add('hidden');
    });
});

$('#register-form').addEventListener('submit', async e => {
    e.preventDefault();
    const email = $('#register-email').value;
    const pw = $('#register-password').value;
    if (pw !== $('#register-password-confirm').value) { showAuthErr('Passwords do not match'); return; }
    setAuthLoad(true, 'register');
    const r = await api('POST', '/register', { email, password: pw });
    setAuthLoad(false, 'register');
    if (r.ok) { toast('Account created! Sign in now.', 'success'); $('#tab-login').click(); $('#login-email').value = email; }
    else showAuthErr(r.data?.detail || r.data?.message || 'Registration failed');
});

$('#login-form').addEventListener('submit', async e => {
    e.preventDefault();
    const email = $('#login-email').value;
    const pw = $('#login-password').value;
    setAuthLoad(true, 'login');
    const r = await api('POST', '/login', { email, password: pw });
    setAuthLoad(false, 'login');
    if (r.ok && r.data?.access_token) {
        state.token = r.data.access_token;
        state.userEmail = email;
        localStorage.setItem('notes_token', state.token);
        localStorage.setItem('notes_email', email);
        enterApp();
    } else showAuthErr(r.data?.message || r.data?.detail || 'Invalid credentials');
});

function showAuthErr(msg) { const el = $('#auth-error'); el.textContent = msg; el.classList.remove('hidden'); }
function setAuthLoad(on, form) {
    const btn = form === 'login' ? $('#login-btn') : $('#register-btn');
    btn.querySelector('span').classList.toggle('hidden', on);
    btn.querySelector('.btn-spinner').classList.toggle('hidden', !on);
    btn.disabled = on;
}

$('#logout-btn').addEventListener('click', () => {
    state.token = null; state.notes = []; state.sharedNotes = []; state.activeNoteId = null; state.isNewNote = false;
    localStorage.removeItem('notes_token'); localStorage.removeItem('notes_email');
    $('#auth-screen').classList.remove('hidden'); $('#app-screen').classList.add('hidden');
    $('#login-form').reset(); $('#register-form').reset(); $('#auth-error').classList.add('hidden');
});

// ═══════════ APP INIT ═══════════
function enterApp() {
    $('#auth-screen').classList.add('hidden'); $('#app-screen').classList.remove('hidden');
    const email = state.userEmail;
    $('#user-email').textContent = email;
    // Better avatar: first letter of email, colorized
    const avatar = $('#user-avatar');
    avatar.textContent = email ? email[0].toUpperCase() : '?';
    // Assign consistent color based on email
    avatar.style.background = emailToColor(email);
    loadAllNotes();
    startLiveClock();
}

function emailToColor(email) {
    if (!email) return '#6b6b6b';
    let hash = 0;
    for (let i = 0; i < email.length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash);
    const colors = ['#e57373','#7986cb','#4db6ac','#ff8a65','#ba68c8','#4fc3f7','#81c784','#ffb74d','#a1887f','#90a4ae'];
    return colors[Math.abs(hash) % colors.length];
}

async function loadAllNotes() {
    const [own, shared] = await Promise.all([api('GET', '/notes'), api('GET', '/shared')]);
    if (own.ok) state.notes = own.data;
    if (shared.ok) state.sharedNotes = shared.data;
    if (own.status === 401 || shared.status === 401) { $('#logout-btn').click(); toast('Session expired.', 'error'); return; }
    renderSidebar();
}

// ═══════════ SIDEBAR RENDERING ═══════════
function renderSidebar() {
    renderNotesList('#my-notes-list', state.notes, false);
    renderNotesList('#shared-notes-list', state.sharedNotes, true);
    $('#my-notes-count').textContent = state.notes.length;
    $('#shared-notes-count').textContent = state.sharedNotes.length;
    // Hide shared section if empty
    const sharedSection = $('#shared-notes-list').closest('.sidebar-section');
    if (sharedSection) sharedSection.style.display = state.sharedNotes.length ? '' : 'none';
}

function renderNotesList(selector, notes, isShared) {
    const el = $(selector);
    if (!notes.length) {
        el.innerHTML = `<div class="notes-list-empty">${isShared ? 'No shared notes' : 'Create your first note'}</div>`;
        return;
    }
    el.innerHTML = notes.map(n => {
        const title = n.title && n.title.trim() ? esc(n.title) : '<span class="text-muted">Untitled</span>';
        const content = n.content && n.content.trim() ? n.content : '';
        const preview = esc(content.substring(0, 70));
        return `<div class="note-item ${n.id === state.activeNoteId ? 'active' : ''}" data-id="${n.id}" data-shared="${isShared}">
            <div class="note-item-title">${title}</div>
            ${preview ? `<div class="note-item-preview">${preview}</div>` : ''}
            <div class="note-item-meta">
                <span class="live-time" data-time="${n.updated_at}">${timeAgo(n.updated_at)}</span>
            </div>
        </div>`;
    }).join('');
    el.querySelectorAll('.note-item').forEach(item => {
        item.addEventListener('click', () => selectNote(item.dataset.id, item.dataset.shared === 'true'));
    });
}

// ═══════════ NOTE SELECTION ═══════════
async function selectNote(id, isShared) {
    state.activeNoteId = id;
    state.isNewNote = false;
    const r = await api('GET', `/notes/${id}`);
    if (!r.ok) { toast('Failed to load note', 'error'); return; }
    const note = r.data;
    state.activeNoteOwner = note.owner_id;
    const isOwner = !isShared;

    showEditor();
    $('#editor-title').value = note.title || '';
    $('#editor-content').value = note.content && note.content.trim() ? note.content : '';
    $('#editor-timestamp').textContent = formatTimestamp(note.updated_at);
    $('#editor-timestamp').dataset.time = note.updated_at;
    $('#save-status').textContent = '';

    // Shared badge
    $('#editor-owner-badge').classList.toggle('hidden', isOwner);

    // Read-only for shared notes
    $('#editor-title').readOnly = !isOwner;
    $('#editor-content').readOnly = !isOwner;
    $('#btn-save').classList.toggle('hidden', !isOwner);
    $('#btn-delete').classList.toggle('hidden', !isOwner);
    $('#btn-share').classList.toggle('hidden', !isOwner);

    if (isOwner) loadSharedAvatars(id);
    else $('#shared-avatars').innerHTML = '';

    $$('.note-item').forEach(el => el.classList.toggle('active', el.dataset.id === id));
    $('#history-panel').classList.add('hidden');
}

function showEditor() {
    $('#empty-state').classList.add('hidden');
    $('#note-editor').classList.remove('hidden');
}

async function loadSharedAvatars(noteId) {
    const r = await api('GET', `/notes/${noteId}/shares`);
    const container = $('#shared-avatars');
    if (!r.ok || !r.data?.length) { container.innerHTML = ''; return; }
    container.innerHTML = r.data.map(u => {
        const initial = u.email[0].toUpperCase();
        const color = emailToColor(u.email);
        return `<div class="shared-avatar" style="background:${color}" title="${esc(u.email)} · ${u.access} access">${initial}</div>`;
    }).join('');
}

// ═══════════ CREATE NOTE (client-side first, API on save) ═══════════
function createNote() {
    state.isNewNote = true;
    state.activeNoteId = null;
    $$('.note-item').forEach(el => el.classList.remove('active'));

    showEditor();
    $('#editor-title').value = '';
    $('#editor-content').value = '';
    $('#editor-timestamp').textContent = 'New note';
    $('#editor-timestamp').dataset.time = '';
    $('#save-status').textContent = '';
    $('#editor-owner-badge').classList.add('hidden');
    $('#editor-title').readOnly = false;
    $('#editor-content').readOnly = false;
    $('#btn-save').classList.remove('hidden');
    $('#btn-delete').classList.add('hidden');  // Can't delete unsaved note
    $('#btn-share').classList.add('hidden');   // Can't share unsaved note
    $('#shared-avatars').innerHTML = '';

    // Focus title immediately
    setTimeout(() => $('#editor-title').focus(), 50);
}
$('#new-note-btn').addEventListener('click', createNote);
$('#empty-new-note-btn').addEventListener('click', createNote);

// ═══════════ SAVE NOTE ═══════════
$('#btn-save').addEventListener('click', async () => {
    const title = $('#editor-title').value.trim();
    const content = $('#editor-content').value.trim();

    if (!title) { toast('Please add a title first', 'error'); $('#editor-title').focus(); return; }
    if (!content) { toast('Write something in your note', 'error'); $('#editor-content').focus(); return; }

    if (state.isNewNote) {
        // CREATE — first API call
        const r = await api('POST', '/notes', { title, content });
        if (r.ok) {
            state.isNewNote = false;
            state.activeNoteId = r.data.id;
            $('#save-status').textContent = '✓ Created';
            $('#btn-delete').classList.remove('hidden');
            $('#btn-share').classList.remove('hidden');
            $('#editor-timestamp').textContent = formatTimestamp(r.data.updated_at);
            $('#editor-timestamp').dataset.time = r.data.updated_at;
            toast('Note created', 'success');
            loadAllNotes();
        } else toast(r.data?.detail || 'Failed to create', 'error');
    } else {
        // UPDATE — existing note
        const r = await api('PUT', `/notes/${state.activeNoteId}`, { title, content });
        if (r.ok) {
            $('#save-status').textContent = '✓ Saved';
            toast('Note saved', 'success');
            loadAllNotes();
        } else toast(r.data?.detail || 'Failed to save', 'error');
    }
    setTimeout(() => { $('#save-status').textContent = ''; }, 2500);
});

// ═══════════ DELETE NOTE ═══════════
$('#btn-delete').addEventListener('click', async () => {
    if (!state.activeNoteId) return;
    if (!confirm('Delete this note permanently?')) return;
    const r = await api('DELETE', `/notes/${state.activeNoteId}`);
    if (r.ok || r.status === 204) {
        toast('Note deleted', 'info');
        state.activeNoteId = null; state.isNewNote = false;
        $('#empty-state').classList.remove('hidden'); $('#note-editor').classList.add('hidden');
        loadAllNotes();
    } else toast(r.data?.detail || 'Failed to delete', 'error');
});

// ═══════════ SHARE ═══════════
$('#btn-share').addEventListener('click', async () => {
    if (!state.activeNoteId) return;
    $('#share-modal').classList.remove('hidden'); $('#share-email').value = ''; $('#share-email').focus();
    const r = await api('GET', `/notes/${state.activeNoteId}/shares`);
    const section = $('#share-current'); const list = $('#share-current-list');
    if (r.ok && r.data?.length) {
        section.classList.remove('hidden');
        list.innerHTML = r.data.map(u => `
            <div class="share-user-row">
                <div class="share-user-left">
                    <div class="share-user-avatar" style="background:${emailToColor(u.email)}">${u.email[0].toUpperCase()}</div>
                    <span>${esc(u.email)}</span>
                </div>
                <span class="share-user-access">Can ${u.access}</span>
            </div>`).join('');
    } else { section.classList.add('hidden'); list.innerHTML = ''; }
});

$('#share-modal-close').addEventListener('click', () => $('#share-modal').classList.add('hidden'));
$('#share-cancel').addEventListener('click', () => $('#share-modal').classList.add('hidden'));
$('#share-modal').addEventListener('click', e => { if (e.target === $('#share-modal')) $('#share-modal').classList.add('hidden'); });

$('#share-confirm').addEventListener('click', async () => {
    const email = $('#share-email').value.trim();
    if (!email) { toast('Enter an email', 'error'); return; }
    const r = await api('POST', `/notes/${state.activeNoteId}/share`, { share_with_email: email });
    if (r.ok) {
        toast(`Shared with ${email}`, 'success');
        $('#share-modal').classList.add('hidden');
        loadSharedAvatars(state.activeNoteId);
    } else toast(r.data?.detail || 'Failed to share', 'error');
});

// ═══════════ VERSION HISTORY ═══════════
$('#btn-history').addEventListener('click', async () => {
    if (!state.activeNoteId) return;
    if (!$('#history-panel').classList.contains('hidden')) { $('#history-panel').classList.add('hidden'); return; }
    const r = await api('GET', `/notes/${state.activeNoteId}/history`);
    if (!r.ok) { toast('Failed to load history', 'error'); return; }
    const history = r.data;
    $('#history-current-title').textContent = $('#editor-title').value || 'Untitled';
    const ts = $('#editor-timestamp').dataset.time;
    $('#history-current-time').textContent = ts ? timeAgo(ts) : 'Now';
    const listEl = $('#history-list');
    const emptyEl = $('#history-empty');
    if (!history.length) {
        listEl.innerHTML = ''; emptyEl.classList.remove('hidden');
    } else {
        emptyEl.classList.add('hidden');
        listEl.innerHTML = history.map(h => `
            <div class="history-entry-wrap">
                <div class="timeline-dot dot-past"></div>
                <div class="history-card" data-title="${esc(h.title)}" data-content="${esc(h.content)}">
                    <div class="history-card-header">
                        <span class="history-tag tag-past">v${h.version}</span>
                        <span class="history-time live-time" data-time="${h.edited_at}">${timeAgo(h.edited_at)}</span>
                    </div>
                    <div class="history-card-title">${esc(h.title) || 'Untitled'}</div>
                    <div class="history-card-preview">${esc((h.content || '').substring(0, 80))}</div>
                </div>
            </div>`).join('');
        listEl.querySelectorAll('.history-card').forEach(card => {
            card.addEventListener('click', () => {
                $('#editor-title').value = card.dataset.title;
                $('#editor-content').value = card.dataset.content;
                toast('Version loaded. Click Save to apply.', 'info');
                $('#history-panel').classList.add('hidden');
            });
        });
    }
    $('#history-panel').classList.remove('hidden');
});
$('#history-close').addEventListener('click', () => $('#history-panel').classList.add('hidden'));

// ═══════════ SEARCH ═══════════
$('#search-input').addEventListener('input', e => {
    clearTimeout(state.searchTimeout);
    const q = e.target.value.trim();
    if (!q) { loadAllNotes(); return; }
    state.searchTimeout = setTimeout(async () => {
        const r = await api('GET', `/search?q=${encodeURIComponent(q)}`);
        if (r.ok) { renderNotesList('#my-notes-list', r.data, false); $('#my-notes-count').textContent = r.data.length; }
    }, 300);
});

// ═══════════ SIDEBAR TOGGLE ═══════════
$('#sidebar-toggle').addEventListener('click', () => $('#sidebar').classList.add('open'));
$('#sidebar-collapse').addEventListener('click', () => $('#sidebar').classList.remove('open'));

// ═══════════ LIVE CLOCK ═══════════
function startLiveClock() {
    setInterval(() => {
        document.querySelectorAll('.live-time').forEach(el => {
            if (el.dataset.time) el.textContent = timeAgo(el.dataset.time);
        });
        const edTs = $('#editor-timestamp');
        if (edTs && edTs.dataset.time) edTs.textContent = formatTimestamp(edTs.dataset.time);
    }, 10000);
}

// ═══════════ KEYBOARD SHORTCUTS ═══════════
document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); if (state.activeNoteId || state.isNewNote) $('#btn-save').click(); }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); $('#search-input').focus(); }
    if (e.key === 'Escape') { $('#share-modal').classList.add('hidden'); $('#history-panel').classList.add('hidden'); }
});

// ═══════════ UTILS ═══════════
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
// Parse server datetime — server returns naive UTC (no Z suffix), so we add it
function parseDate(dateStr) {
    if (!dateStr) return new Date();
    // If the string has no timezone indicator, treat as UTC
    const s = String(dateStr);
    if (!s.endsWith('Z') && !s.includes('+') && !s.includes('-', 10)) {
        return new Date(s + 'Z');
    }
    return new Date(s);
}

function timeAgo(dateStr) {
    const d = parseDate(dateStr); const now = new Date(); const s = Math.floor((now - d) / 1000);
    if (s < 0) return 'Just now'; // future dates (clock skew)
    if (s < 5) return 'Just now'; if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
    const days = Math.floor(h / 24); if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
function formatTimestamp(dateStr) {
    const d = parseDate(dateStr);
    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return `Last edited ${timeAgo(dateStr)} · ${time}`;
}

// ═══════════ INIT ═══════════
if (state.token) enterApp();
else { $('#auth-screen').classList.remove('hidden'); $('#app-screen').classList.add('hidden'); }

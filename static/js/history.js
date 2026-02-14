// ═══════ History Page Logic ═══════

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadHistory();
    initModal();
    initLogout();
});

function checkAuth() {
    const token = localStorage.getItem('yt_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    const user = JSON.parse(localStorage.getItem('yt_user') || '{}');
    const emailEl = document.getElementById('navUserEmail');
    if (emailEl) emailEl.textContent = user.email || '';
}

function initLogout() {
    document.getElementById('btnLogout')?.addEventListener('click', () => {
        localStorage.removeItem('yt_token');
        localStorage.removeItem('yt_user');
        window.location.href = '/login';
    });
}

// ─── Markdown Parser (lightweight) ───

function parseMarkdown(md) {
    if (!md) return '';
    let html = md
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold & Italic
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
        // Horizontal rule
        .replace(/^---$/gm, '<hr>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap in paragraph
    html = '<p>' + html + '</p>';

    // Parse tables
    html = parseTables(html);

    return html;
}

function parseTables(html) {
    const tableRegex = /\|(.+)\|[\s]*<br>\|[-| :]+\|([\s\S]*?)(?=<\/p>|<h[1-6]|$)/g;
    return html.replace(tableRegex, (match, header, body) => {
        const headerCells = header.split('|').map(c => c.trim()).filter(Boolean);
        const rows = body.split('<br>').filter(r => r.includes('|'));

        let table = '<table><thead><tr>';
        headerCells.forEach(cell => { table += `<th>${cell}</th>`; });
        table += '</tr></thead><tbody>';

        rows.forEach(row => {
            const cells = row.split('|').map(c => c.trim()).filter(Boolean);
            if (cells.length > 0 && !cells[0].match(/^[-:]+$/)) {
                table += '<tr>';
                cells.forEach(cell => { table += `<td>${cell}</td>`; });
                table += '</tr>';
            }
        });

        table += '</tbody></table>';
        return table;
    });
}

// ─── Load History ───

let historyData = [];

async function loadHistory() {
    try {
        const token = localStorage.getItem('yt_token');
        const res = await fetch('/api/history', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            document.getElementById('historyEmpty').style.display = 'block';
            return;
        }

        const data = await res.json();
        historyData = data.history || [];

        if (historyData.length === 0) {
            document.getElementById('historyEmpty').style.display = 'block';
            return;
        }

        renderHistory();
    } catch (err) {
        console.error('Failed to load history:', err);
        document.getElementById('historyEmpty').style.display = 'block';
    }
}

function renderHistory() {
    const container = document.getElementById('historyList');
    container.innerHTML = '';

    historyData.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.style.animationDelay = `${i * 0.05}s`;

        const thumbUrl = item.video_id
            ? `https://img.youtube.com/vi/${item.video_id}/mqdefault.jpg`
            : '';

        const date = new Date(item.created_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });

        card.innerHTML = `
            <div class="card-thumbnail">
                ${thumbUrl ? `<img src="${thumbUrl}" alt="thumbnail">` : ''}
            </div>
            <div class="card-info">
                <div class="card-title">${escapeHtml(item.title || 'Untitled')}</div>
                <div class="card-meta">
                    <span>📅 ${date}</span>
                    <span>🌍 ${item.language || 'English'}</span>
                    <span>📝 ${item.transcript_length ? Math.round(item.transcript_length / 100) + ' paragraphs' : ''}</span>
                </div>
            </div>
            <button class="card-delete" data-id="${item.id}" title="Delete">🗑️</button>
        `;

        // Open modal on card click
        card.addEventListener('click', (e) => {
            if (e.target.closest('.card-delete')) return;
            openModal(item);
        });

        // Delete button
        card.querySelector('.card-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteNote(item.id, card);
        });

        container.appendChild(card);
    });
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ─── Modal ───

let currentNoteId = null;

function initModal() {
    document.getElementById('modalClose')?.addEventListener('click', closeModal);
    document.getElementById('noteModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'noteModal') closeModal();
    });

    document.getElementById('btnCopyNotes')?.addEventListener('click', () => {
        const note = historyData.find(n => n.id === currentNoteId);
        if (note) {
            navigator.clipboard.writeText(note.notes)
                .then(() => {
                    document.getElementById('btnCopyNotes').textContent = '✅ Copied!';
                    setTimeout(() => {
                        document.getElementById('btnCopyNotes').textContent = '📋 Copy Notes';
                    }, 2000);
                });
        }
    });

    document.getElementById('btnDeleteNote')?.addEventListener('click', () => {
        if (currentNoteId) {
            deleteNote(currentNoteId);
            closeModal();
        }
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

function openModal(item) {
    currentNoteId = item.id;
    const modal = document.getElementById('noteModal');
    document.getElementById('modalTitle').textContent = item.title || 'Notes';

    const date = new Date(item.created_at).toLocaleDateString('en-US', {
        month: 'long', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    document.getElementById('modalMeta').innerHTML = `
        <span>📅 ${date}</span>
        <span>🌍 ${item.language || 'English'}</span>
        <span>🔗 <a href="${item.youtube_url}" target="_blank" style="color:var(--accent-2)">Watch Video</a></span>
    `;

    document.getElementById('modalBody').innerHTML = parseMarkdown(item.notes);
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('noteModal').style.display = 'none';
    document.body.style.overflow = '';
    currentNoteId = null;
}

// ─── Delete Note ───

async function deleteNote(noteId, cardEl) {
    if (!confirm('Delete this note permanently?')) return;

    try {
        const token = localStorage.getItem('yt_token');
        const res = await fetch(`/api/history/${noteId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            historyData = historyData.filter(n => n.id !== noteId);
            if (cardEl) {
                cardEl.style.transition = 'all 0.3s ease';
                cardEl.style.opacity = '0';
                cardEl.style.transform = 'translateX(40px)';
                setTimeout(() => cardEl.remove(), 300);
            }
            if (historyData.length === 0) {
                document.getElementById('historyEmpty').style.display = 'block';
            }
        }
    } catch (err) {
        console.error('Delete failed:', err);
    }
}

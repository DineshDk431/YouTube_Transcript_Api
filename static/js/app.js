// ================================================
// YouTube Transcripter — Dashboard JavaScript
// ================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initScrollReveal();
    initNavbar();
    initForm();
    initVideoPreview();
    initScrollTop();
    initLanguageSelector();
});

// ─── Auth Check ────────────────────────────
function checkAuth() {
    const token = localStorage.getItem('yt_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    const user = JSON.parse(localStorage.getItem('yt_user') || '{}');
    const emailDisplay = document.getElementById('navUserEmail');
    if (emailDisplay && user.email) {
        emailDisplay.textContent = user.email;
    }

    // Logout
    document.getElementById('btnLogout').addEventListener('click', () => {
        localStorage.removeItem('yt_token');
        localStorage.removeItem('yt_user');
        window.location.href = '/';
    });
}

// ─── Scroll Reveal (3D Animations) ────────
function initScrollReveal() {
    const elements = document.querySelectorAll('.scroll-reveal');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const delay = parseInt(entry.target.dataset.delay) || 0;
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, delay);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
    });

    elements.forEach(el => observer.observe(el));
}

// ─── Navbar Scroll Effect ──────────────────
function initNavbar() {
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }, { passive: true });
}

// ─── Scroll to Top ─────────────────────────
function initScrollTop() {
    const btn = document.getElementById('btnScrollTop');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 400) {
            btn.classList.remove('hidden');
        } else {
            btn.classList.add('hidden');
        }
    }, { passive: true });

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ─── Video Preview ─────────────────────────
function initVideoPreview() {
    const urlInput = document.getElementById('youtubeUrl');
    const previewSection = document.getElementById('videoPreview');
    const videoEmbed = document.getElementById('videoEmbed');

    let debounceTimer;

    urlInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const videoId = extractVideoId(urlInput.value);
            if (videoId) {
                videoEmbed.src = `https://www.youtube.com/embed/${videoId}`;
                previewSection.classList.add('visible');
            } else {
                previewSection.classList.remove('visible');
                videoEmbed.src = '';
            }
        }, 500);
    });
}

// ─── Extract Youtube Video ID ──────────────
function extractVideoId(url) {
    if (!url) return null;

    const patterns = [
        /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    return null;
}



// ─── Language Selector ─────────────────────
function initLanguageSelector() {
    const langSelect = document.getElementById('outputLanguage');
    const customWrapper = document.getElementById('customLangWrapper');

    if (langSelect) {
        langSelect.addEventListener('change', () => {
            if (langSelect.value === 'custom') {
                customWrapper.classList.remove('hidden');
                document.getElementById('customLanguage').focus();
            } else {
                customWrapper.classList.add('hidden');
            }
        });
    }
}

function getSelectedLanguage() {
    const langSelect = document.getElementById('outputLanguage');
    if (langSelect.value === 'custom') {
        const custom = document.getElementById('customLanguage').value.trim();
        return custom || 'English';
    }
    return langSelect.value;
}

// ─── Form Submission ───────────────────────
function initForm() {
    const form = document.getElementById('generateForm');
    const btnGenerate = document.getElementById('btnGenerate');
    const genText = document.getElementById('genText');
    const genSpinner = document.getElementById('genSpinner');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = document.getElementById('youtubeUrl').value.trim();

        if (!url) {
            showToast('Please enter a YouTube URL', 'error');
            return;
        }

        const videoId = extractVideoId(url);
        if (!videoId) {
            showToast('Invalid YouTube URL. Please check and try again.', 'error');
            return;
        }

        // Start generating
        setGenerating(true);
        showProcessing(true);

        try {
            const token = localStorage.getItem('yt_token');
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    youtube_url: url,
                    output_language: getSelectedLanguage(),
                    model: document.getElementById('modelSelector').value
                })
            });

            if (res.status === 401) {
                localStorage.removeItem('yt_token');
                localStorage.removeItem('yt_user');
                window.location.href = '/';
                return;
            }

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Failed to start generation');
            }

            const taskId = data.task_id;
            console.log(`Task started: ${taskId}`);

            let isFinished = false; // Flag to prevent multiple completions

            // Poll for status
            const pollInterval = setInterval(async () => {
                if (isFinished) {
                    clearInterval(pollInterval);
                    return;
                }

                try {
                    const statusRes = await fetch(`/api/tasks/${taskId}`);
                    if (!statusRes.ok) throw new Error("Network error checking status");

                    const statusData = await statusRes.json();

                    if (isFinished) return; // check again after await

                    if (statusData.status === 'completed') {
                        isFinished = true;
                        clearInterval(pollInterval);
                        showProcessing(false);
                        renderNotes(statusData.result.notes);
                        showToast('Notes generated successfully! 🎉', 'success');
                        setGenerating(false);
                    } else if (statusData.status === 'failed') {
                        isFinished = true;
                        clearInterval(pollInterval);
                        showProcessing(false);
                        showToast(`Generation failed: ${statusData.error}`, 'error');
                        setGenerating(false);
                    } else {
                        // Still processing...
                        console.log(`Task status: ${statusData.status}`);
                        // Optional: update UI with step info if available
                        if (statusData.result && statusData.result.step) {
                            document.getElementById('processingStatus').textContent = `Step: ${statusData.result.step.replace('_', ' ')}...`;
                        }
                    }
                } catch (pollErr) {
                    console.error(pollErr);
                    // Don't stop polling on transient errors, but maybe limit retries in prod
                }
            }, 2000);

            // We don't setGenerating(false) here, only inside the poll loop when done.

        } catch (err) {
            showToast(err.message, 'error');
            showProcessing(false);
            setGenerating(false);
        }
    });
}

// ─── Loading State ─────────────────────────
function setGenerating(loading) {
    const btnGenerate = document.getElementById('btnGenerate');
    const genText = document.getElementById('genText');
    const genSpinner = document.getElementById('genSpinner');

    if (loading) {
        genText.classList.add('hidden');
        genSpinner.classList.remove('hidden');
        btnGenerate.disabled = true;
    } else {
        genText.classList.remove('hidden');
        genSpinner.classList.add('hidden');
        btnGenerate.disabled = false;
    }
}

// ─── Processing Animation ──────────────────
function showProcessing(show) {
    const section = document.getElementById('processingSection');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');

    if (show) {
        section.classList.remove('hidden');
        section.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Animate steps
        step1.classList.add('active');
        step2.classList.remove('active', 'done');
        step3.classList.remove('active', 'done');

        setTimeout(() => {
            step1.classList.remove('active');
            step1.classList.add('done');
            step2.classList.add('active');
            document.getElementById('processingStatus').textContent = 'Processing with Gemini AI...';
        }, 2000);

        setTimeout(() => {
            step2.classList.remove('active');
            step2.classList.add('done');
            step3.classList.add('active');
            document.getElementById('processingStatus').textContent = 'Generating detailed notes...';
        }, 4000);
    } else {
        section.classList.add('hidden');
    }
}

// ─── Render Notes (Markdown → HTML) ────────
function renderNotes(markdown) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');

    // Simple markdown to HTML conversion
    let html = markdownToHtml(markdown);
    resultsBody.innerHTML = html;

    resultsSection.classList.add('visible');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Setup copy button
    const btnCopy = document.getElementById('btnCopy');
    btnCopy.onclick = () => {
        copyNotes(markdown);
    };

    // Setup download button
    const btnDownload = document.getElementById('btnDownload');
    btnDownload.onclick = () => {
        downloadNotes(markdown);
    };
}

// ─── Markdown → HTML Parser ────────────────
function markdownToHtml(md) {
    if (!md) return '';

    let html = md;

    // Escape HTML
    html = html.replace(/&/g, '&amp;');
    html = html.replace(/</g, '&lt;');
    html = html.replace(/>/g, '&gt;');

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || ''}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold and italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Tables
    html = html.replace(/((?:^\|.+\|\s*$\n?)+)/gm, (match) => {
        const rows = match.trim().split('\n').filter(r => r.trim());
        let table = '<table>';
        rows.forEach((row, i) => {
            if (row.replace(/[|\-\s:]/g, '') === '') return; // separator row
            const cells = row.split('|').filter(c => c.trim() !== '');
            const tag = i === 0 ? 'th' : 'td';
            table += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
        });
        table += '</table>';
        return table;
    });

    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Horizontal rule
    html = html.replace(/^---$/gm, '<hr>');

    // Unordered lists
    html = html.replace(/^[\s]*[-*+] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Fix multiple consecutive ULs
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Line breaks → paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph if needed
    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p><h/g, '<h');
    html = html.replace(/<\/h(\d)><\/p>/g, '</h$1>');
    html = html.replace(/<p><ul/g, '<ul');
    html = html.replace(/<\/ul><\/p>/g, '</ul>');
    html = html.replace(/<p><pre/g, '<pre');
    html = html.replace(/<\/pre><\/p>/g, '</pre>');
    html = html.replace(/<p><hr><\/p>/g, '<hr>');
    html = html.replace(/<p><blockquote/g, '<blockquote');
    html = html.replace(/<\/blockquote><\/p>/g, '</blockquote>');

    return html;
}

// ─── Copy Notes ────────────────────────────
function copyNotes(text) {
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('btnCopy');
        const copyText = document.getElementById('copyText');
        btn.classList.add('copied');
        copyText.textContent = 'Copied!';
        showToast('Notes copied to clipboard! 📋', 'success');

        setTimeout(() => {
            btn.classList.remove('copied');
            copyText.textContent = 'Copy';
        }, 2500);
    }).catch(() => {
        showToast('Failed to copy. Please try again.', 'error');
    });
}

// ─── Download Notes ────────────────────────
function downloadNotes(text) {
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `youtube-notes-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Notes downloaded! 📥', 'success');
}

// ─── Toast Notifications ───────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

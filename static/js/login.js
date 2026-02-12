document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initCharacterAnimation();
    initFormHandlers();
    initCardTilt();
});

function initParticles() {
    const container = document.getElementById('particles');
    const colors = ['#6c5ce7', '#a29bfe', '#fd79a8', '#00b894', '#e17055'];

    for (let i = 0; i < 30; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        const size = Math.random() * 6 + 2;
        const color = colors[Math.floor(Math.random() * colors.length)];

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            left: ${Math.random() * 100}%;
            animation-duration: ${Math.random() * 15 + 10}s;
            animation-delay: ${Math.random() * 10}s;
        `;
        container.appendChild(particle);
    }
}

function initCardTilt() {
    const card = document.getElementById('loginCard');

    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -4;
        const rotateY = ((x - centerX) / centerX) * 4;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
    });
}

// ─── Panda Character Animation ─────────────
function initCharacterAnimation() {
    const emailInput = document.getElementById('emailInput');
    const passwordInput = document.getElementById('passwordInput');
    const character = document.getElementById('character');
    const charMouth = document.getElementById('charMouth');
    const pupilLeft = document.getElementById('pupilLeft');
    const pupilRight = document.getElementById('pupilRight');
    const eyelidLeft = document.getElementById('eyelidLeft');
    const eyelidRight = document.getElementById('eyelidRight');
    const handLeft = document.getElementById('handLeft');
    const handRight = document.getElementById('handRight');

    // Original hand positions
    const handOriginal = {
        left: { cx: 68, cy: 135 },
        right: { cx: 132, cy: 135 }
    };
    // Covering-eyes positions (hands move up to eye level)
    const handCover = {
        left: { cx: 78, cy: 84 },
        right: { cx: 122, cy: 84 }
    };

    // ── Move hands to a position (smooth via CSS transition) ──
    function moveHands(pos) {
        handLeft.setAttribute('cx', pos.left.cx);
        handLeft.setAttribute('cy', pos.left.cy);
        handRight.setAttribute('cx', pos.right.cx);
        handRight.setAttribute('cy', pos.right.cy);
        // Hide paw pads when covering
        document.querySelectorAll('.paw-pad').forEach(p => {
            p.style.opacity = (pos === handCover) ? '0' : '1';
        });
    }

    // ── Email focus: panda watches with open eyes ──
    emailInput.addEventListener('focus', () => {
        character.classList.add('watching');
        character.classList.remove('password-mode');
        moveHands(handOriginal);
        openEyes();
        charMouth.setAttribute('d', 'M 93 100 Q 100 110 107 100');
    });

    // ── Eye tracking: pupils follow text length ──
    emailInput.addEventListener('input', (e) => {
        const val = e.target.value;
        const maxLen = 30;
        const progress = Math.min(val.length / maxLen, 1);
        const offsetX = -3 + (progress * 6);
        const offsetY = -1;
        pupilLeft.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        pupilRight.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
    });

    // ── Password focus: panda closes eyes + paws cover face ──
    passwordInput.addEventListener('focus', () => {
        character.classList.remove('watching');
        character.classList.add('password-mode');
        closeEyes();
        moveHands(handCover);
        charMouth.setAttribute('d', 'M 95 102 Q 100 106 105 102');
    });

    emailInput.addEventListener('blur', () => {
        setTimeout(() => {
            if (document.activeElement !== passwordInput) resetCharacter();
        }, 100);
    });

    passwordInput.addEventListener('blur', () => {
        setTimeout(() => {
            if (document.activeElement !== emailInput) resetCharacter();
        }, 100);
    });

    // ── Close eyes ──
    function closeEyes() {
        eyelidLeft.setAttribute('cy', '82');
        eyelidLeft.setAttribute('ry', '12');
        eyelidRight.setAttribute('cy', '82');
        eyelidRight.setAttribute('ry', '12');
        pupilLeft.style.opacity = '0';
        pupilRight.style.opacity = '0';
        document.querySelectorAll('.eye-shine').forEach(s => s.style.opacity = '0');
        document.querySelectorAll('.eye-white').forEach(e => e.setAttribute('ry', '2'));
    }

    // ── Open eyes ──
    function openEyes() {
        eyelidLeft.setAttribute('cy', '73');
        eyelidLeft.setAttribute('ry', '3');
        eyelidRight.setAttribute('cy', '73');
        eyelidRight.setAttribute('ry', '3');
        pupilLeft.style.opacity = '1';
        pupilRight.style.opacity = '1';
        document.querySelectorAll('.eye-shine').forEach(s => s.style.opacity = '1');
        document.querySelectorAll('.eye-white').forEach(e => e.setAttribute('ry', '11'));
    }

    function resetCharacter() {
        character.classList.remove('watching', 'password-mode');
        moveHands(handOriginal);
        openEyes();
        pupilLeft.style.transform = 'translate(0, 0)';
        pupilRight.style.transform = 'translate(0, 0)';
        charMouth.setAttribute('d', 'M 93 100 Q 100 110 107 100');
    }
}

// ─── Panda Head Shake (wrong password) ─────
function triggerPandaShake() {
    const pandaHead = document.getElementById('pandaHead');
    const loginCard = document.getElementById('loginCard');

    // Shake the panda's head
    pandaHead.classList.add('head-shake');
    loginCard.classList.add('error-shake');

    // Remove after animation completes
    setTimeout(() => {
        pandaHead.classList.remove('head-shake');
        loginCard.classList.remove('error-shake');
    }, 700);
}

let isSignUpMode = false;

function initFormHandlers() {
    const form = document.getElementById('authForm');
    const toggleLink = document.getElementById('toggleLink');
    const toggleMsg = document.getElementById('toggleMsg');
    const formTitle = document.getElementById('formTitle');
    const formSubtitle = document.getElementById('formSubtitle');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const nameGroup = document.getElementById('nameGroup');
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('passwordInput');
    const googleBtn = document.getElementById('googleBtn');

    // Toggle Login / Sign Up
    toggleLink.addEventListener('click', (e) => {
        e.preventDefault();
        isSignUpMode = !isSignUpMode;

        if (isSignUpMode) {
            formTitle.textContent = 'Create Account ✨';
            formSubtitle.textContent = 'Sign up to start generating AI notes';
            btnText.textContent = 'Create Account';
            toggleMsg.textContent = 'Already have an account?';
            toggleLink.textContent = 'Sign In';
            nameGroup.classList.remove('hidden');
        } else {
            formTitle.textContent = 'Welcome Back! 👋';
            formSubtitle.textContent = 'Sign in to generate AI-powered notes';
            btnText.textContent = 'Sign In';
            toggleMsg.textContent = "Don't have an account?";
            toggleLink.textContent = 'Sign Up';
            nameGroup.classList.add('hidden');
        }
    });

    // Toggle password visibility
    togglePassword.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);

        const handLeft = document.getElementById('handLeft');
        const handRight = document.getElementById('handRight');
        if (type === 'text') {
            // Show password — move paws back down
            handLeft.setAttribute('cx', 68);
            handLeft.setAttribute('cy', 135);
            handRight.setAttribute('cx', 132);
            handRight.setAttribute('cy', 135);
        } else if (document.activeElement === passwordInput) {
            // Hide password — paws cover eyes again
            handLeft.setAttribute('cx', 78);
            handLeft.setAttribute('cy', 84);
            handRight.setAttribute('cx', 122);
            handRight.setAttribute('cy', 84);
        }
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('emailInput').value.trim();
        const password = passwordInput.value;
        const name = document.getElementById('nameInput')?.value.trim() || '';

        if (!email || !password) {
            triggerPandaShake();
            showToast('⚠️ Wrong password or mail id! Please enter valid data', 'error');
            return;
        }

        if (password.length < 6) {
            triggerPandaShake();
            showToast('⚠️ Password must be at least 6 characters', 'error');
            return;
        }

        setLoading(true);

        try {
            const endpoint = isSignUpMode ? '/api/signup' : '/api/login';
            const body = isSignUpMode
                ? { email, password, name }
                : { email, password };

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const data = await res.json();

            if (!res.ok) {
                // Wrong credentials → panda shakes head
                triggerPandaShake();
                showToast('⚠️ Wrong password or mail id! Please enter valid data', 'error');
                return;
            }

            // Store token & user info
            localStorage.setItem('yt_token', data.token);
            localStorage.setItem('yt_user', JSON.stringify({ email: data.email, name: data.name }));

            showToast(isSignUpMode ? 'Account created! 🎉' : 'Welcome back! 🎉', 'success');

            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 800);

        } catch (err) {
            // Network or server error → panda shakes head
            triggerPandaShake();
            showToast('⚠️ Wrong password or mail id! Please enter valid data', 'error');
        } finally {
            setLoading(false);
        }
    });

    // Google Sign-In button
    googleBtn.addEventListener('click', () => {
        showToast('ℹ️ Google Sign-In requires OAuth Client ID setup. Using email/password for now.', 'info');
    });
}

function setLoading(loading) {
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const submitBtn = document.getElementById('submitBtn');

    if (loading) {
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');
        submitBtn.disabled = true;
    } else {
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '🐼',
        info: 'ℹ️'
    };

    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

(function checkAuth() {
    const token = localStorage.getItem('yt_token');
    if (token) {
        window.location.href = '/dashboard';
    }
})();

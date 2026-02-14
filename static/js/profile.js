// ═══════ Profile Page Logic ═══════

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadProfile();
    initPhotoUpload();
    initDobCalculation();
    initProfileForm();
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
    const displayEmail = document.getElementById('profileDisplayEmail');
    if (displayEmail) displayEmail.textContent = user.email || '';
}

function initLogout() {
    document.getElementById('btnLogout')?.addEventListener('click', () => {
        localStorage.removeItem('yt_token');
        localStorage.removeItem('yt_user');
        window.location.href = '/login';
    });
}

async function loadProfile() {
    try {
        const token = localStorage.getItem('yt_token');
        const res = await fetch('/api/profile', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        if (data.name) {
            document.getElementById('profileName').value = data.name;
            document.getElementById('profileDisplayName').textContent = data.name;
        }
        if (data.dob) {
            document.getElementById('profileDob').value = data.dob;
            calculateAge(data.dob);
        }
        if (data.gender) {
            document.getElementById('profileGender').value = data.gender;
        }
        if (data.role) {
            const radio = document.querySelector(`input[name="role"][value="${data.role}"]`);
            if (radio) radio.checked = true;
        }
        if (data.photo_url) {
            showAvatar(data.photo_url);
        }
    } catch (err) {
        console.error('Failed to load profile:', err);
    }
}

function showAvatar(url) {
    const img = document.getElementById('avatarImg');
    const placeholder = document.getElementById('avatarPlaceholder');
    img.src = url;
    img.style.display = 'block';
    placeholder.style.display = 'none';
}

function initPhotoUpload() {
    const input = document.getElementById('photoUpload');
    input?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Preview immediately
        const reader = new FileReader();
        reader.onload = (ev) => showAvatar(ev.target.result);
        reader.readAsDataURL(file);

        // Upload
        const formData = new FormData();
        formData.append('photo', file);
        try {
            const token = localStorage.getItem('yt_token');
            const res = await fetch('/api/upload-photo', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                showAvatar(data.photo_url);
            }
        } catch (err) {
            console.error('Upload failed:', err);
        }
    });
}

function initDobCalculation() {
    const dobInput = document.getElementById('profileDob');
    dobInput?.addEventListener('change', () => {
        calculateAge(dobInput.value);
    });
}

function calculateAge(dobStr) {
    if (!dobStr) return;
    const dob = new Date(dobStr);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const monthDiff = today.getMonth() - dob.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
        age--;
    }
    document.getElementById('profileAge').value = age + ' years';
}

function initProfileForm() {
    const form = document.getElementById('profileForm');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const token = localStorage.getItem('yt_token');
        const roleRadio = document.querySelector('input[name="role"]:checked');

        const body = {
            name: document.getElementById('profileName').value.trim(),
            dob: document.getElementById('profileDob').value,
            gender: document.getElementById('profileGender').value,
            role: roleRadio ? roleRadio.value : 'student'
        };

        try {
            const res = await fetch('/api/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(body)
            });

            const status = document.getElementById('saveStatus');
            if (res.ok) {
                status.textContent = '✅ Profile saved! Redirecting...';
                status.classList.add('show');
                // Update display name
                if (body.name) {
                    document.getElementById('profileDisplayName').textContent = body.name;
                }
                // Automatic redirect option
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                status.textContent = '❌ Failed to save';
                status.style.color = '#e74c3c';
                status.classList.add('show');
            }
        } catch (err) {
            console.error('Save failed:', err);
        }
    });
}

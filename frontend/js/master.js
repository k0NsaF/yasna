document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDashboard();
});

// Переключение вкладок
function switchTab(tabId) {
    // Скрываем все секции
    document.querySelectorAll('section[id^="tab-"]').forEach(el => el.style.display = 'none');
    // Убираем активный класс с кнопок
    document.querySelectorAll('.nav-btn').forEach(el => {
        el.style.color = 'var(--gray)';
        el.style.borderBottom = 'none';
    });

    // Показываем нужную
    document.getElementById(`tab-${tabId}`).style.display = 'block';
    const activeBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
    activeBtn.style.color = 'var(--dark)';
    activeBtn.style.borderBottom = '3px solid var(--yellow)';

    // Загружаем данные для вкладки
    if (tabId === 'dashboard') loadDashboard();
    if (tabId === 'schedule') loadSchedule();
    if (tabId === 'attendance') loadAttendance();
    if (tabId === 'families') loadFamilies();
    if (tabId === 'finance') loadFinance();
}

// --- ГЛАВНАЯ ---
async function loadDashboard() {
    try {
        const stats = await masterRequest('/master/dashboard');
        document.getElementById('stat-lessons').innerText = stats.lessonsToday || 0;
        document.getElementById('stat-children').innerText = stats.childrenTotal || 0;
        document.getElementById('stat-ending').innerText = stats.endingSubs || 0;
    } catch (e) { showToast(e.message, 'error'); }
}

// --- РАСПИСАНИЕ ---
async function loadSchedule() {
    try {
        const lessons = await masterRequest('/master/lessons'); // Возвращает массив
        const tbody = document.getElementById('schedule-list');
        tbody.innerHTML = lessons.map(l => `
            <tr>
                <td>${formatDate(l.datetime)}</td>
                <td>${l.title}</td>
                <td>${l.booked} / ${l.capacity}</td>
                <td><button class="btn" style="padding: 6px 12px; font-size: 13px;">Изменить</button></td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function createLesson(e) {
    e.preventDefault();
    const data = {
        title: document.getElementById('lesson-title').value,
        datetime: document.getElementById('lesson-date').value,
        capacity: parseInt(document.getElementById('lesson-capacity').value)
    };
    try {
        await masterRequest('/master/lessons', { method: 'POST', body: JSON.stringify(data) });
        closeModal('modal-create-lesson');
        showToast('Занятие создано');
        loadSchedule();
    } catch (err) { showToast(err.message, 'error'); }
}

// --- ПОСЕЩАЕМОСТЬ ---
async function loadAttendance() {
    try {
        const list = await masterRequest('/master/attendance');
        const tbody = document.getElementById('attendance-list');
        tbody.innerHTML = list.map(a => `
            <tr>
                <td>${a.childName}</td>
                <td>${a.lessonTitle}</td>
                <td><span class="badge ${a.status === 'attended' ? 'badge-green' : 'badge-red'}">${a.status === 'attended' ? 'Посетил' : 'Пропустил'}</span></td>
                <td>
                    <button class="btn" style="padding: 6px 10px; font-size: 12px;" onclick="markAttendance(${a.id}, 'attended')">Посетил</button>
                    <button class="btn btn-gray" style="padding: 6px 10px; font-size: 12px;" onclick="markAttendance(${a.id}, 'missed')">Пропустил</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function markAttendance(id, status) {
    try {
        await masterRequest(`/master/attendance/${id}`, {
            method: 'PATCH',
            body: JSON.stringify({ status })
        });
        showToast('Отметка сохранена');
        loadAttendance();
    } catch (e) { showToast(e.message, 'error'); }
}

// --- СЕМЬИ ---
async function loadFamilies() {
    try {
        const families = await masterRequest('/master/families');
        const tbody = document.getElementById('families-list');
        tbody.innerHTML = families.map(f => `
            <tr>
                <td>${f.parentName}</td>
                <td>${f.children.join(', ')}</td>
                <td>
                    <button class="btn" style="padding: 6px 12px; font-size: 13px;" onclick="generateLink(${f.id})">Выдать ссылку</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

async function createFamily(e) {
    e.preventDefault();
    const data = {
        parentName: document.getElementById('family-name').value,
        childName: document.getElementById('child-name').value
    };
    try {
        await masterRequest('/master/families', { method: 'POST', body: JSON.stringify(data) });
        closeModal('modal-create-family');
        showToast('Семья добавлена');
        loadFamilies();
    } catch (err) { showToast(err.message, 'error'); }
}

async function generateLink(familyId) {
    try {
        const res = await masterRequest(`/master/families/${familyId}/link`, { method: 'POST' });
        // Показываем модалку с токеном (он приходит один раз)
        document.getElementById('family-link-input').value = `${window.location.origin}/family.html?token=${res.token}`;
        openModal('modal-show-link');
    } catch (e) { showToast(e.message, 'error'); }
}

function copyLinkAndClose() {
    const input = document.getElementById('family-link-input');
    input.select();
    document.execCommand('copy');
    closeModal('modal-show-link');
    showToast('Ссылка скопирована в буфер обмена');
}

// --- ФИНАНСЫ ---
async function loadFinance() {
    try {
        const list = await masterRequest('/master/finance');
        const tbody = document.getElementById('finance-list');
        tbody.innerHTML = list.map(item => `
            <tr>
                <td>${item.childName}</td>
                <td>${item.subName}</td>
                <td><b>${item.balance}</b> занятий</td>
                <td>
                    <button class="btn" style="padding: 6px 12px; font-size: 13px;" onclick="alert('Тут будет форма ручной оплаты')">+ Внести</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}
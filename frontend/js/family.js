let currentChildId = null;
let childrenData = [];

document.addEventListener('DOMContentLoaded', async () => {
    // Проверяем токен в URL
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
        localStorage.setItem("family_token", token);
        // Очищаем URL для безопасности
        window.history.replaceState({}, document.title, "family.html");
    }

    if (!localStorage.getItem("family_token") && !USE_MOCK) {
        alert("Доступ запрещен. Перейдите по персональной ссылке.");
        window.location.href = "index.html";
        return;
    }

    await loadFamilyData();
});

async function loadFamilyData() {
    try {
        // Загружаем инфу о семье
        const family = await familyRequest('/family/me');
        document.getElementById('family-title').innerText = family.familyName || 'Личный кабинет';
        
        // Загружаем детей
        childrenData = await familyRequest('/family/children');
        renderChildrenTabs();

        // Загружаем баланс
        const balance = await familyRequest('/family/balance');
        document.getElementById('balance-lessons').innerText = balance.lessons;
        document.getElementById('balance-money').innerText = formatMoney(balance.money);

        // Загружаем расписание (для записи)
        loadUpcomingLessons();
        
        // Загружаем чеки
        loadHistory();
        
    } catch (err) {
        showToast("Ошибка загрузки данных: " + err.message, 'error');
    }
}

function renderChildrenTabs() {
    const container = document.getElementById('children-tabs');
    container.innerHTML = childrenData.map(child => `
        <button class="btn ${currentChildId === child.id || (!currentChildId && childrenData[0].id === child.id) ? '' : 'btn-gray'}" 
                style="padding: 8px 16px; font-size: 14px;"
                onclick="selectChild(${child.id})">
            ${child.name}
        </button>
    `).join('');
    
    if (!currentChildId && childrenData.length > 0) {
        currentChildId = childrenData[0].id;
    }
}

function selectChild(id) {
    currentChildId = id;
    renderChildrenTabs();
    loadUpcomingLessons();
}

async function loadUpcomingLessons() {
    try {
        const lessons = await apiRequest('/lessons'); // Публичный эндпоинт
        const container = document.getElementById('upcoming-lessons');
        
        if (lessons.length === 0) {
            container.innerHTML = '<p style="color: var(--gray);">Нет доступных занятий</p>';
            return;
        }

        container.innerHTML = lessons.map(l => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #F9FAFB; border-radius: 10px;">
                <div>
                    <div style="font-weight: bold;">${l.title}</div>
                    <div style="font-size: 13px; color: var(--gray);">${formatDate(l.datetime)}</div>
                </div>
                <div style="font-size: 13px;">Свободно: <b>${l.capacity - l.booked}</b></div>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

async function loadHistory() {
    const container = document.getElementById('history-list');
    try {
        const receipts = await familyRequest('/family/receipts');
        
        if (receipts.length === 0) {
            container.innerHTML = '<p style="color: var(--gray);">История пуста</p>';
            return;
        }

        container.innerHTML = receipts.map(r => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid var(--border);">
                <div>
                    <div style="font-weight: bold;">${r.description || 'Оплата'}</div>
                    <div style="font-size: 13px; color: var(--gray);">${formatDate(r.date)}</div>
                </div>
                <button class="btn btn-gray" style="padding: 6px 12px; font-size: 13px;" onclick="showToast('Скачивание чека (тестовый режим)')">Открыть чек</button>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}
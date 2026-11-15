
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDashboard();
});

// ==========================================
// ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК
// ==========================================

function switchTab(tabId) {
    document.querySelectorAll('section[id^="tab-"]').forEach(el => {
        el.style.display = 'none';
    });

    document.querySelectorAll('.nav-btn').forEach(el => {
        el.style.color = 'var(--gray)';
        el.style.borderBottom = 'none';
    });

    const section = document.getElementById(`tab-${tabId}`);
    const activeBtn = document.querySelector(
        `.nav-btn[data-tab="${tabId}"]`
    );

    if (!section || !activeBtn) return;

    section.style.display = 'block';
    activeBtn.style.color = 'var(--dark)';
    activeBtn.style.borderBottom = '3px solid var(--yellow)';

    if (tabId === 'dashboard') loadDashboard();
    if (tabId === 'schedule') loadSchedule();
    if (tabId === 'attendance') loadAttendance();
    if (tabId === 'families') loadFamilies();
    if (tabId === 'finance') loadFinance();
}


// ==========================================
// ГЛАВНАЯ ПАНЕЛЬ
// ==========================================

async function loadDashboard() {
    try {
        const [lessons, families, subscriptions] = await Promise.all([
            masterRequest('/master/lessons'),
            masterRequest('/master/families'),
            masterRequest('/master/subscriptions')
        ]);

        const today = new Date();

        const todayLessons = lessons.filter(lesson => {
            const date = new Date(lesson.starts_at);

            return date.getFullYear() === today.getFullYear()
                && date.getMonth() === today.getMonth()
                && date.getDate() === today.getDate();
        });

        const childrenTotal = families.reduce((sum, family) => {
            return sum + (family.children?.length || 0);
        }, 0);

        const endingSubs = subscriptions.filter(sub => {
            if (!sub.is_active) return false;

            const remaining = sub.total_lessons - sub.used_lessons;

            const expiresSoon = sub.expires_at &&
                new Date(sub.expires_at) <=
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

            return remaining <= 2 || expiresSoon;
        });

        document.getElementById('stat-lessons').innerText =
            todayLessons.length;

        document.getElementById('stat-children').innerText =
            childrenTotal;

        document.getElementById('stat-ending').innerText =
            endingSubs.length;

    } catch (e) {
        showToast('Ошибка загрузки главной панели: ' + e.message, 'error');
    }
}


// ==========================================
// РАСПИСАНИЕ
// ==========================================

async function loadSchedule() {
    try {
        const lessons = await masterRequest('/master/lessons');
        const tbody = document.getElementById('schedule-list');

        if (!lessons || lessons.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4">Пока нет созданных занятий</td>
                </tr>
            `;
            return;
        }

        const lessonsWithChildren = await Promise.all(
            lessons.map(async lesson => {
                const children = await masterRequest(
                    `/master/lessons/${lesson.id}/bookings`
                );

                return {
                    ...lesson,
                    bookedChildren: children
                };
            })
        );

        tbody.innerHTML = lessonsWithChildren.map(lesson => {
            const childNames = lesson.bookedChildren
                .map(child => child.child_name)
                .join(', ');

            return `
                <tr>
                    <td>${formatDate(lesson.starts_at)}</td>
                    <td>
                        ${lesson.title}
                        <br>
                        <small>Стоимость: ${formatMoney(lesson.price)}</small>
                    </td>
                    <td>
                        <strong>
                            ${lesson.booked_count} / ${lesson.capacity}
                        </strong>
                        ${childNames
                    ? `<br><small>${childNames}</small>`
                    : '<br><small>Пока нет записей</small>'}
                    </td>
                    <td>${lesson.is_active ? 'Активно' : 'Неактивно'}</td>
                </tr>
            `;
        }).join('');

    } catch (e) {
        showToast(e.message, 'error');
    }
}


async function createLesson(e) {
    e.preventDefault();

    const data = {
        title: document.getElementById('lesson-title').value.trim(),
        starts_at: document.getElementById('lesson-date').value,
        duration_minutes: 60,
        capacity: parseInt(
            document.getElementById('lesson-capacity').value,
            10
        ),
        price: parseFloat(
            document.getElementById('lesson-price').value
        )
    };

    try {
        await masterRequest('/master/lessons', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        closeModal('modal-create-lesson');
        document.querySelector('#modal-create-lesson form').reset();

        showToast('Занятие создано');

        loadSchedule();
        loadDashboard();

    } catch (e) {
        showToast(e.message, 'error');
    }
}


// ==========================================
// ПОСЕЩАЕМОСТЬ
// ==========================================

async function loadAttendance() {
    try {
        const list = await masterRequest('/master/attendance');
        const tbody = document.getElementById('attendance-list');

        if (!list || list.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4">Пока нет записей на занятия</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = list.map(item => {
            let statusText = 'Не отмечено';
            let statusClass = 'badge-gray';

            if (item.status === 'attended') {
                statusText = 'Посетил';
                statusClass = 'badge-green';
            } else if (item.status === 'missed') {
                statusText = 'Пропустил';
                statusClass = 'badge-red';
            }

            return `
                <tr>
                    <td>${item.childName}</td>
                    <td>${item.lessonTitle}</td>
                    <td>
                        <span class="badge ${statusClass}">
                            ${statusText}
                        </span>
                    </td>
                    <td>
                        <button class="btn"
                            style="padding: 6px 10px; font-size: 12px;"
                            onclick="markAttendance(${item.id}, 'attended')">
                            Посетил
                        </button>

                        <button class="btn btn-gray"
                            style="padding: 6px 10px; font-size: 12px;"
                            onclick="markAttendance(${item.id}, 'missed')">
                            Пропустил
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (e) {
        showToast(e.message, 'error');
    }
}


async function markAttendance(id, status) {
    try {
        await masterRequest(`/master/bookings/${id}/attendance`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });

        showToast('Отметка сохранена');

        loadAttendance();
        loadDashboard();

    } catch (e) {
        showToast(e.message, 'error');
    }
}


// ==========================================
// СЕМЬИ И ДЕТИ
// ==========================================

async function loadFamilies() {
    try {
        const families = await masterRequest('/master/families');
        const tbody = document.getElementById('families-list');

        if (!families || families.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3">Пока нет добавленных семей</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = families.map(family => `
            <tr>
                <td>${family.name}</td>
                <td>
                    ${family.children?.length
                ? family.children.join(', ')
                : 'Дети не добавлены'}
                </td>
                <td>
                    <button class="btn"
                        style="padding: 6px 12px; font-size: 13px;"
                        onclick="generateLink(${family.id})">
                        Выдать ссылку
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        showToast(e.message, 'error');
    }
}


async function createFamily(e) {
    e.preventDefault();

    const familyData = {
        name: document.getElementById('family-name').value.trim(),
        phone: null
    };

    const childData = {
        first_name: document.getElementById('child-name').value.trim(),
        last_name: null,
        birth_date: null
    };

    try {
        const family = await masterRequest('/master/families', {
            method: 'POST',
            body: JSON.stringify(familyData)
        });

        await masterRequest(`/master/families/${family.id}/children`, {
            method: 'POST',
            body: JSON.stringify(childData)
        });

        closeModal('modal-create-family');
        document.querySelector('#modal-create-family form').reset();

        showToast('Семья и ребёнок успешно добавлены');

        loadFamilies();
        loadDashboard();

    } catch (e) {
        showToast(e.message, 'error');
    }
}


// ==========================================
// ПЕРСОНАЛЬНЫЕ ССЫЛКИ
// ==========================================

async function generateLink(familyId) {
    try {
        const result = await masterRequest(
            `/master/families/${familyId}/link`,
            { method: 'POST' }
        );

        document.getElementById('family-link-input').value =
            `${window.location.origin}/family.html?token=${result.access_token}`;

        openModal('modal-show-link');

    } catch (e) {
        showToast(e.message, 'error');
    }
}


function copyLinkAndClose() {
    const input = document.getElementById('family-link-input');

    input.select();
    document.execCommand('copy');

    closeModal('modal-show-link');
    showToast('Ссылка скопирована');
}


// ==========================================
// АБОНЕМЕНТЫ И ПЛАТЕЖИ
// ==========================================

async function loadFinance() {
    try {
        const [payments, subscriptions, families] = await Promise.all([
            masterRequest('/master/payments'),
            masterRequest('/master/subscriptions'),
            masterRequest('/master/families')
        ]);

        renderPayments(payments);
        renderSubscriptions(subscriptions, families);
        fillSubscriptionFamilies(families);

    } catch (e) {
        showToast('Ошибка загрузки финансов: ' + e.message, 'error');
    }
}


function renderPayments(payments) {
    const tbody = document.getElementById('finance-list');

    if (!payments || payments.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">Пока нет платежей</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = payments.map(payment => `
        <tr>
            <td>Семья №${payment.family_id}</td>
            <td>
                ${payment.subscription_id
            ? `Абонемент №${payment.subscription_id}`
            : payment.booking_id
                ? `Разовое занятие №${payment.booking_id}`
                : '—'}
            </td>
            <td><b>${formatMoney(payment.amount)}</b></td>
            <td>${payment.status}</td>
            <td>${formatDate(payment.created_at)}</td>
        </tr>
    `).join('');
}


function renderSubscriptions(subscriptions, families) {
    const tbody = document.getElementById('subscriptions-list');

    if (!subscriptions || subscriptions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">Пока нет абонементов</td>
            </tr>
        `;
        return;
    }

    const familyNames = {};

    families.forEach(family => {
        familyNames[family.id] = family.name;
    });

    tbody.innerHTML = subscriptions.map(sub => {
        const remaining = sub.total_lessons - sub.used_lessons;

        return `
            <tr>
                <td>${sub.id}</td>
                <td>${familyNames[sub.family_id] || `Семья №${sub.family_id}`}</td>
                <td>${sub.title}</td>
                <td>${remaining} из ${sub.total_lessons}</td>
                <td>${formatMoney(sub.price)}</td>
                <td>${sub.expires_at ? formatDate(sub.expires_at) : 'Без срока'}</td>
            </tr>
        `;
    }).join('');
}


function fillSubscriptionFamilies(families) {
    const select = document.getElementById('subscription-family');

    if (!select) return;

    select.innerHTML = '<option value="">Выберите семью</option>';

    families.forEach(family => {
        const option = document.createElement('option');
        option.value = family.id;
        option.textContent = family.name;
        select.appendChild(option);
    });
}


async function createSubscription(e) {
    e.preventDefault();

    const expiresValue = document.getElementById(
        'subscription-expires'
    ).value;

    const data = {
        family_id: parseInt(
            document.getElementById('subscription-family').value,
            10
        ),
        title: document.getElementById('subscription-title').value.trim(),
        total_lessons: parseInt(
            document.getElementById('subscription-total').value,
            10
        ),
        price: parseFloat(
            document.getElementById('subscription-price').value
        ),
        expires_at: expiresValue || null
    };

    try {
        await masterRequest('/master/subscriptions', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        closeModal('modal-create-subscription');

        document.querySelector(
            '#modal-create-subscription form'
        ).reset();

        showToast('Абонемент успешно создан');

        loadFinance();
        loadDashboard();

    } catch (e) {
        showToast(e.message, 'error');
    }
}

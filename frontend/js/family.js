
let currentChildId = null;
let childrenData = [];
let currentFamilyId = null;
let paymentOptions = new Map();


// ==========================================
// ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА
// ==========================================

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
        localStorage.setItem('family_token', token);

        window.history.replaceState(
            {},
            document.title,
            window.location.pathname
        );
    }

    const familyToken = localStorage.getItem('family_token');
    const mockMode = typeof USE_MOCK !== 'undefined' && USE_MOCK;

    if (!familyToken && !mockMode) {
        alert('Доступ запрещён. Перейдите по персональной ссылке.');
        window.location.href = 'index.html';
        return;
    }

    await loadFamilyData();
});


// ==========================================
// ЗАГРУЗКА ДАННЫХ СЕМЬИ
// ==========================================

async function loadFamilyData() {
    try {
        const [family, children, balance] = await Promise.all([
            familyRequest('/family/me'),
            familyRequest('/family/children'),
            familyRequest('/family/subscriptions/balance')
        ]);

        currentFamilyId = family.id;

        document.getElementById('family-title').innerText =
            family.name || 'Личный кабинет';

        childrenData = Array.isArray(children) ? children : [];

        renderChildrenTabs();

        document.getElementById('balance-lessons').innerText =
            balance.remaining_lessons ?? 0;

        document.getElementById('balance-money').innerText =
            formatMoney(balance.money_balance ?? 0);

        await Promise.all([
            loadUpcomingLessons(),
            loadHistory()
        ]);

    } catch (err) {
        showToast(
            'Ошибка загрузки данных: ' + err.message,
            'error'
        );
    }
}


// ==========================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ==========================================

function getChildName(child) {
    return [
        child.first_name,
        child.last_name
    ].filter(Boolean).join(' ') || 'Ребёнок';
}


function escapeFamilyHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => {
        const entities = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        };

        return entities[char];
    });
}


function getBookingStatus(status) {
    const statuses = {
        booked: 'Записан',
        cancelled: 'Отменена'
    };

    return statuses[status] || status || 'Неизвестно';
}


// ==========================================
// ПЕРЕКЛЮЧЕНИЕ ДЕТЕЙ
// ==========================================

function renderChildrenTabs() {
    const container = document.getElementById('children-tabs');

    if (!container) return;

    if (childrenData.length === 0) {
        currentChildId = null;

        container.innerHTML =
            '<p style="color: var(--gray);">Дети пока не добавлены</p>';

        return;
    }

    if (!childrenData.some(child =>
        Number(child.id) === Number(currentChildId)
    )) {
        currentChildId = childrenData[0].id;
    }

    container.innerHTML = childrenData.map(child => {
        const isActive =
            Number(child.id) === Number(currentChildId);

        return `
            <button
                class="btn ${isActive ? '' : 'btn-gray'}"
                style="padding: 8px 16px; font-size: 14px;"
                onclick="selectChild(${Number(child.id)})"
            >
                ${escapeFamilyHtml(getChildName(child))}
            </button>
        `;
    }).join('');
}


async function selectChild(id) {
    currentChildId = Number(id);

    renderChildrenTabs();

    await loadUpcomingLessons();
}


// ==========================================
// ЛИЧНЫЕ ЗАПИСИ РЕБЁНКА
// ==========================================

async function loadUpcomingLessons() {
    const container = document.getElementById('upcoming-lessons');

    if (!container) return;

    if (!currentChildId) {
        container.innerHTML = `
            <p style="color: var(--gray);">
                Сначала добавьте ребёнка в семью
            </p>
        `;
        return;
    }

    container.innerHTML = `
        <p style="color: var(--gray);">
            Загружаем ваши записи...
        </p>
    `;

    try {
        const [bookings, lessons] = await Promise.all([
            familyRequest('/family/bookings'),
            familyRequest('/lessons')
        ]);

        const safeBookings = Array.isArray(bookings) ? bookings : [];
        const safeLessons = Array.isArray(lessons) ? lessons : [];

        const lessonsMap = new Map(
            safeLessons.map(lesson => [
                Number(lesson.id),
                lesson
            ])
        );

        const childBookings = safeBookings
            .filter(booking =>
                Number(booking.child_id) === Number(currentChildId)
            )
            .sort((a, b) => {
                const lessonA = lessonsMap.get(Number(a.lesson_id));
                const lessonB = lessonsMap.get(Number(b.lesson_id));

                const dateA = lessonA
                    ? new Date(lessonA.starts_at).getTime()
                    : 0;

                const dateB = lessonB
                    ? new Date(lessonB.starts_at).getTime()
                    : 0;

                return dateA - dateB;
            });

        if (childBookings.length === 0) {
            container.innerHTML = `
                <p style="color: var(--gray);">
                    У этого ребёнка пока нет записей
                </p>
            `;
            return;
        }

        container.innerHTML = childBookings.map(booking => {
            const lesson = lessonsMap.get(Number(booking.lesson_id));

            const title = lesson
                ? lesson.title
                : `Занятие №${booking.lesson_id}`;

            const date = lesson
                ? formatDate(lesson.starts_at)
                : 'Информация о занятии недоступна';

            const startsAt = lesson
                ? new Date(lesson.starts_at).getTime()
                : 0;

            const canCancel =
                booking.status === 'booked' &&
                startsAt > Date.now();

            const statusText = getBookingStatus(booking.status);

            const statusColor = booking.status === 'cancelled'
                ? '#DC2626'
                : '#16A34A';

            return `
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    background: #F9FAFB;
                    border-radius: 10px;
                    gap: 12px;
                    flex-wrap: wrap;
                ">
                    <div>
                        <div style="font-weight: bold;">
                            ${escapeFamilyHtml(title)}
                        </div>

                        <div style="
                            font-size: 13px;
                            color: var(--gray);
                            margin-top: 4px;
                        ">
                            ${escapeFamilyHtml(date)}
                        </div>

                        <div style="
                            font-size: 13px;
                            color: ${statusColor};
                            margin-top: 4px;
                        ">
                            Статус: ${escapeFamilyHtml(statusText)}
                        </div>
                    </div>

                    ${canCancel ? `
                        <button
                            class="btn btn-gray"
                            onclick="cancelBooking(${Number(booking.id)})"
                        >
                            Отменить запись
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Ошибка загрузки записей:', err);

        container.innerHTML = `
            <p style="color: red;">
                Не удалось загрузить ваши записи:
                ${escapeFamilyHtml(err.message)}
            </p>
        `;
    }
}


// ==========================================
// ОТМЕНА ЗАПИСИ
// ==========================================

async function cancelBooking(bookingId) {
    const confirmed = confirm(
        'Вы действительно хотите отменить запись на занятие?'
    );

    if (!confirmed) return;

    try {
        await familyRequest(
            `/family/bookings/${bookingId}`,
            {
                method: 'DELETE'
            }
        );

        showToast('Запись успешно отменена');

        await loadUpcomingLessons();

    } catch (err) {
        showToast(
            'Не удалось отменить запись: ' + err.message,
            'error'
        );
    }
}


// ==========================================
// ИСТОРИЯ ПЛАТЕЖЕЙ И ЧЕКИ
// ==========================================

async function loadHistory() {
    const container = document.getElementById('history-list');

    if (!container) return;

    try {
        const payments = await familyRequest('/family/payments');

        if (!payments || payments.length === 0) {
            container.innerHTML =
                '<p style="color: var(--gray);">История пуста</p>';
            return;
        }

        const history = await Promise.all(
            payments.map(async payment => {
                try {
                    const receipts = await familyRequest(
                        `/family/payments/${payment.id}/receipt`
                    );

                    return {
                        payment,
                        receipts: Array.isArray(receipts) ? receipts : []
                    };
                } catch (err) {
                    return {
                        payment,
                        receipts: []
                    };
                }
            })
        );

        container.innerHTML = history.map(({ payment, receipts }) => {
            let receiptButton = `
                <span style="color: var(--gray);">
                    Чек не прикреплён
                </span>
            `;

            if (receipts.length > 0) {
                const receipt = receipts[0];

                if (receipt.receipt_url) {
                    receiptButton = `
                        <a
                            class="btn btn-gray"
                            href="${escapeFamilyHtml(receipt.receipt_url)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Открыть чек
                        </a>
                    `;
                } else if (receipt.file_path) {
                    receiptButton = `
                        <button
                            class="btn btn-gray"
                            onclick="downloadReceipt(${Number(receipt.id)})"
                        >
                            Скачать чек
                        </button>
                    `;
                }
            }

            const paymentTitle = payment.subscription_id
                ? `Абонемент №${payment.subscription_id}`
                : payment.booking_id
                    ? `Разовое занятие №${payment.booking_id}`
                    : 'Платёж';

            return `
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    border-bottom: 1px solid var(--border);
                    gap: 12px;
                    flex-wrap: wrap;
                ">
                    <div>
                        <div style="font-weight: bold;">
                            ${paymentTitle} —
                            ${formatMoney(payment.amount)}
                        </div>

                        <div style="font-size: 13px; color: var(--gray);">
                            ${formatDate(payment.created_at)}
                        </div>

                        <div style="font-size: 12px; color: var(--gray);">
                            Статус: ${escapeFamilyHtml(payment.status)}
                        </div>
                    </div>

                    ${receiptButton}
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Ошибка загрузки истории:', err);

        container.innerHTML = `
            <p style="color: red;">
                Не удалось загрузить историю платежей
            </p>
        `;
    }
}


// ==========================================
// СКАЧИВАНИЕ ЧЕКА
// ==========================================

async function downloadReceipt(receiptId) {
    try {
        const token = localStorage.getItem('family_token');

        if (!token) {
            throw new Error('Нет персонального токена семьи');
        }

        const response = await fetch(
            `${API_URL}/family/receipts/${receiptId}/download`,
            {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            let message = 'Не удалось скачать чек';

            try {
                const data = await response.json();
                message = data.detail || message;
            } catch (_) {
                // Стандартное сообщение.
            }

            throw new Error(message);
        }

        const blob = await response.blob();
        const fileUrl = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = fileUrl;
        link.download = `receipt-${receiptId}`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(fileUrl), 1000);

    } catch (err) {
        showToast(err.message, 'error');
    }
}


// ==========================================
// ДЕМОНСТРАЦИОННАЯ ОПЛАТА
// ==========================================

async function openPaymentModal(type = 'subscription') {
    document.getElementById('payment-type').value = type;

    await loadPaymentOptions();

    openModal('modal-family-payment');
}


async function loadPaymentOptions() {
    const type = document.getElementById('payment-type').value;
    const select = document.getElementById('payment-item');
    const amountBlock = document.getElementById('payment-amount');

    select.innerHTML = '<option value="">Загрузка...</option>';
    amountBlock.innerText = '';
    paymentOptions.clear();

    try {
        const payments = await familyRequest('/family/payments');
        const safePayments = Array.isArray(payments) ? payments : [];

        if (type === 'subscription') {
            const subscriptions = await familyRequest('/family/subscriptions');

            const paidIds = new Set(
                safePayments
                    .filter(p =>
                        ['pending', 'succeeded'].includes(p.status)
                    )
                    .map(p => Number(p.subscription_id))
            );

            const available = subscriptions.filter(sub =>
                !sub.is_active &&
                !paidIds.has(Number(sub.id))
            );

            if (available.length === 0) {
                select.innerHTML =
                    '<option value="">Нет доступных абонементов</option>';
                return;
            }

            select.innerHTML =
                '<option value="">Выберите абонемент</option>';

            available.forEach(sub => {
                paymentOptions.set(Number(sub.id), {
                    id: Number(sub.id),
                    amount: Number(sub.price),
                    title: sub.title,
                    type: 'subscription'
                });

                const option = document.createElement('option');
                option.value = sub.id;
                option.textContent =
                    `${sub.title} — ${formatMoney(sub.price)}`;

                select.appendChild(option);
            });

        } else {
            if (!currentChildId) {
                select.innerHTML =
                    '<option value="">Сначала выберите ребёнка</option>';
                return;
            }

            const [bookings, lessons] = await Promise.all([
                familyRequest('/family/bookings'),
                familyRequest('/lessons')
            ]);

            const lessonsMap = new Map(
                lessons.map(lesson => [
                    Number(lesson.id),
                    lesson
                ])
            );

            const paidBookingIds = new Set(
                safePayments
                    .filter(p =>
                        ['pending', 'succeeded'].includes(p.status)
                    )
                    .map(p => Number(p.booking_id))
            );

            const available = bookings.filter(booking =>
                Number(booking.child_id) === Number(currentChildId) &&
                booking.status === 'booked' &&
                !paidBookingIds.has(Number(booking.id))
            );

            const child = childrenData.find(c =>
                Number(c.id) === Number(currentChildId)
            );

            const childName = getChildName(child || {});

            const futureBookings = available.filter(booking => {
                const lesson = lessonsMap.get(Number(booking.lesson_id));

                return lesson &&
                    new Date(lesson.starts_at).getTime() > Date.now();
            });

            if (futureBookings.length === 0) {
                select.innerHTML =
                    '<option value="">Нет неоплаченных записей</option>';
                return;
            }

            select.innerHTML =
                '<option value="">Выберите занятие</option>';

            futureBookings.forEach(booking => {
                const lesson = lessonsMap.get(Number(booking.lesson_id));
                const price = Number(lesson.price);

                paymentOptions.set(Number(booking.id), {
                    id: Number(booking.id),
                    amount: price,
                    title: lesson.title,
                    type: 'booking'
                });

                const option = document.createElement('option');
                option.value = booking.id;
                option.textContent =
                    `${childName}: ${lesson.title} — ${formatDate(lesson.starts_at)} — ${formatMoney(price)}`;

                select.appendChild(option);
            });
        }

    } catch (err) {
        console.error('Ошибка загрузки вариантов оплаты:', err);

        select.innerHTML =
            '<option value="">Не удалось загрузить варианты</option>';

        showToast(err.message, 'error');
    }
}


function updatePaymentAmount() {
    const id = Number(
        document.getElementById('payment-item').value
    );

    const item = paymentOptions.get(id);
    const amountBlock = document.getElementById('payment-amount');

    if (!item) {
        amountBlock.innerText = '';
        return;
    }

    amountBlock.innerText =
        `К оплате: ${formatMoney(item.amount)}`;
}


async function simulateFamilyPayment() {
    const type = document.getElementById('payment-type').value;

    const id = Number(
        document.getElementById('payment-item').value
    );

    const item = paymentOptions.get(id);

    if (!item) {
        showToast('Сначала выберите вариант оплаты', 'error');
        return;
    }

    if (!currentFamilyId) {
        showToast('Не удалось определить семью', 'error');
        return;
    }

    if (!Number.isFinite(item.amount) || item.amount < 0) {
        showToast('Некорректная стоимость', 'error');
        return;
    }

    const data = {
        family_id: currentFamilyId,
        subscription_id: type === 'subscription' ? id : null,
        booking_id: type === 'booking' ? id : null,
        amount: item.amount,
        payment_method: 'demo'
    };

    try {
        const payment = await familyRequest('/family/payments', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        await familyRequest(
            `/family/payments/${payment.id}/simulate`,
            {
                method: 'POST'
            }
        );

        closeModal('modal-family-payment');

        showToast('Демонстрационная оплата прошла успешно');

        await loadFamilyData();

    } catch (err) {
        showToast('Ошибка оплаты: ' + err.message, 'error');
    }
}


// ==========================================
// ОБНОВЛЕНИЕ СТОИМОСТИ ПРИ ВЫБОРЕ
// ==========================================

document.addEventListener('change', event => {
    if (event.target.id === 'payment-item') {
        updatePaymentAmount();
    }

    if (event.target.id === 'payment-type') {
        loadPaymentOptions();
    }
});

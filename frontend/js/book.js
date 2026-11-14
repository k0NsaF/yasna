let selectedLessonId = null;
let selectedChildId = null;
let childrenData = [];

document.addEventListener('DOMContentLoaded', () => {
    loadPublicSchedule();
});

async function loadPublicSchedule() {
    const container = document.getElementById('lessons-container');
    try {
        const lessons = await apiRequest('/lessons');
        
        if (!lessons || lessons.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--gray);">Пока нет доступных занятий</p>';
            return;
        }

        container.innerHTML = lessons.map(l => {
            const free = l.capacity - l.booked;
            const isFull = free <= 0;
            
            return `
            <div class="card" style="display: flex; justify-content: space-between; align-items: center; opacity: ${isFull ? 0.6 : 1};">
                <div>
                    <h3 style="margin: 0 0 5px 0;">${l.title}</h3>
                    <div style="font-size: 14px; color: var(--gray); margin-bottom: 5px;">📅 ${formatDate(l.datetime)}</div>
                    <div style="font-size: 13px;">Свободных мест: <b>${isFull ? 'Нет' : free}</b></div>
                </div>
                <button class="btn ${isFull ? 'btn-gray' : ''}" 
                        ${isFull ? 'disabled' : ''} 
                        onclick="startBooking(${l.id}, '${l.title}')">
                    ${isFull ? 'Мест нет' : 'Записаться'}
                </button>
            </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = `<p style="color: red; text-align: center;">Ошибка загрузки: ${e.message}</p>`;
    }
}

async function startBooking(lessonId, title) {
    selectedLessonId = lessonId;
    document.getElementById('book-lesson-info').innerText = `Занятие: ${title}`;
    
    // Если мы знаем, кто это (есть токен) - показываем детей
    const token = localStorage.getItem("family_token");
    
    if (!token && !USE_MOCK) {
        // Если это публичный юзер, просим персональную ссылку
        openModal('modal-public');
        return;
    }

    // Загружаем детей для выбора
    try {
        childrenData = await familyRequest('/family/children');
        const list = document.getElementById('book-children-list');
        
        list.innerHTML = childrenData.map(c => `
            <button class="btn ${selectedChildId === c.id ? '' : 'btn-gray'} btn-block" onclick="selectChildForBook(${c.id})">
                ${c.name}
            </button>
        `).join('');
        
        if (childrenData.length > 0) selectedChildId = childrenData[0].id;
        
        openModal('modal-book');
    } catch (e) { showToast(e.message, 'error'); }
}

function selectChildForBook(id) {
    selectedChildId = id;
    // Обновляем визуал кнопок
    const buttons = document.querySelectorAll('#book-children-list button');
    buttons.forEach((btn, index) => {
        if (childrenData[index].id === id) {
            btn.classList.remove('btn-gray');
        } else {
            btn.classList.add('btn-gray');
        }
    });
}

async function confirmBooking() {
    if (!selectedChildId) return showToast('Выберите ребенка', 'error');

    try {
        const res = await familyRequest('/family/bookings', {
            method: 'POST',
            body: JSON.stringify({ child_id: selectedChildId, lesson_id: selectedLessonId })
        });
        
        closeModal('modal-book');
        showToast('Ребенок успешно записан!');
        loadPublicSchedule(); // Обновляем список мест
        
    } catch (e) {
        showToast(e.message, 'error');
    }
}
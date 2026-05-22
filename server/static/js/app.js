const socket = io();
let currentUser = null;
let chats = [];
let currentChatId = null;
const LANG = {
    ru: { chats: 'Чаты', settings: 'Настройки', lenta: 'Lenta', logout: 'Выйти', premium: 'Премиум', theme: 'Тема', lang: 'Язык', account: 'Аккаунт', back: 'Назад', edit: 'Редактировать', delete: 'Удалить', online: 'онлайн', typing: 'печатает', justNow: 'только что', minutesAgo: 'мин. назад', hoursAgo: 'ч. назад', daysAgo: 'дн. назад', changeNick: 'Сменить никнейм', changeUsername: 'Сменить юзернейм' },
    en: { chats: 'Chats', settings: 'Settings', lenta: 'Lenta', logout: 'Logout', premium: 'Premium', theme: 'Theme', lang: 'Language', account: 'Account', back: 'Back', edit: 'Edit', delete: 'Delete', online: 'online', typing: 'typing', justNow: 'just now', minutesAgo: 'min ago', hoursAgo: 'h ago', daysAgo: 'd ago', changeNick: 'Change nickname', changeUsername: 'Change username' }
};
let currentLang = localStorage.getItem('gyert_lang') || 'ru';
function t(key) { return LANG[currentLang] && LANG[currentLang][key] || key; }

document.addEventListener('DOMContentLoaded', async () => {
    await loadUser();
    if (!currentUser) return;
    socket.emit('join', { username: currentUser.username });
    loadChats();
    loadContacts();
    bindNavigation();
    setupTheme();
    bindChatInput();
    socket.on('new_message', handleNewMessage);
    socket.on('notification', showToast);
    socket.on('user_status', updateUserStatus);
    applyLang();
});

function applyLang() {
    document.querySelectorAll('[data-lang]').forEach(el => {
        const k = el.dataset.lang;
        if (k) el.textContent = t(k);
    });
    localStorage.setItem('gyert_lang', currentLang);
    document.getElementById('langSelect').value = currentLang;
    document.getElementById('backToChats').textContent = '← ' + t('back');
}

async function loadUser() {
    try {
        const res = await fetch('/api/me');
        if (!res.ok) throw new Error('Not authenticated');
        currentUser = await res.json();
    } catch {
        window.location.href = '/login';
    }
}

async function loadChats() {
    const res = await fetch('/api/chats');
    chats = await res.json();
    chats.sort((a,b) => (b.last_message?.created_at||'').localeCompare(a.last_message?.created_at||''));
    renderChatList();
}

async function loadContacts() {
    const res = await fetch('/api/users/list');
    const users = await res.json();
    const container = document.getElementById('chatList');
    if (!container) return;
    const aliases = JSON.parse(localStorage.getItem('gyert_aliases') || '{}');
    container.innerHTML = users.filter(u => u.id !== currentUser.id).map(u => {
        const alias = aliases[u.id] || {};
        const displayName = alias.nickname || u.display_name;
        const avatar = alias.avatar || '';
        const online = u.is_online ? `<span style="color:#0f0">● ${t('online')}</span>` : (u.last_seen ? `был(а) ${formatLastSeen(u.last_seen)}` : '');
        return `<div class="chat-item" data-user-id="${u.id}">
            <div class="chat-avatar">${avatar ? `<img src="${avatar}" style="width:100%;height:100%;object-fit:cover;border-radius:50%">` : displayName[0]}</div>
            <div class="chat-info">
                <div class="chat-name">${displayName}</div>
                <div class="chat-last-message">@${u.username}</div>
                <div class="chat-status">${online}</div>
            </div>
        </div>`;
    }).join('');
    document.querySelectorAll('.chat-item').forEach(el => {
        el.addEventListener('click', () => startDM(el.dataset.userId));
        el.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContactMenu(el.dataset.userId, e.clientX, e.clientY);
        });
    });
}

function showContactMenu(userId, x, y) {
    const menu = document.createElement('div');
    menu.className = 'ctx-menu';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.innerHTML = `
        <div class="ctx-item" onclick="changeContactNick(${userId})">✏️ ${t('changeNick')}</div>
        <div class="ctx-item" onclick="changeContactAvatar(${userId})">🖼️ Аватар</div>
        <div class="ctx-item" onclick="this.parentElement.remove()">❌ Закрыть</div>
    `;
    document.body.appendChild(menu);
    document.addEventListener('click', () => menu.remove(), {once: true});
}

function changeContactNick(userId) {
    const newNick = prompt('Новый никнейм:');
    if (!newNick) return;
    const aliases = JSON.parse(localStorage.getItem('gyert_aliases') || '{}');
    if (!aliases[userId]) aliases[userId] = {};
    aliases[userId].nickname = newNick;
    localStorage.setItem('gyert_aliases', JSON.stringify(aliases));
    loadContacts();
}

function changeContactAvatar(userId) {
    const url = prompt('URL аватарки:');
    if (!url) return;
    const aliases = JSON.parse(localStorage.getItem('gyert_aliases') || '{}');
    if (!aliases[userId]) aliases[userId] = {};
    aliases[userId].avatar = url;
    localStorage.setItem('gyert_aliases', JSON.stringify(aliases));
    loadContacts();
}

function formatLastSeen(iso) {
    if (!iso) return '';
    const d = new Date(iso + 'Z');
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return t('justNow');
    if (diff < 3600) return Math.floor(diff/60) + ' ' + t('minutesAgo');
    if (diff < 86400) return Math.floor(diff/3600) + ' ' + t('hoursAgo');
    return Math.floor(diff/86400) + ' ' + t('daysAgo');
}

async function startDM(userId) {
    const res = await fetch('/api/chats/dm', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:userId})});
    const chat = await res.json();
    openChat(chat.id);
}

function openChat(chatId) {
    currentChatId = chatId;
    switchView('chat-view');
    fetch(`/api/chats/${chatId}/messages`).then(r => r.json()).then(data => {
        const container = document.getElementById('messages');
        container.innerHTML = data.messages.map(m => renderMessage(m)).join('');
        container.scrollTop = container.scrollHeight;
    });
    socket.emit('join_chat', { chat_id: chatId });
}

function sendMessage() {
    const input = document.getElementById('msgInput');
    if (!input.value.trim() || !currentChatId) return;
    socket.emit('send_message', { chat_id: currentChatId, content: input.value.trim(), type: 'text' });
    input.value = '';
}

function handleNewMessage(msg) {
    if (msg.chat_id === currentChatId) {
        const container = document.getElementById('messages');
        if (container) {
            container.insertAdjacentHTML('beforeend', renderMessage(msg));
            container.scrollTop = container.scrollHeight;
        }
    }
    loadChats();
}

function renderMessage(msg) {
    const isMine = msg.sender_id === currentUser.id;
    const time = new Date(msg.created_at + 'Z').toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    const actions = isMine ? `<span class="msg-actions">
        <button onclick="editMessage(${msg.id})">✏️</button>
        <button onclick="deleteMessage(${msg.id})">🗑️</button>
    </span>` : '';
    return `<div class="message ${isMine ? 'mine' : ''}">
        <div class="bubble">${msg.content}</div>
        <div class="time">${time} ${actions}</div>
    </div>`;
}

async function editMessage(msgId) {
    const newText = prompt('Новый текст:', '');
    if (!newText) return;
    socket.emit('edit_message', { message_id: msgId, content: newText, chat_id: currentChatId });
}

async function deleteMessage(msgId) {
    if (!confirm('Удалить сообщение?')) return;
    socket.emit('delete_message', { message_id: msgId, chat_id: currentChatId });
}

function showToast(data) {
    const toast = document.getElementById('toast');
    toast.textContent = data.text || data;
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}

function updateUserStatus(data) {
    // обновим индикатор в контактах
    const el = document.querySelector(`.chat-item[data-user-id="${data.user_id}"] .chat-status`);
    if (el) {
        el.innerHTML = data.is_online ? `<span style="color:#0f0">● ${t('online')}</span>` : (data.last_seen ? `был(а) ${formatLastSeen(data.last_seen)}` : '');
    }
}

function bindNavigation() {
    document.querySelectorAll('.nav-btn, .mobile-nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const page = e.currentTarget.dataset.page;
            if (page === 'chat') switchView('chat-list-view');
            else if (page === 'settings') switchView('settings-view');
            else if (page === 'lenta') switchView('lenta-view');
        });
    });
    document.getElementById('backToChats').addEventListener('click', () => switchView('chat-list-view'));
    document.getElementById('newChatBtn').addEventListener('click', () => document.getElementById('createModal').style.display = 'flex');
    document.getElementById('logoutBtn').addEventListener('click', async () => { await fetch('/api/logout', {method:'POST'}); window.location.href = '/login'; });
    document.getElementById('premiumBtn').addEventListener('click', () => alert('Премиум подписка будет доступна позже'));
    document.getElementById('switchAccountBtn').addEventListener('click', switchAccount);
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('changeNickBtn').addEventListener('click', changeMyNick);
    document.getElementById('changeUsernameBtn').addEventListener('click', changeMyUsername);
}

async function changeMyNick() {
    const now = Date.now();
    const last = parseInt(localStorage.getItem('gyert_last_nick_change') || '0');
    if (now - last < 86400000) { alert('Можно менять не чаще раза в сутки'); return; }
    const newNick = prompt('Новый никнейм:');
    if (!newNick) return;
    const res = await fetch('/api/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({display_name: newNick})});
    if (res.ok) {
        localStorage.setItem('gyert_last_nick_change', now);
        currentUser.display_name = newNick;
        alert('Никнейм изменён');
    }
}

async function changeMyUsername() {
    const now = Date.now();
    const last = parseInt(localStorage.getItem('gyert_last_username_change') || '0');
    if (now - last < 2592000000) { alert('Можно менять не чаще раза в 30 дней'); return; }
    const newUsername = prompt('Новый юзернейм (латиница, цифры, _):');
    if (!newUsername) return;
    const res = await fetch('/api/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username: newUsername})});
    if (res.ok) {
        localStorage.setItem('gyert_last_username_change', now);
        currentUser.username = newUsername;
        alert('Юзернейм изменён. Перезайдите в аккаунт для обновления.');
    }
}

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById(viewId);
    if (target) target.classList.add('active');
    document.querySelectorAll('.nav-btn, .mobile-nav-btn').forEach(b => b.classList.remove('active'));
    if (viewId === 'chat-list-view') {
        document.querySelectorAll('[data-page="chat"]').forEach(b => b.classList.add('active'));
    } else if (viewId === 'settings-view') {
        document.querySelectorAll('[data-page="settings"]').forEach(b => b.classList.add('active'));
    } else if (viewId === 'lenta-view') {
        document.querySelectorAll('[data-page="lenta"]').forEach(b => b.classList.add('active'));
        loadLenta();
    } else if (viewId === 'chat-view') {
        document.querySelectorAll('[data-page="chat"]').forEach(b => b.classList.add('active'));
    }
}

async function loadLenta() {
    const res = await fetch('/api/reels/all');
    const posts = await res.json();
    const container = document.getElementById('lentaContainer');
    container.innerHTML = posts.map(p => {
        const media = p.media_url ? (p.media_type === 'video' ? `<video src="${p.media_url}" controls loop muted autoplay></video>` : `<img src="${p.media_url}">`) : '';
        return `<div class="reel-card">${media}<div class="reel-caption">${p.content || ''}</div></div>`;
    }).join('');
}

function bindChatInput() {
    const input = document.getElementById('msgInput');
    if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });
}

function setupTheme() {
    const saved = localStorage.getItem('gyert_theme') || 'gyert';
    applyTheme(saved);
    document.getElementById('themeSelect').value = saved;
    document.getElementById('themeSelect').addEventListener('change', (e) => {
        const val = e.target.value;
        applyTheme(val);
        localStorage.setItem('gyert_theme', val);
    });
    document.getElementById('langSelect').addEventListener('change', (e) => {
        currentLang = e.target.value;
        applyLang();
    });
}

function applyTheme(theme) {
    document.body.className = `theme-${theme}`;
    const logo = document.getElementById('logo-img');
    if (logo) {
        logo.src = (theme === 'gyert') ? '/static/gyert_logo.png' : (theme === 'dark' ? '/static/logo-dark.png' : '/static/logo-light.png');
    }
}

function switchAccount() {
    const accounts = JSON.parse(localStorage.getItem('gyert_accounts') || '[]');
    if (accounts.length === 0) {
        alert('Нет сохранённых аккаунтов. Добавьте новый.');
        return;
    }
    const list = accounts.map((acc, i) => `${i+1}. ${acc.username}`).join('\n');
    const choice = prompt(`Выберите аккаунт:\n${list}\n0 - Новый аккаунт`);
    if (choice === '0') {
        localStorage.removeItem('gyert_auth');
        window.location.href = '/login';
    } else if (choice && !isNaN(choice) && choice > 0 && choice <= accounts.length) {
        const acc = accounts[choice-1];
        window.location.href = '/login';
    }
}

// Заглушки для создания
async function createChat() {
    document.getElementById('createModal').style.display = 'none';
    const query = prompt('Введите юзернейм или номер телефона:');
    if (!query) return;
    const res = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
    const users = await res.json();
    if (users.length === 0) { alert('Пользователь не найден'); return; }
    startDM(users[0].id);
}
async function createGroup() {
    document.getElementById('createModal').style.display = 'none';
    const name = prompt('Название группы:');
    if (!name) return;
    const members = prompt('ID участников через запятую (пусто - только вы):');
    const ids = members ? members.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id)) : [];
    const res = await fetch('/api/chats/group', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name, members: ids})});
    const chat = await res.json();
    loadChats();
    openChat(chat.id);
}
function createChannel() {
    document.getElementById('createModal').style.display = 'none';
    alert('Создание каналов будет доступно в ближайшее время');
}

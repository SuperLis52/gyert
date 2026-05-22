const socket = io();
let currentUser = null;
let chats = [];
let currentChatId = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadUser();
    if (!currentUser) return;
    socket.emit('join', { username: currentUser.username });
    loadChats();
    bindNavigation();   // <-- главное исправление
    setupTheme();
    bindChatInput();
    socket.on('new_message', handleNewMessage);
    socket.on('notification', showToast);
});

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

function renderChatList() {
    const container = document.getElementById('chatList');
    if (!container) return;
    container.innerHTML = chats.map(c => {
        const name = c.other_user ? c.other_user.display_name : (c.name || 'Chat');
        const avatarChar = (c.other_user ? c.other_user.display_name : (c.name || 'C'))[0].toUpperCase();
        const lastMsg = c.last_message ? c.last_message.content : '';
        const time = c.last_message ? new Date(c.last_message.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '';
        const unread = c.unread_count || 0;
        return `<div class="chat-item" data-id="${c.id}">
            <div class="chat-avatar">${avatarChar}</div>
            <div class="chat-info">
                <div class="chat-name">${name}</div>
                <div class="chat-last-message">${lastMsg}</div>
            </div>
            <div class="chat-time">${time}</div>
            ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ''}
        </div>`;
    }).join('');
    document.querySelectorAll('.chat-item').forEach(el => {
        el.addEventListener('click', () => openChat(el.dataset.id));
    });
}

function openChat(chatId) {
    currentChatId = chatId;
    switchView('chat-view');
    const chat = chats.find(c => c.id == chatId);
    if (chat) {
        document.getElementById('chatTitle').textContent = chat.other_user ? chat.other_user.display_name : (chat.name || 'Chat');
    }
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
    const time = new Date(msg.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    return `<div class="message ${isMine ? 'mine' : ''}">
        <div class="bubble">${msg.content}</div>
        <div class="time">${time}</div>
    </div>`;
}

function showToast(data) {
    const toast = document.getElementById('toast');
    toast.textContent = data.text || data;
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}

function bindNavigation() {
    // Боковая панель
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const page = e.currentTarget.dataset.page;
            if (page === 'chat') switchView('chat-list-view');
            else if (page === 'settings') switchView('settings-view');
            else if (page === 'lenta') switchView('lenta-view');
        });
    });

    // Мобильная навигация
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const page = e.currentTarget.dataset.page;
            if (page === 'chat') switchView('chat-list-view');
            else if (page === 'settings') switchView('settings-view');
            else if (page === 'lenta') switchView('lenta-view');
        });
    });

    // Кнопка "Назад" в чате
    const backBtn = document.getElementById('backToChats');
    if (backBtn) backBtn.addEventListener('click', () => switchView('chat-list-view'));

    // Кнопка нового чата (заглушка)
    const newChatBtn = document.getElementById('newChatBtn');
    if (newChatBtn) newChatBtn.addEventListener('click', () => alert('Новый чат скоро появится'));

    // Кнопка выхода
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', async () => {
        await fetch('/api/logout', {method:'POST'});
        window.location.href = '/login';
    });

    // Кнопка "Премиум"
    const premiumBtn = document.getElementById('premiumBtn');
    if (premiumBtn) premiumBtn.addEventListener('click', () => alert('Премиум подписка будет доступна позже'));

    // Кнопка отправки сообщения
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
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
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
}

function setupTheme() {
    const saved = localStorage.getItem('gyert_theme') || 'dark';
    applyTheme(saved);
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect) {
        themeSelect.value = saved;
        themeSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            applyTheme(val);
            localStorage.setItem('gyert_theme', val);
        });
    }

    const glassCheck = document.getElementById('glassCheckbox');
    if (glassCheck) {
        const glass = localStorage.getItem('gyert_glass') === 'true';
        glassCheck.checked = glass;
        document.body.classList.toggle('glass', glass);
        glassCheck.addEventListener('change', function() {
            localStorage.setItem('gyert_glass', this.checked);
        });
    }
}

function applyTheme(theme) {
    document.body.className = `theme-${theme}`;
    const logo = document.getElementById('logo-img');
    if (logo) {
        logo.src = `/static/logo-${theme === 'dark' ? 'dark' : 'light'}.png`;
    }
}
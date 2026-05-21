const socket = io();
let currentUser = null;
let chats = [];
let currentChatId = null;
let currentTheme = localStorage.getItem('theme') || 'light-blue';

document.addEventListener('DOMContentLoaded', async () => {
    await loadUser();
    if (!currentUser) return;
    socket.emit('join', { username: currentUser.username });
    loadChats();
    loadReels();
    setupTheme();
    setupNavigation();
    socket.on('new_message', handleNewMessage);
    socket.on('notification', showNotification);
    socket.on('user_status', updateUserStatus);
});

async function loadUser() {
    try {
        const res = await fetch('/api/me');
        if (!res.ok) throw new Error('Not authenticated');
        currentUser = await res.json();
        document.getElementById('user-name').textContent = currentUser.display_name;
        document.getElementById('user-avatar').src = currentUser.avatar_url || '/static/logo-default.png';
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
    const container = document.getElementById('chat-list');
    container.innerHTML = chats.map(c => {
        const name = c.name || 'Chat';
        const lastMsg = c.last_message ? c.last_message.content : '';
        const unread = c.unread_count || 0;
        return `<div class="chat-item ${c.id === currentChatId ? 'active' : ''}" data-id="${c.id}">
            <div class="chat-name">${name}</div>
            <div class="chat-preview">${lastMsg}</div>
            ${unread > 0 ? `<span class="badge">${unread}</span>` : ''}
        </div>`;
    }).join('');
    document.querySelectorAll('.chat-item').forEach(el => {
        el.addEventListener('click', () => openChat(el.dataset.id));
    });
}

function openChat(chatId) {
    currentChatId = chatId;
    socket.emit('join_chat', { chat_id: chatId });
    fetch(`/api/chats/${chatId}/messages`).then(r => r.json()).then(data => {
        const window = document.getElementById('chat-window');
        window.innerHTML = `
            <div class="messages" id="messages">${data.messages.map(m => renderMessage(m)).join('')}</div>
            <div class="input-area">
                <input type="text" id="msg-input" placeholder="Сообщение...">
                <button onclick="sendMessage()">Отправить</button>
            </div>
        `;
        document.getElementById('msg-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
    });
    renderChatList();
}

function sendMessage() {
    const input = document.getElementById('msg-input');
    if (!input.value.trim()) return;
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
    return `<div class="message ${isMine ? 'mine' : ''}">
        <div class="bubble">${msg.content}</div>
        <div class="time">${new Date(msg.created_at).toLocaleTimeString()}</div>
    </div>`;
}

function showNotification(notif) {
    const toast = document.getElementById('toast');
    toast.textContent = notif.text;
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}

function updateUserStatus(data) {
    // можно обновить индикатор в чате
}

async function loadReels() {
    const res = await fetch('/api/reels/all');
    const posts = await res.json();
    const container = document.getElementById('reels-container');
    container.innerHTML = posts.map(p => {
        const media = p.media_url ? (p.media_type === 'video' ? `<video src="${p.media_url}" controls></video>` : `<img src="${p.media_url}">`) : '';
        return `<div class="reel-card">
            ${media}
            <div class="reel-content">${p.content || ''}</div>
        </div>`;
    }).join('');
}

function setupTheme() {
    document.body.className = `theme-${currentTheme}`;
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === currentTheme);
        btn.addEventListener('click', () => {
            currentTheme = btn.dataset.theme;
            document.body.className = `theme-${currentTheme}`;
            localStorage.setItem('theme', currentTheme);
            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const logo = document.getElementById('logo-img');
            if (logo) {
                if (currentTheme === 'dark') logo.src = '/static/logo-dark.png';
                else if (currentTheme === 'light') logo.src = '/static/logo-light.png';
                else logo.src = '/static/logo-default.png';
            }
        });
    });
}

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            if (item.dataset.page === 'settings') {
                alert('Настройки будут позже');
            }
        });
    });
}

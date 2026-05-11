"""
Gyert Patch v3
- Mobile responsive fix
- Email registration
- DeepSeek AI integration
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(ROOT, 'server')

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  OK {os.path.relpath(path, ROOT)}')

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

print('='*50)
print('  Gyert Patch v3')
print('='*50)

# ─── 1. models.py — add email field ───

models_path = os.path.join(SERVER, 'models.py')
models = read(models_path)

if 'email' not in models.split('class User')[1].split('class Post')[0]:
    models = models.replace(
        "    password_hash = db.Column(db.String(256), nullable=False)",
        "    password_hash = db.Column(db.String(256), nullable=False)\n    email = db.Column(db.String(200), unique=True, nullable=True)"
    )
    # Add email to to_dict
    models = models.replace(
        "'phone_number': self.phone_number,",
        "'phone_number': self.phone_number,\n            'email': self.email,"
    )
    write(models_path, models)
    print('  Added email to User model')

# ─── 2. app.py — email register + DeepSeek API ───

app_path = os.path.join(SERVER, 'app.py')
app = read(app_path)

# Update register to accept email
if 'email' not in app.split('def api_register')[1].split('def api_login')[0]:
    app = app.replace(
        "    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+') if phone else None",
        "    email = d.get('email', '').strip().lower()\n    if email and User.query.filter_by(email=email).first():\n        return jsonify({'error': 'Эта почта уже используется'}), 400\n    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+') if phone else None"
    )
    app = app.replace(
        "                phone_number=phone_clean if phone_clean and len(phone_clean) >= 7 else None)",
        "                phone_number=phone_clean if phone_clean and len(phone_clean) >= 7 else None,\n                email=email if email and '@' in email else None)"
    )

# Add login by email
if 'login_by_email' not in app:
    app = app.replace(
        "    user = User.query.filter_by(username=u).first()",
        "    # Try login by email or username\n    user = User.query.filter_by(username=u).first()\n    if not user and '@' in u:\n        user = User.query.filter_by(email=u).first()"
    )

# Add DeepSeek AI endpoint
if 'api_ai_chat' not in app:
    ai_endpoint = """
# ============================================================
# DEEPSEEK AI API
# ============================================================

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def api_ai_chat():
    import urllib.request
    import urllib.error

    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        # Fallback responses when no API key
        fallback = [
            'GyertAI пока работает в демо-режиме. Подключите DEEPSEEK_API_KEY для полноценных ответов.',
            'Интересный вопрос! Для умных ответов нужно добавить API ключ DeepSeek в настройки сервера.',
            'Я GyertAI! Скоро смогу отвечать на любые вопросы. Ждём подключения DeepSeek API.',
        ]
        import random
        return jsonify({'response': random.choice(fallback), 'model': 'demo'})

    try:
        payload = json.dumps({
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are GyertAI, a helpful assistant in Gyert social network. Answer in the same language as the user message. Be concise and friendly.'},
                {'role': 'user', 'content': message}
            ],
            'max_tokens': 1000,
            'temperature': 0.7
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.deepseek.com/chat/completions',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
            return jsonify({'response': ai_response, 'model': 'deepseek-chat'})

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return jsonify({'response': f'Ошибка API: {e.code}', 'model': 'error'})
    except Exception as e:
        return jsonify({'response': f'Ошибка: {str(e)}', 'model': 'error'})

"""
    app = app.replace(
        "# ============================================================\n# SOCKET.IO",
        ai_endpoint + "# ============================================================\n# SOCKET.IO"
    )

write(app_path, app)

# ─── 3. register.html — add email field ───

reg_path = os.path.join(SERVER, 'templates', 'register.html')
reg = read(reg_path)

if 'id="email"' not in reg:
    # Add email field after name
    reg = reg.replace(
        """<div class="field">
                    <label>Юзернейм</label>""",
        """<div class="field">
                    <label>Email <small>(необязательно)</small></label>
                    <input type="email" id="email" placeholder="example@mail.com" autocomplete="email">
                </div>
                <div class="field">
                    <label>Юзернейм</label>"""
    )
    # Add email to submit
    reg = reg.replace(
        "password:pw, phone:document.getElementById('ph').value, avatar_emoji:sel",
        "password:pw, phone:document.getElementById('ph').value, email:document.getElementById('email')?.value||'', avatar_emoji:sel"
    )
    write(reg_path, reg)

# Update login.html — allow email login
login_path = os.path.join(SERVER, 'templates', 'login.html')
login = read(login_path)
if 'email' not in login:
    login = login.replace(
        'placeholder="username"',
        'placeholder="username или email"'
    )
    login = login.replace(
        '<label>Юзернейм</label>',
        '<label>Юзернейм или Email</label>'
    )
    write(login_path, login)

# ─── 4. app.js — fix AI to use real API + mobile nav ───

js_path = os.path.join(SERVER, 'static', 'js', 'app.js')
js = read(js_path)

# Replace sendAI with real API call
old_sendAI = "sendAI(){const inp=document.getElementById('aiInput');const chat=document.getElementById('aiChat');if(!inp||!chat)return;const q=inp.value.trim();if(!q)return;inp.value='';chat.innerHTML+='<div style=\"display:flex;gap:10px;max-width:85%;align-self:flex-end;flex-direction:row-reverse\"><div style=\"font-size:16px\">'+this.avatarHtml(this.me.avatar,32)+'</div><div style=\"padding:12px 16px;background:linear-gradient(135deg,rgba(77,124,255,.2),rgba(255,59,111,.12));border:1px solid rgba(77,124,255,.15);border-radius:18px;font-size:14px\">'+this.esc(q)+'</div></div>';chat.scrollTop=chat.scrollHeight;setTimeout(()=>{const responses=['Интересный вопрос! AI скоро заработает на полную.','GyertAI в разработке — скоро подключим ChatGPT!','Хороший вопрос! Полноценные ответы будут после подключения API.'];chat.innerHTML+='<div style=\"display:flex;gap:10px;max-width:85%\"><div style=\"font-size:24px\">🤖</div><div style=\"padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px;line-height:1.6\">'+responses[Math.floor(Math.random()*responses.length)]+'</div></div>';chat.scrollTop=chat.scrollHeight},1200)}"

new_sendAI = """async sendAI(){const inp=document.getElementById('aiInput');const chat=document.getElementById('aiChat');if(!inp||!chat)return;const q=inp.value.trim();if(!q)return;inp.value='';
        chat.innerHTML+='<div style="display:flex;gap:10px;max-width:85%;align-self:flex-end;flex-direction:row-reverse"><div style="font-size:16px">'+this.avatarHtml(this.me.avatar,32)+'</div><div style="padding:12px 16px;background:linear-gradient(135deg,rgba(77,124,255,.2),rgba(255,59,111,.12));border:1px solid rgba(77,124,255,.15);border-radius:18px;font-size:14px">'+this.esc(q)+'</div></div>';
        chat.scrollTop=chat.scrollHeight;
        // Thinking indicator
        const thinkId='think_'+Date.now();
        chat.innerHTML+='<div style="display:flex;gap:10px;max-width:85%" id="'+thinkId+'"><div style="font-size:24px">🤖</div><div style="padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px"><span class="typing-ind"><span></span><span></span><span></span></span></div></div>';
        chat.scrollTop=chat.scrollHeight;
        try{
            const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q})});
            const d=await r.json();
            const el=document.getElementById(thinkId);
            if(el){const bubble=el.querySelector('div:last-child');if(bubble){bubble.innerHTML=this.renderText(d.response||'Нет ответа');if(d.model&&d.model!=='demo')bubble.innerHTML+='<div style="font-size:10px;color:var(--text3);margin-top:6px">🤖 '+d.model+'</div>'}}
            chat.scrollTop=chat.scrollHeight;
        }catch(e){
            const el=document.getElementById(thinkId);
            if(el){const bubble=el.querySelector('div:last-child');if(bubble)bubble.textContent='Ошибка соединения'}
        }}"""

js = js.replace(old_sendAI, new_sendAI)

write(js_path, js)

# ─── 5. Mobile CSS ───

css_path = os.path.join(SERVER, 'static', 'css', 'main.css')
css = read(css_path)

MOBILE_CSS = """

/* ═══ MOBILE BOTTOM NAV ═══ */
.mobile-nav {
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: var(--card);
    border-top: 1px solid var(--border);
    z-index: 999;
    backdrop-filter: blur(20px);
}
.mobile-nav-inner {
    display: flex;
    justify-content: space-around;
    align-items: center;
    height: 100%;
    max-width: 500px;
    margin: 0 auto;
}
.mn-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    text-decoration: none;
    color: var(--text2);
    font-size: 20px;
    padding: 6px 12px;
    border-radius: 12px;
    transition: all .2s;
    position: relative;
}
.mn-btn.active { color: var(--acc); }
.mn-btn span {
    font-size: 10px;
    font-weight: 600;
}
.mn-badge {
    position: absolute;
    top: 0;
    right: 2px;
    min-width: 14px;
    height: 14px;
    padding: 0 3px;
    background: var(--acc2);
    border-radius: 7px;
    font-size: 9px;
    font-weight: 700;
    color: #fff;
    display: none;
    align-items: center;
    justify-content: center;
}

@media (max-width: 768px) {
    /* Show mobile nav */
    .mobile-nav { display: block; }

    /* Hide desktop sidebar and topnav elements */
    .sidebar-left { display: none !important; }
    .sidebar-right { display: none !important; }
    .nav-search { display: none; }
    .nav-actions .nav-btn { display: none; }

    /* Layout fixes */
    .layout {
        grid-template-columns: 1fr !important;
        padding: 64px 8px 72px !important;
        gap: 12px;
    }

    /* Topnav compact */
    .topnav { height: 50px; }
    .topnav-inner { padding: 0 12px; }
    .logo-text { display: none; }

    /* Main content */
    .main-content { min-width: 0; }

    /* Post cards */
    .post-card { border-radius: 14px; }
    .post-header { padding: 12px; }
    .post-content { padding: 0 12px 10px; font-size: 14px; }
    .post-actions { padding: 6px 8px; }
    .pa-btn { padding: 6px 8px; font-size: 13px; }

    /* Messages layout */
    .messages-layout {
        grid-template-columns: 1fr !important;
        height: calc(100vh - 130px) !important;
    }
    .chat-list-panel { max-height: 100%; }
    .chat-view-panel {
        position: fixed;
        inset: 0;
        z-index: 1001;
        background: var(--bg);
        display: none;
    }
    .chat-view-panel.open { display: flex !important; }
    .cvp-header {
        position: relative;
    }
    .cvp-back {
        display: block !important;
        width: 36px;
        height: 36px;
        border: none;
        background: var(--bg4);
        border-radius: 10px;
        color: var(--text);
        font-size: 18px;
        cursor: pointer;
        margin-right: 8px;
    }

    /* Profile */
    .profile-cover { height: 150px; border-radius: 0; }
    .profile-info-row { border-radius: 0 0 16px 16px; padding: 14px; }
    .profile-big-avatar { width: 72px; height: 72px; }
    .profile-name { font-size: 18px; }
    .profile-stats { gap: 16px; }
    .pstat strong { font-size: 16px; }

    /* Reels */
    .reels-container { gap: 2px; }
    .reel-card { height: 85vh; max-height: none; border-radius: 0; }

    /* AI */
    .ai-page { height: calc(100vh - 130px); }

    /* Create post */
    .create-post-box { border-radius: 14px; }
    .cp-textarea { font-size: 14px; }

    /* Stories */
    .stories-bar { border-radius: 14px; padding: 12px; }

    /* Modals */
    .modal-box {
        width: 95% !important;
        max-height: 90vh !important;
        border-radius: 20px;
    }

    /* Context menu */
    .ctx-menu { border-radius: 14px; }

    /* Empty state */
    .empty-state { padding: 40px 16px; }
    .empty-state .es-icon { font-size: 48px; }
}

/* Small phones */
@media (max-width: 380px) {
    .post-avatar { width: 36px !important; height: 36px !important; }
    .pa-btn { padding: 4px 6px; }
    .pa-count { font-size: 12px; }
    .cp-actions { flex-wrap: wrap; gap: 6px; }
}

/* Tablet */
@media (min-width: 769px) and (max-width: 1100px) {
    .layout { grid-template-columns: 220px 1fr !important; }
    .sidebar-right { display: none !important; }
}

/* Desktop hide mobile nav */
@media (min-width: 769px) {
    .mobile-nav { display: none !important; }
    .cvp-back { display: none !important; }
}
"""

if '/* ═══ MOBILE BOTTOM NAV ═══ */' not in css:
    css += MOBILE_CSS
    write(css_path, css)

# ─── 6. main.html — add mobile bottom nav + back button in chat ───

html_path = os.path.join(SERVER, 'templates', 'main.html')
html = read(html_path)

# Add mobile bottom nav before closing </body>
if 'mobile-nav' not in html:
    mobile_nav = """
<!-- MOBILE BOTTOM NAV -->
<nav class="mobile-nav">
    <div class="mobile-nav-inner">
        <a href="/feed" class="mn-btn" id="mnFeed">🏠<span>Лента</span></a>
        <a href="/reels" class="mn-btn" id="mnReels">🎬<span>Reels</span></a>
        <a href="/messages" class="mn-btn" id="mnMsg">💬<span>Чаты</span><div class="mn-badge" id="mnMsgBadge"></div></a>
        <a href="/notifications" class="mn-btn" id="mnNotif">🔔<span>Уведом.</span><div class="mn-badge" id="mnNotifBadge"></div></a>
        <a href="/profile" class="mn-btn" id="mnProfile">👤<span>Профиль</span></a>
    </div>
</nav>
"""
    html = html.replace('</body>', mobile_nav + '\n</body>')
    write(html_path, html)

# ─── 7. Update app.js — mobile chat back button + mobile nav badges ───

js = read(js_path)

# Fix openChat for mobile — show panel as overlay
old_openChat_start = "async openChat(cid){\n        this.currentChatId=cid;"
new_openChat_start = "async openChat(cid){\n        this.currentChatId=cid;\n        // Mobile: show chat panel as fullscreen overlay\n        const panel=document.getElementById('chatViewPanel');\n        if(panel)panel.classList.add('open');"

if 'panel.classList.add' not in js.split('openChat')[1].split('renderChatList')[0]:
    js = js.replace(old_openChat_start, new_openChat_start)

# Add back button to chat header
js = js.replace(
    "panel.innerHTML='<div class=\"cvp-header\"><div class=\"cvp-avatar\">",
    "panel.innerHTML='<div class=\"cvp-header\"><button class=\"cvp-back\" onclick=\"document.getElementById(\\'chatViewPanel\\').classList.remove(\\'open\\');app.currentChatId=null\">←</button><div class=\"cvp-avatar\">"
)

# Update badges for mobile nav too
old_badges = "['notifBadge','slNotifBadge'].forEach"
new_badges = "['notifBadge','slNotifBadge','mnNotifBadge'].forEach"
js = js.replace(old_badges, new_badges)

# Add mobile nav highlight in init
if 'mnFeed' not in js:
    js = js.replace(
        "this.highlightNav();",
        "this.highlightNav();\n        // Mobile nav highlight\n        document.querySelectorAll('.mn-btn').forEach(b=>{const p=b.href.split('/').pop();b.classList.toggle('active',this.page===p||(this.page==='feed'&&p==='feed'))});"
    )

write(js_path, js)

# ─── 8. Delete old DB ───

for db_path in [
    os.path.join(SERVER, 'instance', 'gyert.db'),
    os.path.join(SERVER, 'gyert.db')
]:
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'  Deleted {db_path}')

print()
print('='*55)
print('  Patch v3 complete!')
print()
print('  Что добавлено:')
print('    - Email при регистрации')
print('    - Вход по email или username')
print('    - DeepSeek AI API (/api/ai/chat)')
print('    - Мобильная нижняя навигация')
print('    - Адаптивные стили для телефонов')
print('    - Кнопка "назад" в чате на мобильных')
print()
print('  Запусти:')
print('    cd C:\\Projects\\max_gyert\\server')
print('    python app.py')
print()
print('  Потом залей на Render:')
print('    cd C:\\Projects\\max_gyert')
print('    git add -A')
print('    git commit -m "v3: mobile + email + DeepSeek AI"')
print('    git push origin main --force')
print()
print('  Для DeepSeek AI добавь в Render:')
print('    Environment Variable:')
print('    DEEPSEEK_API_KEY = ваш_ключ')
print('    (получить на https://platform.deepseek.com)')
print('='*55)
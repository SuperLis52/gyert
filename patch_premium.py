"""
Gyert Patch Premium
- Telegram bot registration
- Premium subscription system
- Premium UI page
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

print('='*55)
print('  Gyert Patch: Telegram + Premium')
print('='*55)

# ─── 1. telegram_bot.py ───

BOT = '''#!/usr/bin/env python3
"""
Gyert Telegram Bot
Регистрация и вход через Telegram
Запуск: python telegram_bot.py
"""

import os
import json
import time
import hashlib
import secrets
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'
GYERT_URL = os.environ.get('GYERT_URL', 'http://localhost:5000')

# Хранилище кодов (в продакшене используй Redis)
pending_codes = {}  # {telegram_id: {code, username, name, expires}}
offset = 0


def api(method, **params):
    url = f'{API_BASE}/{method}'
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f'API error: {e}')
        return {}


def send(chat_id, text, markup=None):
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if markup:
        params['reply_markup'] = json.dumps(markup)
    return api('sendMessage', **params)


def get_updates():
    global offset
    r = api('getUpdates', offset=offset, timeout=30, limit=10)
    updates = r.get('result', [])
    if updates:
        offset = updates[-1]['update_id'] + 1
    return updates


def generate_code():
    return secrets.token_hex(3).upper()


def process_message(msg):
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    user = msg.get('from', {})
    tg_name = user.get('first_name', '') + (' ' + user.get('last_name', '') if user.get('last_name') else '')
    tg_username = user.get('username', '')

    print(f'Message from {tg_name} (@{tg_username}): {text}')

    if text == '/start':
        send(chat_id,
            '👋 <b>Добро пожаловать в Gyert!</b>\\n\\n'
            'Я помогу вам зарегистрироваться или войти в социальную сеть Gyert.\\n\\n'
            '📱 Выберите действие:',
            markup={
                'keyboard': [
                    [{'text': '📝 Зарегистрироваться'}],
                    [{'text': '🔑 Войти в аккаунт'}],
                    [{'text': '❓ Помощь'}]
                ],
                'resize_keyboard': True
            }
        )

    elif text == '📝 Зарегистрироваться':
        code = generate_code()
        pending_codes[str(chat_id)] = {
            'code': code,
            'action': 'register',
            'tg_id': chat_id,
            'tg_name': tg_name,
            'tg_username': tg_username,
            'expires': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
        send(chat_id,
            f'✅ <b>Ваш код регистрации:</b>\\n\\n'
            f'<code>{code}</code>\\n\\n'
            f'🌐 Откройте <a href="{GYERT_URL}/register-tg">страницу регистрации</a> '
            f'и введите этот код.\\n\\n'
            f'⏱ Код действителен <b>10 минут</b>.'
        )

    elif text == '🔑 Войти в аккаунт':
        code = generate_code()
        pending_codes[str(chat_id)] = {
            'code': code,
            'action': 'login',
            'tg_id': chat_id,
            'tg_name': tg_name,
            'tg_username': tg_username,
            'expires': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
        send(chat_id,
            f'🔑 <b>Ваш код входа:</b>\\n\\n'
            f'<code>{code}</code>\\n\\n'
            f'🌐 Откройте <a href="{GYERT_URL}/login-tg">страницу входа</a> '
            f'и введите этот код.\\n\\n'
            f'⏱ Код действителен <b>10 минут</b>.'
        )

    elif text == '❓ Помощь':
        send(chat_id,
            '❓ <b>Помощь</b>\\n\\n'
            '📝 <b>Регистрация</b> — создать новый аккаунт\\n'
            '🔑 <b>Войти</b> — войти в существующий аккаунт\\n\\n'
            f'🌐 Сайт: {GYERT_URL}\\n'
            '📧 Поддержка: @gyert_support'
        )

    else:
        send(chat_id, '👆 Используйте кнопки меню')


def cleanup_expired():
    now = datetime.utcnow()
    expired = [k for k, v in pending_codes.items()
               if datetime.fromisoformat(v['expires']) < now]
    for k in expired:
        del pending_codes[k]


def run():
    if not BOT_TOKEN:
        print('ERROR: Set TELEGRAM_BOT_TOKEN environment variable')
        print('Get token from @BotFather in Telegram')
        return

    me = api('getMe')
    bot_name = me.get('result', {}).get('username', 'Unknown')
    print(f'Bot started: @{bot_name}')
    print(f'Gyert URL: {GYERT_URL}')
    print('Waiting for messages...')

    while True:
        try:
            updates = get_updates()
            for upd in updates:
                if 'message' in upd:
                    process_message(upd['message'])
            cleanup_expired()
            time.sleep(0.5)
        except KeyboardInterrupt:
            print('\\nBot stopped')
            break
        except Exception as e:
            print(f'Error: {e}')
            time.sleep(5)


# Export for Flask access
def get_pending_code(chat_id):
    return pending_codes.get(str(chat_id))

def remove_code(chat_id):
    pending_codes.pop(str(chat_id), None)

def notify_success(chat_id, action, username):
    if action == 'register':
        send(chat_id, f'🎉 <b>Регистрация успешна!</b>\\n\\nДобро пожаловать в Gyert, @{username}!\\n\\n🚀 <a href="{GYERT_URL}/feed">Открыть приложение</a>')
    else:
        send(chat_id, f'✅ <b>Вы вошли в аккаунт!</b>\\n\\n🚀 <a href="{GYERT_URL}/feed">Открыть приложение</a>')


if __name__ == '__main__':
    run()
'''

write(os.path.join(SERVER, 'telegram_bot.py'), BOT)


# ─── 2. models.py — add Premium + TelegramAuth ───

models_path = os.path.join(SERVER, 'models.py')
models = read(models_path)

PREMIUM_MODELS = '''

class PremiumPlan(db.Model):
    __tablename__ = 'premium_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price_month = db.Column(db.Float, nullable=False)
    price_year = db.Column(db.Float, nullable=False)
    features = db.Column(db.Text, default='[]')
    color = db.Column(db.String(20), default='#4d7cff')
    emoji = db.Column(db.String(10), default='⭐')


class UserPremium(db.Model):
    __tablename__ = 'user_premium'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('premium_plans.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    plan = db.relationship('PremiumPlan')

    def is_valid(self):
        return self.is_active and self.expires_at > datetime.utcnow()

    def to_dict(self):
        return {
            'plan': {'name': self.plan.name, 'emoji': self.plan.emoji, 'color': self.plan.color} if self.plan else None,
            'expires_at': self.expires_at.isoformat(),
            'is_valid': self.is_valid(),
            'days_left': max(0, (self.expires_at - datetime.utcnow()).days)
        }


class TelegramAuth(db.Model):
    __tablename__ = 'telegram_auth'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    telegram_id = db.Column(db.String(50), nullable=False)
    tg_name = db.Column(db.String(200), nullable=True)
    tg_username = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(20), default='register')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
'''

if 'class PremiumPlan' not in models:
    models += PREMIUM_MODELS
    write(models_path, models)

# Add premium to User.to_dict
if "'is_premium'" not in models:
    models = read(models_path)
    models = models.replace(
        "            'nft_badge': self.get_nft_badge(),",
        "            'nft_badge': self.get_nft_badge(),\n            'is_premium': self.get_premium() is not None,\n            'premium': self.get_premium(),"
    )
    # Add get_premium method
    models = models.replace(
        "    def get_nft_badge(self):",
        """    def get_premium(self):
        up = UserPremium.query.filter_by(user_id=self.id).first()
        if up and up.is_valid():
            return up.to_dict()
        return None

    def get_nft_badge(self):"""
    )
    write(models_path, models)


# ─── 3. app.py — Telegram + Premium endpoints ───

app_path = os.path.join(SERVER, 'app.py')
app = read(app_path)

# Fix imports
if 'UserPremium' not in app:
    app = app.replace(
        'from models import (db, User, Post, Comment, Story, StoryView, Notification,',
        'from models import (db, User, Post, Comment, Story, StoryView, Notification,\n                    UserPremium, PremiumPlan, TelegramAuth,'
    )

# Add Telegram + Premium routes
if 'register-tg' not in app:
    NEW_ROUTES = """
@app.route('/register-tg')
def register_tg_page():
    return render_template('register_tg.html')

@app.route('/login-tg')
def login_tg_page():
    return render_template('login_tg.html')

@app.route('/premium')
@login_required
def premium_page():
    return render_template('main.html', page='premium')
"""
    app = app.replace(
        "@app.route('/join/<code>')",
        NEW_ROUTES + "\n@app.route('/join/<code>')"
    )

# Add API endpoints
if 'api_tg_verify' not in app:
    TG_PREMIUM_API = """
# ============================================================
# TELEGRAM AUTH API
# ============================================================

@app.route('/api/tg/code', methods=['POST'])
def api_tg_code():
    \"\"\"Создать код от бота (вызывается ботом)\"\"\"
    data = request.get_json() or {}
    bot_secret = data.get('secret', '')
    if bot_secret != os.environ.get('BOT_SECRET', 'gyert_bot_secret'):
        return jsonify({'error': 'Unauthorized'}), 401

    import secrets as sec
    code = sec.token_hex(3).upper()
    ta = TelegramAuth(
        code=code,
        telegram_id=str(data.get('telegram_id', '')),
        tg_name=data.get('tg_name', ''),
        tg_username=data.get('tg_username', ''),
        action=data.get('action', 'register'),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(ta)
    db.session.commit()
    return jsonify({'code': code})


@app.route('/api/tg/register', methods=['POST'])
def api_tg_register():
    \"\"\"Регистрация через Telegram код\"\"\"
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    username = data.get('username', '').strip().lower().replace('@', '')
    display_name = data.get('display_name', '').strip()
    avatar_emoji = data.get('avatar_emoji', '😊')

    ta = TelegramAuth.query.filter_by(code=code, action='register', used=False).first()
    if not ta:
        return jsonify({'error': 'Неверный или истёкший код'}), 400
    if ta.expires_at < datetime.utcnow():
        return jsonify({'error': 'Код истёк. Получите новый в боте'}), 400

    if not username or len(username) < 3:
        return jsonify({'error': 'Юзернейм минимум 3 символа'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Юзернейм занят'}), 400
    if not display_name:
        display_name = ta.tg_name or username

    import secrets as sec
    random_password = sec.token_hex(16)

    user = User(
        username=username,
        display_name=display_name,
        password_hash=generate_password_hash(random_password, method='scrypt'),
        avatar='emoji:' + avatar_emoji
    )
    db.session.add(user)
    db.session.flush()

    ta.used = True
    ta.user_id = user.id
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({'success': True, 'user': user.to_dict(user.id)})


@app.route('/api/tg/login', methods=['POST'])
def api_tg_login():
    \"\"\"Вход через Telegram код\"\"\"
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    username = data.get('username', '').strip().lower().replace('@', '')

    ta = TelegramAuth.query.filter_by(code=code, action='login', used=False).first()
    if not ta:
        return jsonify({'error': 'Неверный или истёкший код'}), 400
    if ta.expires_at < datetime.utcnow():
        return jsonify({'error': 'Код истёк. Получите новый в боте'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    ta.used = True
    ta.user_id = user.id
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({'success': True, 'user': user.to_dict(user.id)})


@app.route('/api/tg/store_code', methods=['POST'])
def api_tg_store():
    \"\"\"Сохранить код напрямую из бота\"\"\"
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    tg_id = str(data.get('telegram_id', ''))
    action = data.get('action', 'register')

    if not TelegramAuth.query.filter_by(code=code, used=False).first():
        ta = TelegramAuth(
            code=code, telegram_id=tg_id,
            tg_name=data.get('tg_name', ''),
            tg_username=data.get('tg_username', ''),
            action=action,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(ta)
        db.session.commit()
    return jsonify({'success': True})


# ============================================================
# PREMIUM API
# ============================================================

@app.route('/api/premium/plans')
def api_premium_plans():
    plans = PremiumPlan.query.all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'emoji': p.emoji,
        'price_month': p.price_month, 'price_year': p.price_year,
        'features': json.loads(p.features), 'color': p.color
    } for p in plans])


@app.route('/api/premium/status')
@login_required
def api_premium_status():
    up = UserPremium.query.filter_by(user_id=current_user.id).first()
    if up and up.is_valid():
        return jsonify({'is_premium': True, 'premium': up.to_dict()})
    return jsonify({'is_premium': False})


@app.route('/api/premium/activate', methods=['POST'])
@login_required
def api_premium_activate():
    \"\"\"Активация промо-кода или тестового периода\"\"\"
    data = request.get_json() or {}
    promo = data.get('promo', '').strip().upper()
    plan_id = data.get('plan_id', 1)

    PROMO_CODES = {
        'GYERT30': 30,
        'PREMIUM7': 7,
        'VIPTEST': 14,
    }

    days = PROMO_CODES.get(promo, 0)
    if not days:
        return jsonify({'error': 'Неверный промо-код'}), 400

    plan = db.session.get(PremiumPlan, plan_id) or PremiumPlan.query.first()
    if not plan:
        return jsonify({'error': 'План не найден'}), 404

    existing = UserPremium.query.filter_by(user_id=current_user.id).first()
    if existing:
        existing.expires_at = datetime.utcnow() + timedelta(days=days)
        existing.is_active = True
        existing.plan_id = plan.id
    else:
        up = UserPremium(user_id=current_user.id, plan_id=plan.id,
                         expires_at=datetime.utcnow() + timedelta(days=days))
        db.session.add(up)
    db.session.commit()
    return jsonify({'success': True, 'days': days, 'message': f'Premium активирован на {days} дней!'})

"""
    app = app.replace(
        "# ============================================================\n# GEMINI AI API",
        TG_PREMIUM_API + "# ============================================================\n# GEMINI AI API"
    )

# Add premium plans creation
if 'create_premium_plans' not in app:
    PLANS_FUNC = """
def create_premium_plans():
    if PremiumPlan.query.count() > 0:
        return
    plans = [
        {
            'name': 'Gyert Plus',
            'emoji': '⭐',
            'price_month': 199,
            'price_year': 1499,
            'color': '#4d7cff',
            'features': ['ИИ ассистент без лимитов', 'Лента без рекламы', 'Эксклюзивные стикеры', 'Значок Plus у профиля', 'Приоритетная поддержка']
        },
        {
            'name': 'Gyert Pro',
            'emoji': '💎',
            'price_month': 399,
            'price_year': 2999,
            'color': '#8b5cf6',
            'features': ['Всё из Plus', 'Неограниченная музыка', 'Расширенная аналитика', 'Кастомный URL профиля', 'Ранний доступ к функциям', 'Верификация аккаунта', 'Хранилище медиа 50 ГБ']
        },
        {
            'name': 'Gyert Business',
            'emoji': '🚀',
            'price_month': 999,
            'price_year': 7999,
            'color': '#ff6b35',
            'features': ['Всё из Pro', 'Бизнес-аналитика', 'API доступ', 'Командный аккаунт (5 мест)', 'Рекламный кабинет', 'Выделенная поддержка 24/7', 'Хранилище медиа 200 ГБ']
        }
    ]
    for p in plans:
        db.session.add(PremiumPlan(
            name=p['name'], emoji=p['emoji'],
            price_month=p['price_month'], price_year=p['price_year'],
            color=p['color'], features=json.dumps(p['features'])
        ))
    db.session.commit()
    print('Premium plans created')

"""
    app = app.replace("def create_stickers():", PLANS_FUNC + "def create_stickers():")
    app = app.replace("        create_stickers()", "        create_stickers()\n    create_premium_plans()")

write(app_path, app)


# ─── 4. register_tg.html ───

REG_TG = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gyert — Регистрация через Telegram</title>
    <link rel="stylesheet" href="/static/css/auth.css">
    <style>
        .tg-steps { display:flex; flex-direction:column; gap:16px; margin:20px 0; }
        .step { display:flex; align-items:flex-start; gap:14px; padding:14px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:14px; }
        .step-num { width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg,#4d7cff,#ff3b6f); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px; flex-shrink:0; }
        .step-text { flex:1; }
        .step-text strong { display:block; font-size:14px; margin-bottom:3px; }
        .step-text span { font-size:13px; color:#8888aa; }
        .tg-btn { display:flex; align-items:center; justify-content:center; gap:10px; padding:14px; background:#2AABEE; border:none; border-radius:12px; color:#fff; font-size:16px; font-weight:700; cursor:pointer; text-decoration:none; transition:all .3s; }
        .tg-btn:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(42,171,238,.4); }
        .code-section { display:none; }
        .code-section.show { display:block; }
        .emoji-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:6px; max-height:120px; overflow-y:auto; margin:8px 0; }
        .ep { aspect-ratio:1; font-size:22px; background:rgba(255,255,255,.04); border:2px solid rgba(255,255,255,.08); border-radius:10px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all .15s; }
        .ep:hover { border-color:#4d7cff; }
        .ep.sel { border-color:#4d7cff; background:rgba(77,124,255,.2); }
        .ava-preview { width:64px; height:64px; border-radius:50%; background:rgba(77,124,255,.15); border:3px solid #4d7cff; display:flex; align-items:center; justify-content:center; font-size:32px; margin:0 auto 8px; }
    </style>
</head>
<body>
    <div class="auth-bg"><div class="blob b1"></div><div class="blob b2"></div></div>
    <div class="auth-wrap">
        <div class="auth-card" style="max-width:460px">
            <div class="auth-logo">
                <div class="logo-circle">G</div>
                <h1>Gyert</h1>
                <p>Регистрация через Telegram</p>
            </div>

            <!-- Step 1: Open bot -->
            <div id="step1">
                <div class="tg-steps">
                    <div class="step">
                        <div class="step-num">1</div>
                        <div class="step-text">
                            <strong>Откройте Telegram бота</strong>
                            <span>Нажмите кнопку ниже и напишите боту /start</span>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">2</div>
                        <div class="step-text">
                            <strong>Нажмите "Зарегистрироваться"</strong>
                            <span>Бот пришлёт вам 6-значный код</span>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">3</div>
                        <div class="step-text">
                            <strong>Введите код здесь</strong>
                            <span>Заполните данные и создайте аккаунт</span>
                        </div>
                    </div>
                </div>

                <a href="https://t.me/GyertBot" target="_blank" class="tg-btn">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.012 9.483c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.875.738z"/></svg>
                    Открыть @GyertBot
                </a>

                <div style="text-align:center;margin-top:16px">
                    <button class="btn-auth" style="padding:10px 24px;font-size:14px" onclick="document.getElementById('step1').style.display='none';document.getElementById('step2').style.display='block'">
                        У меня есть код →
                    </button>
                </div>
            </div>

            <!-- Step 2: Enter code + data -->
            <div id="step2" style="display:none">
                <form id="regForm">
                    <div class="field">
                        <label>Код из Telegram</label>
                        <input type="text" id="code" placeholder="ABC123" maxlength="6" required style="text-transform:uppercase;letter-spacing:4px;font-size:20px;text-align:center">
                    </div>
                    <div class="field">
                        <label>Выберите аватар</label>
                        <div class="ava-preview" id="prev">😊</div>
                        <div class="emoji-grid" id="grid"></div>
                    </div>
                    <div class="field">
                        <label>Имя</label>
                        <input type="text" id="name" placeholder="Ваше имя" required>
                    </div>
                    <div class="field">
                        <label>Юзернейм</label>
                        <div class="field-wrap">
                            <span class="prefix">@</span>
                            <input type="text" id="username" placeholder="username" required pattern="[a-zA-Z0-9_]{3,}">
                        </div>
                    </div>
                    <button type="submit" class="btn-auth">Создать аккаунт</button>
                    <div class="auth-error" id="err"></div>
                </form>
                <div style="text-align:center;margin-top:12px">
                    <a href="#" onclick="document.getElementById('step1').style.display='block';document.getElementById('step2').style.display='none'" style="color:#8888aa;font-size:13px">← Назад</a>
                </div>
            </div>

            <div class="auth-footer">
                Уже есть аккаунт? <a href="/login">Войти</a> ·
                <a href="/register">Обычная регистрация</a>
            </div>
        </div>
    </div>
    <script>
        const E=['😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊','😇','🥰','😍','🤩','😘','😋','😛','🤪','🤓','😎','🥳','😤','🤗','🤔','🤫','🤭','😶','😏','😌','😴','🤯','🥺','😈','👻','💀','🤖','👽','🦊','🐱','🐶','🐻','🐼','🦁','🐯','🐸','🐵','🦋','🦄','🌸','🔥','⚡','🌈','💎','🚀'];
        let sel='😊';
        const g=document.getElementById('grid');
        E.forEach(e=>{const b=document.createElement('button');b.type='button';b.className='ep'+(e===sel?' sel':'');b.textContent=e;b.onclick=()=>{sel=e;document.getElementById('prev').textContent=e;g.querySelectorAll('.ep').forEach(x=>x.classList.remove('sel'));b.classList.add('sel')};g.appendChild(b)});

        document.getElementById('code').oninput=e=>e.target.value=e.target.value.toUpperCase();

        document.getElementById('regForm').onsubmit=async e=>{
            e.preventDefault();
            const err=document.getElementById('err');err.textContent='';
            const r=await fetch('/api/tg/register',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({code:document.getElementById('code').value,display_name:document.getElementById('name').value,username:document.getElementById('username').value,avatar_emoji:sel})});
            const d=await r.json();
            if(d.success)window.location.href='/feed';
            else err.textContent=d.error||'Ошибка';
        };
    </script>
</body>
</html>'''

write(os.path.join(SERVER, 'templates', 'register_tg.html'), REG_TG)


# ─── 5. login_tg.html ───

LOGIN_TG = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gyert — Вход через Telegram</title>
    <link rel="stylesheet" href="/static/css/auth.css">
    <style>
        .tg-btn{display:flex;align-items:center;justify-content:center;gap:10px;padding:14px;background:#2AABEE;border:none;border-radius:12px;color:#fff;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none;transition:all .3s}
        .tg-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(42,171,238,.4)}
    </style>
</head>
<body>
    <div class="auth-bg"><div class="blob b1"></div><div class="blob b2"></div></div>
    <div class="auth-wrap">
        <div class="auth-card">
            <div class="auth-logo">
                <div class="logo-circle">G</div>
                <h1>Gyert</h1>
                <p>Вход через Telegram</p>
            </div>

            <div id="step1">
                <p style="text-align:center;color:#8888aa;margin-bottom:20px">Откройте бота, нажмите "Войти в аккаунт" и введите полученный код</p>
                <a href="https://t.me/GyertBot" target="_blank" class="tg-btn">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.012 9.483c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.875.738z"/></svg>
                    Открыть @GyertBot
                </a>
                <div style="text-align:center;margin-top:16px">
                    <button class="btn-auth" style="padding:10px 24px;font-size:14px" onclick="document.getElementById('step1').style.display='none';document.getElementById('step2').style.display='block'">
                        У меня есть код →
                    </button>
                </div>
            </div>

            <div id="step2" style="display:none">
                <form id="loginForm">
                    <div class="field">
                        <label>Код из Telegram</label>
                        <input type="text" id="code" placeholder="ABC123" maxlength="6" required style="text-transform:uppercase;letter-spacing:4px;font-size:20px;text-align:center">
                    </div>
                    <div class="field">
                        <label>Ваш юзернейм</label>
                        <div class="field-wrap">
                            <span class="prefix">@</span>
                            <input type="text" id="username" placeholder="username" required>
                        </div>
                    </div>
                    <button type="submit" class="btn-auth">Войти</button>
                    <div class="auth-error" id="err"></div>
                </form>
            </div>

            <div class="auth-footer">
                <a href="/login">← Обычный вход</a> · <a href="/register-tg">Регистрация</a>
            </div>
        </div>
    </div>
    <script>
        document.getElementById('code').oninput=e=>e.target.value=e.target.value.toUpperCase();
        document.getElementById('loginForm').onsubmit=async e=>{
            e.preventDefault();
            const err=document.getElementById('err');err.textContent='';
            const r=await fetch('/api/tg/login',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({code:document.getElementById('code').value,username:document.getElementById('username').value})});
            const d=await r.json();
            if(d.success)window.location.href='/feed';
            else err.textContent=d.error||'Ошибка';
        };
    </script>
</body>
</html>'''

write(os.path.join(SERVER, 'templates', 'login_tg.html'), LOGIN_TG)


# ─── 6. Update login.html — add Telegram button ───

login_path = os.path.join(SERVER, 'templates', 'login.html')
login = read(login_path)

if 'register-tg' not in login:
    login = login.replace(
        '<div class="auth-footer">',
        '''<div style="margin:16px 0;text-align:center;position:relative">
                <span style="background:rgba(16,16,36,.92);padding:0 12px;color:#555;font-size:12px;position:relative;z-index:1">или</span>
                <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:rgba(255,255,255,.08)"></div>
            </div>
            <a href="/login-tg" style="display:flex;align-items:center;justify-content:center;gap:10px;padding:12px;background:#2AABEE;border-radius:12px;color:#fff;font-size:14px;font-weight:700;text-decoration:none;transition:all .3s;margin-bottom:16px">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.012 9.483c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.875.738z"/></svg>
                Войти через Telegram
            </a>
            <div class="auth-footer">'''
    )
    write(login_path, login)


# ─── 7. Premium page in app.js ───

js_path = os.path.join(SERVER, 'static', 'js', 'app.js')
js = read(js_path)

# Add premium to loadPage
if "page==='premium'" not in js:
    js = js.replace(
        "}else if(this.page==='music'){",
        """}else if(this.page==='premium'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML='<div id="premiumPage"></div>';await this.loadPremium();
        }else if(this.page==='music'){"""
    )

# Add loadPremium method
PREMIUM_JS = """
    async loadPremium(){
        const c=document.getElementById('premiumPage');if(!c)return;
        const [plansR, statusR]=await Promise.all([fetch('/api/premium/plans'),fetch('/api/premium/status')]);
        const plans=await plansR.json();const status=await statusR.json();

        let currentBadge='';
        if(status.is_premium){
            const p=status.premium;
            currentBadge='<div style="background:linear-gradient(135deg,rgba(77,124,255,.15),rgba(139,92,246,.1));border:1px solid rgba(77,124,255,.3);border-radius:16px;padding:16px;margin-bottom:20px;text-align:center"><div style="font-size:32px">'+p.plan.emoji+'</div><div style="font-weight:700;font-size:18px;margin:6px 0">'+p.plan.name+' активен</div><div style="color:var(--text2);font-size:13px">Осталось '+p.days_left+' дней</div></div>';
        }

        const plansHTML=plans.map(p=>'<div class="premium-card" style="border:2px solid '+p.color+';border-radius:20px;padding:24px;background:rgba(255,255,255,.02);position:relative;overflow:hidden"><div style="position:absolute;top:0;left:0;right:0;height:3px;background:'+p.color+'"></div><div style="font-size:36px;margin-bottom:8px">'+p.emoji+'</div><h3 style="font-size:20px;font-weight:800;margin-bottom:4px">'+p.name+'</h3><div style="font-size:28px;font-weight:800;color:'+p.color+';margin:12px 0">'+p.price_month+' ₽<span style="font-size:14px;font-weight:400;color:var(--text2)">/мес</span></div><div style="font-size:13px;color:var(--text2);margin-bottom:4px">или '+p.price_year+' ₽/год</div><ul style="list-style:none;padding:0;margin:16px 0;display:flex;flex-direction:column;gap:8px">'+p.features.map(f=>'<li style="display:flex;align-items:center;gap:8px;font-size:14px"><span style="color:'+p.color+'">✓</span>'+f+'</li>').join('')+'</ul><button class="btn-primary" style="width:100%;background:'+p.color+';background:linear-gradient(135deg,'+p.color+','+p.color+'aa)" onclick="app.buyPlan('+p.id+')">Выбрать план</button></div>').join('');

        c.innerHTML='<div class="premium-page"><div style="text-align:center;padding:24px 0"><div style="font-size:48px">💎</div><h2 style="font-size:28px;font-weight:800;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent">Gyert Premium</h2><p style="color:var(--text2)">Откройте все возможности социальной сети</p></div>'+currentBadge+'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:20px 0">'+plansHTML+'</div><div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;margin-top:16px"><h4 style="margin-bottom:12px">🎁 Промо-код</h4><div style="display:flex;gap:8px"><input type="text" id="promoInp" placeholder="Введите промо-код" style="flex:1;padding:10px 14px;background:var(--bg4);border:1px solid var(--border);border-radius:10px;color:var(--text);outline:none"><button class="btn-primary btn-sm" onclick="app.applyPromo()">Применить</button></div><div style="font-size:12px;color:var(--text3);margin-top:8px">Попробуйте: PREMIUM7 — 7 дней бесплатно</div></div></div>';
    }

    async buyPlan(planId){
        this.openModal('<div class="modal-header"><h2>💳 Оформление подписки</h2><button class="modal-close" onclick="app.closeModal()">✕</button></div><div class="modal-body" style="text-align:center"><div style="font-size:48px;margin:16px 0">🚧</div><h3>Платёжная система в разработке</h3><p style="color:var(--text2);margin-top:8px">Скоро здесь будет оплата через:<br>💳 Карту · 📱 СБП · ₿ Крипто</p><div style="margin-top:20px;padding:16px;background:var(--bg4);border-radius:12px;font-size:14px;color:var(--text2)">Пока используйте промо-код <strong>PREMIUM7</strong> для 7 дней бесплатно</div></div><div class="modal-footer"><button class="btn-secondary" onclick="app.closeModal()">Закрыть</button></div>');
    }

    async applyPromo(){
        const code=document.getElementById('promoInp')?.value.trim().toUpperCase();if(!code)return;
        const r=await fetch('/api/premium/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({promo:code,plan_id:1})});
        const d=await r.json();
        if(d.success){this.toast('✅ '+d.message);setTimeout(()=>this.loadPremium(),1000)}
        else this.toast('❌ '+(d.error||'Неверный код'));
    }

"""

if 'loadPremium' not in js:
    js = js.replace(
        "    async loadReels()",
        PREMIUM_JS + "\n    async loadReels()"
    )

# Add premium to sidebar nav
html_path = os.path.join(SERVER, 'templates', 'main.html')
html = read(html_path)

if 'data-page="premium"' not in html:
    html = html.replace(
        '<a href="/reels" class="sl-link" data-page="reels">🎬 <span>Reels</span></a>',
        '<a href="/premium" class="sl-link" data-page="premium">💎 <span>Premium</span></a>\n            <a href="/reels" class="sl-link" data-page="reels">🎬 <span>Reels</span></a>'
    )
    # Add to mobile nav
    html = html.replace(
        '<a href="/reels" class="mn-btn" id="mnReels">🎬<span>Reels</span></a>',
        '<a href="/premium" class="mn-btn" id="mnPremium">💎<span>Premium</span></a>\n        <a href="/reels" class="mn-btn" id="mnReels">🎬<span>Reels</span></a>'
    )
    write(html_path, html)

write(js_path, js)


# ─── 8. Premium CSS ───

css_path = os.path.join(SERVER, 'static', 'css', 'main.css')
css = read(css_path)

PREMIUM_CSS = """
/* ═══ PREMIUM ═══ */
.premium-page { max-width: 900px; margin: 0 auto; padding-bottom: 40px; }
.premium-card { transition: transform .2s, box-shadow .2s; }
.premium-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,.3); }
@media (max-width: 768px) {
    .premium-page { padding: 0 4px; }
    .premium-card { padding: 16px !important; }
}
"""

if '.premium-page' not in css:
    css += PREMIUM_CSS
    write(css_path, css)


# ─── 9. Delete DB ───

for db_path in [
    os.path.join(SERVER, 'instance', 'gyert.db'),
    os.path.join(SERVER, 'gyert.db')
]:
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'  Deleted {db_path}')


print()
print('='*55)
print('  Patch Premium complete!')
print()
print('  Что добавлено:')
print('    - Telegram бот регистрация/вход')
print('    - 3 тарифа Premium (Plus/Pro/Business)')
print('    - Промо-коды (PREMIUM7, GYERT30, VIPTEST)')
print('    - Страница /register-tg и /login-tg')
print('    - Кнопка Telegram на странице входа')
print('    - Раздел 💎 Premium в навигации')
print()
print('  Следующие шаги:')
print()
print('  1. Создай Telegram бота:')
print('     - Напиши @BotFather в Telegram')
print('     - /newbot → введи имя → скопируй токен')
print()
print('  2. Добавь в Render Environment:')
print('     TELEGRAM_BOT_TOKEN = твой_токен')
print('     GYERT_URL = https://gyert.onrender.com')
print('     BOT_SECRET = gyert_bot_secret')
print()
print('  3. Тест локально:')
print('     cd C:\\Projects\\max_gyert\\server')
print('     python app.py')
print()
print('  4. Пуш на Render:')
print('     cd C:\\Projects\\max_gyert')
print('     git add -A')
print('     git commit -m "Premium + Telegram auth"')
print('     git push origin main --force')
print('='*55)
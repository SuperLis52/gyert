import os, uuid, json, re, secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import (db, User, Post, Comment, Story, StoryView, Notification,
                    UserPremium, PremiumPlan, TelegramAuth,
                    Chat, ChatMember, Message, MessageRead, Reaction,
                    NftCode, UserNft, StickerPack, likes_table, followers_table)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gyert-social-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gyert.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars')
app.config['MEDIA_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'media')
app.config['POSTS_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'posts')
app.config['VOICE_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'voice')
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

ALLOWED = {'png','jpg','jpeg','gif','webp','mp4','webm','mp3','ogg','pdf','zip'}
online_users = {}
typing_users = {}

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))

def allowed(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED

def add_notification(user_id, from_user_id, ntype, text, link=None):
    if user_id == from_user_id:
        return
    n = Notification(user_id=user_id, from_user_id=from_user_id, type=ntype, text=text, link=link)
    db.session.add(n)
    db.session.commit()
    sid = online_users.get(user_id)
    if sid:
        socketio.emit('notification', n.to_dict(), room=sid)

def notify_chat_members(chat, exclude=None):
    for m in chat.members:
        if m.user_id != exclude:
            sid = online_users.get(m.user_id)
            if sid:
                socketio.emit('chat_created', {'chat_id': chat.id}, room=sid)

# ---------- DEMO & INIT ----------
def create_demo():
    if User.query.count() > 0:
        return
    demos = [
        ('alexey', 'Alexey', 'qaz12wsx'),
        ('polina', 'Polina', 'SDR56tgh'),
        ('elizaveta', 'Elizaveta', 'lisaeliza'),
        ('razrab', 'Elisey', 'qaz10okm'),
        ('razrab2', 'Nikita', 'nicN'),
    ]
    for u, d, p in demos:
        user = User(username=u, display_name=d,
                    password_hash=generate_password_hash(p, method='scrypt'))
        db.session.add(user)
    db.session.commit()

def create_nft_codes():
    if NftCode.query.count() > 0:
        return
    codes = [
        ('invest147thg','investor','💵','Investor NFT','$254.67'),
        ('dog567_0','dog','🐕','Dog NFT','$50.00'),
        ('crowcraw','crow','🐦','Crow NFT','$100.00'),
    ]
    for c in codes:
        db.session.add(NftCode(code=c[0],nft_type=c[1],nft_emoji=c[2],nft_name=c[3],nft_price=c[4]))
    db.session.commit()

def create_premium_plans():
    if PremiumPlan.query.count() > 0:
        return
    plans = [
        {'name': 'Gyert Plus', 'emoji': '⭐', 'price_month': 199, 'price_year': 1499, 'color': '#4d7cff',
         'features': ['ИИ ассистент', 'Лента без рекламы', 'Эксклюзивные стикеры', 'Значок Plus', 'Приоритетная поддержка']},
        {'name': 'Gyert Pro', 'emoji': '💎', 'price_month': 399, 'price_year': 2999, 'color': '#8b5cf6',
         'features': ['Всё из Plus', 'Неограниченная музыка', 'Расширенная аналитика', 'Кастомный URL', 'Ранний доступ', 'Верификация', 'Хранилище 50 ГБ']},
        {'name': 'Gyert Business', 'emoji': '🚀', 'price_month': 999, 'price_year': 7999, 'color': '#ff6b35',
         'features': ['Всё из Pro', 'Бизнес-аналитика', 'API доступ', 'Командный аккаунт (5 мест)', 'Рекламный кабинет', 'Поддержка 24/7', 'Хранилище 200 ГБ']}
    ]
    for p in plans:
        db.session.add(PremiumPlan(name=p['name'], emoji=p['emoji'], price_month=p['price_month'], price_year=p['price_year'], color=p['color'], features=json.dumps(p['features'])))
    db.session.commit()

def create_stickers():
    if StickerPack.query.count() > 0:
        return
    packs = [
        ('Смайлы', ['😀','😂','🥰','😎','🤔','😢','🤩','🥳','😤','🤗','😴','🤯','🥺','😈','👻']),
        ('Жесты', ['👍','👎','👋','🤝','✌️','🤞','👌','🤙','💪','👏','🙏','🫶','✋','🤟','👊']),
        ('Животные', ['🐱','🐶','🦊','🐻','🐼','🐨','🦁','🐯','🐸','🐵','🦋','🐢','🦄','🌸','🔥']),
    ]
    for name, stickers in packs:
        db.session.add(StickerPack(name=name, stickers=json.dumps(stickers)))
    db.session.commit()

# ---------- ROUTES ----------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/chat')
@login_required
def chat_page():
    return render_template('index.html')

@app.route('/profile')
@login_required
def my_profile_page():
    return render_template('index.html', page='profile')

@app.route('/profile/<username>')
@login_required
def profile_page(username):
    return render_template('index.html', page='profile', target_username=username)

@app.route('/reels')
@login_required
def reels_page():
    return render_template('index.html', page='reels')

@app.route('/login-tg')
def login_tg_page():
    return render_template('login_tg.html')

@app.route('/register-tg')
def register_tg_page():
    return render_template('register_tg.html')

# ---------- AUTH API ----------
@app.route('/api/register', methods=['POST'])
def api_register():
    d = request.get_json() or {}
    u = d.get('username','').strip().lower()
    dn = d.get('display_name','').strip()
    pw = d.get('password','')
    if not u or not dn or not pw:
        return jsonify({'error':'Fill all fields'}), 400
    if User.query.filter_by(username=u).first():
        return jsonify({'error':'Username taken'}), 400
    user = User(username=u, display_name=dn, password_hash=generate_password_hash(pw, method='scrypt'))
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    return jsonify({'success': True, 'user': user.to_dict(user.id)})

@app.route('/api/login', methods=['POST'])
def api_login():
    d = request.get_json() or {}
    u = d.get('username','').strip().lower()
    pw = d.get('password','')
    user = User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash, pw):
        return jsonify({'error':'Invalid credentials'}), 401
    login_user(user, remember=True)
    return jsonify({'success': True, 'user': user.to_dict(user.id)})

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    current_user.is_online = False
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    logout_user()
    return jsonify({'success': True})

@app.route('/api/me')
@login_required
def api_me():
    return jsonify(current_user.to_dict(current_user.id))

# Telegram login
try:
    from telegram_bot import get_pending_code, remove_code
except ImportError:
    def get_pending_code(*args): return None
    def remove_code(*args): pass

@app.route('/api/tg/register', methods=['POST'])
def api_tg_register():
    d = request.get_json() or {}
    code = d.get('code','').strip().upper()
    username = d.get('username','').strip().lower()
    display_name = d.get('display_name','').strip()
    avatar_emoji = d.get('avatar_emoji','smile')
    if not code or not username or not display_name:
        return jsonify({'error':'Заполните все поля'}), 400
    from telegram_bot import pending_codes
    found = None
    for cid, data in pending_codes.items():
        if data['code'] == code and data['action'] == 'register':
            found = data
            break
    if not found:
        return jsonify({'error':'Неверный или истёкший код'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error':'Юзернейм занят'}), 400
    user = User(username=username, display_name=display_name,
                password_hash=generate_password_hash('tg_'+secrets.token_hex(8), method='scrypt'),
                avatar='emoji:' + avatar_emoji)
    db.session.add(user)
    db.session.commit()
    remove_code(found.get('tg_id',''))
    login_user(user, remember=True)
    return jsonify({'success':True, 'user':user.to_dict(user.id)})

@app.route('/api/tg/login', methods=['POST'])
def api_tg_login():
    d = request.get_json() or {}
    code = d.get('code','').strip().upper()
    username = d.get('username','').strip().lower()
    if not code or not username:
        return jsonify({'error':'Введите код и юзернейм'}), 400
    from telegram_bot import pending_codes
    found = None
    for cid, data in pending_codes.items():
        if data['code'] == code and data['action'] == 'login':
            found = data
            break
    if not found:
        return jsonify({'error':'Неверный или истёкший код'}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error':'Пользователь не найден'}), 404
    remove_code(found.get('tg_id',''))
    login_user(user, remember=True)
    return jsonify({'success':True, 'user':user.to_dict(user.id)})

# ---------- CHAT API ----------
@app.route('/api/chats')
@login_required
def api_chats():
    memberships = ChatMember.query.filter_by(user_id=current_user.id).all()
    result = []
    for m in memberships:
        chat = db.session.get(Chat, m.chat_id)
        if chat:
            result.append(chat.to_dict(current_user.id))
    return jsonify(result)

@app.route('/api/chats/dm', methods=['POST'])
@login_required
def api_create_dm():
    other_id = request.get_json().get('user_id')
    other = db.session.get(User, other_id)
    if not other:
        return jsonify({'error':'User not found'}), 404
    for mc in ChatMember.query.filter_by(user_id=current_user.id).all():
        chat = db.session.get(Chat, mc.chat_id)
        if chat and not chat.is_group:
            if ChatMember.query.filter_by(chat_id=chat.id, user_id=other_id).first():
                return jsonify(chat.to_dict(current_user.id))
    chat = Chat(is_group=False, created_by=current_user.id)
    db.session.add(chat)
    db.session.flush()
    db.session.add(ChatMember(chat_id=chat.id, user_id=current_user.id))
    db.session.add(ChatMember(chat_id=chat.id, user_id=other_id))
    db.session.commit()
    return jsonify(chat.to_dict(current_user.id))

@app.route('/api/chats/<int:cid>/messages')
@login_required
def api_messages(cid):
    if not ChatMember.query.filter_by(chat_id=cid, user_id=current_user.id).first():
        return jsonify({'error':'Access denied'}), 403
    msgs = Message.query.filter_by(chat_id=cid).order_by(Message.created_at.desc()).limit(50).all()
    return jsonify({'messages': [m.to_dict() for m in reversed(msgs)]})

# ---------- SOCKET.IO ----------
@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        current_user.is_online = True
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        online_users[current_user.id] = request.sid
        for m in ChatMember.query.filter_by(user_id=current_user.id).all():
            join_room(f'chat_{m.chat_id}')
        emit('user_status', {'user_id': current_user.id, 'is_online': True}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        online_users.pop(current_user.id, None)
        emit('user_status', {'user_id': current_user.id, 'is_online': False}, broadcast=True)

@socketio.on('send_message')
def on_msg(data):
    if not current_user.is_authenticated: return
    cid = data.get('chat_id')
    content = data.get('content','').strip()
    if not cid or not content: return
    if not ChatMember.query.filter_by(chat_id=cid, user_id=current_user.id).first(): return
    msg = Message(chat_id=cid, sender_id=current_user.id, content=content, message_type='text')
    db.session.add(msg)
    db.session.commit()
    emit('new_message', msg.to_dict(), room=f'chat_{cid}')
    # Уведомление другим участникам
    chat = db.session.get(Chat, cid)
    if chat:
        for m in chat.members:
            if m.user_id != current_user.id:
                add_notification(m.user_id, current_user.id, 'message',
                    f'{current_user.display_name}: {content[:50]}', f'/chat?chat={cid}')

@socketio.on('join_chat')
def on_join_chat(data):
    join_room(f"chat_{data.get('chat_id')}")

# ---------- REELS API ----------
@app.route('/api/reels/all')
@login_required
def api_reels_all():
    posts = Post.query.filter(Post.media_url != None, Post.is_deleted == False).order_by(Post.created_at.desc()).limit(20).all()
    return jsonify([p.to_dict(current_user.id) for p in posts])

# ---------- INIT ----------
for folder in [app.config['UPLOAD_FOLDER'], app.config['MEDIA_FOLDER'], app.config['POSTS_FOLDER'], app.config['VOICE_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

with app.app_context():
    db.create_all()
    create_nft_codes()
    create_stickers()
    create_premium_plans()
    create_demo()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gyert.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars')
app.config['MEDIA_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'media')
app.config['POSTS_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'posts')
app.config['VOICE_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'voice')
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

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


def create_demo():
    if User.query.count() > 0:
        return
    from werkzeug.security import generate_password_hash
    demos = [
        ('alexey', 'Alexey', 'qaz12wsx', 'alexey@gyert.com', '+79608253884'),
        ('polina', 'Polina', 'SDR56tgh', 'polina@gyert.com', '+79379805880'),
        ('elizaveta', 'Elizaveta', 'lisaeliza', 'liza@gyert.com', '+79874475289'),
        ('razrab', 'Elisey', 'qaz10okm', 'elisey@gyert.com', '+79033093388'),
        ('razrab2', 'Nikita', 'nicN', 'nikita@gyert.com', '+79093442766'),
    ]
    for u, d, p, e, ph in demos:
        user = User(username=u, display_name=d,
                    password_hash=generate_password_hash(p, method='scrypt'),
                    email=e, phone_number=ph, avatar='emoji:' + ['😎','🥰','🤩','🦊','🐱'][demos.index((u,d,p,e,ph))])
        db.session.add(user)
    db.session.commit()
    print('Demo users created')
def create_nft_codes():
    if NftCode.query.count() > 0:
        return
    codes = [
        ('invest147thg','investor','💵','Investor NFT','$254.67'),
        ('invest675714el','investor','💵','Investor NFT','$254.67'),
        ('investotets14','investor','💵','Investor NFT','$254.67'),
        ('investrazrabnekit13','investor','💵','Investor NFT','$254.67'),
        ('investrazrabelis14','investor','💵','Investor NFT','$254.67'),
        ('investmaman654580','investor','💵','Investor NFT','$254.67'),
        ('dog567_0','dog','🐕','Dog NFT','$50.00'),
        ('dogIk0827','dog','🐕','Dog NFT','$50.00'),
        ('dog_dob_dod_dor17098','dog','🐕','Dog NFT','$50.00'),
        ('dojikzac009e6','dog','🐕','Dog NFT','$50.00'),
        ('dogneplati972546','dog','🐕','Dog NFT','$50.00'),
        ('dogyatester','dog','🐕','Dog NFT','$50.00'),
        ('dog_yarazrab','dog','🐕','Dog NFT','$50.00'),
        ('crowcraw','crow','🐦','Crow NFT','$100.00'),
        ('crowik','crow','🐦','Crow NFT','$100.00'),
        ('crowneberi','crow','🐦','Crow NFT','$100.00'),
        ('crowzaberi','crow','🐦','Crow NFT','$100.00'),
    ]
    for c in codes:
        db.session.add(NftCode(code=c[0],nft_type=c[1],nft_emoji=c[2],nft_name=c[3],nft_price=c[4]))
    db.session.commit()


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

def create_stickers():
    if StickerPack.query.count() > 0:
        return
    packs = [
        ('Смайлы', ['😀','😂','🥰','😎','🤔','😢','🤩','🥳','😤','🤗','😴','🤯','🥺','😈','👻']),
        ('Жесты', ['👍','👎','👋','🤝','✌️','🤞','👌','🤙','💪','👏','🙏','🫶','✋','🤟','👊']),
        ('Животные', ['🐱','🐶','🦊','🐻','🐼','🐨','🦁','🐯','🐸','🐵','🦋','🐢','🐙','🦄','🐧']),
    ]
    for name, stickers in packs:
        db.session.add(StickerPack(name=name, stickers=json.dumps(stickers)))
    db.session.commit()

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('feed_page'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('feed_page'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/feed')
@login_required
def feed_page():
    return render_template('main.html', page='feed')

@app.route('/messages')
@login_required
def messages_page():
    return render_template('main.html', page='messages')

@app.route('/notifications')
@login_required
def notifications_page():
    return render_template('main.html', page='notifications')

@app.route('/profile')
@login_required
def my_profile_page():
    return render_template('main.html', page='profile')

@app.route('/profile/<username>')
@login_required
def profile_page(username):
    return render_template('main.html', page='profile', target_username=username)

@app.route('/reels')
@login_required
def reels_page():
    return render_template('main.html', page='reels')

@app.route('/music')
@login_required
def music_page():
    return render_template('main.html', page='music')

@app.route('/ai')
@login_required
def ai_page():
    return render_template('main.html', page='ai')

@app.route('/search')
@login_required
def search_page():
    return render_template('main.html', page='search')

@app.route('/post/<int:post_id>')
@login_required
def post_page(post_id):
    return render_template('main.html', page='post', post_id=post_id)


@app.route('/verify-email')
@login_required
def verify_email_page():
    return render_template('verify_email.html')

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

@app.route('/join/<code>')
def join_group(code):
    if not current_user.is_authenticated:
        return redirect(url_for('login_page') + '?next=/join/' + code)
    chat = Chat.query.filter_by(invite_code=code).first()
    if not chat:
        return 'Ссылка недействительна', 404
    if not ChatMember.query.filter_by(chat_id=chat.id, user_id=current_user.id).first():
        db.session.add(ChatMember(chat_id=chat.id, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for('messages_page') + '?chat=' + str(chat.id))

@app.route('/avatars/<filename>')
def get_avatar(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/media/<filename>')
def get_media(filename):
    return send_from_directory(app.config['MEDIA_FOLDER'], filename)

@app.route('/static/posts/<filename>')
def get_post_media(filename):
    return send_from_directory(app.config['POSTS_FOLDER'], filename)

@app.route('/static/voice/<filename>')
def get_voice(filename):
    return send_from_directory(app.config['VOICE_FOLDER'], filename)

# ============================================================
# AUTH API
# ============================================================

@app.route('/api/register', methods=['POST'])
def api_register():
    d = request.get_json() or {}
    u = d.get('username','').strip().replace('@','').lower()
    dn = d.get('display_name','').strip()
    pw = d.get('password','')
    phone = d.get('phone','').strip()
    emoji = d.get('avatar_emoji','smile')
    email = d.get('email', '').strip().lower()

    if not u or not dn or not pw:
        return jsonify({'error':'Fill all fields'}), 400
    if len(u) < 3:
        return jsonify({'error':'Username min 3 chars'}), 400
    if len(pw) < 6:
        return jsonify({'error':'Password min 6 chars'}), 400
    if User.query.filter_by(username=u).first():
        return jsonify({'error':'Username taken'}), 400
    if email and User.query.filter_by(email=email).first():
        return jsonify({'error':'Email already used'}), 400

    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+') if phone else None

    user = User(
        username=u,
        display_name=dn,
        password_hash=generate_password_hash(pw, method='scrypt'),
        avatar='emoji:' + emoji,
        phone_number=phone_clean if phone_clean and len(phone_clean) >= 7 else None,
        email=email if email else None,
        email_verified=True
    )
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    return jsonify({'success': True, 'user': user.to_dict(user.id)})


@app.route('/api/login', methods=['POST'])
def api_login():
    d = request.get_json() or {}
    u = d.get('username','').strip().replace('@','').lower()
    pw = d.get('password','')
    if not u or not pw:
        return jsonify({'error':'Введите данные'}), 400
    # Try login by email or username
    user = User.query.filter_by(username=u).first()
    if not user and '@' in u:
        user = User.query.filter_by(email=u).first()
    if not user or not check_password_hash(user.password_hash, pw):
        return jsonify({'error':'Неверный логин или пароль'}), 401
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

# ============================================================
# USERS API
# ============================================================

@app.route('/api/users/<username>')
@login_required
def api_user_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error':'Не найден'}), 404
    return jsonify(user.to_dict(current_user.id))

@app.route('/api/users/search')
@login_required
def api_search_users():
    q = request.args.get('q','').strip()
    if len(q) < 2:
        return jsonify([])
    users = User.query.filter(
        (User.username.ilike(f'%{q}%') | User.display_name.ilike(f'%{q}%')),
        User.id != current_user.id
    ).limit(20).all()
    return jsonify([u.to_dict(current_user.id) for u in users])

@app.route('/api/users/<int:uid>/follow', methods=['POST'])
@login_required
def api_follow(uid):
    user = db.session.get(User, uid)
    if not user or uid == current_user.id:
        return jsonify({'error':'Error'}), 400
    if current_user.is_following(user):
        current_user.following.remove(user)
        db.session.commit()
        return jsonify({'following': False})
    else:
        current_user.following.append(user)
        db.session.commit()
        add_notification(uid, current_user.id, 'follow',
            f'{current_user.display_name} подписался на вас', f'/profile/{current_user.username}')
        return jsonify({'following': True})

@app.route('/api/users/<int:uid>/followers')
@login_required
def api_followers(uid):
    rows = db.session.query(followers_table).filter(followers_table.c.followed_id == uid).all()
    users = [db.session.get(User, r.follower_id) for r in rows]
    return jsonify([u.to_dict(current_user.id) for u in users if u])

@app.route('/api/users/<int:uid>/following')
@login_required
def api_following(uid):
    rows = db.session.query(followers_table).filter(followers_table.c.follower_id == uid).all()
    users = [db.session.get(User, r.followed_id) for r in rows]
    return jsonify([u.to_dict(current_user.id) for u in users if u])

@app.route('/api/users/recommended')
@login_required
def api_recommended():
    following_ids = [r.followed_id for r in db.session.query(followers_table).filter(followers_table.c.follower_id == current_user.id).all()]
    following_ids.append(current_user.id)
    users = User.query.filter(~User.id.in_(following_ids)).order_by(db.func.random()).limit(5).all()
    return jsonify([u.to_dict(current_user.id) for u in users])

@app.route('/api/settings', methods=['PUT'])
@login_required
def api_settings():
    d = request.get_json() or {}
    now = datetime.utcnow()
    errors = []
    if 'display_name' in d:
        n = d['display_name'].strip()
        if n and n != current_user.display_name:
            if current_user.last_displayname_change and (now - current_user.last_displayname_change).total_seconds() < 86400:
                errors.append('Имя: подождите 24ч')
            else:
                current_user.display_name = n
                current_user.last_displayname_change = now
    if 'username' in d:
        u = d['username'].strip().lower().replace('@','')
        if u and u != current_user.username:
            if len(u) < 3: errors.append('Юзернейм мин 3')
            elif User.query.filter_by(username=u).first(): errors.append('Юзернейм занят')
            elif current_user.last_username_change and (now - current_user.last_username_change).total_seconds() < 2592000:
                errors.append('Юзернейм: подождите 30 дней')
            else:
                current_user.username = u
                current_user.last_username_change = now
    for f in ['bio','location','website','theme','accent_color','language']:
        if f in d: setattr(current_user, f, d[f])
    if 'phone' in d:
        phone = ''.join(c for c in d['phone'] if c.isdigit() or c == '+')
        current_user.phone_number = phone if len(phone) >= 7 else None
    if 'is_private' in d:
        current_user.is_private = bool(d['is_private'])
    db.session.commit()
    r = {'success': len(errors) == 0, 'user': current_user.to_dict(current_user.id)}
    if errors: r['errors'] = errors
    return jsonify(r)

@app.route('/api/settings/phone', methods=['PUT'])
@login_required
def api_settings_phone():
    phone = (request.get_json() or {}).get('phone','').strip()
    clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    current_user.phone_number = clean if len(clean) >= 7 else None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/avatar', methods=['POST'])
@login_required
def api_avatar():
    f = request.files.get('avatar')
    if not f or not allowed(f.filename):
        return jsonify({'error':'Недопустимый файл'}), 400
    ext = f.filename.rsplit('.',1)[1].lower()
    fn = f'{current_user.username}_{uuid.uuid4().hex[:8]}.{ext}'
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
    current_user.avatar = fn
    db.session.commit()
    return jsonify({'success': True, 'avatar': fn})

@app.route('/api/cover', methods=['POST'])
@login_required
def api_cover():
    f = request.files.get('cover')
    if not f or not allowed(f.filename):
        return jsonify({'error':'Недопустимый файл'}), 400
    ext = f.filename.rsplit('.',1)[1].lower()
    fn = f'cover_{current_user.username}_{uuid.uuid4().hex[:8]}.{ext}'
    f.save(os.path.join(app.config['MEDIA_FOLDER'], fn))
    current_user.cover_image = f'/static/media/{fn}'
    db.session.commit()
    return jsonify({'success': True, 'cover': current_user.cover_image})

# ============================================================
# FEED & POSTS API
# ============================================================

@app.route('/api/feed')
@login_required
def api_feed():
    page = request.args.get('page', 1, type=int)
    following_ids = [r.followed_id for r in db.session.query(followers_table).filter(followers_table.c.follower_id == current_user.id).all()]
    following_ids.append(current_user.id)
    posts = Post.query.filter(
        Post.author_id.in_(following_ids),
        Post.is_deleted == False,
        Post.visibility == 'public'
    ).order_by(Post.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return jsonify({'posts': [p.to_dict(current_user.id) for p in posts.items], 'has_more': posts.has_next})

@app.route('/api/explore')
@login_required
def api_explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(is_deleted=False, visibility='public').order_by(Post.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return jsonify({'posts': [p.to_dict(current_user.id) for p in posts.items], 'has_more': posts.has_next})

@app.route('/api/posts', methods=['POST'])
@login_required
def api_create_post():
    d = request.get_json() or {}
    content = d.get('content','').strip()
    if not content and not d.get('media_url'):
        return jsonify({'error':'Пустой пост'}), 400
    post = Post(author_id=current_user.id, content=content,
                media_url=d.get('media_url'), media_type=d.get('media_type'),
                visibility=d.get('visibility','public'))
    db.session.add(post)
    db.session.commit()
    socketio.emit('new_post', post.to_dict(current_user.id), broadcast=True)
    return jsonify(post.to_dict(current_user.id))

@app.route('/api/posts/<int:pid>')
@login_required
def api_get_post(pid):
    post = db.session.get(Post, pid)
    if not post or post.is_deleted:
        return jsonify({'error':'Не найден'}), 404
    return jsonify(post.to_dict(current_user.id))

@app.route('/api/posts/<int:pid>', methods=['PUT'])
@login_required
def api_edit_post(pid):
    post = db.session.get(Post, pid)
    if not post or post.author_id != current_user.id:
        return jsonify({'error':'Нет прав'}), 403
    content = (request.get_json() or {}).get('content','').strip()
    if content:
        post.content = content
        post.edited_at = datetime.utcnow()
        db.session.commit()
    return jsonify(post.to_dict(current_user.id))

@app.route('/api/posts/<int:pid>', methods=['DELETE'])
@login_required
def api_delete_post(pid):
    post = db.session.get(Post, pid)
    if not post or post.author_id != current_user.id:
        return jsonify({'error':'Нет прав'}), 403
    post.is_deleted = True
    db.session.commit()
    socketio.emit('post_deleted', {'post_id': pid}, broadcast=True)
    return jsonify({'success': True})

@app.route('/api/posts/<int:pid>/like', methods=['POST'])
@login_required
def api_like(pid):
    post = db.session.get(Post, pid)
    if not post:
        return jsonify({'error':'Не найден'}), 404
    exists = db.session.query(likes_table).filter(
        likes_table.c.user_id == current_user.id, likes_table.c.post_id == pid).count() > 0
    if exists:
        db.session.execute(likes_table.delete().where(
            likes_table.c.user_id == current_user.id, likes_table.c.post_id == pid))
        liked = False
    else:
        db.session.execute(likes_table.insert().values(user_id=current_user.id, post_id=pid))
        liked = True
        add_notification(post.author_id, current_user.id, 'like',
            f'{current_user.display_name} лайкнул ваш пост', f'/post/{pid}')
    db.session.commit()
    count = db.session.query(likes_table).filter(likes_table.c.post_id == pid).count()
    socketio.emit('post_liked', {'post_id': pid, 'likes_count': count, 'user_id': current_user.id, 'liked': liked}, broadcast=True)
    return jsonify({'liked': liked, 'likes_count': count})

@app.route('/api/posts/<int:pid>/repost', methods=['POST'])
@login_required
def api_repost(pid):
    orig = db.session.get(Post, pid)
    if not orig:
        return jsonify({'error':'Не найден'}), 404
    text = (request.get_json() or {}).get('content','')
    post = Post(author_id=current_user.id, content=text, repost_of_id=pid, visibility='public')
    db.session.add(post)
    db.session.commit()
    add_notification(orig.author_id, current_user.id, 'repost',
        f'{current_user.display_name} поделился вашим постом', f'/post/{post.id}')
    return jsonify(post.to_dict(current_user.id))

@app.route('/api/posts/<int:pid>/comments')
@login_required
def api_comments(pid):
    comments = Comment.query.filter_by(post_id=pid, parent_id=None, is_deleted=False).order_by(Comment.created_at.asc()).all()
    return jsonify([c.to_dict() for c in comments])

@app.route('/api/posts/<int:pid>/comments', methods=['POST'])
@login_required
def api_add_comment(pid):
    post = db.session.get(Post, pid)
    if not post:
        return jsonify({'error':'Не найден'}), 404
    d = request.get_json() or {}
    content = d.get('content','').strip()
    if not content:
        return jsonify({'error':'Пустой комментарий'}), 400
    c = Comment(post_id=pid, author_id=current_user.id, content=content, parent_id=d.get('parent_id'))
    db.session.add(c)
    db.session.commit()
    add_notification(post.author_id, current_user.id, 'comment',
        f'{current_user.display_name} прокомментировал ваш пост', f'/post/{pid}')
    socketio.emit('new_comment', {'post_id': pid, 'comment': c.to_dict()}, broadcast=True)
    return jsonify(c.to_dict())

@app.route('/api/comments/<int:cid>', methods=['DELETE'])
@login_required
def api_delete_comment(cid):
    c = db.session.get(Comment, cid)
    if not c or c.author_id != current_user.id:
        return jsonify({'error':'Нет прав'}), 403
    c.is_deleted = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users/<username>/posts')
@login_required
def api_user_posts(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify([])
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(author_id=user.id, is_deleted=False).order_by(Post.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return jsonify({'posts': [p.to_dict(current_user.id) for p in posts.items], 'has_more': posts.has_next})

@app.route('/api/media', methods=['POST'])
@login_required
def api_upload_media():
    f = request.files.get('media')
    if not f or not allowed(f.filename):
        return jsonify({'error':'Недопустимый файл'}), 400
    ext = f.filename.rsplit('.',1)[1].lower()
    fn = f'post_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}'
    f.save(os.path.join(app.config['POSTS_FOLDER'], fn))
    mt = 'image' if ext in {'png','jpg','jpeg','gif','webp'} else 'video' if ext in {'mp4','webm'} else 'file'
    return jsonify({'success': True, 'url': f'/static/posts/{fn}', 'type': mt})


# ============================================================
# REELS API
# ============================================================

@app.route('/api/reels')
@login_required
def api_reels():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(
        Post.is_deleted == False,
        Post.visibility == 'public',
        Post.media_url != None
    ).order_by(db.func.random()).paginate(page=page, per_page=10, error_out=False)
    return jsonify({'posts': [p.to_dict(current_user.id) for p in posts.items], 'has_more': posts.has_next})

@app.route('/api/reels/all')
@login_required
def api_reels_all():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(
        Post.is_deleted == False,
        Post.visibility == 'public'
    ).order_by(Post.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return jsonify({'posts': [p.to_dict(current_user.id) for p in posts.items], 'has_more': posts.has_next})

# ============================================================
# STORIES API
# ============================================================

@app.route('/api/stories')
@login_required
def api_stories():
    from datetime import timezone
    now = datetime.utcnow()
    following_ids = [r.followed_id for r in db.session.query(followers_table).filter(followers_table.c.follower_id == current_user.id).all()]
    following_ids.append(current_user.id)
    stories = Story.query.filter(Story.author_id.in_(following_ids), Story.expires_at > now).order_by(Story.created_at.desc()).all()
    result = {}
    for s in stories:
        uid = s.author_id
        if uid not in result:
            result[uid] = {'user': s.author.to_dict(), 'stories': [], 'has_unseen': False}
        sd = s.to_dict()
        seen = StoryView.query.filter_by(story_id=s.id, user_id=current_user.id).first()
        sd['seen'] = bool(seen)
        if not seen: result[uid]['has_unseen'] = True
        result[uid]['stories'].append(sd)
    return jsonify(list(result.values()))

@app.route('/api/stories', methods=['POST'])
@login_required
def api_create_story():
    f = request.files.get('media')
    text = request.form.get('text','')
    bg = request.form.get('bg','#000000')
    if not f and not text:
        return jsonify({'error':'Нет контента'}), 400
    media_url = None
    media_type = 'text'
    if f and allowed(f.filename):
        ext = f.filename.rsplit('.',1)[1].lower()
        fn = f'story_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}'
        f.save(os.path.join(app.config['MEDIA_FOLDER'], fn))
        media_url = f'/static/media/{fn}'
        media_type = 'video' if ext in {'mp4','webm'} else 'image'
    expires = datetime.utcnow() + timedelta(hours=24)
    story = Story(author_id=current_user.id, media_url=media_url or '',
                  media_type=media_type, text_overlay=text, bg_color=bg, expires_at=expires)
    db.session.add(story)
    db.session.commit()
    return jsonify(story.to_dict())

@app.route('/api/stories/<int:sid>/view', methods=['POST'])
@login_required
def api_view_story(sid):
    if not StoryView.query.filter_by(story_id=sid, user_id=current_user.id).first():
        db.session.add(StoryView(story_id=sid, user_id=current_user.id))
        db.session.commit()
    return jsonify({'success': True})

# ============================================================
# NOTIFICATIONS API
# ============================================================

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([n.to_dict() for n in notifs])

@app.route('/api/notifications/read', methods=['POST'])
@login_required
def api_read_notifs():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/count')
@login_required
def api_notif_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

# ============================================================
# MESSAGES API
# ============================================================

@app.route('/api/chats')
@login_required
def api_chats():
    ms = ChatMember.query.filter_by(user_id=current_user.id).all()
    chats = []
    for m in ms:
        c = db.session.get(Chat, m.chat_id)
        if c:
            cd = c.to_dict(current_user.id)
            cd['typing_users'] = list(typing_users.get(c.id, {}).values())
            chats.append(cd)
    chats.sort(key=lambda c: c.get('last_message',{}).get('created_at','') if c.get('last_message') else '', reverse=True)
    return jsonify(chats)

@app.route('/api/chats/dm', methods=['POST'])
@login_required
def api_create_dm():
    oid = (request.get_json() or {}).get('user_id')
    other = db.session.get(User, oid)
    if not other:
        return jsonify({'error':'Не найден'}), 404
    for mc in ChatMember.query.filter_by(user_id=current_user.id).all():
        c = db.session.get(Chat, mc.chat_id)
        if c and not c.is_group:
            if ChatMember.query.filter_by(chat_id=c.id, user_id=oid).first():
                return jsonify(c.to_dict(current_user.id))
    chat = Chat(is_group=False, created_by=current_user.id)
    db.session.add(chat); db.session.flush()
    db.session.add(ChatMember(chat_id=chat.id, user_id=current_user.id))
    db.session.add(ChatMember(chat_id=chat.id, user_id=oid))
    db.session.commit()
    notify_chat_members(chat, exclude=current_user.id)
    return jsonify(chat.to_dict(current_user.id))

@app.route('/api/chats/group', methods=['POST'])
@login_required
def api_create_group():
    d = request.get_json() or {}
    name = d.get('name','').strip()
    if not name:
        return jsonify({'error':'Имя обязательно'}), 400
    chat = Chat(name=name, is_group=True, created_by=current_user.id, invite_code=secrets.token_urlsafe(12))
    db.session.add(chat); db.session.flush()
    db.session.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role='owner'))
    for mid in d.get('members',[]):
        if mid != current_user.id:
            db.session.add(ChatMember(chat_id=chat.id, user_id=mid, role='member'))
    db.session.commit()
    notify_chat_members(chat, exclude=current_user.id)
    return jsonify(chat.to_dict(current_user.id))

@app.route('/api/chats/<int:cid>/messages')
@login_required
def api_messages(cid):
    if not ChatMember.query.filter_by(chat_id=cid, user_id=current_user.id).first():
        return jsonify({'error':'Нет доступа'}), 403
    page = request.args.get('page',1,type=int)
    msgs = Message.query.filter_by(chat_id=cid).order_by(Message.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return jsonify({'messages':[m.to_dict() for m in reversed(msgs.items)],'has_more':msgs.has_next})

@app.route('/api/chats/<int:cid>/invite', methods=['POST'])
@login_required
def api_invite(cid):
    c = db.session.get(Chat, cid)
    if not c: return jsonify({'error':'Не найден'}), 404
    if not c.invite_code: c.invite_code = secrets.token_urlsafe(12); db.session.commit()
    return jsonify({'invite_url': f'/join/{c.invite_code}'})

@app.route('/api/voice', methods=['POST'])
@login_required
def api_upload_voice():
    f = request.files.get('voice')
    if not f: return jsonify({'error':'Нет файла'}), 400
    fn = f'voice_{current_user.id}_{uuid.uuid4().hex[:8]}.webm'
    f.save(os.path.join(app.config['VOICE_FOLDER'], fn))
    return jsonify({'success': True, 'url': f'/static/voice/{fn}'})

# ============================================================
# NFT API
# ============================================================

@app.route('/api/nft/activate', methods=['POST'])
@login_required
def api_nft_activate():
    code = (request.get_json() or {}).get('code','').strip()
    nft = NftCode.query.filter_by(code=code).first()
    if not nft: return jsonify({'error':'Неверный код'}), 404
    if nft.activated_by: return jsonify({'error':'Код уже активирован'}), 400
    UserNft.query.filter_by(user_id=current_user.id).update({'equipped': False})
    nft.activated_by = current_user.id; nft.activated_at = datetime.utcnow()
    un = UserNft(user_id=current_user.id, nft_code_id=nft.id, equipped=True)
    db.session.add(un); db.session.commit()
    return jsonify({'success': True, 'nft': nft.to_dict()})

@app.route('/api/nft/my')
@login_required
def api_my_nfts():
    return jsonify([n.to_dict() for n in UserNft.query.filter_by(user_id=current_user.id).all()])

# ============================================================
# STICKERS API
# ============================================================

@app.route('/api/stickers')
@login_required
def api_stickers():
    return jsonify([p.to_dict() for p in StickerPack.query.all()])


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

    api_key = os.environ.get('GEMINI_API_KEY', '')

    if not api_key:
        return jsonify({'response': 'API ключ не настроен. Добавьте GEMINI_API_KEY в переменные окружения.', 'model': 'demo'})

    try:
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + api_key

        payload = json.dumps({
            'contents': [{
                'parts': [{'text': 'You are GyertAI, a helpful assistant. Answer in the same language as the user. Be concise and friendly.\n\nUser: ' + message}]
            }],
            'generationConfig': {
                'maxOutputTokens': 1000,
                'temperature': 0.7
            }
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            candidates = result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    return jsonify({'response': parts[0].get('text', 'Нет ответа'), 'model': 'Gemini'})
            return jsonify({'response': 'Нет ответа от модели', 'model': 'error'})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        if e.code == 429:
            return jsonify({'response': 'Слишком много запросов. Подождите минуту.', 'model': 'error'})
        elif e.code == 403:
            return jsonify({'response': 'Неверный API ключ.', 'model': 'error'})
        return jsonify({'response': 'Ошибка API: ' + str(e.code), 'model': 'error'})
    except Exception as e:
        return jsonify({'response': 'Ошибка: ' + str(e), 'model': 'error'})

# ============================================================
# SOCKET.IO
# ============================================================

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        current_user.is_online = True; current_user.last_seen = datetime.utcnow(); db.session.commit()
        online_users[current_user.id] = request.sid
        for m in ChatMember.query.filter_by(user_id=current_user.id).all():
            join_room(f'chat_{m.chat_id}')
        join_room(f'user_{current_user.id}')
        emit('user_status',{'user_id':current_user.id,'is_online':True,'last_seen':datetime.utcnow().isoformat()},broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        current_user.is_online = False; current_user.last_seen = datetime.utcnow(); db.session.commit()
        online_users.pop(current_user.id, None)
        for cid in typing_users: typing_users[cid].pop(current_user.id, None)
        emit('user_status',{'user_id':current_user.id,'is_online':False,'last_seen':datetime.utcnow().isoformat()},broadcast=True)

@socketio.on('send_message')
def on_msg(data):
    if not current_user.is_authenticated: return
    cid = data.get('chat_id'); content = data.get('content','').strip()
    if not cid: return
    if not ChatMember.query.filter_by(chat_id=cid, user_id=current_user.id).first(): return
    mtype = data.get('type','text')
    if data.get('sticker'): content = data['sticker']; mtype = 'sticker'
    msg = Message(chat_id=cid, sender_id=current_user.id, content=content or '',
                  message_type=mtype, reply_to_id=data.get('reply_to_id'),
                  forwarded_from_name=data.get('forwarded_from_name'),
                  media_url=data.get('media_url'), media_type=data.get('media_type_hint'),
                  voice_url=data.get('voice_url'))
    db.session.add(msg); db.session.commit()
    emit('new_message', msg.to_dict(), room=f'chat_{cid}')
    chat = db.session.get(Chat, cid)
    if chat:
        for m in chat.members:
            if m.user_id != current_user.id:
                add_notification(m.user_id, current_user.id, 'message',
                    f'{current_user.display_name}: {content[:50]}', f'/messages?chat={cid}')

@socketio.on('edit_message')
def on_edit(data):
    if not current_user.is_authenticated: return
    msg = db.session.get(Message, data.get('message_id'))
    if not msg or msg.sender_id != current_user.id: return
    nc = data.get('content','').strip()
    if nc: msg.content = nc; msg.edited_at = datetime.utcnow(); db.session.commit()
    emit('message_edited',{'id':msg.id,'chat_id':msg.chat_id,'content':nc,'edited_at':msg.edited_at.isoformat()},room=f'chat_{msg.chat_id}')

@socketio.on('delete_message')
def on_del_msg(data):
    if not current_user.is_authenticated: return
    msg = db.session.get(Message, data.get('message_id'))
    if not msg or msg.sender_id != current_user.id: return
    msg.is_deleted = True; msg.content = ''; db.session.commit()
    emit('message_deleted',{'message_id':msg.id,'chat_id':msg.chat_id},room=f'chat_{msg.chat_id}')

@socketio.on('add_reaction')
def on_react(data):
    if not current_user.is_authenticated: return
    mid = data.get('message_id'); emoji = data.get('emoji','')
    if not mid or not emoji: return
    ex = Reaction.query.filter_by(message_id=mid, user_id=current_user.id, emoji=emoji).first()
    if ex: db.session.delete(ex)
    else: db.session.add(Reaction(message_id=mid, user_id=current_user.id, emoji=emoji))
    db.session.commit()
    msg = db.session.get(Message, mid)
    if msg: emit('reaction_updated',{'message_id':mid,'chat_id':msg.chat_id,'reactions':msg.to_dict()['reactions']},room=f'chat_{msg.chat_id}')

@socketio.on('mark_read')
def on_read(data):
    if not current_user.is_authenticated: return
    cid = data.get('chat_id')
    for mid in data.get('message_ids',[]):
        if not MessageRead.query.filter_by(message_id=mid, user_id=current_user.id).first():
            db.session.add(MessageRead(message_id=mid, user_id=current_user.id))
    db.session.commit()
    emit('messages_read',{'chat_id':cid,'user_id':current_user.id,'message_ids':data.get('message_ids',[]),'read_at':datetime.utcnow().isoformat()},room=f'chat_{cid}')

@socketio.on('typing')
def on_typing(data):
    if current_user.is_authenticated:
        cid = data.get('chat_id')
        if cid not in typing_users: typing_users[cid] = {}
        typing_users[cid][current_user.id] = current_user.display_name
        emit('user_typing',{'chat_id':cid,'user_id':current_user.id,'display_name':current_user.display_name},room=f'chat_{cid}',include_self=False)

@socketio.on('stop_typing')
def on_stop(data):
    if current_user.is_authenticated:
        cid = data.get('chat_id')
        if cid in typing_users: typing_users[cid].pop(current_user.id, None)
        emit('user_stop_typing',{'chat_id':cid,'user_id':current_user.id},room=f'chat_{cid}',include_self=False)

@socketio.on('join_chat')
def on_join(data):
    join_room(f"chat_{data.get('chat_id')}")

# ============================================================
# INIT
# ============================================================

if __name__ == '__main__':
    for folder in [app.config['UPLOAD_FOLDER'],app.config['MEDIA_FOLDER'],app.config['POSTS_FOLDER'],app.config['VOICE_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    dap = os.path.join(app.config['UPLOAD_FOLDER'],'default.png')
    if not os.path.exists(dap):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGBA',(200,200),(0,245,195,255))
            ImageDraw.Draw(img).ellipse([20,20,180,180],fill=(20,20,40,255))
            img.save(dap)
        except:
            import struct,zlib
            def mp(w,h,r,g,b):
                def c(t,d):
                    x=t+d; return struct.pack('>I',len(d))+x+struct.pack('>I',zlib.crc32(x)&0xffffffff)
                rw=b''
                for _ in range(h): rw+=b'\x00'+bytes([r,g,b])*w
                return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+c(b'IDAT',zlib.compress(rw))+c(b'IEND',b'')
            open(dap,'wb').write(mp(64,64,0,200,180))
    with app.app_context():
        db.create_all()
        create_nft_codes()
        create_stickers()
    create_premium_plans()
    print('\n'+'='*50+'\n  GYERT SOCIAL NETWORK\n  http://localhost:5000\n'+'='*50+'\n')
    port = int(os.environ.get('PORT',5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
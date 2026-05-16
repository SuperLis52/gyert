"""
Gyert Patch: Email verification + New Brand Identity
- Required email with verification code
- New logo (white bg, blue wifi waves)
- New brand colors (clean blue minimalist)
"""

import os, struct, zlib, math

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
print('  Gyert: Email Verification + New Brand')
print('='*55)

# ─── 1. Генерируем новую иконку (синие WiFi волны на белом) ───

def create_logo_png(size, filepath):
    """Создаём PNG с белым фоном и синими WiFi-волнами"""
    pixels = []
    radius = size / 2 - 2
    cx = cy = size / 2
    bg = (255, 255, 255, 255)
    blue = (37, 99, 235, 255)  # #2563EB
    
    for y in range(size):
        row = []
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Скругление углов
            if dist > radius:
                row.append((0, 0, 0, 0))
                continue
            
            # Белый фон по умолчанию
            color = bg
            
            # Углы координат относительно центра, повёрнутые
            # WiFi волны — три дуги в правом верхнем углу
            # Дуги направлены от центра к правому нижнему
            
            # Точка-источник внизу слева (для WiFi)
            sx = size * 0.18
            sy = size * 0.78
            d_from_source = math.sqrt((x - sx) ** 2 + (y - sy) ** 2)
            
            # Угол от источника
            angle = math.atan2(y - sy, x - sx)
            # Только сектор -90° до 0° (вправо и вверх)
            if -math.pi/2 - 0.2 < angle < 0.2:
                # Три дуги: маленькая, средняя, большая
                r1 = size * 0.18  # маленькая
                r2 = size * 0.40  # средняя
                r3 = size * 0.62  # большая
                thickness = size * 0.06
                
                if (abs(d_from_source - r1) < thickness or 
                    abs(d_from_source - r2) < thickness or 
                    abs(d_from_source - r3) < thickness):
                    color = blue
            
            # Точка (источник) внизу слева
            if d_from_source < size * 0.06:
                color = blue
            
            row.append(color)
        pixels.append(row)
    
    def chunk(ct, cd):
        c = ct + cd
        return struct.pack('>I', len(cd)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    
    raw = b''
    for row in pixels:
        raw += b'\x00'
        for r, g, b, a in row:
            raw += bytes([r, g, b, a])
    
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    
    with open(filepath, 'wb') as f:
        f.write(png)

static_dir = os.path.join(SERVER, 'static')
os.makedirs(static_dir, exist_ok=True)

create_logo_png(192, os.path.join(static_dir, 'icon-192.png'))
create_logo_png(512, os.path.join(static_dir, 'icon-512.png'))
create_logo_png(64, os.path.join(static_dir, 'favicon.png'))
print('  OK icons generated')

# ─── 2. manifest.json — новые цвета ───

manifest = '''{
    "name": "Gyert",
    "short_name": "Gyert",
    "description": "Социальная сеть Gyert",
    "start_url": "/feed",
    "display": "standalone",
    "orientation": "portrait",
    "theme_color": "#2563EB",
    "background_color": "#ffffff",
    "icons": [
        {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
    ],
    "categories": ["social", "communication"],
    "lang": "ru"
}'''

write(os.path.join(static_dir, 'manifest.json'), manifest)

# ─── 3. Обновляем модель User — email обязательный + verify ───

models_path = os.path.join(SERVER, 'models.py')
models = read(models_path)

if 'email_verified' not in models:
    models = models.replace(
        "    email = db.Column(db.String(200), unique=True, nullable=True)",
        "    email = db.Column(db.String(200), unique=True, nullable=True)\n    email_verified = db.Column(db.Boolean, default=False)\n    email_verify_code = db.Column(db.String(10), nullable=True)\n    email_verify_expires = db.Column(db.DateTime, nullable=True)"
    )
    models = models.replace(
        "'email': self.email,",
        "'email': self.email,\n            'email_verified': self.email_verified,"
    )
    write(models_path, models)

# ─── 4. app.py — verification endpoints ───

app_path = os.path.join(SERVER, 'app.py')
app = read(app_path)

# Update register — require email + send code
if 'email_verify_code' not in app:
    old_reg = """    email = d.get('email', '').strip().lower()
    if email and User.query.filter_by(email=email).first():
        return jsonify({'error': 'Эта почта уже используется'}), 400"""
    
    new_reg = """    email = d.get('email', '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        return jsonify({'error': 'Введите корректный email'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Эта почта уже используется'}), 400"""
    
    app = app.replace(old_reg, new_reg)
    
    # Generate code and store before commit
    app = app.replace(
        "    user = User(username=username, display_name=display_name,",
        """    import secrets as sec
    verify_code = ''.join([str(sec.randbelow(10)) for _ in range(6)])
    user = User(username=username, display_name=display_name,"""
    )
    
    app = app.replace(
        "                email=email if email and '@' in email else None)",
        """                email=email,
                email_verified=False,
                email_verify_code=verify_code,
                email_verify_expires=datetime.utcnow() + timedelta(hours=24))"""
    )

# Add verification endpoints
if 'api_verify_email' not in app:
    VERIFY_API = '''
# ============================================================
# EMAIL VERIFICATION
# ============================================================

def send_email(to_email, subject, body):
    """Отправка email через SMTP (Gmail/Mail.ru)"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    
    if not smtp_user or not smtp_pass:
        print(f'[EMAIL DEV] To: {to_email} | Subject: {subject} | Body: {body}')
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email
        
        html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f5f7fa;padding:20px;margin:0">
        <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
            <div style="text-align:center;margin-bottom:24px">
                <div style="display:inline-block;width:64px;height:64px;background:#2563EB;border-radius:16px;line-height:64px;font-size:32px;color:#fff;font-weight:bold">G</div>
                <h1 style="margin:12px 0 4px;color:#2563EB;font-size:24px">Gyert</h1>
            </div>
            <h2 style="color:#1a1a2e;font-size:20px;margin-bottom:16px">{subject}</h2>
            <div style="color:#444;font-size:15px;line-height:1.6">{body}</div>
            <div style="margin-top:32px;padding-top:16px;border-top:1px solid #eee;color:#888;font-size:13px;text-align:center">
                Gyert — социальная сеть нового поколения<br>
                <a href="https://gyert.onrender.com" style="color:#2563EB">gyert.onrender.com</a>
            </div>
        </div></body></html>"""
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f'SMTP error: {e}')
        return False


@app.route('/api/email/send', methods=['POST'])
@login_required
def api_send_verify_email():
    if current_user.email_verified:
        return jsonify({'error': 'Email уже подтверждён'}), 400
    if not current_user.email:
        return jsonify({'error': 'Email не указан'}), 400
    
    import secrets as sec
    code = ''.join([str(sec.randbelow(10)) for _ in range(6)])
    current_user.email_verify_code = code
    current_user.email_verify_expires = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    
    body = f"""<p>Привет, <strong>{current_user.display_name}</strong>!</p>
    <p>Ваш код подтверждения email:</p>
    <div style="text-align:center;margin:24px 0">
        <div style="display:inline-block;background:#f0f4ff;border:2px solid #2563EB;border-radius:12px;padding:16px 32px;font-size:32px;font-weight:bold;color:#2563EB;letter-spacing:8px;font-family:monospace">{code}</div>
    </div>
    <p>Код действителен 24 часа.</p>
    <p>Если вы не запрашивали этот код — проигнорируйте письмо.</p>"""
    
    sent = send_email(current_user.email, 'Подтверждение email', body)
    return jsonify({'success': True, 'sent': sent, 'dev_code': code if not sent else None})


@app.route('/api/email/verify', methods=['POST'])
@login_required
def api_verify_email():
    code = (request.get_json() or {}).get('code', '').strip()
    if not code:
        return jsonify({'error': 'Введите код'}), 400
    
    if current_user.email_verified:
        return jsonify({'success': True, 'already': True})
    
    if not current_user.email_verify_code:
        return jsonify({'error': 'Код не запрошен'}), 400
    
    if current_user.email_verify_expires < datetime.utcnow():
        return jsonify({'error': 'Код истёк. Запросите новый'}), 400
    
    if current_user.email_verify_code != code:
        return jsonify({'error': 'Неверный код'}), 400
    
    current_user.email_verified = True
    current_user.email_verify_code = None
    db.session.commit()
    return jsonify({'success': True})

'''
    
    app = app.replace(
        "# ============================================================\n# GEMINI AI API",
        VERIFY_API + "# ============================================================\n# GEMINI AI API"
    )

# Auto-send verification email on register
app = app.replace(
    "    login_user(user, remember=True)\n    return jsonify({'success': True, 'user': user.to_dict()})",
    """    login_user(user, remember=True)
    # Send verification email
    body = f'<p>Привет, <strong>{display_name}</strong>!</p><p>Спасибо за регистрацию в Gyert!</p><p>Ваш код подтверждения email:</p><div style="text-align:center;margin:24px 0"><div style="display:inline-block;background:#f0f4ff;border:2px solid #2563EB;border-radius:12px;padding:16px 32px;font-size:32px;font-weight:bold;color:#2563EB;letter-spacing:8px;font-family:monospace">{verify_code}</div></div><p>Код действителен 24 часа.</p>'
    send_email(email, 'Добро пожаловать в Gyert!', body)
    return jsonify({'success': True, 'user': user.to_dict(), 'verify_required': True})"""
)

write(app_path, app)

# ─── 5. register.html — email обязателен ───

reg_path = os.path.join(SERVER, 'templates', 'register.html')
reg = read(reg_path)

# Email уже есть — делаем required
reg = reg.replace(
    '<input type="email" id="email" placeholder="example@mail.com" autocomplete="email">',
    '<input type="email" id="email" placeholder="example@mail.com" autocomplete="email" required>'
)
reg = reg.replace('Email <small>(необязательно)</small>', 'Email <small>(будет проверен)</small>')

# email уже передаётся в submit, но проверим
if 'email:' not in reg:
    reg = reg.replace(
        "password:pw, phone:document.getElementById('ph').value, avatar_emoji:sel",
        "password:pw, phone:document.getElementById('ph').value, email:document.getElementById('email').value, avatar_emoji:sel"
    )

write(reg_path, reg)

# ─── 6. Email verification page ───

VERIFY_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Подтверждение email — Gyert</title>
    <link rel="icon" type="image/png" href="/static/favicon.png">
    <link rel="stylesheet" href="/static/css/auth.css">
    <style>
        .code-input { font-size: 28px !important; text-align: center; letter-spacing: 12px; font-family: monospace; padding: 14px !important; }
        .email-info { background: rgba(37,99,235,0.08); border: 1px solid rgba(37,99,235,0.2); border-radius: 12px; padding: 14px; margin-bottom: 16px; font-size: 14px; color: #444; text-align: center; }
        .email-info strong { color: #2563EB; }
        .resend { text-align: center; margin-top: 12px; font-size: 13px; color: #888; }
        .resend a { color: #2563EB; cursor: pointer; }
    </style>
</head>
<body>
    <div class="auth-bg"><div class="blob b1"></div><div class="blob b2"></div></div>
    <div class="auth-wrap">
        <div class="auth-card">
            <div class="auth-logo">
                <img src="/static/icon-192.png" style="width:72px;height:72px;border-radius:18px" alt="Gyert">
                <h1>Gyert</h1>
                <p>Подтверждение email</p>
            </div>
            <div class="email-info">
                📧 Мы отправили 6-значный код на <strong id="emailDisplay">ваш email</strong>
            </div>
            <form id="verifyForm">
                <div class="field">
                    <label>Код подтверждения</label>
                    <input type="text" id="code" class="code-input" placeholder="000000" maxlength="6" pattern="[0-9]{6}" required>
                </div>
                <button type="submit" class="btn-auth">Подтвердить</button>
                <div class="auth-error" id="err"></div>
            </form>
            <div class="resend">
                Не пришло письмо? <a onclick="resend()">Отправить повторно</a>
            </div>
            <div class="auth-footer">
                <a href="/feed">Пропустить (подтвердите позже)</a>
            </div>
        </div>
    </div>
    <script>
        fetch('/api/me').then(r=>r.json()).then(u=>{document.getElementById('emailDisplay').textContent=u.email||'ваш email';if(u.email_verified)location.href='/feed'});
        
        document.getElementById('code').oninput=e=>e.target.value=e.target.value.replace(/\\D/g,'');
        
        document.getElementById('verifyForm').onsubmit=async e=>{
            e.preventDefault();
            const err=document.getElementById('err');err.textContent='';
            const r=await fetch('/api/email/verify',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({code:document.getElementById('code').value})});
            const d=await r.json();
            if(d.success){location.href='/feed'}
            else err.textContent=d.error||'Ошибка';
        };
        
        async function resend(){
            const r=await fetch('/api/email/send',{method:'POST'});
            const d=await r.json();
            const err=document.getElementById('err');
            if(d.success){err.style.color='#2563EB';err.textContent='✓ Письмо отправлено!';if(d.dev_code)err.textContent+=' (DEV код: '+d.dev_code+')'}
            else{err.style.color='#ff3b3b';err.textContent=d.error||'Ошибка'}
        }
    </script>
</body>
</html>'''

write(os.path.join(SERVER, 'templates', 'verify_email.html'), VERIFY_HTML)

# Добавляем роут в app.py
app = read(app_path)
if "verify-email" not in app:
    app = app.replace(
        "@app.route('/register-tg')",
        "@app.route('/verify-email')\n@login_required\ndef verify_email_page():\n    return render_template('verify_email.html')\n\n@app.route('/register-tg')"
    )
    write(app_path, app)

# После регистрации — редирект на verify
reg = read(reg_path)
reg = reg.replace(
    "if(d.success){window.location.href='/feed'}",
    "if(d.success){window.location.href=d.verify_required?'/verify-email':'/feed'}"
)
write(reg_path, reg)

# ─── 7. НОВЫЙ БРЕНДИНГ — обновляем CSS ───

# auth.css — белый минималистичный стиль
AUTH_CSS = '''* { margin:0; padding:0; box-sizing:border-box; }
body {
    min-height: 100vh;
    background: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1a202c;
    overflow-y: auto;
    -webkit-font-smoothing: antialiased;
}
.auth-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.blob { position: absolute; border-radius: 50%; filter: blur(100px); opacity: .15; }
.b1 { width: 500px; height: 500px; background: #2563EB; top: -150px; right: -150px; animation: float 20s infinite; }
.b2 { width: 400px; height: 400px; background: #60A5FA; bottom: -100px; left: -100px; animation: float 16s infinite reverse; }
.b3 { width: 350px; height: 350px; background: #3B82F6; top: 40%; left: 50%; transform: translate(-50%,-50%); animation: float 24s infinite; }
@keyframes float {
    0%,100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(40px,-40px) scale(1.05); }
}
.auth-wrap {
    position: relative; z-index: 1;
    max-width: 440px; margin: 0 auto;
    padding: 40px 20px 60px;
}
.auth-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 24px;
    padding: 40px 32px;
    box-shadow: 0 4px 24px rgba(37,99,235,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
.auth-logo { text-align: center; margin-bottom: 32px; }
.logo-circle {
    width: 72px; height: 72px;
    background: #2563EB;
    border-radius: 18px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 900; color: #ffffff;
    margin-bottom: 12px;
    box-shadow: 0 8px 24px rgba(37,99,235,0.25);
}
.auth-logo h1 {
    font-size: 28px; font-weight: 800;
    color: #2563EB;
    margin-bottom: 4px;
}
.auth-logo p { color: #64748b; font-size: 14px; }

.field { margin-bottom: 16px; }
.field label {
    display: block; font-size: 13px; font-weight: 600;
    color: #475569; margin-bottom: 6px;
}
.field label small { color: #94a3b8; font-weight: 400; }
.field-wrap, .field-row { position: relative; display: flex; align-items: center; }
.prefix {
    position: absolute; left: 14px;
    color: #2563EB; font-weight: 700; font-size: 16px;
    z-index: 1;
}
.field-wrap input, .field-row input { padding-left: 32px !important; }
input, textarea {
    width: 100%; padding: 12px 14px;
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    color: #1a202c;
    font-size: 15px; outline: none;
    transition: all .2s;
    font-family: inherit;
}
input:focus, textarea:focus {
    border-color: #2563EB;
    background: #ffffff;
    box-shadow: 0 0 0 4px rgba(37,99,235,0.1);
}
input::placeholder { color: #94a3b8; }

.btn-auth {
    width: 100%; padding: 13px;
    background: #2563EB;
    border: none; border-radius: 12px;
    color: #ffffff; font-size: 15px; font-weight: 600;
    cursor: pointer; margin-top: 8px;
    transition: all .2s;
}
.btn-auth:hover { background: #1d4ed8; transform: translateY(-1px); box-shadow: 0 8px 20px rgba(37,99,235,0.25); }
.btn-auth:active { transform: translateY(0); }
.btn-auth:disabled { background: #cbd5e1; cursor: not-allowed; transform: none; }

.auth-error { color: #ef4444; font-size: 13px; margin-top: 10px; text-align: center; min-height: 18px; }
.auth-footer {
    text-align: center; margin-top: 20px;
    padding-top: 16px; border-top: 1px solid #e5e7eb;
    color: #64748b; font-size: 14px;
}
.auth-footer a { color: #2563EB; text-decoration: none; font-weight: 600; }
.auth-footer a:hover { text-decoration: underline; }

/* Reusable emoji picker styles */
.ava-circle {
    background: #f0f4ff !important;
    border: 3px solid #2563EB !important;
    box-shadow: 0 0 20px rgba(37,99,235,0.15) !important;
}
.emoji-box {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
}
.ep {
    background: #ffffff !important;
    border: 2px solid #e2e8f0 !important;
}
.ep:hover { border-color: #2563EB !important; background: #f0f4ff !important; }
.ep.sel { border-color: #2563EB !important; background: #2563EB !important; color: #fff; }
'''

write(os.path.join(SERVER, 'static', 'css', 'auth.css'), AUTH_CSS)

# main.css — обновляем брендовые цвета
css_path = os.path.join(SERVER, 'static', 'css', 'main.css')
css = read(css_path)

# Меняем основные акцентные цвета
css = css.replace("--acc:#4d7cff", "--acc:#2563EB")
css = css.replace("--acc2:#ff3b6f", "--acc2:#3B82F6")
css = css.replace("--acc-glow:rgba(77,124,255,.3)", "--acc-glow:rgba(37,99,235,.2)")
css = css.replace("--grad:linear-gradient(135deg,#4d7cff,#ff3b6f)", "--grad:linear-gradient(135deg,#2563EB,#3B82F6)")

# Light тема становится дефолтной — чище
css = css.replace(
    ".theme-light{--bg:#f0f2f5;--bg2:#fff;--bg3:#e8eaed;--bg4:rgba(0,0,0,.03);--text:#1a1a2e;--text2:#666;--text3:#999;--border:rgba(0,0,0,.08);--shadow:rgba(0,0,0,.1);--card:#fff;}",
    ".theme-light{--bg:#f8fafc;--bg2:#ffffff;--bg3:#f1f5f9;--bg4:#f8fafc;--text:#0f172a;--text2:#64748b;--text3:#94a3b8;--border:#e2e8f0;--shadow:rgba(0,0,0,.06);--card:#ffffff;}"
)

# Dark тема — синий акцент вместо фиолетового
css = css.replace(
    ".theme-dark{--bg:#0a0a1a;--bg2:#10102a;--bg3:#1a1a3e;--bg4:rgba(255,255,255,.04);",
    ".theme-dark{--bg:#0f172a;--bg2:#1e293b;--bg3:#334155;--bg4:rgba(255,255,255,.04);"
)

# Логотип — синий вместо градиента
css = css.replace(
    ".logo-g{width:36px;height:36px;background:var(--grad);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;color:#fff;box-shadow:0 0 15px var(--acc-glow);}",
    ".logo-g{width:36px;height:36px;background:#2563EB;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;color:#fff;box-shadow:0 4px 12px rgba(37,99,235,0.25);}"
)

css = css.replace(
    ".logo-text{font-size:20px;font-weight:800;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}",
    ".logo-text{font-size:20px;font-weight:800;color:#2563EB;}"
)

# Banner для верификации
EMAIL_BANNER_CSS = '''
/* ═══ EMAIL VERIFICATION BANNER ═══ */
.verify-banner {
    background: linear-gradient(135deg, #FEF3C7, #FDE68A);
    border: 1px solid #F59E0B;
    color: #92400E;
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
}
.verify-banner-btn {
    margin-left: auto;
    padding: 6px 14px;
    background: #F59E0B;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
}
.verify-banner-btn:hover { background: #D97706; }

/* New brand updates */
.theme-light .logo-g { background: #2563EB; }
.theme-light .nav-search input { background: #f1f5f9; border-color: #e2e8f0; }
.theme-light .post-card { box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.theme-light .sidebar-left, .theme-light .sr-block { box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
'''

if 'verify-banner' not in css:
    css += EMAIL_BANNER_CSS

write(css_path, css)

# ─── 8. main.html — обновляем favicon + theme-color + banner ───

html_path = os.path.join(SERVER, 'templates', 'main.html')
html = read(html_path)

# Добавляем favicon если нет
if '<link rel="icon"' not in html:
    html = html.replace(
        '<link rel="stylesheet" href="/static/css/main.css">',
        '<link rel="icon" type="image/png" href="/static/favicon.png">\n    <link rel="apple-touch-icon" href="/static/icon-192.png">\n    <meta name="theme-color" content="#2563EB">\n    <link rel="stylesheet" href="/static/css/main.css">'
    )

# Светлая тема по дефолту
html = html.replace('<body class="theme-dark"', '<body class="theme-light"')

# Добавляем banner верификации сверху main
if 'verify-banner' not in html:
    html = html.replace(
        '<main class="main-content" id="mainContent">',
        '<main class="main-content" id="mainContent">\n        <div class="verify-banner" id="verifyBanner" style="display:none">📧 Подтвердите email чтобы получить все возможности <button class="verify-banner-btn" onclick="window.location.href=\'/verify-email\'">Подтвердить</button></div>'
    )

write(html_path, html)

# ─── 9. app.js — показ banner если email не подтверждён + новые цвета ───

js_path = os.path.join(SERVER, 'static', 'js', 'app.js')
js = read(js_path)

# Светлая тема по дефолту
js = js.replace(
    "this.applyTheme(this.me.theme||'dark');",
    "this.applyTheme(this.me.theme||'light');"
)

# Banner verification
if 'verifyBanner' not in js:
    js = js.replace(
        "this.updateNav();",
        "this.updateNav();\n        if(this.me.email && !this.me.email_verified){const b=document.getElementById('verifyBanner');if(b)b.style.display='flex'}"
    )

# Новые цвета акцента
js = js.replace(
    "if(p==='cyan-green'){r.setProperty('--acc','#00f5c3');r.setProperty('--acc-rgb','0,245,195');r.setProperty('--acc-glow','rgba(0,245,195,.3)');r.setProperty('--grad','linear-gradient(135deg,#00f5c3,#a8ff00)');}else{r.setProperty('--acc','#4d7cff');r.setProperty('--acc-rgb','77,124,255');r.setProperty('--acc-glow','rgba(77,124,255,.3)');r.setProperty('--grad','linear-gradient(135deg,#4d7cff,#ff3b6f)');}",
    "if(p==='cyan-green'){r.setProperty('--acc','#10B981');r.setProperty('--acc-glow','rgba(16,185,129,.2)');r.setProperty('--grad','linear-gradient(135deg,#10B981,#3B82F6)');}else{r.setProperty('--acc','#2563EB');r.setProperty('--acc-glow','rgba(37,99,235,.2)');r.setProperty('--grad','linear-gradient(135deg,#2563EB,#3B82F6)');}"
)

write(js_path, js)

# ─── 10. login.html — обновляем стиль ───

login_path = os.path.join(SERVER, 'templates', 'login.html')
login = read(login_path)

# Если ещё нет favicon
if 'favicon' not in login:
    login = login.replace(
        '<link rel="stylesheet" href="/static/css/auth.css">',
        '<link rel="icon" type="image/png" href="/static/favicon.png">\n    <link rel="stylesheet" href="/static/css/auth.css">'
    )

write(login_path, login)

# То же для register
reg = read(reg_path)
if 'favicon' not in reg:
    reg = reg.replace(
        '<title>Gyert — Регистрация</title>',
        '<title>Gyert — Регистрация</title>\n    <link rel="icon" type="image/png" href="/static/favicon.png">'
    )
write(reg_path, reg)

# ─── 11. Delete DB ───

for db_path in [
    os.path.join(SERVER, 'instance', 'gyert.db'),
    os.path.join(SERVER, 'gyert.db')
]:
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'  Deleted {db_path}')

print()
print('='*55)
print('  Готово!')
print()
print('  Что сделано:')
print('    + Новая иконка (синие WiFi-волны на белом)')
print('    + Светлая тема по умолчанию')
print('    + Новый брендовый цвет #2563EB')
print('    + Чистый минималистичный auth дизайн')
print('    + Обязательная email-верификация')
print('    + 6-значный код на email')
print('    + Страница /verify-email')
print('    + Banner "подтвердите email" в шапке')
print()
print('  Для отправки email добавь в Render Environment:')
print('    SMTP_HOST = smtp.gmail.com')
print('    SMTP_PORT = 587')
print('    SMTP_USER = твой@gmail.com')
print('    SMTP_PASS = пароль_приложения_gmail')
print()
print('  Пароль приложения Gmail:')
print('    1. https://myaccount.google.com/security')
print('    2. Включи 2FA')
print('    3. App passwords -> Создай для Gyert')
print()
print('  Без SMTP — код выводится в консоль сервера')
print()
print('  Запуск:')
print('    cd C:\\Projects\\max_gyert\\server')
print('    python app.py')
print()
print('  Пуш на Render:')
print('    cd C:\\Projects\\max_gyert')
print('    git add -A')
print('    git commit -m "New brand + email verification"')
print('    git push origin main --force')
print('='*55)
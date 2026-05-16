import re

path = r"C:\Projects\max_gyert\server\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Новая функция
new_func = """@app.route('/api/register', methods=['POST'])
def api_register():
    d = request.get_json() or {}
    u = d.get('username','').strip().replace('@','').lower()
    dn = d.get('display_name','').strip()
    pw = d.get('password','')
    phone = d.get('phone','').strip()
    emoji = d.get('avatar_emoji','😊')
    email = d.get('email', '').strip().lower()

    if not u or not dn or not pw:
        return jsonify({'error':'Все поля обязательны'}), 400
    if not email or '@' not in email or '.' not in email:
        return jsonify({'error':'Введите корректный email'}), 400
    if len(u) < 3:
        return jsonify({'error':'Юзернейм мин 3 символа'}), 400
    if len(pw) < 6:
        return jsonify({'error':'Пароль мин 6 символов'}), 400
    if User.query.filter_by(username=u).first():
        return jsonify({'error':'Юзернейм занят'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error':'Эта почта уже используется'}), 400

    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+') if phone else None

    import secrets as sec
    verify_code = ''.join([str(sec.randbelow(10)) for _ in range(6)])

    user = User(
        username=u,
        display_name=dn,
        password_hash=generate_password_hash(pw, method='scrypt'),
        avatar='emoji:' + emoji,
        phone_number=phone_clean if phone_clean and len(phone_clean) >= 7 else None,
        email=email,
        email_verified=False,
        email_verify_code=verify_code,
        email_verify_expires=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)

    body = '<p>Привет, <strong>' + dn + '</strong>!</p>'
    body += '<p>Ваш код подтверждения email:</p>'
    body += '<div style="text-align:center;margin:24px 0">'
    body += '<div style="display:inline-block;background:#f0f4ff;border:2px solid #2563EB;border-radius:12px;padding:16px 32px;font-size:32px;font-weight:bold;color:#2563EB;letter-spacing:8px;font-family:monospace">'
    body += verify_code
    body += '</div></div>'
    body += '<p>Код действителен 24 часа.</p>'

    try:
        send_email(email, 'Добро пожаловать в Gyert!', body)
    except Exception as e:
        print('Email send error:', e)

    return jsonify({'success': True, 'user': user.to_dict(user.id), 'verify_required': True})

"""

# Регулярка: найти api_register от декоратора до следующего @app.route или @login_manager или @socketio
pattern = r"@app\.route\('/api/register'.*?\)\s*\ndef api_register\(\):.*?(?=\n@app\.route|\n@login_manager|\n@socketio|\n# =)"

if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_func, content, count=1, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: api_register заменена")
else:
    print("ERROR: api_register не найдена в файле")
    print("Ищем что есть:")
    for line in content.split("\n"):
        if "api_register" in line or "def api_register" in line:
            print("  ", line)
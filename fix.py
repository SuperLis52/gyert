import re

path = r"C:\Projects\max_gyert\server\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Простая замена через split
start = content.find("@app.route('/api/register'")
if start == -1:
    print("ERROR: api_register not found")
    exit()

# Найдём конец функции — следующий @app.route после неё
end = content.find("@app.route(", start + 10)
if end == -1:
    print("ERROR: end not found")
    exit()

new_func = '''@app.route('/api/register', methods=['POST'])
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


'''

new_content = content[:start] + new_func + content[end:]

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("OK: api_register replaced")
print(f"Length before: {len(content)}, after: {len(new_content)}")
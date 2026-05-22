#!/usr/bin/env python3
"""
Gyert Telegram Bot — Registration Flow
"""
import os, json, time, secrets, hashlib
import urllib.request, urllib.parse
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'
GYERT_URL = os.environ.get('GYERT_URL', 'http://localhost:5000')

# Хранилище состояний пользователей (в памяти, для прода нужно использовать Redis)
user_states = {}   # {chat_id: {'step': 1, 'phone': ..., 'nickname': ..., 'username': ..., 'tg_name': ..., 'tg_username': ...}}
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

def ask_phone(chat_id):
    """Отправляет кнопку для отправки номера телефона"""
    keyboard = [[{'text': '📱 Отправить номер телефона', 'request_contact': True}]]
    send(chat_id, 'Для регистрации мне нужен ваш номер телефона. Нажмите кнопку ниже.', {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': True})

def ask_nickname(chat_id):
    keyboard = [[{'text': 'Пропустить'}]]
    send(chat_id, 'Введите ваш никнейм (отображаемое имя):', {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': True})

def ask_username(chat_id):
    send(chat_id, 'Теперь введите @username (латиница, цифры, _):')

def ask_password(chat_id):
    send(chat_id, 'Придумайте пароль (минимум 6 символов):')

def get_updates():
    global offset
    r = api('getUpdates', offset=offset, timeout=30, limit=10)
    updates = r.get('result', [])
    if updates:
        offset = updates[-1]['update_id'] + 1
    return updates

def process_message(msg):
    chat_id = msg['chat']['id']
    user = msg.get('from', {})
    tg_name = user.get('first_name', '') + (' ' + user.get('last_name', '') if user.get('last_name') else '')
    tg_username = user.get('username', '')

    # Обработка команды /start
    if msg.get('text') == '/start':
        user_states[chat_id] = {'step': 1, 'tg_name': tg_name, 'tg_username': tg_username}
        ask_phone(chat_id)
        return

    # Обработка контакта (номер телефона)
    contact = msg.get('contact')
    if contact:
        if chat_id in user_states and user_states[chat_id].get('step') == 1:
            phone = contact.get('phone_number', '')
            # Сохраняем телефон (убираем '+' если есть)
            user_states[chat_id]['phone'] = phone.replace('+', '')
            user_states[chat_id]['step'] = 2
            ask_nickname(chat_id)
        else:
            send(chat_id, 'Вы ещё не начали регистрацию. Напишите /start.')
        return

    text = msg.get('text', '')
    if not text:
        return

    # Шаг 2: никнейм
    if chat_id in user_states and user_states[chat_id].get('step') == 2:
        if text == 'Пропустить':
            nickname = tg_name
        else:
            nickname = text.strip()
        user_states[chat_id]['nickname'] = nickname
        user_states[chat_id]['step'] = 3
        ask_username(chat_id)
        return

    # Шаг 3: @username
    if chat_id in user_states and user_states[chat_id].get('step') == 3:
        username = text.strip().replace('@', '').lower()
        if len(username) < 3:
            send(chat_id, 'Username слишком короткий. Попробуйте ещё раз (минимум 3 символа).')
            return
        user_states[chat_id]['username'] = username
        user_states[chat_id]['step'] = 4
        ask_password(chat_id)
        return

    # Шаг 4: пароль
    if chat_id in user_states and user_states[chat_id].get('step') == 4:
        password = text.strip()
        if len(password) < 6:
            send(chat_id, 'Пароль слишком короткий. Минимум 6 символов.')
            return
        state = user_states.pop(chat_id)
        # Регистрируем пользователя через API Gyert
        try:
            # Сначала регистрируем
            reg_data = json.dumps({
                'username': state['username'],
                'display_name': state['nickname'],
                'password': password,
                'phone': state.get('phone', ''),
                'avatar_emoji': '😊'
            }).encode()
            req = urllib.request.Request(f'{GYERT_URL}/api/register',
                                         data=reg_data,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get('success'):
                    send(chat_id, f'🎉 <b>Регистрация успешна!</b>\n\n'
                                  f'Теперь вы можете войти в аккаунт на сайте Gyert:\n'
                                  f'{GYERT_URL}/login\n\n'
                                  f'Ваш логин: @{state["username"]}')
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    send(chat_id, f'❌ Ошибка: {error_msg}\nПопробуйте ещё раз, начав с /start.')
        except Exception as e:
            send(chat_id, f'❌ Ошибка соединения с сервером. Попробуйте позже.')
        return

    # Если ни одно условие не подошло
    send(chat_id, 'Я вас не понял. Используйте /start для начала регистрации.')

def run():
    if not BOT_TOKEN:
        print('ERROR: Set TELEGRAM_BOT_TOKEN environment variable')
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
            time.sleep(0.5)
        except KeyboardInterrupt:
            print('\nBot stopped')
            break
        except Exception as e:
            print(f'Error: {e}')
            time.sleep(5)

if __name__ == '__main__':
    run()

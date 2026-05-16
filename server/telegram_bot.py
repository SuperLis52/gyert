#!/usr/bin/env python3
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
            '👋 <b>Добро пожаловать в Gyert!</b>\n\n'
            'Я помогу вам зарегистрироваться или войти в социальную сеть Gyert.\n\n'
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
            f'✅ <b>Ваш код регистрации:</b>\n\n'
            f'<code>{code}</code>\n\n'
            f'🌐 Откройте <a href="{GYERT_URL}/register-tg">страницу регистрации</a> '
            f'и введите этот код.\n\n'
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
            f'🔑 <b>Ваш код входа:</b>\n\n'
            f'<code>{code}</code>\n\n'
            f'🌐 Откройте <a href="{GYERT_URL}/login-tg">страницу входа</a> '
            f'и введите этот код.\n\n'
            f'⏱ Код действителен <b>10 минут</b>.'
        )

    elif text == '❓ Помощь':
        send(chat_id,
            '❓ <b>Помощь</b>\n\n'
            '📝 <b>Регистрация</b> — создать новый аккаунт\n'
            '🔑 <b>Войти</b> — войти в существующий аккаунт\n\n'
            f'🌐 Сайт: {GYERT_URL}\n'
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
            print('\nBot stopped')
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
        send(chat_id, f'🎉 <b>Регистрация успешна!</b>\n\nДобро пожаловать в Gyert, @{username}!\n\n🚀 <a href="{GYERT_URL}/feed">Открыть приложение</a>')
    else:
        send(chat_id, f'✅ <b>Вы вошли в аккаунт!</b>\n\n🚀 <a href="{GYERT_URL}/feed">Открыть приложение</a>')


if __name__ == '__main__':
    run()

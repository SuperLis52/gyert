#!/usr/bin/env python3
"""
Gyert Telegram Bot – Registration with steps, back button, and confirmation
"""
import os
import json
import logging
import asyncio
import secrets
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
GYERT_URL = os.environ.get('GYERT_URL', 'http://localhost:5000')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не задан")
    exit(1)

# Состояния разговора
ASK_PHONE, ASK_NICKNAME, ASK_USERNAME, ASK_PASSWORD, CONFIRM = range(5)

# Временное хранилище данных пользователей (в продакшене — Redis)
user_data = {}

def api_register(username, display_name, password, phone, avatar_emoji='😊'):
    """Отправляет запрос на регистрацию в Gyert API"""
    data = json.dumps({
        'username': username,
        'display_name': display_name,
        'password': password,
        'phone': phone,
        'avatar_emoji': avatar_emoji
    }).encode()
    req = urllib.request.Request(f'{GYERT_URL}/api/register',
                                 data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"Registration API error: {e}")
        return None

async def start(update: Update, context: CallbackContext) -> int:
    """Команда /start"""
    user = update.effective_user
    user_data[user.id] = {'tg_name': user.full_name, 'tg_username': user.username}
    keyboard = [[KeyboardButton('📱 Отправить номер телефона', request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        '👋 Добро пожаловать в Gyert!\nДля регистрации мне нужен ваш номер телефона. Нажмите кнопку ниже.',
        reply_markup=reply_markup
    )
    return ASK_PHONE

async def phone_received(update: Update, context: CallbackContext) -> int:
    """Получаем контакт (номер телефона)"""
    contact = update.message.contact
    if not contact:
        await update.message.reply_text('Пожалуйста, используйте кнопку для отправки номера.')
        return ASK_PHONE
    user_id = update.effective_user.id
    user_data[user_id]['phone'] = contact.phone_number
    # Переходим к никнейму
    keyboard = [['Пропустить']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        'Введите ваш никнейм (отображаемое имя) или нажмите "Пропустить", чтобы использовать имя из Telegram.',
        reply_markup=reply_markup
    )
    return ASK_NICKNAME

async def nickname_entered(update: Update, context: CallbackContext) -> int:
    """Получаем никнейм"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == 'Пропустить':
        nickname = user_data[user_id].get('tg_name', 'User')
    else:
        nickname = text
    user_data[user_id]['nickname'] = nickname
    keyboard = [['↩️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f'Никнейм: <b>{nickname}</b>\nТеперь введите @username (латиница, цифры, _):',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return ASK_USERNAME

async def username_entered(update: Update, context: CallbackContext) -> int:
    """Получаем username"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == '↩️ Назад':
        # Возвращаемся к вводу никнейма
        keyboard = [['Пропустить']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text('Введите ваш никнейм:', reply_markup=reply_markup)
        return ASK_NICKNAME
    username = text.replace('@', '').lower()
    if len(username) < 3:
        await update.message.reply_text('Username слишком короткий. Минимум 3 символа.')
        return ASK_USERNAME
    # Проверка на допустимые символы
    if not all(c.isalnum() or c == '_' for c in username):
        await update.message.reply_text('Только латиница, цифры и _.')
        return ASK_USERNAME
    user_data[user_id]['username'] = username
    keyboard = [['↩️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f'Username: @{username}\nТеперь придумайте пароль (минимум 6 символов):',
        reply_markup=reply_markup
    )
    return ASK_PASSWORD

async def password_entered(update: Update, context: CallbackContext) -> int:
    """Получаем пароль"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == '↩️ Назад':
        keyboard = [['↩️ Назад']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text('Введите @username:', reply_markup=reply_markup)
        return ASK_USERNAME
    password = text
    if len(password) < 6:
        await update.message.reply_text('Пароль слишком короткий. Минимум 6 символов.')
        return ASK_PASSWORD
    user_data[user_id]['password'] = password
    # Показываем сводку и запрашиваем подтверждение
    state = user_data[user_id]
    summary = (
        f'📋 <b>Проверьте данные:</b>\n'
        f'Телефон: {state.get("phone", "не указан")}\n'
        f'Никнейм: {state["nickname"]}\n'
        f'Username: @{state["username"]}\n'
        f'Пароль: {"*" * len(password)}\n\n'
        f'Всё верно? Отправьте "Да" для завершения, или "Нет" для отмены.'
    )
    keyboard = [['✅ Да', '↩️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='HTML')
    return CONFIRM

async def confirm(update: Update, context: CallbackContext) -> int:
    """Подтверждение и регистрация"""
    text = update.message.text.strip().lower()
    user_id = update.effective_user.id
    if text == '↩️ назад' or text == 'нет':
        await update.message.reply_text('Регистрация отменена. Начните заново с /start.',
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if text != 'да' and text != '✅ да':
        await update.message.reply_text('Пожалуйста, ответьте "Да" или "Нет".')
        return CONFIRM

    state = user_data.pop(user_id, None)
    if not state:
        await update.message.reply_text('Ошибка состояния. Начните с /start.')
        return ConversationHandler.END

    # Регистрируем
    result = api_register(
        username=state['username'],
        display_name=state['nickname'],
        password=state['password'],
        phone=state.get('phone', '')
    )
    if result and result.get('success'):
        await update.message.reply_text(
            f'🎉 <b>Регистрация успешна!</b>\n\n'
            f'Теперь вы можете войти в аккаунт на сайте Gyert:\n'
            f'{GYERT_URL}/login\n\n'
            f'Ваш логин: @{state["username"]}',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
    else:
        error = result.get('error', 'Неизвестная ошибка') if result else 'Ошибка соединения'
        await update.message.reply_text(
            f'❌ Ошибка регистрации: {error}\nПопробуйте снова /start.',
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Регистрация отменена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def run_bot():
    """Запускает бота в текущем event loop (для интеграции с Flask)"""
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_PHONE: [MessageHandler(filters.CONTACT, phone_received)],
            ASK_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nickname_entered)],
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_entered)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_entered)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

if __name__ == '__main__':
    run_bot()

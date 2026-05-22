import os
import threading
import sys
from app import app, db, socketio

def start_telegram_bot():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN не задан – бот не запущен")
        return
    try:
        from telegram_bot import run_bot
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")

if __name__ == '__main__':
    # Запускаем бота в отдельном демон-потоке
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

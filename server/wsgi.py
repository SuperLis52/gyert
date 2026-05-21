import os
from app import app, db, socketio, create_nft_codes, create_stickers, create_premium_plans, create_demo

for folder in [
    app.config['UPLOAD_FOLDER'],
    app.config['MEDIA_FOLDER'],
    app.config['POSTS_FOLDER'],
    app.config['VOICE_FOLDER']
]:
    os.makedirs(folder, exist_ok=True)

with app.app_context():
    db.create_all()
    create_nft_codes()
    create_stickers()
    create_premium_plans()
    create_demo()
    print("Database initialized and demo data created.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
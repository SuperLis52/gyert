import os
from app import app, db, socketio, create_nft_codes, create_stickers, create_demo

for folder in [
    app.config['UPLOAD_FOLDER'],
    app.config['MEDIA_FOLDER'],
    app.config['POSTS_FOLDER'],
    app.config['VOICE_FOLDER']
]:
    os.makedirs(folder, exist_ok=True)

dap = os.path.join(app.config['UPLOAD_FOLDER'],'default.png')
if not os.path.exists(dap):
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
    create_demo()
    create_nft_codes()
    create_stickers()

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
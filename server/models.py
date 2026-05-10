from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

likes_table = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'))
)

followers_table = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(256), default='default.png')
    bio = db.Column(db.Text, default='')
    phone_number = db.Column(db.String(20), nullable=True)
    theme = db.Column(db.String(20), default='dark')
    accent_color = db.Column(db.String(20), default='cyan-green')
    language = db.Column(db.String(5), default='ru')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_username_change = db.Column(db.DateTime, nullable=True)
    last_displayname_change = db.Column(db.DateTime, nullable=True)
    cover_image = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)

    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    memberships = db.relationship('ChatMember', backref='user', lazy='dynamic')

    following = db.relationship('User', secondary=followers_table,
        primaryjoin=(followers_table.c.follower_id == id),
        secondaryjoin=(followers_table.c.followed_id == id),
        backref=db.backref('followers_list', lazy='dynamic'), lazy='dynamic')

    nfts = db.relationship('UserNft', backref='owner', lazy='dynamic')

    def followers_count(self):
        return db.session.query(followers_table).filter(followers_table.c.followed_id == self.id).count()

    def following_count(self):
        return db.session.query(followers_table).filter(followers_table.c.follower_id == self.id).count()

    def is_following(self, user):
        return self.following.filter(followers_table.c.followed_id == user.id).count() > 0

    def get_nft_badge(self):
        nft = UserNft.query.filter_by(user_id=self.id, equipped=True).first()
        if nft and nft.nft:
            return {'emoji': nft.nft.nft_emoji, 'name': nft.nft.nft_name, 'price': nft.nft.nft_price, 'index': '#' + nft.nft.code}
        return None

    def to_dict(self, current_user_id=None):
        d = {
            'id': self.id, 'username': self.username, 'display_name': self.display_name,
            'avatar': self.avatar, 'bio': self.bio or '', 'phone_number': self.phone_number,
            'theme': self.theme, 'accent_color': self.accent_color, 'language': self.language,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_online': self.is_online, 'created_at': self.created_at.isoformat(),
            'cover_image': self.cover_image, 'location': self.location,
            'website': self.website, 'is_verified': self.is_verified, 'is_private': self.is_private,
            'followers_count': self.followers_count(), 'following_count': self.following_count(),
            'posts_count': self.posts.count(),
            'nft_badge': self.get_nft_badge(),
        }
        if current_user_id:
            from flask_login import current_user as cu
            d['is_following'] = db.session.query(followers_table).filter(
                followers_table.c.follower_id == current_user_id,
                followers_table.c.followed_id == self.id).count() > 0
            d['is_followed_by'] = db.session.query(followers_table).filter(
                followers_table.c.follower_id == self.id,
                followers_table.c.followed_id == current_user_id).count() > 0
        return d


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(256), nullable=True)
    media_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    repost_of_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    visibility = db.Column(db.String(20), default='public')

    likes = db.relationship('User', secondary=likes_table, backref=db.backref('liked_posts', lazy='dynamic'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    repost_of = db.relationship('Post', remote_side=[id], uselist=False)

    def likes_count(self):
        return db.session.query(likes_table).filter(likes_table.c.post_id == self.id).count()

    def to_dict(self, current_user_id=None):
        repost = None
        if self.repost_of_id and self.repost_of:
            repost = self.repost_of.to_dict()
        d = {
            'id': self.id, 'author': self.author.to_dict() if self.author else None,
            'content': self.content if not self.is_deleted else '', 'media_url': self.media_url,
            'media_type': self.media_type, 'created_at': self.created_at.isoformat(),
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_deleted': self.is_deleted, 'is_pinned': self.is_pinned,
            'likes_count': self.likes_count(), 'comments_count': self.comments.count(),
            'reposts_count': Post.query.filter_by(repost_of_id=self.id, is_deleted=False).count(),
            'repost_of': repost, 'visibility': self.visibility,
        }
        if current_user_id:
            d['is_liked'] = db.session.query(likes_table).filter(
                likes_table.c.user_id == current_user_id,
                likes_table.c.post_id == self.id).count() > 0
        return d


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'post_id': self.post_id,
            'author': self.author.to_dict() if self.author else None,
            'content': self.content if not self.is_deleted else '',
            'parent_id': self.parent_id, 'created_at': self.created_at.isoformat(),
            'is_deleted': self.is_deleted,
            'replies_count': self.replies.count(),
        }


class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_url = db.Column(db.String(256), nullable=False)
    media_type = db.Column(db.String(20), default='image')
    text_overlay = db.Column(db.String(200), nullable=True)
    bg_color = db.Column(db.String(20), default='#000000')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    views = db.relationship('StoryView', backref='story', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'author': self.author.to_dict() if self.author else None,
            'media_url': self.media_url, 'media_type': self.media_type,
            'text_overlay': self.text_overlay, 'bg_color': self.bg_color,
            'created_at': self.created_at.isoformat(),
            'views_count': self.views.count(),
        }


class StoryView(db.Model):
    __tablename__ = 'story_views'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    type = db.Column(db.String(30), nullable=False)
    text = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    from_user = db.relationship('User', foreign_keys=[from_user_id])

    def to_dict(self):
        return {
            'id': self.id, 'type': self.type, 'text': self.text, 'link': self.link,
            'is_read': self.is_read, 'created_at': self.created_at.isoformat(),
            'from_user': self.from_user.to_dict() if self.from_user else None,
        }


class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)
    is_group = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.String(256), default='default.png')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invite_code = db.Column(db.String(32), unique=True, nullable=True)
    members = db.relationship('ChatMember', backref='chat', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='chat', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, uid=None):
        d = {'id': self.id, 'name': self.name, 'is_group': self.is_group,
             'avatar': self.avatar, 'created_at': self.created_at.isoformat(),
             'members': [m.to_dict() for m in self.members], 'invite_code': self.invite_code}
        if not self.is_group and uid:
            other = self.members.filter(ChatMember.user_id != uid).first()
            if other and other.user:
                d['name'] = other.user.display_name
                d['avatar'] = other.user.avatar
                d['other_user'] = other.user.to_dict(uid)
        lm = self.messages.filter_by(is_deleted=False).order_by(Message.created_at.desc()).first()
        if lm: d['last_message'] = lm.to_dict()
        unread = 0
        if uid:
            unread = self.messages.filter(Message.sender_id != uid, Message.is_deleted == False,
                ~Message.read_by.any(MessageRead.user_id == uid)).count()
        d['unread_count'] = unread
        return d


class ChatMember(db.Model):
    __tablename__ = 'chat_members'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    __table_args__ = (db.UniqueConstraint('chat_id', 'user_id'),)
    def to_dict(self):
        return {'user_id': self.user_id, 'role': self.role,
                'display_name': self.user.display_name if self.user else None,
                'username': self.user.username if self.user else None,
                'avatar': self.user.avatar if self.user else None,
                'is_online': self.user.is_online if self.user else False}


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    forwarded_from_name = db.Column(db.String(120), nullable=True)
    media_url = db.Column(db.String(256), nullable=True)
    media_type = db.Column(db.String(20), nullable=True)
    voice_url = db.Column(db.String(256), nullable=True)
    read_by = db.relationship('MessageRead', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    reactions = db.relationship('Reaction', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    reply_to = db.relationship('Message', remote_side=[id], uselist=False)

    def to_dict(self):
        reply = None
        if self.reply_to_id and self.reply_to:
            reply = {'id': self.reply_to.id, 'sender_name': self.reply_to.sender.display_name if self.reply_to.sender else '?',
                     'content': self.reply_to.content[:100] if not self.reply_to.is_deleted else ''}
        rxn = {}
        for r in self.reactions:
            if r.emoji not in rxn: rxn[r.emoji] = {'emoji': r.emoji, 'count': 0, 'users': []}
            rxn[r.emoji]['count'] += 1; rxn[r.emoji]['users'].append(r.user_id)
        return {
            'id': self.id, 'chat_id': self.chat_id, 'sender_id': self.sender_id,
            'sender_name': self.sender.display_name if self.sender else '?',
            'sender_avatar': self.sender.avatar if self.sender else 'default.png',
            'sender_nft_badge': self.sender.get_nft_badge() if self.sender else None,
            'content': self.content if not self.is_deleted else '',
            'message_type': self.message_type, 'created_at': self.created_at.isoformat(),
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_deleted': self.is_deleted, 'reply_to': reply,
            'forwarded_from_name': self.forwarded_from_name,
            'media_url': self.media_url, 'media_type': self.media_type,
            'voice_url': self.voice_url,
            'read_by': [r.to_dict() for r in self.read_by],
            'reactions': list(rxn.values()),
        }


class MessageRead(db.Model):
    __tablename__ = 'message_reads'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id'),)
    def to_dict(self):
        return {'user_id': self.user_id, 'read_at': self.read_at.isoformat()}


class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', 'emoji'),)


class NftCode(db.Model):
    __tablename__ = 'nft_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    nft_type = db.Column(db.String(50), nullable=False)
    nft_emoji = db.Column(db.String(10), nullable=False)
    nft_name = db.Column(db.String(100), nullable=False)
    nft_price = db.Column(db.String(20), nullable=False)
    activated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    activated_at = db.Column(db.DateTime, nullable=True)
    def to_dict(self):
        return {'code': self.code, 'nft_type': self.nft_type, 'nft_emoji': self.nft_emoji,
                'nft_name': self.nft_name, 'nft_price': self.nft_price, 'index': '#' + self.code,
                'activated': self.activated_by is not None}


class UserNft(db.Model):
    __tablename__ = 'user_nfts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nft_code_id = db.Column(db.Integer, db.ForeignKey('nft_codes.id'), nullable=False)
    equipped = db.Column(db.Boolean, default=True)
    nft = db.relationship('NftCode')

    def to_dict(self):
        return {'id': self.id, 'nft': self.nft.to_dict() if self.nft else None, 'equipped': self.equipped}


class StickerPack(db.Model):
    __tablename__ = 'sticker_packs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stickers = db.Column(db.Text, default='[]')
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'stickers': json.loads(self.stickers)}
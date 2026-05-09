from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from server.extensions import db


class SerializerMixin:
    def fmt_time(self, value):
        if value is None:
            return None
        return value.strftime('%Y-%m-%d %H:%M:%S')


class Role(db.Model):
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permission = db.Column(db.String(50), unique=True, nullable=False)

    @staticmethod
    def ensure_defaults():
        defaults = [('ADMIN', 'ANY'), ('USER', 'SOME')]
        for name, permission in defaults:
            if Role.query.filter_by(name=name).first() is None:
                db.session.add(Role(name=name, permission=permission))
        db.session.commit()


class States(db.Model):
    __tablename__ = 'states'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    timestamp = db.Column(db.DateTime, default=datetime.now)

    @staticmethod
    def ensure_defaults():
        for name in ['正常', '禁用']:
            if States.query.filter_by(name=name).first() is None:
                db.session.add(States(name=name))
        db.session.commit()


class ThirdParty(db.Model):
    __tablename__ = 'third_party'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    @staticmethod
    def ensure_defaults():
        for name in ['default', 'github']:
            if ThirdParty.query.filter_by(name=name).first() is None:
                db.session.add(ThirdParty(name=name))
        db.session.commit()


class User(db.Model, SerializerMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    website = db.Column(db.String(128), default='')
    avatar = db.Column(db.String(128), nullable=False, default='')
    confirm = db.Column(db.Integer, nullable=False, default=1)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), default=2)
    create_time = db.Column(db.DateTime, default=datetime.now)
    slogan = db.Column(db.String(200), default='')
    recent_login = db.Column(db.DateTime, default=datetime.now)
    received_email_tag = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, db.ForeignKey('states.id'), default=1)
    reg_way = db.Column(db.Integer, db.ForeignKey('third_party.id'), default=1)

    role = db.relationship('Role')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @property
    def is_admin(self):
        return self.role_id == 1 or (self.role and self.role.name == 'ADMIN')

    def to_public(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'website': self.website or '',
            'avatar': self.avatar or '',
            'slogan': self.slogan or '',
            'role': 'ADMIN' if self.is_admin else 'USER',
            'createdAt': self.fmt_time(self.create_time),
            'recentLogin': self.fmt_time(self.recent_login)
        }


class BlogType(db.Model):
    __tablename__ = 'blog_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    counts = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(300), nullable=False, default='')
    create_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'counts': self.counts or 0
        }


class Blog(db.Model, SerializerMixin):
    __tablename__ = 'blog'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('blog_type.id'))
    pre_img = db.Column(db.String(200), nullable=False, default='')
    introduce = db.Column(db.String(255), nullable=False, default='')
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Integer, nullable=False, default=0)
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    read_times = db.Column(db.Integer, default=0)
    delete_flag = db.Column(db.Integer, db.ForeignKey('states.id'), default=1)
    is_top = db.Column(db.Integer, default=0)

    category = db.relationship('BlogType')

    def to_card(self):
        return {
            'id': self.id,
            'title': self.title,
            'intro': self.introduce or '',
            'cover': self.pre_img or '',
            'category': self.category.name if self.category else '未分类',
            'readTimes': self.read_times or 0,
            'isTop': bool(self.is_top),
            'createdAt': self.fmt_time(self.create_time),
            'updatedAt': self.fmt_time(self.update_time)
        }

    def to_detail(self):
        item = self.to_card()
        item['content'] = self.content
        return item


class BlogComment(db.Model, SerializerMixin):
    __tablename__ = 'blog_comment'

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    parent_id = db.Column(db.Integer)
    replied_id = db.Column(db.Integer, db.ForeignKey('blog_comment.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'))
    delete_flag = db.Column(db.Integer, default=0)

    author = db.relationship('User')

    def to_dict(self, sentiment=None):
        return {
            'id': self.id,
            'body': self.body or '',
            'author': self.author.to_public() if self.author else None,
            'blogId': self.blog_id,
            'parentId': self.parent_id,
            'repliedId': self.replied_id,
            'sentiment': sentiment,
            'createdAt': self.fmt_time(self.timestamp)
        }


class CommentSentiment(db.Model):
    __tablename__ = 'comment_sentiment'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('blog_comment.id'), unique=True, nullable=False)
    label = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0.0)
    positive = db.Column(db.Float, nullable=False, default=0.0)
    neutral = db.Column(db.Float, nullable=False, default=0.0)
    negative = db.Column(db.Float, nullable=False, default=0.0)
    raw = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'label': self.label,
            'score': round(self.score or 0, 4),
            'probabilities': {
                'positive': round(self.positive or 0, 4),
                'neutral': round(self.neutral or 0, 4),
                'negative': round(self.negative or 0, 4)
            }
        }

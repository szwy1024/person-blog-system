import secrets
from datetime import datetime
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, jsonify, redirect, request, session
from sqlalchemy import or_

from server.extensions import db
from server.models import Blog, BlogComment, BlogType, CommentSentiment, Role, States, ThirdParty, User
from server.sentiment import dump_raw, predict_sentiment


api = Blueprint('api', __name__)


def ok(data=None, **extra):
    payload = {'ok': True}
    if data is not None:
        payload['data'] = data
    payload.update(extra)
    return jsonify(payload)


def fail(message, status=400):
    return jsonify({'ok': False, 'message': message}), status


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required():
    user = current_user()
    if user is None:
        return None, fail('请先登录', 401)
    return user, None


def admin_required():
    user, error = login_required()
    if error:
        return None, error
    if not user.is_admin:
        return None, fail('需要管理员权限', 403)
    return user, None


def github_oauth_enabled():
    return bool(current_app.config.get('GITHUB_CLIENT_ID') and current_app.config.get('GITHUB_CLIENT_SECRET'))


def frontend_redirect(**params):
    url = current_app.config.get('FRONTEND_URL') or current_app.config.get('SITE_URL') or '/'
    if params:
        separator = '&' if '?' in url else '?'
        url = '{}{}{}'.format(url, separator, urlencode(params))
    return redirect(url)


def github_headers(access_token):
    return {
        'Authorization': 'token {}'.format(access_token),
        'Accept': 'application/vnd.github+json',
        'User-Agent': current_app.config.get('SITE_NAME') or 'Blogin'
    }


def get_github_email(access_token, fallback):
    if fallback:
        return fallback
    response = requests.get(
        'https://api.github.com/user/emails',
        headers=github_headers(access_token),
        timeout=8
    )
    response.raise_for_status()
    emails = response.json() or []
    verified = [item for item in emails if item.get('email') and item.get('verified')]
    primary = next((item for item in verified if item.get('primary')), None)
    selected = primary or (verified[0] if verified else None)
    return selected.get('email') if selected else ''


def unique_username(seed):
    base = ''.join(ch if ch.isalnum() or ch in ['_', '-'] else '_' for ch in (seed or 'github_user')).strip('_')
    base = (base or 'github_user')[:32]
    candidate = base
    index = 1
    while User.query.filter_by(username=candidate).first() is not None:
        suffix = '_{}'.format(index)
        candidate = '{}{}'.format(base[:40 - len(suffix)], suffix)
        index += 1
    return candidate


@api.route('/health')
def api_health():
    return ok({'status': 'ok'})


@api.route('/site')
def site():
    github_owner = current_app.config['SITE_GITHUB_OWNER']
    github_repo = current_app.config['SITE_GITHUB_REPO']
    github_url = ''
    if github_owner:
        github_url = 'https://github.com/{}'.format(github_owner)
        if github_repo:
            github_url = '{}/{}'.format(github_url, github_repo)

    return ok({
        'name': current_app.config['SITE_NAME'],
        'subtitle': current_app.config['SITE_SUBTITLE'],
        'owner': current_app.config['SITE_OWNER'],
        'email': current_app.config['SITE_EMAIL'],
        'url': current_app.config['SITE_URL'],
        'startDate': current_app.config['SITE_START_DATE'],
        'avatar': current_app.config['SITE_AVATAR'],
        'heroTitle': current_app.config['SITE_HERO_TITLE'],
        'heroText': current_app.config['SITE_HERO_TEXT'],
        'github': {
            'owner': github_owner,
            'repo': github_repo,
            'url': github_url
        },
        'auth': {
            'github': github_oauth_enabled()
        }
    })


@api.route('/auth/me')
def me():
    user = current_user()
    return ok(user.to_public() if user else None)


@api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    account = (data.get('account') or '').strip()
    password = data.get('password') or ''
    if not account or not password:
        return fail('请输入邮箱/用户名和密码')

    user = User.query.filter(or_(User.email == account, User.username == account)).first()
    if user is None or not user.check_password(password):
        return fail('账号或密码错误', 401)

    user.recent_login = datetime.now()
    db.session.commit()
    session.permanent = True
    session['user_id'] = user.id
    return ok(user.to_public())


@api.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return ok()


@api.route('/auth/github/login')
def github_login():
    if not github_oauth_enabled():
        return fail('GitHub 登录尚未配置', 503)

    state = secrets.token_urlsafe(24)
    session['github_oauth_state'] = state
    params = {
        'client_id': current_app.config['GITHUB_CLIENT_ID'],
        'redirect_uri': current_app.config['GITHUB_REDIRECT_URI'],
        'scope': current_app.config['GITHUB_OAUTH_SCOPE'],
        'state': state,
        'allow_signup': 'true'
    }
    return redirect('https://github.com/login/oauth/authorize?{}'.format(urlencode(params)))


@api.route('/auth/github/callback')
def github_callback():
    if not github_oauth_enabled():
        return frontend_redirect(oauth='github', status='disabled')

    code = request.args.get('code')
    state = request.args.get('state')
    expected_state = session.pop('github_oauth_state', None)
    if not code or not state or state != expected_state:
        return frontend_redirect(oauth='github', status='state_error')

    try:
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id': current_app.config['GITHUB_CLIENT_ID'],
                'client_secret': current_app.config['GITHUB_CLIENT_SECRET'],
                'code': code,
                'redirect_uri': current_app.config['GITHUB_REDIRECT_URI'],
                'state': state
            },
            headers={'Accept': 'application/json'},
            timeout=8
        )
        token_response.raise_for_status()
        access_token = (token_response.json() or {}).get('access_token')
        if not access_token:
            return frontend_redirect(oauth='github', status='token_error')

        profile_response = requests.get(
            'https://api.github.com/user',
            headers=github_headers(access_token),
            timeout=8
        )
        profile_response.raise_for_status()
        profile = profile_response.json() or {}

        email = get_github_email(access_token, profile.get('email'))
        if not email:
            return frontend_redirect(oauth='github', status='email_required')

        user = User.query.filter_by(email=email).first()
        if user is None:
            third_party = ThirdParty.query.filter_by(name='github').first()
            if third_party is None:
                third_party = ThirdParty(name='github')
                db.session.add(third_party)
                db.session.flush()

            user = User(
                username=unique_username(profile.get('login') or email.split('@')[0]),
                email=email,
                website=profile.get('html_url') or '',
                avatar=profile.get('avatar_url') or '',
                slogan=profile.get('bio') or '',
                role_id=2,
                confirm=1,
                reg_way=third_party.id
            )
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
        else:
            if profile.get('avatar_url'):
                user.avatar = profile.get('avatar_url')
            if profile.get('html_url') and not user.website:
                user.website = profile.get('html_url')
            if profile.get('bio') and not user.slogan:
                user.slogan = profile.get('bio')

        user.recent_login = datetime.now()
        db.session.commit()
        session.permanent = True
        session['user_id'] = user.id
        return frontend_redirect(oauth='github', status='success')
    except requests.RequestException:
        current_app.logger.exception('GitHub OAuth request failed')
        return frontend_redirect(oauth='github', status='request_error')


@api.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    if not username or not email or len(password) < 6:
        return fail('用户名、邮箱和至少 6 位密码为必填项')
    if User.query.filter(or_(User.email == email, User.username == username)).first():
        return fail('用户名或邮箱已经存在')

    user = User(username=username, email=email, role_id=2, confirm=1, avatar='')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return ok(user.to_public())


@api.route('/categories')
def categories():
    rows = BlogType.query.order_by(BlogType.create_time.desc()).all()
    return ok([row.to_dict() for row in rows])


@api.route('/blogs')
def blogs():
    page = max(int(request.args.get('page', 1)), 1)
    size = min(max(int(request.args.get('size', 8)), 1), 30)
    keyword = (request.args.get('q') or '').strip()
    category_id = request.args.get('category')

    query = Blog.query.filter(Blog.is_private == 0)
    if keyword:
        like = '%{}%'.format(keyword)
        query = query.filter(or_(Blog.title.like(like), Blog.introduce.like(like), Blog.content.like(like)))
    if category_id:
        query = query.filter(Blog.type_id == int(category_id))

    query = query.order_by(Blog.is_top.desc(), Blog.create_time.desc())
    pager = query.paginate(page=page, per_page=size, error_out=False)
    return ok({
        'items': [item.to_card() for item in pager.items],
        'page': page,
        'size': size,
        'total': pager.total,
        'pages': pager.pages
    })


@api.route('/blogs/<int:blog_id>')
def blog_detail(blog_id):
    blog = Blog.query.get_or_404(blog_id)
    if blog.is_private:
        user = current_user()
        if user is None or not user.is_admin:
            return fail('文章不存在或无权访问', 404)
    blog.read_times = (blog.read_times or 0) + 1
    db.session.commit()
    return ok(blog.to_detail())


@api.route('/blogs/<int:blog_id>/comments')
def comments(blog_id):
    rows = BlogComment.query.filter_by(blog_id=blog_id, delete_flag=0).order_by(BlogComment.timestamp.desc()).all()
    sentiment_map = {
        item.comment_id: item.to_dict()
        for item in CommentSentiment.query.filter(CommentSentiment.comment_id.in_([row.id for row in rows])).all()
    } if rows else {}
    return ok([row.to_dict(sentiment_map.get(row.id)) for row in rows])


@api.route('/blogs/<int:blog_id>/comments', methods=['POST'])
def create_comment(blog_id):
    user, error = login_required()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    body = (data.get('body') or '').strip()
    if not body:
        return fail('评论内容不能为空')
    if len(body) > 1000:
        return fail('评论内容不能超过 1000 字')

    Blog.query.get_or_404(blog_id)
    comment = BlogComment(body=body, blog_id=blog_id, author_id=user.id, delete_flag=0)
    db.session.add(comment)
    db.session.flush()

    prediction = predict_sentiment(body)
    probs = prediction.get('probabilities') or {}
    sentiment = CommentSentiment(
        comment_id=comment.id,
        label=prediction.get('label', 'neutral'),
        score=float(prediction.get('score', 0)),
        positive=float(probs.get('positive', 0)),
        neutral=float(probs.get('neutral', 0)),
        negative=float(probs.get('negative', 0)),
        raw=dump_raw(prediction.get('raw', prediction))
    )
    db.session.add(sentiment)
    db.session.commit()
    return ok(comment.to_dict(sentiment.to_dict()))


@api.route('/admin/stats')
def admin_stats():
    user, error = admin_required()
    if error:
        return error
    return ok({
        'blogs': Blog.query.count(),
        'comments': BlogComment.query.filter_by(delete_flag=0).count(),
        'users': User.query.count(),
        'categories': BlogType.query.count()
    })


@api.route('/admin/blogs', methods=['POST'])
def admin_create_blog():
    user, error = admin_required()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return fail('标题和正文不能为空')
    category_id = data.get('typeId')
    if category_id is None:
        category = BlogType.query.first()
        if category is None:
            category = BlogType(name='默认分类', description='默认文章分类')
            db.session.add(category)
            db.session.flush()
        category_id = category.id

    blog = Blog(
        title=title,
        content=content,
        type_id=category_id,
        introduce=(data.get('intro') or content[:120]).strip(),
        pre_img=(data.get('cover') or '').strip(),
        is_private=1 if data.get('isPrivate') else 0,
        is_top=1 if data.get('isTop') else 0,
        delete_flag=1
    )
    db.session.add(blog)
    db.session.commit()
    return ok(blog.to_detail())


@api.route('/admin/blogs/<int:blog_id>', methods=['PUT'])
def admin_update_blog(blog_id):
    user, error = admin_required()
    if error:
        return error
    blog = Blog.query.get_or_404(blog_id)
    data = request.get_json(silent=True) or {}
    for field, attr in [('title', 'title'), ('content', 'content'), ('intro', 'introduce'), ('cover', 'pre_img')]:
        if field in data:
            setattr(blog, attr, (data.get(field) or '').strip())
    if 'typeId' in data:
        blog.type_id = data.get('typeId')
    if 'isPrivate' in data:
        blog.is_private = 1 if data.get('isPrivate') else 0
    if 'isTop' in data:
        blog.is_top = 1 if data.get('isTop') else 0
    blog.update_time = datetime.now()
    db.session.commit()
    return ok(blog.to_detail())


@api.route('/admin/blogs/<int:blog_id>', methods=['DELETE'])
def admin_delete_blog(blog_id):
    user, error = admin_required()
    if error:
        return error
    blog = Blog.query.get_or_404(blog_id)
    db.session.delete(blog)
    db.session.commit()
    return ok()


@api.route('/admin/categories', methods=['POST'])
def admin_create_category():
    user, error = admin_required()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return fail('分类名不能为空')
    if BlogType.query.filter_by(name=name).first():
        return fail('分类已经存在')
    category = BlogType(name=name, description=(data.get('description') or '').strip())
    db.session.add(category)
    db.session.commit()
    return ok(category.to_dict())

import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv('.env')


def env(name, default=''):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value


class Config:
    SECRET_KEY = env('SECRET_KEY', 'dev-secret-key')
    JSON_AS_ASCII = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{}:{}@{}/{}?charset=utf8mb4'.format(
        env('DATABASE_USER', 'root'),
        env('DATABASE_PWD', ''),
        env('DATABASE_HOST', 'localhost'),
        env('DATABASE_NAME', 'blog')
    )
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    SUPER_USER_NAME = env('SUPER_USER_NAME', 'admin')
    SUPER_USER_EMAIL = env('SUPER_USER_EMAIL', 'admin@example.com')
    SUPER_USER_PWD = env('SUPER_USER_PWD', '12345678')

    SITE_NAME = env('SITE_NAME', 'Blogin Lab')
    SITE_SUBTITLE = env('SITE_SUBTITLE', '记录技术、想法与实验')
    SITE_OWNER = env('SITE_OWNER', '站点主人')
    SITE_EMAIL = env('SITE_EMAIL', SUPER_USER_EMAIL)
    SITE_URL = env('SITE_URL', 'http://127.0.0.1:5173')
    SITE_START_DATE = env('SITE_START_DATE', '2026-05-09')
    SITE_AVATAR = env('SITE_AVATAR', '')
    SITE_GITHUB_OWNER = env('SITE_GITHUB_OWNER', '')
    SITE_GITHUB_REPO = env('SITE_GITHUB_REPO', '')
    SITE_HERO_TITLE = env('SITE_HERO_TITLE', SITE_NAME)
    SITE_HERO_TEXT = env('SITE_HERO_TEXT', '一个由 Flask API 与 Vue 驱动的现代个人博客。')
    FRONTEND_URL = env('FRONTEND_URL', SITE_URL)
    GITHUB_CLIENT_ID = env('GITHUB_CLIENT_ID', '')
    GITHUB_CLIENT_SECRET = env('GITHUB_CLIENT_SECRET', '')
    GITHUB_REDIRECT_URI = env('GITHUB_REDIRECT_URI', 'http://127.0.0.1:8000/api/auth/github/callback')
    GITHUB_OAUTH_SCOPE = env('GITHUB_OAUTH_SCOPE', 'read:user user:email')
    MODEL_TYPE = env('MODEL_TYPE', '')
    SENTIMENT_SERVICE_URL = env('SENTIMENT_SERVICE_URL', '')

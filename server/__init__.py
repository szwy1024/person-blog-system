import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from server.config import Config
from server.extensions import db
from server.routes import api


def create_app(config_class=Config):
    if isinstance(config_class, str) or config_class is None:
        config_class = Config
    app = Flask(
        __name__,
        static_folder='../frontend/dist',
        static_url_path=''
    )
    app.config.from_object(config_class)

    CORS(app, supports_credentials=True)
    db.init_app(app)
    app.register_blueprint(api, url_prefix='/api')

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def spa(path):
        if path.startswith('api/'):
            return jsonify({'message': 'Not found'}), 404
        if not app.static_folder or not os.path.exists(os.path.join(app.static_folder, 'index.html')):
            return jsonify({
                'message': 'Frontend is served by Vite in development.',
                'url': 'http://127.0.0.1:5173'
            })
        if path and app.static_folder:
            try:
                return send_from_directory(app.static_folder, path)
            except Exception:
                pass
        return send_from_directory(app.static_folder, 'index.html')

    @app.cli.command('initdb')
    def initdb():
        from server.models import Role, States, ThirdParty

        db.create_all()
        Role.ensure_defaults()
        States.ensure_defaults()
        ThirdParty.ensure_defaults()
        print('Database initialized.')

    @app.cli.command('admin')
    def admin():
        from server.models import User, Role

        db.create_all()
        Role.ensure_defaults()
        States = __import__('server.models', fromlist=['States']).States
        ThirdParty = __import__('server.models', fromlist=['ThirdParty']).ThirdParty
        States.ensure_defaults()
        ThirdParty.ensure_defaults()

        email = app.config['SUPER_USER_EMAIL']
        password = app.config['SUPER_USER_PWD']
        username = app.config['SUPER_USER_NAME']

        user = User.query.filter((User.email == email) | (User.username == username)).first()
        if user is None:
            user = User(username=username, email=email, confirm=1, role_id=1)
            user.set_password(password)
            db.session.add(user)
        else:
            user.username = username
            user.email = email
            user.role_id = 1
            user.confirm = 1
            user.set_password(password)
        db.session.commit()
        print('Admin user is ready: {}'.format(email))

    return app

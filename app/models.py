from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Asset(db.Model):
    """
    Tracks every file that lives on ImageKit instead of local disk.

    category:
      - 'static'   → site assets mirrored from the repo's static/ folder
                     (css, js, images, vedio, assets) — local_path is the
                     original relative path e.g. 'css/app.css'
      - 'upload'   → user-uploaded product/reference images
      - 'output'   → AI-generated images/videos from Flux/Kling
    """
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    category      = db.Column(db.String(20), nullable=False, index=True)  # static | upload | output
    subtype       = db.Column(db.String(30), nullable=True)               # e.g. 'product', 'reference', 'image', 'video'
    local_path    = db.Column(db.String(500), nullable=True, index=True)  # relative path, for 'static' category lookups
    imagekit_url  = db.Column(db.String(500), nullable=False)
    imagekit_file_id = db.Column(db.String(100), nullable=True)
    session_id    = db.Column(db.String(100), nullable=True, index=True)
    created_at    = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Asset {self.category}:{self.local_path or self.imagekit_file_id}>'

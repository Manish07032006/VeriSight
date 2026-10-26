"""
SQLAlchemy models matching the project's ER diagram.

Three tables:
  - User        : accounts / login
  - NewsScan     : one row per text submission (fake-news + AI-text verdicts)
  - MediaScan    : one row per image/video submission (deepfake + AI-image verdicts)
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    news_scans = db.relationship("NewsScan", backref="user", lazy=True)
    media_scans = db.relationship("MediaScan", backref="user", lazy=True)

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


class NewsScan(db.Model):
    __tablename__ = "news_scan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    input_text = db.Column(db.Text, nullable=False)

    fake_news_verdict = db.Column(db.String(20), nullable=False)
    fake_news_confidence = db.Column(db.Float, nullable=False)

    ai_text_verdict = db.Column(db.String(20), nullable=False)
    ai_text_confidence = db.Column(db.Float, nullable=False)

    explanation = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "input_text": self.input_text,
            "fake_news_verdict": self.fake_news_verdict,
            "fake_news_confidence": self.fake_news_confidence,
            "ai_text_verdict": self.ai_text_verdict,
            "ai_text_confidence": self.ai_text_confidence,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat(),
        }


class MediaScan(db.Model):
    __tablename__ = "media_scan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    file_path = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(10), nullable=False)
    frames_analyzed = db.Column(db.Integer, nullable=False, default=1)

    deepfake_verdict = db.Column(db.String(20), nullable=False)
    deepfake_confidence = db.Column(db.Float, nullable=False)

    ai_image_verdict = db.Column(db.String(20), nullable=False)
    ai_image_confidence = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "file_path": self.file_path,
            "media_type": self.media_type,
            "frames_analyzed": self.frames_analyzed,
            "deepfake_verdict": self.deepfake_verdict,
            "deepfake_confidence": self.deepfake_confidence,
            "ai_image_verdict": self.ai_image_verdict,
            "ai_image_confidence": self.ai_image_confidence,
            "created_at": self.created_at.isoformat(),
        }
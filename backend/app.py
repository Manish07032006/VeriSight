"""
Main Flask application entry point.

Run with: python app.py
Then visit http://127.0.0.1:5000/ping to confirm everything is wired up.
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from models import db, User, NewsScan, MediaScan
from auth import auth_bp
from inputs import inputs_bp, UPLOAD_FOLDER
from history import history_bp
import model_loader

load_dotenv()

app = Flask(__name__)
CORS(app)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL not set. Create a .env file in this folder with:\n"
        "DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/fake_news_detector"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60 MB hard cap

db.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(inputs_bp)
app.register_blueprint(history_bp)


@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


@app.route("/db-test")
def db_test():
    test_user = User.query.filter_by(username="db_test_user").first()
    if not test_user:
        test_user = User(username="db_test_user", email="test@example.com")
        test_user.set_password("temporary_password")
        db.session.add(test_user)
        db.session.commit()

    return jsonify({
        "message": "Database connection is working.",
        "user": test_user.to_dict(),
    })


# ==============================================================================
# ROUTE: Serves uploaded image/video files so the UI can display previews
# ==============================================================================
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Tables ensured: user, news_scan, media_scan")

    print("Loading backend models onto RTX 3050 GPU...")
    model_loader.load_all_models()

    app.run(debug=True, use_reloader=False)
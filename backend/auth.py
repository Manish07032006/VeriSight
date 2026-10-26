"""
Authentication routes: signup, login, and a decorator to protect other routes.

Uses PyJWT for stateless token-based auth, since the frontend (React) and
backend (Flask) run on different origins/ports.
"""

import os
import datetime
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, current_app

from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _get_secret_key():
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY not set. Add a line to your .env file:\n"
            "JWT_SECRET_KEY=some-long-random-string"
        )
    return secret


def generate_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm="HS256")


def token_required(f):
    """
    Decorator for protecting routes. Expects a header:
      Authorization: Bearer <token>
    Injects the authenticated User object as the first argument.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, _get_secret_key(), algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        current_user = User.query.get(payload["user_id"])
        if not current_user:
            return jsonify({"error": "User no longer exists"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are all required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered"}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    token = generate_token(new_user.id)

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user": new_user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        # deliberately vague, so we don't reveal whether the username exists
        return jsonify({"error": "Invalid username or password"}), 401

    token = generate_token(user.id)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
    """Quick way to test that a token works: returns whoever it belongs to."""
    return jsonify({"user": current_user.to_dict()}), 200
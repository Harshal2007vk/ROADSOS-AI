from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config.settings import settings
import json

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
COOKIE_NAME = "roadsos_session"
MAX_AGE = settings.SESSION_MAX_AGE


def create_session(response: Response, user_id: int, user_name: str, is_admin: bool = False):
    payload = json.dumps({"user_id": user_id, "user_name": user_name, "is_admin": is_admin})
    token = serializer.dumps(payload)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
    )


def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload_str = serializer.loads(token, max_age=MAX_AGE)
        return json.loads(payload_str)
    except (BadSignature, SignatureExpired, Exception):
        return None


def clear_session(response: Response):
    response.delete_cookie(key=COOKIE_NAME)

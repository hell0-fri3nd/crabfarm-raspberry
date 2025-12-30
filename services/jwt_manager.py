import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from os import getenv
from functools import wraps
from flask import request, jsonify, g

class JWTManager:
    def __init__(self):
        load_dotenv()
        self.__secret_key = getenv("JWT_SECRET_KEY")
        self.__algorithm = getenv("JWT_ALGORITHM")

        if not self.__secret_key or not self.__algorithm:
            raise RuntimeError("JWT configuration missing")
    
    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.__secret_key,
                algorithms=[self.__algorithm]
            )

            return payload

        except ExpiredSignatureError:
            raise ValueError("Token expired")
        except InvalidTokenError:
            raise ValueError("Invalid token")
    
    def requires_access(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({
                    "error": "Authorization header missing or invalid"
                }), 401

            token = auth_header.split(" ")[1]

            try:
                payload = self.decode_token(token)
            except ValueError as e:
                return jsonify({"error": str(e)}), 401

            g.user = payload
            return func(*args, **kwargs)

        return wrapper



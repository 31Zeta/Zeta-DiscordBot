"""
Web控制面板认证

登录流程：用户在Discord中使用 /webauth 获取一次性验证码（10分钟内有效，使用一次后失效），
在网页中输入验证码后获得签名的会话Cookie（有效期由 /webauth 的天数参数决定）。
"""
from typing import *
import os
import hmac
import json
import time
import base64
import hashlib
import secrets
import string
import collections

SECRET_KEY_PATH = "./data/web_secret_key"
CODE_TTL_SECONDS = 600
CODE_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
CODE_LENGTH = 8
# 每个IP每分钟最多尝试登录次数
LOGIN_ATTEMPTS_PER_MINUTE = 8


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class WebAuth:
    def __init__(self, secret_path: str = SECRET_KEY_PATH):
        self._secret = self._load_secret(secret_path)
        # 验证码 -> {user_id, username, days, expires}
        self._codes: Dict[str, dict] = {}
        self._attempts: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

    @staticmethod
    def _load_secret(path: str) -> bytes:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                secret = file.read().strip()
            if len(secret) >= 32:
                return secret.encode("utf-8")
        secret = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as file:
            file.write(secret)
        return secret.encode("utf-8")

    def _cleanup(self) -> None:
        now = time.time()
        for code in [code for code, info in self._codes.items() if info["expires"] < now]:
            del self._codes[code]

    def generate_code(self, user_id, username: str, days: int = 3) -> Tuple[str, int]:
        """
        为用户生成一次性登录验证码，同一用户之前的验证码会失效
        返回 (验证码, 有效分钟数)
        """
        self._cleanup()
        for code in [code for code, info in self._codes.items() if info["user_id"] == str(user_id)]:
            del self._codes[code]
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        self._codes[code] = {
            "user_id": str(user_id),
            "username": str(username),
            "days": max(1, min(30, int(days))),
            "expires": time.time() + CODE_TTL_SECONDS,
        }
        return code, CODE_TTL_SECONDS // 60

    def redeem_code(self, code: str) -> Optional[dict]:
        """
        使用验证码，成功时返回用户信息（验证码随即失效）
        """
        self._cleanup()
        code = str(code or "").strip().upper().replace(" ", "").replace("-", "")
        for stored_code in list(self._codes.keys()):
            if hmac.compare_digest(stored_code, code):
                return self._codes.pop(stored_code)
        return None

    def allow_attempt(self, client_key: str) -> bool:
        """
        登录尝试频率限制
        """
        now = time.time()
        attempts = self._attempts[client_key]
        while attempts and now - attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= LOGIN_ATTEMPTS_PER_MINUTE:
            return False
        attempts.append(now)
        return True

    def _sign(self, payload: str) -> str:
        return _b64encode(hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).digest())

    def make_token(self, user_id, username: str, days: int) -> Tuple[str, int]:
        """
        生成签名的会话令牌，返回 (令牌, 有效秒数)
        """
        max_age = int(days) * 86400
        payload = _b64encode(json.dumps({
            "uid": str(user_id),
            "name": str(username),
            "exp": int(time.time()) + max_age,
        }, ensure_ascii=False).encode("utf-8"))
        return f"{payload}.{self._sign(payload)}", max_age

    def verify_token(self, token: Optional[str]) -> Optional[dict]:
        if not token or "." not in token:
            return None
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(self._sign(payload), signature):
            return None
        try:
            data = json.loads(_b64decode(payload).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict) or int(data.get("exp", 0)) < time.time():
            return None
        return {"id": str(data.get("uid")), "name": str(data.get("name"))}

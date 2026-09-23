"""P02 — password hashing (stdlib scrypt), session tokens, login throttling."""
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32
MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algo, n, r, p, salt, expected = encoded.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                            dklen=len(expected) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), expected)


# Used to spend the same time when the email does not exist (no user enumeration by timing).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginThrottle:
    """In-process limiter: max `limit` failures per key within `window` seconds.
    Single-process only; P24 replaces it with a Redis-backed limiter."""

    def __init__(self, limit: int = 5, window: float = 15 * 60):
        self.limit, self.window = limit, window
        self._fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._fails[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._prune(key, time.monotonic())) >= self.limit

    def fail(self, key: str) -> None:
        self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)


throttle = LoginThrottle()

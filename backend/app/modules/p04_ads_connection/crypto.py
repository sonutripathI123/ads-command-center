"""P04 — encryption of OAuth refresh tokens at rest (Fernet: AES-128-CBC + HMAC-SHA256)."""
from cryptography.fernet import Fernet, InvalidToken

from app.modules.p04_ads_connection.config import encryption_key


def encrypt(plaintext: str) -> str:
    return Fernet(encryption_key()).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return Fernet(encryption_key()).decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise RuntimeError("Stored credential cannot be decrypted (encryption key changed?)") from e

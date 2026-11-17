import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


TAG = b"SEC3"
SALT_SIZE = 16
NONCE_SIZE = 12
HEADER_SIZE = 40
AES_TAG_SIZE = 16


def _make_key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Для шифрования требуется пароль.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=260_000,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_packet(data: bytes, password: str, packet_size: int | None = None) -> bytes:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _make_key(password, salt)

    encrypted_size = len(data) + AES_TAG_SIZE
    minimum_size = HEADER_SIZE + encrypted_size
    total_size = minimum_size if packet_size is None else packet_size
    if total_size < minimum_size:
        raise ValueError("Заданный размер пакета слишком мал для AES-GCM.")

    header = (
        TAG
        + salt
        + nonce
        + encrypted_size.to_bytes(4, "big")
        + total_size.to_bytes(4, "big")
    )
    encrypted = AESGCM(key).encrypt(nonce, data, header)
    padding = bytes(total_size - len(header) - len(encrypted))
    return header + encrypted + padding


def decrypt_packet(packet: bytes, password: str) -> bytes:
    if len(packet) < HEADER_SIZE or packet[:4] != TAG:
        raise ValueError("Пакет AES-GCM не найден или повреждён.")

    salt = packet[4:20]
    nonce = packet[20:32]
    encrypted_size = int.from_bytes(packet[32:36], "big")
    declared_size = int.from_bytes(packet[36:40], "big")

    if declared_size != len(packet) or encrypted_size < AES_TAG_SIZE:
        raise ValueError("Неверная длина зашифрованного пакета.")
    if HEADER_SIZE + encrypted_size > len(packet):
        raise ValueError("Зашифрованные данные обрезаны.")

    encrypted = packet[HEADER_SIZE:HEADER_SIZE + encrypted_size]
    padding = packet[HEADER_SIZE + encrypted_size:]
    if any(padding):
        raise ValueError("Служебное дополнение пакета повреждено.")

    key = _make_key(password, salt)
    return AESGCM(key).decrypt(nonce, encrypted, packet[:HEADER_SIZE])

from array import array
import hashlib
import random
from pathlib import Path

import numpy as np
from PIL import Image

from .crypto_box import TAG as ENCRYPTED_TAG, encrypt_packet, decrypt_packet, HEADER_SIZE


PLAIN_TAG = b"TXT3"
PLAIN_HEADER_SIZE = 12


def to_bits(data: bytes):
    for byte in data:
        for shift in range(7, -1, -1):
            yield (byte >> shift) & 1


def to_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8:
        raise ValueError("Длина последовательности бит должна делиться на 8.")

    result = bytearray()
    for start in range(0, len(bits), 8):
        value = 0
        for bit in bits[start:start + 8]:
            value = (value << 1) | bit
        result.append(value)
    return bytes(result)


def _positions(total: int, mixed: bool, password: str | None):
    if not mixed:
        return range(total)
    if not password:
        raise ValueError("Для случайного порядка требуется пароль.")

    seed_data = hashlib.sha256(password.encode("utf-8")).digest()[:8]
    seed = int.from_bytes(seed_data, "big")
    indexes = array("I", range(total))
    random.Random(seed).shuffle(indexes)
    return indexes


def _make_plain_packet(text: str, packet_size: int | None = None) -> bytes:
    data = text.encode("utf-8")
    min_size = PLAIN_HEADER_SIZE + len(data)
    total_size = min_size if packet_size is None else packet_size
    if total_size < min_size:
        raise ValueError("Заданный размер пакета слишком мал для сообщения.")

    header = PLAIN_TAG + len(data).to_bytes(4, "big") + total_size.to_bytes(4, "big")
    return header + data + bytes(total_size - min_size)


def _write_packet(cover_path: str, output_path: str, packet: bytes,
                  mixed: bool = False, password: str | None = None) -> int:
    with Image.open(cover_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()

    flat = rgb.reshape(-1)
    needed = len(packet) * 8
    if needed > flat.size:
        available = flat.size // 8
        raise ValueError(
            f"Сообщение не помещается: требуется {needed} бит, "
            f"доступно {flat.size} бит (около {available} байт)."
        )

    order = _positions(flat.size, mixed, password)
    for bit, index in zip(to_bits(packet), order):
        old_value = int(flat[index])
        flat[index] = (old_value & 254) | bit

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(flat.reshape(rgb.shape)).save(destination, format="PNG")
    return needed


def _read_bytes(flat: np.ndarray, order, start: int, count: int) -> bytes:
    last_bit = start + count * 8
    if last_bit > len(order):
        raise ValueError("Изображение содержит не весь заголовок или пакет.")

    bits = [int(flat[order[pos]]) & 1 for pos in range(start, last_bit)]
    return to_bytes(bits)


def _read_packet(image_path: str, mixed: bool = False,
                 password: str | None = None) -> bytes:
    with Image.open(image_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)

    flat = rgb.reshape(-1)
    order = _positions(flat.size, mixed, password)
    signature = _read_bytes(flat, order, 0, 4)

    if signature == PLAIN_TAG:
        header_size = PLAIN_HEADER_SIZE
        header = _read_bytes(flat, order, 0, header_size)
        total_size = int.from_bytes(header[8:12], "big")
    elif signature == ENCRYPTED_TAG:
        header_size = HEADER_SIZE
        header = _read_bytes(flat, order, 0, header_size)
        total_size = int.from_bytes(header[36:40], "big")
    else:
        raise ValueError("Скрытые данные не найдены. Проверьте файл и порядок позиций.")

    if total_size < header_size or total_size * 8 > flat.size:
        raise ValueError("В заголовке указана недопустимая длина сообщения.")
    return _read_bytes(flat, order, 0, total_size)


def hide_text(cover_path: str, output_path: str, text: str,
              password: str | None = None, mixed: bool = False,
              packet_size: int | None = None) -> int:
    if password:
        packet = encrypt_packet(text.encode("utf-8"), password, packet_size)
    else:
        if mixed:
            raise ValueError("Случайное размещение доступно вместе с паролем.")
        packet = _make_plain_packet(text, packet_size)

    return _write_packet(cover_path, output_path, packet, mixed, password)


def reveal_text(image_path: str, password: str | None = None,
                mixed: bool = False) -> str:
    packet = _read_packet(image_path, mixed, password)

    if packet[:4] == PLAIN_TAG:
        text_size = int.from_bytes(packet[4:8], "big")
        data = packet[PLAIN_HEADER_SIZE:PLAIN_HEADER_SIZE + text_size]
    else:
        if not password:
            raise ValueError("Для расшифрования сообщения введите пароль.")
        data = decrypt_packet(packet, password)

    return data.decode("utf-8")

from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
from cryptography.exceptions import InvalidTag

from src.image_channel import hide_text, reveal_text


def test_all_modes() -> None:
    rng = np.random.default_rng(2026)
    cover = rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)
    message = "Проверка LSB: текст должен восстановиться полностью."
    password = "test-password-2026"

    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        source = base / "cover.png"
        Image.fromarray(cover).save(source)

        modes = (
            ("plain.png", None, False),
            ("encrypted.png", password, False),
            ("random.png", password, True),
        )
        for filename, key, random_order in modes:
            output = base / filename
            hide_text(str(source), str(output), message, key, random_order)
            assert reveal_text(str(output), key, random_order) == message

        try:
            reveal_text(str(base / "encrypted.png"), "wrong-password")
        except InvalidTag:
            pass
        else:
            raise AssertionError("Неверный пароль не должен расшифровывать пакет")

        try:
            hide_text(str(source), str(base / "too_large.png"), "X" * 50_000)
        except ValueError:
            pass
        else:
            raise AssertionError("Проверка вместимости не обнаружила переполнение")


if __name__ == "__main__":
    test_all_modes()
    print("Все проверки пройдены.")

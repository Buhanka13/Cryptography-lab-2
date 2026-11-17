import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from .image_channel import hide_text, reveal_text
from .statistics import (
    cover_statistics,
    image_metrics,
    load_rgb,
    save_difference,
    save_histogram,
)


ROOT = Path(__file__).resolve().parents[1]
IMGS = ROOT / "imgs"
RESULTS = ROOT / "results"

PASSWORD = "lab-password-demo-2026"
PACKET_OVERHEAD = 56
PAYLOAD_RATES = (0.01, 0.05)

IMAGE_NAMES = ("cover.png", "gradient.png")

METHODS = (
    ("Plain LSB", None, False, "stego_plain.png"),
    ("Encrypted LSB", PASSWORD, False, "stego_encrypted.png"),
    ("Encrypted Random LSB", PASSWORD, True, "stego_random.png"),
)

COLUMNS = (
    "Вариант",
    "Пакет, байт",
    "Пакет, бит",
    "PSNR, dB",
    "SSIM",
    "Изменено компонент",
    "Changed ratio",
    "P(LSB=0)",
    "P(LSB=1)",
    "χ²",
    "p-value",
)


def make_text(component_count: int, fill_rate: float) -> tuple[str, int]:
    if not 0 < fill_rate < 1:
        raise ValueError("Уровень заполнения должен быть между 0 и 1.")

    packet_size = int(component_count * fill_rate / 8)
    text_size = packet_size - PACKET_OVERHEAD
    if text_size <= 0:
        raise ValueError("Изображение слишком мало для выбранного payload.")

    phrase = b"LSB experiment: the same message is embedded in every method. "
    message = (phrase * ((text_size + len(phrase) - 1) // len(phrase)))[:text_size]
    return message.decode("ascii"), packet_size


def write_csv(path: Path, columns: tuple | list, rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(columns)
        writer.writerows(rows)


def format_probability(value: float) -> str:
    return "<1e-300" if value == 0 else f"{value:.3e}"


def result_row(name: str, metrics: dict, packet_size: int | None) -> list:
    if packet_size is None: 
        packet_bytes, packet_bits = "—", "—"
        psnr, ssim = "—", "—"
    else:
        packet_bytes = packet_size
        packet_bits = packet_size * 8
        psnr = f"{metrics['PSNR']:.3f}"
        ssim = f"{metrics['SSIM']:.6f}"

    return [
        name,
        packet_bytes,
        packet_bits,
        psnr,
        ssim,
        metrics.get("changed_components", 0),
        f"{metrics.get('changed_ratio', 0.0):.8f}",
        f"{metrics['P_LSB_0']:.6f}",
        f"{metrics['P_LSB_1']:.6f}",
        f"{metrics['chi_square']:.4f}",
        format_probability(metrics["p_value"]),
    ]


def run_methods(
    image_path: Path,
    message: str,
    packet_size: int,
    output_dir: Path,
    save_images: bool = False,
) -> list[list]:
    cover = load_rgb(image_path)
    rows = []

    for title, password, random_order, filename in METHODS:
        output_path = output_dir / filename
        hide_text(
            str(image_path),
            str(output_path),
            message,
            password=password,
            mixed=random_order,
            packet_size=packet_size,
        )

        restored = reveal_text(
            str(output_path),
            password=password,
            mixed=random_order,
        )
        if restored != message:
            raise RuntimeError(f"Извлечённое сообщение не совпало: {title}.")

        stego = load_rgb(output_path)
        metrics = image_metrics(cover, stego)
        rows.append(result_row(title, metrics, packet_size))
        print(f"[OK] {image_path.name}: {title}, {packet_size * 8} бит")

        if save_images and title == "Plain LSB":
            save_difference(cover, stego, RESULTS / "difference.png")
            save_histogram(cover, stego, RESULTS / "histogram.png")

        if not save_images:
            output_path.unlink(missing_ok=True)

    return rows


def run_image_comparison() -> list[list]:
    rows = []
    for image_name in IMAGE_NAMES:
        image_path = IMGS / image_name
        if not image_path.is_file():
            raise FileNotFoundError(f"Не найдено изображение: {image_path}")

        cover = load_rgb(image_path)
        message, packet_size = make_text(cover.size, PAYLOAD_RATES[0])
        baseline = cover_statistics(cover)
        rows.append([image_name, *result_row("Cover", baseline, None)])

        if image_name == "cover.png":
            rows.extend(
                [image_name, *row]
                for row in run_methods(
                    image_path, message, packet_size, IMGS, save_images=True
                )
            )
        else:
            with TemporaryDirectory() as temp_dir:
                rows.extend(
                    [image_name, *row]
                    for row in run_methods(
                        image_path,
                        message,
                        packet_size,
                        Path(temp_dir),
                    )
                )

    return rows


def run_payload_comparison() -> list[list]:
    image_path = IMGS / "cover.png"
    cover = load_rgb(image_path)
    rows = []

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for rate in PAYLOAD_RATES:
            message, packet_size = make_text(cover.size, rate)
            method_rows = run_methods(
                image_path,
                message,
                packet_size,
                temp_path,
            )
            rows.extend([[f"{rate:.0%}", *row] for row in method_rows])

    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    for image_name in IMAGE_NAMES:
        image_path = IMGS / image_name
        if not image_path.is_file():
            raise FileNotFoundError(
                f"Не найдено {image_path}. Поместите собственное PNG в imgs/cover.png "
                "и используйте imgs/gradient.png как второе изображение."
            )
        with Image.open(image_path) as image:
            if image.format != "PNG":
                raise ValueError(f"Файл {image_path.name} должен быть PNG.")
            if image_name == "cover.png" and min(image.size) < 256:
                raise ValueError("Собственное изображение должно быть не меньше 256×256.")

    print("Запуск лабораторного эксперимента")
    comparison_rows = run_image_comparison()
    payload_rows = run_payload_comparison()

    write_csv(
        RESULTS / "metrics.csv",
        ["Изображение", *COLUMNS],
        comparison_rows,
    )
    write_csv(
        RESULTS / "payload_levels.csv",
        ["Заполнение", *COLUMNS],
        payload_rows,
    )
    print("Готово: таблицы и визуализации сохранены в results/.")


if __name__ == "__main__":
    main()

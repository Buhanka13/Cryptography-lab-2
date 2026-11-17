from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.stats import chi2
from skimage.metrics import structural_similarity


def load_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def paired_chi_square(values: np.ndarray) -> tuple[float, float]:
    frequencies = np.bincount(values.reshape(-1), minlength=256).reshape(128, 2).astype(float)
    totals = frequencies.sum(axis=1)
    nonempty = totals > 0
    expected = totals[nonempty, None] / 2.0
    observed = frequencies[nonempty]

    statistic = float(np.sum((observed - expected) ** 2 / expected))
    degrees = int(np.count_nonzero(nonempty))
    probability = float(chi2.sf(statistic, degrees)) if degrees else 1.0
    return statistic, probability


def image_metrics(cover: np.ndarray, stego: np.ndarray) -> dict:
    difference = cover.astype(np.int16) - stego.astype(np.int16)
    mse = float(np.mean(difference.astype(np.float64) ** 2))
    psnr = float("inf") if mse == 0 else 10 * np.log10((255 ** 2) / mse)
    ssim = float(structural_similarity(cover, stego, channel_axis=2, data_range=255))

    flat = stego.reshape(-1)
    changed_count = int(np.count_nonzero(difference))
    component_count = int(cover.size)
    p_one = float(np.mean(flat & 1))
    chi_value, p_value = paired_chi_square(flat)

    return {
        "PSNR": psnr,
        "SSIM": ssim,
        "changed_components": changed_count,
        "changed_ratio": changed_count / component_count,
        "P_LSB_0": 1.0 - p_one,
        "P_LSB_1": p_one,
        "chi_square": chi_value,
        "p_value": p_value,
    }


def cover_statistics(cover: np.ndarray) -> dict:
    flat = cover.reshape(-1)
    p_one = float(np.mean(flat & 1))
    chi_value, p_value = paired_chi_square(flat)
    return {
        "P_LSB_0": 1.0 - p_one,
        "P_LSB_1": p_one,
        "chi_square": chi_value,
        "p_value": p_value,
    }


def save_difference(cover: np.ndarray, stego: np.ndarray, path: str | Path) -> None:
    diff = np.abs(cover.astype(np.int16) - stego.astype(np.int16))
    visible = np.clip(diff * 255, 0, 255).astype(np.uint8)
    Image.fromarray(visible).save(path)


def save_histogram(cover: np.ndarray, stego: np.ndarray, path: str | Path) -> None:
    plt.figure(figsize=(10, 4.5))
    plt.hist(cover.reshape(-1), bins=256, range=(0, 256), alpha=0.55, label="Cover")
    plt.hist(stego.reshape(-1), bins=256, range=(0, 256), alpha=0.55, label="Stego")
    plt.xlabel("Значение RGB-компоненты")
    plt.ylabel("Количество компонент")
    plt.title("Распределение значений до и после встраивания")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

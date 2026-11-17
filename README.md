# Лабораторная работа №2 — стеганография и статистический анализ

## Требования

Python 3.10 или новее.

Установка библиотек:

```bash
python -m pip install -r requirements.txt
```

## Изображения

В `imgs/` должны находиться:

- `cover.png` — собственное RGB/PNG-изображение размером не менее 256×256;
- `gradient.png` — второе изображение для сравнения с другим типом содержимого.

`checkerboard.png` и `noise_texture.png` оставлены в папке как дополнительные исходные примеры, но для запуска эксперимента не нужны.

## Запуск эксперимента

Из корневой папки проекта:

```bash
python -m src.experiment
```

Скрипт выполняет:

1. сравнение Plain LSB, Encrypted LSB и Encrypted Random LSB на `cover.png` и `gradient.png`;
2. измерение PSNR, SSIM, числа и доли изменённых компонент, распределения LSB и χ²;
3. сравнение уровней заполнения 1% и 5% на `cover.png`;
4. сохранение карты разности и гистограммы для Plain LSB.

Результаты сохраняются в `results/`:

- `metrics.csv` — статистика для двух изображений, включая исходные Cover;
- `payload_levels.csv` — влияние размера сообщения;
- `difference.png` — усиленная карта разности;
- `histogram.png` — гистограмма RGB-компонент.

Три итоговых изображения записываются в `imgs/stego_plain.png`, `imgs/stego_encrypted.png` и `imgs/stego_random.png`.

В зашифрованных режимах `salt` и `nonce` генерируются заново, поэтому численные метрики этих режимов могут немного отличаться при повторном запуске.

## Ручное встраивание и извлечение

Обычный LSB:

```bash
python -m src.cli hide --input imgs/cover.png --output imgs/plain_demo.png --text "Тестовое сообщение"
python -m src.cli read --input imgs/plain_demo.png
```

Шифрование AES-GCM перед встраиванием:

```bash
python -m src.cli hide --input imgs/cover.png --output imgs/encrypted_demo.png --text "Секретный текст" --password "my-password"
python -m src.cli read --input imgs/encrypted_demo.png --password "my-password"
```

Шифрование с псевдослучайным порядком позиций:

```bash
python -m src.cli hide --input imgs/cover.png --output imgs/random_demo.png --text "Текст в случайных позициях" --password "my-password" --random
python -m src.cli read --input imgs/random_demo.png --password "my-password" --random
```

Для извлечения зашифрованного сообщения и воспроизведения случайного порядка нужен тот же пароль.

## Проверка

```bash
python -m tests.test_stego
```

## Криптографический формат

Для зашифрованного режима используется AES-256-GCM. Ключ выводится из пароля с помощью PBKDF2-HMAC-SHA256; для каждого пакета генерируются случайные salt и nonce. Формат пакета содержит сигнатуру, salt, nonce и длины данных. Режим Random использует воспроизводимую перестановку позиций, зависящую от пароля.

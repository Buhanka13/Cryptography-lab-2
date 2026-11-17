import argparse

from .image_channel import hide_text, reveal_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скрывает текст в PNG с помощью RGB-компонент."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    hide = commands.add_parser("hide", help="спрятать текст")
    hide.add_argument("--input", required=True, help="исходное PNG")
    hide.add_argument("--output", required=True, help="куда сохранить stego PNG")
    hide.add_argument("--text", required=True, help="текст для сокрытия")
    hide.add_argument("--password", help="пароль включает AES-GCM")
    hide.add_argument("--random", action="store_true", help="перемешать позиции")

    read = commands.add_parser("read", help="извлечь текст")
    read.add_argument("--input", required=True, help="PNG со скрытым сообщением")
    read.add_argument("--password", help="пароль для расшифрования")
    read.add_argument("--random", action="store_true", help="использовать тот же порядок позиций")

    args = parser.parse_args()
    try:
        if args.command == "hide":
            count = hide_text(
                args.input, args.output, args.text,
                password=args.password, mixed=args.random,
            )
            print(f"Готово: записано {count} бит в {args.output}")
        else:
            text = reveal_text(args.input, password=args.password, mixed=args.random)
            print("Извлечённый текст:")
            print(text)
    except Exception as error:
        parser.exit(1, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()

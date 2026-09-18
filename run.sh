if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    echo -e "\033[31m[!] ОШИБКА: Запущена сессия Wayland. Захват экрана через mss заблокирован.\033[0m"
    echo -e "Выполните на хосте: steamosctl set-default-desktop-session plasmax11.desktop"
    echo -e "Затем перезапустите сессию рабочего стола."
    exit 1
fi

#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py"

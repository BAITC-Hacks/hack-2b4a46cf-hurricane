"""Local setup and run in one command, works on Windows, macOS and Linux (stdlib only).

python dev.py            # check tools, prepare .env, start everything, wait for /health
python dev.py down       # stop containers (add -v to drop the database)
python dev.py logs app   # follow logs of a service
python dev.py status     # docker compose ps
python dev.py check      # only the tools table
"""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
DEFAULT_PORTS = {"APP_PORT": 8000, "UI_PORT": 5173, "DB_PORT": 5432}
PLACEHOLDERS = {"OPENAI_API_KEY": "sk-..."}
IS_WINDOWS = platform.system() == "Windows"

INSTALL_HINTS = {
    "git": ("brew install git", "winget install Git.Git"),
    "docker": ("brew install --cask docker", "winget install Docker.DockerDesktop"),
    "node": ("brew install node@22", "winget install OpenJS.NodeJS.LTS"),
    "yarn": ("npm i -g yarn@1", "npm i -g yarn@1"),
    "uv": ("brew install uv", "winget install astral-sh.uv"),
    "railway": ("brew install railway", "npm i -g @railway/cli"),
}


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    executable = shutil.which(args[0])
    if executable is None:
        raise FileNotFoundError(args[0])
    sys.stdout.flush()  # keep our prints ordered with the child's output
    return subprocess.run([executable, *args[1:]], text=True, **kwargs)


def version_of(args: list[str]) -> str | None:
    try:
        result = run(args, capture_output=True, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if result.returncode == 0 and output else None


def detect_compose() -> list[str] | None:
    for candidate in (["docker", "compose"], ["podman", "compose"], ["docker-compose"]):
        if version_of([*candidate, "version"]):
            return candidate
    return None


def hint_for(tool: str) -> str:
    mac_hint, windows_hint = INSTALL_HINTS[tool]
    return windows_hint if IS_WINDOWS else mac_hint


def check_tools(compose: list[str] | None) -> None:
    rows = [
        ("git", version_of(["git", "--version"]), True),
        ("compose", version_of([*compose, "version"]) if compose else None, True),
        ("node", version_of(["node", "--version"]), False),
        ("yarn", version_of(["yarn", "--version"]), False),
        ("uv", version_of(["uv", "--version"]), False),
        ("railway", version_of(["railway", "--version"]), False),
    ]
    print("\nИнструменты:")
    for name, version, required in rows:
        mark = "[ok]" if version else ("[!!]" if required else "[--]")
        note = version or ("нужен: " + hint_for("docker" if name == "compose" else name))
        print(f"  {mark} {name:<8} {note}")
    print("  Обязательны git и compose. Остальное для работы без Docker и для деплоя.")


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def is_port_busy(port: int) -> bool:
    """Checks both IPv4 and IPv6 loopback: Docker/Podman proxies often listen on IPv6 only."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.5)
                if probe.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def free_port_near(port: int) -> int:
    candidate = port + 10
    while is_port_busy(candidate):
        candidate += 1
    return candidate


def set_env_value(key: str, value: str) -> None:
    """Rewrites `KEY=...` in .env in place, or appends it when the key is absent."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key and not line.lstrip().startswith("#"):
            lines[index] = f"{key}={value}"
            replaced = True
    if not replaced:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_stack_running(compose: list[str]) -> bool:
    listing = run([*compose, "ps", "-q"], cwd=ROOT, capture_output=True)
    return listing.returncode == 0 and bool(listing.stdout.strip())


def assign_free_ports(values: dict[str, str]) -> None:
    reassigned = False
    for key, default in DEFAULT_PORTS.items():
        configured = int(values.get(key) or default)
        if not is_port_busy(configured):
            continue
        if configured != default:
            sys.exit(f"Порт {configured} из {key} в .env занят. Укажите другой порт и повторите.")
        new_port = free_port_near(default)
        values[key] = str(new_port)
        set_env_value(key, str(new_port))
        reassigned = True
        print(f"  порт {default} занят, {key} переназначен на {new_port} (записано в .env)")
    if not reassigned:
        return
    # The frontend and CORS point at host ports, so they move together with the ports.
    derived = {
        "VITE_API_URL": f"http://localhost:{values.get('APP_PORT') or DEFAULT_PORTS['APP_PORT']}",
        "CORS_ORIGINS": f"http://localhost:{values.get('UI_PORT') or DEFAULT_PORTS['UI_PORT']}",
    }
    for key, value in derived.items():
        values[key] = value
        set_env_value(key, value)
        print(f"  {key}={value} (записано в .env)")


def prepare_env(compose: list[str]) -> dict[str, str]:
    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print(f"\n.env создан из .env.example: {ENV_FILE}")
    values = read_env()
    # A running stack of this project already holds its ports: a rerun must reuse them, not move.
    if is_stack_running(compose):
        print("  контейнеры проекта уже запущены, порты из .env сохранены")
    else:
        assign_free_ports(values)

    missing = [
        key for key, placeholder in PLACEHOLDERS.items() if values.get(key, "") in ("", placeholder)
    ]
    if missing:
        print(f"  в .env не заполнены: {', '.join(missing)}.")
        print("  Стек поднимется, но объяснения будут шаблонными, а поиск по смыслу описания выключен.")
    return values


def enable_git_hooks() -> None:
    try:
        run(["git", "config", "core.hooksPath", ".githooks"], cwd=ROOT, check=True)
        print("\nGit-хук на сообщения коммитов включён (.githooks).")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("\nНе удалось включить git-хуки. Вручную: git config core.hooksPath .githooks")


def wait_for_health(port: int, timeout_seconds: int = 180) -> bool:
    url = f"http://localhost:{port}/health"
    print(f"\nЖду {url} ...", end="", flush=True)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    print(" ok")
                    return True
        except OSError:
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print(" не дождался")
    return False


def compose_up(compose: list[str]) -> None:
    if compose[0] == "podman":
        podman_info = run(["podman", "info"], capture_output=True)
        if podman_info.returncode != 0:
            sys.exit("Podman не отвечает. Запустите машину: podman machine start")
    check_tools(compose)
    enable_git_hooks()
    values = prepare_env(compose)
    print("\nСборка и запуск контейнеров (первый раз 2–4 минуты)...")
    run([*compose, "up", "--build", "-d"], cwd=ROOT, check=True)
    app_port = int(values.get("APP_PORT") or DEFAULT_PORTS["APP_PORT"])
    ui_port = int(values.get("UI_PORT") or DEFAULT_PORTS["UI_PORT"])
    healthy = wait_for_health(app_port)
    run([*compose, "ps", "-a"], cwd=ROOT)
    if not healthy:
        run([*compose, "logs", "--tail", "40", "app", "migrate"], cwd=ROOT)
        sys.exit("API не поднялся. Логи выше. Повторить: python dev.py")
    print(
        f"\nГотово.\n  UI:   http://localhost:{ui_port}\n  API:  http://localhost:{app_port}/docs\n"
        "  Остановить: python dev.py down    Логи: python dev.py logs app"
    )


def main(argv: list[str]) -> None:
    command, *rest = argv or ["up"]
    compose = detect_compose()
    if command == "check":
        check_tools(compose)
        return
    if compose is None:
        check_tools(None)
        sys.exit("\nНужен Docker Desktop или Podman Desktop с Compose.")
    if command == "up":
        compose_up(compose)
    elif command == "down":
        run([*compose, "down", *rest], cwd=ROOT, check=True)
    elif command == "logs":
        run([*compose, "logs", "-f", "--tail", "100", *rest], cwd=ROOT)
    elif command == "status":
        run([*compose, "ps", "-a"], cwd=ROOT)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    if sys.version_info < (3, 9):  # noqa: UP036  script must fail nicely on old Pythons
        sys.exit("Нужен Python 3.9 или новее.")
    if IS_WINDOWS:
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(130)
    except subprocess.CalledProcessError as error:
        sys.exit(f"Команда завершилась с ошибкой: {' '.join(error.cmd)}")

"""Adiciona ou remove o Whisper Microfone do startup do Windows.

Grava uma entrada no registro:
  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

Uso:
    python scripts/add_to_startup.py           # adiciona ao startup
    python scripts/add_to_startup.py --remove  # remove do startup
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_APP_NAME = "WhisperMicrofone"
_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _run_bat_path() -> Path:
    """Caminho absoluto para run.bat na raiz do projeto."""
    return Path(__file__).parent.parent / "run.bat"


def _startup_command(run_bat: Path) -> str:
    """Comando gravado no registro — abre minimizado sem janela de console visivel."""
    return f'cmd /c start /min "" "{run_bat}"'


def _add_startup(run_bat: Path) -> None:
    try:
        import winreg
    except ImportError:
        print("[ERRO] winreg nao disponivel. Este script requer Windows.", file=sys.stderr)
        sys.exit(1)

    if not run_bat.exists():
        print(f"[ERRO] run.bat nao encontrado em: {run_bat}", file=sys.stderr)
        sys.exit(1)

    command = _startup_command(run_bat)

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
    except OSError as exc:
        print(f"[ERRO] Nao foi possivel gravar no registro: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Startup adicionado com sucesso.")
    print(f"  Chave : HKCU\\{_REGISTRY_KEY}")
    print(f"  Nome  : {_APP_NAME}")
    print(f"  Valor : {command}")
    print()
    print("O Whisper Microfone sera iniciado automaticamente no proximo login do Windows.")


def _remove_startup() -> None:
    try:
        import winreg
    except ImportError:
        print("[ERRO] winreg nao disponivel. Este script requer Windows.", file=sys.stderr)
        sys.exit(1)

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        print(f"Entrada '{_APP_NAME}' removida do startup do Windows.")
    except FileNotFoundError:
        print(f"Entrada '{_APP_NAME}' nao encontrada no registro. Nenhuma acao necessaria.")
    except OSError as exc:
        print(f"[ERRO] Nao foi possivel remover do registro: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adiciona ou remove o Whisper Microfone do startup do Windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python scripts/add_to_startup.py           # adiciona\n"
            "  python scripts/add_to_startup.py --remove  # remove\n"
        ),
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove a entrada de startup do registro em vez de adicionar.",
    )
    args = parser.parse_args()

    if args.remove:
        _remove_startup()
    else:
        _add_startup(_run_bat_path())


if __name__ == "__main__":
    main()

"""
build_exe.py — Empacota whisper-microfone como executável Windows via PyInstaller.

Uso:
    python scripts/build_exe.py              # one-dir (dist/whisper-microfone/)
    python scripts/build_exe.py --onefile    # one-file (dist/whisper-microfone.exe)
    python scripts/build_exe.py --debug      # mantém janela de console

Requer PyInstaller instalado no ambiente ativo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent.resolve()
ENTRY_POINT = ROOT / "src" / "whisper_microfone" / "__main__.py"
ICON = ROOT / "assets" / "icon.ico"
DEFAULTS_SRC = ROOT / "src" / "whisper_microfone" / "config" / "defaults"
ASSETS_SRC = ROOT / "assets"


# ---------------------------------------------------------------------------
# Arg builder
# ---------------------------------------------------------------------------

def get_pyinstaller_args(onefile: bool, debug: bool) -> list[str]:
    """Retorna a lista de argumentos para PyInstaller.__main__.run()."""

    args: list[str] = [
        str(ENTRY_POINT),
        "--name=whisper-microfone",
        "--distpath=dist",
        "--workpath=build",
        "--specpath=.",
        "--noconfirm",          # sobrescreve sem perguntar
        "--clean",              # limpa cache de build anterior
    ]

    # Console / windowed
    if debug:
        args.append("--console")
    else:
        args.append("--noconsole")

    # One-file vs one-dir
    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    # Ícone — apenas se o arquivo existir
    if ICON.is_file():
        args.append(f"--icon={ICON}")
    else:
        print(f"[build] Aviso: {ICON} não encontrado — build sem ícone.")

    # --add-data: config/defaults
    # Separador Windows = ";"
    if DEFAULTS_SRC.is_dir():
        args.append(
            f"--add-data={DEFAULTS_SRC};whisper_microfone/config/defaults"
        )
    else:
        print(f"[build] Aviso: {DEFAULTS_SRC} não encontrado — defaults não empacotados.")

    # --add-data: assets (sons, ícones, etc.)
    if ASSETS_SRC.is_dir():
        args.append(f"--add-data={ASSETS_SRC};assets")

    # Hidden imports necessários
    hidden_imports = [
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pyperclip",
        "sounddevice",
        "silero_vad",
        "torch",
        "groq",
        "soundfile",
        "loguru",
        "pydantic",
        "watchdog",
        "watchdog.observers",
        "watchdog.events",
    ]
    for module in hidden_imports:
        args.append(f"--hidden-import={module}")

    # Exclusões — reduzem tamanho sem impacto funcional
    excludes = [
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
    ]
    for module in excludes:
        args.append(f"--exclude-module={module}")

    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Empacota whisper-microfone como executável Windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/build_exe.py                  # one-dir, sem console
  python scripts/build_exe.py --onefile        # .exe único
  python scripts/build_exe.py --onefile --debug  # .exe único com console
""",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        default=False,
        help="Gera um único .exe portátil (inicialização mais lenta).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Mantém a janela de console para ver logs em tempo real.",
    )
    args = parser.parse_args()

    # Garante que src/ está no path para eventuais imports durante o build
    src_path = str(ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    pyinstaller_args = get_pyinstaller_args(
        onefile=args.onefile,
        debug=args.debug,
    )

    mode = "one-file" if args.onefile else "one-dir"
    console = "com console" if args.debug else "sem console"
    print(f"[build] Iniciando build — modo: {mode}, {console}")
    print(f"[build] Entry point : {ENTRY_POINT}")
    print(f"[build] Root        : {ROOT}")
    print("[build] Args PyInstaller:")
    for arg in pyinstaller_args:
        print(f"         {arg}")
    print()

    try:
        import PyInstaller.__main__ as pyi_main  # noqa: PLC0415
    except ImportError:
        print("[build] ERRO: PyInstaller não encontrado.")
        print("        Instale com: pip install pyinstaller")
        sys.exit(1)

    pyi_main.run(pyinstaller_args)

    # Localiza e informa o artefato gerado
    print()
    if args.onefile:
        exe = ROOT / "dist" / "whisper-microfone.exe"
        if exe.is_file():
            size_mb = exe.stat().st_size / (1024 * 1024)
            print(f"[build] Concluido! Executavel: {exe}  ({size_mb:.1f} MB)")
        else:
            print(f"[build] Concluido! Executavel esperado em: {exe}")
    else:
        out_dir = ROOT / "dist" / "whisper-microfone"
        exe = out_dir / "whisper-microfone.exe"
        if exe.is_file():
            print(f"[build] Concluido! Pasta: {out_dir}")
            print(f"[build] Executavel  : {exe}")
        else:
            print(f"[build] Concluido! Pasta esperada em: {out_dir}")


if __name__ == "__main__":
    main()

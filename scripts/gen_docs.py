"""Gera docs/CONFIG.md e docs/CONFIG.en.md a partir dos schemas Pydantic.

Uso:
    python scripts/gen_docs.py

Os arquivos são sempre sobrescritos — nunca edite manualmente.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Garante que src/ está no path ao rodar como script
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from pydantic.fields import FieldInfo  # noqa: E402

from whisper_microfone.config.schemas import (  # noqa: E402
    AdvancedConfig,
    AppConfig,
    AudioConfig,
    GroqModelEntry,
    HistoryConfig,
    InjectionConfig,
    KeyCombination,
    LoggingConfig,
    ModelConfig,
    ThemeColor,
    ThemeFont,
    ThemeLayout,
    TranscriptionConfig,
    UIConfig,
    VADConfig,
)

# ---------------------------------------------------------------------------
# Mapeamento: nome da seção → (modelo Pydantic, arquivo TOML)
# ---------------------------------------------------------------------------
_SECTIONS: list[tuple[str, str, type, str]] = [
    # (título PT, título EN, modelo, arquivo TOML)
    ("Aplicação", "Application", AppConfig, "config.toml → [app]"),
    ("Modelo", "Model", ModelConfig, "config.toml → [model]"),
    ("Áudio", "Audio", AudioConfig, "config.toml → [audio]"),
    ("VAD (detecção de voz)", "VAD (voice activity detection)", VADConfig, "config.toml → [vad]"),
    ("Transcrição", "Transcription", TranscriptionConfig, "config.toml → [transcription]"),
    ("Injeção de texto", "Text injection", InjectionConfig, "config.toml → [injection]"),
    ("Interface", "Interface", UIConfig, "config.toml → [ui]"),
    ("Histórico", "History", HistoryConfig, "config.toml → [history]"),
    ("Logs", "Logs", LoggingConfig, "config.toml → [logging]"),
    ("Cores", "Colors", ThemeColor, "theme.toml → [colors]"),
    ("Fontes", "Fonts", ThemeFont, "theme.toml → [fonts]"),
    ("Layout", "Layout", ThemeLayout, "theme.toml → [layout]"),
    ("Atalhos — Push-to-talk", "Shortcuts — Push-to-talk", KeyCombination, "shortcuts.toml → [push_to_talk]"),
    ("Atalhos — Popup", "Shortcuts — Popup", KeyCombination, "shortcuts.toml → [open_mic_popup]"),
    ("Catálogo — Modelo Groq", "Catalog — Groq model", GroqModelEntry, "models.toml → [[available_models]]"),
    ("Avançado", "Advanced", AdvancedConfig, "advanced.toml"),
]


def _default_repr(field: FieldInfo) -> str:
    """Representação legível do valor default de um campo."""
    if field.is_required():
        return "—"
    if field.default is not None and field.default is not ...:
        val = field.default
        if isinstance(val, bool):
            return str(val).lower()
        if isinstance(val, str):
            return f'"{val}"' if val else '""'
        return str(val)
    if field.default_factory is not None:  # type: ignore[misc]
        try:
            val = field.default_factory()  # type: ignore[misc]
            if isinstance(val, dict) and not val:
                return "{}"
            if isinstance(val, list) and not val:
                return "[]"
            return str(val)
        except Exception:
            return "—"
    return "—"


def _constraints(field: FieldInfo) -> str:
    """Extrai restrições numéricas do campo (ge, le, gt, lt)."""
    meta = field.metadata
    parts: list[str] = []
    for m in meta:
        name = type(m).__name__
        if name == "Ge":
            parts.append(f"≥ {m.ge}")
        elif name == "Le":
            parts.append(f"≤ {m.le}")
        elif name == "Gt":
            parts.append(f"> {m.gt}")
        elif name == "Lt":
            parts.append(f"< {m.lt}")
    return ", ".join(parts) if parts else ""


def _type_str(field: FieldInfo) -> str:
    """Representação simplificada do tipo anotado."""
    ann = field.annotation
    if ann is None:
        return "any"
    name = getattr(ann, "__name__", None) or str(ann)
    # Simplifica tipos genéricos comuns
    name = (
        name.replace("typing.Literal", "Literal")
        .replace("typing.Optional", "Optional")
        .replace("<class '", "")
        .replace("'>", "")
        .replace("whisper_microfone.config.schemas.", "")
    )
    # Literal[...] — extrai os valores
    raw = str(field.annotation)
    if raw.startswith("typing.Literal[") or "Literal[" in raw:
        inner = raw.split("Literal[", 1)[1].rstrip("]")
        return f"Literal[{inner}]"
    return name


def _render_section(title: str, model: type, toml_ref: str, lang: str) -> str:
    """Renderiza uma seção Markdown para um schema Pydantic."""
    lines: list[str] = []
    lines.append(f"### {title}")
    lines.append("")
    lines.append(f"**Arquivo:** `{toml_ref}`")
    lines.append("")
    lines.append("| Campo | Tipo | Default | Restrições | Descrição |" if lang == "pt"
                 else "| Field | Type | Default | Constraints | Description |")
    lines.append("|---|---|---|---|---|")

    for field_name, field_info in model.model_fields.items():
        typ = _type_str(field_info)
        default = _default_repr(field_info)
        constraints = _constraints(field_info)
        description = field_info.description or "—"
        lines.append(f"| `{field_name}` | `{typ}` | `{default}` | {constraints} | {description} |")

    lines.append("")
    return "\n".join(lines)


def _render_doc(lang: str) -> str:
    """Renderiza o documento completo em PT ou EN."""
    is_pt = lang == "pt"

    header = """# Referência de Configuração — Whisper Microfone

> **Gerado automaticamente** a partir dos schemas Pydantic em `config/schemas.py`.
> Não edite este arquivo manualmente — execute `python scripts/gen_docs.py` para atualizar.

## Como configurar

Os arquivos de configuração ficam em `%APPDATA%\\whisper-microfone\\config\\` (Windows)
ou `~/.local/share/whisper-microfone/config/` (Linux/Mac).

Na primeira execução, os defaults são copiados automaticamente para essa pasta.
Edite os arquivos TOML com qualquer editor de texto — o app detecta as mudanças
automaticamente (hot-reload).

### Precedência

```
Defaults empacotados < Config do usuário < Variáveis de ambiente
```

**Variáveis de ambiente:** `WHISPER_MIC_<SECAO>__<CAMPO>=valor`
Exemplo: `WHISPER_MIC_APP__LANGUAGE_UI=en`

---

""" if is_pt else """# Configuration Reference — Whisper Microphone

> **Auto-generated** from Pydantic schemas in `config/schemas.py`.
> Do not edit this file manually — run `python scripts/gen_docs.py` to update.

## How to configure

Configuration files are located at `%APPDATA%\\whisper-microfone\\config\\` (Windows)
or `~/.local/share/whisper-microfone/config/` (Linux/Mac).

On first run, defaults are automatically copied to that folder.
Edit the TOML files with any text editor — the app detects changes
automatically (hot-reload).

### Precedence

```
Packaged defaults < User config < Environment variables
```

**Environment variables:** `WHISPER_MIC_<SECTION>__<FIELD>=value`
Example: `WHISPER_MIC_APP__LANGUAGE_UI=en`

---

"""

    sections: list[str] = []
    for title_pt, title_en, model, toml_ref in _SECTIONS:
        title = title_pt if is_pt else title_en
        sections.append(_render_section(title, model, toml_ref, lang))

    footer = "\n---\n\n*Gerado por `scripts/gen_docs.py`*\n" if is_pt else \
             "\n---\n\n*Generated by `scripts/gen_docs.py`*\n"

    return header + "\n".join(sections) + footer


def main() -> None:
    docs_dir = _ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)

    pt_path = docs_dir / "CONFIG.md"
    en_path = docs_dir / "CONFIG.en.md"

    pt_path.write_text(_render_doc("pt"), encoding="utf-8")
    print(f"Gerado: {pt_path}")

    en_path.write_text(_render_doc("en"), encoding="utf-8")
    print(f"Gerado: {en_path}")


if __name__ == "__main__":
    main()

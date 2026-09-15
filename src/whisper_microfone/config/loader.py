from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import ValidationError

from whisper_microfone.config.paths import (
    config_dir,
    defaults_dir,
    set_portable_mode,
)
from whisper_microfone.config.schemas import FullConfig

# Prefixo das env vars de override: WHISPER_MIC_<SECAO>__<CAMPO>
# Ex: WHISPER_MIC_APP__LANGUAGE_UI=en
_ENV_PREFIX = "WHISPER_MIC_"

# Chaves que vêm no topo de advanced.toml (sem seção própria)
_ADVANCED_KEYS = frozenset({
    "worker_thread_priority", "audio_buffer_size", "hotkey_poll_interval_ms",
    "clipboard_timeout_ms", "sqlite_journal_mode", "portable_mode",
})


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge recursivo: override sobrescreve base, recursivo para sub-dicts."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _build_normalized(
    config: dict[str, Any],
    theme: dict[str, Any],
    shortcuts: dict[str, Any],
    prompts: dict[str, Any],
    models: dict[str, Any],
    advanced: dict[str, Any],
) -> dict[str, Any]:
    """Monta o dict final no formato que FullConfig.model_validate() espera.

    Cada arquivo TOML tem seu namespace isolado — sem risco de colisão entre
    config.toml[ui] (UIConfig) e prompts.toml[ui] (strings de idioma).
    """
    out: dict[str, Any] = {}

    # config.toml — seções diretas (app, model, audio, vad,
    #               transcription, injection, ui, history, logging)
    out.update(config)

    # theme.toml → agrupado em "theme"
    out["theme"] = theme

    # shortcuts.toml → agrupado em "shortcuts"
    out["shortcuts"] = shortcuts

    # prompts.toml → agrupado em "prompts"
    out["prompts"] = prompts

    # models.toml → agrupado em "models_catalog"
    out["models_catalog"] = models

    # advanced.toml → agrupado em "advanced"
    out["advanced"] = advanced

    return out


def _apply_env_overrides(out: dict[str, Any]) -> dict[str, Any]:
    """Aplica env vars WHISPER_MIC_<SECTION>__<FIELD>=value sobre o dict normalizado.

    Exemplos:
        WHISPER_MIC_APP__LANGUAGE_UI=en
        WHISPER_MIC_MODEL__GROQ_MODEL=whisper-large-v3
        WHISPER_MIC_ADVANCED__PORTABLE_MODE=true
    Pydantic faz coerção de tipo (string → int/bool/float).
    """
    result = {k: dict(v) if isinstance(v, dict) else v for k, v in out.items()}
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(_ENV_PREFIX):
            continue
        remainder = env_key[len(_ENV_PREFIX):]
        if "__" not in remainder:
            continue
        section, field = remainder.split("__", 1)
        section = section.lower()
        field = field.lower()
        if section not in result:
            result[section] = {}
        if not isinstance(result[section], dict):
            result[section] = {}
        result[section][field] = env_val
    return result


def _ensure_user_configs() -> None:
    """Copia os defaults para %APPDATA%/config/ na primeira execução."""
    dest = config_dir()
    src = defaults_dir()
    for name in ("config.toml", "theme.toml", "shortcuts.toml",
                 "prompts.toml", "models.toml", "advanced.toml"):
        target = dest / name
        if not target.exists():
            target.write_bytes((src / name).read_bytes())


def _bootstrap_portable_mode(advanced_raw: dict[str, Any]) -> None:
    """Ativa modo portátil se portable_mode=true no dict de advanced."""
    portable = advanced_raw.get("portable_mode", False)
    if isinstance(portable, str):
        portable = portable.lower() in ("1", "true", "yes")
    set_portable_mode(bool(portable))


def load_config() -> FullConfig:
    """Carrega, mescla e valida a configuração completa.

    Ordem de precedência (maior sobrescreve menor):
    1. Defaults empacotados em config/defaults/*.toml
    2. Config do usuário em %APPDATA%/whisper-microfone/config/*.toml
    3. Variáveis de ambiente WHISPER_MIC_<SECTION>__<FIELD>=value

    Cada arquivo TOML é mergeado individualmente (default→user) mantendo
    namespaces isolados, evitando colisões entre seções de mesmo nome em
    arquivos diferentes (ex: [ui] em config.toml vs [ui.pt-br] em prompts.toml).

    Na primeira execução, copia os defaults para %APPDATA% automaticamente.
    """
    dd = defaults_dir()

    # Carrega defaults separados por arquivo
    d_config = _load_toml(dd / "config.toml")
    d_theme = _load_toml(dd / "theme.toml")
    d_shortcuts = _load_toml(dd / "shortcuts.toml")
    d_prompts = _load_toml(dd / "prompts.toml")
    d_models = _load_toml(dd / "models.toml")
    d_advanced = _load_toml(dd / "advanced.toml")

    # Bootstrap portable_mode com defaults antes de resolver config_dir()
    _bootstrap_portable_mode(d_advanced)

    _ensure_user_configs()

    ud = config_dir()

    # Carrega config do usuário e mescla sobre os defaults (por arquivo)
    config = _deep_merge(d_config, _load_toml(ud / "config.toml"))
    theme = _deep_merge(d_theme, _load_toml(ud / "theme.toml"))
    shortcuts = _deep_merge(d_shortcuts, _load_toml(ud / "shortcuts.toml"))
    prompts = _deep_merge(d_prompts, _load_toml(ud / "prompts.toml"))
    models = _deep_merge(d_models, _load_toml(ud / "models.toml"))
    advanced = _deep_merge(d_advanced, _load_toml(ud / "advanced.toml"))

    # Re-bootstrap caso usuário tenha alterado portable_mode
    _bootstrap_portable_mode(advanced)

    normalized = _build_normalized(config, theme, shortcuts, prompts, models, advanced)
    normalized = _apply_env_overrides(normalized)

    try:
        return FullConfig.model_validate(normalized)
    except ValidationError as exc:
        raise ConfigLoadError(
            f"Configuração inválida — verifique os arquivos em {config_dir()}:\n{exc}"
        ) from exc


def save_section(section_name: str, data: dict[str, Any]) -> None:
    """Persiste uma seção de configuração no arquivo TOML do usuário.

    Mapeia a seção ao arquivo correto e aplica merge com o conteúdo existente.
    """
    file_map = {
        # config.toml
        "app": "config.toml", "model": "config.toml",
        "audio": "config.toml", "vad": "config.toml",
        "transcription": "config.toml", "injection": "config.toml",
        "ui": "config.toml", "history": "config.toml", "logging": "config.toml",
        # theme.toml
        "colors": "theme.toml", "fonts": "theme.toml", "layout": "theme.toml",
        # shortcuts.toml
        "push_to_talk": "shortcuts.toml", "toggle_pause": "shortcuts.toml",
        "focus_window": "shortcuts.toml", "quit_app": "shortcuts.toml",
        # models.toml
        "available_models": "models.toml",
        # advanced.toml (seção inteira)
        "advanced": "advanced.toml",
    }
    filename = file_map.get(section_name)
    if filename is None:
        raise ValueError(f"Seção desconhecida: {section_name!r}")

    target = config_dir() / filename
    existing = _load_toml(target)
    if filename == "advanced.toml":
        # advanced.toml é plano — mescla direto no topo
        existing.update(data)
    else:
        existing[section_name] = data
    with open(target, "wb") as fh:
        tomli_w.dump(existing, fh)


class ConfigLoadError(RuntimeError):
    """Erro ao carregar ou validar configuração."""

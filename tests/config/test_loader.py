from __future__ import annotations

from pathlib import Path

from whisper_microfone.config import paths
from whisper_microfone.config.loader import load_config


def test_load_config_bootstraps_current_groq_defaults(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setenv("WHISPER_MIC_APPDATA_DIR", str(tmp_path))
    monkeypatch.delenv("WHISPER_MIC_PORTABLE", raising=False)
    paths._base_dir = None

    config = load_config()

    assert config.model.groq_model == "whisper-large-v3-turbo"
    assert config.models_catalog.available_models
    assert (tmp_path / "config" / "config.toml").is_file()

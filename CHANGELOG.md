# Changelog

Todas as mudanças notáveis neste projeto serão documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
e este projeto adota [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

### Adicionado

- Testes automatizados mínimos para carregamento da configuração Groq e contrato de transcrição
- Testes do pipeline do engine para ditado e descarte de silêncio pelo VAD
- Execução bloqueante do pytest na CI
- Typecheck bloqueante do núcleo da aplicação

### Alterado

- Plano e referência de configuração alinhados ao motor atual baseado na API Groq
- Typecheck configurado com o plugin do Pydantic e escopo inicial em `config`, `core` e `engine`

### Corrigido

- Gerador de documentação atualizado para os schemas vigentes após a remoção do motor local
- Pendências de lint que impediam a validação do código-fonte na CI
- Emissão duplicada do estado `idle` quando o VAD descartava a gravação

### Removido

- Script de pré-download do faster-whisper, incompatível com o motor Groq

---

## [0.1.0] - 2026-04-29

Primeiro release Alpha.

### Adicionado

- Sistema de configuração em camadas (TOML + env vars + defaults empacotados) com hot-reload via watchdog
- Schemas Pydantic tipados para todas as seções de configuração: `AppConfig`, `ModelConfig`, `LifecycleConfig`, `AudioConfig`, `VADConfig`, `TranscriptionConfig`, `InjectionConfig`, `UIConfig`, `HistoryConfig`, `LoggingConfig`, `ThemeConfig`, `ShortcutsConfig`, `PromptsConfig`, `ModelsCatalog`, `AdvancedConfig`
- Captura de áudio via sounddevice (16 kHz mono float32) com suporte a dispositivo por nome ou índice
- VAD Silero para remoção de silêncio antes da transcrição, com workaround para paths não-ASCII no Windows
- Transcrição com faster-whisper (lazy load + auto-unload por timer de inatividade)
- Injeção de texto via pynput (digitação) com fallback para clipboard (Ctrl+V) e restauração do clipboard original
- Hotkey global push-to-talk (pynput) com supressão de auto-repeat e suporte a hot-reload de combinação
- Histórico de transcrições em SQLite (WAL mode) com busca, filtro por idioma e limpeza automática por idade
- Métricas de sistema em tempo real (RAM, VRAM, GPU%, CPU%) via pynvml + psutil com fallback sem GPU NVIDIA
- Bridge motor/UI via `QObject` + Qt Signals/Slots (thread-safe, sem polling)
- Internacionalização PT-BR + EN completa via `prompts.toml`
- Documentação de configuração gerada automaticamente a partir dos schemas Pydantic
- Scripts utilitários: download de modelos, listagem de dispositivos, build PyInstaller, startup Windows
- CI/CD com GitHub Actions: lint, typecheck e build automático em release

---

[Não lançado]: https://github.com/Gustavo1341/whisper-microphone/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Gustavo1341/whisper-microphone/releases/tag/v0.1.0

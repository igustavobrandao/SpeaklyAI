# Whisper Microfone — Plano de Arquitetura e Implementação

> [!IMPORTANT]
> Este documento registra a arquitetura original, baseada em `faster-whisper`
> local/CUDA. Desde o commit `489ad46`, o produto usa a API Whisper da Groq.
> Para trabalho novo, o estado e as pendências abaixo prevalecem sobre as
> seções históricas deste arquivo.

## Estado atual e pendências (2026-09-15)

As Fases 1–5 foram implementadas e o aplicativo está na versão Alpha 0.2.0.
A migração para Groq simplificou o motor, mas deixou artefatos do desenho
local/CUDA que ainda precisam ser reconciliados.

| Prioridade | Estado | Pendência | Critério de conclusão |
|---|---|---|---|
| P0 | Concluído | Alinhar specs e documentação gerada ao motor Groq | `scripts/gen_docs.py` executa e os documentos não expõem schemas removidos |
| P0 | Concluído | Criar cobertura automatizada mínima para configuração, transcrição e pipeline do engine | Testes protegem os contratos críticos sem chamar serviços externos |
| P0 | Concluído | Tornar a CI bloqueante para testes e typecheck do núcleo | Pytest e mypy de `config`, `core` e `engine` falham o pull request em regressões |
| P1 | Concluído | Remover o script local obsoleto `scripts/pre_download_model.py` | Nenhum comando operacional promete download de modelo local |
| P1 | Em andamento | Validar o executável Groq em build limpo do Windows | Build one-file de 287,8 MB passou; falta iniciar sem conflito de instância e concluir uma transcrição |
| P1 | Concluído | Revisar telas e métricas herdadas de GPU/modelo local | UI diferencia as métricas do sistema do processamento Groq em nuvem |
| P1 | Pendente | Migrar a UI para enums atuais do PySide6 e reincluí-la no mypy | A camada `ui/` volta a fazer parte do typecheck estrito |
| P2 | Concluído | Atualizar versão e changelog da migração | Metadados e notas de release descrevem a arquitetura Groq |

### Contrato vigente do motor

```text
hotkey/click → captura 16 kHz mono → VAD Silero → WAV em memória
             → Groq Whisper API → normalização → injeção/clipboard
```

- O motor requer `GROQ_API_KEY`; nenhum modelo local é carregado.
- O modelo padrão é `whisper-large-v3-turbo` e permanece configurável.
- O áudio é enviado à Groq; o produto não deve ser descrito como processamento totalmente local.
- Configurações do usuário continuam em TOML e segredos ficam fora desses arquivos.

## Arquitetura original (referência histórica)

> **Objetivo:** substituto open source do `Win + H` do Windows. Hotkey global push-to-talk → grava microfone → transcreve localmente com Whisper na GPU → injeta texto na janela ativa.
>
> **Princípios:** zero hardcoded, motor sob demanda (lazy load + auto-unload), interface estilo VS Code, multilíngue (PT-BR + EN) desde o dia 1.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Stack técnico](#2-stack-técnico)
3. [Decisões de modelo](#3-decisões-de-modelo)
4. [Estratégia "motor de partida"](#4-estratégia-motor-de-partida-lazy-load--auto-unload)
5. [Sistema de configuração (zero hardcoded)](#5-sistema-de-configuração-zero-hardcoded)
6. [Interface estilo VS Code](#6-interface-estilo-vs-code)
7. [Estrutura de pastas](#7-estrutura-de-pastas)
8. [Detalhamento por módulo](#8-detalhamento-por-módulo)
9. [Internacionalização PT-BR + EN](#9-internacionalização-pt-br--en)
10. [Performance esperada](#10-performance-esperada-na-rtx-3050-6gb)
11. [Plano de implementação por etapas](#11-plano-de-implementação-por-etapas)
12. [Riscos e mitigações](#12-riscos-e-mitigações)
13. [Hardware de referência do desenvolvedor](#13-hardware-de-referência)
14. [Decisões já tomadas](#14-decisões-já-tomadas-pelo-usuário)

---

## 1. Visão geral

Aplicação Python que roda em background no Windows, escuta um hotkey global (push-to-talk), captura áudio do microfone enquanto a tecla está pressionada, transcreve localmente com **faster-whisper** rodando em CUDA, e injeta o texto resultante na janela ativa via simulação de teclado, com fallback para clipboard.

**Fluxo resumido:**

```
[Tecla pressionada]
        ↓
[Captura áudio (sounddevice, 16 kHz mono)]
        ↓ paralelo: [Pré-carrega modelo Whisper se descarregado]
[Tecla solta]
        ↓
[VAD (Silero) trim de silêncio]
        ↓
[faster-whisper small int8_float16 em CUDA]
        ↓
[Tenta digitar (pynput.Controller.type)]
        ↓ se falhar/timeout
[Cola via clipboard (Ctrl+V) com backup/restore]
        ↓
[Texto aparece na janela ativa]
```

**Diferencial:** lazy load do modelo. Em idle frio o app consome ~80 MB de RAM e 0 de VRAM. Modelo é carregado em paralelo enquanto o usuário fala (escondendo o tempo de carga) e auto-descarrega após N segundos de inatividade.

---

## 2. Stack técnico

| Camada | Biblioteca | Versão alvo | Motivo |
|---|---|---|---|
| Engine STT | `faster-whisper` (CTranslate2) | >=1.1.0 | 4× mais rápido que whisper original, ½ da VRAM, suporta int8/float16 |
| Modelo padrão | `Systran/faster-whisper-small` | — | 244M params, multilíngue PT+EN, ~480MB disco, ~1.3GB VRAM int8_float16 |
| VAD | `silero-vad` (ONNX) | >=5.1 | <2MB, ~1ms/chunk, elimina alucinações de silêncio |
| Captura áudio | `sounddevice` (PortAudio) | >=0.4.7 | Stream baixa latência |
| Hotkey global | `pynput` | >=1.7.7 | Detecta press/release, sem necessidade de admin |
| Injeção texto | `pynput` + `pyperclip` | — | Digita Unicode + fallback clipboard |
| GUI | `PySide6` (Qt6 LGPL) | >=6.8 | Profissional, performance, gráficos nativos |
| Tema | `pyqtdarktheme` | >=2.1 | Dark theme estilo VS Code |
| Gráficos tempo real | `pyqtgraph` | >=0.13 | Performático, integra com Qt |
| Ícones | `qtawesome` | >=1.3 | Font Awesome / Material Icons |
| Métricas GPU | `pynvml` | >=11.5 | VRAM e uso de GPU NVIDIA |
| Métricas sistema | `psutil` | >=6.0 | RAM e CPU |
| Tray (alternativa, fallback) | `pystray` | >=0.19 | Backup se QSystemTrayIcon der problema |
| Validação config | `pydantic` + `pydantic-settings` | >=2.5 | Schemas tipados |
| TOML | `tomli` / `tomli_w` | builtin py3.11+ | Read/write TOML |
| Watcher de arquivos | `watchdog` | >=4.0 | Hot-reload de config |
| Logs | `loguru` | >=0.7 | Rotação automática, formato amigável |
| Banco histórico | `sqlite3` (builtin) | — | Sem dependência externa |
| Empacotamento | `PyInstaller` | >=6.0 | Executável único `.exe` |
| Runtime CUDA | `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` (wheels) | — | Não exige CUDA toolkit instalado no sistema |

### `requirements.txt`

```txt
# Core engine
faster-whisper>=1.1.0
silero-vad>=5.1
sounddevice>=0.4.7
numpy>=1.26
pynput>=1.7.7
pyperclip>=1.9.0

# UI
PySide6>=6.8
pyqtdarktheme>=2.1
pyqtgraph>=0.13
qtawesome>=1.3

# Métricas
pynvml>=11.5
psutil>=6.0

# Config & utilities
pydantic>=2.9
pydantic-settings>=2.5
tomli-w>=1.0
watchdog>=4.0
loguru>=0.7

# CUDA wheels (Windows + NVIDIA)
nvidia-cublas-cu12
nvidia-cudnn-cu12

# Dev/test (em requirements-dev.txt)
# pytest, pytest-qt, pytest-mock, ruff, black, mypy, pyinstaller
```

---

## 3. Decisões de modelo

### Escolha padrão: `small` em `int8_float16`

Para **multilíngue PT+EN** com requisito de baixo consumo:

| Modelo | Disco | VRAM (int8_float16) | Latência ~5s áudio (RTX 3050) | WER PT/EN |
|---|---|---|---|---|
| tiny | 75 MB | ~0.5 GB | ~150 ms | Ruim em PT, erra muito |
| base | 145 MB | ~0.7 GB | ~250 ms | Aceitável EN, fraco PT |
| **small** ⭐ | **480 MB** | **~1.3 GB** | **~400 ms** | **Bom PT, ótimo EN — sweet spot** |
| medium | 1.5 GB | ~2.5 GB | ~900 ms | Excelente, mas pesa o dobro |
| large-v3-turbo | 1.6 GB | ~3 GB | ~600 ms | Top, mas só compensa com mais VRAM livre |

**Justificativa:** cabe folgado em 6GB de VRAM, deixa GPU livre para outras apps, WER em PT-BR satisfatório. Alternativas `medium`, `large-v3-turbo` e `distil-large-v3` (só inglês) ficam disponíveis no catálogo `models.toml`.

### Por que `int8_float16` e não `float16` puro

- Pesos em INT8 (½ tamanho), ativações em FP16 (precisão preservada)
- Economia de ~40% de VRAM com perda de qualidade praticamente imperceptível
- Funciona nativamente no CTranslate2 com aceleração CUDA

---

## 4. Estratégia "motor de partida" (lazy load + auto-unload)

### Problema

| Abordagem | RAM idle | VRAM idle | 1ª transcrição | Subsequente |
|---|---|---|---|---|
| Sempre carregado | ~600 MB | ~1.3 GB | ~400 ms | ~400 ms |
| Sempre descarregado | ~80 MB | 0 | ~3-5 s ❌ | ~3-5 s ❌ |
| **Lazy + auto-unload** ⭐ | **~80 MB → 600 MB** | **0 → 1.3 GB** | **~400 ms*** | **~400 ms** |

\* Carga acontece **em paralelo** durante a fala do usuário (1-5s), escondendo a latência.

### Mecanismo

```
[App inicia] → 80 MB RAM, 0 MB VRAM
       ↓
[Usuário pressiona hotkey]
       ↓ (em paralelo)
   [Áudio começa a gravar]    [Modelo começa a carregar em thread]
       ↓                           ↓
[Usuário fala 2-5s]          [Modelo pronto + warmup com silêncio 1s]
       ↓                           ↓
[Usuário solta hotkey] ←——— sincroniza ———→
       ↓
[Transcreve em ~400ms] → injeta texto
       ↓
[Timer de auto-unload reinicia: 180s]
       ↓
[Sem uso por 180s] → unload silencioso → 80 MB RAM, 0 MB VRAM
```

### 3 perfis pré-configurados em `models.toml`

| Perfil | Quando usar | `unload_after_idle_seconds` | `preload_on_startup` |
|---|---|---|---|
| **economic** | Uso esporádico | 60 | false |
| **balanced** ⭐ | Padrão recomendado | 180 | false |
| **always_ready** | Ditado constante | 0 | true |

### Implementação chave (`transcriber.py`)

- Modelo é `None` inicialmente
- `preload_async()` dispara load em thread separada
- `transcribe()` espera o load se estiver acontecendo, ou carrega sob demanda
- Timer de unload reinicia a cada uso
- Unload chama `del`, `gc.collect()`, `torch.cuda.empty_cache()`

---

## 5. Sistema de configuração (zero hardcoded)

### Princípio

Toda string, número, caminho, cor, hotkey, threshold, timeout ou comportamento ajustável vai para configuração externa. Nada de magic numbers no código.

### Hierarquia em 3 camadas

```
┌─────────────────────────────────────────────────────────┐
│  1. DEFAULTS (empacotados no pacote, fonte da verdade)  │
│     src/whisper_microfone/config/defaults/*.toml        │
│         ↓ sobrescrito por                               │
│  2. CONFIG DO USUÁRIO                                   │
│     %APPDATA%\whisper-microfone\config\*.toml           │
│         ↓ sobrescrito por                               │
│  3. VARIÁVEIS DE AMBIENTE (CI / power users)            │
│     WHISPER_MIC_MODEL_NAME=medium ...                   │
└─────────────────────────────────────────────────────────┘
```

### 6 arquivos TOML separados por domínio

```
%APPDATA%\whisper-microfone\config\
├── config.toml         # Configuração principal do usuário
├── theme.toml          # Cores, fontes, tamanhos da UI
├── shortcuts.toml      # Atalhos de teclado (PTT, pausar, abrir janela)
├── prompts.toml        # i18n (PT-BR + EN) + prompts opcionais para Whisper
├── models.toml         # Catálogo de modelos disponíveis + perfis
└── advanced.toml       # Tunables que 99% não vão tocar
```

Cada arquivo tem schema Pydantic correspondente em `config/schemas.py`.

### Hot-reload

Watchdog observa `%APPDATA%\whisper-microfone\config\`. Mudança em qualquer `*.toml`:
- Mudou modelo → unload + reload no próximo uso
- Mudou hotkey → re-registra listener
- Mudou tema → aplica imediatamente na UI
- Mudou idioma → recarrega `prompts.toml` e atualiza widgets

### Defaults empacotados

```
src/whisper_microfone/config/defaults/
├── config.toml
├── theme.toml
├── shortcuts.toml
├── prompts.toml
├── models.toml
└── advanced.toml
```

Esses arquivos viajam com o pacote, são read-only no instalado, e são copiados para `%APPDATA%` na primeira execução. A partir daí o usuário edita lá.

### Documentação automática

- `docs/CONFIG.md` gerado de docstrings dos schemas Pydantic
- Tooltips na UI Config leem o `description` do Pydantic
- `config.example.toml` comentado gerado por script
- Documentação **nunca** desatualiza, vem do código

### Schemas resumidos (`config/schemas.py`)

```python
class AppConfig(BaseModel):
    start_with_windows: bool = False
    start_minimized: bool = True
    language_ui: Literal["pt-br", "en"] = "pt-br"
    profile: str = "balanced"

class ModelConfig(BaseModel):
    name: str = ""                    # vazio = herda do profile
    compute_type: Literal["", "int8", "int8_float16", "float16", "float32"] = ""
    device: Literal["auto", "cuda", "cpu"] = "auto"
    language: str = "auto"
    download_dir: str = ""

class LifecycleConfig(BaseModel):
    preload_on_startup: bool = False
    unload_after_idle_seconds: int = 180
    load_during_recording: bool = True
    warmup_on_load: bool = True
    warmup_audio_seconds: float = 1.0

class AudioConfig(BaseModel):
    sample_rate: Literal[16000] = 16000
    channels: int = 1
    device_name: str = ""
    device_index: int = -1
    min_duration_ms: int = 300
    max_duration_seconds: int = 60

class VADConfig(BaseModel):
    enabled: bool = True
    threshold: float = 0.5
    min_silence_ms: int = 200
    speech_pad_ms: int = 100

class TranscriptionConfig(BaseModel):
    beam_size: int = 1
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = False
    initial_prompt: str = ""
    suppress_blank: bool = True
    temperature: float = 0.0

class InjectionConfig(BaseModel):
    strategy: Literal["type_then_paste", "paste_only", "type_only"] = "type_then_paste"
    type_delay_ms: int = 5
    paste_fallback_after_ms: int = 1500
    restore_clipboard: bool = True
    restore_clipboard_delay_ms: int = 100
    trim_whitespace: bool = True
    add_trailing_space: bool = False
    capitalize_first: bool = False
    sentence_end_punctuation: str = ""

class UIConfig(BaseModel):
    show_tray_icon: bool = True
    play_sounds: bool = True
    sound_volume: float = 0.3
    metrics_update_interval_ms: int = 500
    chart_history_seconds: int = 60
    window_width: int = 900
    window_height: int = 600
    remember_window_position: bool = True

class HistoryConfig(BaseModel):
    enabled: bool = True
    store_text: bool = True
    max_entries: int = 500
    auto_clean_after_days: int = 30

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    file_rotation_mb: int = 10
    file_retention: int = 5
    log_metrics: bool = False

class FullConfig(BaseModel):
    """Raiz: junta tudo após resolver perfil."""
    app: AppConfig
    model: ModelConfig
    lifecycle: LifecycleConfig
    audio: AudioConfig
    vad: VADConfig
    transcription: TranscriptionConfig
    injection: InjectionConfig
    ui: UIConfig
    history: HistoryConfig
    logging: LoggingConfig
    theme: ThemeConfig
    shortcuts: ShortcutsConfig
    prompts: PromptsConfig
    models_catalog: ModelsCatalog
    advanced: AdvancedConfig
```

---

## 6. Interface estilo VS Code

### Stack visual

- **PySide6** (Qt6 LGPL) — widgets nativos, performance, gráficos
- **PyQtDarkTheme** — tema dark estilo VS Code fora da caixa
- **pyqtgraph** — gráficos em tempo real (~60fps, baixo overhead)
- **qtawesome** — ícones Font Awesome / Material para sidebar

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ≡  Whisper Microfone                              ─  □  ✕      │
├──────────┬──────────────────────────────────────────────────────┤
│  🎙️ Início│   ┌─ Status ────────────────────────────┐           │
│  📊 Monitor│   │  ● Ativo  •  Modelo: small (carregado)│         │
│  ⚙️ Config│   │  Hotkey:  Ctrl + Alt + Space          │         │
│  📜 Histórico│ │  [▶ Pausar]  [⏏ Descarregar modelo]  │         │
│  ℹ️ Sobre │   └───────────────────────────────────────┘         │
│  ────    │                                                      │
│  🟢 Ativo│   ┌─ Consumo em tempo real ──────────────┐           │
│          │   │  RAM    ▓▓▓▓░░░░░░  612 MB            │           │
│          │   │  VRAM   ▓▓▓░░░░░░░  1.31 GB / 6 GB    │           │
│          │   │  GPU    ▁▁▁▂▃▅▂▁▁▁  4%               │           │
│          │   │  CPU    ▁▁▁▁▁▁▁▁▁▁  1%               │           │
│          │   └───────────────────────────────────────┘           │
│          │   ┌─ Última transcrição ─────────────────┐           │
│          │   │  "Olá, isso é um teste de ditado"   │           │
│          │   │  Idioma: pt  •  Latência: 412 ms     │           │
│          │   └───────────────────────────────────────┘           │
└──────────┴──────────────────────────────────────────────────────┘
```

### 5 páginas (sidebar VS Code-like)

1. **🎙️ Início** — visão geral: status + métricas resumidas + última transcrição + ações rápidas
2. **📊 Monitor** — gráficos detalhados em tempo real (linha temporal RAM/VRAM/GPU/CPU dos últimos 60s) + estatísticas da sessão
3. **⚙️ Config** — formulário com todos os campos, validação visual, sem editar TOML manualmente
4. **📜 Histórico** — últimas 500 transcrições (configurável) com busca, filtro por idioma, copiar/exportar CSV
5. **ℹ️ Sobre** — versão, modelo carregado, GPU detectada, status CUDA, link para logs

### Comportamento da janela

- App inicia **minimizado na bandeja** por padrão (configurável)
- Clique no ícone da bandeja → abre/foca janela
- Fechar janela (X) → volta para bandeja, **não fecha o app**
- "Sair" só pelo menu da bandeja ou Ctrl+Q

### 6 estados da bandeja

| Ícone | Estado | Tooltip (PT) | Tooltip (EN) |
|---|---|---|---|
| ⚪ Cinza | Pausado | "Whisper pausado — clique para ativar" | "Whisper paused — click to activate" |
| 🟢 Verde | Ativo, modelo descarregado | "Pronto • Modelo descarregado" | "Ready • Model unloaded" |
| 🔵 Azul | Carregando modelo | "Carregando IA..." | "Loading AI..." |
| 🟢 Verde+ponto | Ativo, modelo quente | "Pronto • Latência mínima" | "Ready • Minimal latency" |
| 🔴 Vermelho | Gravando | "Ouvindo..." | "Listening..." |
| 🟡 Amarelo | Transcrevendo | "Processando..." | "Processing..." |

### Atalhos globais (configuráveis em `shortcuts.toml`)

- `Ctrl+Alt+Space` (default) → push-to-talk
- `Ctrl+Alt+P` → pausar/despausar PTT
- `Ctrl+Alt+W` → focar janela principal
- `Ctrl+Q` → sair (apenas com janela em foco)

### Comunicação UI ↔ motor

Tudo num único processo. Comunicação via **Qt Signals/Slots** (thread-safe nativamente):

```
┌─────────────────────────────────────────────────────┐
│  Processo único                                     │
│  ┌──────────────────────────────────┐               │
│  │  Qt Main Thread                  │               │
│  │  - UI                            │               │
│  │  - System Tray                   │               │
│  └──────────────────────────────────┘               │
│            ↑↓ Qt Signals (thread-safe)              │
│  ┌──────────────────────────────────┐               │
│  │  Worker threads                  │               │
│  │  - Hotkey listener               │               │
│  │  - Audio capture                 │               │
│  │  - Whisper engine                │               │
│  │  - Metrics collector (Timer)     │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

---

## 7. Estrutura de pastas

```
whisper-microfone/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md                            # PT + EN
├── README.en.md                         # English version
├── LICENSE                              # MIT recomendado
├── CHANGELOG.md
├── run.bat                              # Atalho Windows
├── run.sh                               # Linux futuro
├── docs/
│   ├── CONFIG.md                        # Gerado de schemas
│   ├── CONFIG.en.md
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md
│   └── images/
├── assets/
│   ├── icon.ico
│   ├── icon-warm.ico
│   ├── icon-cold.ico
│   ├── icon-recording.ico
│   ├── icon-loading.ico
│   ├── icon-paused.ico
│   ├── icon-error.ico
│   └── sounds/
│       ├── start.wav
│       └── stop.wav
├── scripts/
│   ├── gen_docs.py                      # Gera docs/CONFIG.md de schemas
│   ├── test_audio_devices.py            # Lista mics
│   └── build_exe.py                     # PyInstaller
├── src/
│   └── whisper_microfone/
│       ├── __init__.py
│       ├── __main__.py                  # python -m whisper_microfone
│       ├── version.py
│       ├── logging_setup.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schemas.py               # Pydantic models
│       │   ├── loader.py                # Load + merge + validate
│       │   ├── paths.py                 # appdata_dir, models_dir, etc
│       │   ├── watcher.py               # Hot-reload
│       │   └── defaults/
│       │       ├── config.toml
│       │       ├── theme.toml
│       │       ├── shortcuts.toml
│       │       ├── prompts.toml
│       │       ├── models.toml
│       │       └── advanced.toml
│       ├── core/                        # MOTOR (sem Qt)
│       │   ├── __init__.py
│       │   ├── audio.py                 # Captura sounddevice
│       │   ├── vad.py                   # Silero VAD wrapper
│       │   ├── transcriber.py           # faster-whisper + lazy load
│       │   ├── hotkey.py                # pynput push-to-talk
│       │   ├── injector.py              # type → paste fallback
│       │   ├── metrics.py               # pynvml + psutil
│       │   └── history.py               # SQLite store
│       ├── i18n/
│       │   ├── __init__.py
│       │   └── translator.py            # Carrega prompts.toml + getter
│       ├── ui/                          # INTERFACE (depende do core)
│       │   ├── __init__.py
│       │   ├── app.py                   # QApplication + tema
│       │   ├── main_window.py           # Janela principal + sidebar
│       │   ├── tray.py                  # QSystemTrayIcon
│       │   ├── theme.py                 # Aplica theme.toml ao Qt
│       │   ├── pages/
│       │   │   ├── __init__.py
│       │   │   ├── home.py
│       │   │   ├── monitor.py
│       │   │   ├── config_page.py
│       │   │   ├── history.py
│       │   │   └── about.py
│       │   └── widgets/
│       │       ├── __init__.py
│       │       ├── metric_bar.py
│       │       ├── live_chart.py
│       │       ├── status_card.py
│       │       ├── transcription_card.py
│       │       └── hotkey_capture.py    # Captura combinação de teclas
│       └── engine.py                    # Bridge core ↔ UI (QObject + signals)
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── audio_pt.wav
    │   ├── audio_en.wav
    │   └── audio_silence.wav
    ├── core/
    │   ├── test_audio.py
    │   ├── test_vad.py
    │   ├── test_transcriber.py
    │   ├── test_hotkey.py
    │   ├── test_injector.py
    │   ├── test_metrics.py
    │   └── test_history.py
    ├── config/
    │   ├── test_schemas.py
    │   ├── test_loader.py
    │   ├── test_merge.py
    │   ├── test_profiles.py
    │   └── test_env_overrides.py
    └── ui/
        ├── test_main_window.py
        └── test_pages.py
```

**Princípio:** `core/` não importa nada de Qt. Pode ser testado e reusado independentemente.

---

## 8. Detalhamento por módulo

### 8.1 `core/audio.py`

- Stream `sounddevice.InputStream` 16 kHz mono float32
- `start()`: empilha chunks num `deque` thread-safe
- `stop()`: concatena em `np.ndarray`, retorna `None` se < `min_duration_ms`
- Aplica `max_duration_seconds` como corte de segurança

### 8.2 `core/vad.py`

- Carrega `silero-vad` ONNX uma vez (~2 MB RAM, roda em CPU)
- `trim_silence(audio)`: detecta speech, concatena segmentos com gap máximo
- Elimina alucinações tipo "obrigado por assistir" / "thanks for watching"

### 8.3 `core/transcriber.py` (com lazy load)

```python
class WhisperTranscriber:
    def __init__(self, model_cfg, lifecycle_cfg, transcription_cfg):
        self._model_cfg = model_cfg
        self._lifecycle = lifecycle_cfg
        self._transcription = transcription_cfg
        self._model: WhisperModel | None = None
        self._lock = threading.Lock()
        self._loading: threading.Event | None = None
        self._unload_timer: threading.Timer | None = None

    def preload_async(self):
        with self._lock:
            if self._model is not None or self._loading is not None:
                return
            self._loading = threading.Event()
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        model = WhisperModel(
            self._model_cfg.name,
            device=self._model_cfg.device,
            compute_type=self._model_cfg.compute_type,
            download_root=str(models_dir()),
        )
        if self._lifecycle.warmup_on_load:
            silence = np.zeros(int(16000 * self._lifecycle.warmup_audio_seconds), dtype=np.float32)
            list(model.transcribe(silence, language="en")[0])
        with self._lock:
            self._model = model
            self._loading.set()

    def transcribe(self, audio, language=None) -> str:
        if self._loading and not self._loading.is_set():
            self._loading.wait()
        if self._model is None:
            self._load()
        self._reset_unload_timer()
        segments, _ = self._model.transcribe(
            audio,
            language=None if language == "auto" else language,
            beam_size=self._transcription.beam_size,
            no_speech_threshold=self._transcription.no_speech_threshold,
            condition_on_previous_text=self._transcription.condition_on_previous_text,
            initial_prompt=self._transcription.initial_prompt or None,
            temperature=self._transcription.temperature,
            suppress_blank=self._transcription.suppress_blank,
            vad_filter=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()

    def _reset_unload_timer(self):
        if self._lifecycle.unload_after_idle_seconds <= 0:
            return
        if self._unload_timer:
            self._unload_timer.cancel()
        self._unload_timer = threading.Timer(
            self._lifecycle.unload_after_idle_seconds, self._unload
        )
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _unload(self):
        with self._lock:
            if self._model is None:
                return
            del self._model
            self._model = None
            self._loading = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except ImportError:
            pass
```

### 8.4 `core/hotkey.py`

- `pynput.keyboard.Listener` com lógica press/release
- Estado: rastreia quais teclas do combo estão pressionadas
- Quando todas pressionadas → `on_press()`
- Quando qualquer uma é solta → `on_release()`
- Suprime auto-repeat
- Modos: `push_to_talk` | `toggle` | `hybrid`

### 8.5 `core/injector.py`

```python
class TextInjector:
    def inject(self, text: str):
        text = self._post_process(text)  # trim, capitalize, etc
        if self.cfg.strategy == "paste_only":
            return self._paste(text)
        if self.cfg.strategy == "type_only":
            return self._type(text)
        try:
            self._type_with_timeout(text)
        except TypingTimeoutError:
            logger.warning("Type timeout, falling back to paste")
            self._paste(text)

    def _paste(self, text: str):
        backup = pyperclip.paste() if self.cfg.restore_clipboard else None
        pyperclip.copy(text)
        keyboard.Controller().press(Key.ctrl)
        keyboard.Controller().press('v')
        keyboard.Controller().release('v')
        keyboard.Controller().release(Key.ctrl)
        if backup is not None:
            time.sleep(self.cfg.restore_clipboard_delay_ms / 1000)
            pyperclip.copy(backup)
```

### 8.6 `core/metrics.py`

- `pynvml`: handle único, `nvmlDeviceGetMemoryInfo()` + `nvmlDeviceGetUtilizationRates()`
- `psutil`: `Process(os.getpid()).memory_info().rss` + `cpu_percent()`
- `get_metrics() -> Metrics` (dataclass): RAM_MB, VRAM_MB, VRAM_total_MB, GPU%, CPU%

### 8.7 `core/history.py`

- SQLite em `%APPDATA%\whisper-microfone\history.db`
- Tabela: `transcriptions(id, timestamp, language, text, duration_ms, latency_ms)`
- `add()`, `list(limit, offset, filter_lang, search)`, `clear()`, `auto_clean(days)`

### 8.8 `engine.py` — Bridge core ↔ UI

```python
class Engine(QObject):
    # Sinais para a UI
    state_changed = Signal(str)              # idle_warm|idle_cold|loading|recording|transcribing|paused|error
    transcribed = Signal(str, dict)          # texto, metadata
    metrics_updated = Signal(object)         # Metrics dataclass
    error_occurred = Signal(str)
    config_reloaded = Signal()

    def __init__(self, config: FullConfig):
        super().__init__()
        self.config = config
        self.transcriber = WhisperTranscriber(...)
        self.recorder = AudioRecorder(...)
        self.vad = SileroVAD(...) if config.vad.enabled else None
        self.injector = TextInjector(...)
        self.history = HistoryStore(...)
        self.hotkey = PushToTalkHotkey(
            config.shortcuts.push_to_talk.combination,
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._metrics_timer = QTimer()
        self._metrics_timer.timeout.connect(self._emit_metrics)
        self._metrics_timer.start(config.ui.metrics_update_interval_ms)
        self.paused = False

    def _on_press(self):
        if self.paused: return
        self.state_changed.emit("recording")
        self.recorder.start()
        if self.config.lifecycle.load_during_recording:
            self.transcriber.preload_async()

    def _on_release(self):
        if self.paused: return
        audio = self.recorder.stop()
        if audio is None:
            self.state_changed.emit(self._idle_state())
            return
        self.state_changed.emit("transcribing")
        if self.vad: audio = self.vad.trim_silence(audio)
        try:
            t0 = time.perf_counter()
            text = self.transcriber.transcribe(audio, self.config.model.language)
            latency = (time.perf_counter() - t0) * 1000
            if text:
                self.injector.inject(text)
                self.history.add(text, len(audio)/16000*1000, latency)
                self.transcribed.emit(text, {"latency_ms": latency})
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.state_changed.emit(self._idle_state())
```

### 8.9 `i18n/translator.py`

```python
class Translator:
    def __init__(self, prompts: PromptsConfig, language: str):
        self._strings = prompts.ui[language]  # ui.pt-br ou ui.en

    def t(self, key: str, **kwargs) -> str:
        value = self._strings.get(key, f"<{key}>")
        return value.format(**kwargs) if kwargs else value

# Uso na UI
t = translator.t
button.setText(t("btn_pause"))
label.setText(t("status_loading"))
```

---

## 9. Internacionalização PT-BR + EN

### Estratégia

- **Toda string da UI** vem de `prompts.toml` em `[ui.pt-br]` ou `[ui.en]`
- Idioma trocável em runtime via `[app].language_ui`
- Fallback para EN se chave não existe em PT, e para `<key>` se não existe em nenhum
- Documentação espelhada: `README.md` (PT) + `README.en.md` (EN)

### `prompts.toml` completo (defaults)

```toml
# ============================================================
# UI strings — Português (Brasil)
# ============================================================
[ui.pt-br]
# App
app_title = "Whisper Microfone"
app_subtitle = "Ditado por voz local"
quit_confirm_title = "Sair"
quit_confirm_message = "Tem certeza que deseja sair?"

# Sidebar
sidebar_home = "Início"
sidebar_monitor = "Monitor"
sidebar_config = "Configurações"
sidebar_history = "Histórico"
sidebar_about = "Sobre"

# Status states
status_idle_warm = "Pronto"
status_idle_cold = "Pronto (modelo descarregado)"
status_loading = "Carregando IA..."
status_recording = "Ouvindo..."
status_transcribing = "Processando..."
status_paused = "Pausado"
status_error = "Erro"

# Buttons
btn_pause = "Pausar"
btn_resume = "Retomar"
btn_load_model = "Carregar modelo"
btn_unload_model = "Descarregar modelo"
btn_preheat = "Pré-aquecer"
btn_disable_ptt = "Desativar PTT"
btn_enable_ptt = "Ativar PTT"
btn_copy_last = "Copiar última"
btn_open_logs = "Abrir logs"
btn_open_config_file = "Abrir config.toml"
btn_apply = "Aplicar"
btn_cancel = "Cancelar"
btn_save = "Salvar"
btn_clear = "Limpar"
btn_export = "Exportar"

# Cards
card_status = "Status"
card_consumption = "Consumo em tempo real"
card_last_transcription = "Última transcrição"
card_quick_actions = "Ações rápidas"
card_session_stats = "Estatísticas da sessão"

# Stats
stat_transcriptions_today = "Transcrições hoje"
stat_avg_latency = "Latência média"
stat_chars_dictated = "Caracteres ditados"
stat_total_dictation_time = "Tempo total ditando"
stat_model_loads = "Carregamentos do modelo"

# Tray tooltips
tray_paused = "Whisper pausado — clique para ativar"
tray_idle_warm = "Pronto • Latência mínima"
tray_idle_cold = "Pronto • Modelo descarregado"
tray_loading = "Carregando IA..."
tray_recording = "Ouvindo..."
tray_transcribing = "Processando..."
tray_error = "Erro — clique para detalhes"

# Tray menu
tray_menu_show = "Mostrar janela"
tray_menu_pause = "Pausar PTT"
tray_menu_resume = "Retomar PTT"
tray_menu_load = "Carregar modelo agora"
tray_menu_unload = "Descarregar modelo"
tray_menu_quit = "Sair"

# Config page sections
config_section_app = "Aplicação"
config_section_model = "Modelo"
config_section_lifecycle = "Ciclo de vida"
config_section_audio = "Áudio"
config_section_vad = "VAD (detecção de voz)"
config_section_transcription = "Transcrição"
config_section_injection = "Injeção de texto"
config_section_ui = "Interface"
config_section_history = "Histórico"
config_section_logging = "Logs"
config_section_theme = "Tema"
config_section_shortcuts = "Atalhos"

# Errors
error_cuda_not_available = "CUDA não disponível. Instale drivers NVIDIA atualizados."
error_model_load_failed = "Falha ao carregar modelo: {error}"
error_audio_device = "Erro ao acessar microfone: {error}"
error_hotkey_register = "Falha ao registrar atalho global: {hotkey}"
error_no_speech_detected = "Nenhuma fala detectada"

# Notifications
notif_model_loaded = "Modelo carregado em {seconds:.1f}s"
notif_model_unloaded = "Modelo descarregado por inatividade"
notif_config_reloaded = "Configuração recarregada"
notif_history_cleared = "Histórico limpo"

# About
about_version = "Versão"
about_gpu = "GPU detectada"
about_cuda = "CUDA"
about_model = "Modelo carregado"
about_license = "Licença"
about_repo = "Repositório"

# History
history_search_placeholder = "Buscar nas transcrições..."
history_filter_language = "Filtrar idioma"
history_empty = "Nenhuma transcrição ainda"
history_column_time = "Hora"
history_column_language = "Idioma"
history_column_text = "Texto"
history_column_duration = "Duração"
history_column_latency = "Latência"

# ============================================================
# UI strings — English
# ============================================================
[ui.en]
# App
app_title = "Whisper Microphone"
app_subtitle = "Local voice dictation"
quit_confirm_title = "Quit"
quit_confirm_message = "Are you sure you want to quit?"

# Sidebar
sidebar_home = "Home"
sidebar_monitor = "Monitor"
sidebar_config = "Settings"
sidebar_history = "History"
sidebar_about = "About"

# Status states
status_idle_warm = "Ready"
status_idle_cold = "Ready (model unloaded)"
status_loading = "Loading AI..."
status_recording = "Listening..."
status_transcribing = "Processing..."
status_paused = "Paused"
status_error = "Error"

# Buttons
btn_pause = "Pause"
btn_resume = "Resume"
btn_load_model = "Load model"
btn_unload_model = "Unload model"
btn_preheat = "Pre-heat"
btn_disable_ptt = "Disable PTT"
btn_enable_ptt = "Enable PTT"
btn_copy_last = "Copy last"
btn_open_logs = "Open logs"
btn_open_config_file = "Open config.toml"
btn_apply = "Apply"
btn_cancel = "Cancel"
btn_save = "Save"
btn_clear = "Clear"
btn_export = "Export"

# Cards
card_status = "Status"
card_consumption = "Real-time consumption"
card_last_transcription = "Last transcription"
card_quick_actions = "Quick actions"
card_session_stats = "Session statistics"

# Stats
stat_transcriptions_today = "Transcriptions today"
stat_avg_latency = "Average latency"
stat_chars_dictated = "Characters dictated"
stat_total_dictation_time = "Total dictation time"
stat_model_loads = "Model loads"

# Tray tooltips
tray_paused = "Whisper paused — click to activate"
tray_idle_warm = "Ready • Minimal latency"
tray_idle_cold = "Ready • Model unloaded"
tray_loading = "Loading AI..."
tray_recording = "Listening..."
tray_transcribing = "Processing..."
tray_error = "Error — click for details"

# Tray menu
tray_menu_show = "Show window"
tray_menu_pause = "Pause PTT"
tray_menu_resume = "Resume PTT"
tray_menu_load = "Load model now"
tray_menu_unload = "Unload model"
tray_menu_quit = "Quit"

# Config page sections
config_section_app = "Application"
config_section_model = "Model"
config_section_lifecycle = "Lifecycle"
config_section_audio = "Audio"
config_section_vad = "VAD (voice activity detection)"
config_section_transcription = "Transcription"
config_section_injection = "Text injection"
config_section_ui = "Interface"
config_section_history = "History"
config_section_logging = "Logs"
config_section_theme = "Theme"
config_section_shortcuts = "Shortcuts"

# Errors
error_cuda_not_available = "CUDA not available. Install up-to-date NVIDIA drivers."
error_model_load_failed = "Failed to load model: {error}"
error_audio_device = "Error accessing microphone: {error}"
error_hotkey_register = "Failed to register global hotkey: {hotkey}"
error_no_speech_detected = "No speech detected"

# Notifications
notif_model_loaded = "Model loaded in {seconds:.1f}s"
notif_model_unloaded = "Model unloaded due to inactivity"
notif_config_reloaded = "Configuration reloaded"
notif_history_cleared = "History cleared"

# About
about_version = "Version"
about_gpu = "Detected GPU"
about_cuda = "CUDA"
about_model = "Loaded model"
about_license = "License"
about_repo = "Repository"

# History
history_search_placeholder = "Search transcriptions..."
history_filter_language = "Filter by language"
history_empty = "No transcriptions yet"
history_column_time = "Time"
history_column_language = "Language"
history_column_text = "Text"
history_column_duration = "Duration"
history_column_latency = "Latency"

# ============================================================
# Optional Whisper prompts (initial_prompt parameter)
# ============================================================
[whisper_prompts]
default = ""
technical_pt = "Transcrição técnica de programação. Termos comuns: API, Python, função, variável, classe, debug, commit, branch."
technical_en = "Technical programming transcription. Common terms: API, Python, function, variable, class, debug, commit, branch."
medical_pt = "Transcrição médica. Termos clínicos."
medical_en = "Medical transcription. Clinical terms."
legal_pt = "Transcrição jurídica."
legal_en = "Legal transcription."
```

---

## 10. Performance esperada na RTX 3050 6GB

### Latência

| Etapa | Tempo |
|---|---|
| Captura (durante fala) | 0 (streaming) |
| VAD trim | ~10 ms |
| Whisper small int8_float16 (5s áudio) | ~350-450 ms |
| Injeção (digitação 50 chars) | ~250 ms |
| **Total percebido após soltar tecla** | **~700 ms** |
| Carga do modelo (a frio, 1ª vez) | ~3-5 s (escondido durante a fala) |
| Carga do modelo (cache de disco) | ~1-2 s |

### Footprint

| Estado | RAM total | VRAM | Notas |
|---|---|---|---|
| App rodando, janela fechada (idle frio) | ~140 MB | 0 | UI carregada mas sem renderizar |
| App rodando, janela aberta no Início | ~180 MB | 0 | UI ativa atualizando 2x/s |
| App em uso (modelo quente) | ~750 MB | ~1.3 GB | Soma motor + UI |
| Janela minimizada para tray | ~140 MB | 0 ou 1.3 GB | Depende do estado do modelo |

A UI adiciona ~60-80 MB sobre o motor puro.

---

## 11. Plano de implementação por etapas

> Cada etapa termina com **smoke test manual** + **testes automatizados** quando aplicável. **Commitar ao final de cada etapa** — ver `CLAUDE.md` na raiz para o protocolo de SSH (conta `Gustavo1341`) e formato de commit.

### Fase 1 — Fundação

| # | Etapa | Entregável | Verificação |
|---|---|---|---|
| 1 | Setup do projeto | `pyproject.toml`, `requirements.txt`, `.gitignore`, venv, estrutura de pastas vazias | `pip install -r requirements.txt` ok |
| 2.1 | Schemas Pydantic em `config/schemas.py` | Todos os schemas (App, Model, Lifecycle, Audio, VAD, Transcription, Injection, UI, History, Logging, Theme, Shortcuts, Prompts, ModelsCatalog, Advanced, FullConfig) | `pytest tests/config/test_schemas.py` |
| 2.2 | Defaults TOML em `config/defaults/` | 6 arquivos: config, theme, shortcuts, prompts (PT+EN completo), models, advanced | Carregam sem erro |
| 2.3 | `config/paths.py` | `appdata_dir()`, `models_dir()`, `logs_dir()`, `assets_dir()`, override portátil | Cria pastas no 1º run |
| 2.4 | `config/loader.py` | Merge defaults + user + env, validação Pydantic, retorna `FullConfig` | `load_config()` funciona |
| 2.5 | `config/watcher.py` | Watchdog + sinal `config_changed` | Editar TOML dispara reload |
| 2.6 | `i18n/translator.py` | Carrega `prompts.toml`, função `t(key, **kwargs)` | Trocar idioma em runtime |
| 2.7 | `logging_setup.py` (loguru) | Logs rotativos em `logs_dir()` | Arquivo gerado |
| 2.8 | `scripts/gen_docs.py` | Gera `docs/CONFIG.md` e `docs/CONFIG.en.md` | Docs criados |

### Fase 2 — Motor

| # | Etapa | Entregável | Verificação |
|---|---|---|---|
| 3 | `core/audio.py` | Captura + script `scripts/test_audio_devices.py` | Grava 3s e salva WAV legítimo |
| 4 | `core/vad.py` | Silero VAD + trim | Áudio de saída < entrada quando há silêncio |
| 5 | `core/transcriber.py` | faster-whisper + lazy load + auto-unload | Transcreve PT e EN, descarrega após timeout |
| 6 | `core/metrics.py` | pynvml + psutil | Retorna RAM/VRAM/GPU/CPU corretos |
| 7 | `core/injector.py` | type → paste fallback + restore clipboard | Injeta "olá ção" em Notepad com acentos |
| 8 | `core/hotkey.py` | Push-to-talk pynput | Press/release detectados, console mostra |
| 9 | `core/history.py` | SQLite store | Adiciona, lista, limpa transcrições |

### Fase 3 — Bridge motor + UI

| # | Etapa | Entregável | Verificação |
|---|---|---|---|
| 10 | `engine.py` (QObject + sinais) | Pipeline ponta-a-ponta sem UI gráfica | Hotkey → texto no Notepad |

### Fase 4 — Interface

| # | Etapa | Entregável | Verificação |
|---|---|---|---|
| 11 | `ui/theme.py` + `ui/app.py` | QApplication com PyQtDarkTheme | Janela vazia abre com tema dark |
| 12 | `ui/main_window.py` (sidebar + roteamento) | Sidebar VS Code-like com 5 itens | Troca entre páginas vazias |
| 13 | `ui/widgets/` | metric_bar, live_chart (pyqtgraph), status_card, transcription_card, hotkey_capture | Widgets isolados funcionam |
| 14 | `ui/pages/home.py` | Status + métricas resumidas + última transcrição + ações | Reflete estado real do motor |
| 15 | `ui/pages/monitor.py` | 4 gráficos pyqtgraph + estatísticas da sessão | Atualiza a cada 500ms |
| 16 | `ui/pages/config_page.py` | Formulário completo + validação + apply sem restart | Edita config.toml via UI |
| 17 | `ui/pages/history.py` | Tabela + busca + filtros + export | Lista últimas transcrições |
| 18 | `ui/pages/about.py` | Versão, GPU, CUDA, modelo, licença | Diagnóstico completo |
| 19 | `ui/tray.py` | QSystemTrayIcon + 6 estados + menu | Minimiza p/ tray, ícone muda |

### Fase 5 — Empacotamento e polimento

| # | Etapa | Entregável | Verificação |
|---|---|---|---|
| 20 | `run.bat` + atalho startup opcional | Inicia minimizado com Windows (configurável) | Reboot → roda sozinho |
| 21 | README.md (PT) + README.en.md | Instalação, uso, troubleshooting, screenshots | Usuário consegue instalar do zero |
| 22 | Build com PyInstaller | `whisper-microfone.exe` portátil | Roda em máquina sem Python |
| 23 | Workflow GitHub Actions | Build automático em release | Tag → release com .exe |
| 24 | LICENSE (MIT) + CHANGELOG.md | Licença + histórico | Pronto para publicação |

---

## 12. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| cuDNN não encontrado em runtime | Alta | Wheels `nvidia-cublas-cu12` e `nvidia-cudnn-cu12` no requirements; documentar no README |
| Driver NVIDIA antigo / sem CUDA | Média | Validar `nvidia-smi` no startup; fallback automático para CPU (int8) com aviso visual |
| Hotkey conflita com outro app | Média | Config editável via UI; lista de combinações comuns conflitantes no docs |
| Apps elevados (admin) ignoram pynput | Baixa | Documentar; opcional: criar tarefa agendada com "Run with highest privileges" |
| Alucinações Whisper em silêncio | Média | VAD + `no_speech_threshold=0.6` + `condition_on_previous_text=False` |
| Modelo demora a baixar 1ª vez | Alta (1ª vez) | Pré-download via `scripts/pre_download_model.py`; barra de progresso no 1º uso |
| GPU compartilhada com jogos/Premiere | Alta | Auto-unload após inatividade libera VRAM; "Pausar PTT" via hotkey global |
| pynput não detecta Win key em alguns layouts | Baixa | Documentar; permitir combinações alternativas |
| QSystemTrayIcon falha em algumas distros Windows | Baixa | Fallback para `pystray` |
| Erros de threading entre Qt e workers | Média | Sempre usar `Signal/Slot`; nunca tocar widgets fora da main thread |
| Texto com emoji ou Unicode raro falha digitação | Baixa | Estratégia híbrida cai para clipboard automaticamente |

---

## 13. Hardware de referência

- **GPU:** NVIDIA RTX 3050 6 GB
- **OS:** Windows 11 Pro 10.0.26200
- **Python:** 3.11+ recomendado (3.12 OK)
- **Driver NVIDIA:** atualizado (suporta CUDA 12)

> Não exige instalação de CUDA Toolkit — wheels `nvidia-cublas-cu12` e `nvidia-cudnn-cu12` resolvem em userspace.

---

## 14. Decisões já tomadas pelo usuário

| Pergunta | Resposta |
|---|---|
| GPU/VRAM | RTX 3050 6 GB — modelo que **não consuma muito** |
| Idioma | PT-BR + EN (multilíngue) |
| Modo de ativação | **Push-to-talk** (segura tecla) |
| Estratégia de injeção | Tenta digitar; se falhar, **Ctrl+V** |
| Comportamento de carga | **Lazy load + auto-unload** (motor de partida rápido) |
| Interface | **Estilo VS Code** (PySide6 + dark theme) |
| Hardcoded | **Zero** — tudo configurável em TOML |
| Idioma da documentação | PT-BR + EN desde o dia 1 |

---

## 15. Próximos passos no novo chat

1. Abrir novo chat com este `PLAN.md` anexado/colado
2. Solicitar: **"Leia o `PLAN.md` e inicie pela Etapa 1 (Setup do projeto). Siga sequencialmente, mostrando o resultado de cada etapa para revisão e commitando ao final de cada uma conforme o protocolo em `CLAUDE.md`."**
3. Conferir cada etapa antes de avançar
4. Ajustar o que precisar no caminho — é só editar este markdown e o assistente segue a versão atualizada
5. Commits são feitos ao final de cada etapa (ver `CLAUDE.md` para o protocolo SSH e formato)

---

## 16. Comandos rápidos esperados

```bash
# Instalação dev
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# Rodar
python -m whisper_microfone

# Testes
pytest

# Gerar docs de config
python scripts/gen_docs.py

# Listar dispositivos de áudio
python scripts/test_audio_devices.py

# Build executável
python scripts/build_exe.py
```

---

**Status:** Arquitetura aprovada, pronto para implementação.
**Data:** 2026-04-29
**Autor (planejamento):** Gustavo Brandão + Claude (Sonnet 4.6)
**Licença prevista:** MIT

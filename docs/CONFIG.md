# Referência de Configuração — Whisper Microfone

> **Gerado automaticamente** a partir dos schemas Pydantic em `config/schemas.py`.
> Não edite este arquivo manualmente — execute `python scripts/gen_docs.py` para atualizar.

## Como configurar

Os arquivos de configuração ficam em `%APPDATA%\whisper-microfone\config\` (Windows)
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

### Aplicação

**Arquivo:** `config.toml → [app]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `start_with_windows` | `bool` | `false` |  | Iniciar automaticamente com o Windows |
| `start_minimized` | `bool` | `true` |  | Iniciar minimizado na bandeja do sistema |
| `language_ui` | `Literal['pt-br', 'en']` | `"pt-br"` |  | Idioma da interface (pt-br ou en) |

### Modelo

**Arquivo:** `config.toml → [model]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `groq_model` | `str` | `"whisper-large-v3-turbo"` |  | Modelo Groq Whisper. Opções: whisper-large-v3-turbo, whisper-large-v3, distil-whisper-large-v3-en |
| `language` | `str` | `"auto"` |  | Idioma de transcrição. 'auto' = detecção automática. Exemplos: pt, en, es |

### Áudio

**Arquivo:** `config.toml → [audio]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `sample_rate` | `Literal[16000]` | `16000` |  | Taxa de amostragem em Hz. Whisper requer 16000 Hz |
| `channels` | `int` | `1` | ≥ 1, ≤ 2 | Canais de áudio. 1 = mono (recomendado para Whisper) |
| `device_name` | `str` | `""` |  | Nome do dispositivo de entrada. Vazio = dispositivo padrão do sistema |
| `device_index` | `int` | `-1` |  | Índice do dispositivo de entrada (sounddevice). -1 = dispositivo padrão |
| `min_duration_ms` | `int` | `300` | ≥ 100 | Duração mínima de áudio para processar (ms). Abaixo disso, descarta |
| `max_duration_seconds` | `int` | `60` | ≥ 5, ≤ 300 | Duração máxima de gravação por pressão de tecla (segundos) |

### VAD (detecção de voz)

**Arquivo:** `config.toml → [vad]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `enabled` | `bool` | `true` |  | Ativar VAD (Voice Activity Detection) com Silero para remover silêncio |
| `threshold` | `float` | `0.5` | ≥ 0.0, ≤ 1.0 | Threshold de probabilidade de fala (0.0-1.0). Mais alto = mais seletivo |
| `min_silence_ms` | `int` | `200` | ≥ 0 | Duração mínima de silêncio para considerar pausa entre falas (ms) |
| `speech_pad_ms` | `int` | `100` | ≥ 0 | Padding em ms adicionado ao redor dos segmentos de fala detectados |

### Transcrição

**Arquivo:** `config.toml → [transcription]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `initial_prompt` | `str` | `""` |  | Prompt inicial para o Whisper. Útil para termos técnicos. Vazio = sem prompt |
| `temperature` | `float` | `0.0` | ≥ 0.0, ≤ 1.0 | Temperatura de amostragem. 0.0 = determinístico (recomendado para ditado) |

### Injeção de texto

**Arquivo:** `config.toml → [injection]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `strategy` | `Literal['type_then_paste', 'paste_only', 'type_only']` | `"type_then_paste"` |  | Estratégia de injeção de texto: tenta digitar e cai para paste se falhar, só paste, ou só digitação |
| `type_delay_ms` | `int` | `5` | ≥ 0 | Delay entre cada caractere digitado (ms). Aumentar se a injeção perder caracteres |
| `paste_fallback_after_ms` | `int` | `1500` | ≥ 100 | Timeout em ms para fallback para paste quando strategy=type_then_paste |
| `restore_clipboard` | `bool` | `true` |  | Restaurar conteúdo anterior do clipboard após injeção via paste |
| `restore_clipboard_delay_ms` | `int` | `100` | ≥ 0 | Delay em ms antes de restaurar o clipboard |
| `trim_whitespace` | `bool` | `true` |  | Remover espaços em branco no início e fim do texto transcrito antes de injetar |
| `add_trailing_space` | `bool` | `false` |  | Adicionar espaço ao final do texto injetado (útil para ditado contínuo) |
| `capitalize_first` | `bool` | `false` |  | Capitalizar a primeira letra do texto transcrito |
| `sentence_end_punctuation` | `str` | `""` |  | Pontuação a adicionar ao final se o texto não terminar com pontuação. Vazio = não adicionar |

### Interface

**Arquivo:** `config.toml → [ui]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `show_tray_icon` | `bool` | `true` |  | Mostrar ícone na bandeja do sistema |
| `play_sounds` | `bool` | `true` |  | Reproduzir sons de feedback (início/fim de gravação) |
| `sound_volume` | `float` | `0.3` | ≥ 0.0, ≤ 1.0 | Volume dos sons de feedback (0.0-1.0) |
| `metrics_update_interval_ms` | `int` | `500` | ≥ 100, ≤ 5000 | Intervalo de atualização das métricas na UI (ms) |
| `chart_history_seconds` | `int` | `60` | ≥ 10, ≤ 300 | Janela de tempo exibida nos gráficos de métricas (segundos) |
| `window_width` | `int` | `900` | ≥ 400 | Largura inicial da janela principal (px) |
| `window_height` | `int` | `600` | ≥ 300 | Altura inicial da janela principal (px) |
| `remember_window_position` | `bool` | `true` |  | Lembrar posição e tamanho da janela entre sessões |

### Histórico

**Arquivo:** `config.toml → [history]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `enabled` | `bool` | `true` |  | Ativar armazenamento do histórico de transcrições |
| `store_text` | `bool` | `true` |  | Armazenar o texto das transcrições (desativar por privacidade) |
| `max_entries` | `int` | `500` | ≥ 10, ≤ 10000 | Número máximo de entradas no histórico |
| `auto_clean_after_days` | `int` | `30` | ≥ 1 | Limpar automaticamente entradas com mais de N dias. 0 = nunca limpar |

### Logs

**Arquivo:** `config.toml → [logging]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `level` | `Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']` | `"INFO"` |  | Nível de log. DEBUG para diagnóstico detalhado |
| `file_rotation_mb` | `int` | `10` | ≥ 1, ≤ 100 | Tamanho máximo do arquivo de log antes de rotacionar (MB) |
| `file_retention` | `int` | `5` | ≥ 1, ≤ 20 | Número máximo de arquivos de log a manter |
| `log_metrics` | `bool` | `false` |  | Logar métricas de RAM/CPU no arquivo de log (verboso) |

### Cores

**Arquivo:** `theme.toml → [colors]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `accent` | `str` | `"#007ACC"` |  | Cor de destaque principal (hex) |
| `accent_hover` | `str` | `"#1A8CD8"` |  | Cor de destaque ao passar o mouse (hex) |
| `recording` | `str` | `"#F44747"` |  | Cor do indicador de gravação (hex) |
| `transcribing` | `str` | `"#FFCC02"` |  | Cor do indicador de transcrição em andamento (hex) |
| `ready` | `str` | `"#89D185"` |  | Cor do indicador de pronto (hex) |
| `paused` | `str` | `"#858585"` |  | Cor do indicador de pausado (hex) |
| `error` | `str` | `"#F44747"` |  | Cor do indicador de erro (hex) |

### Fontes

**Arquivo:** `theme.toml → [fonts]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `family` | `str` | `"Segoe UI"` |  | Família de fonte da interface |
| `size_base` | `int` | `13` | ≥ 8, ≤ 24 | Tamanho base da fonte em pontos |
| `size_small` | `int` | `11` | ≥ 6, ≤ 20 | Tamanho de fonte pequena em pontos |
| `size_large` | `int` | `16` | ≥ 10, ≤ 32 | Tamanho de fonte grande em pontos |
| `monospace` | `str` | `"Consolas"` |  | Família de fonte monoespaçada |

### Layout

**Arquivo:** `theme.toml → [layout]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `sidebar_width` | `int` | `200` | ≥ 120, ≤ 400 | Largura da sidebar em pixels |
| `sidebar_icon_size` | `int` | `20` | ≥ 12, ≤ 48 | Tamanho dos ícones da sidebar em pixels |
| `card_padding` | `int` | `12` | ≥ 4, ≤ 32 | Padding interno dos cards em pixels |
| `card_radius` | `int` | `6` | ≥ 0, ≤ 20 | Raio de borda dos cards em pixels |
| `spacing` | `int` | `8` | ≥ 2, ≤ 24 | Espaçamento padrão entre elementos em pixels |

### Atalhos — Push-to-talk

**Arquivo:** `shortcuts.toml → [push_to_talk]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `combination` | `str` | `—` |  | Combinação de teclas no formato 'ctrl+alt+space' |
| `enabled` | `bool` | `true` |  | Atalho ativo |

### Atalhos — Popup

**Arquivo:** `shortcuts.toml → [open_mic_popup]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `combination` | `str` | `—` |  | Combinação de teclas no formato 'ctrl+alt+space' |
| `enabled` | `bool` | `true` |  | Atalho ativo |

### Catálogo — Modelo Groq

**Arquivo:** `models.toml → [[available_models]]`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `id` | `str` | `—` |  | ID do modelo na API Groq (ex: whisper-large-v3-turbo) |
| `display_name` | `str` | `—` |  | Nome amigável exibido na UI |
| `recommended` | `bool` | `false` |  | Marcar como recomendado na UI |
| `description_pt` | `str` | `""` |  | Descrição em PT-BR |
| `description_en` | `str` | `""` |  | Descrição em inglês |

### Avançado

**Arquivo:** `advanced.toml`

| Campo | Tipo | Default | Restrições | Descrição |
|---|---|---|---|---|
| `worker_thread_priority` | `Literal['normal', 'above_normal', 'high']` | `"normal"` |  | Prioridade das threads de worker (audio, transcription) |
| `audio_buffer_size` | `int` | `4096` | ≥ 512, ≤ 65536 | Tamanho do buffer de áudio em amostras (sounddevice blocksize) |
| `hotkey_poll_interval_ms` | `int` | `10` | ≥ 1, ≤ 100 | Intervalo de polling do listener de hotkey (ms) |
| `clipboard_timeout_ms` | `int` | `2000` | ≥ 500 | Timeout máximo para operações de clipboard (ms) |
| `sqlite_journal_mode` | `Literal['WAL', 'DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'OFF']` | `"WAL"` |  | Modo de journaling do SQLite para o histórico |
| `portable_mode` | `bool` | `false` |  | Modo portátil: armazena dados na pasta do executável em vez de %APPDATA% |

---

*Gerado por `scripts/gen_docs.py`*

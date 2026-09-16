# Whisper Microfone

![Status](https://img.shields.io/badge/status-Alpha%200.2.0-orange) ![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Licença](https://img.shields.io/badge/licença-MIT-green) ![Plataforma](https://img.shields.io/badge/plataforma-Windows-blue)

Substituto open source do Win+H do Windows. Pressione um atalho, fale, solte — o texto aparece onde o cursor estiver. Transcrição via [Groq Whisper API](https://console.groq.com/), sem modelo local, sem GPU necessária.

---

## Funcionalidades

- **Push-to-talk global** — atalho configurável (padrão: `Ctrl+Alt+Space`) funciona em qualquer janela
- **Transcrição via Groq** — usa a API Whisper da Groq; rápido, sem GPU, sem modelo local
- **Mini popup de ditado** — janela flutuante estilo dark card ativada por `Ctrl+F9`; mostra estado de gravação e countdown
- **VAD integrado** — Silero VAD remove silêncio antes de enviar, reduzindo alucinações e custo de API
- **Injeção inteligente de texto** — cola o texto diretamente na janela ativa via clipboard
- **Interface dark Apple-style** — 4 abas: Início, Config, Histórico, Sobre
- **Multilíngue** — interface em PT-BR e EN; transcrição em qualquer idioma suportado pelo Whisper
- **Zero hardcoded** — tudo configurável em arquivos TOML
- **Histórico de transcrições** — armazenamento local em SQLite, pesquisável pela interface
- **Bandeja do sistema** — roda em background sem ocupar a barra de tarefas

---

## Requisitos

| Componente | Versão mínima |
|---|---|
| Windows | 10 / 11 (64-bit) |
| Python | 3.11 ou superior |
| Groq API Key | Gratuita em [console.groq.com](https://console.groq.com/) |

> Não requer GPU. Toda a transcrição é feita na nuvem via Groq.

---

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/Gustavo1341/whisper-microphone.git
cd whisper-microphone

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar o arquivo de configuração com sua chave da Groq
echo GROQ_API_KEY=sua_chave_aqui > .env
```

Obtenha sua chave gratuita em [console.groq.com/keys](https://console.groq.com/keys).

---

## Iniciando

```bash
cd whisper-microphone
.venv\Scripts\activate
python -m whisper_microfone
```

O app minimiza para a bandeja do sistema. A janela principal pode ser aberta clicando no ícone da bandeja.

---

## Como usar

### Push-to-talk (`Ctrl+Alt+Space`)

1. Posicione o cursor em qualquer campo de texto (editor, browser, chat, etc.)
2. Segure `Ctrl+Alt+Space`
3. Fale
4. Solte — o texto transcrito é colado automaticamente onde o cursor estava

### Mini popup (`Ctrl+F9`)

Use quando não tiver um campo de texto ativo ou quiser ver o status da gravação:

1. Pressione `Ctrl+F9` — abre o popup flutuante com countdown de 1 segundo
2. Fale após o countdown
3. Pressione `Ctrl+F9` novamente — para a gravação e transcreve
4. O texto transcrito fica disponível no clipboard para colar onde quiser (`Ctrl+V`)

> **Nota sobre teclados de notebook:** Alguns teclados reportam `Ctrl+F9` como uma tecla especial internamente. Se o atalho não funcionar, verifique a seção de Troubleshooting abaixo.

---

## Atalhos padrão

| Atalho | Ação |
|---|---|
| `Ctrl+Alt+Space` | Push-to-talk (segurar para gravar, soltar para transcrever) |
| `Ctrl+F9` | Abrir/fechar mini popup de ditado |
| `Ctrl+Alt+P` | Pausar / retomar o listener de hotkey |
| `Ctrl+Alt+W` | Mostrar / esconder a janela principal |

Todos os atalhos são configuráveis em `%APPDATA%\whisper-microfone\config\shortcuts.toml`.

---

## Configuração

Os arquivos de configuração ficam em `%APPDATA%\whisper-microfone\config\` e são criados automaticamente na primeira execução.

| Arquivo | Conteúdo |
|---|---|
| `config.toml` | App, modelo, áudio, VAD, transcrição, injeção, UI, histórico, logs |
| `shortcuts.toml` | Atalhos de teclado |
| `theme.toml` | Cores, fontes e layout |
| `advanced.toml` | Configurações avançadas |

---

## Troubleshooting

**Popup não abre com `Ctrl+F9`**

Alguns teclados de notebook (especialmente com teclas Fn) reportam `Ctrl+F9` como `F17` para o sistema operacional. Se isso acontecer, edite `%APPDATA%\whisper-microfone\config\shortcuts.toml` e troque a combinação:

```toml
[open_mic_popup]
combination = "f17"
enabled = true
```

Para descobrir qual código sua tecla gera, você pode testar executando:
```bash
.venv\Scripts\python.exe -c "
from pynput.keyboard import Listener
def show(k): print(k)
with Listener(on_press=show) as l: l.join()
"
```

**Microfone não detectado**

Verifique os dispositivos disponíveis:
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```
Configure o microfone em `config.toml → [audio] → device_name` ou `device_index`.

**Texto não é colado na janela ativa**

O app usa clipboard para injetar texto. Certifique-se de que a janela alvo está em foco no momento em que a transcrição termina. Se a janela alvo rodar com privilégios elevados (ex.: Gerenciador de Tarefas), inicie o app também como Administrador.

**Erro de API Key**

Verifique se o arquivo `.env` na raiz do projeto contém `GROQ_API_KEY=sua_chave`. A chave pode ser obtida gratuitamente em [console.groq.com/keys](https://console.groq.com/keys).

---

## Licença

MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.

Autor: Gustavo Brandão

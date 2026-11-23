# Relatório v1.0.0, sessão agent

Branch: `feature/windows-app-agent`, PR para `feature/windows-app`. Spec: `docs/specs/spec-v1.0.0.md` (§0 e §2, com o Pillow como dependência direta). Handoff: `docs/handoff-v1.0.0.md` (Sessão agent). ADR: 0022. Contrato: "Agente como processo filho do app".

Máquina de todas as medições: i5-8500 (6 núcleos), UHD 630. Medições sem tocar nas portas 8080 e 8443, na câmera do usuário nem no `%LOCALAPPDATA%\wcam`: portas livres escolhidas na hora, câmera falsa e diretório de dados temporário.

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Spike (§0) e números | Feito; decisões do orquestrador registradas no contrato | scratchpad, números abaixo |
| 2. Modo filho (§2) | Feito | `wcam/parent_pipe.py`, `wcam/cli.py`, `wcam/app.py` |
| 3. Empacotamento PyInstaller em pasta | Feito | `agent/packaging/`, `wcam/config.py` |
| 4. Prioridade para o app | Feito no próprio agente, por decisão do orquestrador | `wcam/process_priority.py` |
| 5. Testes e versão | Feito; `version` 1.0.0 | `tests/`, `agent/pyproject.toml` |

## Critérios de aceitação tocados

| CA | Parte do agente | Resultado |
|---|---|---|
| 3 | Sobe pelo app e encerra junto | Cumprido do lado do agente: EOF no stdin encerra com código 0; pai morto encerra com código 0; porta ocupada sai com 3. O ciclo com o app é da sessão app |
| 7 | Nenhuma porta com o app fechado | Cumprido do lado do agente: com o pai morto, as duas portas fecham (medido com o pipe e com o Job Object). O `nmap` fica para a validação com o usuário |
| 8 | Decodificação na placa no executável; prioridade | Decodificação cumprida no executável gerado (teste de ponta a ponta abaixo). A prioridade está implementada, mas a medição na reunião de 15 min em 2160p30 fica para a validação com o usuário |
| 9 | Verificação e versão | Agent verde (seção Verificação); `version` 1.0.0 |

## Spike (§0)

Executável do PyInstaller 6.22.3 em pasta (Python 3.13.18, PyAV 17.1.0):

| Medida | Valor |
|---|---|
| Build | 45 a 85 s |
| Pasta | 158 a 160 MB, 272 arquivos; FFmpeg do PyAV 63 MB, numpy 27 MB, cryptography 17 MB, Pillow 13 MB |
| Primeiro `200` no `/api/health` | 7,25 s na primeira abertura depois do build, de 2 a 4 s nas seguintes, uma vez 9 s |
| Memória parado | 119 MB |
| DLL da câmera nativa | Carrega e lê o formato anunciado (1920x1080@30, parada). Publicar quadros ficou para a validação |

Para o executável funcionar:
- `--collect-data wcam`, sem o qual as migrations SQL ficam de fora e o agente cai ao abrir o banco;
- `--collect-submodules uvicorn`;
- `web/dist` e `locales` como dados.

Processo filho de decodificação (ADR 0018) dentro do executável:
- Com spawn e `freeze_support`, o filho é o próprio `wcam.exe`. Abre o dxva2 em 696 ms (595 ms fora do executável).
- `IMG_0641.MOV` (HEVC 3840x2160, 1198 quadros) decodificado inteiro na placa:

| | Executável | Python normal |
|---|---|---|
| Ritmo | 41,2 fps | 46,7 fps |
| Decodificação por quadro (filho) | 12,6 ms | 11,0 ms |
| Cópia por quadro | 7,8 ms | 6,7 ms |
| CPU do filho, de um núcleo | 53% | 53% |
| CPU do pai, de um núcleo | 20% | 22% |

Uma rodada de cada, então a diferença pode ser ruído. As duas ficam acima de 30 fps.

Modo filho, com um app falso que abre o agente e depois morre:

| Mecanismo | Resultado com o pai morto |
|---|---|
| Nenhum | Agente vivo e com as duas portas abertas |
| Job Object com `KILL_ON_JOB_CLOSE` | Agente, conhost e filho de decodificação somem em 0,04 a 0,08 s; os filhos herdam o job |
| stdin com leitura bloqueante numa thread | Abertura travada: o health passou de 40 s, porque o pipe síncrono serializa as outras operações no mesmo handle |
| stdin com `PeekNamedPipe` a cada 250 ms | Abertura normal; depois do EOF, saída limpa com código 0 em 0,47 a 0,73 s; com o filho de decodificação, tudo sai em 0,28 a 0,48 s |

Decisão do orquestrador: `PeekNamedPipe` no agente mais o Job Object no app; 5 s entre o EOF e o `TerminateJobObject`.

Prioridade:
- `AvSetMmThreadCharacteristicsW("Capture")` só registra a thread que faz a chamada. Leva de 40 a 57 µs dentro do executável e sobe a prioridade da thread.
- `ABOVE_NORMAL` posto de fora no agente não passa para o filho de decodificação, que nasce `NORMAL`.
- Decisão do orquestrador: cada processo do agente cuida da própria prioridade, sempre no Windows, e o app não mexe.

## O que foi feito

- `--child`:
  - O agente consulta o stdin a cada 250 ms (`PeekNamedPipe` no Windows, `select` no Linux).
  - No EOF, pede o encerramento pelo mesmo caminho do Ctrl+C.
  - Sem `--child`, o `uv run wcam` continua igual, sem a bandeja.
- Códigos de saída:
  - 0: encerramento pedido.
  - 2: sem rede local (já existia).
  - 3: porta ocupada (o uvicorn já sai com 3).
- Prioridade (`wcam/process_priority.py`, atrás de um `Protocol` com fake):
  - O processo principal e o filho de decodificação ficam em `ABOVE_NORMAL`, com o EcoQoS desligado.
  - MMCSS "Capture", uma vez por thread, em:
    - a thread do filho de decodificação;
    - a thread de entrega do `FramePipeline`;
    - a thread que decodifica o vídeo da biblioteca;
    - a thread do decodificador do celular, no `get_decoder` do aiortc.
  - Se o Windows recusar, fica só um aviso no log. Fora do Windows, nada muda.
- A bandeja Python (`wcam/tray`) saiu, e o `pystray` saiu do `pyproject.toml`.
  - O Pillow virou dependência direta, por causa da tira de miniaturas.
  - As chaves `tray.*` continuam nos locales, porque o app usa.
- Empacotamento:
  - Build: `uv run pyinstaller packaging/wcam.spec`, a partir de `agent`, com o web já compilado em `web/dist`.
  - Saída em `agent/dist/wcam/` (`wcam.exe` e `_internal`).
  - No executável, o agente acha `web/dist` e `locales` na própria pasta, e as variáveis `WCAM_*` continuam valendo.
  - O PyInstaller entrou no grupo de desenvolvimento.
  - Sobra no build um aviso de `tzdata`, sem efeito no Windows.

## Testes novos

- Modo filho, com processos reais:
  - stdin fechado: código 0, mensagem de parado e nenhum traceback;
  - pai morto: código 0;
  - porta ocupada: código 3;
  - o agente roda acima do normal (Windows).
- O filho de decodificação roda acima do normal (Windows).
- Prioridade com fake: as duas chamadas; recusa só registrada no log; MMCSS uma vez por thread e em cada thread; a thread de entrega entra no MMCSS.
- Pipe com `os.pipe` real, aberto e fechado; o vigia para quando o pipe fecha e não para enquanto o pipe está aberto.
- Caminhos de `web/dist` e `locales` no executável e no repositório.
- Executável empacotado, de ponta a ponta. O teste é pulado sem o executável gerado. Ele faz:
  - `wcam.exe --child` em portas livres;
  - celular aiortc real pareado e confirmado dos dois lados;
  - vídeo enviado e ativado;
  - confere o decodificador `hardware` no status;
  - confere que o filho de decodificação é o próprio `wcam.exe`;
  - confere a saída com código 0 no EOF.

## Verificação

A partir de `agent`, no Windows:
- `uv run ruff check` e `uv run ruff format --check`: limpos.
- `uv run pyright`: 0 erros.
- `uv run pytest`: 567 passaram e 1 foi pulado. Com o executável gerado, o teste de ponta a ponta do empacotamento também passou.

`npm run test:e2e`: no Docker, num worktree temporário, com `-p` próprio e sem portas no host (seção abaixo).

## Não verificado

Fica para a validação com o usuário:
- `/api/health` e encerramento com o celular conectado e o 4K decodificando (o prazo combinado é de 5 s).
- Publicar quadros na câmera nativa de dentro do executável.
- Prioridade numa reunião de 15 min em 2160p30 contra a v0.10.0 (CA 8). Se não ajudar, sai.
- `nmap` com o app aberto e fechado (CA 7).

## e2e e Linux

- `npm run test:e2e` no Docker, num worktree temporário em 42d47fa, com `-p wcam-agent-e2e` e um override com `ports: !reset []` no agent e no web: 33 passaram em 4,8 min. O `npm error` do contêiner web no fim é o Vite recebendo SIGTERM no encerramento.
- CI do push 42d47fa: web, e2e, vcam e agent no Windows verdes. No agent do Ubuntu, falhou o teste do pai morto: no Linux o psutil não devolve o código de saída de um processo que não é filho direto. O teste passou a conferir a saída do agente (mensagem de parado, sem traceback), que vale nos dois sistemas.
- Testes do modo filho, do pipe, da prioridade, dos caminhos e de encerramento num contêiner `python:3.13-slim`: 16 passaram e 1 foi pulado (o de prioridade, só Windows).

# 0018. Decodificação na placa de vídeo num processo separado

Status: Aceita
Data: 2026-11-16
Complementa: ADR 0014 (decodificação no hardware como próximo passo)

## Contexto
A spec v0.10.0 §1.6 pediu um spike antes do código. Medido no PC do usuário (i5-8500, Intel UHD 630, driver 31.0.101.2141), PyAV 17.1.0 e aiortc 1.15.0, com 300 quadros do `IMG_0641.MOV` recodificados em H.264 Constrained Baseline (o perfil que o celular negocia) e High, e com o próprio MOV (HEVC Main 4K):

- O PyAV instalado oferece `d3d11va`, `dxva2`, `d3d12va`, `qsv`, `cuda` e `amf`. A UHD 630 decodifica H.264 CB e High, HEVC Main e Main 10 em `d3d11va`, `dxva2`, `d3d12va` e `qsv`.
- Os quadros da placa de vídeo são iguais byte a byte aos do software em todos os caminhos (300 de 300 por arquivo; Main 10 comparado em 10 bits).
- Decodificar e deixar o quadro na placa custa de 3 a 4 ms em 2160p e quase nada de CPU. O custo está na cópia para a memória e na passagem de NV12 para I420.
- No PyAV, a cópia dos caminhos `d3d11va`, `dxva2` e `d3d12va` (`av_hwframe_transfer_data` em `_transfer_hwframe`) segura o GIL: de 14 ms (`dxva2`) a 30 ms (`d3d11va`, `d3d12va`) por quadro em 2160p. No processo do agente, isso trava o event loop a cada quadro.
- Só `qsv` e o software soltam o GIL. O `qsv` funciona só com placa Intel e, com o celular em 4K, gasta tanta CPU na cópia quanto o software (cerca de 45% contra 41% de um núcleo).

| 2160p30, por quadro (% de um núcleo) | Software | `dxva2` | `d3d11va` | `qsv` |
|---|---|---|---|---|
| H.264 CB (celular) | 14,4 ms, 42% | 21,7 ms, 41% (21% sem I420) | 31,6 ms, 27% | 25 a 30 ms, 45% |
| MOV HEVC 4K | 12,2 ms, 179% | 15,0 ms, 35% (21% sem I420) | 27,8 ms, 27% | 14,3 ms, 60% |
| GIL preso por quadro | não | cerca de 14 ms | cerca de 30 ms | não |

Opções consideradas:
- **`qsv` no processo do agente**: menos código e sem dependência nova, mas só Intel, e não reduz a CPU com o celular.
- **Corrigir o PyAV** para soltar o GIL na cópia: uma linha, mas exige esperar uma versão nova ou manter uma wheel própria como dependência.
- **`dxva2` num processo de decodificação separado**: o GIL do processo filho não trava o agente, funciona com qualquer fabricante e isola falha de driver. Custa o ciclo de vida do processo e mais uma cópia por memória compartilhada (de 2 a 3 ms em 4K).
- **Media Foundation pelo `vcam`, ou outra biblioteca**: custo alto, sem ganho sobre a anterior.
- **Imagem na placa de vídeo de ponta a ponta** (cor na placa e textura compartilhada com o `vcam`): é a única forma de tirar a cópia, mas muda a arquitetura (MAJOR). Fica fora da v0.10.0.

Escolha do usuário em 2026-11-16: processo separado.

## Decisão
- A decodificação na placa de vídeo roda num processo filho do agente, um por fonte (celular e vídeo da biblioteca), com dono e encerramento explícitos. Os pacotes entram por fila; os quadros saem por memória compartilhada, com o processo do agente lendo fora do event loop.
- Caminho no filho: `dxva2`, com cópia para a memória no próprio filho. Sem placa, sem o codec ou o perfil, ou com o filho falhando ao abrir, a fonte usa o software do PyAV no processo do agente, como na v0.9.0.
- Encaixe no aiortc pela troca de `get_decoder` importado por `aiortc.rtcrtpreceiver`: uma fábrica devolve o decodificador do WCam para `video/H264` e o original para os outros codecs, com verificação na partida. O aiortc não é copiado.
- Falha no meio do fluxo (erro do FFmpeg ou o filho caindo): a fonte passa para software no próximo quadro-chave, e o decodificador pede um PLI ao receptor da sessão atual (`_send_rtcp_pli` por `run_coroutine_threadsafe`). A sessão não cai e o vídeo não para.
- `WCAM_HW_DECODE=off` não cria o processo filho.
- A CPU do WCam (`process.cpuPercent` e o CA 2 da spec) soma o agente e os processos filhos.
- Sem dependência nova: `multiprocessing` e `multiprocessing.shared_memory` da biblioteca padrão.

## Consequências
- A CPU do vídeo 4K da biblioteca cai de cerca de 179% para cerca de 35% de um núcleo; com o celular em 4K, a decodificação cai pouco. O CA 2 com o celular depende da tradução de cor (§1.2), que pode ler NV12 direto e pular a passagem para I420 (de 5 a 7 ms em 4K).
- Uma falha de driver derruba só o processo filho, nunca o agente.
- O agente passa a ter processos filhos para encerrar junto com ele, inclusive no fechamento pela bandeja e no PyInstaller (`freeze_support`).
- Se uma versão futura do PyAV soltar o GIL na cópia, o processo filho pode voltar para dentro do agente com uma ADR nova.

# Relatório v0.9.0, sessão agent

Branch: `feature/video-agent`, PR para `feature/video`. Spec: `docs/specs/spec-v0.9.0.md`; handoff: `docs/handoff-v0.9.0.md` (Sessão agent); ADR 0016.

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Arquivo | Feito | `video/store.py`, `video/errors.py`, `api/console_routes.py` |
| 2. Reprodução | Feito | `video/playback.py`, `video/frames.py`, `media/pipeline.py` |
| 3. Ativar e desativar | Feito | `video/source.py`, `sessions/manager.py`, `sessions/controls.py`, `services.py` |
| 4. Linha do tempo | Feito | `video/playback.py`, `video/source.py`, `api/console_routes.py` |
| 5. Bandeja | Feito; bandeja real no Windows não verificada | `tray/` |
| 6. Testes | Feito; CPU do CA 6 pendente dos arquivos do usuário | `tests/` |
| 7. Versão 0.9.0 | Feito | `agent/pyproject.toml` |
| Vídeo de teste do e2e | Feito (combinado com a web e o orquestrador) | `tools/make_test_video.py` |

## Arquivo (§1.1)

- Domínio novo `wcam/video`, sem FastAPI nem aiortc. `VideoStore` grava o corpo de `request.stream()` num arquivo temporário (`.upload-<id>`) dentro de `<diretório de dados>/video/`, juntando 4 MB antes de cada escrita, feita numa thread (`asyncio.to_thread`). Nada do vídeo fica inteiro na memória.
- Limite de 20 GB contado durante o envio: passou, o envio para, o temporário é apagado e a resposta é `413 video_too_large`. Um `Content-Length` declarado acima do limite dá `413` antes de ler o corpo.
- Limite do uvicorn e do Starlette: nenhum dos dois limita o tamanho do corpo lido por `request.stream()`, então o único limite é o do agente.
- Validação em thread: `av.open`, primeira faixa de vídeo, primeiro quadro decodificado e duração maior que zero. Falhou, o temporário é apagado e a resposta é `422 video_unsupported`. Uma imagem PNG abre no FFmpeg como vídeo de um quadro sem duração e é recusada por essa regra (teste).
- Só depois da validação o arquivo anterior é apagado e o novo ganha o nome original, limpo de caminho e de caracteres inválidos no Windows. Um envio recusado mantém o vídeo anterior guardado (desativado, porque o envio desativa antes).
- `width` e `height` são os de exibição, com a rotação gravada aplicada: vídeo em pé sai com altura maior que largura. `fps` é a taxa média do arquivo, com 2 casas; `durationSeconds`, com 3.
- Reinício: `VideoStore.load()` no `cli` procura o vídeo no diretório, apaga envios interrompidos e arquivos que não decodificam mais. O estado ativo não é guardado. Depois de reiniciar, o nome é o do arquivo em disco (o original já limpo).
- `X-File-Name` ausente ou vazio: `422 invalid_request`.

## Reprodução (§1.2)

- `VideoPlayback` é uma tarefa com dono (`VideoSource`), cancelada ao desativar, ao remover, ao trocar o arquivo e no encerramento do agente (`app.run`). Decodificação e conversão rodam num executor próprio (`wcam-video`), com threads de decodificação do FFmpeg (`thread_type AUTO`).
- Ritmo: a cada tique da câmera (1 / fps anunciado), o tempo do vídeo avança pelo relógio, não pela decodificação. O decodificador avança até o último quadro com `pts` menor ou igual a esse tempo, sem converter os quadros pulados, e converte só o que vai para a câmera. Um quadro repetido (vídeo com fps menor) reaproveita a conversão.
- Relógio e espera injetáveis para teste. Achado no Windows: o timer do asyncio acorda em passos de cerca de 15,6 ms, e um vídeo em pé de 60 fps entregou só 21,7 fps à câmera. A espera passou para `time.sleep` numa thread (timer de alta resolução no Windows), e um tique atrasado é compensado no seguinte; só um atraso maior que um período inteiro recomeça a contagem. Com isso, 30,0 fps nos dois vídeos medidos.
- Conversão (`video/frames.py`): rotação gravada lida de `frame.rotation` (matriz de exibição, convenção do FFmpeg: anti-horário em graus); o quadro é reduzido no tamanho já girado, com `reformat` para I420, BT.709 e faixa limitada, interpolação por área, e depois girado em numpy plano a plano. Proporção diferente ganha faixas pretas Y=16, UV=128 centralizadas, pelo mesmo `paste_i420` do retrato do celular. HDR sem mapeamento de tom.
- Volta ao começo: quando o tempo do vídeo passa da duração, ele volta por módulo e o decodificador busca o início; até o primeiro quadro novo, a câmera continua com o último quadro do fim. Nenhum quadro preto entre as voltas (teste).
- Pipeline: origem nova `FrameSource.VIDEO` (`virtualCamera.source` `video`). O quadro do vídeo entra na mesma fila do celular e é entregue pelo mesmo worker; nos tiques sem quadro novo, o pipeline repete o último quadro do vídeo. Espelho invertendo as colunas de Y, U e V; congelamento pelo `held` que já existia. A medição de SSIM só vale para quadros do celular.
- `/dev`: `delivered` e as etapas valem para o vídeo ativo. `decode` é o avanço do decodificador; `color` é rotação, redução e faixas; `deliver` e `total` como no celular. Evento `video_source` (`{"active", "name"}`) ao ativar e ao desativar.

## Ativar e desativar (§1.3)

- `PUT /api/video-source {"active"}` (modelo estrito). Ativar sem arquivo: `409 no_video_file`; `DELETE /api/video-source/file` sem arquivo: `404 no_video_file`. Os dois códigos iguais com status diferentes usam um `status_code` opcional no `AgentError`.
- Ativar: o gerenciador fecha a janela do QR, encerra a sessão com `video_source` (o celular recebe `session_state ended video_source`) e passa a recusar `POST /api/pairing` com `409 video_source_active`. Desativar volta ao quadro de espera e reabre a possibilidade de parear.
- Controles: `frozen` vale sem celular com o vídeo ativo; `cameraOff` e `facing` continuam `409 no_live_session`; `mirror` vale sempre. Desativar descongela.
- Falha inesperada na reprodução (arquivo apagado por fora, por exemplo) registra no log e desativa o vídeo, em vez de deixar a câmera parada.

## Linha do tempo (§1.4)

- `positionSeconds` é o `pts` do quadro entregue, relativo ao início da faixa, com 3 casas; `null` com o vídeo desativado. Mudança só de posição não publica no SSE.
- `PUT /api/video-source/position {"seconds"}` (modelo estrito): fora de `[0, durationSeconds)`, incluindo NaN e infinito, `422 invalid_request`; desativado, `409 video_source_inactive`. O pedido é guardado e atendido no próximo tique: busca no quadro-chave anterior (`seek` com `backward`), decodifica sem entregar até o ponto, entrega esse quadro e segue no mesmo ritmo. Durante a busca a câmera repete o último quadro.
- Congelar para a posição; ao descongelar, o vídeo segue de onde parou. Pular com a imagem congelada entrega o quadro do novo ponto no lugar do congelado e continua congelado.

## Bandeja (§1.5)

- Item "Usar vídeo" (`tray.use_video`) marcável, desabilitado sem arquivo, marcado com o vídeo ativo; liga e desliga pelo mesmo `VideoSource` das rotas.
- Sexto estado `video`: triângulo de reprodução apontando para a direita em `#e6e6e6` (`--data-2`), dica com `state.video`. Com o vídeo ativo e congelado, o estado é o de imagem congelada. Congelar fica habilitado com o vídeo ativo.

## Vídeo de teste do e2e

- `python -m wcam.tools.make_test_video <saida.mp4>`: H.264 em MP4, 1280x720, 30 fps, 6 s, sem áudio, padrão determinístico (fundo Y=110, marcador claro no canto superior esquerdo, barra que anda), nunca preto. Os testes do agent usam a mesma função em tamanho pequeno, com fps e rotação variados. O compose da integração já gera `/reference/test-video.mp4` com ele.

## Testes

- `test_video_playback.py`: 4 s de relógio falso dão 4 × 30 quadros com vídeos de 15, 30 e 60 fps; 15 fps repete cada quadro; 60 fps pula um quadro por tique, sem câmera lenta; volta ao começo sem quadro preto; pular entrega o ponto pedido no próximo quadro e segue dali; posição parada enquanto congelado e retomada de onde parou; pular congelado entrega o novo ponto e continua congelado; regra de compensação do tique.
- `test_video_frames.py`: vídeo em pé com rotação gravada aparece em pé, marcador no canto certo, faixas laterais com Y=16 e UV=128; vídeo mais largo ganha faixas em cima e embaixo; vídeo maior é reduzido sem distorcer.
- `test_video_store.py`: metadados; texto e PNG recusados sem arquivo no disco; limite recusado sem arquivo; troca do vídeo; vídeo encontrado depois de reiniciar; remover; nome sem caminho.
- `test_video_pipeline.py`: quadro do vídeo na câmera com `source` `video`; repetição do último quadro entre quadros; espelho; congelado até um pulo trocar o quadro; desativar volta ao quadro de espera.
- `test_session_manager.py`: ativar encerra o celular com `video_source` e fecha o QR; pareamento recusado e reaberto; congelar sem celular com o vídeo; desativar descongela.
- `test_video_source_api.py`: as rotas com todos os códigos de erro, `videoSource` no status, evento do `/dev`. `test_tray.py`: item, estado e ação da bandeja.
- `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` (estrito) e `uv run pytest`: 482 passed, 1 skipped.

## CPU (CA 6)

Pendente: o usuário vai fornecer um vídeo 1080p30 H.264 e um 4K HEVC gravado no iPhone. A medição é um script fora do repositório: reprodução real, pipeline com câmera falsa, sem portas, 5 s de aquecimento e média de `psutil` por segundo durante 60 s, num PC de 6 núcleos.

Referência, com os mesmos números que vão para os arquivos do usuário (100% = um núcleo), câmera em 1080p30:

| Vídeo | CPU do processo | CPU da máquina | Quadros entregues | `color` mediana / p95 |
|---|---|---|---|---|
| Sintético 1080p30 H.264 (gerador de teste), 15 s | 66,6% | 11,1% | 30,0 fps | 6,0 / 21,3 ms |
| WhatsApp em pé, 384x848, 60 fps H.264, 15 s | 22,8% | 3,8% | 30,0 fps | 4,5 / 7,4 ms |

O vídeo sintético é mais fácil de decodificar que um vídeo real; o número do CA é o dos arquivos do iPhone.

## Não verificado

- Câmera WCam real (Media Foundation) com o vídeo no OBS, no app Câmera do Windows e no Meet (CA 1 a 4), e o pulo visto no Meet em até 1 s (CA 3). Precisa do agente nas portas do usuário; combinar com o orquestrador.
- Vídeo do iPhone: rotação real (o teste usa a matriz de exibição gravada pelo PyAV, a mesma convenção do FFmpeg) e HEVC 10 bits com HDR (cor lavada é a limitação aceita pela ADR 0016).
- Envio real de um arquivo grande pelo console (o limite de 20 GB está testado com um limite pequeno).
- Bandeja real no Windows com o sexto estado.
- e2e (`npm run test:e2e`) com o web: a sessão web está rodando contra esta branch.

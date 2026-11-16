# Relatório v0.9.0 revisão 2, sessão agent

Branch: `feature/video-agent`, PR para `feature/video`. Spec: `docs/specs/spec-v0.9.0.md` (revisão 2); handoff: `docs/handoff-v0.9.0-r2.md` (Sessão agent); ADR 0017. Relatório da revisão 1: `docs/relatorio-v0.9.0-agent.md`.

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Bugs (§1.6) | Linhas verdes: causa e correção com teste. Travamento: medido e corrigido o que era ritmo | `video/frames.py`, `video/playback.py` |
| 2. Biblioteca (§1.1) | Feito | `video/library.py`, `video/filmstrip.py`, `persistence/`, `api/console_routes.py` |
| 3. Linha do tempo (§1.2) | Feito | `video/timeline.py`, `video/source.py` |
| 4. Reprodução (§1.3) | Feito | `video/playback.py` |
| 5. Usar vídeo (§1.4) | Feito | `video/source.py`, `sessions/manager.py`, `sessions/phone_messages.py`, `media/pipeline.py`, `media/peer.py` |
| 6. Bandeja (§1.5) | Feito; bandeja real no Windows não verificada | `tray/` |
| 7. Testes e versão | Feito; `version` 0.9.0 conferida | `tests/`, `agent/pyproject.toml` |
| Vídeo de teste 2 do e2e | Feito (combinado com a web e o orquestrador) | `tools/make_test_video.py` (`portrait`) |

## Linhas verdes e azuis em 4K (§1.6, CA 7)

- Causa raiz: o `swscale` do FFmpeg 8 (libswscale 9.5, PyAV 17.1) roda com várias threads por padrão. Numa conversão de yuv420p para yuv420p no mesmo tamanho, ele deixa uma linha de croma sem escrever em cada borda de fatia. No `IMG_0641.MOV` com a câmera em 4K, as linhas de croma 308, 617 e 926 (luma 616, 1234 e 1852) saíam com U=V=0, o que dá verde com o Y normal, e, girado 180 graus, aparecia nas linhas 153, 462 e 771. Isso afeta o quadro entregue à câmera, e por isso aparecia no app Câmera e na prévia.
- Só acontece quando o tamanho de saída é igual ao do vídeo e a origem já é yuv420p BT.709 de faixa limitada (vídeo do iPhone em 4K com a câmera em 4K). Com redução ou com origem em 10 bits, nv12, yuvj420p ou 4:2:2, não acontece. O quadro decodificado estava limpo. Corrida entre threads, reaproveitamento de buffer e stride foram descartados.
- Correção, em duas partes:
  1. Quadro já no formato da câmera (yuv420p, BT.709, faixa limitada, mesmo tamanho) não passa pelo `swscale`. Os planos são copiados respeitando o `linesize`, e a rotação é feita na mesma cópia.
  2. Quando passa pelo `swscale` no mesmo tamanho (outra matriz ou faixa), a conversão roda com uma thread só.
- Testes:
  - `test_4k_conversion_without_scaling_keeps_every_chroma_row` falhava com `[308, 617, 926]` antes de `threads=1` e passa depois.
  - `test_4k_video_at_the_camera_size_keeps_every_row_of_the_picture` cobre o quadro entregue.
  - `test_frame_already_in_the_camera_format_is_copied_byte_for_byte` compara o caminho sem `swscale` com o `swscale` de uma thread, byte a byte.
- Varredura de 60 quadros do `IMG_0641.MOV` em 4K: 60 de 60 quadros com linhas zeradas antes da correção, 0 depois.

## Travamentos (§1.6, CA 8)

### Diagnóstico (antes)

Números de antes, com o código da revisão 1. Medi com um script no worktree: FramePipeline real, FakeSink, prévia simulada a 30 fps e câmera a 30 fps, de 20 a 50 s por caso depois de 5 s de aquecimento. A máquina já estava em 62% de CPU antes de começar, com as apps da bateria abertas.

| Caso | Quadros únicos por segundo (ideal 30) | Intervalo p99 / máximo | Intervalos acima de 66 ms |
|---|---|---|---|
| `IMG_0641` 4K HEVC, câmera 1080p | 28,1 | 89 / 183 ms | 18 em 20 s |
| 1080p H.264 (transcodificado do 0641), câmera 1080p | 29,2 | 76 / 82 ms | 19 em 20 s |
| 1080p H.264, câmera 4K | 25,7 | 93 / 156 ms | 23 em 20 s |
| `IMG_0641`, câmera 4K (4 rodadas) | 18,3 a 28,6 | 90 a 526 / 196 a 1624 ms | 7 a 49 acima de 100 ms |

- O event loop não era a causa: atraso mediano de 0,02 ms e p99 de até 0,33 ms. A entrega ao vcam levava menos de 1 ms, e nenhum quadro foi descartado no pipeline.
- Causa 1: decodificar, converter e girar era síncrono dentro do tick, numa thread só. Em 4K, isso levava de 15 a 18 ms na mediana e 32 ms no p95, contra 33 ms de orçamento.
- Causa 2: atrasado, o tick decodificava todos os quadros até o relógio, porque P e B dependem dos anteriores. O tick seguinte ficava mais longo, e isso virava uma espiral de 0,5 a 1,6 s de congelamento.
- A decodificação HEVC sozinha rodava a 66 quadros por segundo em média, nunca abaixo de 41, então ela não era o limite. É bug de agendamento, não de CPU.

### Correção

1. **Ler adiante.** Uma thread produtora (`wcam-video`), com dono e parada explícita, decodifica e converte numa fila limitada de 4 quadros (`ReadAhead`). O tick do event loop só escolhe na fila o quadro do instante, sem decodificar nem converter. Pular, editar a linha do tempo, desativar e mudar o formato da câmera recomeçam a fila com uma geração nova, e quadro da geração anterior nunca é entregue. Congelar não esvazia a fila: com a posição parada, os quadros nela são os próximos, não velhos, e nenhum é entregue enquanto está congelado. Pular congelado recomeça a fila e entrega só o quadro do novo ponto.
2. **Troca de trecho.** Uma segunda thread (`wcam-video-next`) abre o próximo trecho, busca o `inSeconds` e decodifica e converte o primeiro quadro enquanto o atual toca.
3. **Menos trabalho por quadro.** Sem `swscale` quando o quadro já está no formato da câmera, e rotação feita na cópia final, sem `concatenate`. Medido no mesmo processo com a máquina entre 61% e 81% de CPU:

   | Caso | Antes (mediana / p95) | Depois (mediana / p95) |
   |---|---|---|
   | `IMG_0641` 4K HEVC para câmera 4K | 32,5 / 105,9 ms | 12,0 / 29,2 ms |
   | `IMG_0641` para câmera 1080p | 8,4 / 76,3 ms | 5,5 / 11,6 ms |
   | 1080p H.264 para câmera 1080p | 10,0 / 18,8 ms | 8,2 / 14,0 ms |
   | 1080p H.264 para câmera 4K | 19,8 / 36,6 ms | 14,8 / 27,9 ms |

4. **Espiral de atraso.**
   - Quadro que já passou do relógio por mais de um período é decodificado sem conversão, a menos que a fila esteja vazia. Nesse caso ele vai para a câmera, que assim não fica sem imagem.
   - Atraso maior que 0,5 s salta ao quadro-chave seguinte ao relógio dentro do trecho. Sem quadro-chave depois, passa ao próximo trecho. Um novo salto só acontece com mais 0,5 s de atraso.
   - Isso pula conteúdo, o que a spec aceita, e as medições contam quantas vezes aconteceu.
5. **Escolha do quadro no tick.** Medir mostrou um efeito que não aparecia antes:
   - Com o relógio da reprodução começando exatamente no `pts` do primeiro quadro, cada tick caía na fronteira entre dois quadros. Uma variação de poucos ms do Windows trocava o quadro escolhido, e cada pulo vinha com uma repetição. Com o vídeo de teste, isso dava 40% de quadros repetidos ou pulados.
   - O tick agora escolhe o quadro mais próximo do seu instante (meio período de margem).
   - Um tick atrasado mostra o quadro vencido mais antigo em vez de pular para o mais novo. Só pula quando há mais de 2 vencidos.

### Depois

Medi com o mesmo tipo de script, adaptado à API nova. Ele roda com prévia simulada e conta só quadros novos, porque a câmera repete o último entre um e outro:
- Repetido por atraso: cada período do vídeo sem quadro novo.
- Pulado por atraso: cada quadro do vídeo que não chegou à câmera.
- A porcentagem é a soma dos dois sobre os quadros esperados.

Para comparar sob a mesma carga, rodei a revisão 1 (7d1a10c, num worktree temporário no scratchpad) intercalada com a revisão 2. A carga da máquina está anotada; o PC é um i5-8500 com 6 núcleos e 6 threads.

| Caso | Duração | CPU da máquina antes / durante | Revisão 1 | Revisão 2 |
|---|---|---|---|---|
| CA 8: vídeo de teste (1280x720 H.264), câmera 1080p30 | 2 min | 24% / 38% | | 30,0 novos/s; 7 repetidos e 2 pulados, **0,25%**; p99 37,6 ms, máximo 102 ms; 0 saltos |
| CA 8: `IMG_0641` 4K HEVC, câmera 1080p30 | 2 min (r1: 60 s) | 25% / 66% | 0,1 repetido/s e 1,2 pulado/s (4,3%); p99 67 ms; 19 intervalos acima de 66 ms | 30,0 novos/s; 17 repetidos e 4 pulados, **0,58%**; p99 40,8 ms; 5 acima de 66 ms; 0 saltos |
| `IMG_0641`, câmera 4K | 2 min (r1: 60 s) | 27% / 63% | 0,4 repetido/s e 0,8 pulado/s (4,0%); p99 65 ms; 16 acima de 66 ms | 30,0 novos/s; 7 repetidos e 0 pulados, **0,19%**; p99 36,6 ms; 2 acima de 66 ms; 0 saltos |
| 1080p H.264, câmera 4K | 60 s | 16% / 60% | | 30,0 novos/s; **0,28%**; p99 41,3 ms; 0 saltos |

- CPU do processo com o `IMG_0641`: 243% em 1080p e 237% em 4K (100% é um núcleo), quase toda na decodificação HEVC em software. É o custo que fica para a 0.10.0. A conversão em 4K caiu para 7,3 ms de mediana e 9,6 ms no p95.
- Saltos ao quadro-chave: 0 nas medições finais.
- Com a máquina sobrecarregada (76% a 96% de CPU antes de começar, com Opera, a VM do WSL e o app Câmera), as duas revisões degradam. Nessa rodada:
  - A r1 com `IMG_0641` em 4K entregou 0,5 quadro por segundo, e a r2 entregou 16,6, com 4 saltos.
  - Essa rodada mostrou dois bugs da r2, corrigidos e cobertos por teste:
    1. O salto repetia a busca a cada quadro.
    2. O salto para a frente sem quadro-chave depois, perto do fim do arquivo, lançava `PermissionError` e parava a reprodução.
  - Com a decodificação abaixo do tempo real, a câmera agora recebe o quadro mais novo decodificado sempre que a fila esvazia, em vez de nenhum.
- O CA 8 pede "sem travamento visível no Meet": isso fica para a bateria com o usuário.

## Biblioteca (§1.1)

- `POST /api/videos` verifica a sessão `live` e o limite de 20 vídeos antes de ler o corpo (`409 no_live_session`, `409 video_library_full`). Depois grava em partes num `.upload-<id>`, valida o primeiro quadro, gera a tira de miniaturas e renomeia para `<id><extensão>`. Qualquer falha apaga o envio e a tira. Os limites de 20 GB (`413 video_too_large`) e de arquivo sem vídeo (`422 video_unsupported`) seguem a revisão 1.
- Nome no disco é `<id>` mais a extensão original, só se ela for segura. O nome original, decodificado do `X-File-Name`, fica no banco e volta em `name`.
- Tira de miniaturas:
  - É feita só com os quadros-chave (`skip_frame=NONKEY`, threads por fatia). Escolho o quadro-chave mais perto de cada um de N pontos espaçados por igual na duração, com N = mínimo entre 60 e o número de quadros-chave.
  - Cada miniatura tem 160 de largura e a rotação aplicada, num JPEG lado a lado.
  - Motivo: no `IMG_0641.MOV` (4K HEVC, 40 s, um quadro-chave a cada 0,93 s), decodificar o quadro exato em 60 pontos levou 51 s, contra 2,3 s para os 43 quadros-chave.
  - Consequência: vídeos com poucos quadros-chave têm menos miniaturas. Os vídeos de teste gravam um quadro-chave por segundo.
  - `GET /api/videos/{id}/filmstrip` responde com `Cache-Control: public, max-age=31536000, immutable`, porque o `id` nunca é reaproveitado (combinado com a web).
- Persistência:
  - Não havia pacote de persistência no agente. Entrou `wcam/persistence` com `sqlite3` da biblioteca padrão, sem dependência nova.
  - Migrations em `persistence/migrations/NNNN_*.sql`, aplicadas em ordem pelo `pragma user_version`, cada uma numa transação.
  - Migration 0001 cria `videos` e `clips` (`on delete cascade`), com `create table if not exists`.
  - Banco em `<diretório de dados>/wcam.sqlite3`.
- Arquivo único da revisão 1: ao subir, arquivos da pasta `video` que não pertencem a nenhum vídeo do banco (o da revisão 1, envios interrompidos) são apagados com log. Vídeo do banco sem arquivo é esquecido. Escolhi descartar em vez de migrar para não decodificar um 4K na subida.
- `DELETE /api/videos/{id}` apaga arquivo, tira e linha. Os trechos saem pelo `cascade` e da linha do tempo em memória. Com o vídeo ativo, a reprodução segue sem os trechos dele, ou desativa se a linha do tempo ficar vazia.

## Linha do tempo (§1.2)

- `PUT /api/timeline`: até 50 trechos; `id` de 1 a 64 caracteres, devolvido como veio; `0 <= inSeconds < outSeconds <= durationSeconds` e trecho de pelo menos 0,5 s, com tolerância de 1e-6; `videoId` existente; campo desconhecido ou de tipo errado: `422 invalid_request`. `inSeconds` e `outSeconds` são guardados e devolvidos sem arredondar (combinado com a web); `timeline.durationSeconds` vem com 3 casas.
- Vale na hora. Com o vídeo ativo, a reprodução recomeça no mesmo segundo da linha do tempo, ou do início se ele passar da nova duração. Vazia, o vídeo desativa.
- Evento `timeline` no `/api/dev/events` com `{"clips", "durationSeconds"}`.

## Reprodução (§1.3)

- `VideoPlayback` toca a sequência de trechos em tempo contínuo e volta ao começo depois do último. O primeiro quadro de cada trecho é o do `inSeconds`, e nenhum quadro passa do `outSeconds` (teste).
- Na troca de trecho e na volta, a câmera repete no máximo um quadro (teste com relógio falso, dois vídeos de fps diferentes e corte).
- Vídeo com mais fps que a câmera: a produtora só converte os quadros que serão mostrados. Com menos fps: cada quadro é entregue uma vez e a câmera o repete.
- `positionSeconds` é a posição na linha do tempo do quadro entregue; com Congelar ligado, para.
- Pular: `PUT /api/video-source/position` na linha do tempo inteira, `422` fora de `[0, duração)` e `409 video_source_inactive` com o vídeo desligado.

## Usar vídeo e voltar à câmera (§1.4)

- Ativar exige sessão `live` (`409 no_live_session`) e trecho (`409 timeline_empty`). Ativar não encerra a sessão: manda `{"type": "video_source", "active": true}` ao celular. Desativar manda `false` se houver sessão `live`.
- Celular que chega a `live` com o vídeo ativo recebe `video_source` `true` depois de `controls`.
- `{"type": "set_video_source", "active": false}` do celular desativa o vídeo. `true` é ignorado com log.
- Celular sai com o vídeo ativo: a sessão termina com o motivo de sempre, o vídeo continua, `Congelar` é mantido e `POST /api/pairing` funciona. Saíram o motivo `video_source` e o `409` do pareamento.
- Controles com o vídeo ativo: `cameraOff` e `facing` dão `409 video_source_active` pelo console. Do celular, são ignorados com log e o celular recebe `controls` de volta. `frozen` vale sem celular.
- Falta de quadros do celular com o vídeo ativo: o observador de episódios não registra amostras enquanto o vídeo está ativo, e o pipeline esquece o horário do último quadro do celular ao ativar e ao desativar. Assim, o tempo no vídeo não vira queda nem intervalo quando a câmera do celular volta (teste).
- Ao desativar com o celular `live`, a câmera mostra o quadro de espera até o primeiro quadro do celular chegar.

## Bandeja (§1.5)

- "Usar vídeo" fica habilitado com o celular `live` e pelo menos um trecho, ou com o vídeo ativo. Com o vídeo ativo, fica marcado e mostra "Voltar à câmera" (`controls.back_to_phone`).
- Desligar câmera e Trocar câmera ficam desabilitados com o vídeo ativo. Congelar fica habilitado.

## Contrato

Sem mudança de contrato além do que a revisão 2 já registra. Combinado com a web por mensagem:
- O id do vídeo é hex de 16 caracteres.
- O id do trecho tem de 1 a 64 caracteres.
- Mudança em `videos`, `timeline` e `active` sai no SSE na hora.
- Os segundos voltam sem arredondar.
- Cache imutável na tira.

## Testes

Verificação a partir de `agent`: `ruff check`, `ruff format --check` e `pyright` estrito estão limpos. A suíte `pytest` deu 512 passados e 1 pulado.

Uma falha intermitente: das 7 execuções completas, uma acusou 1 falha. Ela não se repetiu nas 6 seguintes nem em 6 rodadas só dos arquivos de vídeo, sessão e bandeja, e não consegui identificar o teste, porque aquela saída mostrava só o resumo. Fica registrada.

Testes novos ou reescritos, com vídeos gerados por PyAV:
- `test_video_frames.py`: as linhas verdes em 4K (falhava antes), a cópia sem `swscale` igual ao `swscale` de uma thread, byte a byte, a rotação, as faixas e a redução.
- `test_video_playback.py`, com relógio falso:
  - fps da câmera com vídeo mais rápido e mais lento, sem câmera lenta;
  - volta ao começo sem preto;
  - primeiro quadro de cada trecho no `inSeconds` e nenhum depois do `outSeconds`;
  - no máximo um quadro repetido na troca de trecho e na volta;
  - pular no primeiro e no segundo trecho, congelar, pular congelado;
  - edição da linha do tempo seguindo do mesmo segundo;
  - salto sem quadro-chave depois.
- `test_read_ahead.py`: tick atrasado mostra o quadro vencido mais antigo; mais de 2 vencidos pulam para o mais novo; recomeço descarta quadros da geração anterior.
- `test_video_library.py`: biblioteca cheia, limite de tamanho, arquivos órfãos e da revisão 1 apagados ao subir, vídeo sem arquivo esquecido, migration aplicada uma vez, extensão segura, escolha dos quadros-chave da tira.
- `test_video_source_api.py`:
  - Envio:
    - envio sem `live` (409, nada gravado);
    - envio com tira de miniaturas e cache imutável;
    - tira em pé de vídeo girado;
    - arquivo que não é vídeo;
    - envio sem nome.
  - Linha do tempo:
    - linha do tempo devolvida como veio;
    - cada regra inválida (`422`);
    - mais de 50 trechos;
    - excluir vídeo tira os trechos.
  - Persistência: biblioteca e linha do tempo depois de reiniciar, com o vídeo desligado.
  - Usar vídeo:
    - ativar sem `live` e sem trecho (409);
    - vídeo ativo com a sessão `live`, `video_source` `true` e `false` ao celular, controles com `409 video_source_active`;
    - celular sai e o vídeo continua;
    - `set_video_source` do celular;
    - linha do tempo vazia desativa;
    - eventos `timeline` e `video_source`.
- `test_session_manager.py`, `test_tray.py`, `test_video_pipeline.py` e `test_make_test_video.py`: regras da sessão com o vídeo ativo, item da bandeja, tempo no vídeo não contado como intervalo do celular, vídeo de teste em pé.

## Não verificado

- CA 1 a 5 com a câmera real (OBS, app Câmera, Meet), a bandeja real e o celular real: ficam para a bateria com o usuário, porque as portas 8080 e 8443 e a câmera não foram usadas.
- e2e: roda na sessão web com as duas branches.
- Envio real de 20 GB.
- Vídeo do iPhone gravado em pé (rotação 90) e HEVC 10 bits HDR.

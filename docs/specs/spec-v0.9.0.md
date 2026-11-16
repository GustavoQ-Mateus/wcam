# Spec v0.9.0, Vídeo como câmera

Status: Entregue (2026-11-15; revisão 2, aprovada no mesmo dia depois da bateria da revisão 1)
Branch de integração: `feature/video`
Sessões: `agent`, `web`
Referências: `docs/planejamento.md` §1 (CA-1, CA-2, CA-4), §5.4 (controles); spec v0.8.0 (console, prévia, bandeja); ADR 0011 (câmera nativa); ADR 0015 (prévia); ADR 0016 (vídeo como origem, substituída em parte pela ADR 0017). Pedido do usuário em 2026-11-13.

## Objetivo

Com o celular conectado, o usuário monta no console uma linha do tempo com um ou mais vídeos, como num editor de vídeo simples, e a câmera WCam passa a mostrar essa linha do tempo em repetição, no lugar da câmera do celular, até ele voltar à câmera. Para os apps (Meet, Teams, Zoom, Discord, OBS, app Câmera do Windows) continua sendo a mesma câmera nativa "WCam".

Decisões do usuário (2026-11-13):
- Qualquer vídeo que o PC consiga abrir, sem tratamento especial de HDR nem de formato nesta versão.
- O vídeo chega ao PC por qualquer meio (cabo, nuvem, mensageiro), não pelo `/cam`.
- A câmera continua no formato escolhido (decisão do orquestrador, aceita pelo usuário): o vídeo é ajustado a ele.

Decisões do usuário na bateria (2026-11-15), que mudam a revisão 1:
- Linha do tempo de editor, no estilo do Clipchamp: vários vídeos, cortar o começo e o fim de cada trecho, dividir, arrastar para mudar a ordem. Entra nesta versão.
- Escolher e usar vídeo só com o celular conectado, por segurança. Usar vídeo desliga a câmera do celular sem desconectar; voltar à câmera religa a câmera do mesmo celular, sem novo QR.
- Se o celular desconectar com o vídeo rodando, o vídeo continua. Para voltar à câmera do celular, lê o QR de novo.
- A interface da revisão 1 ficou feia (botão Descongelar repetido sobre a prévia e na barra; área Vídeo solta abaixo do QR). Refazer.
- O vídeo travou na câmera e na prévia, e em 4K apareceram linhas verdes e azuis. Bugs da revisão 1, corrigidos nesta versão (§1.6).

A câmera virtual nativa (`vcam`) não muda.

## 1. Agent

### 1.1 Biblioteca de vídeos

- `POST /api/videos` recebe um vídeo como corpo bruto (`application/octet-stream`), com o nome original em `X-File-Name` (codificado em URL), gravado em partes direto no disco em `<diretório de dados>/video/`, sem carregar na memória. Limite de 20 GB por arquivo (`413 video_too_large`) e de 20 vídeos guardados (`409 video_library_full`).
- Só com o celular em `live`: sem sessão `live`, `409 no_live_session` antes de ler o corpo.
- Ao terminar, abre com PyAV e decodifica o primeiro quadro; sem faixa de vídeo decodificável, apaga e responde `422 video_unsupported`.
- Gera a tira de miniaturas do vídeo para a linha do tempo: até 60 quadros espaçados por igual na duração, cada um com 160 de largura e a proporção do vídeo já com a rotação aplicada, lado a lado num JPEG. Servida em `GET /api/videos/{id}/filmstrip`.
- `DELETE /api/videos/{id}` apaga o arquivo e tira da linha do tempo os trechos que o usam; `404 video_not_found`.
- Vídeos e linha do tempo sobrevivem a reiniciar o agente (tabelas novas por migration). O estado ativo não sobrevive: o agente sempre sobe com o vídeo desativado.
- Áudio é ignorado.

### 1.2 Linha do tempo

- Uma faixa só, com trechos em sequência, sem espaço entre eles. Cada trecho é `{"id", "videoId", "inSeconds", "outSeconds"}`: um pedaço de um vídeo da biblioteca. O mesmo vídeo pode aparecer em mais de um trecho.
- `PUT /api/timeline` com `{"clips": [...]}` troca a linha do tempo inteira: o console calcula arrastar, cortar e dividir e manda o resultado. `id` é gerado pelo console e devolvido como veio. Regras: até 50 trechos; `0 <= inSeconds < outSeconds <= durationSeconds` do vídeo; trecho de pelo menos 0,5 s; `videoId` existente. Fora disso, `422 invalid_request`.
- Vale na hora, com o vídeo ativo ou não. Com o vídeo ativo, a reprodução segue no mesmo segundo da linha do tempo (limitado à nova duração). Se a linha do tempo ficar vazia com o vídeo ativo, o vídeo desativa (§1.4).

### 1.3 Reprodução

- Uma tarefa com dono e cancelamento explícito; decodificação e conversão no executor, fora do event loop.
- Toca os trechos em ordem e, no fim do último, volta ao começo do primeiro.
- Cada quadro é convertido para I420 no formato anunciado (`videoFormat.camera`), com a rotação gravada aplicada, mantendo a proporção, centralizado com faixas pretas (Y=16, UV=128).
- Ritmo pelo `pts`, não pela velocidade da decodificação: a câmera recebe quadros no fps anunciado, repetindo ou pulando quadros conforme o vídeo; nunca em câmera lenta.
- Troca de trecho sem preto e sem parada: o próximo trecho é aberto e tem o primeiro quadro decodificado antes do fim do atual. Na troca, no máximo um quadro repetido.
- Pular para um ponto: `PUT /api/video-source/position` com `{"seconds"}` na linha do tempo inteira. Busca o quadro-chave anterior no trecho certo, decodifica sem entregar até o ponto e segue dali; a câmera repete o último quadro enquanto isso. Fora de `[0, duração da linha do tempo)`: `422 invalid_request`; vídeo desativado: `409 video_source_inactive`.
- `videoSource.positionSeconds` é a posição do quadro entregue na linha do tempo. Com Congelar imagem ligado, a posição para; ao descongelar, segue de onde parou. Pular congelado entrega o quadro do novo ponto e continua congelado.
- Cor pelo caminho padrão do PyAV; HDR sem mapeamento de tom (limitação registrada).

### 1.4 Usar vídeo e voltar à câmera

- `PUT /api/video-source` com `{"active": bool}`: `204`.
- Ativar exige o celular em `live` (`409 no_live_session`) e a linha do tempo com pelo menos um trecho (`409 timeline_empty`).
- Ativar não encerra a sessão: o agente manda ao celular `{"type": "video_source", "active": true}`, o celular desliga a câmera (para a faixa, a luz da câmera apaga) e mostra que o computador está mostrando um vídeo, com o botão para voltar à câmera. Enquanto o vídeo está ativo, a falta de quadros do celular não é queda nem congelamento.
- Desativar (console, bandeja ou celular): com a sessão `live`, o agente manda `{"type": "video_source", "active": false}`, o celular religa a câmera e a imagem do celular volta. Sem sessão, a câmera volta ao quadro de espera e o console ao QR.
- Celular desconecta com o vídeo ativo: a sessão termina com o motivo de sempre e o vídeo continua. O console oferece o QR. Um celular que conectar nesse estado entra em `live` com a câmera desligada e a mensagem do vídeo, até alguém voltar à câmera.
- Celular manda `{"type": "set_video_source", "active": false}` quando o usuário toca em voltar à câmera. Só vale em `live`; `active: true` vindo do celular é ignorado com log (escolher vídeo é só no computador).
- Controles com o vídeo ativo: Congelar imagem (no console, Pausar e Continuar da linha do tempo) e Espelhar valem, Congelar também sem celular; Desligar câmera e Trocar câmera respondem `409 video_source_active`.
- `virtualCamera.source` `video`. A prévia do console mostra o vídeo, porque mostra o quadro entregue.

### 1.5 Bandeja

- Item "Usar vídeo" marcável, habilitado só com o celular em `live` e a linha do tempo com trecho, ou com o vídeo ativo (para poder voltar).
- Sexto estado do ícone: vídeo em repetição, selo em forma de triângulo de reprodução, `--data-2`, dica com o estado em texto.

### 1.6 Bugs da revisão 1

- Linhas verdes e azuis com a câmera em 4K: causa raiz no relatório, com teste que falha antes da correção (nenhuma linha do quadro entregue com Y, U e V zerados).
- Travamentos: o relatório mede, em 1080p30 e em 4K, tempo de decodificação e conversão por quadro e quadros repetidos ou pulados por atraso, com o vídeo de teste H.264 e o `IMG_0641.MOV` do usuário (4K HEVC). Bug de ritmo ou de agendamento é corrigido nesta versão. Custo de CPU da decodificação HEVC em software fica para a 0.10.0 Desempenho (decodificação na GPU), com os números registrados.

## 2. Web (console)

Direção das skills de design (registro em `docs/design-v0.9.0.md`, refeito): `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `mobile-native` para o `/cam`, `animate` e `review-animations` para arrastar e cortar.

### 2.1 Onde o vídeo aparece

- Sem celular conectado e sem vídeo ativo, o console não mostra nada de vídeo: só o QR, como na v0.8.0.
- Com o celular em `live`, um controle "Usar vídeo" entra junto dos controles da câmera e abre o editor.
- O editor ocupa a tela do console: prévia em cima (o que os apps recebem), barra de reprodução, linha do tempo na largura toda e a biblioteca de vídeos ao lado. Estado claro de que a câmera mostra o vídeo, não o celular. "Voltar à câmera" sempre visível.
- Cada controle aparece uma vez: nada de botão repetido sobre a prévia e na barra (bug da revisão 1).

### 2.2 Biblioteca

- Escolher ou arrastar arquivos (vários de uma vez), progresso de cada envio, nome e duração; resolução, fps e codec só em Detalhes. Remover com confirmação quando o vídeo está em uso na linha do tempo.
- Envio com `XMLHttpRequest` (progresso), num módulo em `data/` ou `media/`, um por vez em fila.
- Adicionar à linha do tempo: arrastar o vídeo para a faixa (entra na posição solta) ou o botão de adicionar (entra no fim), já com o vídeo inteiro.

### 2.3 Linha do tempo de editor

- Faixa com os trechos lado a lado, largura proporcional à duração, com a tira de miniaturas (`/filmstrip`) e o nome.
- Régua de tempo e cursor de reprodução que anda com a posição; clicar ou arrastar na régua pula (`PUT /api/video-source/position` ao soltar).
- Arrastar um trecho muda a ordem. Arrastar a borda esquerda ou direita corta o começo ou o fim, com o tempo mostrado durante o arraste. Dividir no cursor (botão e tecla S). Excluir trecho (botão e tecla Delete). Zoom da faixa (mais e menos), para cortar com precisão em vídeo longo.
- Cada mudança vira `PUT /api/timeline` ao soltar, com a linha do tempo inteira calculada num módulo puro em `data/` (testado com Vitest).
- Teclado: espaço pausa e continua (Congelar), setas pulam 5 s, Tab chega a cada trecho, Alt com setas move o trecho selecionado. Rótulos acessíveis em trechos, bordas e cursor.
- Entre eventos do SSE, o cursor avança pelo relógio local e é corrigido pelo agente a cada evento (regra da revisão 1, que continua).
- Com o vídeo inativo e o celular conectado, o editor fica disponível para montar a linha do tempo antes de usar; a prévia mostra a câmera do celular e o botão principal é "Usar vídeo".

### 2.4 `/cam`

- Ao receber `video_source` `active: true`: para a faixa da câmera (luz apagada) e mostra "O computador está mostrando um vídeo" com o botão "Voltar à câmera" (`set_video_source`). Ao receber `false`: pede a câmera de novo e volta ao visor, sem novo QR.

### 2.5 Erros

Texto próprio para `video_too_large`, `video_unsupported`, `video_library_full`, `video_not_found`, `timeline_empty`, `video_source_active`, `video_source_inactive` e para `no_live_session` no envio.

### 2.6 Gráficos e ícones por biblioteca

Sem mudança desde a revisão 1 (decisões registradas abaixo): gráficos do `/dev` continuam em SVG próprio; ícones em `lucide-react`.

## 3. Contrato (`docs/contrato.md` 0.9.0, reescrito na seção "Vídeo como câmera")

- `POST /api/videos`: corpo bruto, `X-File-Name`; `201 {"id", "name", "durationSeconds", "width", "height", "fps", "codec", "filmstripFrames"}`; `409 no_live_session`, `409 video_library_full`, `413 video_too_large`, `422 video_unsupported`.
- `GET /api/videos/{id}/filmstrip`: `200 image/jpeg`; `404 video_not_found`.
- `DELETE /api/videos/{id}`: `204`; `404 video_not_found`.
- `PUT /api/timeline` com `{"clips": [{"id", "videoId", "inSeconds", "outSeconds"}]}`: `204`; `422 invalid_request`.
- `PUT /api/video-source` com `{"active": bool}`: `204`; `409 no_live_session`, `409 timeline_empty`, `422 invalid_request`.
- `PUT /api/video-source/position` com `{"seconds"}`: `204`; `409 video_source_inactive`, `422 invalid_request`.
- `GET /api/status` e SSE do console: `"videoSource": {"videos": [{"id", "name", "durationSeconds", "width", "height", "fps", "codec", "filmstripFrames"}], "timeline": {"clips": [...], "durationSeconds"}, "active": bool, "positionSeconds": number | null}`.
- DataChannel: agente para o celular `{"type": "video_source", "active": bool}` (ao ativar, ao desativar e ao chegar a `live` com o vídeo ativo); celular para o agente `{"type": "set_video_source", "active": false}`.
- `PATCH /api/controls`: `cameraOff` e `facing` com o vídeo ativo, `409 video_source_active`; `frozen` aceito sem celular com o vídeo ativo.
- Saem da revisão 1: `PUT`/`DELETE /api/video-source/file`, `videoSource.file`, `lastEnded.reason` `video_source`, `409 video_source_active` no `POST /api/pairing`, erro `no_video_file`.
- Erros novos ou mudados: `video_library_full` (409), `video_not_found` (404), `timeline_empty` (409), `video_source_active` (409, agora nos controles).
- `GET /api/dev/events`: evento `video_source` (`{"active"}`) e `timeline` (`{"clips": n, "durationSeconds"}`).

## 4. ADR

ADR 0017 substitui na ADR 0016 a parte "com o vídeo ativo, o celular não é usado: a sessão termina" e acrescenta a linha do tempo: o vídeo só é escolhido e ativado com o celular conectado, o celular fica conectado com a câmera desligada, e a origem toca uma sequência de trechos. O resto da ADR 0016 (ajuste ao formato anunciado, CA-2 só para o celular, HDR sem mapeamento) continua.

## 5. Planejamento

O orquestrador emenda `docs/planejamento.md` antes do código: §5.4, "Usar vídeo" só com o celular conectado e "Voltar à câmera" no console, na bandeja e no celular.

## Textos

O orquestrador põe em `locales/` antes do código: editor (biblioteca, adicionar, dividir, excluir trecho, zoom, régua, Pausar, Continuar, rótulos acessíveis de trecho, borda e cursor), "Voltar à câmera", mensagem e botão do celular, erros novos. Saem `cam.ended_video_source` e `errors.no_video_file`. `console.*` e `cam.*` de detalhe a sessão web pode acrescentar, nos dois arquivos, listando no relatório.

## Testes

- Agent: vídeos gerados no teste com PyAV. Envio sem sessão `live` (`409`, nada gravado); biblioteca cheia; tira de miniaturas com o número certo de quadros e rotação aplicada; `PUT /api/timeline` com cada regra inválida (`422`); excluir vídeo tira os trechos; persistência depois de reiniciar; reprodução de dois trechos de vídeos diferentes com corte (o `pts` do primeiro quadro de cada trecho é o `inSeconds`, nenhum quadro depois do `outSeconds`, no máximo um quadro repetido na troca, volta ao começo); pular para um ponto no segundo trecho; ativar sem sessão e sem trecho (`409`); ativar com sessão manda `video_source` ao celular e a sessão continua `live`; desativar religa; celular desconecta com o vídeo ativo e o vídeo continua; `set_video_source` do celular; controles com o vídeo ativo; ritmo com relógio falso; o teste das linhas verdes da §1.6.
- Web: Vitest no módulo da linha do tempo (mover, cortar respeitando 0,5 s e a duração, dividir no cursor, excluir, posição do cursor por trecho), no envio em fila e na posição pelo relógio.
- e2e: com o celular falso em `live`, enviar dois vídeos, montar a linha do tempo, usar vídeo (`virtualCamera.source` `video`, sessão ainda `live`, celular com a mensagem), pular, voltar à câmera (imagem do celular de volta sem novo QR); SSIM do CA-2 com o vídeo desativado.

## Decisões registradas

- 2026-11-15, gráficos (CA 9 da revisão 1): o `uPlot` não reduziu a CPU do navegador no `/dev` (renderizador 9,97% com SVG contra 15,14% com `uPlot`, prévia ligada; GPU dobrou com canvas; JS do `/dev` de 84,2 para 106,7 KB gzip). Não entra; os gráficos continuam em SVG próprio, sem mudança visual.
- 2026-11-15, ícones: o `lucide-react` fica. A troca dos ícones é pedido do usuário e cumpre o limite de JS (`/` de 88,9 para 90,2 KB gzip).
- 2026-11-15, bateria da revisão 1: linha do tempo de editor e vídeo só com celular conectado entram nesta versão (decisão do usuário); o vídeo continua se o celular desconectar.

- 2026-11-15, tira de miniaturas (§1.1): feita dos quadros-chave mais próximos de pontos espaçados por igual, até 60, porque quadros exatos levavam 51 s no 4K HEVC contra 2,3 s. Vídeo com poucos quadros-chave tem menos miniaturas (`filmstripFrames` informa quantas).
- 2026-11-15, leitura adiante (§1.3): Congelar não esvazia a fila (os quadros nela são os próximos); pular, editar e desativar recomeçam a fila sem entregar quadro velho.

## Fora do escopo

- Mais de uma faixa, transições, textos, sobreposições, velocidade, áudio, mudar posição ou tamanho do vídeo no quadro, desfazer e refazer.
- HDR com mapeamento de tom; trocar o formato da câmera para o do vídeo; enviar o vídeo pelo celular.
- Decodificação na GPU (0.10.0 Desempenho).

## Critérios de aceitação

1. Com o celular conectado, dois vídeos do iPhone do usuário enviados e montados na linha do tempo (um deles cortado) aparecem em sequência e em repetição na câmera WCam no OBS, no app Câmera do Windows e no Meet, sem câmera lenta, sem preto na troca de trecho e na volta.
2. Sem celular conectado, o console não oferece vídeo e o agente recusa envio e ativação.
3. Usar vídeo desliga a câmera do celular (luz apagada) sem desconectar; Voltar à câmera, no console, na bandeja ou no celular, traz a imagem do celular de volta sem novo QR; tudo aparece nos três lugares em menos de 300 ms.
4. Celular desconectado com o vídeo rodando: o vídeo continua e o console oferece o QR.
5. Editor: adicionar, mudar a ordem arrastando, cortar pelas bordas, dividir no cursor, excluir e pular pela régua, com mouse e teclado; o Meet mostra a mudança em até 1 s, sem preto. Pausar para a posição.
6. Vídeo em pé aparece em pé, com faixas; outra resolução ocupa o formato sem distorcer.
7. Nenhuma linha verde, azul ou de cor errada em nenhum formato da câmera, conferido em 1080p e em 4K.
8. Em 1080p30, com o vídeo de teste e com o `IMG_0641.MOV`, sem travamento visível no Meet e quadros repetidos ou pulados por atraso abaixo de 1% em 2 min. Em 4K, os números ficam registrados no relatório como base da 0.10.0.
9. Interface refeita conferida pelo usuário: sem controle repetido, editor com a direção das skills registrada.
10. Arquivo que não é vídeo é recusado com texto próprio, sem deixar arquivo no disco.
11. CA-2 do celular mantido (SSIM de pelo menos 0,98 no e2e com o vídeo desativado).
12. Verificação completa do CLAUDE.md e `npm run test:e2e`; `version` 0.9.0 em `agent/pyproject.toml` e `web/package.json`.

## Changelog

Entregue em 2026-11-15, revisão 2. Bateria do usuário com o WCam rodando no Windows (câmera nativa, celular real), todos os itens validados.

- CA 1: dois vídeos do iPhone (IMG_0641 e IMG_0642, 4K HEVC) montados e cortados na linha do tempo, em sequência e em repetição no OBS, no app Câmera e no Meet, sem câmera lenta nem preto. Validado pelo usuário.
- CA 2: sem celular, o console não oferece vídeo; o agente responde `409 no_live_session` ao envio e à ativação (testes). Validado pelo usuário.
- CA 3: Usar vídeo desliga a câmera do celular sem desconectar; Voltar à câmera no console, na bandeja e no celular, sem novo QR. Validado pelo usuário.
- CA 4: celular desconectado com o vídeo rodando; o vídeo continua e o console oferece o QR. Validado pelo usuário.
- CA 5: editor com adicionar, ordenar, cortar, dividir, excluir, zoom e régua. Validado pelo usuário.
- CA 6: vídeo em pé com faixas (e2e com `E2E_TEST_VIDEO_2` e bateria).
- CA 7: linhas verdes e azuis corrigidas. Causa: o swscale multithread do FFmpeg 8 deixava uma linha de croma sem escrever em cada borda de fatia ao converter no mesmo tamanho. Quadro já no formato da câmera é copiado sem swscale; conversão no mesmo tamanho em uma thread. Varredura de 60 quadros do IMG_0641 em 4K: 60 com linhas zeradas antes, 0 depois. Validado pelo usuário em 4K.
- CA 8: quadros repetidos ou pulados por atraso em 2 min, mesma carga (i5-8500, 6 núcleos, 16 a 27% de CPU antes): vídeo de teste em 1080p30 0,25%; IMG_0641 em 1080p30 0,58% (revisão 1: 4,3%); IMG_0641 com a câmera em 4K 0,19%, p99 de 37 ms (revisão 1: 4,0%). Nenhum salto ao quadro-chave. CPU do processo com HEVC 4K em cerca de 240%, quase toda na decodificação (base da 0.10.0).
- CA 9: interface refeita, sem controle repetido, direção em `docs/design-v0.9.0.md`. Validada pelo usuário.
- CA 10: arquivo que não é vídeo recusado com `video_unsupported`, arquivo apagado (testes e bateria).
- CA 11: SSIM 0,9836 no e2e com o vídeo desativado.
- CA 12: pytest 512 passados e 1 pulado, ruff, format e pyright limpos; build, lint e 209 testes Vitest; e2e 33 de 33; CI verde em todos os jobs; `version` 0.9.0 nos dois lados.

Achados:
- Falha intermitente no pytest (1 em 7 execuções completas) identificada: `test_running_pipeline_feeds_placeholders_continuously`, de 2026-11-01, exigia 10 quadros em 0,5 s de relógio, e o timer do Windows (degraus de 15,6 ms) sob carga entregava 9. Corrida no teste, não no código; o teste passou a esperar os 10 quadros com teto de 3 s e limite superior pelo tempo decorrido (PR #50), 12 de 12 com os 6 núcleos ocupados.
- `comparison.spec` instável com a máquina carregada (A/B igual com o agent das duas revisões).
- O zoom da linha do tempo só tem botões; atalho de teclado e Ctrl com a roda do mouse ficam como melhoria.
- Ícones em `lucide-react`; gráficos do `/dev` continuam em SVG próprio (uPlot não reduziu a CPU).

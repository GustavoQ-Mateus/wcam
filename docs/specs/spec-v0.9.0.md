# Spec v0.9.0, Vídeo como câmera

Status: Aprovada (2026-11-15)
Branch de integração: `feature/video`
Sessões: `agent`, `web`
Referências: `docs/planejamento.md` §1 (CA-1, CA-2), §5.4 (controles); spec v0.8.0 (console, prévia, bandeja); ADR 0011 (câmera nativa); ADR 0015 (prévia). Pedido do usuário em 2026-11-13.

## Objetivo

O usuário envia um vídeo pelo console, e a câmera WCam passa a mostrar esse vídeo em repetição, do começo ao fim e de novo, até ele desativar. Para os apps (Meet, Teams, Zoom, Discord, OBS, app Câmera do Windows) continua sendo a mesma câmera nativa "WCam".

Decisões do usuário (2026-11-13):
- Qualquer vídeo que o PC consiga abrir, sem tratamento especial de HDR nem de formato nesta versão. Melhorias ficam para depois.
- Com o vídeo ativo, o celular não é usado: a conexão com o celular termina e o QR code não é oferecido até o vídeo ser desativado. O vídeo chega ao PC por qualquer meio (cabo, nuvem, mensageiro), não pelo `/cam`.
- A câmera continua no formato escolhido (decisão do orquestrador, aceita pelo usuário): o vídeo é ajustado a ele. Trocar o formato da câmera exigiria o app reabrir a câmera no meio da reunião.

Decisão do usuário na aprovação (2026-11-15): o vídeo tem uma linha do tempo no console (§1.4 e §2.1).

A câmera virtual nativa (`vcam`) não muda.

## 1. Agent

### 1.1 Arquivo

- `PUT /api/video-source/file` recebe o arquivo como corpo bruto (`application/octet-stream`), com o nome original no cabeçalho `X-File-Name` (codificado em URL), gravado em partes direto no disco, sem carregar tudo na memória, em `<diretório de dados>/video/`. Limite de 20 GB; acima disso, `413 video_too_large`.
- Ao terminar, o agente abre o arquivo com PyAV e confere que há uma faixa de vídeo decodificável (decodifica o primeiro quadro). Se não houver, apaga o arquivo e responde `422 video_unsupported`.
- Guarda um vídeo por vez: um envio novo substitui o anterior (desativando antes, se estiver ativo). O arquivo fica no diretório de dados até ser removido (`DELETE /api/video-source/file`) e sobrevive a reiniciar o agente; o estado ativo não sobrevive (o agente sempre sobe com o vídeo desativado).
- Áudio é ignorado.

### 1.2 Reprodução

- Uma tarefa com dono e cancelamento explícito; decodificação e conversão no executor, fora do event loop.
- Cada quadro é convertido para I420 no formato anunciado pela câmera (`videoFormat.camera`), mantendo a proporção, centralizado com faixas pretas (Y=16, UV=128) quando a proporção não bate. A rotação gravada no arquivo (vídeo do celular em pé) é aplicada antes.
- O ritmo segue o tempo do vídeo (`pts`), não a velocidade da decodificação. A câmera recebe quadros no fps anunciado: quadro repetido quando o vídeo tem fps menor, quadro pulado quando tem maior ou quando a decodificação atrasa. O vídeo nunca fica em câmera lenta.
- No fim, volta ao começo e continua, sem quadro preto entre as voltas.
- Cor: faixa e matriz convertidas para o que a câmera espera, com o caminho padrão do PyAV. HDR sai sem mapeamento de tom (pode ficar com cor lavada); fica registrado como limitação.

### 1.3 Ativar e desativar

- `PUT /api/video-source` com `{"active": bool}`: `204`. Ativar sem arquivo: `409 no_video_file`.
- Ativar encerra a sessão do celular, se houver, com o motivo novo `video_source` (o celular mostra que o computador passou a usar um vídeo), fecha a janela do QR e faz `POST /api/pairing` responder `409 video_source_active` enquanto o vídeo estiver ativo.
- Desativar volta ao comportamento normal: quadro de espera até um celular conectar.
- `virtualCamera.source` ganha `video`.
- Controles com o vídeo ativo: Congelar imagem e Espelhar valem (congela o quadro atual do vídeo; espelha a saída); Desligar câmera e Trocar câmera continuam exigindo celular (`409 no_live_session`).
- A prévia do console (ADR 0015) mostra o vídeo, porque mostra o quadro entregue.

### 1.4 Linha do tempo

- O agente sabe a posição atual do vídeo em segundos (pelo `pts` do quadro entregue) e a publica em `videoSource.positionSeconds`.
- `PUT /api/video-source/position` com `{"seconds": number}` pula para esse ponto: busca o quadro-chave anterior, decodifica sem entregar até o ponto pedido e segue dali, no mesmo ritmo e na mesma repetição. Até achar o ponto, a câmera repete o último quadro entregue, sem preto. Fora de `[0, durationSeconds)`: `422 invalid_request`. Com o vídeo desativado: `409 video_source_inactive`.
- Com Congelar imagem ligado, a posição para; ao descongelar, o vídeo segue de onde parou (não salta o tempo congelado). Pular com o vídeo congelado entrega o quadro do novo ponto e continua congelado.

### 1.5 Bandeja

- Item "Usar vídeo" marcável, desabilitado sem arquivo.
- Sexto estado do ícone: vídeo em repetição, selo em forma de triângulo de reprodução, `--data-2`, dica com o estado em texto.

## 2. Web (console)

- Área "Vídeo" no console, com direção das skills de design (registro em `docs/design-v0.9.0.md`): escolher ou arrastar um arquivo, barra de progresso do envio, nome, duração, resolução e fps do vídeo enviado (fps e resolução só em Detalhes), **Usar vídeo** e **Voltar ao celular**, **Remover vídeo**.
- Com o vídeo ativo, o console mostra o estado "Vídeo em repetição" com a prévia, no lugar do QR e da área do celular, e deixa claro que a câmera não está ao vivo.
- Envio com `XMLHttpRequest` (progresso do upload), encapsulado em módulo em `data/` ou `media/`, fora do componente.
- `/cam`: mensagem para o encerramento `video_source`.
- Erros `video_too_large`, `video_unsupported`, `no_video_file`, `video_source_active` e `video_source_inactive` com texto próprio.

### 2.1 Linha do tempo

- Com o vídeo ativo, o console mostra sob a prévia uma linha do tempo do vídeo: posição atual, duração e uma barra que o usuário clica ou arrasta para pular (`PUT /api/video-source/position` ao soltar, não durante o arraste). Operável pelo teclado (setas pulam 5 s) e com rótulo acessível.
- Entre os eventos do SSE, o console avança a posição pelo relógio local enquanto o vídeo roda e não está congelado, e corrige pelo valor do agente a cada evento, para a barra andar sem saltos de 1 s.
- Sem miniaturas, cortes ou marcadores nesta versão.

### 2.2 Gráficos e ícones por biblioteca

Pedido do usuário em 2026-11-15: trocar os gráficos do `/dev` e os ícones desenhados à mão (SVG próprio, decisão da spec v0.8.0 §4.1) por bibliotecas, para deixar a interface mais leve.

- Gráficos: `uPlot`, que desenha em canvas e foi feita para séries temporais em tempo real. Hoje o React redesenha cada SVG a cada amostra, 1 vez por segundo em cada gráfico. Vale para todos os gráficos do `/dev`: séries, minigráficos da faixa de saúde e histograma. Marcas de evento, linhas de referência e cores continuam como estão (tokens de §5.6, skill `dataviz`).
- Ícones: `lucide-react`, importando ícone por ícone para o build levar só os usados. Substitui os ícones de console, `/cam`, `/dev` e do que entrar na área Vídeo. O ícone da bandeja continua desenhado pelo agente em Pillow.
- Justificativa das duas dependências: código de desenho a menos para manter, e no `/dev` menos trabalho do navegador a cada amostra. Biblioteca não deixa a página mais leve por si só, então a troca precisa provar isso com a medição do CA 9. Se uma delas não melhorar, ela não entra e o relatório registra o motivo.
- O estilo dos gráficos não muda (pedido do usuário): mesmo tipo de cada gráfico, mesmas cores, espessura de linha, grade, eixos, rótulos, linhas de referência, marcas de evento e layout da v0.8.0. A biblioteca é configurada para ficar igual ao atual, sem tema, legenda, tooltip ou animação padrão dela. Na revisão, comparo capturas antes e depois lado a lado.

## 3. Contrato (`docs/contrato.md` vai para 0.9.0)

- `PUT /api/video-source/file`: corpo bruto, `X-File-Name`; `201 {"name", "durationSeconds", "width", "height", "fps", "codec"}`; `413 video_too_large`, `422 video_unsupported`.
- `DELETE /api/video-source/file`: `204` (desativa antes); `404 no_video_file` sem arquivo.
- `PUT /api/video-source` com `{"active": bool}`: `204`; `409 no_video_file`; `422 invalid_request`.
- `GET /api/status` ganha `"videoSource": {"file": {"name", "durationSeconds", "width", "height", "fps", "codec"} | null, "active": bool, "positionSeconds": number | null}` (`null` com o vídeo desativado) no primeiro nível, sempre presente; entra no SSE do console.
- `PUT /api/video-source/position` com `{"seconds": number}`: `204`; `409 video_source_inactive`; `422 invalid_request`.
- `virtualCamera.source`: `video`. `lastEnded.reason`: `video_source`. `POST /api/pairing`: `409 video_source_active`.
- Erros novos na tabela geral: `video_too_large` (413), `video_unsupported` (422), `no_video_file` (404 no `DELETE`, 409 no `PUT`), `video_source_active` (409), `video_source_inactive` (409).
- `GET /api/dev/events`: `delivered` vale também para o vídeo; evento `video_source` (`{"active", "name"}`).

## 4. ADR

ADR 0016: o vídeo enviado pelo usuário é uma origem própria da câmera, ajustada ao formato anunciado (pode redimensionar e converter cor). O CA-2 continua valendo só para a imagem do celular, que não muda.

## 5. Planejamento

O orquestrador emenda `docs/planejamento.md` antes do código: §5.4 ganha a linha "Usar vídeo" (bandeja e console); §6 ganha a 0.9.0 "Vídeo como câmera", e "Zoom e enquadramento" passa a 0.11.0, depois da 0.10.0 "Desempenho" (decisão do usuário em 2026-11-15), com as linhas seguintes andando.

## Textos

Chaves novas em `locales/` na integração antes do código: área Vídeo do console, estado "Vídeo em repetição", Usar vídeo, Voltar ao celular, Remover vídeo, progresso do envio, item e estado da bandeja, encerramento `video_source` no celular, a linha do tempo (rótulo acessível e tempos) e os cinco erros.

## Testes

- Agent: vídeos pequenos gerados no próprio teste com PyAV (H.264, 2 s; um em pé com rotação gravada; um de 60 fps; um de 15 fps). Testes de: arquivo inválido (`422`, arquivo apagado); volta ao começo sem quadro preto; quadro ajustado com faixas nos valores certos e rotação aplicada; ritmo (em 4 s de relógio falso, a câmera recebe 4 × fps quadros, com repetição ou pulo conforme o vídeo); ativar encerra a sessão com `video_source` e `POST /api/pairing` responde `409`; Congelar e Espelhar com o vídeo; pular para um ponto (o próximo quadro entregue tem `pts` no ponto pedido, sem preto durante a busca), pular fora da duração (`422`) e com o vídeo desativado (`409`); posição parada enquanto congelado.
- Web: Vitest no módulo de envio (progresso e erros) e na posição da linha do tempo (avanço pelo relógio, correção pelo agente, parada com Congelar).
- e2e: enviar um vídeo pelo console, ativar, ver `virtualCamera.source` `video` e a prévia com imagem; arrastar a linha do tempo e ver `positionSeconds` no ponto escolhido; desativar volta ao QR.

## Decisões registradas

- 2026-11-15, gráficos (§2.2, CA 8 e 9): o `uPlot` não reduziu a CPU do navegador no `/dev` (renderizador 9,97% com SVG contra 15,14% com `uPlot`, prévia ligada; GPU dobrou com canvas; JS do `/dev` de 84,2 para 106,7 KB gzip). Pela regra da §2.2, ele não entra e os gráficos continuam em SVG próprio, sem mudança visual.
- 2026-11-15, ícones (§2.2, CA 9): o `lucide-react` fica. A condição de CPU vale para a troca dos gráficos, já que o `/dev` não tem ícones; a troca dos ícones é pedido do usuário e cumpre o limite de JS (`/` de 88,9 para 90,2 KB gzip). O usuário confere o desenho novo dos ícones na bateria.

## Fora do escopo

- HDR com mapeamento de tom, corte ou escolha de trecho, miniaturas na linha do tempo, lista de vídeos, velocidade, áudio.
- Trocar o formato da câmera para o do vídeo.
- Enviar o vídeo pelo celular.

## Critérios de aceitação

1. Um vídeo gravado no iPhone do usuário, enviado pelo console, aparece em repetição na câmera WCam no OBS, no app Câmera do Windows e no Meet, sem câmera lenta e sem quadro preto na volta.
2. Vídeo em pé aparece em pé, com faixas laterais; vídeo de outra resolução ocupa o formato anunciado sem distorcer.
3. Linha do tempo: mostra a posição andando, pula para o ponto escolhido (clique, arraste e teclado) com a imagem no Meet mudando em até 1 s e sem quadro preto, e para com Congelar imagem.
4. Ativar o vídeo encerra o celular e esconde o QR; desativar volta ao QR; tudo aparece no console e na bandeja em menos de 300 ms.
5. Arquivo que não é vídeo é recusado com texto próprio, sem deixar arquivo no disco.
6. CPU registrada no relatório com um vídeo 1080p30 H.264 e um 4K HEVC do iPhone.
7. CA-2 do celular mantido (SSIM de pelo menos 0,98 no e2e com o vídeo desativado).
8. Gráficos do `/dev` em `uPlot` e ícones em `lucide-react` (§2.2), com o mesmo visual da v0.8.0, conferido pelo usuário.
9. Relatório web com antes e depois da troca de bibliotecas: tamanho do JS da `/` e da `/dev` (gzip) e CPU do navegador com o `/dev` aberto por 2 min na janela de 120 s. A troca só fica se reduzir a CPU sem aumentar o JS da `/` em mais de 15 KB gzip.
10. Verificação completa do CLAUDE.md e `npm run test:e2e`; `version` 0.9.0 em `agent/pyproject.toml` e `web/package.json`.

# Relatório v0.9.0 revisão 2, sessão web

Spec: `docs/specs/spec-v0.9.0.md` (revisão 2) · Handoff: `docs/handoff-v0.9.0-r2.md` · ADR 0017 · Branch: `feature/video-web` (worktree `.worktrees/web-video`) · Design: `docs/design-v0.9.0.md` (refeito)

## 1. Onde o vídeo aparece (spec §2.1)

- Sem celular `live` e sem vídeo ativo, o console não mostra nada de vídeo; o painel da revisão 1 abaixo do QR saiu.
- Com o celular `live`, "Usar vídeo" entra na fileira de controles do Ao vivo e abre o editor (`console/video-editor.tsx`). O editor fica aberto só para aquela conexão do celular e fecha quando o vídeo é desativado de qualquer lugar (console, bandeja ou celular).
- Editor:
  - Prévia em cima e, ao lado, a biblioteca e o painel Celular.
  - Fileira de reprodução: Pausar ou Continuar, o relógio, Dividir, Excluir trecho, Afastar e Aproximar, Espelhar, Prévia, e o botão principal (Usar vídeo com o vídeo inativo; Voltar à câmera com ele ativo).
  - Linha do tempo na largura toda, com Formato e Detalhes abaixo.
- Com o vídeo inativo, Voltar à câmera aparece como secundário e fecha o editor. A prévia mostra a câmera do celular.
- Com o vídeo ativo, a pílula diz "Vídeo em repetição", abaixo da prévia aparece "A câmera está mostrando o vídeo, não o celular", e o painel Celular troca a escolha de câmera por "A câmera do celular fica desligada enquanto o vídeo passa".
- Se o celular sair com o vídeo rodando, o painel Celular dá lugar ao QR e ao "QR code novo" na coluna lateral; a confirmação do código também aparece ali quando um celular novo chega.
- Cada controle aparece uma vez: Descongelar e Ligar câmera saíram de cima da prévia (Ao vivo, editor e `/dev`); o aviso continua, sem o botão repetido.

## 2. Biblioteca (spec §2.2)

- Vários arquivos de uma vez, pelo botão "Escolher vídeo" ou arrastando para a biblioteca ou para a faixa.
- O envio é feito por `media/upload-queue.ts`, fora do componente: um arquivo por vez, com `XMLHttpRequest` (`POST /api/videos`), progresso por arquivo, erro por `code` na própria linha e botão para fechar o aviso. Desmontar o console aborta o envio em curso.
- Cada vídeo aparece com miniatura (o primeiro quadro da tira), nome e duração. Resolução, fps e codec ficam só em Detalhes: do vídeo que está passando, quando o vídeo está ativo.
- Remover pede confirmação na própria linha quando o vídeo está na linha do tempo ("Remover vídeo" e "Manter").
- Sem celular, adicionar fica desabilitado com "Conecte o celular para enviar um vídeo". Com 20 vídeos guardados, aparece o texto de `errors.video_library_full`.

## 3. Linha do tempo (spec §2.3)

- As regras ficam em `data/timeline.ts`, um módulo puro com Vitest: mover, inserir o vídeo inteiro, cortar respeitando 0,5 s e a duração, dividir no cursor, excluir, posição por trecho, ponto de soltar, destino do arraste, passo da régua e quadro da tira. Os tempos vão com 3 casas.
- Faixa:
  - Trechos com largura proporcional à duração, a tira `/filmstrip` repetida na proporção do vídeo e o nome.
  - Régua com passo que mantém os rótulos afastados.
  - Cursor desenhado só com `transform`, a cada quadro.
- Gestos:
  - Arrastar um trecho muda a ordem, e os vizinhos abrem espaço.
  - As bordas cortam o começo ou o fim, com o tempo em décimos sobre a borda.
  - Clicar ou arrastar na régua pula. Com o vídeo ativo, o pedido sai ao soltar; com ele inativo, a régua move o cursor local, que é o ponto de Dividir.
  - Zoom de 1x a 32x.
- Cada mudança vira `PUT /api/timeline` com a linha do tempo inteira, ao soltar. A faixa mostra a mudança na hora e volta ao valor do agente se o pedido falhar.
- Teclado:
  - Espaço pausa e continua; setas pulam 5 s; Home volta ao começo.
  - Tab passa por cada trecho. Alt com setas move o trecho selecionado; S divide; Delete ou Backspace exclui.
  - Nas bordas, setas cortam 0,1 s (1 s com Shift).
- Rótulos acessíveis: o trecho mostra "Trecho n de N: nome, duração"; as bordas e a régua são `slider` com rótulo e `aria-valuetext`.
- Entre eventos do SSE, o cursor avança pelo relógio local, e o valor do agente o corrige a cada evento. Depois de um pulo, o cursor fica no ponto escolhido até chegar o próximo evento (`data/use-playback-position.ts`).

## 4. `/cam` (spec §2.4)

- `video_source` é lido em `data/control-message.ts`. Com `true`, a câmera para (faixa parada, luz apagada) pelo mesmo caminho do Desligar câmera. O visor dá lugar a "O computador está mostrando um vídeo", "A câmera deste celular está desligada." e o botão "Voltar à câmera", que manda `set_video_source` `false`.
- Com `false`, a câmera de `facing` é pedida de novo e volta ao `replaceTrack`, sem renegociar nem novo QR.
- Saíram o motivo `video_source` e `cam.ended_video_source` do `/cam`.

## 5. Erros (spec §2.5)

`video_too_large`, `video_unsupported`, `video_library_full` e `no_live_session` aparecem na linha do envio. `video_not_found`, `timeline_empty`, `video_source_active` e `video_source_inactive` aparecem no editor, abaixo da fileira de reprodução. Todos usam o texto de `errors.*`.

## 6. Testes e verificação

- `npm run build` sem avisos, `npm run lint` limpo, `npm test` com 209 testes.
- Testes novos:
  - `data/timeline.test.ts` (22).
  - `media/upload-queue.test.ts` (7: ordem, progresso por arquivo, erro que não para a fila, fechar aviso, abortar, assinatura).
  - `video-position` (relógio em décimos).
  - `control-message` (`video_source` e `set_video_source`).
  - `console-view` (QR e confirmação com o vídeo ativo).
- e2e num worktree temporário com `feature/video-web` e `origin/feature/video-agent` (71e75ab), no compose sem portas no host:
  - `video-source.spec.ts` passou (15 s). Com o celular falso em `live`, ele:
    - envia os dois vídeos de teste e confere os metadados do deitado (1280 × 720, h264, 6 s) e do em pé (720 × 1280);
    - adiciona os dois, corta o primeiro pela borda com o mouse, inverte a ordem arrastando, divide pela régua e exclui pelo teclado, conferindo a linha do tempo do agente a cada passo;
    - usa o vídeo: `virtualCamera.source` `video`, mesma sessão em `live` e o celular com "O computador está mostrando um vídeo";
    - pausa, pula pela régua (posição do agente em até 0,5 s) e continua;
    - volta à câmera pelo celular (vídeo inativo, mesma sessão, fonte `phone`, pílula Ao vivo), usa de novo e volta pelo console.
  - SSIM do CA-2 com o vídeo desativado: 0,9837 (mínimo 0,9820, 30 quadros). `light-quality` também passou.
  - Conjunto completo: 30 passaram e 1 falhou, `comparison.spec.ts:20` (a captura de tela do celular não chega ao painel; o console mostra "Sinal perdido"). A mesma falha acontece em `origin/feature/video-agent` sozinha, com o web da revisão 1, então não vem do web; já foi passada à sessão agent.
- Detector do `impeccable`: nenhum achado nos arquivos alterados.

## 7. Critérios de aceitação que a sessão web toca

| CA | Situação |
| --- | --- |
| 2 Sem celular | Console sem vídeo no Aguardando; adicionar desabilitado sem celular |
| 3 Usar vídeo e voltar | Celular com a câmera parada e a mensagem; Voltar à câmera pelo celular e pelo console sem novo QR, verificado no e2e. Bandeja e os 300 ms com o app real: não verificados por esta sessão |
| 4 Celular sai com o vídeo | QR na coluna do editor; visto em captura com dados simulados, não no e2e |
| 5 Editor | Adicionar, ordenar arrastando, cortar pela borda, dividir, excluir e pular pela régua, com mouse e teclado, verificados no e2e. Pausar para a posição: verificado. Mudança no Meet em até 1 s: não verificado |
| 9 Interface refeita | Sem controle repetido; direção das skills em `docs/design-v0.9.0.md`. Falta a conferência do usuário |
| 10 Arquivo que não é vídeo | Texto de `errors.video_unsupported` na linha do envio (teste da fila); apagar do disco é do agent |
| 11 CA-2 | SSIM 0,9837 |
| 12 Verificação | Build, lint, Vitest e e2e acima; `version` 0.9.0 em `web/package.json` |

## 8. Textos

- Chaves novas, nos dois arquivos:
  - `console.video_queued` ("Na fila")
  - `console.video_keep` ("Manter")
  - `console.video_dismiss` ("Fechar aviso")
  - `console.video_phone_camera_off` ("A câmera do celular fica desligada enquanto o vídeo passa.")
- Apagadas por não terem mais uso: `console.video_replace`, `console.video_timeline`, `console.video_title`, `console.video_duration`.
- `cam.ended_video_source` e `errors.no_video_file` não são mais usadas pelo web (o orquestrador apaga).

## 9. Não verificado

- O fluxo real fora do Docker (`uv run wcam`, celular real, câmera virtual no OBS, no app Câmera e no Meet): o WCam do usuário ocupa as portas 8080 e 8443.
- A tela do `/cam` com o vídeo ativo num celular real (`mobile-native` pede hardware). No e2e ela foi vista só pelo texto.
- Arrastar arquivos do Windows para a biblioteca e para a faixa: o e2e usa o seletor de arquivo; arrastar da biblioteca para a faixa também não está no e2e (o botão Adicionar está).
- O visual foi conferido por esta sessão em capturas do Chromium do compose, com dados simulados (editor vazio, inativo com seleção, ativo, ativo com zoom, congelado, sem celular, 390 px, confirmação de remover, cortando e arrastando). O usuário não viu.
- `review-animations` não pôde ser chamado por esta sessão (só roda por pedido do usuário).
- A falha do `comparison.spec.ts`, que depende da correção na sessão agent.

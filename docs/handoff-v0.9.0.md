# Handoff v0.9.0, sessões agent e web

De: orquestrador
Spec: `docs/specs/spec-v0.9.0.md` (Aprovada em 2026-11-15)
Contrato: `docs/contrato.md` (versão 0.9.0): seção nova "Vídeo como câmera"; rotas `PUT`/`DELETE /api/video-source/file`, `PUT /api/video-source`, `PUT /api/video-source/position`; `videoSource` no status e no SSE; `video` em `virtualCamera.source`; `video_source` em `lastEnded.reason` e nos eventos do `/dev`; `frozen` aceito sem celular com o vídeo ativo; erros `video_too_large`, `video_unsupported`, `no_video_file`, `video_source_active` e `video_source_inactive`
ADR: `docs/adr/0016-video-como-origem-da-camera.md`
Planejamento: §5.4 (Usar vídeo, Pular no vídeo, bandeja com seis estados) e §6 (0.9.0 Vídeo como câmera; 0.10.0 Desempenho, zoom passa a 0.11.0)

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-video` | `feature/video-agent` |
| web | `.worktrees/web-video` | `feature/video-web` |

Os worktrees são criados a partir de `feature/video`. Antes do relatório, `git merge origin/feature/video`.

## Textos

Já em `locales/` na integração:
- Compartilhadas e do agent: `state.video`, `controls.use_video`, `controls.back_to_phone`, `tray.use_video`, `errors.video_too_large`, `errors.video_unsupported`, `errors.no_video_file`, `errors.video_source_active`, `errors.video_source_inactive`.
- Web: `cam.ended_video_source`, `console.video_*` (título, escolher, arrastar, progresso, remover, trocar, duração, aviso de que a câmera mostra o vídeo, rótulo e tempos da linha do tempo).

Regras da v0.8.0 continuam: chaves compartilhadas e do agent (`controls.*`, `camera.*`, `state.*`, `terminal.*`, `tray.*`, `errors.*`) só mudam pelo orquestrador; `console.*`, `cam.*` e `dev.*` a sessão web pode ajustar ou acrescentar, nos dois arquivos no mesmo commit, listando no relatório.

## Ordem

1. Agent e web combinam por SendMessage um vídeo de teste e a ordem do e2e. Nada de subir o agente nas portas 8080 e 8443 nem abrir a câmera do usuário sem combinar comigo.
2. Em paralelo: agent com arquivo, reprodução, ativar e linha do tempo; web com a medição "antes" das bibliotecas (CA 9) antes de trocar qualquer coisa, depois área Vídeo e linha do tempo.
3. Troca de bibliotecas (spec §2.2) por último no web, com capturas antes e depois lado a lado no relatório.

## Sessão agent

1. **Arquivo** (spec §1.1): upload em partes direto no disco, sem carregar na memória, limite de 20 GB contado durante o envio (aborta e apaga ao passar), validação com PyAV decodificando o primeiro quadro, um vídeo por vez, arquivo sobrevive a reinício e o estado ativo não. Conferir o limite de corpo do uvicorn e do Starlette para 20 GB.
2. **Reprodução** (spec §1.2): origem nova no domínio, atrás do mesmo ponto em que o celular entrega quadros; decodificação e conversão no executor; tarefa com dono e cancelamento explícito. Ritmo pelo `pts` com relógio injetável para teste; rotação gravada aplicada; faixas Y=16, UV=128; volta ao começo sem preto.
3. **Ativar e desativar** (spec §1.3): encerra a sessão com `video_source`, fecha o pareamento, `409 video_source_active`, controles conforme o contrato, prévia mostra o vídeo.
4. **Linha do tempo** (spec §1.4): `positionSeconds` pelo `pts` entregue; pular busca o quadro-chave anterior e decodifica sem entregar até o ponto, com a câmera repetindo o último quadro; posição parada com Congelar.
5. **Bandeja** (spec §1.5): item "Usar vídeo" marcável, desabilitado sem arquivo; sexto estado do ícone.
6. **Testes** da spec, com vídeos gerados no próprio teste. CPU do CA 6 medida com um vídeo 1080p30 H.264 e um 4K HEVC do iPhone (o usuário fornece o arquivo; combinar comigo). Mandar os números antes de fechar.
7. Versão 0.9.0 em `agent/pyproject.toml`.

## Sessão web

Skills de design obrigatórias e registradas em `docs/design-v0.9.0.md`: `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `dataviz` para os gráficos; `animate` e `review-animations` se houver movimento.

1. **Medição antes** (CA 9): tamanho gzip do JS de `/` e `/dev` e CPU do navegador com o `/dev` aberto por 2 min na janela de 120 s, com o mesmo procedimento que será usado depois.
2. **Área Vídeo** (spec §2): escolher ou arrastar, progresso, metadados (fps e resolução só em Detalhes), Usar vídeo, Voltar ao celular, Remover vídeo; estado "Vídeo em repetição" com a prévia no lugar do QR e da área do celular. Envio com `XMLHttpRequest` num módulo fora do componente. Erros por `code`.
3. **Linha do tempo** (spec §2.1): posição, duração, barra com clique, arraste (pede ao soltar) e teclado (setas, 5 s), rótulo acessível; avanço pelo relógio local entre eventos do SSE, corrigido pelo agente, parado com Congelar. Regra de posição num módulo puro em `data/` com Vitest.
4. **`/cam`**: mensagem do encerramento `video_source`.
5. **Bibliotecas** (spec §2.2): `uPlot` nos gráficos do `/dev` e `lucide-react` nos ícones, com o mesmo estilo de hoje (pedido do usuário): sem tema, legenda, tooltip ou animação padrão. Medição depois igual à de antes. Se uma das duas não cumprir o CA 9, ela não entra e o relatório diz por quê.
6. **e2e** da spec: enviar, ativar, prévia com imagem, linha do tempo, desativar volta ao QR; SSIM do CA-2 com o vídeo desativado.
7. Versão 0.9.0 em `web/package.json`.

## Fechamento

Relatórios em `docs/relatorio-v0.9.0-agent.md` e `docs/relatorio-v0.9.0-web.md`, com cada CA que a sessão toca, o que foi medido e o que não foi verificado. Verificação completa do CLAUDE.md antes. PR de cada branch de sessão para `feature/video`. O usuário verifica o visual; avisem só quando terminar ou quando precisarem dele.

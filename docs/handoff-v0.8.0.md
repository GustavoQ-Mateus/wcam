# Handoff v0.8.0, sessões agent e web

De: orquestrador (`wcam-38`)
Spec: `docs/specs/spec-v0.8.0.md` (Aprovada em 2026-11-12)
Contrato: `docs/contrato.md` (versão 0.8.0): seções novas "Controles", "Eventos do console", "Prévia do console" e "Console do desenvolvedor"; `confirmations` e `rtpPacketsBeforeLive` em `session`; `controls` no status; `held` e `camera_off` em `virtualCamera.source`; `confirmation`, `controls`, `stats_request`, `confirm_code`, `reject_code`, `set_controls` e `stats` no DataChannel; `no_live_session` na tabela geral de erros
Planejamento: §4 (confirmação nos dois lados), §5.2, §5.3 e §5.4 (Congelar imagem e Desligar câmera no lugar de Pausar, ícone da bandeja com cinco estados), §6 (0.9.0 vira "Zoom e enquadramento")
Protótipo aprovado: https://claude.ai/artifact/4j5uK8opMCjxa2iy1p1F8b (telas "Console: aguardando celular", "Console: confirmar código", "Console: ao vivo", "Console do desenvolvedor", "Bandeja: console rápido")

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-console` | `feature/console-agent` |
| web | `.worktrees/web-console` | `feature/console-web` |

Os worktrees são criados a partir de `feature/console`. Antes do relatório, `git merge origin/feature/console` para pegar o que mudar na integração.

## Textos

Já em `locales/` na integração:
- Revisão de linguagem (spec §6): `console.status_checking`, `console.status_running`, `console.cpu`, `errors.network_error`, `errors.web_not_built`, `errors.invalid_request`, `errors.internal_error` e `errors.pairing_window_closed` sem termos internos. `console.confirm` e `console.reject` passam a "É igual" e "É diferente"; `console.confirm_title` e `cam.confirm_title` com a pergunta nova.
- Compartilhadas (web e bandeja): `controls.*`, `camera.front`, `camera.back`, `state.*` (estado em texto para console, celular e dica da bandeja).
- Agent: `terminal.confirm_hint`, `tray.*` (`tray.tooltip` recebe `{state}` de `state.*`), `errors.no_live_session`.
- Web: `console.step_*`, `console.confirmation_*`, `console.frozen_since`, `console.preview_hidden`, `console.phone_title`, `console.orientation_*`, `console.path_*`, `console.apps_none`, `console.apps_count`, `console.details`, `console.developer`, `cam.confirm_same`, `cam.confirm_different`, `cam.confirm_waiting_pc`, `cam.ended_code_different`, `cam.frozen`, `cam.camera_off` e `dev.*`.

Regras:
- Chaves compartilhadas e as do agent (`controls.*`, `camera.*`, `state.*`, `terminal.*`, `tray.*`, `errors.*`) só mudam pelo orquestrador: peçam por SendMessage.
- Chaves só do web (`console.*`, `cam.*`, `dev.*`) a sessão web pode ajustar ou acrescentar, nos dois arquivos no mesmo commit, e lista no relatório.
- Chaves que ficam sem uso saem no mesmo commit que tira o uso, nos dois arquivos: `cam.confirm_body`, `cam.switch_camera`, `cam.preview_off` (substituídas por `controls.*`), `console.disconnect`, `console.state_live`, `console.source_*` e o que mais o console novo deixar de usar.

## Ordem

1. **Spike `zoom` (web) primeiro**, em `spike/zoom`, a partir de `feature/console`. O teste no iPhone é feito pelo usuário; marquem comigo antes de pedir. Nada de subir o agente nas portas 8080 e 8443 ou abrir a câmera sem combinar.
2. **Confirmação nos dois lados (spec §1)** é a primeira coisa de produto nas duas sessões: é correção de segurança. Agent e web combinam por SendMessage a ordem do teste e2e do falso computador.
3. Depois, em paralelo: controles, SSE, prévia, `/dev`, bandeja.

## Sessão agent

1. **Confirmação** (spec §1.2, contrato "Código de confirmação" e DataChannel): `confirmations` na sessão, `confirm_code` e `reject_code`, `confirmation` ao celular, `live` só com os dois lados, `confirmation_timeout` para os dois. Antes de `live`: qualquer outra mensagem ignorada com log; `rtpPacketsBeforeLive` contado pelos pacotes RTP de vídeo que chegam (no ponto mais cedo possível do aiortc, isolado num módulo como nas regras anteriores sobre o aiortc), também em `lastEnded`. `FrameGate` fica. `terminal.confirm_hint` impresso quando a conexão chega a `awaiting_confirmation`.
   - Testes de integração com celular aiortc: confirma PC depois celular, celular depois PC, só PC até o tempo limite, `reject_code`, mensagem de controle antes de `live`. Em todos, `rtpPacketsBeforeLive` 0 com um celular que segue o contrato; e um teste com um celular que envia vídeo antes de `live` (faixa já no transceiver) prova que o contador conta e que nenhum quadro chega à câmera.
2. **Controles** (contrato "Controles"): estado `controls` no domínio, `PATCH /api/controls`, `set_controls`, `controls` ao celular. Congelar repete o último quadro entregue (`held`); câmera desligada gera o quadro com o ícone de câmera riscada no formato anunciado (desenho em YUV pelo próprio agente, sem imagem externa; teste com valores de pixel no centro e na borda); espelho inverte colunas de Y, U e V (teste com quadro sintético). Espelho no executor junto da tradução de cor, sem passo extra fora dele.
3. **SSE do console** (`GET /api/events`): evento `status` ao conectar, a cada mudança e a cada 1 s. Um publicador no domínio, com assinantes; a borda HTTP só serializa. Teste de que uma mudança de controle chega ao assinante em menos de 300 ms.
4. **Prévia** (contrato "Prévia do console"): segunda conexão aiortc só em loopback, faixa que lê o último quadro entregue e reduz para 960x540 no executor, até 30 fps. Uma por vez. Medir CPU do processo em 1080p30 e 2160p30 com e sem prévia (2 min cada, câmera falsa basta para o custo da prévia) e mandar os números para mim antes de fechar: escrevo a ADR 0015. Se a prévia passar de 10 pontos de CPU, cai para 15 fps.
5. **Console do desenvolvedor** (contrato "Console do desenvolvedor"): `GET /api/dev/events`, coleta por etapa ligada só com assinante (teste: sem assinante, o coletor não mede), `stats_request` ao celular, `stats` guardado, eventos (últimos 50).
6. **Bandeja** (spec §5): `pystray` como dependência nova (registrar a justificativa no relatório), atrás de um `Protocol` com implementação falsa para teste, thread com dono e encerramento explícito. Ícones desenhados em código (Pillow já vem com o pystray) nos cinco estados com cor e forma; dica com `tray.tooltip`. Menu nativo do spec §5, textos de `locales/`, itens desabilitados sem celular. Sair encerra como o Ctrl+C (`terminal.stopped`, código 0). Sem Windows ou sem `pystray`, segue sem bandeja com log.
7. **Linguagem** (spec §6): teste pytest que lê `locales/en.json` e `locales/pt-BR.json` e falha se um termo proibido aparecer num valor (não na chave): agente, servidor, sessão, token, pareamento, requisição, interface, agent, server, session, token, pairing, request, interface. Exceções só para chaves `dev.*` e `terminal.fingerprint`, listadas no teste.
8. Versão 0.8.0 em `agent/pyproject.toml`.

## Sessão web

Skills de design obrigatórias e registradas em `docs/design-v0.8.0.md`, decisão por decisão: `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `mobile-native` para o celular e `dataviz` para os gráficos de `/dev`; `animate` e `review-animations` se houver movimento. O protótipo aprovado é a direção: seguir layout, hierarquia e nomes; os tokens são os de §5.6.

1. **Spike `zoom`** (spec §0): página temporária só na branch do spike. Resultado em `docs/relatorio-v0.8.0-web.md`, com a tabela por câmera.
2. **Confirmação no celular** (spec §1.1): transceiver sem faixa (`addTransceiver("video", {direction: "sendonly"})`), a câmera entra com `replaceTrack` só em `live`; visor pode mostrar a câmera antes. Tela Confirmar com o código, É igual e É diferente, estado depois de É igual (`confirmation`), encerramento com `cam.ended_code_different` quando o próprio celular recusou. `camera_capabilities` e `set_video_format` só depois de `live`. Vitest na lógica do publicador: nenhum `replaceTrack` com câmera e nenhuma mensagem fora `confirm_code` e `reject_code` antes de `live`.
3. **Console** (spec §2): estados da §2.1, SSE no lugar da consulta periódica, prévia por WebRTC local (hook em `media/`), painel do celular com frontal e traseira, caminho da imagem, Detalhes recolhível com os termos técnicos, seletor de formato refeito no visual novo, link Desenvolvedor.
4. **Controles** (spec §3): console e celular. No celular: Congelar mostra `cam.frozen`; Desligar câmera faz `track.stop()` e `replaceTrack(null)`, visor preto com Ligar câmera; Trocar câmera pelo `facing` recebido. O estado mostrado é sempre o do último `controls`, nunca a escolha local.
5. **Console do desenvolvedor** (spec §4): rota `/dev`, layout do protótipo, gráficos em SVG próprio (sem biblioteca), janela de 30, 60 ou 120 s, Pausar gráficos, Exportar CSV (até 10 min de amostras). No celular: `stats` a cada 1 s enquanto `stats_request` ligado, montagem da mensagem em `data/` com Vitest.
6. **e2e** (Playwright, câmera falsa): falso computador (o teste altera a impressão digital na resposta para o código divergir; o celular toca em É diferente; `lastEnded.rtpPacketsBeforeLive` 0 e `rejected`), só PC confirmado até o tempo limite (0 pacote), confirmação nas duas ordens; cada controle aparece no outro lado em menos de 300 ms; prévia mostra imagem e fecha ao desligar; SSIM de pelo menos 0,98 com a prévia ligada e Espelhar desligado.
7. Versão 0.8.0 em `web/package.json`.

## Fechamento

Relatórios em `docs/relatorio-v0.8.0-agent.md` e `docs/relatorio-v0.8.0-web.md`, com cada CA da spec que a sessão toca, o que foi medido e o que não foi verificado. Verificação completa do CLAUDE.md antes. PR de cada branch de sessão para `feature/console`. O usuário verifica o visual; avisem só quando terminar ou quando precisarem dele.

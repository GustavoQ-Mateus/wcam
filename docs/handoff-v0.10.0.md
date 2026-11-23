# Handoff v0.10.0, sessões agent e web

De: orquestrador
Spec: `docs/specs/spec-v0.10.0.md` (Aprovada em 2026-11-15)
Contrato: `docs/contrato.md` 0.10.0: `session.video.decoder`, `videoSource.decoder`, etapa `transfer` nos tempos por etapa, evento `decoder` do `/api/dev/events` (motivos `unsupported`, `open_failed`, `stream_error`, `disabled`), `WCAM_HW_DECODE`
Planejamento: §6, linha 0.10.0

Worktrees e branches a partir de `origin/feature/performance`:

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-performance` | `feature/performance-agent` |
| web | `.worktrees/web-performance` | `feature/performance-web` |

Antes de começar e antes do relatório, `git merge origin/feature/performance`.

## Textos

Na integração: `console.detail_decoder`, `console.detail_decoder_hardware` ("Placa de vídeo"), `console.detail_decoder_software` ("Processador"), `dev.stage_transfer`. O aviso da troca imediata de formato só entra se a ADR da §1.4 decidir por ela; eu acrescento antes do código.

## Ordem

1. Agent: medição de "antes" na v0.9.0 (CPU e tempos por etapa com o celular em 2160p30 e 1080p30 e com `C:\Users\gusta\Downloads\IMG_0641.MOV` em 4K, só leitura) e o spike de decodificação da §1.6. Os números vêm para mim antes de qualquer código da §1.1; eu escrevo a ADR do caminho com eles.
2. Web, em paralelo: rótulo do decodificador nos detalhes e etapa `transfer` no `/dev`, pelo contrato. O limite novo do indicador "Processamento p95" espera o número do agent, que ele manda por SendMessage.
3. Agent: §1.1, §1.2 e §1.5 depois da ADR; §1.3 (reunião de 30 min) e o spike da §1.4 precisam do usuário e do celular: combinem comigo o horário antes.
4. Nada nas portas 8080 e 8443 nem na câmera do usuário sem combinar comigo.

## Sessão agent

1. **Antes e spike** (§1.6): `hwaccel` disponíveis no PyAV instalado, perfis da UHD 630 (H.264 High, HEVC Main e Main 10), como encaixar na recepção do aiortc sem copiar o aiortc e o custo de cada opção, tempo por quadro e CPU em 1080p30 e 2160p30 com a cópia para a memória incluída. Sem caminho usável no PyAV, as alternativas com custo, e paramos para decidir com o usuário.
2. **Decodificação na placa de vídeo** (§1.1): fallback para software ao abrir e no meio do fluxo sem derrubar a sessão, com PLI ao celular; igualdade de bytes com software no vídeo de referência (teste pulado sem placa de vídeo); etapa `transfer` fora do event loop; `WCAM_HW_DECODE`; `decoder` no status e evento `decoder` no `/dev`.
3. **Tradução de cor** (§1.2): sem prender o event loop nem o GIL; igualdade de bytes contra a v0.9.0 em faixa cheia, limitada, retrato e espelhado. Técnica e números no relatório.
4. **Vídeo como câmera** (§1.5): a reprodução usa a §1.1; CA 8 da v0.9.0 com o HEVC 4K e a câmera em 4K; troca de caminho sem preto.
5. **Quedas de fps** (§1.3): reunião de 30 min no Meet em 2160p30 e 1080p30 com o CSV do `/dev`, separando celular, rede e PC; corrigir o que for do PC.
6. **Troca de formato** (§1.4): spike com Meet, Teams, Zoom, Discord, OBS e app Câmera, tabela por app para a minha ADR. Mudança no `vcam` só se a ADR pedir.
7. Limite revisto do "Processamento p95" a partir das medições, mandado para a web.
8. Testes da spec. `version` 0.10.0 no `agent/pyproject.toml`.

## Sessão web

Skills: `impeccable` (`audit` e `polish` no que mudar), `emil-design-eng`; registro curto em `docs/design-v0.10.0.md`. Regras anti slop e tokens de §5.6 valem.

1. **Detalhes do console** (§2): "Decodificação" com "Placa de vídeo" ou "Processador", só na área de detalhes, pelo `session.video.decoder` (e `videoSource.decoder` com o vídeo ativo); sem linha quando `null`.
2. **`/dev`** (§2): etapa `transfer` nos tempos por etapa, evento `decoder` na lista de eventos, limite novo do indicador quando o agent mandar. Mesmo estilo de gráfico. CSV com a coluna da etapa nova.
3. **Zoom por Ctrl com a roda** sobre a faixa da linha do tempo, se couber sem atrasar.
4. Vitest no rótulo do decodificador e no limite do indicador; e2e com `decoder` `software` no status e o SSIM do CA-2.
5. `version` 0.10.0 no `web/package.json`.

## Fechamento

Relatórios em `docs/relatorio-v0.10.0-agent.md` e `docs/relatorio-v0.10.0-web.md`, com cada CA tocado, o que foi medido (antes e depois, mesmo procedimento, PC i5-8500 de 6 núcleos com UHD 630) e o que não foi verificado. Verificação completa do CLAUDE.md antes. PR de cada branch de sessão para `feature/performance`. O usuário confere o visual; avisem só quando terminar ou quando precisarem dele.

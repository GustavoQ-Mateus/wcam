# Handoff v0.9.0 revisão 2, sessões agent e web

De: orquestrador
Spec: `docs/specs/spec-v0.9.0.md` (revisão 2, Aprovada em 2026-11-15)
Contrato: `docs/contrato.md` 0.9.0, seção "Vídeo como câmera" reescrita, mais `video_source` e `set_video_source` no DataChannel, erros `video_library_full`, `video_not_found`, `timeline_empty`, `video_source_active` (agora nos controles), `cameraOff`/`facing` com o vídeo ativo
ADR: `docs/adr/0017-video-com-celular-conectado-e-linha-do-tempo.md` (substitui em parte a 0016)
Planejamento: §5.4 (Usar vídeo só com celular, Voltar à câmera nos três lugares, editar a linha do tempo)

Mesmos worktrees e branches da revisão 1, a partir de `feature/video` atualizada:

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-video` | `feature/video-agent` |
| web | `.worktrees/web-video` | `feature/video-web` |

Antes de começar e antes do relatório, `git merge origin/feature/video`.

## O que muda da revisão 1

- O celular não é mais desconectado ao usar vídeo: fica em `live` com a câmera desligada. Sai o motivo `video_source` e o `409 video_source_active` do pareamento.
- Um arquivo vira biblioteca (`/api/videos`) e linha do tempo de trechos (`/api/timeline`). Sai `/api/video-source/file`.
- Envio e ativação só com o celular em `live`.
- Bugs da bateria: linhas verdes e azuis em 4K, travamentos, botão Descongelar repetido, área Vídeo solta abaixo do QR.

## Textos

Na integração: `controls.back_to_phone` agora diz "Voltar à câmera"; `errors.video_source_active` com texto novo; `errors.video_library_full`, `errors.video_not_found`, `errors.timeline_empty`; `cam.video_playing`, `cam.video_playing_body`, `cam.back_to_camera`; `console.video_library`, `console.video_add`, `console.video_needs_phone`, `console.video_remove_in_use`, `console.timeline_*` (vazia, dividir, excluir, zoom, pausar, continuar, rótulos de trecho, bordas e cursor).

`cam.ended_video_source` e `errors.no_video_file` saem: parem de usar; eu apago dos dois arquivos no fechamento. `console.video_replace`, `console.video_drop` e `console.video_timeline` a sessão web pode apagar se não usar mais. Regras de chave da v0.8.0 continuam.

## Ordem

1. Agent primeiro nos bugs (linhas verdes, travamentos), já pedidos por mensagem: diagnóstico com números para mim antes de seguir.
2. Agent e web combinam por SendMessage o formato de `videoSource`, a ordem do e2e e os vídeos de teste. Nada nas portas 8080 e 8443 nem na câmera do usuário sem combinar comigo (o WCam do usuário roda pelo agent0.6.0).
3. Web começa com `impeccable shape` do editor e o módulo puro da linha do tempo, em paralelo com o agent.

## Sessão agent

1. **Bugs** (spec §1.6): causa raiz das linhas verdes com teste que falha antes; medições de travamento em 1080p30 e 4K com o vídeo de teste e `C:\Users\gusta\Downloads\IMG_0641.MOV` (só leitura); correção do que for ritmo ou agendamento.
2. **Biblioteca** (§1.1): `POST /api/videos` com `409 no_live_session` antes de ler o corpo, limite de 20 GB e de 20 vídeos, validação, tira de miniaturas em JPEG (até 60 quadros, 160 de largura, rotação aplicada), `DELETE`, persistência por migration nova (tabelas de vídeos e trechos, SQL no padrão do CLAUDE.md). Migrar ou descartar o arquivo único da revisão 1 que já estiver no diretório de dados, sem quebrar o início do agente.
3. **Linha do tempo** (§1.2): `PUT /api/timeline` com as regras, aplicada na hora.
4. **Reprodução** (§1.3): sequência de trechos com o próximo aberto antes do fim do atual, no máximo um quadro repetido na troca; volta ao começo; pular na linha do tempo inteira; posição e Congelar como na revisão 1.
5. **Usar vídeo** (§1.4): sessão continua `live`; `video_source` para o celular ao ativar, desativar e ao chegar a `live` com vídeo ativo; `set_video_source` do celular; falta de quadros do celular com o vídeo ativo não é queda nem `frozen`; vídeo continua se o celular sair; controles com `409 video_source_active`.
6. **Bandeja** (§1.5): "Usar vídeo" habilitado só com celular `live` e trecho, ou com o vídeo ativo; rótulo "Voltar à câmera" pela chave.
7. Testes da spec. Versão 0.9.0 já está no `agent/pyproject.toml`; confira.

## Sessão web

Skills obrigatórias, registradas em `docs/design-v0.9.0.md` (refeito, dizendo o que mudou da revisão 1 e por quê): `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `mobile-native` no `/cam`, `animate` e `review-animations` em arrastar, cortar e no cursor. Regras anti slop e tokens de §5.6 valem.

1. **Onde o vídeo aparece** (§2.1): nada de vídeo sem celular `live` e sem vídeo ativo; "Usar vídeo" junto dos controles com o celular `live`; editor em tela com prévia, barra de reprodução, linha do tempo na largura toda e biblioteca ao lado; "Voltar à câmera" sempre visível; cada controle uma vez só (Descongelar repetido era bug).
2. **Biblioteca** (§2.2): vários arquivos, envio em fila com `XMLHttpRequest` fora do componente, progresso por arquivo, metadados técnicos só em Detalhes, remover com confirmação se em uso, adicionar arrastando ou pelo botão.
3. **Linha do tempo** (§2.3): trechos com a tira de miniaturas, régua, cursor, arrastar para ordenar, cortar pelas bordas com o tempo visível, dividir (S), excluir (Delete), zoom, teclado e rótulos acessíveis; `PUT /api/timeline` ao soltar; regras num módulo puro em `data/` com Vitest; cursor pelo relógio local corrigido pelo SSE.
4. **`/cam`** (§2.4): `video_source` para a faixa (luz apagada) e mostra a mensagem com "Voltar à câmera"; `false` pede a câmera e volta ao visor sem renegociar.
5. **Erros** (§2.5) por `code`.
6. **e2e** da spec com o celular falso em `live`; SSIM do CA-2 com o vídeo desativado.
7. Versão 0.9.0 no `web/package.json` (confira).

## Fechamento

Relatórios novos em `docs/relatorio-v0.9.0-r2-agent.md` e `docs/relatorio-v0.9.0-r2-web.md`, com cada CA tocado, o que foi medido e o que não foi verificado; o do agent com as medições da §1.6 e o CPU do PC certo (i5-8500, 6 núcleos). Verificação completa do CLAUDE.md antes. PR de cada branch de sessão para `feature/video`. O usuário confere o visual; avisem só quando terminar ou quando precisarem dele.

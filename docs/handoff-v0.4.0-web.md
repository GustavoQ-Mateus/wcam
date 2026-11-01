# Handoff v0.4.0, sessão web

De: orquestrador
Para: sessão `web`
Spec: `docs/specs/spec-v0.4.0.md` (Aprovada)
Contrato: `docs/contrato.md` (versão 0.4.0)

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\web-camera-virtual`. Faça `cd` para ela e trabalhe só dentro dela.
- Branch: `feature/camera-virtual-web`, a partir de `feature/camera-virtual`. PR futuro para `feature/camera-virtual`.
- Não edite `agent/`, `locales/`, arquivos da raiz nem `docs/` (exceto o relatório). O contrato é o ponto de encontro com a sessão agent; pergunte antes de qualquer desvio.

## Escopo

A seção "Escopo da sessão web" da spec. Esta versão não tem tela nova na `/cam` e não tem fase de design.

1. **Console provisório:** acrescente a câmera virtual (ativa ou indisponível, com o motivo), a origem (celular ou quadro preto), o codec, a CPU do agente e o aviso de `framesScaled`. Os textos já estão em `locales/` (`console.virtual_camera_*`, `console.source_*`, `console.frames_scaled` e `console.cpu`). Mesmas regras de antes: tokens e anti AI slop.
2. **Tipos do contrato 0.4.0** em `data/contract.ts`.
3. **e2e do fluxo completo:** confere `virtualCamera.source` indo de `placeholder` a `phone` depois do Confirmar, e de volta a `placeholder` depois de Desconectar.
4. **e2e de qualidade:** um projeto Playwright que lança o Chromium com `--use-file-for-fake-video-capture=<referência .y4m>`. O caminho dentro do container vem da sessão agent, que vai te avisar. Faça o fluxo até `live`, espere pelo menos 30 quadros em `quality.frames` e confira `quality.ssim >= 0.98`. Registre no relatório o SSIM médio e o mínimo medidos.
5. Versão 0.4.0 no `package.json`.

## Verificação

A partir de `.worktrees/web-camera-virtual/web`: `npm run build` sem avisos, `npm run lint`, `npm test`. Antes do relatório, o e2e no compose contra o agente da integração (faça `git merge origin/feature/camera-virtual` quando a sessão agent entregar).

## Commits e relatório

Conventional Commits, sem referência a Claude ou Anthropic. Push liberado; PR não. No fim, `docs/relatorio-v0.4.0-web.md`, e me avise (`wcam-c8`).

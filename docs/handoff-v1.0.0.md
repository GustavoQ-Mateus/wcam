# Handoff v1.0.0, sessões app, agent e web

De: orquestrador
Spec: `docs/specs/spec-v1.0.0.md` (Aprovada em 2026-11-23, com o atalho na tela da §1.1)
ADR: `docs/adr/0022-app-windows-em-csharp.md` (app em C#, agente Python como processo filho)
Contrato: sem mudança prevista (§7 da spec). Precisou de rota ou variável nova, me peça antes do código.
CLAUDE.md: nova pasta `app` e a verificação dela.

| Sessão | Worktree | Branch |
|---|---|---|
| app (C#, inclui o instalador) | `.worktrees/app-windows` | `feature/windows-app-app` |
| agent | `.worktrees/agent-windows` | `feature/windows-app-agent` |
| web | `.worktrees/web-windows` | `feature/windows-app-web` |

Todas a partir de `origin/feature/windows-app`. Antes de começar e antes do relatório, `git merge origin/feature/windows-app`. O WCam do usuário roda pelo terminal `wcam1.0.0`; nada nas portas 8080 e 8443 nem na câmera do usuário sem combinar comigo.

## Textos

Na integração: `tray.start_with_windows`, `tray.agent_restarting`, `tray.agent_stopped`, `tray.show_overlay`, `overlay.*` (ícone, painel, prévia flutuante, ajuda do Ctrl, atalho de teclado, esconder). O título da janela usa `app.name`; os controles do painel reusam `controls.*` e `tray.*`. Textos do instalador: a sessão app propõe como o Inno Setup lê os textos (de `locales/` ou gerados a partir dele) e me pede as chaves.

## Ordem

1. **Spikes primeiro, números para mim antes do código** (spec §0):
   - app: WinUI com Native AOT, bandeja e janela WebView2 (tamanho, abertura, memória, publish sem avisos); a prévia em qualidade total na janela e a prévia flutuante (caminhos e CPU em 1080p30 e 2160p30, com o Meet aberto); a exclusão de captura de tela no ícone, no painel e na prévia flutuante.
   - agent: PyInstaller em pasta, com o processo filho de decodificação da ADR 0018 funcionando dentro do executável, e o modo filho (sem bandeja, encerra quando o pai morre).
2. Eu escrevo a ADR da prévia com os números e emendo o contrato se precisar.
3. Implementação em paralelo: app (bandeja, janela, atalho na tela, ciclo de vida, prioridade do agente, instalador), agent (modo filho, empacotamento, saída do `pystray`), web (console dentro do app).
4. Medições com o usuário pelo `wcam1.0.0`: reunião de 15 min em 2160p30 com a prioridade do agente; instalação limpa; `nmap`; Meet, Teams, Zoom, Discord, OBS e um site com `getUserMedia`.

## Sessão app

Skills para o atalho na tela e a janela: `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `animate` e `review-animations`, registradas em `docs/design-v1.0.0.md`. Regras anti slop e tokens de §5.6. Regras de C# do CLAUDE.md, iguais às do `vcam`.

1. Spike (§0) e números.
2. App (§1): uma instância só; agente como processo filho com saúde por `GET /api/health`, nova tentativa com limite, encerramento junto; bandeja com os controles de hoje e "Iniciar com o Windows"; janela WebView2 do console com tamanho e posição lembrados.
3. Atalho na tela (§1.1): ícone preso na borda escolhida (Ctrl para arrastar), painel pelo Ctrl com o mouse e por atalho global, prévia flutuante arrastável e redimensionável, exclusão de captura, estado sem depender só de cor.
4. Prioridade do agente: acima do normal, sem EcoQoS, MMCSS de captura nas threads de decodificação e entrega (o agent expõe o que for preciso); medida em reunião.
5. Instalador (§4) em `installer`: um pedido de administrador, registro da câmera, regra de firewall só 8443, rede privada e sub-rede local, desinstalação completa com a pergunta dos dados. Sem assinatura de código nesta versão.
6. Testes xUnit da spec. `version` 1.0.0.

## Sessão agent

1. Spike (§0) e números.
2. Modo filho (§2): sem bandeja nem navegador, encerra limpo quando o app pede ou o pai morre; `pystray` removido do produto e da dependência se nada mais usar.
3. Empacotamento PyInstaller em pasta com `web/dist`, `locales` e o FFmpeg do PyAV.
4. O que a prioridade do app precisar das threads de decodificação e entrega.
5. Testes da spec. `version` 1.0.0.

## Sessão web

1. Console dentro do app (§3): esconder o que não faz sentido na janela, pelo sinal que o app passa.
2. Prévia em qualidade total, se a ADR pedir algo do web.
3. Vitest e e2e de sempre. `version` 1.0.0.

## Fechamento

Relatórios em `docs/relatorio-v1.0.0-app.md`, `docs/relatorio-v1.0.0-agent.md` e `docs/relatorio-v1.0.0-web.md`, com cada CA tocado, o que foi medido e o que não foi verificado. Verificação completa do CLAUDE.md antes. PR de cada branch de sessão para `feature/windows-app`. O usuário confere o visual; avisem só quando terminar ou quando precisarem dele.

## Adendo de 2026-11-23 (levantamento da sessão web)

- Nada no console precisa ser escondido dentro do app: não há "abrir em nova aba", e o link para o `/dev` fica (é útil e só de leitura). Por isso não há sinal do app para o web nem mudança de contrato; a §3 da spec fica só com a prévia, se a ADR pedir.
- Para a sessão app, na WebView2:
  - liberar a câmera (`PermissionRequested`) só para a origem `http://127.0.0.1:8080`;
  - manter downloads (CSV e PNG) e `<input type=file>` funcionando;
  - `IsZoomControlEnabled = false`, para o zoom da página não disputar com o Ctrl+roda do editor;
  - decidir o menu de contexto padrão, as teclas do navegador (F5, Ctrl+P) e as DevTools: desligados no build de Release.

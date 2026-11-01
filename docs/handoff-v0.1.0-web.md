# Handoff v0.1.0, sessão web

De: orquestrador
Para: sessão `web`
Spec: `docs/specs/spec-v0.1.0.md` (Aprovada)
Contrato: `docs/contrato.md`

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\web` (worktree já criado). Faça `cd` para ela antes de qualquer coisa e trabalhe só dentro dela.
- Branch: `feature/fundacao-web`, criada a partir de `feature/fundacao`. PR para `feature/fundacao`, nunca para `main`.
- Não edite `docs/`, `locales/` nem `agent/`. Precisou de chave de idioma nova ou mudança no contrato, registre no relatório e o orquestrador decide.
- Node 24 e npm 11 estão instalados.

## Escopo

Da spec v0.1.0:

- §3 Web completo, do zero em `web/`:
  - Vite + React + TypeScript com `strict`, `noUncheckedIndexedAccess` e `exactOptionalPropertyTypes`.
  - `styles/tokens.scss` com todos os tokens de `docs/planejamento.md` §5.6 como variáveis CSS em `:root`, e `styles/base.scss` (reset, `color-scheme: dark`, foco visível com `--focus` em 2px e 2px de afastamento).
  - `router.tsx` sem biblioteca: `/cam` carrega `cam/cam-page.tsx`, qualquer outro caminho carrega `console/console-page.tsx`, ambos por `lazy()`. Mantenha os nomes de arquivo `cam-page` e `console-page`: o e2e identifica os chunks por eles.
  - `data/i18n.ts` puro (resolução de idioma e tradução com chaves tipadas a partir de `locales/en.json`, placeholders `{nome}`), separado de onde se lê `navigator.language`, para os testes rodarem sem navegador. `pt*` vira `pt-BR`, o resto vira `en`. Defina `document.documentElement.lang`.
  - `data/api-client.ts`: `fetch` tipado que converte o corpo de erro do contrato em `ApiError` com `code` e `status`; falha de rede vira `code` `network_error`.
  - `data/contract.ts` com os tipos de `docs/contrato.md` (`Health`, `Surface`, `ErrorBody`).
  - Páginas provisórias: console com o nome do produto e o estado de `GET /api/health` (`console.status_checking`, `console.status_running`, erro por `errors.<code>`); `/cam` com o nome e `cam.pair_instruction`. Sem direção visual definitiva ainda, mas já sem nada das regras anti AI slop do CLAUDE.md.
  - `index.html` com `viewport-fit=cover`, `theme-color` preto e `color-scheme` escuro.
  - `vite.config.ts`: proxy de `/api` para `process.env.VITE_AGENT_URL ?? "http://127.0.0.1:8080"` com `changeOrigin: true` (o agente rejeita `Host` desconhecido); `server.fs.allow` incluindo a raiz do repositório, porque `locales/` fica fora de `web/`; o `tsconfig` precisa incluir `../locales/*.json`.
  - ESLint (flat config, typescript-eslint strict, react-hooks), Prettier, Vitest e Playwright, com os scripts `dev`, `build` (`tsc -b && vite build`), `lint`, `test` e `test:e2e`.
- §5 Docker, só a sua parte:
  - `web/Dockerfile`: Node 24, `npm ci`, roda `npm run dev -- --host 0.0.0.0`. Contexto na raiz do repositório.
  - `web/e2e.Dockerfile`: imagem oficial `mcr.microsoft.com/playwright` na versão exatamente igual ao `@playwright/test` do `package-lock.json`, roda `npx playwright test`. Contexto na raiz.
  - O `docker-compose.yml` é da sessão agent e referencia esses dois arquivos.
- §7 Testes do web: os três testes Vitest da spec e os três e2e. O e2e lê `E2E_CONSOLE_URL` e `E2E_PHONE_URL` (falha com mensagem clara se faltarem), ignora erro de certificado e verifica que a `/cam` não pede nenhum arquivo com `console-page` no nome.

Os textos de `locales/` desta versão já existem na branch: `app.name`, `console.*`, `cam.*` e `errors.*`. Use-os; não escreva texto de interface no código.

Fora do seu escopo: `agent/`, `docker-compose.yml`, CI, arquivos da raiz, `locales/` e `docs/`.

## Critérios de aceitação sob sua responsabilidade

CA 6, 7 e 9 (lado web) da spec, verificados na sua branch. O CA 6 em e2e depende do agente; antes da integração, verifique pelo `npm run build`, que deve gerar chunks separados `console-page-*.js` e `cam-page-*.js`. Registre isso no relatório.

## Design

As páginas desta versão são provisórias. Use só os tokens, a tipografia do sistema e as regras anti AI slop do CLAUDE.md. A direção visual definitiva sai na spec de front, com as skills `taste-skill`, `impeccable` e `emil-design-eng`.

## Verificação antes de cada commit

A partir de `.worktrees/web/web`: `npm run build` sem avisos, `npm run lint` e `npm test`.

## Commits

Conventional Commits com escopo `web`, um por unidade lógica, sem qualquer referência a Claude ou Anthropic. Push para `origin/feature/fundacao-web` liberado; PR só quando o orquestrador pedir.

## Relatório

Ao terminar, escreva `docs/relatorio-v0.1.0-web.md` na sua branch (é a única exceção à regra de não editar `docs/`), com:

1. O que foi feito, uma linha por mudança.
2. Cada CA sob sua responsabilidade: verificado, não verificado ou falhou, com a evidência.
3. Divergências da spec ou do contrato, com o motivo.
4. Versões fixadas das dependências principais (React, Vite, TypeScript, Playwright).
5. Perguntas em aberto para o orquestrador.

Depois avise o orquestrador (`wcam-c8`) por mensagem.
